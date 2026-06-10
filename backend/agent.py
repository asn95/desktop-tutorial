"""
C3MR Workflow Agent — Gemini-powered autonomous agent for managing
field collection operations via natural language.

Usage:
    from backend.agent import run_agent
    response = await run_agent("What's our collection rate this week?")
"""
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from .agent_tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL = os.environ.get("AGENT_MODEL", "gemini-3.5-flash")

SYSTEM_PROMPT = """You are the C3MR Operations Agent — an AI assistant for managing debt collection field operations.

You help managers by:
- Querying real-time dashboard statistics and analytics
- Finding and filtering collection targets by status, area, officer, or amount
- Identifying overdue targets that need follow-up
- Flagging problematic targets with many officer comments
- Assigning targets to officers (individually or auto-distribute)
- Evaluating officer performance and workload balance
- Generating daily operational reports

RULES:
- Always use the available tools to get real data. Never make up numbers.
- When assigning targets, always confirm the action and show what was done.
- Format currency as Indonesian Rupiah (Rp) with thousand separators.
- Keep responses concise but informative.
- If the user asks something outside your capabilities, say so clearly.
- For destructive actions (bulk assign, reassign), describe what you'll do first, then execute.
- Reply in the same language the user writes in (Indonesian or English).

RESPONSE FORMAT:
- PLAIN TEXT ONLY — never use markdown. No **bold**, no _italic_, no `backticks`, no # headers. They render as literal symbols in Telegram.
- Use the bullet character • and line breaks for readability.
- Keep responses under 4000 characters (Telegram limit).
"""

MAX_TOOL_ROUNDS = 10


def _to_function_declarations(tool_definitions: list[dict]) -> list[dict]:
    """Convert Anthropic-style tool definitions to Gemini function declarations."""
    declarations = []
    for tool in tool_definitions:
        decl = {"name": tool["name"], "description": tool["description"]}
        schema = tool.get("input_schema") or {}
        if schema.get("properties"):
            decl["parameters"] = schema
        declarations.append(decl)
    return declarations


GEMINI_TOOLS = [types.Tool(function_declarations=_to_function_declarations(TOOL_DEFINITIONS))]


async def run_agent(user_message: str) -> str:
    """Run the agent with a user message and return the final text response."""
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_message)])]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=GEMINI_TOOLS,
        max_output_tokens=2048,
    )

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0] if response.candidates else None
        parts = (candidate.content.parts or []) if candidate and candidate.content else []
        function_calls = [p.function_call for p in parts if p.function_call]

        # No tool calls — return the final text
        if not function_calls:
            return (response.text or "").strip() or "Done."

        # Append the model's turn, execute each tool, send results back
        contents.append(candidate.content)
        result_parts = []
        for fc in function_calls:
            fn = TOOL_FUNCTIONS.get(fc.name)
            if fn:
                try:
                    result = fn(**dict(fc.args or {}))
                    payload = {"result": json.loads(json.dumps(result, default=str))}
                except Exception as e:
                    payload = {"error": str(e)}
            else:
                payload = {"error": f"Unknown tool: {fc.name}"}
            result_parts.append(
                types.Part.from_function_response(name=fc.name, response=payload)
            )
        contents.append(types.Content(role="user", parts=result_parts))

    return "I reached the maximum number of steps. Please try a simpler question."
