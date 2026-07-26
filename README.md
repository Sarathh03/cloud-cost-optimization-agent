# ☁️ Cloud Cost Optimization Agent

An automated system that detects idle/wasteful AWS EC2 instances, explains
the issue in plain English using an LLM, and can stop the instance
automatically — with verification that the action actually worked.

---

## What This Project Does

1. **Monitors** real AWS EC2 instances (state, CPU usage, tags)
2. **Detects** waste using rule-based logic (e.g. instance still running
   after training finished, with low CPU usage)
3. **Diagnoses** the root cause of the issue
4. **Explains** the issue in plain English using an LLM (Groq/Llama 3.3)
5. **Acts** by stopping the wasteful instance (with user confirmation via
   a dashboard button)
6. **Verifies** the action actually worked by re-checking AWS

All of this is shown live in a Streamlit dashboard.

---

# 🤖 Cloud Cost Optimization Agent

An orchestrated Agentic AI system that monitors real AWS EC2 instances,
retrieves relevant cost-optimization policy knowledge, reasons about
whether an instance is wasteful, reflects on its own decision, and — only
with human approval — stops the instance and verifies the result.

---

## What This Project Does

1. **Monitor** — reads real EC2 state, CPU usage, tags, and uptime via `boto3`
2. **Retrieve (RAG)** — searches a knowledge base of cost-optimization
   policies for guidance relevant to this instance's situation
3. **Diagnose** — an LLM reasons over the instance data + retrieved policy
   knowledge + past decisions, and decides whether to propose stopping it
   (via tool calling — the model chooses the action, not `if/else` code)
4. **Reflect** — the agent double-checks its own decision before acting,
   and can reject its own proposal or loop back to re-diagnose
5. **Act** — only after a human confirms, the agent calls AWS's real
   `stop_instances` API
6. **Verify** — re-checks AWS to confirm the action actually worked
7. **Remember** — every decision (data seen, reasoning, action, outcome)
   is logged, so future runs on the same instance have memory of the past

All of this is orchestrated as an explicit graph (LangGraph) and shown
live in a Streamlit dashboard.

---

## Why This Counts as Agentic AI (Not Just Automation)

An earlier version of this project used `if/else` rules to detect
waste, with an LLM only writing a friendly sentence about a decision
the code already made. That is **automation with an AI narrator**, not
an agent.

This version is different: the LLM is handed raw instance data plus
retrieved policy knowledge and **decides for itself**, via tool calling,
whether the situation warrants action. It then **checks its own
reasoning** in a separate reflection step before anything happens. That
loop — perceive → retrieve → reason → reflect → (approved) act → verify
— is what makes this a genuine agentic AI system rather than a rule
engine with an AI-generated caption.

---

## Agentic AI Components (Mapped to Core Concepts)

| Concept | Implementation | File |
|---|---|---|
| **Agent / Reasoning** | LLM (Groq, Llama 3.3 70B) decides via tool calling whether to act | `agent_graph.py` (`diagnose_node`) |
| **Orchestration** | LangGraph `StateGraph` with 5 nodes and conditional routing | `agent_graph.py` |
| **Agentic RAG** | TF-IDF retrieval over a policy knowledge base, run before every decision | `knowledge_base.py`, `rag_retriever.py` |
| **Memory / State** | JSON-based decision log; past decisions per instance are recalled in the reasoning prompt | `memory_store.py` |
| **Reflection / Self-correction** | A second LLM call critiques the first decision; can reject and trigger a re-diagnose loop (max 2 loops, then defers to human) | `agent_graph.py` (`reflect_node`, `route_after_reflection`) |
| **Tool use** | `stop_instance` exposed to the LLM as a callable tool via function calling | `agent_graph.py` |
| **Human-in-the-loop** | Action only executes after explicit dashboard confirmation | `app.py`, `agent_graph.py` (`act_node`) |
| **Monitoring / Environment sensing** | Real EC2 state + CloudWatch CPU + real uptime via `boto3` | `step3_aws_real_data.py` |
| **Action + Verification** | Real AWS API calls to stop and re-check instance state | `step4_stop_and_verify.py` |

---

## Orchestration Graph

```
                 START
                   │
                   ▼
        ┌─────────────────────┐
        │  retrieve_knowledge   │   <- Agentic RAG: searches policy docs
        └──────────┬───────────┘
                    │
                    ▼
        ┌─────────────────────┐
        │      diagnose          │◄──────────────┐   <- LLM decides via tool calling,
        └──────────┬───────────┘                │      using retrieved knowledge + memory
                    │                             │
                    ▼                             │
        ┌─────────────────────┐                 │
        │       reflect          │                 │   <- LLM self-checks its own decision
        └──────────┬───────────┘                │
                    │                             │
           ┌────────┴────────┐                   │
           ▼                 ▼                   │
     [approved]      [rejected, retry] ───────────┘
           │           (max 2 loops)
           │
     [not wanting to act] ──► END
           │
           ▼
        ┌───────┐
        │  act    │   <- only runs if human_approved=True
        └───┬───┘
            │
            ▼
        ┌───────┐
        │ verify  │   <- re-checks real AWS state
        └───┬───┘
            │
            ▼
           END
```

