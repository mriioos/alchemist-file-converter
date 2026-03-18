class ConversionError(Exception):
    """Raised when a file conversion fails."""


class TaskNotFoundError(Exception):
    """Raised when a task ID is not found."""


class TaskNotReadyError(Exception):
    """Raised when trying to download a task that hasn't completed."""


class TaskExpiredError(Exception):
    """Raised when a task's output has been cleaned up."""


class UnsupportedMimeTypeError(Exception):
    """Raised when the uploaded file's MIME type doesn't match the converter."""

    def __init__(self, expected: list[str], got: str):
        self.expected = expected
        self.got = got
        super().__init__(f"Expected {expected}, got {got}")


class FileTooLargeError(Exception):
    """Raised when the uploaded file exceeds the size limit."""
