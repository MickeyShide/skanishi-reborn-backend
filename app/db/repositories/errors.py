# app/repositories/errors.py


class RepositoryError(Exception):
    """Base repository error."""


class ObjectNotFoundError(RepositoryError):
    """Object was not found."""


class MultipleObjectsFoundError(RepositoryError):
    """Expected one object, got multiple."""
