"""Executor のテスト。"""

from __future__ import annotations

import time
from typing import Any

from runtime.executor import Executor
from runtime.models import ExecutionStatus, ToolDefinition
from runtime.registry import ToolRegistry

# ------------------------------------------------------------------
# フィクスチャ
# ------------------------------------------------------------------

INPUT_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"result": {"type": "string"}},
    "required": ["result"],
}


def _make_registry(
    name: str = "echo",
    timeout_seconds: int = 10,
    handler: Any = None,
) -> ToolRegistry:
    if handler is None:

        def handler(data: dict[str, Any]) -> dict[str, Any]:
            return {"result": data["message"]}

    registry = ToolRegistry()
    definition = ToolDefinition(
        name=name,
        version="1.0.0",
        description="テスト用ツール",
        input_schema=INPUT_SCHEMA,
        output_schema=OUTPUT_SCHEMA,
        timeout_seconds=timeout_seconds,
    )
    registry.register(definition, handler)
    return registry


# ------------------------------------------------------------------
# 正常系
# ------------------------------------------------------------------


class TestExecutorSuccess:
    def test_execute_returns_success(self) -> None:
        executor = Executor(_make_registry())
        result = executor.execute("echo", {"message": "hello"})
        assert result.succeeded
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output == {"result": "hello"}

    def test_elapsed_seconds_is_positive(self) -> None:
        executor = Executor(_make_registry())
        result = executor.execute("echo", {"message": "test"})
        assert result.elapsed_seconds >= 0


# ------------------------------------------------------------------
# 未登録ツール
# ------------------------------------------------------------------


class TestExecutorNotFound:
    def test_unknown_tool_returns_not_found(self) -> None:
        executor = Executor(ToolRegistry())
        result = executor.execute("nonexistent", {})
        assert result.status == ExecutionStatus.NOT_FOUND
        assert not result.succeeded

    def test_tool_without_handler_returns_not_found(self) -> None:
        # カタログに定義はあるがハンドラなし
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            tool_data = {
                "name": "no_handler",
                "version": "1.0.0",
                "input_schema": INPUT_SCHEMA,
                "output_schema": OUTPUT_SCHEMA,
            }
            (Path(td) / "no_handler.json").write_text(
                json.dumps(tool_data), encoding="utf-8"
            )
            registry = ToolRegistry()
            registry.load_catalog(Path(td))
            executor = Executor(registry)
            result = executor.execute("no_handler", {"message": "hi"})
        assert result.status == ExecutionStatus.NOT_FOUND


# ------------------------------------------------------------------
# バリデーションエラー
# ------------------------------------------------------------------


class TestExecutorValidationError:
    def test_invalid_input_returns_validation_error(self) -> None:
        executor = Executor(_make_registry())
        result = executor.execute("echo", {"message": 999})
        assert result.status == ExecutionStatus.VALIDATION_ERROR
        assert not result.succeeded

    def test_missing_required_input_returns_validation_error(self) -> None:
        executor = Executor(_make_registry())
        result = executor.execute("echo", {})
        assert result.status == ExecutionStatus.VALIDATION_ERROR

    def test_invalid_output_returns_validation_error(self) -> None:
        def bad_handler(data: dict[str, Any]) -> dict[str, Any]:
            # 出力スキーマに違反: result が int でなく返す
            return {"result": 12345}

        # result は string で required のはずなのに int を返す
        registry = _make_registry(handler=bad_handler)
        # OUTPUT_SCHEMA は result: string で required なのに int を返す
        executor = Executor(registry)
        result = executor.execute("echo", {"message": "test"})
        assert result.status == ExecutionStatus.VALIDATION_ERROR


# ------------------------------------------------------------------
# タイムアウト
# ------------------------------------------------------------------


class TestExecutorTimeout:
    def test_timeout_returns_timeout_status(self) -> None:
        def slow_handler(data: dict[str, Any]) -> dict[str, Any]:
            time.sleep(10)
            return {"result": "done"}

        executor = Executor(_make_registry(timeout_seconds=1, handler=slow_handler))
        result = executor.execute("echo", {"message": "slow"})
        assert result.status == ExecutionStatus.TIMEOUT
        assert not result.succeeded


# ------------------------------------------------------------------
# 実行エラー
# ------------------------------------------------------------------


class TestExecutorExecutionError:
    def test_handler_exception_returns_execution_error(self) -> None:
        def failing_handler(data: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("意図的な実行エラー")

        executor = Executor(_make_registry(handler=failing_handler))
        result = executor.execute("echo", {"message": "test"})
        assert result.status == ExecutionStatus.EXECUTION_ERROR
        assert not result.succeeded
