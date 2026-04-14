"""バリデータのテスト。"""

from __future__ import annotations

import pytest

from runtime.validator import ValidationError, validate_input, validate_output

STRING_SCHEMA = {
    "type": "object",
    "properties": {"value": {"type": "string"}},
    "required": ["value"],
}


class TestValidateInput:
    def test_valid_input_passes(self) -> None:
        validate_input(STRING_SCHEMA, {"value": "hello"})

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError, match="input"):
            validate_input(STRING_SCHEMA, {})

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(ValidationError, match="input"):
            validate_input(STRING_SCHEMA, {"value": 123})

    def test_extra_field_allowed_by_default(self) -> None:
        # additionalProperties が未定義の場合は追加フィールドを許可
        validate_input(STRING_SCHEMA, {"value": "ok", "extra": "ignored"})

    def test_invalid_schema_raises_validation_error(self) -> None:
        bad_schema = {"type": "INVALID_TYPE"}
        with pytest.raises(ValidationError):
            validate_input(bad_schema, {"value": "test"})


class TestValidateOutput:
    def test_valid_output_passes(self) -> None:
        schema = {"type": "object", "properties": {"result": {"type": "integer"}}}
        validate_output(schema, {"result": 42})

    def test_wrong_type_raises(self) -> None:
        schema = {
            "type": "object",
            "properties": {"result": {"type": "integer"}},
            "required": ["result"],
        }
        with pytest.raises(ValidationError, match="output"):
            validate_output(schema, {"result": "not_an_int"})

    def test_empty_schema_accepts_any_object(self) -> None:
        validate_output({"type": "object"}, {"anything": True})


class TestValidationError:
    def test_error_has_path(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_input(STRING_SCHEMA, {"value": 99})
        assert exc_info.value.path != ""
