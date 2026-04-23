# Elements
These are the main elements of this system. See [architecture decisions](./architecture-decisions.md) for information beind these choices.
In this document we will explain each element and their interactions, and then connect them all at the end.
<img src="./assets/Architecture_elements.png" width="50%" alt="Architecture Elements">

## Workflow 
This is a [Temporal Workflow](https://docs.temporal.io/workflows) - a durable straightforward description of the process to be executed. See [agent_goal_workflow.py](./workflows/agent_goal_workflow.py).
Temporal is used to make the process scalable, durable, reliable, secure, and visible.

### Workflow Responsibilities:
- Orchestrates interactive loops:
    - LLM Loop: Prompts LLM, durably executes LLM, stores responses
    - Interactive Loop: Elicits responses from input (in our case a human) and validates input responses
    - Tool Execution Loop: Durably executes Tools
- Keeps record of all interactions ([Signals, Queries, Updates](https://docs.temporal.io/develop/python/message-passing))
- Handles failures gracefully
- Input, LLM and Tool interaction history stored for debugging and analysis

## Activities
These are [Temporal Activities](https://docs.temporal.io/activities). Defined as simple functions, they are auto-retried async/event driven behind the scenes. Activities durably execute Tools and the LLM. See [tool_activities.py](./activities/tool_activities.py).

### LangGraph for Agent Planning
The two LLM-calling activities (`agent_toolPlanner` and `agent_validatePrompt`) use [LangGraph](https://langchain-ai.github.io/langgraph/) internally. Each activity invokes a single-step `StateGraph` that calls `ChatLiteLLM.bind_tools([schema], tool_choice="required")` and parses the result with `PydanticToolsParser` — this replaces hand-written JSON prompting and parsing with Pydantic-validated structured output. The graphs are defined in [`activities/langgraph_agent.py`](./activities/langgraph_agent.py) and compiled once at module load (satisfying Temporal's determinism requirement). Temporal still drives the outer loop; LangGraph handles exactly one planning step per activity call.

Each activity constructs the LLM message list as `[SystemMessage(instructions), *history_messages, HumanMessage(prompt)]`. The conversation history from Temporal's workflow state is converted to proper `HumanMessage`/`AIMessage` objects by `prompts/history_converter.py` rather than being JSON-serialized into the system prompt. This keeps the system prompt focused on instructions and lets the LLM consume history in its native multi-turn format.

## Tools 
Tools define the capabilities of the system. They are simple Python functions (could be in any language as Temporal supports multiple languages).
They are executed by Temporal Activities. They are “just code” - can connect to any API or system. They also are where the deterministic business logic is: you can validate and retry actions using code you write.
Failures are handled gracefully by Temporal.

Activities + Tools turn the probabalistic input from the user and LLM into deterministic action.

## Prompts
Prompts are where the instructions to the LLM are. Prompts are made up of initial instructions, goal instructions, and tool instructions. 
See [agent prompts](./prompts/agent_prompt_generators.py) and [goal & tool prompts](./tools/goal_registry.py). 

This is where you can add probabalistic business logic to
- to control process flow
- describe what to do
- give examples of interactions
- give instruction and validation for the LLM

## LLM
Probabalistic execution: it will _probably_ do what you tell it to do.
Turns the guidance from the prompts (see [agent prompts](./prompts/agent_prompt_generators.py) and [goal prompts](./tools/goal_registry.py)) into 
You have a choice of providers - see [setup](./setup.md). 
The LLM:
- Drives toward the initial Goal and any subsequent Goals selected by user
- Decides what to do based on input, such as:
    - Validates user input for Tools
    - Decides when to execute Tools
    - Decides on next step for Goal
- Formats input and interprets output for Tools
- is executed by Temporal Activities
    - API failures and logical failures are handled transparently

## Interaction
Interaction is managed with Temporal Signals and Queries. These are durably stored in Workflow History. 
History can be used for analysis and debugging. It's all “just code” so it's easy to add new Signals and Queries. 
Input can be very dynamic, just needs to be serializable.

The Workflow executes the Interaction Loop: gathering input, validating input, and providing a response:

![Interaction Loop](./assets/interaction_loop.png)

Here's a more detailed example for gathering inputs for Tools:

![Tool Gathering](./assets/argument_gathering_cycle.png)

# Architecture Model
Now that we have the pieces and what they do, here is a more complete diagram of how the pieces work together: 


![Architecture](./assets/ai_agent_architecture_model.png "Architecture Model")


# Adding features
Want to add more Goals and Tools? See [adding goals and tools](./adding-goals-and-tools.md). Have fun!