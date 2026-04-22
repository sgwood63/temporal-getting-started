import os
from typing import Annotated, Any, Dict, Literal, Optional, Type, TypeVar

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import PydanticToolsParser
from langchain_litellm import ChatLiteLLM
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing_extensions import TypedDict

T = TypeVar("T", bound=BaseModel)


class ToolPlannerOutput(BaseModel):
    response: str
    next: Literal["question", "confirm", "pick-new-goal", "done"]
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None


class ValidationOutput(BaseModel):
    validationResult: bool
    validationFailedReason: Optional[Dict[str, Any]] = None


class PlannerState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    result: Optional[ToolPlannerOutput]


class ValidationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    result: Optional[ValidationOutput]


def _build_llm() -> ChatLiteLLM:
    return ChatLiteLLM(
        model=os.environ.get("LLM_MODEL", "openai/gpt-4"),
        api_key=os.environ.get("LLM_KEY"),
        base_url=os.environ.get("LLM_BASE_URL") or None,
    )


def _structured_output(llm: ChatLiteLLM, schema: Type[T]):
    bound = llm.bind_tools([schema], tool_choice="required")
    parser = PydanticToolsParser(tools=[schema], first_tool_only=True)
    return bound | parser


def _build_planner_graph():
    llm = _build_llm()
    structured_llm = _structured_output(llm, ToolPlannerOutput)

    def planner_node(state: PlannerState) -> dict:
        return {"result": structured_llm.invoke(state["messages"])}

    g = StateGraph(PlannerState)
    g.add_node("planner", planner_node)
    g.set_entry_point("planner")
    g.add_edge("planner", END)
    return g.compile()


def _build_validation_graph():
    llm = _build_llm()
    structured_llm = _structured_output(llm, ValidationOutput)

    def validation_node(state: ValidationState) -> dict:
        return {"result": structured_llm.invoke(state["messages"])}  # type: ignore[arg-type]

    g = StateGraph(ValidationState)
    g.add_node("validator", validation_node)
    g.set_entry_point("validator")
    g.add_edge("validator", END)
    return g.compile()


_PLANNER_GRAPH = None
_VALIDATION_GRAPH = None


def get_planner_graph():
    global _PLANNER_GRAPH
    if _PLANNER_GRAPH is None:
        _PLANNER_GRAPH = _build_planner_graph()
    return _PLANNER_GRAPH


def get_validation_graph():
    global _VALIDATION_GRAPH
    if _VALIDATION_GRAPH is None:
        _VALIDATION_GRAPH = _build_validation_graph()
    return _VALIDATION_GRAPH
