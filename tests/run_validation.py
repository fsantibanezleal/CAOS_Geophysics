"""Run expensive numerical tests locally and persist machine-readable evidence."""
from pathlib import Path
import datetime
import json
import subprocess
import sys
import torch

root=Path(__file__).resolve().parents[1]
out=root/'docs/validation';out.mkdir(parents=True,exist_ok=True)
result=subprocess.run([sys.executable,'-m','pytest','tests/test_rebuild.py','--junitxml='+str(out/'numerical.xml')],cwd=root)
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=result.returncode,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
(out/'environment.json').write_text(json.dumps(record,indent=2))
raise SystemExit(result.returncode)
