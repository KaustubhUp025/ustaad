"""set_reply_language as the Live agent calls it: the instruction reaches the model once, at connect, so a switch he
asks for travels through this tool's result and the session state the other tools and notes read (phone test, Oct 18)."""

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from agent.media_tools import MediaDesk
from models.worker import LANGS


def language_tools(desk: MediaDesk) -> list[FunctionTool]:
    def set_reply_language(tool_context: ToolContext, lang: str) -> dict:
        """Switches the reply language, only when he asks you to speak another language. `lang`: hi, te, ta, bn or
        en. Not when he just uses a few words of another language, and not because a card, note or memory is in
        another language. SET: from now on reply in `language`. UNSUPPORTED: tell him which languages you speak."""
        if lang not in LANGS:
            return {"status": "UNSUPPORTED", "supported": [name for _, name in LANGS.values()]}
        name = LANGS[lang][1]
        tool_context.state["lang"], tool_context.state["language_name"], desk.lang = lang, name, lang
        return {"status": "SET", "language": name}

    tool = FunctionTool(set_reply_language)
    tool.behavior = types.Behavior.BLOCKING
    return [tool]
