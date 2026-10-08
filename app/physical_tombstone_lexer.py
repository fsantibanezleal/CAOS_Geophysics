"""Registered current tombstone lexical fields, not a generic JSON decoder.

The inherited token scanner keeps its original limits and implementation.
Only exact saved SQL/compact metadata paths have their already declared caps.
A non-building pass closes the schema/record envelopes before tree allocation.
The caller must then validate the complete current tombstone and native join.
"""

from app.physical_contract import M, _Reader, fields, require

ROOT = 'geophysics.physical-deletion/v2'
RECEIPT = 'geophysics.deletion-receipt-native/v1'
INVENTORY = 'geophysics.physical-deleted-inventory/v1'
JOINT_INVENTORY = 'geophysics.physical-deleted-inventory/v2'
JOINT = 'geophysics.joint-deleted-custody/v1'
INDEX_CAP = 256 * 1024
_JOINT_PATH = ('physical_inventory', 'joint')


def _lexical_cap(path):
    if (len(path) == 3 and path[0] == 'legacy_receipt'
            and path[1] in ('asset_hashes', 'asset_manifest', 'derived_manifest')
            and path[2] == 'utf8'):
        return 4*M
    if path in (
        _JOINT_PATH + ('datasets', None, 'body', 'utf8'),
        _JOINT_PATH + ('jobs', None, 'index', 'utf8'),
        _JOINT_PATH + ('jobs', None, 'request_utf8'),
    ):
        return INDEX_CAP
    return 8192


class _CurrentReader(_Reader):
    def __init__(self, source):
        super().__init__(source, 16, 200000)
        self.path = ()
        self.schemas = {}
        self.joint_seen = False

    def value(self, depth=1, key=None, *, build=True):
        previous = self.path
        self.path = () if depth == 1 else previous + (key,)
        path = self.path
        try:
            self.space()
            if self.pos < len(self.source) and self.source[self.pos] == '"':
                # Counts remain exactly those of inherited value(); keys still
                # use inherited string(128). No key-only utf8/base64 exemption.
                self.nodes -= 1
                require(self.nodes >= 0 and depth <= self.depth, 'structure_limit')
                result = self.string(_lexical_cap(path))
            else:
                result = super().value(depth, key, build=build)
            if path in (('schema',), ('legacy_receipt', 'schema'),
                        ('physical_inventory', 'schema'), _JOINT_PATH + ('schema',)):
                self.schemas[path] = result
            if path == ():
                fields(result, 'schema id project_id owner_id deleted_at origin_revision legacy_receipt physical_inventory')
            elif path == ('legacy_receipt',):
                fields(result, 'schema id owner_id project_id deleted_at backup_purge_status asset_hashes asset_manifest derived_manifest')
            elif path == ('physical_inventory',):
                schema = self.schemas.get(path + ('schema',))
                require(schema in (INVENTORY, JOINT_INVENTORY), 'current_tombstone_lexer_schema')
                fields(result, 'schema raw_assets datasets edges productions jobs custody source_policy_sha256 '
                       'waveform_sources waveform_artifacts profile_archives' + (' joint' if schema == JOINT_INVENTORY else ''))
            elif path == _JOINT_PATH:
                fields(result, 'schema originals datasets sources jobs artifacts')
                self.joint_seen = True
            elif _lexical_cap(path + ('utf8',)) > 8192 and result is not None:
                fields(result, 'utf8 bytes sha256')
            return result
        finally:
            self.path = previous

    def finish(self, *, build):
        result = self.value(build=build)
        self.space()
        require(self.pos == len(self.source), 'trailing_json')
        require(self.schemas.get(('schema',)) == ROOT
                and self.schemas.get(('legacy_receipt', 'schema')) == RECEIPT,
                'current_tombstone_lexer_schema')
        joint = self.schemas.get(('physical_inventory', 'schema')) == JOINT_INVENTORY
        require(self.joint_seen == joint and
                (not joint or self.schemas.get(_JOINT_PATH + ('schema',)) == JOINT),
                'current_tombstone_lexer_schema')
        return result


def decode_current_tombstone(chunks):
    """EOF/closed-envelope decoding; never historical admission or SQL repair."""
    body = bytearray()
    for chunk in chunks:
        require(type(chunk) is bytes, 'source_bytes')
        require(len(body) + len(chunk) <= 16*M, 'source_limit')
        body.extend(chunk)
    try:
        source = body.decode('utf-8', 'strict')
    except UnicodeError as error:
        from app.physical_contract import ContractError
        raise ContractError('encoding') from error
    require(not source.startswith('\ufeff'), 'bom')
    _CurrentReader(source).finish(build=False)
    return _CurrentReader(source).finish(build=True)
