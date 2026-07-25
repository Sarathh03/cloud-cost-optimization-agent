"""
FULL DASHBOARD: Real AWS Data + Real Stop + Verify
------------------------------------------------------
This ties together everything you've built:
  - detect_anomaly()               (from step1 - rule engine)
  - explain_with_groq()            (from step2 - LLM explanation)
  - get_real_instances()           (from step3 - real AWS data)
  - stop_instance(), verify_stopped()  (from step4 - real action + verify)

It shows each REAL instance, flags anomalies, shows the plain-English
explanation, and gives a Stop button that actually stops the instance
on AWS and verifies it worked.

Before running:
1. Install Streamlit:   pip install streamlit
2. Make sure GROQ_API_KEY is set in your terminal (same as before):
       set GROQ_API_KEY=your_key_here
3. Make sure "aws configure" was already run successfully.
4. Run with:
       streamlit run app.py
   (NOT "python app.py" — Streamlit apps are launched differently)
"""

import streamlit as st
from step1_fake_data_and_rules import detect_anomaly
from step2_groq_explanation import explain_with_groq
from step3_aws_real_data import get_real_instances
from step4_stop_and_verify import stop_instance, verify_stopped

st.set_page_config(page_title="Cloud Cost Optimization Agent", page_icon="☁️")

st.title("☁️ Cloud Cost Optimization Agent")
st.caption("Detects idle / wasteful cloud instances and explains why in plain English.")

# Track which instances the user has stopped, so the dashboard remembers
# within this session (resets if you restart the app).
if "stopped_instances" not in st.session_state:
    st.session_state.stopped_instances = set()

with st.spinner("Fetching real AWS instances..."):
    real_instances = get_real_instances()

if not real_instances:
    st.error("No EC2 instances found in us-east-2. Launch one to see it here.")

for instance in real_instances:
    instance_id = instance["instance_id"]
    anomaly = detect_anomaly(instance)

    with st.container(border=True):
        st.subheader(f"Instance: {instance_id}")

        col1, col2, col3 = st.columns(3)
        col1.metric("State", instance["state"])
        col2.metric("CPU Usage", f"{instance['cpu_percent']}%")
        col3.metric("Training", instance["training_status"])

        if instance_id in st.session_state.stopped_instances:
            st.success("✅ Instance stopped and verified")

        elif anomaly:
            st.warning(f"⚠️ ANOMALY DETECTED: {anomaly['anomaly_type']}")
            st.write(f"**Root Cause:** {anomaly['root_cause']}")

            with st.spinner("Getting explanation..."):
                explanation = explain_with_groq(anomaly)
            st.info(explanation)

            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button("🛑 Stop Instance", key=f"stop_{instance_id}"):
                with st.spinner("Sending stop request to AWS..."):
                    stop_instance(instance_id)
                with st.spinner("Verifying it actually stopped..."):
                    success, state = verify_stopped(instance_id, wait_seconds=15)
                if success:
                    st.session_state.stopped_instances.add(instance_id)
                    st.rerun()
                else:
                    st.error(f"Stop request sent, but instance is still '{state}'. Check AWS console.")
            if btn_col2.button("Ignore", key=f"ignore_{instance_id}"):
                st.write("Ignored for now.")

        else:
            st.success("No anomaly detected.")
