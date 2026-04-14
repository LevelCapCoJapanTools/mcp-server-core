"""ツールレジストリ — 登録済みツールの管理と検索。"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from runtime.models import ToolDefinition

logger = logging.getLogger(__name__)

# ツールハンドラの型: 入力 dict を受け取り、出力 dict を返す同期関数
ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """登録済みツールの一覧を管理するレジストリ。

    - カタログディレクトリ（JSON ファイル群）からツール定義を読み込む。
    - ハンドラ関数を登録し、Executor から参照可能にする。
    - 未登録ツールへのアクセスは KeyError を送出する。
    """

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    # ------------------------------------------------------------------
    # 登録
    # ------------------------------------------------------------------

    def register(
        self,
        definition: ToolDefinition,
        handler: ToolHandler,
    ) -> None:
        """ツール定義とハンドラ関数を登録する。

        Args:
            definition: ToolDefinition インスタンス。
            handler: 入力 dict を受け取り出力 dict を返す呼び出し可能オブジェクト。

        Raises:
            ValueError: ツールが無効化されている場合。
        """
        if not definition.enabled:
            raise ValueError(
                f"ツール '{definition.name}' は無効化されているため登録できません"
            )
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler
        logger.info(
            "ツールを登録しました: name=%s version=%s",
            definition.name,
            definition.version,
        )

    def load_catalog(self, catalog_dir: Path) -> None:
        """カタログディレクトリから JSON ファイルを読み込み、定義を登録する。

        JSON ファイルには handler フィールドは含まれないため、
        定義のみを内部に保持し、ハンドラは別途 register() で登録すること。

        Args:
            catalog_dir: ツール定義 JSON ファイルを格納するディレクトリ。

        Raises:
            FileNotFoundError: カタログディレクトリが存在しない場合。
        """
        if not catalog_dir.exists():
            raise FileNotFoundError(
                f"カタログディレクトリが見つかりません: {catalog_dir}"
            )
        count = 0
        for json_file in sorted(catalog_dir.glob("*.json")):
            try:
                raw = json_file.read_text(encoding="utf-8")
                data: dict[str, Any] = json.loads(raw)
                definition = _build_definition(data)
                # カタログ読み込み時はハンドラなしで定義だけ保持
                self._definitions[definition.name] = definition
                count += 1
                logger.debug("カタログから定義を読み込みました: %s", json_file.name)
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning(
                    "ツール定義ファイルをスキップしました: %s (%s)", json_file.name, exc
                )
        logger.info("カタログ読み込み完了: %d 件 (dir=%s)", count, catalog_dir)

    # ------------------------------------------------------------------
    # 参照
    # ------------------------------------------------------------------

    def get_definition(self, name: str) -> ToolDefinition:
        """ツール定義を取得する。

        Args:
            name: ツール名。

        Returns:
            ToolDefinition インスタンス。

        Raises:
            KeyError: ツールが登録されていない場合。
        """
        if name not in self._definitions:
            raise KeyError(f"未登録のツールです: '{name}'")
        return self._definitions[name]

    def get_handler(self, name: str) -> ToolHandler:
        """ツールハンドラを取得する。

        Args:
            name: ツール名。

        Returns:
            ToolHandler 呼び出し可能オブジェクト。

        Raises:
            KeyError: ハンドラが登録されていない場合。
        """
        if name not in self._handlers:
            raise KeyError(f"ハンドラが未登録のツールです: '{name}'")
        return self._handlers[name]

    def list_tools(self) -> list[str]:
        """登録済みツール名の一覧を返す（定義のみのツールを含む）。"""
        return sorted(self._definitions.keys())

    def has_handler(self, name: str) -> bool:
        """指定ツールにハンドラが登録されているかどうかを返す。"""
        return name in self._handlers


# ------------------------------------------------------------------
# ヘルパー関数
# ------------------------------------------------------------------


def _build_definition(data: dict[str, Any]) -> ToolDefinition:
    """辞書から ToolDefinition を構築する。

    Args:
        data: JSON パース済みの辞書。

    Returns:
        ToolDefinition インスタンス。

    Raises:
        KeyError: 必須フィールドが存在しない場合。
        ValueError: フィールド値が不正な場合。
    """
    return ToolDefinition(
        name=data["name"],
        version=data.get("version", "1.0.0"),
        description=data.get("description", ""),
        input_schema=data["input_schema"],
        output_schema=data.get("output_schema", {"type": "object"}),
        timeout_seconds=int(data.get("timeout_seconds", 30)),
        enabled=bool(data.get("enabled", True)),
    )
