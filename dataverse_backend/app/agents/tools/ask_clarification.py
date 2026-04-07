from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
from typing import Dict, Any, List, Optional


class AskClarificationTool(BaseTool):
    """Tool for asking user clarification questions."""

    def __init__(self):
        super().__init__()
        self.name = "ask_clarification"
        self.description = """Pause execution and ask user a question.
USE WHEN: Query is ambiguous, missing information, or needs user input."""
        self.input_schema = {
            "question": {
                "type": "string",
                "description": "The clarification question to ask the user"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of answer options for multiple choice",
                "default": None
            }
        }
        self.output_schema = {
            "description": "ClarificationRequest object to pause execution"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        question = params.get("question", "")
        options = params.get("options")

        if not question:
            return ToolResult(
                success=False,
                data={},
                error_message="No question provided for clarification",
                confidence=0.0
            )

        clarification_request = {
            "type": "clarification",
            "question": question,
            "options": options,
            "session_id": session.session_id
        }

        return ToolResult(
            success=True,
            data=clarification_request,
            display=None,  # This will be handled by frontend
            confidence=1.0
        )