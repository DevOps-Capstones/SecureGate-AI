def evaluate_security_gate(secrets_count: int, critical_count: int) -> dict[str, bool]:
    return {
        "deployment_approved": secrets_count == 0 and critical_count == 0,
    }
