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

## Where the "Agents" Actually Are

The original design used the word "agent" for every stage (Monitor Agent,
Diagnosis Agent, Action Agent, Verify Agent). In the actual build, only
**one part uses AI** — the rest are deterministic, rule-based code. This
was an intentional choice: predictable, testable behavior everywhere
except the one place AI adds real value (turning a decision into a
human-readable sentence).

| Stage | AI Involved? | What It Really Is | File |
|---|---|---|---|
| Monitor | ❌ No | Reads real EC2 state + CloudWatch CPU data via `boto3` | `step3_aws_real_data.py` |
| Diagnosis | ❌ No | Rule-based `if/else` logic — no model involved | `step1_fake_data_and_rules.py` |
| **Explanation** | ✅ **Yes** | Sends the rule engine's output to an LLM (Groq, Llama 3.3 70B) to write a plain-English explanation | `step2_groq_explanation.py` |
| Action | ❌ No | Calls AWS's `stop_instances` API directly | `step4_stop_and_verify.py` |
| Verify | ❌ No | Re-calls AWS's `describe_instances` API to confirm the new state | `step4_stop_and_verify.py` |

**In one sentence:** rule-based logic handles detection, diagnosis, action,
and verification reliably; an LLM is used only for the human-facing
explanation, keeping the system's actual decisions safe and predictable.

---

## Architecture / Flow

```
   EC2 + CloudWatch (real AWS data)
              │
              ▼
   ┌─────────────────────┐
   │   Rule Engine        │   <-- if/else logic, no AI
   │  (detect_anomaly)     │
   └─────────┬────────────┘
              │  anomaly found?
              ▼
   ┌─────────────────────┐
   │   LLM Explanation     │   <-- only AI step (Groq)
   │  (explain_with_groq)  │
   └─────────┬────────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Streamlit Dashboard  │   <-- shows everything, has Stop button
   └─────────┬────────────┘
              │  user clicks "Stop Instance"
              ▼
   ┌─────────────────────┐
   │   Stop Action         │   <-- real AWS API call
   │  (stop_instance)      │
   └─────────┬────────────┘
              │
              ▼
   ┌─────────────────────┐
   │   Verification         │   <-- re-checks AWS state
   │  (verify_stopped)      │
   └─────────────────────┘
```

---

## Project Files

| File | Purpose |
|---|---|
| `step1_fake_data_and_rules.py` | Fake instance data (for early testing) + the rule engine (`detect_anomaly`) that both fake and real data run through |
| `step2_groq_explanation.py` | Sends anomaly details to Groq's LLM API and returns a plain-English explanation |
| `step3_aws_real_data.py` | Pulls real EC2 instance state + CloudWatch CPU usage via `boto3`, shaped to match the fake data format |
| `step4_stop_and_verify.py` | Stops a real EC2 instance and verifies the stop actually happened |
| `app.py` | The Streamlit dashboard tying everything together, with real Stop/Verify wired in |

---

## How It Was Built (Development Order)

We deliberately built this in a "fake data first" order, so every layer
could be tested without touching AWS or spending money:

1. **Fake data + rule engine** — hardcoded a few sample instances,
   wrote `if/else` rules to catch obvious waste patterns, tested by
   manually editing values and re-running.
2. **LLM explanation** — connected Groq's API, sent the rule engine's
   output as a prompt, confirmed it returned clean plain-English text.
3. **Streamlit dashboard** — built a visual UI showing the same fake
   data with Stop/Ignore buttons (Stop only simulated at this stage).
4. **Real AWS data** — created a limited, read-only IAM user, launched
   one Free Tier `t2.micro` EC2 instance, and replaced the fake data
   function with a real `boto3` call to `describe_instances` +
   CloudWatch's `get_metric_statistics`.
5. **Real Stop + Verify** — expanded the IAM user with a narrow custom
   policy (`ec2:StopInstances`, `ec2:DescribeInstances` only — nothing
   else), then wired the dashboard's Stop button to actually call AWS
   and confirm the result.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- An AWS account with a Free Tier EC2 instance running
- A free Groq API key ([console.groq.com](https://console.groq.com/keys))
- AWS CLI configured (`aws configure`) with an IAM user that has:
  - `AmazonEC2ReadOnlyAccess`
  - `CloudWatchReadOnlyAccess`
  - A custom policy allowing only `ec2:StopInstances` + `ec2:DescribeInstances`

### Install dependencies
```bash
pip install boto3 groq streamlit
```

### Set your Groq API key
```bash
# Windows (per terminal session)
set GROQ_API_KEY=your_key_here

# To avoid re-setting it every time, add it as a permanent
# Windows environment variable instead (System Properties -> Environment Variables).
```

### Tag your EC2 instance
Add a tag to your test instance so the rule engine can evaluate it:
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

- The IAM user used by this project has **only** the permissions it
  needs: read instance/CloudWatch data, and stop instances. It cannot
  launch, terminate, or modify anything else.
- A billing alarm should be set in AWS Budgets before testing, as a
  safety net against unexpected charges.
- All testing was done on a single Free Tier `t2.micro` instance to
  stay within AWS's free usage limits.

---

## Possible Future Improvements

- Add more anomaly rules (oversized instance, stuck training job, etc.)
- Track real `runtime_hours` instead of leaving it at 0
- Add automatic (not manual) remediation for very safe/obvious cases
- Deploy the Streamlit dashboard so it's accessible outside localhost
- Add a history/log of past detections and actions taken
