"""Minimal YAML loader supporting the subset used in this project."""
from __future__ import annotations

import shlex
from typing import Any, List, Tuple


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    result_chars = []
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == "#" and not in_single and not in_double:
            break
        result_chars.append(ch)
    return "".join(result_chars).rstrip()


def _tokenize(text: str) -> List[Tuple[int, str]]:
    tokens: List[Tuple[int, str]] = []
    for raw_line in text.splitlines():
        cleaned = _strip_comment(raw_line)
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        tokens.append((indent, cleaned.strip()))
    return tokens


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        lexer = shlex.shlex(inner, posix=True)
        lexer.whitespace = ","
        lexer.whitespace_split = True
        lexer.quotes = '"'
        return [token.strip() for token in lexer if token.strip()]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _parse_sequence(tokens: List[Tuple[int, str]], start: int, parent_indent: int) -> Tuple[List[Any], int]:
    items: List[Any] = []
    i = start
    while i < len(tokens):
        indent, content = tokens[i]
        if indent <= parent_indent:
            break
        if not content.startswith("- "):
            break
        item_value = content[2:].strip()
        items.append(_parse_scalar(item_value))
        i += 1
    return items, i


def _parse_mapping(tokens: List[Tuple[int, str]], start: int, parent_indent: int) -> Tuple[dict, int]:
    mapping: dict[str, Any] = {}
    i = start
    while i < len(tokens):
        indent, content = tokens[i]
        if indent <= parent_indent:
            break
        if content.startswith("- "):
            raise ValueError("Unexpected list item inside mapping without key")
        if ":" not in content:
            raise ValueError(f"Invalid line: {content!r}")
        key, remainder = content.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()
        if not remainder:
            next_index = i + 1
            if next_index < len(tokens) and tokens[next_index][0] > indent:
                next_indent = tokens[next_index][0]
                next_content = tokens[next_index][1]
                if next_content.startswith("- "):
                    value, i = _parse_sequence(tokens, next_index, indent)
                else:
                    value, i = _parse_mapping(tokens, next_index, indent)
            else:
                value = None
                i += 1
        else:
            value = _parse_scalar(remainder)
            i += 1
        mapping[key] = value
    return mapping, i


def safe_load(stream: Any) -> Any:
    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = str(stream)
    tokens = _tokenize(text)
    mapping, index = _parse_mapping(tokens, 0, -1)
    if index != len(tokens):
        raise ValueError("Did not consume entire document")
    return mapping


def dump(data: Any) -> str:
    raise NotImplementedError("Only safe_load is implemented in this minimal loader")
