class BrazenError(Exception):
    """Base error for deterministic, user-actionable failures."""


class ValidationError(BrazenError, ValueError):
    """Raised when a contract or invariant is violated."""

    def __init__(self, message: str, *, path: str | None = None):
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)


class GateFailure(BrazenError):
    """Raised when a binary engineering gate fails."""
