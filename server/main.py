"""MCPServer — MCP実行基盤のサーバークラス。

実行フロー:
1. tool名を受け取る
2. 入力を検証
3. tool定義をロード
4. 実行
5. 出力を検証
6. ログ記録
7. 結果返却
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from runtime.audit_logger import setup_audit_logging
from runtime.executor import Executor
from runtime.models import ExecutionResult, ToolDefinition
from runtime.registry import ToolHandler, ToolRegistry

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP ツール実行基盤サーバー。

    登録済みツールのみを実行可能にし、全実行を監査ログに記録する。
    任意コマンドの実行および未登録ツールの実行は禁止する。

    使用例::

        server = MCPServer()
        server.register_tool(definition, handler)
        result = server.call("my_tool", {"param": "value"})
    """

    def __init__(self, catalog_dir: Path | None = None) -> None:
        """MCPServer を初期化する。

        Args:
            catalog_dir: ツール定義 JSON ファイルを格納するディレクトリ（省略可）。
                         指定した場合、起動時に定義を読み込む。
        """
        setup_audit_logging()
        self._registry = ToolRegistry()
        self._executor = Executor(self._registry)
        if catalog_dir is not None:
            self._registry.load_catalog(catalog_dir)
        logger.info("MCPServer を初期化しました (catalog_dir=%s)", catalog_dir)

    def register_tool(
        self,
        definition: ToolDefinition,
        handler: ToolHandler,
    ) -> None:
        """ツール定義とハンドラ関数を登録する。

        Args:
            definition: ToolDefinition インスタンス。
            handler: 入力 dict を受け取り出力 dict を返す呼び出し可能オブジェクト。
        """
        self._registry.register(definition, handler)

    def call(
        self,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> ExecutionResult:
        """ツールを呼び出す。

        Args:
            tool_name: 実行するツール名。
            input_data: ツールへの入力辞書。

        Returns:
            ExecutionResult インスタンス（成功・失敗問わず常に返す）。
        """
        return self._executor.execute(tool_name, input_data)

    def list_tools(self) -> list[str]:
        """登録済みツール名の一覧を返す。"""
        return self._registry.list_tools()
