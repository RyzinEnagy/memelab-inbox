"""Telemetry probe for evidently at the pin. Run under `unshare -n` plus strace so nothing can leave.

mode core: import, drift report, snapshot save, local file Workspace add_run (default library use).
mode ui:   build the local UI service app and call GET /api/projects through litestar's TestClient
           (the UI service is where TelemetryComponent sends events).
Prints which telemetry modules were imported. Connect attempts are read from the strace file by runwrap.py.
"""
import os
import sys
import tempfile
import time
from datetime import datetime

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402

mode = sys.argv[1]
work = tempfile.mkdtemp(prefix="ev_probe_")
print("mode", mode, "DO_NOT_TRACK" in os.environ, "XDG_CONFIG_HOME", os.environ.get("XDG_CONFIG_HOME"))
df = C.load()
tr = df[df.split == "train"][C.FEATURES]
ho = df[df.split == "holdout"][C.FEATURES]
if mode == "core":
    from evidently import Report
    from evidently.presets import DataDriftPreset
    from evidently.ui.workspace import Workspace
    snap = Report([DataDriftPreset()]).run(ho, tr, timestamp=datetime(2026, 10, 24))
    snap.save_json(os.path.join(work, "snap.json"))
    ws = Workspace.create(os.path.join(work, "ws"))
    proj = ws.create_project("probe")
    ws.add_run(proj.id, snap)
    print("workspace runs", len(ws.list_runs(proj.id)) if hasattr(ws, "list_runs") else "n/a")
elif mode == "ui":
    from litestar.testing import TestClient
    from evidently.ui.service.app import create_app, get_config
    cfg = get_config(workspace=os.path.join(work, "ws"))
    app = create_app(cfg)
    with TestClient(app) as client:
        r = client.get("/api/projects")
        print("GET /api/projects", r.status_code, r.text[:80])
        r = client.get("/api/version")
        print("GET /api/version", r.status_code, r.text[:80])
    time.sleep(3)  # give a telemetry daemon or thread time to try
print("evidently.telemetry imported:", "evidently.telemetry" in sys.modules)
print("iterative_telemetry imported:", "iterative_telemetry" in sys.modules)
cfgdir = os.environ.get("XDG_CONFIG_HOME")
if cfgdir:
    found = []
    for root, _, files in os.walk(cfgdir):
        for f in files:
            found.append(os.path.relpath(os.path.join(root, f), cfgdir))
    print("files written under XDG_CONFIG_HOME:", sorted(found))
