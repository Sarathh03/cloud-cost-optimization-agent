"""
GUARDRAILS
--------------
Safety checks that sit between "the agent wants to act" and "AWS actually
gets called." Even a well-reasoning agent should never be fully trusted
with irreversible actions - guardrails are the seatbelt.

These are deliberately simple and explicit (not another LLM call), because
guardrails should be predictable and impossible for the model to talk its
way around.
"""

MAX_ACTIONS_PER_RUN = 3  # circuit breaker: refuse to act more than N times per run
_actions_this_run = {"count": 0}  # simple in-memory counter, resets each process run


class GuardrailViolation(Exception):
    """Raised when a proposed action fails a safety check."""
    pass


def is_protected_instance(instance: dict) -> bool:
    """
    Checks for a 'do_not_stop' tag. If a team wants to permanently
    exempt an instance (e.g. a shared dev box), this is how they'd do it.
    NOTE: get_real_instances() would need to be extended to include raw
    tags for this to see anything beyond training_status - see note in
    step3_aws_real_data.py.
    """
    return instance.get("do_not_stop", False) is True


def validate_tool_call(instance: dict, instance_id: str, reason: str) -> None:
    """
    Runs all guardrail checks before allowing act_node to actually call
    AWS. Raises GuardrailViolation if any check fails; callers should
    catch this and treat it as "do not act."
    """
    # 1. The instance_id the LLM wants to act on must match the instance
    #    we actually fetched from AWS - this catches hallucinated IDs.
    if instance_id != instance["instance_id"]:
        raise GuardrailViolation(
            f"Instance ID mismatch: agent referenced '{instance_id}' but "
            f"the instance under review is '{instance['instance_id']}'."
        )

    # 2. Never act on an explicitly protected instance
    if is_protected_instance(instance):
        raise GuardrailViolation(
            f"Instance {instance_id} is tagged do_not_stop - refusing to act."
        )

    # 3. Reject empty or suspiciously short reasoning - a real decision
    #    should be justified, not a one-word stub.
    if not reason or len(reason.strip()) < 15:
        raise GuardrailViolation(
            "Reasoning is missing or too short to justify an action."
        )

    # 4. Never act on an instance that isn't actually running
    #    (defensive check - stopping an already-stopped instance is
    #    harmless but signals the agent's data may be stale).
    if instance["state"] != "running":
        raise GuardrailViolation(
            f"Instance {instance_id} is not in 'running' state "
            f"(currently '{instance['state']}') - refusing to act."
        )

    # 5. Circuit breaker - cap how many real actions this process will
    #    take in one run, regardless of how many instances are flagged.
    if _actions_this_run["count"] >= MAX_ACTIONS_PER_RUN:
        raise GuardrailViolation(
            f"Reached the maximum of {MAX_ACTIONS_PER_RUN} actions for this "
            f"run - remaining proposals require a fresh run to reduce blast radius."
        )


def record_action_taken():
    """Call this AFTER a real action succeeds, to advance the circuit breaker."""
    _actions_this_run["count"] += 1
