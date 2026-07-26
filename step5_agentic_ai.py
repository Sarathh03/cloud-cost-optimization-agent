"""
STEP 5 (UPGRADE): True Agentic AI using Tool Calling
--------------------------------------------------------
Difference from before:
  OLD: if/else rules DECIDE there's an anomaly -> code stops the instance.
       The LLM only wrote a sentence about a decision it never made.

  NEW: We describe the "stop_instance" action to the LLM as a TOOL.
       We give the LLM the raw instance data (state, CPU, tags) and let
       IT decide whether the situation calls for stopping the instance.
       If it decides yes, it calls the tool itself. THIS is what makes
       it an agent: the model reasons and chooses an action, instead of
       just following someone else's if/else logic.

We still keep step1's rule engine available for comparison in your report,
but this script's decision-making is done ENTIRELY by the LLM.

Run with: python step5_agentic_ai.py
"""

import os
import json
from groq import Groq
from step3_aws_real_data import get_real_instances
from step4_stop_and_verify import stop_instance, verify_stopped

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# -----------------------------------------
# Describe the tool the LLM is allowed to use
# -----------------------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "stop_instance",
            "description": "Stops an AWS EC2 instance that is wasting money "
                            "(e.g. still running after its job finished, or "
                            "sitting idle with very low CPU usage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "The EC2 instance ID to stop, e.g. i-0abc123"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why this instance should be stopped"
                    }
                },
                "required": ["instance_id", "reason"]
            }
        }
    }
]


def run_agent_on_instance(instance):
    """
    Sends ONE instance's real data to the LLM and lets IT decide
    whether to call the stop_instance tool. No if/else deciding here.
    """
    prompt = f"""
You are a cloud cost optimization agent. You will be given real data about
one AWS EC2 instance. Decide, using your own judgment, whether this instance
is being wasteful (for example: still running after training/work is done,
or running with very low CPU usage for no good reason).

If it IS wasteful, call the stop_instance tool with the instance_id and a
short reason. If it is NOT wasteful (e.g. actively being used, or already
stopped), do NOT call any tool — just explain briefly why it's fine.

Instance data:
{json.dumps(instance, indent=2)}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice="auto"  # the model decides whether to use the tool or not
    )

    message = response.choices[0].message
    return message


if __name__ == "__main__":
    print("Fetching real AWS instances...\n")
    instances = get_real_instances()

    if not instances:
        print("No instances found.")
        exit()

    for instance in instances:
        print(f"Instance: {instance['instance_id']}")
        print(f"  State: {instance['state']} | CPU: {instance['cpu_percent']}% | Training: {instance['training_status']}")

        decision = run_agent_on_instance(instance)

        if decision.tool_calls:
            # The LLM decided, on its own, to take action
            for call in decision.tool_calls:
                args = json.loads(call.function.arguments)
                instance_id = args["instance_id"]
                reason = args["reason"]

                print(f"  🤖 AGENT DECISION: Stop this instance")
                print(f"     Reason (from LLM): {reason}")

                confirm = input(f"     Agent wants to stop {instance_id}. Type YES to allow: ").strip()
                if confirm == "YES":
                    stop_instance(instance_id)
                    success, state = verify_stopped(instance_id, wait_seconds=15)
                    print(f"     ✅ Verified state: {state}" if success else f"     ⚠️ Still {state}")
                else:
                    print("     Cancelled by user. Instance left running.")
        else:
            # The LLM decided NOT to act, and explained why
            print(f"  🤖 AGENT DECISION: No action needed")
            print(f"     Reasoning (from LLM): {decision.content}")

        print("-" * 60)