---

## Project Files

| File | Purpose |
|---|---|
| `knowledge_base.py` | The knowledge source — cost-optimization policy documents |
| `rag_retriever.py` | TF-IDF retrieval over the knowledge base (the "R" in RAG) |
| `memory_store.py` | Persistent decision log + recall of past decisions per instance |
| `agent_graph.py` | LangGraph orchestration: retrieve → diagnose → reflect → act → verify |
| `step3_aws_real_data.py` | Real EC2/CloudWatch monitoring via `boto3`, including real uptime |
| `step4_stop_and_verify.py` | Real AWS stop action + verification |
| `app.py` | Streamlit dashboard — the full agent, visualized |
| `step1_fake_data_and_rules.py`, `step2_groq_explanation.py`, `step5_agentic_ai.py` | Earlier development stages, kept for the rule-based-vs-agentic comparison (see below) |

---

## Development Order (Why It Was Built This Way)

We built this in layers, testing each one independently before wiring
it into the next, so every component could be verified in isolation:

1. **Fake data + rule engine** — validated basic detection logic with
   no AWS cost or risk.
2. **LLM explanation only** — connected an LLM but kept it purely
   descriptive (no decision-making power yet).
3. **Streamlit dashboard (simulated)** — visualized the flow before
   touching real infrastructure.
4. **Real AWS monitoring** — replaced fake data with real `boto3` calls
   on a Free Tier EC2 instance, with a locked-down, read-only IAM user.
5. **Real Stop + Verify** — expanded IAM to a narrow `StopInstancesOnly`
   custom policy, wired a real action + verification loop.
6. **Agentic upgrade (tool calling)** — replaced the rule engine with
   an LLM that decides via tool calling, kept for comparison as
   `step5_agentic_ai.py`.
7. **Full orchestration (this version)** — added Agentic RAG, memory,
   and a reflection/self-correction loop, all coordinated through a
   LangGraph state graph.

---

## Rule-Based vs. Agentic: A Direct Comparison

| | Rule-based (Step 1-4) | Agentic (this version) |
|---|---|---|
| Who decides? | `if/else` code | The LLM, via tool calling |
| Uses retrieved knowledge? | No | Yes (RAG) |
| Remembers past decisions? | No | Yes (memory log) |
| Double-checks itself? | No | Yes (reflection loop) |
| Predictability | Fully deterministic | Reasoning-based, less rigid |
| Caught the `runtime_hours=0` data bug? | No (wouldn't have noticed) | Yes — reflection flagged a freshly-started instance as too new to judge, exposing a real gap in the original monitoring code |

That last row happened during real testing, not as a designed demo: the
reflection step rejected a stop recommendation because the instance had
only been running 0.09 hours, correctly reasoning that a freshly-started
instance's CPU/training data might not be representative yet. This is a
concrete example of the self-correction mechanism catching an edge case
a pure rule engine would have missed.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- An AWS account with a Free Tier EC2 instance
- A free Groq API key ([console.groq.com](https://console.groq.com/keys))
- AWS CLI configured (`aws configure`) with an IAM user limited to:
  - `AmazonEC2ReadOnlyAccess`
  - `CloudWatchReadOnlyAccess`
  - A custom policy allowing only `ec2:StopInstances` + `ec2:DescribeInstances`

### Install dependencies
```bash
pip install boto3 groq streamlit langgraph scikit-learn
```

### Set your Groq API key
```bash
set GROQ_API_KEY=your_key_here
```

### Tag your EC2 instance
```
Key: training_status
Value: completed
```

### Run the dashboard
```bash
streamlit run app.py
```

---

## Safety Notes

- The IAM user has only the permissions it needs: read instance/CloudWatch
  data, and stop instances. It cannot launch, terminate, or modify
  anything else.
- A billing alarm was set in AWS Budgets before testing.
- Real AWS actions require explicit human confirmation via the dashboard
  — the agent never acts autonomously without approval.
- All testing was done on a single Free Tier `t2.micro` instance.

---

## Possible Future Improvements

- Add more tools (e.g. `resize_instance`, `alert_only`) so the agent
  chooses between multiple actions, not just stop/don't-stop
- Replace TF-IDF retrieval with embedding-based retrieval for a larger
  knowledge base
- Add automatic (not manual) remediation for very high-confidence,
  low-risk cases
- Persist memory in a real database instead of a local JSON file
- Deploy the dashboard so it's accessible outside localhost

