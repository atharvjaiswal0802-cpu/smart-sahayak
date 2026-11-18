"""Embed backend/app/seed.json into frontend/index.html so the offline demo mode matches the server seed.
Run after editing seed.json:  python scripts/sync_demo_seed.py"""
import json, pathlib
root = pathlib.Path(__file__).resolve().parents[1]
seed = (root / "backend/app/seed.json").read_text()
tpl = (root / "frontend/index.template.html").read_text()
(root / "frontend/index.html").write_text(tpl.replace("__SEED__", json.dumps(json.loads(seed), separators=(",", ":"))))
print("frontend/index.html written")
