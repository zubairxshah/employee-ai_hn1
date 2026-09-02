"""
LLMBrain — agentic loop with provider switching.

Reads a task markdown file, lets the model reason + call MCP tools, returns a
summary. The loop is bounded by config.MAX_TURNS_PER_TASK to prevent runaway
costs.

Provider is selected by config.PROVIDER ("gemini" | "openrouter").
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from production_utils import get_structured_logger
from agent_config import AGENT_ROLE

from llm_brain import config
from llm_brain.tool_definitions import build_tools, build_openai_tools
from llm_brain.tool_executor import ToolExecutor
from llm_brain.system_prompt import build_system_prompt


logger = get_structured_logger("llm_brain.brain")


class LLMBrain:
    def __init__(self):
        config.validate()
        self._executor = ToolExecutor()
        self._system_prompt = build_system_prompt()

        if config.PROVIDER == "gemini":
            self._init_gemini()
        elif config.PROVIDER == "openrouter":
            self._init_openrouter()
        else:
            raise RuntimeError(f"Unsupported provider: {config.PROVIDER}")

    # ==================== Gemini ====================

    def _init_gemini(self) -> None:
        from google import genai
        from google.genai import types

        self._genai_types = types
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        self._gen_config = types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            tools=build_tools(),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2,
        )

    def _process_gemini(self, task_path: Path) -> str:
        types = self._genai_types
        chat = self._client.chats.create(model=config.MODEL_NAME, config=self._gen_config)
        opening = (
            f"A new task file is at `{task_path}`. Read it, decide what to do, "
            "then call the tools needed to complete it. Summarize the outcome when done."
        )
        response = chat.send_message(opening)

        for turn in range(config.MAX_TURNS_PER_TASK):
            function_responses: List = []
            candidate = response.candidates[0] if response.candidates else None
            parts = candidate.content.parts if candidate and candidate.content else []
            for part in parts or []:
                fc = getattr(part, "function_call", None)
                if not fc or not fc.name:
                    continue
                args = dict(fc.args) if fc.args else {}
                result = self._executor.execute(fc.name, args)
                function_responses.append(
                    types.Part.from_function_response(name=fc.name, response=result)
                )

            if not function_responses:
                text = "\n".join(p.text for p in parts or [] if getattr(p, "text", None))
                logger.info(f"Task complete after {turn + 1} turn(s): {text[:120]}")
                return text

            response = chat.send_message(function_responses)

        text = ""
        if response.candidates and response.candidates[0].content:
            text = "\n".join(
                p.text for p in (response.candidates[0].content.parts or [])
                if getattr(p, "text", None)
            )
        logger.warning(f"Gemini task hit MAX_TURNS_PER_TASK={config.MAX_TURNS_PER_TASK}.")
        return f"[truncated after {config.MAX_TURNS_PER_TASK} turns] {text}"

    # ==================== OpenRouter (OpenAI-compatible) ====================

    def _init_openrouter(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            base_url=config.OPENROUTER_BASE_URL,
            api_key=config.OPENROUTER_API_KEY,
        )
        self._openai_tools = build_openai_tools()

    def _process_openrouter(self, task_path: Path) -> str:
        opening = (
            f"A new task file is at `{task_path}`. Read it, decide what to do, "
            "then call the tools needed to complete it. Summarize the outcome when done."
        )
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": opening},
        ]

        for turn in range(config.MAX_TURNS_PER_TASK):
            response = self._client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                tools=self._openai_tools,
                tool_choice="auto",
                temperature=0.2,
            )
            choice = response.choices[0]
            msg = choice.message
            # Always record the assistant turn so subsequent tool messages have context
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in (msg.tool_calls or [])
                ] if msg.tool_calls else None,
            })

            if not msg.tool_calls:
                text = msg.content or ""
                logger.info(f"Task complete after {turn + 1} turn(s): {text[:120]}")
                return text

            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                result = self._executor.execute(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        logger.warning(f"OpenRouter task hit MAX_TURNS_PER_TASK={config.MAX_TURNS_PER_TASK}.")
        return f"[truncated after {config.MAX_TURNS_PER_TASK} turns]"

    # ==================== Dispatch ====================

    def process_task(self, task_path: Path) -> str:
        """Run the agentic loop on a single task file. Returns the final summary text."""
        task_path = Path(task_path)
        logger.info(
            f"Processing task: {task_path.name} "
            f"(provider={config.PROVIDER}, role={AGENT_ROLE}, model={config.MODEL_NAME})"
        )
        self._executor.reset_task_state()

        if config.PROVIDER == "openrouter":
            return self._process_openrouter(task_path)
        return self._process_gemini(task_path)
