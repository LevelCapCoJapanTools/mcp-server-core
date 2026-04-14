"""入出力バリデータ — JSON Schema を用いた入力・出力の検証。"""

from __future__ import annotations

import logging
from typing import Any

import jsonschema
import jsonschema.exceptions

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """入力または出力が JSON Schema に違反した場合に送出される例外。"""

    def __init__(self, message: str, path: str = "") -> None:
        super().__init__(message)
        self.path = path


def validate_input(schema: dict[str, Any], data: dict[str, Any]) -> None:
    """入力データをスキーマに対して検証する。

    Args:
        schema: JSON Schema オブジェクト（ToolDefinition.input_schema）。
        data: 検証対象の入力辞書。

    Raises:
        ValidationError: スキーマ違反が発見された場合。
    """
    _validate(schema, data, phase="input")


def validate_output(schema: dict[str, Any], data: dict[str, Any]) -> None:
    """出力データをスキーマに対して検証する。

    Args:
        schema: JSON Schema オブジェクト（ToolDefinition.output_schema）。
        data: 検証対象の出力辞書。

    Raises:
        ValidationError: スキーマ違反が発見された場合。
    """
    _validate(schema, data, phase="output")


def _validate(schema: dict[str, Any], data: dict[str, Any], phase: str) -> None:
    """内部バリデーション処理。

    Args:
        schema: JSON Schema オブジェクト。
        data: 検証対象の辞書。
        phase: "input" または "output"（ログ用）。

    Raises:
        ValidationError: スキーマ違反が発見された場合。
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
        logger.debug("%s バリデーション成功", phase)
    except jsonschema.exceptions.ValidationError as exc:
        path = (
            " -> ".join(str(p) for p in exc.absolute_path)
            if exc.absolute_path
            else "root"
        )
        message = f"{phase} バリデーション失敗: {exc.message} (path: {path})"
        logger.warning(message)
        raise ValidationError(message, path=path) from exc
    except jsonschema.exceptions.SchemaError as exc:
        message = f"スキーマ定義が不正です ({phase}): {exc.message}"
        logger.error(message)
        raise ValidationError(message) from exc
