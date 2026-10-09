"""Closed literal allocated 0005/0006/0007 schema identities, never a mount.

Recognizing DDL is not recognizing another method's publication or custody.
Each nonempty extension still requires its own registered lifecycle reader.
"""

from types import MappingProxyType

from app.physical_contract import require
from app.physical_persistence import TABLES
from app.physical_successor import ddl_sha256


BASE_TABLES = frozenset(('access_tokens', 'account_usage', 'deletion_receipts',
    'observation_datasets', 'processing_jobs', 'projects', 'rate_windows',
    'raw_assets', 'source_records', 'user', 'waveform_dataset_sources',
    'waveform_result_artifacts', 'alembic_version', *TABLES))
JOINT_TABLES = frozenset(('joint_dataset_sources', 'joint_result_artifacts'))
MAGNETIC_TABLES = frozenset(('magnetic_survey_intakes', 'magnetic_survey_dataset_attempts',
    'magnetic_survey_admissions', 'magnetic_survey_attempts', 'magnetic_survey_members',
    'magnetic_survey_exports'))
DDL = MappingProxyType({
    '0005_physical_forest': 'b35d30cbbc77e7c26ad4d4c0efa7d2365cdd582e7e22979ca1ae0461ef1dacb4',
    '0006_joint_artifacts': 'f8adb510cd7ababbc2bfcc78bd511da64222f055526455c9ba6c1ee51c7f702c',
    '0007_magnetic_line_artifacts': '51f3fd52abd56feaf3017e49d807e0acaa2984fa6f21227dfcd60316aa65b9eb',
})
EXTENSIONS = MappingProxyType({
    '0005_physical_forest': frozenset(),
    '0006_joint_artifacts': JOINT_TABLES,
    '0007_magnetic_line_artifacts': JOINT_TABLES | MAGNETIC_TABLES,
})


def schema_tables(connection):
    heads = connection.execute('SELECT version_num FROM alembic_version').fetchall()
    require(len(heads) == 1 and heads[0][0] in DDL, 'physical_classifier_schema')
    revision = heads[0][0]
    require(ddl_sha256(connection) == DDL[revision], 'physical_classifier_schema')
    tables = BASE_TABLES | EXTENSIONS[revision]
    require({row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")} == tables,
            'physical_classifier_tables')
    return revision, tables


def require_bound_extensions(connection):
    """No zero-charge/empty-result exemption for unbound retained custody.

    Empty literal successor tables permit normal M01/legacy operation. Retained
    rows stay refused until their owning runtime supplies the actual specific
    custody adapter. This is a proof boundary, not a migration prerequisite.
    """
    revision, _ = schema_tables(connection)
    for table in sorted(EXTENSIONS[revision]):
        require(connection.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone() is None,
                'physical_union_custody_adapter_required:'+table)
    return revision
