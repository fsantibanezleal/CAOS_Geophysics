"""One-time v2 metadata migration: record actual snapped Deepwave receiver nodes.

No model, measurement, wavefield or inversion result is changed. The solver has
always truncated receiver indices to integer grid nodes. Update the JSON metadata
and its catalogue checksum to match that existing numerical acquisition.
"""
import hashlib
import json
from pathlib import Path
import torch

root = Path(__file__).resolve().parents[1] / 'data/derived/v2'
catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8'))
count = 0
for case in catalog['cases']:
    if case['family'] != 'seismic':
        continue
    for variant in case['variants']:
        path = root / variant['path']
        data = json.loads(path.read_text(encoding='utf-8'))
        receivers = data['parameters']['receivers']
        data['receivers'] = (torch.linspace(3, 60, receivers).long() * 25).tolist()
        encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        path.write_bytes(encoded)
        variant.update(sha256=hashlib.sha256(encoded).hexdigest(), bytes=len(encoded))
        count += 1
(root / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(f'Corrected receiver metadata for {count} seismic artifacts; solver arrays unchanged.')
