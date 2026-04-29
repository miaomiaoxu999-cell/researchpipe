"""SDK exception types — all carry hint_for_agent so LLM callers can recover."""
from __future__ import annotations

from typing import Any


class ResearchPipeError(Exception):
    """Base error.

    Attributes:
      code:    machine-readable error code (e.g. 'rate_limit_exceeded').
      message: human-readable message.
      hint_for_agent: copy that an LLM agent can read to decide next action.
      documentation_url: URL with details.
      status_code: HTTP status when the error came from the server.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "unknown",
        hint_for_agent: str | None = None,
        documentation_url: str | None = None,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
        raw: Any | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint_for_agent = hint_for_agent
        self.documentation_url = documentation_url
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.raw = raw

    @classmethod
    def from_response_body(cls, body: dict, *, status_code: int):
        err = body.get("error") or body.get("detail") or {}
        if not isinstance(err, dict):
            err = {"message": str(err)}
        msg = err.get("message", "unknown error")
        code = err.get("code", "unknown")
        klass = _ERROR_MAP.get(code, cls) if status_code != 429 else RateLimitError
        return klass(
            msg,
            code=code,
            hint_for_agent=err.get("hint_for_agent"),
            documentation_url=err.get("documentation_url"),
            status_code=status_code,
            retry_after_seconds=err.get("retry_after_seconds"),
            raw=body,
        )


class AuthError(ResearchPipeError):
    pass


class RateLimitError(ResearchPipeError):
    pass


class CreditsExceededError(ResearchPipeError):
    pass


class ValidationError(ResearchPipeError):
    pass


class UpstreamError(ResearchPipeError):
    pass


class NotFoundError(ResearchPipeError):
    pass


_ERROR_MAP: dict[str, type[ResearchPipeError]] = {
    "auth_invalid": AuthError,
    "rate_limit_exceeded": RateLimitError,
    "credits_exceeded": CreditsExceededError,
    "validation_failed": ValidationError,
    "upstream_failure": UpstreamError,
    "upstream_timeout": UpstreamError,
    "quota_resource_not_found": NotFoundError,
}
