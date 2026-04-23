from typing import List, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from models.data_types import ConversationHistory


def convert_history_to_messages(
    history: ConversationHistory,
) -> Tuple[List[BaseMessage], str]:
    """Convert Temporal ConversationHistory to LangChain message objects.

    Returns (messages, summary_text) where summary_text aggregates any
    "conversation_summary" entries for injection into the system prompt.
    """
    messages: List[BaseMessage] = []
    summary_parts: List[str] = []

    for entry in history.get("messages", []):
        actor = entry.get("actor", "")
        response = entry.get("response", "")

        if actor == "conversation_summary":
            summary_parts.append(str(response))
        elif actor == "user":
            messages.append(HumanMessage(content=str(response)))
        elif actor == "agent":
            content = (
                response.get("response", str(response))
                if isinstance(response, dict)
                else str(response)
            )
            messages.append(AIMessage(content=content))
        elif actor == "tool_result":
            messages.append(HumanMessage(content=f"[Tool result] {str(response)}"))
        elif actor == "user_confirmed_tool_run":
            messages.append(HumanMessage(content=f"[Confirmed tool run] {str(response)}"))
        else:
            messages.append(HumanMessage(content=f"[{actor}] {str(response)}"))

    return messages, "\n".join(summary_parts)
