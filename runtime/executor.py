"""エグゼキュータ — ツール実行パイプラインの制御。

実行フロー:
1. tool名を受け取る
2. 入力を検証
3. tool定義をロード
4. サンドボックス内で実行（タイムアウト付き）
5. 出力を検証
6. ログ記録
7. 結果返却
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from typing import Any

from runtime.audit_logger import log_execution
from runtime.models import ExecutionResult, ExecutionStatus
from runtime.registry import ToolRegistry
from runtime.sandbox import SandboxViolationError, check_output_size, sandbox_context
from runtime.validator import ValidationError, validate_input, validate_output

logger = logging.getLogger(__name__)


class Executor:
    """ツールの実行パイプラインを制御するクラス。

    登録済みツールのみ実行可能。未登録ツールや無効化されたツールは拒否する。
    """

    def __init__(self, registry: ToolRegistry) -> None:
        """Executor を初期化する。

        Args:
            registry: 使用する ToolRegistry インスタンス。
        """
        self._registry = registry

    def execute(
        self,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> ExecutionResult:
        """ツールを実行し、結果を返す。

        Args:
            tool_name: 実行するツール名。
            input_data: ツールへの入力辞書。

        Returns:
            ExecutionResult インスタンス（成功・失敗問わず常に返す）。
        """
        start = time.monotonic()
        logger.info("実行開始: tool=%s", tool_name)

        # 1. ツール定義のロード（未登録チェック）
        try:
            definition = self._registry.get_definition(tool_name)
        except KeyError as exc:
            elapsed = time.monotonic() - start
            result = ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.NOT_FOUND,
                error_message=str(exc),
                elapsed_seconds=elapsed,
            )
            log_execution(result)
            return result

        # 2. 入力の検証
        try:
            validate_input(definition.input_schema, input_data)
        except ValidationError as exc:
            elapsed = time.monotonic() - start
            result = ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.VALIDATION_ERROR,
                error_message=str(exc),
                elapsed_seconds=elapsed,
            )
            log_execution(result)
            return result

        # 3. ハンドラのロード（ハンドラ未登録チェック）
        try:
            handler = self._registry.get_handler(tool_name)
        except KeyError as exc:
            elapsed = time.monotonic() - start
            result = ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.NOT_FOUND,
                error_message=str(exc),
                elapsed_seconds=elapsed,
            )
            log_execution(result)
            return result

        # 4. サンドボックス内でタイムアウト付き実行
        output: dict[str, Any] = {}
        try:
            with sandbox_context(tool_name):
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(handler, input_data)
                    try:
                        output = future.result(timeout=definition.timeout_seconds)
                    except concurrent.futures.TimeoutError:
                        future.cancel()
                        elapsed = time.monotonic() - start
                        timeout_msg = (
                            f"タイムアウト ({definition.timeout_seconds}s)"
                            " を超過しました"
                        )
                        result = ExecutionResult(
                            tool_name=tool_name,
                            status=ExecutionStatus.TIMEOUT,
                            error_message=timeout_msg,
                            elapsed_seconds=elapsed,
                        )
                        log_execution(result)
                        return result
        except SandboxViolationError as exc:
            elapsed = time.monotonic() - start
            result = ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.EXECUTION_ERROR,
                error_message=f"サンドボックス違反: {exc}",
                elapsed_seconds=elapsed,
            )
            log_execution(result)
            return result
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.exception(
                "ツール実行中に予期しないエラーが発生しました: tool=%s", tool_name
            )
            result = ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.EXECUTION_ERROR,
                error_message=f"実行エラー: {exc}",
                elapsed_seconds=elapsed,
            )
            log_execution(result)
            return result

        # 5. 出力サイズチェック
        try:
            check_output_size(output)
        except SandboxViolationError as exc:
            elapsed = time.monotonic() - start
            result = ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.EXECUTION_ERROR,
                error_message=str(exc),
                elapsed_seconds=elapsed,
            )
            log_execution(result)
            return result

        # 6. 出力の検証
        try:
            validate_output(definition.output_schema, output)
        except ValidationError as exc:
            elapsed = time.monotonic() - start
            result = ExecutionResult(
                tool_name=tool_name,
                status=ExecutionStatus.VALIDATION_ERROR,
                error_message=str(exc),
                elapsed_seconds=elapsed,
            )
            log_execution(result)
            return result

        # 7. 成功
        elapsed = time.monotonic() - start
        result = ExecutionResult(
            tool_name=tool_name,
            status=ExecutionStatus.SUCCESS,
            output=output,
            elapsed_seconds=elapsed,
        )
        log_execution(result)
        logger.info("実行完了: tool=%s elapsed=%.3fs", tool_name, elapsed)
        return result
