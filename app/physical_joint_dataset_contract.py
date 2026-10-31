"""Exact structural M11 dataset grammar, no async importer or numerical import."""
# Functions copied unchanged from M11 41b2afe:app/joint_datasets.py.
from app import physical_joint_native_contract as native
from app.physical_contract import canonical as canonical_bytes
SCHEMA = "geophysics.joint-native-dataset/v1"

def close_manifests(payload):
    manifests = payload['manifests']; sources = payload['members']; total = 0
    parsed = {}
    for role in ('development','sealed'):
        main = 'request.json' if role == 'development' else 'sealed.json'
        raw = canonical_bytes(manifests[role])
        parsed[role], expected = native.manifest(raw,role)
        if set(sources[role]) != set(expected): raise ValueError('joint_dataset_exact_inventory')
        for name, original in expected.items():
            binding = sources[role][name]
            # Input JSON may be valid noncanonical UTF8. Its actual byte identity
            # is in the source row; canonicalized metadata is not its original.
            if name != main and (binding['raw_sha256'] != original['sha256']
                    or original['bytes'] is not None and binding['raw_bytes'] != original['bytes']):
                raise ValueError('joint_dataset_original_binding')
            if name.endswith('.npy') and binding['descriptor'] != parsed[role]['arrays'][name[:-4]]:
                raise ValueError('joint_dataset_descriptor_binding')
            total += binding['raw_bytes']
    if total > native.MAX_BYTES: raise ValueError('joint_dataset_total_bytes')
    dev, sealed = parsed['development'], parsed['sealed']
    if sealed['payload']['plan_sha256'] != dev['development']['plan_sha256']:
        raise ValueError('joint_dataset_plan_binding')
    seal = dev['sealed_manifest']; native._keys(seal, ('schema','gravity','magnetic'))
    if seal['schema'] != 'joint-survey-sealed-manifest-1': raise ValueError('joint_dataset_sealed_schema')
    for m in ('gravity','magnetic'):
        declaration = seal[m]
        native._keys(declaration,('count','noise_kind','observations_file_sha256','noise_file_sha256','rows_sha256'))
        rows, observed, noise = (sealed['arrays'][m+'_'+name] for name in ('rows','observed','noise'))
        if (type(declaration['count']) is not int or rows['shape'] != [declaration['count']]
                or observed['shape'] != rows['shape'] or declaration['rows_sha256'] != rows['data_sha256']
                or declaration['observations_file_sha256'] != observed['file_sha256']
                or declaration['noise_file_sha256'] != noise['file_sha256']
                or declaration['noise_kind'] not in ('diagonal_sd','full_covariance')
                or noise['shape'] != ([declaration['count']] if declaration['noise_kind']=='diagonal_sd' else [declaration['count']]*2)):
            raise ValueError('joint_dataset_sealed_binding')
    return sum(dev['arrays'][m+'_receivers']['shape'][0] for m in ('gravity','magnetic'))

def validate_dataset(payload, dataset):
    native._keys(payload,('schema','dataset_id','version','owner_id','project_id','raw_asset_id',
        'parent_raw_sha256','parser_version','modality','dimensions','manifests','members',
        'qc_verdict','scientific_values_decoded','scientific_accepted'))
    if (payload['schema'] != SCHEMA or payload['dataset_id'] != dataset.id or type(payload['version']) is not int
            or payload['version'] != dataset.version or payload['owner_id'] != str(dataset.owner_id)
            or payload['project_id'] != dataset.project_id or payload['raw_asset_id'] != dataset.raw_asset_id
            or payload['parent_raw_sha256'] != dataset.raw_sha256 or payload['parser_version'] != native.PARSER
            or dataset.parser_version != native.PARSER or payload['modality'] != native.MODALITY or dataset.modality != native.MODALITY
            or payload['scientific_values_decoded'] is not False or payload['scientific_accepted'] is not False
            or payload['qc_verdict'] != 'structural_native_members_only'
            or payload['dimensions'] != {'source_observations':dataset.row_count}
            or close_manifests(payload) != dataset.row_count):
        raise ValueError('joint_dataset_identity')
    seen = set()
    for members in payload['members'].values():
        for binding in members.values():
            native._keys(binding,('asset_id','source_id','source_version','raw_sha256','raw_bytes',
                'rights_decision','private_storage_permission','descriptor'))
            if binding['asset_id'] in seen: raise ValueError('joint_dataset_duplicate_asset')
            seen.add(binding['asset_id'])
    primary = payload['members']['development']['request.json']
    if primary['asset_id'] != dataset.raw_asset_id or primary['raw_sha256'] != dataset.raw_sha256:
        raise ValueError('joint_dataset_primary_binding')
