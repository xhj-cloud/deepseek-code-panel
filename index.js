"use strict";

/**
 * DeepSeek Harness 代码面板 - Host 插件
 *
 * dsh 的插件宿主是 Node.js/Cordis，因此这里用一个非常薄的 Node 插件负责：
 *   1. 启动 Python 本地服务（server.py）
 *   2. 在 dsh 退出时自动停止该 Python 服务
 *
 * 真正的文件读取、代码与结构提取逻辑全部在 Python 侧。
 */

const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const name = "deepseek-code-panel";
const inject = [];

function apply(ctx, config) {
  const pluginDir = __dirname;
  // pnpm 安装本地 file: 依赖时通常会拷贝项目文件但不包含 venv，
  // 因此默认指向原始项目目录（由 install.sh 写入 config.projectDir）。
  const projectDir = config?.projectDir || pluginDir;
  const pythonBin = config?.pythonBin || path.join(projectDir, "venv", "bin", "python");
  const serverScript = config?.serverScript || path.join(projectDir, "server.py");
  const port = Number(config?.port || 8765);
  const host = config?.host || "127.0.0.1";

  if (!fs.existsSync(pythonBin)) {
    ctx.logger.warn(
      `[code-panel] Python venv not found at ${pythonBin}; run setup.sh first or set config.pythonBin`
    );
  }

  ctx.effect(() => {
    const child = spawn(pythonBin, [serverScript, "--host", host, "--port", String(port)], {
      cwd: projectDir,
      stdio: "inherit",
      env: {
        ...process.env,
        DSH_CODE_PANEL_PORT: String(port),
        DSH_CODE_PANEL_ROOT: projectDir,
      },
    });

    child.on("error", (err) => {
      ctx.logger.error(`[code-panel] failed to start python server: ${err.message}`);
    });
    child.on("exit", (code, signal) => {
      console.log(`[code-panel] python server exited code=${code} signal=${signal}`);
    });

    return () => {
      if (!child.killed) {
        child.kill();
      }
    };
  }, "deepseek-code-panel: python server");
}

module.exports = { name, apply, inject };
