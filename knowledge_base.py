"""
KNOWLEDGE SOURCE for Agentic RAG
------------------------------------
This is the "knowledge source" the rubric asks for. In a real company,
this might be pulled from AWS's own documentation, your team's internal
cost-optimization playbook, or past incident reports. For this project,
we've written a small set of grounded guidelines so the agent has
something real to retrieve and reason against, instead of relying only
on its own general training knowledge.

Each entry is one "document" the retriever can find and hand to the agent.
"""

KNOWLEDGE_BASE = [
    {
        "id": "doc1",
        "title": "Idle instance policy",
        "text": (
            "An EC2 instance is considered idle and safe to stop if its CPU "
            "utilization has stayed below 10% for at least 10 minutes AND "
            "there is no active job (such as training) currently running on "
            "it. Idle running instances are one of the most common sources "
            "of unnecessary cloud spend."
        )
    },
    {
        "id": "doc2",
        "title": "Post-training instance handling",
        "text": (
            "Once a machine learning training job completes, the instance "
            "that ran it should be stopped within a short window unless it "
            "is explicitly needed for immediate follow-up work (such as "
            "evaluation or deployment). Leaving a post-training instance "
            "running is considered wasteful."
        )
    },
    {
        "id": "doc3",
        "title": "When NOT to stop an instance",
        "text": (
            "An instance should NOT be stopped if it shows meaningful CPU "
            "activity (above 10%), if its training_status is 'running' or "
            "'unknown', or if it has been recently started (within the last "
            "few minutes) and may still be initializing services."
        )
    },
    {
        "id": "doc4",
        "title": "Cost impact of forgotten instances",
        "text": (
            "A t2.micro or t3.micro instance left running unnecessarily "
            "typically costs a small but nonzero amount per hour. While "
            "individually small, forgotten instances across a team or "
            "organization compound into significant recurring waste over "
            "a month if left unchecked."
        )
    },
    {
        "id": "doc5",
        "title": "Human-in-the-loop requirement",
        "text": (
            "Automated stop actions on cloud resources should always be "
            "confirmed by a human before execution unless the organization "
            "has explicitly enabled fully automatic remediation for very "
            "low-risk, well-understood cases. This avoids accidental "
            "disruption of resources that appear idle but are actually "
            "still needed."
        )
    },
]
