"""Independent complete local archive replay, with no optimizer invocation."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data-pipeline'))
from gravity_workflow_io import main  # noqa: E402

if __name__ == '__main__': raise SystemExit(main(['verify',*sys.argv[1:]]))
