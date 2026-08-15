#!/usr/bin/env bash
# 将 deepseek-code-panel 安装到本机 dsh web profile。
#
# 用法:
#   ./install.sh [profile_dir]
# 默认 profile_dir = ~/.dsh/profiles/web
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE_DIR="${1:-$HOME/.dsh/profiles/web}"

if [[ ! -f "$PROFILE_DIR/package.json" ]]; then
  echo "error: profile not found at $PROFILE_DIR" >&2
  exit 1
fi

echo "==> Creating venv (if needed) ..."
if [[ ! -x "$SCRIPT_DIR/venv/bin/python" ]]; then
  bash "$SCRIPT_DIR/setup.sh"
else
  echo "    venv already exists"
fi

echo "==> Registering file dependency in $PROFILE_DIR/package.json ..."
python3 - "$PROFILE_DIR/package.json" "$SCRIPT_DIR" <<'PY'
import json, sys, os

pkg_path = sys.argv[1]
plugin_dir = sys.argv[2]
with open(pkg_path, "r", encoding="utf-8") as f:
    pkg = json.load(f)

pkg.setdefault("dependencies", {})
pkg["dependencies"]["deepseek-code-panel"] = f"file:{plugin_dir}"

with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(pkg, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("    added deepseek-code-panel dependency")
PY

echo "==> Installing profile dependencies ..."
if command -v pnpm >/dev/null 2>&1; then
  (cd "$PROFILE_DIR" && pnpm install --force)
else
  echo "warning: pnpm not found, please run 'pnpm install --force' in $PROFILE_DIR manually" >&2
fi

echo "==> Patching cordis.patch.yml ..."
PATCH_FILE="$PROFILE_DIR/cordis.patch.yml"
if grep -q "^[[:space:]]*- id: code-panel" "$PATCH_FILE"; then
  echo "    code-panel entry already present"
else
  cat >> "$PATCH_FILE" <<YAML

# DeepSeek code panel: 右侧代码/结构面板
- insert:
    - id: code-panel
      name: deepseek-code-panel
      config:
        port: 8765
        projectDir: $SCRIPT_DIR
YAML
  echo "    added code-panel entry"
fi

echo "==> Done."
echo "    重启 dsh web 后，右侧会出现可折叠的代码面板。"
