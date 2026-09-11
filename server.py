#!/usr/bin/env python3
"""DeepSeek Harness 代码面板 - Python 本地服务

为 dsh 右侧代码面板提供文件代码与文件结构数据。

用法:
    python server.py [--port 8765] [--host 127.0.0.1]

该服务仅监听本机回环地址，提供以下 API:
    GET /api/health
    GET /api/tree?root=<workspace>[&max_depth=N]   全量文件扁平列表（下拉框用）
    GET /api/list?root=<workspace>[&path=<rel-dir>]  单层子项列表（目录树懒加载用）
    GET /api/view?root=<workspace>&path=<relative-file-path>
    GET /api/image?root=<workspace>&path=<relative-image>  图片流式传输
"""

from __future__ import annotations

import argparse
import json
import mimetypes
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
MAX_IMAGE_BYTES = 100 * 1024 * 1024  # 图片预览放宽到 100MB（流式传输，内存占用低）
STREAM_CHUNK = 64 * 1024  # 图片流式传输块大小


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
                language = detect_language(str(entry))
                limit = MAX_IMAGE_BYTES if language == "image" else MAX_FILE_BYTES
                if size > limit:
                    continue
                rel = entry.relative_to(root_path).as_posix()
                files.append({
                    "path": rel,
                    "name": name,
                    "type": "file",
                    "language": language,
                })

    walk(root_path, 0)
    return files


def list_children(root: str, rel: str) -> list[dict[str, Any]] | None:
    """列出 root/rel 目录下的一层子项（目录在前，名称不区分大小写排序）。

    用于目录树懒加载。越界或目录不存在时返回 None。
    """
    target = safe_join(root, rel) if rel else safe_join(root, "")
    if target is None or not os.path.isdir(target):
        return None
    root_real = os.path.realpath(root)
    entries: list[dict[str, Any]] = []
    try:
        it = sorted(os.scandir(target), key=lambda e: (e.is_file(), e.name.lower()))
    except OSError:
        return None
    for entry in it:
        name = entry.name
        if name in EXCLUDED_DIRS or name in EXCLUDED_FILES:
            continue
        try:
            if entry.is_dir():
                entries.append({
                    "name": name,
                    "path": os.path.relpath(entry.path, root_real).replace(os.sep, "/"),
                    "type": "dir",
                })
            elif entry.is_file():
                try:
                    size = entry.stat().st_size
                except OSError:
                    continue
                language = detect_language(entry.path)
                limit = MAX_IMAGE_BYTES if language == "image" else MAX_FILE_BYTES
                if size > limit:
                    continue
                entries.append({
                    "name": name,
                    "path": os.path.relpath(entry.path, root_real).replace(os.sep, "/"),
                    "type": "file",
                    "language": language,
                })
        except OSError:
            continue
    return entries


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
                self._send_json(200, {"ok": True, "service": "deepseek-code-panel", "pid": os.getpid()})
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

            if parsed.path == "/api/list":
                root = (query.get("root") or [""])[0]
                rel = (query.get("path") or [""])[0]
                if not root or not os.path.isdir(root):
                    self._send_json(400, {"error": "root must be an existing directory"})
                    return
                entries = list_children(root, rel)
                if entries is None:
                    self._send_json(404, {"error": "directory not found"})
                    return
                self._send_json(200, {"root": root, "path": rel, "entries": entries})
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

            if parsed.path == "/api/image":
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
                if detect_language(target) != "image":
                    self._send_json(415, {"error": "not an image file"})
                    return
                try:
                    stat = os.stat(target)
                except OSError as e:
                    self._send_json(500, {"error": str(e)})
                    return
                if stat.st_size > MAX_IMAGE_BYTES:
                    self._send_json(413, {"error": "image too large"})
                    return
                mime, _ = mimetypes.guess_type(target)
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Content-Length", str(stat.st_size))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    # 分块流式传输，避免大图片全部读入内存
                    with open(target, "rb") as f:
                        while True:
                            chunk = f.read(STREAM_CHUNK)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    # 浏览器取消下载（快速切换图片时常见），忽略
                    pass
                return

            self._send_json(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": f"{type(e).__name__}: {e}"})


def _kill_stale_server(host: str, port: int, timeout: float = 5.0) -> bool:
    """端口被占用时，若占用者是本服务的旧实例（health 返回自身 pid），
    向其发送 SIGTERM 并等待端口释放。返回端口是否已释放。"""
    import signal
    import socket
    import time
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=2) as r:
            data = json.load(r)
    except Exception:
        return False
    if not isinstance(data, dict) or data.get("service") != "deepseek-code-panel" or not data.get("pid"):
        return False
    try:
        os.kill(int(data["pid"]), signal.SIGTERM)
        print(f"[code-panel] sent SIGTERM to stale server pid={data['pid']}", flush=True)
    except (ProcessLookupError, PermissionError, ValueError):
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                pass  # 旧实例仍在监听，继续等待
        except OSError:
            return True  # 连接被拒绝，端口已释放
        time.sleep(0.2)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepSeek Harness code panel local server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    try:
        httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError:
        print(f"[code-panel] port {args.port} in use; trying to stop a stale code-panel server ...", flush=True)
        if not _kill_stale_server(args.host, args.port):
            print(f"[code-panel] error: port {args.port} is in use by another process", flush=True)
            sys.exit(1)
        try:
            httpd = ThreadingHTTPServer((args.host, args.port), Handler)
        except OSError as e:
            print(f"[code-panel] error: cannot bind port {args.port}: {e}", flush=True)
            sys.exit(1)
    print(f"[code-panel] listening on http://{args.host}:{args.port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
