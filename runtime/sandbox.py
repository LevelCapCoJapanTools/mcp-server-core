"""サンドボックス — ツール実行を隔離するコンテキストマネージャ。"""

from __future__ import annotations

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)


class SandboxViolationError(Exception):
    """サンドボックス制約違反が発生した場合に送出される例外。"""


@contextmanager
def sandbox_context(tool_name: str) -> Generator[None, None, None]:
    """ツール実行を隔離するコンテキストマネージャ。

    現在の実装ではリソース使用量の記録と実行フェーズのログを提供する。
    将来的に seccomp / chroot などの実行隔離層を追加可能な設計にする。

    Args:
        tool_name: 実行するツール名（ログ用）。

    Yields:
        None。

    Raises:
        SandboxViolationError: サンドボックス制約に違反した場合。
    """
    start = time.monotonic()
    logger.info("サンドボックス開始: tool=%s", tool_name)
    try:
        yield
    except SandboxViolationError:
        raise
    except Exception:
        # サンドボックス外へ例外を透過させる
        raise
    finally:
        elapsed = time.monotonic() - start
        logger.info("サンドボックス終了: tool=%s elapsed=%.3fs", tool_name, elapsed)


def check_output_size(output: dict[str, Any], max_bytes: int = 1_048_576) -> None:
    """出力サイズ上限チェック。

    Args:
        output: 検証対象の出力辞書。
        max_bytes: 許容する最大バイト数（デフォルト 1 MiB）。

    Raises:
        SandboxViolationError: 出力が上限を超えた場合。
    """
    import json

    encoded = json.dumps(output, ensure_ascii=False).encode("utf-8")
    if len(encoded) > max_bytes:
        raise SandboxViolationError(
            f"出力サイズが上限を超えています: {len(encoded)} bytes > {max_bytes} bytes"
        )
