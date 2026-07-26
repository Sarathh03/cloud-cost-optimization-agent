"""
FULL DASHBOARD: Real AWS Data + Orchestrated Agent (RAG + Memory + Reflection) + Real Stop + Verify
--------------------------------------------------------------------------------------------------------
This is the final, complete version. It ties together:
  - get_real_instances()   (step3 - real AWS monitoring)
  - agent_graph.py         (LangGraph orchestration: retrieve_knowledge -> diagnose -> reflect -> act -> verify)
  - rag_retriever.py       (Agentic RAG: retrieves relevant policy docs before reasoning)
  - memory_store.py        (memory/state: logs every decision, recalls past decisions per instance)
  - step4_stop_and_verify.py (real AWS action + verification)

Flow shown on screen:
  1. Agent retrieves relevant knowledge for this instance's situation
  2. Agent reasons and proposes a decision (tool call or not)
  3. Agent reflects on its own decision before acting
  4. If it still wants to act, YOU confirm via the button (human-in-the-loop)
  5. Only then does it call AWS for real, and verifies the result

Before running:
  pip install streamlit langgraph groq scikit-learn boto3
  set GROQ_API_KEY=your_key_here
  (aws configure must already be done)

Run with: streamlit run app.py
"""

import streamlit as st
from step3_aws_real_data import get_real_instances
from agent_graph import run_full_agent

st.set_page_config(page_title="Cloud Cost Optimization Agent", page_icon="🤖")

st.title("🤖 Cloud Cost Optimization Agent")
st.caption(
    "Orchestrated agent: retrieves policy knowledge, reasons, reflects, then acts only with your approval."
)

if "stopped_instances" not in st.session_state:
    st.session_state.stopped_instances = set()
if "proposals" not in st.session_state:
    st.session_state.proposals = {}  # instance_id -> graph result (the agent's proposal)

with st.spinner("Fetching real AWS instances..."):
    real_instances = get_real_instances()

if not real_instances:
    st.error("No EC2 instances found. Launch one to see it here.")

for instance in real_instances:
    instance_id = instance["instance_id"]

    with st.container(border=True):
        st.subheader(f"Instance: {instance_id}")

        col1, col2, col3 = st.columns(3)
        col1.metric("State", instance["state"])
        col2.metric("CPU Usage", f"{instance['cpu_percent']}%")
        col3.metric("Training", instance["training_status"])

        if instance_id in st.session_state.stopped_instances:
            st.success("✅ Instance stopped and verified")
            continue

        # Run the agent's proposal phase (retrieve -> diagnose -> reflect), no action yet
        if instance_id not in st.session_state.proposals:
            with st.spinner("🤖 Agent retrieving knowledge and reasoning..."):
                result = run_full_agent(instance, human_approved=False)
            st.session_state.proposals[instance_id] = result

        result = st.session_state.proposals[instance_id]

        with st.expander("📚 Retrieved knowledge used by the agent"):
            for doc in result["retrieved_docs"]:
                st.write(f"**{doc['title']}** (relevance: {doc['score']})")
                st.write(doc["text"])

        with st.expander("🔎 Agent's self-reflection"):
            st.write(result["reflection_notes"])

        if result["wants_to_act"] and result["reflection_passed"]:
            st.warning("🤖 AGENT DECISION: Recommend stopping this instance")
            st.info(f"**Reasoning:** {result['reasoning']}")

            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button("🛑 Confirm Stop", key=f"stop_{instance_id}"):
                with st.spinner("Executing approved action and verifying..."):
                    final_result = run_full_agent(instance, human_approved=True)
                if final_result["verified_state"] in ("stopped", "stopping"):
                    st.session_state.stopped_instances.add(instance_id)
                    st.rerun()
                else:
                    st.error(
                        f"Stop sent, but state is '{final_result['verified_state']}'. Check AWS console."
                    )
            if btn_col2.button("Override / Ignore", key=f"ignore_{instance_id}"):
                st.write("Agent's suggestion overridden. Instance left running.")

        elif result["wants_to_act"] and not result["reflection_passed"]:
            # Agent initially leaned toward stopping, but its own reflection
            # raised unresolved doubts (and the retry loop didn't clear them).
            st.info(
                "🤖 AGENT DECISION: Flagged for review, but not confident enough to recommend"
            )
            st.write(f"**Initial reasoning:** {result['reasoning']}")
            st.write(f"**Reflection's concern:** {result['reflection_notes']}")

            if st.button(
                "🛑 Stop anyway (manual override)", key=f"forcestop_{instance_id}"
            ):
                with st.spinner("Executing manual override and verifying..."):
                    final_result = run_full_agent(instance, human_approved=True)
                if final_result["verified_state"] in ("stopped", "stopping"):
                    st.session_state.stopped_instances.add(instance_id)
                    st.rerun()
                else:
                    st.error(
                        f"Stop sent, but state is '{final_result['verified_state']}'. Check AWS console."
                    )

        else:
            st.success("🤖 AGENT DECISION: No action needed")
            st.write(f"**Reasoning:** {result['reasoning']}")
