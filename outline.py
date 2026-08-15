"""文件结构（outline）解析工具。

目前提供：
- 语言识别（按扩展名）
- Python：基于标准库 ast 的类/函数树
- JavaScript / TypeScript：基于行首正则的类/函数/接口/类型声明
- Markdown：标题结构
- 其他语言：轻量正则（可能不够精确，可按需扩展）
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".json": "json",
        ".md": "markdown",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".java": "java",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".sql": "sql",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".vue": "vue",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
    }
    return mapping.get(ext, "text")


def _py_outline(content: str) -> list[dict[str, Any]]:
    try:
        import ast

        tree = ast.parse(content)
    except SyntaxError:
        return []

    nodes: list[dict[str, Any]] = []

    def visit_body(body: list[ast.stmt], depth: int, parent: list[dict[str, Any]]) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                item = {
                    "name": node.name,
                    "kind": "function",
                    "line": node.lineno,
                    "children": [],
                }
                parent.append(item)
                visit_body(node.body, depth + 1, item["children"])
            elif isinstance(node, ast.ClassDef):
                item = {
                    "name": node.name,
                    "kind": "class",
                    "line": node.lineno,
                    "children": [],
                }
                parent.append(item)
                visit_body(node.body, depth + 1, item["children"])

    visit_body(tree.body, 0, nodes)
    return nodes


# 简单但实用的 JS/TS 结构提取：基于行首正则，不做完整 AST。
_JS_PATTERNS = [
    (re.compile(r"^\s*export\s+default\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"), "function"),
    (re.compile(r"^\s*export\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"), "function"),
    (re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"), "function"),
    (re.compile(r"^\s*export\s+class\s+([A-Za-z_$][\w$]*)"), "class"),
    (re.compile(r"^\s*class\s+([A-Za-z_$][\w$]*)"), "class"),
    (re.compile(r"^\s*export\s+interface\s+([A-Za-z_$][\w$]*)"), "interface"),
    (re.compile(r"^\s*interface\s+([A-Za-z_$][\w$]*)"), "interface"),
    (re.compile(r"^\s*export\s+type\s+([A-Za-z_$][\w$]*)\s*="), "type"),
    (re.compile(r"^\s*type\s+([A-Za-z_$][\w$]*)\s*="), "type"),
    (re.compile(r"^\s*export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)\s*=>|function)"), "function"),
    (re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)\s*=>|function)"), "function"),
]

_OTHER_PATTERNS = [
    (re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:async\s+)?(?:function\s+)?([A-Za-z_$][\w$]*)\s*\("), "function"),
    (re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:class|interface|enum)\s+([A-Za-z_$][\w$]*)"), "type"),
]


def _regex_outline(content: str, language: str) -> list[dict[str, Any]]:
    patterns = _JS_PATTERNS if language in {"javascript", "typescript"} else _OTHER_PATTERNS
    nodes: list[dict[str, Any]] = []
    seen_lines: set[int] = set()
    for lineno, raw in enumerate(content.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("/*"):
            continue
        for pattern, kind in patterns:
            m = pattern.match(raw)
            if m:
                name = m.group(1)
                if lineno in seen_lines:
                    continue
                seen_lines.add(lineno)
                nodes.append({
                    "name": name,
                    "kind": kind,
                    "line": lineno,
                    "children": [],
                })
                break
    return nodes


def _markdown_outline(content: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for lineno, raw in enumerate(content.splitlines(), 1):
        m = re.match(r"^(#{1,6})\s+(.*)", raw)
        if m:
            nodes.append({
                "name": m.group(2).strip(),
                "kind": f"h{len(m.group(1))}",
                "line": lineno,
                "children": [],
            })
    return nodes


def build_outline(path: str, language: str, content: str) -> list[dict[str, Any]]:
    if language == "python":
        return _py_outline(content)
    if language in {"markdown"}:
        return _markdown_outline(content)
    if language in {"json"}:
        return []
    return _regex_outline(content, language)
