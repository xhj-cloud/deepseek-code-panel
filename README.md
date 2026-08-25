# DeepSeek Code Panel

一个 DeepSeek Harness (dsh) 插件：在窗口右侧显示一个可折叠、可拖宽、可交互的**代码面板**。

## 功能概览

- 右侧浮动面板，可最小化/展开
- 面板左侧边缘可**左右拖动调整宽度**（280px ~ 窗口宽度-32px）
- 上半部分：当前选中文件的代码，带行号
- 下半部分：当前工作区（dsh 当前会话 `cwd`）的**目录树**
  - 文件夹可展开/折叠，带 `📁` / `📄` 图标
  - 点击文件后在上半部分查看代码，并高亮当前文件
- 未选择文件时，上半部分显示“未选择文件”（保持空白，不自动加载文件）

## 架构

dsh 的插件宿主是 **Node.js / Cordis**，浏览器端 UI 也由 JavaScript 渲染；但本插件的核心业务逻辑按需求使用 **Python** 实现，并通过 **venv** 管理运行环境。

```
┌──────────────────────────────────────────────────────────────┐
│ dsh web (浏览器)                                             │
│                                                              │
│  client.js  ── 注册到 shell.overlay ── 右侧浮动代码面板      │
│      │  HTTP fetch                                           │
│      ▼                                                       │
│  Python server.py  (127.0.0.1:8765)                          │
│      ├── /api/tree   目录树                                  │
│      ├── /api/view   文件内容                                │
│      └── outline.py  文件结构解析（备用/可扩展）             │
│                                                              │
│ dsh host (Node.js)                                           │
│      index.js ── 随 dsh 启动 Python 服务，退出时自动停止      │
└──────────────────────────────────────────────────────────────┘
```

| 层 | 语言 | 文件 | 职责 |
|---|---|---|---|
| Host 插件 | JavaScript (Node) | `index.js` | 随 dsh 启动/停止 Python 本地服务 |
| Client 插件 | JavaScript (Browser) | `client.js` | 在 dsh web 右侧 `shell.overlay` 渲染代码面板 |
| 本地服务 | **Python** | `server.py` | HTTP API：目录树、文件读取、结构解析入口 |
| 结构解析 | **Python** | `outline.py` | 语言识别与代码结构解析（Python AST、JS/TS 正则、Markdown 标题） |
| 包元数据 | JSON | `package.json` | 声明 dsh 客户端插件入口（`dsh.client`） |
| 依赖声明 | text | `requirements.txt` | Python 依赖清单（当前仅使用标准库） |
| 环境脚本 | bash | `setup.sh` | 创建 `venv` 并安装依赖 |
| 安装脚本 | bash | `install.sh` | 将插件安装到 `~/.dsh/profiles/web` |

## 目录结构

```
deepseek-code-panel/
├── server.py          # Python 本地 HTTP 服务（API 层）
├── outline.py         # 结构解析逻辑（Python AST / 正则 outline）
├── client.js          # dsh 浏览器端插件（shell.overlay）
├── index.js           # dsh Node 端插件（启动 Python 服务）
├── package.json       # dsh 客户端插件元数据
├── requirements.txt   # Python 依赖声明
├── setup.sh           # 创建 venv 并安装依赖
├── install.sh         # 安装到本机 dsh web profile
├── .gitignore         # 忽略 venv / __pycache__ / node_modules 等
└── README.md          # 本文档
```

## 文件详解

### `server.py`

Python 本地 HTTP 服务，只监听 `127.0.0.1`。基于标准库 `http.server.ThreadingHTTPServer` 实现，无第三方依赖。

主要函数：

| 函数 | 作用 |
|---|---|
| `safe_join(root, rel)` | 将相对路径安全解析到 `root` 内，防止路径穿越 |
| `list_files(root, max_depth)` | 递归列出工作区文件，跳过 `.git`、`node_modules`、`venv`、`__pycache__` 等目录 |
| `Handler` | HTTP 请求处理器，统一 JSON 响应与 CORS 头 |
| `main()` | 解析 `--host` / `--port` 并启动服务 |

命令行：

```bash
./venv/bin/python server.py --host 127.0.0.1 --port 8765
```

### `outline.py`

文件结构与语言识别模块，当前 UI 主要展示目录树，此模块保留为代码结构解析能力（可扩展）：

