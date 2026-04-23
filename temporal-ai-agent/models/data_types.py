from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Literal, Optional, Union

from models.tool_definitions import AgentGoal


@dataclass
class AgentGoalWorkflowParams:
    conversation_summary: Optional[str] = None
    prompt_queue: Optional[Deque[str]] = None


@dataclass
class CombinedInput:
    tool_params: AgentGoalWorkflowParams
    agent_goal: AgentGoal


Message = Dict[str, Union[str, Dict[str, Any]]]
ConversationHistory = Dict[str, List[Message]]
NextStep = Literal["confirm", "question", "pick-new-goal", "done"]


@dataclass
class ToolPromptInput:
    prompt: str
    context_instructions: str
    conversation_history: Optional[ConversationHistory] = None


@dataclass
class ValidationInput:
    prompt: str
    conversation_history: ConversationHistory
    agent_goal: AgentGoal


@dataclass
class ValidationResult:
    validationResult: bool
    validationFailedReason: Optional[Union[dict, str]] = None

    def __post_init__(self):
        if self.validationFailedReason is None:
            self.validationFailedReason = {}
        elif isinstance(self.validationFailedReason, str):
            import json as _json
            try:
                self.validationFailedReason = _json.loads(self.validationFailedReason)
            except (_json.JSONDecodeError, ValueError):
                self.validationFailedReason = {"response": self.validationFailedReason}


@dataclass
class EnvLookupInput:
    show_confirm_env_var_name: str
    show_confirm_default: bool


@dataclass
class EnvLookupOutput:
    show_confirm: bool
    multi_goal_mode: bool
