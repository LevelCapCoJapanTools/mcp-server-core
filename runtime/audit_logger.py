"""監査ログ — 全ツール実行を記録する構造化ロガー。"""

from __future__ import annotations

import logging
from typing import Any

from runtime.models import ExecutionResult

_AUDIT_LOGGER_NAME = "mcp.audit"

logger = logging.getLogger(_AUDIT_LOGGER_NAME)


def setup_audit_logging(level: int = logging.INFO) -> None:
    """監査ロガーの基本設定を行う。

    アプリケーション起動時に一度呼び出す。すでにハンドラが設定済みの場合は
    重複設定を避けるためスキップする。

    Args:
        level: ログレベル（デフォルト INFO）。
    """
    audit = logging.getLogger(_AUDIT_LOGGER_NAME)
    if audit.handlers:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    audit.addHandler(handler)
    audit.setLevel(level)
    audit.propagate = False


def log_execution(result: ExecutionResult, extra: dict[str, Any] | None = None) -> None:
    """ツール実行結果を監査ログに記録する。

    Secrets や PII を含む可能性がある入力は記録しない。
    実行結果のステータスと所要時間のみを記録する。

    Args:
        result: ExecutionResult インスタンス。
        extra: 追加のコンテキスト情報（オプション）。Secrets/PII を含めないこと。
    """
    context: dict[str, Any] = {
        "tool": result.tool_name,
        "status": result.status.value,
        "elapsed_seconds": round(result.elapsed_seconds, 4),
    }
    if extra:
        context.update(extra)
    if result.error_message:
        context["error"] = result.error_message

    if result.succeeded:
        logger.info("EXECUTION_COMPLETE %s", _format(context))
    else:
        logger.warning("EXECUTION_FAILED %s", _format(context))


def _format(context: dict[str, Any]) -> str:
    """コンテキスト辞書をログ用の文字列に変換する。"""
    return " ".join(f"{k}={v!r}" for k, v in context.items())