| 函数 | 作用 |
|---|---|
| `detect_language(path)` | 按扩展名识别语言（python / javascript / typescript / markdown 等） |
| `_py_outline(content)` | 使用 Python `ast` 解析函数、异步函数、类及其嵌套结构 |
| `_regex_outline(content, language)` | JS/TS 等语言的行首正则解析（函数、类、接口、类型） |
| `_markdown_outline(content)` | 解析 Markdown 标题结构 |
| `build_outline(path, language, content)` | 按语言分发到上述解析器 |

### `client.js`

dsh 浏览器端插件。通过 `window.__ModuleLoader__.load()` 注册为 dsh 客户端模块，并通过 `ctx.slots.register()` 注册到内置的 `shell.overlay` 槽位。

内部组成：

| 部分 | 说明 |
|---|---|
| `CodePanel` | 主面板组件，管理文件列表、选中文件、加载状态、宽度拖拽 |
| `FileTree` | 目录树容器，把扁平文件列表构造成树 |
| `FileTreeNode` | 目录树节点，支持展开/折叠与选中高亮 |
| `buildFileTree(files)` | 将 `/api/tree` 返回的扁平列表构造成嵌套目录树 |
| `onResizeStart / Move / End` | 面板宽度拖拽逻辑，监听 `window` 上的 pointer 事件 |
| CSS | 内嵌样式，包含面板、拖拽条、目录树、代码区等样式 |

关键行为：

- 面板挂载在 `shell.overlay`（覆盖层本身 `pointer-events: none`，面板自己 `pointerEvents: auto`）
- 目录树请求当前会话 `cwd` 对应的 `/api/tree`
- 点击文件后请求 `/api/view`，上半部分渲染带行号的代码
- 未选择文件时上半部分显示“未选择文件”

### `index.js`

dsh Node 端 Host 插件（CommonJS）。随 dsh 启动 Python 服务，随 dsh 退出而停止。

读取的配置项：

| 配置 | 默认值 | 说明 |
|---|---|---|
| `config.projectDir` | `__dirname` | 项目根目录，用于定位 `server.py` 与 `venv` |
| `config.pythonBin` | `projectDir/venv/bin/python` | Python 解释器路径 |
| `config.serverScript` | `projectDir/server.py` | Python 服务入口 |
| `config.port` | `8765` | Python 服务端口 |
| `config.host` | `127.0.0.1` | Python 服务监听地址 |

### `package.json`

包元数据，关键字段：

```json
{
  "name": "deepseek-code-panel",
  "type": "commonjs",
  "exports": {
    ".": "./index.js",
    "./client": "./client.js",
    "./package.json": "./package.json"
  },
  "dsh": {
    "client": {
      "platform": "web"
    }
  }
}
```

- `exports["."]`：Host 插件入口（`index.js`）
- `exports["./client"]`：dsh 客户端插件入口（`client.js`），由 dsh 扫描后注入浏览器
- `exports["./package.json"]`：dsh 客户端模块系统解析包元数据时需要
- `dsh.client.platform = "web"`：声明这是 web 客户端插件

### `install.sh`

一键安装脚本，完成：

1. 若 `venv` 不存在则调用 `setup.sh` 创建
2. 将 `deepseek-code-panel` 作为本地文件依赖写入 profile 的 `package.json`
3. 在 profile 目录执行 `pnpm install --force`（强制刷新本地文件依赖）
4. 在 `cordis.patch.yml` 中追加插件条目（已存在则跳过）

### `setup.sh`

创建 Python venv 并安装 `requirements.txt`。

## 安装

### 自动安装

```bash
cd ~/projects/deepseek-code-panel
./install.sh
```

重启 dsh：

```bash
dsh web
```

### 手动安装

1. 创建虚拟环境：

```bash
cd ~/projects/deepseek-code-panel
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

2. 在 `~/.dsh/profiles/web/package.json` 的 `dependencies` 中加入：

```json
"deepseek-code-panel": "file:/Users/xianghaojing/projects/deepseek-code-panel"
```

3. 安装依赖：

```bash
cd ~/.dsh/profiles/web
pnpm install --force
```

4. 在 `~/.dsh/profiles/web/cordis.patch.yml` 末尾追加：

```yaml
# DeepSeek code panel: 右侧代码/结构面板
- insert:
    - id: code-panel
      name: deepseek-code-panel
      config:
        port: 8765
        projectDir: /Users/xianghaojing/projects/deepseek-code-panel
