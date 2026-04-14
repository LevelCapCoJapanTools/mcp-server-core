"""データモデル定義 — ToolDefinition / ExecutionResult。"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ExecutionStatus(enum.Enum):
    """ツール実行の結果ステータス。"""

    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True)
class ToolDefinition:
    """登録済みツールの定義。

    Attributes:
        name: ツール識別子（一意）。
        version: セマンティックバージョン文字列。
        description: ツールの説明。
        input_schema: JSON Schema オブジェクト（入力検証用）。
        output_schema: JSON Schema オブジェクト（出力検証用）。
        timeout_seconds: 実行タイムアウト秒数（デフォルト 30 秒）。
        enabled: False の場合は実行禁止。
    """

    name: str
    version: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_seconds: int = 30
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name は空にできません")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds は正の整数である必要があります")


@dataclass
class ExecutionResult:
    """ツール実行の結果。

    Attributes:
        tool_name: 実行したツール名。
        status: 実行ステータス。
        output: 実行出力（成功時）。
        error_message: エラーメッセージ（失敗時）。
        elapsed_seconds: 実行所要時間（秒）。
    """

    tool_name: str
    status: ExecutionStatus
    output: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    elapsed_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        """成功かどうかを返す。"""
        return self.status == ExecutionStatus.SUCCESS
