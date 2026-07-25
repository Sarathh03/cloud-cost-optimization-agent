# 📸 Project Screenshots — What Each One Proves

This document walks through each screenshot in order, explaining what it
shows and which part of the Cloud Cost Optimization Agent project it
demonstrates. Use this alongside `README.md` for your project report or
demo walkthrough.

---

### 01_billing_budget_alarm.png
**AWS Billing → Budgets → Overview**
Shows a $1.00 budget alarm ("My Zero-Spend Budget-Agenti...") set up in
AWS Billing and Cost Management, with a "Healthy" status and $0.00 spent
so far. This proves a safety net was in place *before* any real AWS
resources were touched — protecting against unexpected charges while
testing.

### 02_iam_readonly_permissions.png
**IAM → Users → cloud-agent-readonly → Permissions**
Shows the IAM user created specifically for this project, with exactly
3 attached policies: `AmazonEC2ReadOnlyAccess`, `CloudWatchReadOnlyAccess`,
and `IAMUserChangePassword`. This demonstrates the least-privilege setup —
the credentials used by the script could only *read* AWS data at this
stage, not modify anything.

### 03_ec2_instance_running_tagged.png
**EC2 → Instances → test-ml-instance**
Shows the Free Tier `t2.micro` instance (`i-074b998100d7f0eee`) running
in the `us-east-2` (Ohio) region, right after a tag-management request
succeeded. This is the real EC2 instance used to test the "Monitor" and
"Diagnosis" stages against actual AWS data instead of fake data.

### 04_vscode_real_data_no_anomaly.png
**VS Code — running `step3_aws_real_data.py`**
Terminal output shows the script connecting to real AWS, finding the
instance in a `stopped` state with `0.0%` CPU, and correctly reporting
**"No anomaly"** — because a stopped instance isn't wasting money. This
proves the rule engine correctly distinguishes "stopped and fine" from
"running and wasteful."

### 05_ec2_console_stopped.png
**EC2 Console — instance state: Stopped**
Confirms the instance's real state in the AWS console at this point in
testing, matching what the script reported in image 04.

### 06_ec2_console_starting.png
**EC2 Console — instance state: Running (Initializing)**
Shows the instance right after being manually started, status check
still "Initializing." This was done deliberately to test whether the
rule engine would catch it as idle once it was running.

### 07_vscode_anomaly_detected.png
**VS Code — running `step3_aws_real_data.py` again**
Now that the instance is `running` with `0.0%` CPU and the
`training_status: completed` tag, the script correctly flags:
**"ANOMALY DETECTED — Idle Instance After Training."** This is the key
proof that the Monitor + Diagnosis stages work end-to-end on real,
live AWS data (not just the fake test data from Step 1).

### 08_vscode_multiple_runs_anomaly.png
**VS Code — repeated runs**
Shows the script run multiple times in a row, each time consistently
detecting the same anomaly as CPU usage stayed low (`0.0%` → `0.25%`).
This demonstrates the detection is stable and repeatable, not a fluke.

### 09_ec2_after_stop_policy_added.png
**EC2 Console + open browser tabs: "StopInstancesOnly" and "Policies | IAM"**
The browser tabs visible here show the custom `StopInstancesOnly` IAM
policy being created and attached — the narrow permission that allows
the script to stop instances (and only stop them, nothing else). This
is the setup step before the real Stop action was wired in.

### 10_streamlit_dashboard_full_flow.png / 11_streamlit_dashboard_alt.png
**Streamlit Dashboard — full UI**
The finished dashboard showing:
- Real instance ID, state (`running`), CPU (`0.0%`), and training status
- The anomaly warning: "Idle Instance After Training"
- The root cause explanation
- The **plain-English explanation written by the LLM (Groq)**
- The "Stop Instance" and "Ignore" buttons

This single screenshot demonstrates almost the entire project at once:
Monitor → Diagnose → Explain, all visualized, with Act available as a
one-click action.

### 12_github_repo_pushed.png
**GitHub — cloud-cost-optimization-agent repository**
Confirms the final codebase (`app.py` and all 4 step files) successfully
pushed to a public GitHub repository, with commit history and file
structure visible. This is the delivered, shareable artifact of the
project.

---

## How These Map to the Project Stages

| Stage | Proven By |
|---|---|
| Safety setup (billing alarm, least-privilege IAM) | 01, 02 |
| Monitor (real AWS data) | 03, 04, 05, 06 |
| Diagnosis (rule-based anomaly detection) | 04, 07, 08 |
| Explanation (LLM / Groq) | 10, 11 |
| Action + Verify (real Stop, permission setup) | 09, 10, 11 |
| Final delivery | 12 |