```

5. 重启 `dsh web`。

## 使用说明

1. 启动 dsh web 后，右侧会出现代码面板。
2. 上半部分默认显示“未选择文件”。
3. 在下半部分目录树中展开文件夹，点击文件。
4. 上半部分显示文件代码（带行号）。
5. 鼠标按住面板左侧竖条左右拖动，可调整面板宽度。
6. 点击右上角 `—` 最小化；点击右侧竖条恢复。
7. 点击 `刷新` 重新加载当前工作区目录树。

## API 文档

### `GET /api/health`

健康检查。

响应：

```json
{ "ok": true }
```

### `GET /api/tree?root=<workspace>&max_depth=5`

列出工作区目录下的文件（扁平列表）。

参数：

| 参数 | 说明 |
|---|---|
| `root` | 工作区根目录的绝对路径，必填 |
| `max_depth` | 最大扫描层数，默认 4 |

响应：

```json
{
  "root": "/Users/xianghaojing/projects",
  "files": [
    {
      "path": "deepseek-code-panel/server.py",
      "name": "server.py",
      "type": "file",
      "language": "python"
    }
  ]
}
```

### `GET /api/view?root=<workspace>&path=<relative-file>`

读取单个文件内容。

参数：

| 参数 | 说明 |
|---|---|
| `root` | 工作区根目录绝对路径，必填 |
| `path` | 相对于 `root` 的文件路径，必填 |

响应：

```json
{
  "path": "server.py",
  "absolute": "/abs/path/server.py",
  "language": "python",
  "content": "print('hello')\n",
  "structure": [
    { "name": "main", "kind": "function", "line": 168, "children": [] }
  ]
}
```

说明：`structure` 由 `outline.py` 生成，当前 UI 未直接展示；后续若切换回代码结构树可直接使用。

## 安全说明

- Python 服务只监听 `127.0.0.1`
- `/api/view` 会校验相对路径，禁止逃逸出 workspace root
- 默认跳过 `.git`、`node_modules`、`venv`、`__pycache__`、`dist`、`build` 等目录
- 单文件读取上限 2MB，超过返回 413

## 常见问题

### 面板没出现？

- 确认已执行 `./install.sh`
- 确认 `~/.dsh/profiles/web/cordis.patch.yml` 中存在 `code-panel` 条目
- 重启 `dsh web`
- 查看 dsh 终端是否有 `[code-panel]` 相关日志

### 面板出现但目录树为空？

- 确认当前会话有 `cwd`（日志中 `root=...` 即为当前工作区）
- 确认 Python 服务已启动：`lsof -nP -iTCP:8765 -sTCP:LISTEN`
- 手动测试：`curl 'http://127.0.0.1:8765/api/tree?root=<你的工作区>'`

### 日志里的 `%2F` 是什么？

`%2F` 是 URL 编码的 `/`。例如：

```
GET /api/tree?root=%2FUsers%2Fxianghaojing%2Fprojects&max_depth=5
```

实际请求的路径就是：

```
/Users/xianghaojing/projects
```

返回 `200` 表示请求成功，是正常日志。

### 更新代码后浏览器里还是旧界面？

dsh 对客户端插件有 bundle 缓存。更新代码后请重启 `dsh web`；若仍无效，可在 profile 目录执行：

```bash
cd ~/.dsh/profiles/web
pnpm install --force
```

然后重启 dsh。

## 开发调试

单独启动 Python 服务：

```bash
cd ~/projects/deepseek-code-panel
./venv/bin/python server.py --port 8765
```

手动测试 API：

```bash
curl http://127.0.0.1:8765/api/health
curl 'http://127.0.0.1:8765/api/tree?root=/Users/xianghaojing/projects'
curl 'http://127.0.0.1:8765/api/view?root=/Users/xianghaojing/projects&path=deepseek-code-panel/server.py'
```

语法检查：

```bash
node --check client.js
node --check index.js
python3 -m py_compile server.py outline.py
```

## License

[CC BY-NC 4.0](LICENSE) © 2026 [xhj-cloud](https://github.com/xhj-cloud)

本项目采用 CC BY-NC 4.0（署名-非商业性使用）协议开源：可以自由查看、使用、修改和分发，但**禁止任何商业用途**。

