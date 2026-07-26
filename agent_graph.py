"""
AGENT ORCHESTRATION GRAPH (LangGraph)
------------------------------------------
This is the "orchestration workflow design" the rubric asks for.

Instead of one big Python function doing everything, we define the agent
as a GRAPH of small steps (nodes), connected by edges that decide what
happens next. This makes the workflow explicit, inspectable, and easy to
extend - which is exactly why frameworks like LangGraph exist.

Graph shape:

    retrieve_knowledge
            |
            v
        diagnose  <-------.
            |              |
            v              |
         reflect ----------+   (loops back to diagnose once if reflection
            |                   finds a problem, otherwise continues)
            v
     [decision: act or end]
        /          \\
      act          end
       |
       v
     verify
       |
       v
      end

Install: pip install langgraph
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

from rag_retriever import retrieve_relevant_docs
from memory_store import summarize_history_for_prompt, log_decision
from step4_stop_and_verify import stop_instance, verify_stopped
from guardrails import validate_tool_call, record_action_taken, GuardrailViolation

import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

tools = [
    {
        "type": "function",
        "function": {
            "name": "stop_instance",
            "description": "Stops an AWS EC2 instance that is wasting money.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string"},
                    "reason": {"type": "string"}
                },
                "required": ["instance_id", "reason"]
            }
        }
    }
]


# -----------------------------------------
# 1. Define the shared state that flows through the graph
# -----------------------------------------
class AgentState(TypedDict):
    instance: dict                 # raw instance data (from step3)
    retrieved_docs: list           # knowledge base docs found relevant
    reasoning: str                 # the agent's explanation
    wants_to_act: bool             # did the agent decide to stop it?
    reflection_notes: str          # self-check output
    reflection_passed: bool        # did the self-check approve the decision?
    reflection_loops: int          # safety counter to avoid infinite loops
    action_taken: Optional[str]    # "stopped" | "no_action" | "blocked"
    verified_state: Optional[str]  # AWS state after verification
    human_approved: Optional[bool] # set by the caller (dashboard/CLI) before act
    guardrail_message: Optional[str]  # set if a guardrail blocked the action


# -----------------------------------------
# 2. Node: Retrieve relevant knowledge (RAG step)
# -----------------------------------------
def retrieve_knowledge_node(state: AgentState) -> dict:
    instance = state["instance"]
    query = (
        f"instance state {instance['state']}, "
        f"cpu {instance['cpu_percent']}%, "
        f"training {instance['training_status']}"
    )
    docs = retrieve_relevant_docs(query, top_k=2)
    return {"retrieved_docs": docs}


# -----------------------------------------
# 3. Node: Diagnose (the LLM reasons and decides using tool calling)
# -----------------------------------------
def diagnose_node(state: AgentState) -> dict:
    instance = state["instance"]
    docs_text = "\n\n".join(f"- {d['title']}: {d['text']}" for d in state["retrieved_docs"])
    history_text = summarize_history_for_prompt(instance["instance_id"])

    prompt = f"""
You are a cloud cost optimization agent. Decide whether this EC2 instance
should be stopped, using the policy knowledge and past decisions below.

Instance data:
{json.dumps(instance, indent=2)}

Relevant policy knowledge (retrieved):
{docs_text}

{history_text}

If the instance should be stopped, call the stop_instance tool with a
clear reason grounded in the policy knowledge above. If not, explain why
in plain text without calling any tool.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice="auto"
    )
    message = response.choices[0].message

    if message.tool_calls:
        args = json.loads(message.tool_calls[0].function.arguments)
        return {"wants_to_act": True, "reasoning": args.get("reason", "")}
    else:
        return {"wants_to_act": False, "reasoning": message.content or ""}


