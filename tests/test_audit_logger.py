"""監査ロガーのテスト。"""

from __future__ import annotations

import logging

import pytest

from runtime.audit_logger import log_execution, setup_audit_logging
from runtime.models import ExecutionResult, ExecutionStatus


@pytest.fixture(autouse=True)
def reset_audit_logger() -> pytest.Generator[None, None, None]:
    """各テスト前後に監査ロガーの状態をリセットする。"""
    audit = logging.getLogger("mcp.audit")
    original_handlers = list(audit.handlers)
    original_propagate = audit.propagate
    original_level = audit.level
    yield
    audit.handlers = original_handlers
    audit.propagate = original_propagate
    audit.level = original_level


class TestSetupAuditLogging:
    def test_setup_does_not_raise(self) -> None:
        setup_audit_logging()

    def test_setup_idempotent(self) -> None:
        # 2回呼んでも重複ハンドラが追加されないこと
        setup_audit_logging()
        setup_audit_logging()
        audit_logger = logging.getLogger("mcp.audit")
        assert len(audit_logger.handlers) == 1


class TestLogExecution:
    """caplog は propagate=False のロガーを捕捉できないため、
    ハンドラを直接注入してログレコードを検証する。"""

    @pytest.fixture(autouse=True)
    def inject_handler(
        self, caplog: pytest.LogCaptureFixture
    ) -> pytest.Generator[None, None, None]:
        audit = logging.getLogger("mcp.audit")
        audit.setLevel(logging.DEBUG)
        audit.addHandler(caplog.handler)
        yield
        audit.removeHandler(caplog.handler)

    def test_log_success(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="mcp.audit"):
            result = ExecutionResult(
                tool_name="echo",
                status=ExecutionStatus.SUCCESS,
                output={"result": "ok"},
                elapsed_seconds=0.01,
            )
            log_execution(result)
        assert any("EXECUTION_COMPLETE" in r.message for r in caplog.records)

    def test_log_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING, logger="mcp.audit"):
            result = ExecutionResult(
                tool_name="echo",
                status=ExecutionStatus.TIMEOUT,
                error_message="タイムアウト",
                elapsed_seconds=5.0,
            )
            log_execution(result)
        assert any("EXECUTION_FAILED" in r.message for r in caplog.records)

    def test_log_contains_tool_name(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="mcp.audit"):
            result = ExecutionResult(
                tool_name="my_special_tool",
                status=ExecutionStatus.SUCCESS,
                elapsed_seconds=0.1,
            )
            log_execution(result)
        assert any("my_special_tool" in r.message for r in caplog.records)

    def test_log_extra_context(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="mcp.audit"):
            result = ExecutionResult(
                tool_name="echo",
                status=ExecutionStatus.SUCCESS,
                elapsed_seconds=0.001,
            )
            log_execution(result, extra={"request_id": "req-001"})
        assert any("req-001" in r.message for r in caplog.records)
