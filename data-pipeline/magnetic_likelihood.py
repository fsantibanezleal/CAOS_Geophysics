"""Geometry-first, row-authorized likelihood decoding from original bytes.

No numerical imports until the complete byte/schema/geometry seal has passed.
Outer likelihood is unavailable until a final model is frozen, and is read once.
This is a trusted local separation seam, not a hostile-process security boundary.
"""

import hashlib
import struct

from magnetic_survey_json import _Lexer, _NUMBER, parse_request, fail
from magnetic_survey import plan_geometry


def _selected_tokens(text, span, indices):
    """Scan flat tokens without materializing an unrequested likelihood list."""
    lexer = _Lexer(b'[]')
    lexer.raw = text
    lexer.i = span.start
    lexer.punctuation('[')
    requested = set(indices)
    values = {}
    for index in range(span.count):
        if index in requested:
            values[index] = float(lexer.scalar())
        else:
            # Complete type/lexeme/hash validation already occurred before the
            # seal. Advance unrequested numeric lexemes WITHOUT converting the
            # observation into a Python number, even transiently in this reader.
            lexer.whitespace()
            number = _NUMBER.match(text, lexer.i)
            if number is None:
                fail('type', '$/likelihood', 'Previously validated numeric span required')
            lexer.i = number.end()
            lexer.token()
        lexer.whitespace()
        if index+1 < span.count:
            lexer.punctuation(',')
    lexer.punctuation(']')
    if lexer.i != span.end or len(values) != len(requested):
        fail('count', '$/likelihood', 'Authorized token count mismatch')
    return [values[i] for i in indices]


