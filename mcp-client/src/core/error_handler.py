"""Centralized error handling and custom exception definitions.

This module provides a hierarchy of custom exceptions and error recovery patterns
for the agentics system, including graceful fallbacks and proper logging.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from src.core.logger import logger


class ErrorSeverity(StrEnum):
    """Severity levels for error reporting."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AgenticsError(Exception):
    """Base exception for all agentics-specific errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AgenticsError.

        Args:
            message: Human-readable error message
            severity: Severity level of the error
            error_code: Machine-readable error code for routing/tracking
            details: Additional context as a dictionary
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "details": self.details,
        }

    def to_user_message(self) -> str:
        """Return a user-friendly error message."""
        return self.message


class ToolError(AgenticsError):
    """Error from tool invocation or execution failure."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        retryable: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize ToolError.

        Args:
            message: Error description
            tool_name: Name of the tool that failed
            retryable: Whether the error is retryable
            **kwargs: Additional arguments passed to AgenticsError
        """
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        self.retryable = retryable

    def to_user_message(self) -> str:
        """Return user-friendly error message."""
        if self.tool_name:
            return f"Tool '{self.tool_name}' encountered an issue: {self.message}"
        return f"A tool encountered an issue: {self.message}"


class AgentError(AgenticsError):
    """Error from agent execution or decision-making."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize AgentError.

        Args:
            message: Error description
            agent_name: Name of the agent that failed
            **kwargs: Additional arguments passed to AgenticsError
        """
        super().__init__(message, **kwargs)
        self.agent_name = agent_name

    def to_user_message(self) -> str:
        """Return user-friendly error message."""
        if self.agent_name:
            return f"Agent '{self.agent_name}' encountered an issue: {self.message}"
        return f"An agent encountered an issue: {self.message}"


class DatabaseError(AgenticsError):
    """Error from database operations."""

    def __init__(
        self,
        message: str,
        retryable: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize DatabaseError.

        Args:
            message: Error description
            retryable: Whether the operation can be retried
            **kwargs: Additional arguments passed to AgenticsError
        """
        super().__init__(message, **kwargs)
        self.retryable = retryable

    def to_user_message(self) -> str:
        """Return user-friendly error message."""
        return (
            "Database operation failed. Please try again later."
            if self.retryable
            else "A persistent database error occurred."
        )


class LLMError(AgenticsError):
    """Error from LLM provider."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        retryable: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize LLMError.

        Args:
            message: Error description
            provider: LLM provider name (e.g., 'azure', 'google')
            retryable: Whether the call can be retried
            **kwargs: Additional arguments passed to AgenticsError
        """
        super().__init__(message, **kwargs)
        self.provider = provider
        self.retryable = retryable

    def to_user_message(self) -> str:
        """Return user-friendly error message."""
        return (
            "The AI model is temporarily unavailable. Please try again."
            if self.retryable
            else "Unable to reach the AI model. Please try again later."
        )


class ValidationError(AgenticsError):
    """Error from input validation."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ValidationError.

        Args:
            message: Error description
            field: Field that failed validation
            **kwargs: Additional arguments passed to AgenticsError
        """
        super().__init__(message, severity=ErrorSeverity.LOW, **kwargs)
        self.field = field

    def to_user_message(self) -> str:
        """Return user-friendly error message."""
        if self.field:
            return f"Invalid input for '{self.field}': {self.message}"
        return f"Invalid input: {self.message}"


class ConfigError(AgenticsError):
    """Error from configuration issues."""

    def __init__(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Initialize ConfigError.

        Args:
            message: Error description
            **kwargs: Additional arguments passed to AgenticsError
        """
        super().__init__(
            message, severity=ErrorSeverity.CRITICAL, **kwargs
        )

    def to_user_message(self) -> str:
        """Return user-friendly error message."""
        return "System configuration error. Please contact support."


def log_error(
    error: Exception,
    context: dict[str, Any] | None = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
) -> None:
    """Log error with context information.

    Args:
        error: The exception to log
        context: Additional context to include in logs
        severity: Severity level for the log
    """
    error_data = {
        "error_type": error.__class__.__name__,
        "message": str(error),
        "severity": severity.value,
    }

    if isinstance(error, AgenticsError):
        error_data.update(error.to_dict())

    if context:
        error_data["context"] = context

    log_message = json.dumps(error_data, default=str)

    if severity == ErrorSeverity.CRITICAL:
        logger.error(log_message)
    elif severity == ErrorSeverity.HIGH:
        logger.error(log_message)
    elif severity == ErrorSeverity.MEDIUM:
        logger.warning(log_message)
    elif severity == ErrorSeverity.LOW:
        logger.info(log_message)
    else:
        logger.info(log_message)


async def handle_tool_failure(
    tool_name: str,
    error: Exception,
    fallback_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Handle tool failure with logging and optional fallback.

    Args:
        tool_name: Name of the tool that failed
        error: The exception raised
        fallback_result: Optional fallback result to return

    Returns:
        Result dictionary with status and error info
    """
    log_error(
        error,
        context={"tool_name": tool_name},
        severity=ErrorSeverity.HIGH,
    )

    if fallback_result is not None:
        return {
            "status": "fallback",
            "tool_name": tool_name,
            "error": str(error),
            "data": fallback_result,
        }

    return {
        "status": "error",
        "tool_name": tool_name,
        "error": str(error),
        "retryable": (
            True
            if isinstance(error, (ToolError, DatabaseError, LLMError))
            and getattr(error, "retryable", True)
            else False
        ),
    }