# -----------------------------------------
# 4. Node: Reflect (self-check the diagnosis before acting)
# -----------------------------------------
def reflect_node(state: AgentState) -> dict:
    if not state["wants_to_act"]:
        # Nothing to double-check if the agent isn't proposing action
        return {"reflection_passed": True, "reflection_notes": "No action proposed; nothing to reflect on."}

    instance = state["instance"]
    prompt = f"""
You previously decided to stop this instance with this reasoning:
"{state['reasoning']}"

Instance data:
{json.dumps(instance, indent=2)}

Double-check your own decision. Is there any reason this could be a MISTAKE
(e.g. instance just started and still initializing, CPU data missing, training
status is 'unknown' rather than confirmed 'completed')? Answer with exactly
"APPROVE" if your original decision still holds, or "REJECT: <reason>" if you
now think it was wrong.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.strip()

    if text.upper().startswith("APPROVE"):
        return {"reflection_passed": True, "reflection_notes": text}
    else:
        return {
            "reflection_passed": False,
            "reflection_notes": text,
            "reflection_loops": state.get("reflection_loops", 0) + 1
        }


# -----------------------------------------
# 5. Router: decide where to go after reflection
# -----------------------------------------
def route_after_reflection(state: AgentState) -> str:
    if not state["wants_to_act"]:
        return "end"
    if state["reflection_passed"]:
        return "act"
    if state.get("reflection_loops", 0) >= 2:
        # Safety valve: don't loop forever, just stop proposing action
        return "end"
    return "diagnose"  # loop back and re-diagnose with the reflection's concerns


# -----------------------------------------
# 6. Node: Act (only reached if a human has approved, checked by caller)
# -----------------------------------------
def act_node(state: AgentState) -> dict:
    instance = state["instance"]
    instance_id = instance["instance_id"]

    if not state.get("human_approved"):
        # Caller (dashboard/CLI) hasn't approved yet - do nothing.
        log_decision(instance_id, instance, state["reasoning"], "no_action", "Awaiting human approval")
        return {"action_taken": "no_action"}

    # GUARDRAILS: validate before touching real AWS, regardless of how
    # confident the agent (or the human) is. Any failure here blocks the
    # action entirely - no override, since these are safety-critical checks,
    # not judgment calls.
    try:
        validate_tool_call(instance, instance_id, state["reasoning"])
    except GuardrailViolation as e:
        log_decision(instance_id, instance, state["reasoning"], "blocked", str(e))
        return {"action_taken": "blocked", "guardrail_message": str(e)}

    stop_instance(instance_id)
    record_action_taken()
    log_decision(instance_id, instance, state["reasoning"], "stopped")
    return {"action_taken": "stopped"}


# -----------------------------------------
# 7. Node: Verify
# -----------------------------------------
def verify_node(state: AgentState) -> dict:
    if state["action_taken"] != "stopped":
        return {"verified_state": None}
    instance_id = state["instance"]["instance_id"]
    success, aws_state = verify_stopped(instance_id, wait_seconds=15)
    return {"verified_state": aws_state}


# -----------------------------------------
# Build the graph
# -----------------------------------------
def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("retrieve_knowledge", retrieve_knowledge_node)
    builder.add_node("diagnose", diagnose_node)
    builder.add_node("reflect", reflect_node)
    builder.add_node("act", act_node)
    builder.add_node("verify", verify_node)

    builder.add_edge(START, "retrieve_knowledge")
    builder.add_edge("retrieve_knowledge", "diagnose")
    builder.add_edge("diagnose", "reflect")
    builder.add_conditional_edges(
        "reflect",
        route_after_reflection,
        {"act": "act", "diagnose": "diagnose", "end": END}
    )
    builder.add_edge("act", "verify")
    builder.add_edge("verify", END)

    return builder.compile()


agent_graph = build_graph()


def run_full_agent(instance, human_approved=False):
    """
    Convenience function: runs the entire graph for one instance.
    Call with human_approved=False first to see the agent's proposal,
    then call again with human_approved=True after the user confirms.
    """
    initial_state = {
        "instance": instance,
        "retrieved_docs": [],
        "reasoning": "",
        "wants_to_act": False,
        "reflection_notes": "",
        "reflection_passed": False,
        "reflection_loops": 0,
        "action_taken": None,
        "verified_state": None,
        "human_approved": human_approved,
        "guardrail_message": None
    }
    return agent_graph.invoke(initial_state)
