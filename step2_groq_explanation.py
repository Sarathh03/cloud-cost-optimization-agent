"""
STEP 3 + STEP 4: LLM Explanation using Groq
----------------------------------------------
This builds on step1_fake_data_and_rules.py.
The rule engine already found the anomaly and root cause (no AI needed for that).
Here, we just ask an LLM (via Groq) to turn that into a friendly, readable sentence.

Before running:
1. Install the SDK:      pip install groq
2. Get a free API key:   https://console.groq.com/keys (no credit card needed)
3. Set it as an environment variable (don't paste it directly in code):

   On Windows (cmd):
       set GROQ_API_KEY=your_key_here

   Then run this script in the SAME terminal window.
"""

import os
from groq import Groq

# Import the fake data + rule engine from step 1
from step1_fake_data_and_rules import fake_instances, detect_anomaly


def explain_with_groq(anomaly):
    """
    Takes the anomaly dict from our rule engine and asks an LLM (via Groq)
    to write a short, human-friendly explanation.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = f"""
You are a cloud cost assistant. Explain the following detected issue in
1-2 short, friendly sentences for a non-technical user. Do not invent
any new facts, only explain what is given below.

Instance ID: {anomaly["instance_id"]}
Anomaly Type: {anomaly["anomaly_type"]}
Root Cause: {anomaly["root_cause"]}
Recommended Action: {anomaly["recommended_action"]}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    print("Scanning instances...\n")

    for instance in fake_instances:
        anomaly = detect_anomaly(instance)

        print(f"Instance: {instance['instance_id']}")

        if anomaly:
            print("  ⚠️  ANOMALY DETECTED")
            print(f"     Type: {anomaly['anomaly_type']}")
            print("     Explanation (from Groq):")
            explanation = explain_with_groq(anomaly)
            print(f"     {explanation}")
        else:
            print("  ✅ No anomaly")

        print("-" * 50)