class SealedLikelihood:
    def __init__(self, raw):
        self.handle = parse_request(raw)
        self.plan = plan_geometry(self.handle)
        self.metadata = self.handle.metadata()
        lexical = _Lexer(raw)
        document = lexical.document()
        self._text = lexical.raw
        self._observed = document['observations']['values']['data']
        self._noise = document['noise']['values']['data']
        self._frozen = None
        self._outer_used = False

    def _rows(self, rows, role, fold):
        if type(rows) is not tuple or not rows or any(type(r) is not int for r in rows) or any(a >= b for a, b in zip(rows, rows[1:])):
            fail('partition', '$/rows', 'Strictly increasing original row tuple required')
        partition = self.plan['partition']
        if role in ('fit', 'validation', 'refit') and self._frozen is not None:
            fail('partition', '$/role', 'Fitting/selection likelihood is closed after final-model freeze')
        if role in ('fit', 'validation'):
            if type(fold) is not int or not 0 <= fold <= 2:
                fail('partition', '$/fold', 'Declared fold index required')
            allowed = partition['folds'][fold]['fit_rows' if role == 'fit' else 'validation_rows']['data']
        elif role in ('refit', 'development'):
            if fold is not None:
                fail('partition', '$/fold', 'Refit has no inner fold')
            if role == 'development' and self._frozen is None:
                fail('partition', '$/role', 'Development evaluation requires final-model freeze')
            allowed = self.plan['final_refit_rows']['data']
        elif role == 'outer':
            if fold is not None or self._frozen is None or self._outer_used:
                fail('partition', '$/outer', 'Outer likelihood requires a frozen model and one-time evaluation')
            allowed = partition['outer_rows']['data']
        else:
            fail('partition', '$/role', 'Unknown likelihood role')
        if tuple(allowed) != rows:
            fail('partition', '$/rows', 'Exact sealed role membership required')

    def read(self, rows, *, role, fold=None):
        self._rows(rows, role, fold)
        import numpy as np
        from magnetic_inverse import owned
        c = self.metadata['observations']['values']['shape'][1]
        indices = [row*c+j for row in rows for j in range(c)]
        observed = owned(np.array(_selected_tokens(self._text, self._observed, indices), dtype=np.float64).reshape(len(rows), c))
        if self.metadata['noise']['kind'] == 'diagonal_sd':
            noise = owned(np.array(_selected_tokens(self._text, self._noise, indices), dtype=np.float64).reshape(len(rows), c))
            if np.any(noise <= 0.):
                fail('uncertainty', '$/noise', 'Declared standard deviations must be positive')
        else:
            d = self.metadata['noise']['values']['shape'][0]
            principal = [i*d+j for i in indices for j in indices]
            noise = owned(np.array(_selected_tokens(self._text, self._noise, principal), dtype=np.float64).reshape(len(indices), len(indices)))
            if not np.array_equal(noise, noise.T):
                fail('uncertainty', '$/noise', 'Covariance must be exactly symmetric')
            try:
                np.linalg.cholesky(noise)
            except np.linalg.LinAlgError:
                fail('uncertainty', '$/noise', 'Principal covariance must be SPD')
            if float(np.linalg.cond(noise, 2)) > 1e8:
                fail('uncertainty', '$/noise', 'Principal covariance condition exceeds 1e8')
        if role == 'outer':
            self._outer_used = True
        return observed, dict(kind=self.metadata['noise']['kind'], values=noise)

    def validate_noise(self):
        """Validate the whole declared error model without reading observations."""
        import numpy as np
        shape = self.metadata['noise']['values']['shape']
        values = _selected_tokens(self._text, self._noise, range(self._noise.count))
        if self.metadata['noise']['kind'] == 'diagonal_sd':
            if any(v <= 0. for v in values):
                fail('uncertainty', '$/noise', 'Every declared SD must be positive')
        else:
            covariance = np.array(values, dtype=np.float64).reshape(shape)
            if not np.array_equal(covariance, covariance.T):
                fail('uncertainty', '$/noise', 'Complete covariance symmetry required')
            try:
                np.linalg.cholesky(covariance)
            except np.linalg.LinAlgError:
                fail('uncertainty', '$/noise', 'Complete covariance SPD required')
            if float(np.linalg.cond(covariance, 2)) > 1e8:
                fail('uncertainty', '$/noise', 'Complete covariance condition exceeds 1e8')
            if self.metadata['noise']['cross_partition_dependence'] == 'declared_absent':
                c = self.metadata['observations']['values']['shape'][1]
                partition = self.plan['partition']
                pairs = [(partition['outer_rows']['data'], partition['development_rows']['data'])]
                pairs += [(fold['fit_rows']['data'], fold['validation_rows']['data']) for fold in partition['folds']]
                for left, right in pairs:
                    i = [row*c+component for row in left for component in range(c)]
                    j = [row*c+component for row in right for component in range(c)]
                    if np.any(covariance[np.ix_(i, j)] != 0.):
                        fail('uncertainty', '$/noise/cross_partition_dependence',
                             'Nonzero cross-partition covariance contradicts declared_absent; do not remove it')

    def freeze(self, candidate, chi_si, *, receipt=None):
        import numpy as np
        a = self.metadata['prior']['start_si']['shape'][0]
        if (type(candidate) is not str or type(chi_si) is not np.ndarray or chi_si.dtype != np.float64
                or chi_si.shape != (a,) or not np.isfinite(chi_si).all() or self._frozen is not None):
            fail('type', '$/freeze', 'One explicit native final model freeze required')
        lower = self.metadata['prior']['lower_si']['data']
        upper = self.metadata['prior']['upper_si']['data']
        if np.any(chi_si < lower) or np.any(chi_si > upper):
            fail('physical_metadata', '$/freeze', 'Physical final model outside supplied bounds')
        model_hash = hashlib.sha256(b''.join(struct.pack('<d', float(v)) for v in chi_si)).hexdigest()
        if receipt is not None:
            import os
            from magnetic_local_paths import external_path
            from magnetic_calibration import descriptor
            from magnetic_survey_json import canonical
            path = external_path(receipt)
            body = canonical(dict(schema='magnetic-local-model-freeze-1', candidate=candidate,
                model_sha256=model_hash, chi_si=descriptor(chi_si), identity=self.plan['identity'],
                state='frozen_before_outer_evaluation', claims=self.plan['claims']))
            created = False
            try:
                with path.open('xb') as stream:
                    created = True
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
                if path.read_bytes() != body:
                    fail('durability', '$/freeze', 'Actual model-freeze readback mismatch')
            except BaseException:
                if created:
                    path.unlink(missing_ok=True)
                raise
        self._frozen = (candidate, model_hash, self.plan['identity']['configuration_sha256'])
        return model_hash

    def frozen(self):
        return self._frozen
