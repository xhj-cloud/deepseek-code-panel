#!/usr/bin/env python3
"""DeepSeek Harness 代码面板 - Python 本地服务

为 dsh 右侧代码面板提供文件代码与文件结构数据。

用法:
    python server.py [--port 8765] [--host 127.0.0.1]

该服务仅监听本机回环地址，提供两个 JSON API:
    GET /api/health
    GET /api/tree?root=<workspace>
    GET /api/view?root=<workspace>&path=<relative-file-path>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from outline import build_outline, detect_language

# 一些常见的、不应出现在文件列表中的目录/文件
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__",
    "node_modules", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".next", ".nuxt", ".cache", ".DS_Store",
}
EXCLUDED_FILES = {".DS_Store", "Thumbs.db"}
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2MB，避免浏览器卡死


def safe_join(root: str, rel: str) -> str | None:
    """将 rel 安全地解析到 root 内；越界或不存在时返回 None。"""
    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, rel))
    if candidate != root_real and not candidate.startswith(root_real + os.sep):
        return None
    return candidate


def list_files(root: str, max_depth: int = 4) -> list[dict[str, Any]]:
    """递归列出 root 下适合展示的代码文件（扁平列表）。"""
    root_path = Path(root)
    files: list[dict[str, Any]] = []

    def walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return
        for entry in entries:
            name = entry.name
            if name in EXCLUDED_DIRS or name in EXCLUDED_FILES:
                continue
            if entry.is_dir():
                walk(entry, depth + 1)
            elif entry.is_file():
                try:
                    size = entry.stat().st_size
                except OSError:
                    continue
                if size > MAX_FILE_BYTES:
                    continue
                rel = entry.relative_to(root_path).as_posix()
                files.append({
                    "path": rel,
                    "name": name,
                    "type": "file",
                    "language": detect_language(str(entry)),
                })

    walk(root_path, 0)
    return files


# ──────────────────────────────────────────────
# HTTP 服务
# ──────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "DeepSeekCodePanel/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[code-panel] %s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                self._send_json(200, {"ok": True})
                return

            if parsed.path == "/api/tree":
                root = (query.get("root") or [""])[0]
                if not root or not os.path.isdir(root):
                    self._send_json(400, {"error": "root must be an existing directory"})
                    return
                max_depth = int((query.get("max_depth") or ["4"])[0])
                files = list_files(root, max_depth=max_depth)
                self._send_json(200, {"root": root, "files": files})
                return

            if parsed.path == "/api/view":
                root = (query.get("root") or [""])[0]
                rel = (query.get("path") or [""])[0]
                if not root or not os.path.isdir(root):
                    self._send_json(400, {"error": "root must be an existing directory"})
                    return
                if not rel:
                    self._send_json(400, {"error": "path is required"})
                    return
                target = safe_join(root, rel)
                if target is None:
                    self._send_json(403, {"error": "path escapes workspace root"})
                    return
                if not os.path.isfile(target):
                    self._send_json(404, {"error": "file not found"})
                    return
                try:
                    stat = os.stat(target)
                    if stat.st_size > MAX_FILE_BYTES:
                        self._send_json(413, {"error": "file too large"})
                        return
                    with open(target, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except OSError as e:
                    self._send_json(500, {"error": str(e)})
                    return
                language = detect_language(target)
                structure = build_outline(target, language, content)
                self._send_json(200, {
                    "path": rel,
                    "absolute": target,
                    "language": language,
                    "content": content,
                    "structure": structure,
                })
                return

            self._send_json(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": f"{type(e).__name__}: {e}"})


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepSeek Harness code panel local server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[code-panel] listening on http://{args.host}:{args.port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
