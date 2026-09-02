"""
Park-and-resume handling for tasks waiting on human approval.

When the brain calls approval__request_approval during a task, the queue parks
the task: it moves to Pending_Approval/<domain>/ and we write a sidecar JSON
capturing the approval request_id and the brain's summary at park time.

Periodically the queue calls find_resumable() which polls the Approval MCP for
each parked task's request_id. If a decision has been recorded
(approved/rejected), prepare_resume() moves the task back to Needs_Action/ with
a resume marker appended, and the brain picks it up on the next tick.

Storage:
    Pending_Approval/<domain>/<task>.md         — the original task file
    Pending_Approval/<domain>/<task>.context.json — sidecar with state
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from production_utils import MCPClient, get_structured_logger
from agent_config import get_vault_path

from llm_brain import config


logger = get_structured_logger("llm_brain.approval_handler")


class ApprovalHandler:
    def __init__(self):
        self.vault_path = Path(get_vault_path())
        self.pending_dir = self.vault_path / "Pending_Approval"
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.approval_client = MCPClient(
            config.MCP_BASE_URLS["approval"], "approval", timeout=10
        )

    def park(
        self,
        claimed_path: Path,
        summary: str,
        approval_info: Dict[str, Any],
        domain: str = "",
    ) -> Optional[Path]:
        """
        Move a task from In_Progress to Pending_Approval and write a sidecar.

        Returns the new path of the parked task, or None if the move failed.
        """
        dest_dir = self.pending_dir / domain if domain else self.pending_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        parked_path = dest_dir / claimed_path.name
        if parked_path.exists():
            stem = claimed_path.stem
            parked_path = dest_dir / f"{stem}_{int(datetime.now().timestamp())}.md"

        try:
            os.rename(str(claimed_path), str(parked_path))
        except OSError as e:
            logger.error(f"Park failed: {claimed_path.name} - {e}")
            return None

        sidecar = parked_path.with_suffix(".context.json")
        sidecar.write_text(
            json.dumps(
                {
                    "parked_at": datetime.now().isoformat(),
                    "task_name": claimed_path.name,
                    "domain": domain,
                    "summary": summary,
                    "approval": approval_info,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(
            f"Parked: {parked_path.name} (request_id={approval_info.get('request_id')})"
        )
        return parked_path

    def find_resumable(self) -> List[Dict[str, Any]]:
        """
        Scan Pending_Approval/ for parked tasks. For each, poll the Approval MCP
        for status. Return entries that are no longer pending.

        Returns a list of dicts: {task_path, sidecar_path, status, domain, sidecar_data}.
        """
        if not self.pending_dir.exists():
            return []

        resumable: List[Dict[str, Any]] = []
        for sidecar in self.pending_dir.rglob("*.context.json"):
            try:
                data = json.loads(sidecar.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Skipping malformed sidecar {sidecar.name}: {e}")
                continue

            request_id = data.get("approval", {}).get("request_id")
            if not request_id:
                continue

            status = self._check_approval(request_id)
            if status not in {"approved", "rejected"}:
                continue

            task_path = sidecar.with_suffix("")
            task_path = task_path.with_suffix(".md")
            if not task_path.exists():
                logger.warning(f"Sidecar without task file: {sidecar.name}")
                continue

            resumable.append(
                {
                    "task_path": task_path,
                    "sidecar_path": sidecar,
                    "status": status,
                    "domain": data.get("domain", ""),
                    "sidecar_data": data,
                }
            )
        return resumable

    def prepare_resume(self, entry: Dict[str, Any]) -> Optional[Path]:
        """
        Move a parked task back to Needs_Action/<domain>/ with a resume marker
        appended. Delete the sidecar. Returns the new Needs_Action path.
        """
        task_path: Path = entry["task_path"]
        sidecar_path: Path = entry["sidecar_path"]
        status: str = entry["status"]
        domain: str = entry["domain"]
        info = entry["sidecar_data"].get("approval", {})

        marker = (
            f"\n\n---\n## Resume Marker\n"
            f"- Approval status: **{status.upper()}**\n"
            f"- Original request_id: `{info.get('request_id')}`\n"
            f"- Action requested: {info.get('action')}\n"
            f"- Parked at: {entry['sidecar_data'].get('parked_at')}\n\n"
            f"The brain previously requested approval for this action. The human "
            f"has now {'APPROVED' if status == 'approved' else 'REJECTED'} the request. "
            f"{'Proceed with the action.' if status == 'approved' else 'Do not execute the action; close the task as rejected.'}\n"
        )

        try:
            content = task_path.read_text(encoding="utf-8")
            task_path.write_text(content + marker, encoding="utf-8")
        except OSError as e:
            logger.error(f"Failed to append resume marker: {e}")
            return None

        dest_dir = self.needs_action_dir / domain if domain else self.needs_action_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / task_path.name

        try:
            os.rename(str(task_path), str(dest))
            sidecar_path.unlink(missing_ok=True)
            logger.info(f"Resumed: {dest.name} (status={status})")
            return dest
        except OSError as e:
            logger.error(f"Resume move failed: {task_path.name} - {e}")
            return None

    def _check_approval(self, request_id: str) -> str:
        """Query the Approval MCP. Returns 'approved' | 'rejected' | 'pending' | 'error'."""
        result = self.approval_client.post("check_approval", data={"request_id": request_id})
        if not isinstance(result, dict):
            return "error"
        return result.get("status", "error")
