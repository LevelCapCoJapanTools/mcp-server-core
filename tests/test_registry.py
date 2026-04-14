"""ToolRegistry のテスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runtime.models import ToolDefinition
from runtime.registry import ToolRegistry

# ------------------------------------------------------------------
# フィクスチャ
# ------------------------------------------------------------------


@pytest.fixture
def simple_definition() -> ToolDefinition:
    return ToolDefinition(
        name="echo",
        version="1.0.0",
        description="入力をそのまま返す",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
        output_schema={
            "type": "object",
            "properties": {"result": {"type": "string"}},
        },
        timeout_seconds=10,
    )


def echo_handler(data: dict[str, Any]) -> dict[str, Any]:
    return {"result": data["message"]}


# ------------------------------------------------------------------
# register / get_definition / get_handler
# ------------------------------------------------------------------


class TestRegister:
    def test_register_success(self, simple_definition: ToolDefinition) -> None:
        registry = ToolRegistry()
        registry.register(simple_definition, echo_handler)
        assert "echo" in registry.list_tools()

    def test_get_definition_returns_same_object(
        self, simple_definition: ToolDefinition
    ) -> None:
        registry = ToolRegistry()
        registry.register(simple_definition, echo_handler)
        assert registry.get_definition("echo") is simple_definition

    def test_get_handler_returns_callable(
        self, simple_definition: ToolDefinition
    ) -> None:
        registry = ToolRegistry()
        registry.register(simple_definition, echo_handler)
        handler = registry.get_handler("echo")
        assert callable(handler)

    def test_register_disabled_tool_raises(self) -> None:
        disabled = ToolDefinition(
            name="disabled_tool",
            version="1.0.0",
            description="",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            enabled=False,
        )
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="無効化"):
            registry.register(disabled, lambda d: d)

    def test_get_definition_unknown_raises_key_error(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="未登録"):
            registry.get_definition("unknown")

    def test_get_handler_unknown_raises_key_error(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="ハンドラが未登録"):
            registry.get_handler("unknown")


# ------------------------------------------------------------------
# list_tools
# ------------------------------------------------------------------


class TestListTools:
    def test_list_tools_empty(self) -> None:
        assert ToolRegistry().list_tools() == []

    def test_list_tools_sorted(self, simple_definition: ToolDefinition) -> None:
        registry = ToolRegistry()
        for name in ["zoo", "apple", "mango"]:
            defn = ToolDefinition(
                name=name,
                version="1.0.0",
                description="",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )
            registry.register(defn, lambda d: d)
        assert registry.list_tools() == ["apple", "mango", "zoo"]


# ------------------------------------------------------------------
# load_catalog
# ------------------------------------------------------------------


class TestLoadCatalog:
    def test_load_catalog_reads_json_files(self, tmp_path: Path) -> None:
        tool_data = {
            "name": "greet",
            "version": "1.0.0",
            "description": "挨拶",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        }
        (tmp_path / "greet.json").write_text(json.dumps(tool_data), encoding="utf-8")
        registry = ToolRegistry()
        registry.load_catalog(tmp_path)
        assert "greet" in registry.list_tools()

    def test_load_catalog_skips_invalid_json(self, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("NOT_JSON", encoding="utf-8")
        registry = ToolRegistry()
        registry.load_catalog(tmp_path)
        assert registry.list_tools() == []

    def test_load_catalog_missing_dir_raises(self, tmp_path: Path) -> None:
        registry = ToolRegistry()
        with pytest.raises(FileNotFoundError):
            registry.load_catalog(tmp_path / "nonexistent")

    def test_load_catalog_skips_missing_required_field(self, tmp_path: Path) -> None:
        # input_schema が欠けている
        bad_data = {"name": "no_schema", "version": "1.0.0"}
        (tmp_path / "no_schema.json").write_text(json.dumps(bad_data), encoding="utf-8")
        registry = ToolRegistry()
        registry.load_catalog(tmp_path)
        assert registry.list_tools() == []


# ------------------------------------------------------------------
# has_handler
# ------------------------------------------------------------------


class TestHasHandler:
    def test_has_handler_true_after_register(
        self, simple_definition: ToolDefinition
    ) -> None:
        registry = ToolRegistry()
        registry.register(simple_definition, echo_handler)
        assert registry.has_handler("echo") is True

    def test_has_handler_false_after_catalog_load(self, tmp_path: Path) -> None:
        tool_data = {
            "name": "catalog_tool",
            "version": "1.0.0",
            "input_schema": {"type": "object"},
        }
        (tmp_path / "catalog_tool.json").write_text(
            json.dumps(tool_data), encoding="utf-8"
        )
        registry = ToolRegistry()
        registry.load_catalog(tmp_path)
        # カタログ読み込みのみではハンドラは登録されない
        assert registry.has_handler("catalog_tool") is False
