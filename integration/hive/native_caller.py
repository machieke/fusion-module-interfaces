"""Test transport around the unmodified native ASGI app, in a killable process.

No fake Hive, Supervisor, actor, dispatch, PeTTa or model invocation. TestClient
avoids opening a development credential policy to the network.
"""
import contextlib
import json
import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from hive.core.app import create_app
from hive.core.config import load_settings
from hive.core import exclusive


def main():
    data = Path(sys.argv[1])
    # stdout is this test driver's framing; native diagnostics go to stderr.
    with contextlib.redirect_stdout(sys.stderr):
        settings = load_settings(data_dir=data, admin_password="generated-local-test-password",
                                 petta_path=os.environ["PETTA_PATH"], offline=True)
        exclusive.acquire_or_exit(settings.data_dir, exclusive.HELD)
        app = create_app(settings, reconcile_seconds=0)
        exclusive.startup_recovery(exclusive.HELD, app.state.hive)
    with contextlib.redirect_stdout(sys.stderr), TestClient(app) as client:
        login = client.post("/api/auth/login", json={"password": "generated-local-test-password"})
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["token"]
        sys.__stdout__.write(json.dumps({"ready": True}) + "\n")
        sys.__stdout__.flush()
        for line in sys.stdin:
            command = json.loads(line)
            response = client.request(command["method"], command["path"], json=command.get("body"))
            sys.__stdout__.write(json.dumps({"code": response.status_code, "body": response.json()}) + "\n")
            sys.__stdout__.flush()


if __name__ == "__main__":
    main()
