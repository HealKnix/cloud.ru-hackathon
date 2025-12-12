class PlanParseError(Exception):
    """Raised when LLM plan cannot be parsed."""


class LLMClientError(Exception):
    """Raised when the LLM request fails."""


class ODataClientError(Exception):
    """Raised when OData call fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: object | None = None,
        url: str | None = None,
        elapsed_ms: int | None = None,
        params: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.url = url
        self.elapsed_ms = elapsed_ms
        self.params = params
