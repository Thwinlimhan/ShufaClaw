"""Startup fail-policy helpers isolated from heavy runtime dependencies."""


def enforce_startup_fail_policy(is_production: bool, v2_ready: bool) -> None:
    """Raise when production startup requirements are not met."""
    if is_production and not v2_ready:
        raise RuntimeError("V2 infrastructure is required in production mode")
