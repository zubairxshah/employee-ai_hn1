"""
Tool executor — bridges Gemini function calls to MCP HTTP endpoints.

Each tool name `<service>__<action>` is dispatched to MCP_BASE_URLS[service] /<action>.
Role gating (can_execute_action) runs before any HTTP call.
"""

from typing import Any, Dict

from production_utils import MCPClient, get_structured_logger
from agent_config import can_execute_action, AGENT_ROLE

from llm_brain import config
from llm_brain.tool_definitions import tool_names


logger = get_structured_logger("llm_brain.tool_executor")

# Set of declared tool names — used to reject hallucinated function calls.
# Gemini's API is permissive; it will happily emit function_calls for tools
# that were not declared if the model sees the name elsewhere in the context.
_DECLARED_TOOLS = set(tool_names())


# Tools whose MCP endpoints are GET (most MCP endpoints are POST).
# Verified against mcp_servers/*_mcp.py @app.route definitions.
_GET_ACTIONS: set = {
    "approval__list_pending_approvals",
    "linkedin__get_messages",
    "facebook__get_engagement_summary",
    "twitter__get_engagement_summary",
}


class ToolExecutor:
    """Dispatches Gemini tool calls to MCP servers."""

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {
            service: MCPClient(url, service, timeout=30)
            for service, url in config.MCP_BASE_URLS.items()
        }
        # Per-task state. Reset by reset_task_state() before each new task.
        # When the brain calls approval__request_approval, we capture it here
        # so the task_queue can park the task instead of marking it done.
        self.pending_approval: Dict[str, Any] | None = None

    def reset_task_state(self) -> None:
        """Clear per-task state. Called at the start of each task."""
        self.pending_approval = None

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call. Returns a dict the model receives as the function response."""
        if tool_name not in _DECLARED_TOOLS:
            logger.warning(f"Hallucinated tool call rejected: {tool_name}")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not available. You may have invented this name.",
                "hint": "Only call tools that were declared in your tool list.",
            }

        if "__" not in tool_name:
            return {"success": False, "error": f"Malformed tool name: {tool_name}"}

        service, action = tool_name.split("__", 1)

        if not can_execute_action(action):
            logger.warning(
                f"Role={AGENT_ROLE} blocked from executing {tool_name}. "
                "Use the draft equivalent instead."
            )
            return {
                "success": False,
                "error": f"Action '{action}' is not permitted for role={AGENT_ROLE}",
                "hint": f"On cloud role, use the *_draft variant of this tool.",
            }

        client = self._clients.get(service)
        if client is None:
            return {"success": False, "error": f"Unknown MCP service: {service}"}

        logger.info(f"Executing tool {tool_name} args={list(args.keys())}")
        try:
            if tool_name in _GET_ACTIONS:
                result = client.get(action, params=args)
            else:
                result = client.post(action, data=args)
        except Exception as e:
            logger.error(f"Tool {tool_name} raised: {e}")
            return {"success": False, "error": f"Tool execution error: {e}"}

        # Capture approval requests so the queue can park the task.
        if tool_name == "approval__request_approval" and result.get("success"):
            self.pending_approval = {
                "request_id": result.get("request_id"),
                "action": args.get("action"),
                "amount": args.get("amount"),
                "recipient": args.get("recipient"),
                "reason": args.get("reason"),
            }
            logger.info(f"Approval requested: request_id={self.pending_approval['request_id']}")

        return result
