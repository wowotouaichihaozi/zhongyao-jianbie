"""Shared domain exceptions used across HTTP and service modules."""


class LearningProfileRequiredError(ValueError):
    """Raised when a profile-driven operation has no active profile."""
