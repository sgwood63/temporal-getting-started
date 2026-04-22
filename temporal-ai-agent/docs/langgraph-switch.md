# Migrate Agent Logic to LangGraph (keep Temporal)

> **Note:** This is the implementation plan for the `langgraph-switch` branch. The plan was written before implementation; see the [Actual Implementation](#actual-implementation) section for what was built and why it diverged slightly from the original design.

## Context

The project uses `temporal-ai-agent`, a community Temporal workflow that manually builds system prompts, calls LiteLLM, and parses a custom `{response, next, tool, args}` JSON contract. The goal is to replace this hand-rolled agent logic with **LangGraph** — the most popular Python agent framework (~10M downloads/week, by the LangChain team) — while keeping Temporal as the durable workflow engine for signals, retries, and state.

## Framework Choice: LangGraph

LangGraph models agent logic as a state graph. For this project we use a **single-step graph** (one LLM call per Temporal activity invocation), which preserves Temporal's control over the outer loop. This is critical: a full ReAct loop inside LangGraph would bypass Temporal's retry/audit machinery.

## Architecture

```
Temporal workflow (outer loop — unchanged)
  └─ calls agent_toolPlanner activity
        └─ LangGraph graph.invoke() — ONE LLM call
              └─ ChatLiteLLM.with_structured_output(ToolPlannerOutput)
        └─ output.model_dump() → {next, tool, args, response}  ← same dict contract
```

Temporal never changes. LangGraph replaces the inside of `agent_toolPlanner` and `agent_validatePrompt`.

## Files Changed

| File | Change |
|------|--------|
| `activities/tool_activities.py` | Replace `agent_toolPlanner` and `agent_validatePrompt` bodies; remove `litellm.completion`, `sanitize_json_response`, `parse_json_response` |
| `activities/langgraph_agent.py` | **New file** — LangGraph graphs, Pydantic output models, lazy singletons |
| `pyproject.toml` | Add `langgraph`, `langchain-core`, `langchain-litellm` |
| `tests/test_tool_activities.py` | Update mocks from `litellm.completion` to `get_planner_graph` / `get_validation_graph` |

Tools in `tools/`, goals in `goals/`, and the workflow in `workflows/` are **untouched**.

## Implementation Steps

### Step 1 — Add dependencies (`pyproject.toml`)
```toml
"langgraph>=0.2.0,<0.3",
"langchain-core>=0.3.0,<0.4",
"langchain-litellm>=0.1.0,<0.2",
```

### Step 2 — Create `activities/langgraph_agent.py`

**Pydantic output models** (replace manual JSON parsing):
```python
class ToolPlannerOutput(BaseModel):
    response: str
    next: Literal["question", "confirm", "pick-new-goal", "done"]
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None

class ValidationOutput(BaseModel):
    validationResult: bool
    validationFailedReason: Optional[Dict[str, Any]] = None
```

**State types:**
```python
class PlannerState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    result: Optional[ToolPlannerOutput]

class ValidationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    result: Optional[ValidationOutput]
```

**Single-step graphs** (compiled lazily, not inside activities):
```python
def _build_planner_graph():
    llm = ChatLiteLLM(model=os.environ["LLM_MODEL"], api_key=os.environ["LLM_KEY"])
    structured_llm = llm.with_structured_output(ToolPlannerOutput)

    def planner_node(state: PlannerState) -> dict:
        return {"result": structured_llm.invoke(state["messages"])}

    g = StateGraph(PlannerState)
    g.add_node("planner", planner_node)
    g.set_entry_point("planner")
    g.add_edge("planner", END)
    return g.compile()
```

**Lazy module-level singletons** (safe for Temporal determinism — graphs have no side effects at compile time):
```python
_PLANNER_GRAPH = None

def get_planner_graph():
    global _PLANNER_GRAPH
    if _PLANNER_GRAPH is None:
        _PLANNER_GRAPH = _build_planner_graph()
    return _PLANNER_GRAPH
```

### Step 3 — Update `activities/tool_activities.py`

Replace `agent_toolPlanner` body:
```python
@activity.defn
async def agent_toolPlanner(self, input: ToolPromptInput) -> dict:
    from activities.langgraph_agent import ToolPlannerOutput, get_planner_graph

    graph = get_planner_graph()
    state = await asyncio.to_thread(
        graph.invoke,
        {
            "messages": [
                SystemMessage(content=input.context_instructions + ". The current date is " + datetime.now().strftime("%B %d, %Y")),
                HumanMessage(content=input.prompt),
            ],
            "result": None,
        },
    )
    output: ToolPlannerOutput = state["result"]
    return output.model_dump()
```

Replace `agent_validatePrompt` — now uses its own dedicated validation graph instead of calling `agent_toolPlanner`:
```python
@activity.defn
async def agent_validatePrompt(self, validation_input: ValidationInput) -> ValidationResult:
    from activities.langgraph_agent import ValidationOutput, get_validation_graph

    graph = get_validation_graph()
    state = await asyncio.to_thread(graph.invoke, {
        "messages": [SystemMessage(content=context_instructions), HumanMessage(content=validation_prompt)],
        "result": None,
    })
    output: ValidationOutput = state["result"]
    return ValidationResult(
        validationResult=output.validationResult,
        validationFailedReason=output.validationFailedReason or {},
    )
```

### Step 4 — Run tests and validate
```bash
cd temporal-ai-agent
uv run pytest
uv run scripts/run_worker.py          # Terminal 1
uv run uvicorn api.main:app --reload  # Terminal 2
cd frontend && npm run dev            # Terminal 3
```

Test the `goal_event_flight_invoice` goal end-to-end: FindEvents → SearchFlights → CreateInvoice.

## Key Constraints

- Graphs are compiled lazily on first use (not inside activities) — satisfies Temporal determinism requirement
- Tool functions in `tools/` are never registered with LangGraph — Temporal's `dynamic_tool_activity` executes them
- Activity method names (`agent_toolPlanner`, `agent_validatePrompt`) are unchanged — string references in `workflow_helpers.py` remain valid
- `langchain-litellm` preserves multi-provider support via `LLM_MODEL` env var (`openai/gpt-4o`, `anthropic/claude-...`, etc.)

## Actual Implementation

The plan originally proposed using `bind_tools` with sentinel tools (`DoneSignal`, `PickNewGoalSignal`) for native LangGraph function calling. After exploring the codebase, a `_structured_output()` helper using `bind_tools` + `PydanticToolsParser` was chosen instead for these reasons:

1. **System prompt preservation** — `generate_genai_prompt` builds a carefully tuned system prompt with decision logic, examples, and tool descriptions. The `bind_tools` approach would have required significant prompt rewrites to remove the existing JSON format instructions. Passing the Pydantic schema directly as a tool keeps the prompt intact and simply validates the output against it.

2. **Simpler output contract** — The existing `{next, tool, args, response}` dict structure maps directly to `ToolPlannerOutput`. No sentinel tools or output mapping functions needed.

3. **Dedicated validation graph** — `agent_validatePrompt` previously abused `agent_toolPlanner` by sending a prompt that asked for `{validationResult, validationFailedReason}` instead of the normal tool-planning schema. The new implementation gives validation its own `ValidationOutput` model and graph, eliminating this confusion.

4. **No changes to workflow or data models** — The `ToolPromptInput` dataclass and `agent_goal_workflow.py` required zero modifications since the dict contract is identical.

### Why `bind_tools` instead of `with_structured_output`

`with_structured_output()` was the initial implementation but caused a runtime error:

```
litellm.BadRequestError: OpenAIException - Invalid value: 'any'.
Supported values are: 'none', 'auto', and 'required'.
```

`with_structured_output` hardcodes `tool_choice="any"` internally (in `langchain_core`). `langchain-litellm` is supposed to convert `"any"` → `"required"` for OpenAI models, but only for models listed in its hardcoded `_OPENAI_MODELS` set — which does not include models specified with the `openai/` provider prefix (e.g. `openai/gpt-5.4-2026-03-05`).

The fix: a `_structured_output()` helper that calls `bind_tools([schema], tool_choice="required")` directly and pipes through `PydanticToolsParser`. This bypasses the broken conversion and works regardless of how the model is named:

```python
def _structured_output(llm: ChatLiteLLM, schema: Type[T]):
    bound = llm.bind_tools([schema], tool_choice="required")
    parser = PydanticToolsParser(tools=[schema], first_tool_only=True)
    return bound | parser
```
