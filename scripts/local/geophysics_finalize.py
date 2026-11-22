"""Write the product readiness receipt for an already generated candidate stage."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: geophysics_finalize.py <candidate-stage>")
    root = Path(__file__).resolve().parents[2]
    stage = Path(sys.argv[1]).resolve()
    if stage == root or stage.is_relative_to(root):
        raise SystemExit("candidate stage must be outside the repository")
    checker = root / "scripts/check_readiness.py"
    spec = importlib.util.spec_from_file_location("geophysics_readiness", checker)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load product readiness checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ready = module.document(stage)
    if ready.get("state") != "available":
        raise SystemExit(f"candidate catalog is incomplete: {ready.get('state')}")
    target = stage / "data/derived/readiness.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ready, separators=(",", ":"), ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"readiness finalized: {ready['counts']['cases']} cases, "
          f"{ready['counts']['variants']} variants, {ready['artifacts']['present']} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
