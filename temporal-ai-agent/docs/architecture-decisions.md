# Architecture Decisions
This documents some of the "why" behind the [architecture](./architecture.md). 

## AI Models
We wanted to have flexibility to use different models, because this space is changing rapidly and models get better regularly.
Also, for you, we wanted to let you pick your model of choice. The system is designed to make changing models out simple. For how to do that, checkout the [setup guide](./setup.md).

## LangGraph for Agent Planning
The original implementation called LiteLLM directly and parsed the LLM's output by sanitizing and decoding a manually specified JSON schema (`{next, tool, args, response}`). This was fragile — LLMs occasionally returned markdown fences, duplicate JSON, or extra commentary that broke parsing.

We replaced the two planning activities (`agent_toolPlanner`, `agent_validatePrompt`) with [LangGraph](https://langchain-ai.github.io/langgraph/) `StateGraph`s. Each graph calls `ChatLiteLLM.bind_tools([schema], tool_choice="required")` and parses the result with `PydanticToolsParser`, producing a guaranteed-valid Pydantic model before the result ever reaches the workflow.

`with_structured_output()` was the original target API but it hardcodes `tool_choice="any"` internally, which the OpenAI API rejects (it only accepts `"none"`, `"auto"`, or `"required"`). The `langchain-litellm` library converts `"any"` → `"required"` for known OpenAI model names, but the conversion is bypassed for models specified with the `openai/` provider prefix (e.g. `openai/gpt-5.4-2026-03-05`). Using `bind_tools` directly with `tool_choice="required"` avoids this ambiguity entirely and works regardless of how the model name is specified.

LangGraph was chosen because it is the most widely adopted Python agent framework (part of the LangChain ecosystem), integrates cleanly with LiteLLM via `langchain-litellm`, and supports structured output across all major providers. The single-step graph pattern keeps Temporal fully in control of the outer loop while LangGraph handles one planning call per activity invocation.

## Conversation History as LangChain Message Objects

The initial LangGraph implementation embedded the full `ConversationHistory` as a JSON blob inside the `SystemMessage` on every LLM call. This worked, but required the LLM to parse a raw JSON string — an unnatural format that consumed tokens describing structure rather than content.

We changed both planning activities to convert Temporal's dict-based history to proper LangChain message objects (`HumanMessage`, `AIMessage`) before invoking the graph. The LLM now receives history in the multi-turn format it was trained on:

```
[SystemMessage(instructions), HumanMessage(...), AIMessage(...), ..., HumanMessage(current_prompt)]
```

Temporal's `ConversationHistory` format is **unchanged** — conversion is an activity-layer concern handled by `prompts/history_converter.py`. The `"agent"` actor maps to `AIMessage` with the response text extracted from the dict. `"tool_result"` and `"user_confirmed_tool_run"` map to prefixed `HumanMessage` objects since proper `ToolMessage` requires a `tool_call_id` that isn't tracked in Temporal's history. `"conversation_summary"` entries (written on `continue_as_new`) are pulled out of the message list and injected into the system prompt instead, since they are meta-context rather than conversational turns.

## Temporal
We asked one of the AI models used in this demo to answer this question (edited minorly):

### Reliability and State Management:
 Temporal ensures durability and fault tolerance, which are critical for agentic AI systems that involve long-running, complex workflows. For example, it preserves application state across failures, allowing AI agents to resume from where they left off without losing progress. Major AI companies use this for research experiments and agentic flows, where reliability is essential for continuous exploration.
### Handling Complex, Dynamic Workflows: 
Agentic AI often involves unpredictable, multi-step processes like web crawling or data searching. Temporal’s workflow orchestration simplifies managing these tasks by abstracting complexity, providing features like retries, timeouts, and signals/queries. Temporal makes observability and resuming failed complex experiments and deep searches simple.
### Scalability and Speed: 
Temporal enables rapid development and scaling, crucial for AI systems handling large-scale experiments or production workloads. AI model deployment and SRE teams use it to get code to production quickly with scale as a focus, while research teams can (and do!) run hundreds of experiments daily. Temporal customers report a significant reduction in development time (e.g., 20 weeks to 2 weeks for a feature).
### Observability and Debugging: 
Agentic AI systems need insight into where processes succeed or fail. Temporal provides end-to-end visibility and durable workflow history, which Temporal customers are using to track agentic flows and understand failure points.
### Simplified Error Handling: 
Temporal abstracts failure management (e.g., retries, rollbacks) so developers can focus on AI logic rather than "plumbing" code. This is vital for agentic AI, where external interactions (e.g., APIs, data sources) are prone to failure.
### Flexibility for Experimentation: 
For research-heavy agentic AI, Temporal supports dynamic, code-first workflows and easy integration of new signals/queries, aligning with researchers needs to iterate quickly on experimental paths.

In essence, Temporal’s value lies in its ability to make agentic AI systems more reliable, scalable, and easier to develop by handling the underlying complexity of distributed workflows for both research and applied AI tasks.

Temporal was built to solve the problems of distributed computing, including scalability, reliability, security, visibility, and complexity. Agentic AI systems are complex distributed systems, so Temporal should fit well. Scaling, security, and productionalization are major pain points in March 2025 for building agentic systems.

In this system Temporal lets you:
- Orchestrate interactions across distributed data stores and tools <br />
- Hold state, potentially over long periods of time <br />
- Ability to ‘self-heal’ and retry until the (probabilistic) LLM returns valid data <br />
- Support for human intervention such as approvals <br />
- Parallel processing for efficiency of data retrieval and tool use <br />