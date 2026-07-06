"""Shared Markdown rendering helpers for generated reports."""

from __future__ import annotations


def render_table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def render_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)
