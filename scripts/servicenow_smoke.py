"""Live smoke test for the ServiceNow client (run by hand, never in CI).

Creates one change request on your personal developer instance, adds a work note and
attaches a small text file. Credentials come from .env; nothing is printed except
the change number and ids.

    python scripts/servicenow_smoke.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from dotenv import load_dotenv

from dq_tools.config import ServiceNowSettings
from dq_tools.servicenow import ServiceNowClient


def main() -> None:
    load_dotenv()
    client = ServiceNowClient.from_settings(ServiceNowSettings.from_env())

    change = client.create_change_request(
        "DQ Gate smoke test", "Created by scripts/servicenow_smoke.py (synthetic, safe to delete)."
    )
    sys_id = change["sys_id"]
    print(f"Created {change['number']} (sys_id={sys_id})")

    client.add_work_note(sys_id, "Smoke test work note.")
    print("Added work note")

    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence.txt"
        evidence.write_text("synthetic evidence file\n")
        attachment = client.attach_file(sys_id, evidence)
    print(f"Attached {attachment['file_name']} (sys_id={attachment['sys_id']})")


if __name__ == "__main__":
    main()
