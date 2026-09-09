/**
 * DeepSeek Harness 代码面板 - 浏览器端插件
 *
 * 注册到 dsh 的 shell.overlay（frame 级浮动层），在右侧显示一个可折叠面板。
 * 面板上半部分显示文件代码，下半部分显示该文件的结构（outline）。
 * 数据来自同机 Python 服务：http://127.0.0.1:8765
 */
window.__ModuleLoader__.load({
  id: "deepseek-code-panel",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });

    var React = require("react");
    var jsxRuntime = require("react/jsx-runtime");

    // ── 样式 ─────────────────────────────────────────────
    var css = [
      ".dsh-code-panel-root{position:fixed;top:16px;right:16px;bottom:16px;width:440px;max-width:calc(100vw - 32px);z-index:2147483000;display:flex;flex-direction:column;border:1px solid var(--dsw-alias-border-l2,#333);border-radius:12px;background:var(--dsw-alias-bg-base,#1e1e1e);color:var(--dsw-alias-label-primary,#e8e8e8);box-shadow:0 8px 32px rgba(0,0,0,.35);overflow:hidden;font-size:13px;line-height:1.5}",
      ".dsh-code-panel-root *{box-sizing:border-box}",
      ".dsh-code-panel-resizer{position:absolute;left:0;top:0;bottom:0;width:8px;cursor:col-resize;z-index:20;touch-action:none}",
      ".dsh-code-panel-resizer::before{content:'';position:absolute;left:2px;top:50%;transform:translateY(-50%);width:3px;height:36px;border-radius:2px;background:rgba(128,128,128,.35)}",
      ".dsh-code-panel-resizer:hover,.dsh-code-panel-resizer:active{background:rgba(128,128,128,.18)}",
      ".dsh-code-panel-resizer:hover::before,.dsh-code-panel-resizer:active::before{background:rgba(79,193,255,.8)}",
      ".dsh-code-panel-header{display:flex;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-1);flex:none}",
      ".dsh-code-panel-title{font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}",
      ".dsh-code-panel-btn{background:transparent;border:1px solid transparent;border-radius:6px;color:inherit;font-size:12px;padding:2px 8px;cursor:pointer;flex:none}",
      ".dsh-code-panel-btn:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.08))}",
      ".dsh-code-panel-toolbar{display:flex;align-items:center;gap:6px;padding:6px 12px;border-bottom:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-base);flex:none}",
      ".dsh-code-panel-select{flex:1;min-width:0;background:var(--dsw-alias-bg-layer-2);color:inherit;border:1px solid var(--dsw-alias-border-l2);border-radius:6px;padding:4px 8px;font-size:12px;outline:none}",
      ".dsh-code-panel-body{display:flex;flex-direction:column;flex:1;min-height:0}",
      ".dsh-code-panel-half{display:flex;flex-direction:column;min-height:0}",
      ".dsh-code-panel-half-top{flex:1 1 50%;border-bottom:1px solid var(--dsw-alias-border-l2,#333)}",
      ".dsh-code-panel-half-bottom{flex:1 1 50%}",
      ".dsh-code-panel-section-label{padding:4px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--dsw-alias-label-secondary);border-bottom:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-1);flex:none}",
      ".dsh-code-panel-code{flex:1;overflow:auto;margin:0;padding:8px 12px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre;tab-size:4;color:var(--dsw-alias-label-primary)}",
      ".dsh-code-panel-structure{flex:1;overflow:auto;padding:6px 6px 12px}",
      ".dsh-code-panel-tree ul{list-style:none;margin:0;padding-left:14px}",
      ".dsh-code-panel-tree>ul{padding-left:2px}",
      ".dsh-code-panel-tree li{padding:0}",
      ".dsh-code-panel-tree .tree-row{display:flex;align-items:center;gap:4px;padding:1px 6px 1px 2px;border-radius:5px;white-space:nowrap;overflow:hidden;cursor:default}",
      ".dsh-code-panel-tree .tree-row:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.06))}",
      ".dsh-code-panel-tree .tree-row.selected{background:rgba(79,193,255,.15)}",
      ".dsh-code-panel-tree .tree-caret{width:14px;flex:none;text-align:center;cursor:pointer;color:var(--dsw-alias-label-secondary,#999);font-size:10px;user-select:none}",
      ".dsh-code-panel-tree .tree-caret-placeholder{width:14px;flex:none}",
      ".dsh-code-panel-tree .tree-icon{width:18px;flex:none;text-align:center;font-size:12px}",
      ".dsh-code-panel-tree .kind{color:var(--dsw-alias-state-business-primary,#4176e6);flex:none;font-size:11px;min-width:52px}",
      ".dsh-code-panel-tree .tree-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}",
      ".dsh-code-panel-tree .line{color:var(--dsw-alias-label-tertiary);flex:none;margin-left:8px;font-size:11px}",
      ".dsh-code-panel-message{display:flex;align-items:center;justify-content:center;flex:1;color:var(--dsw-alias-label-secondary,#999);padding:16px;text-align:center}",
      ".dsh-code-panel-minimized{position:fixed;top:50%;right:0;transform:translateY(-50%);z-index:2147483000;background:var(--dsw-alias-bg-layer-1);border:1px solid var(--dsw-alias-border-l2);border-right:none;border-radius:10px 0 0 10px;padding:10px 6px;cursor:pointer;writing-mode:vertical-rl;font-size:13px;color:var(--dsw-alias-label-primary);box-shadow:-4px 0 16px rgba(0,0,0,.2)}",
      "@media (max-width:640px){.dsh-code-panel-root{top:8px;right:8px;left:8px;bottom:8px;width:auto;max-width:none}.dsh-code-panel-resizer{display:none}}"
    ].join("\n");

    var tagId = "deepseek-code-panel/styles";
    if (typeof document !== "undefined" && document.querySelector("style[data-plugin-css=" + JSON.stringify(tagId) + "]") === null) {
      var tag = document.createElement("style");
      tag.dataset.plugin = "deepseek-code-panel";
      tag.dataset.pluginCss = tagId;
      tag.textContent = css;
      document.head.appendChild(tag);
    }

    // ── 工具函数 ─────────────────────────────────────────
    var API_BASE = "http://127.0.0.1:8765";

    function apiUrl(pathname, params) {
      var url = new URL(API_BASE + pathname);
      if (params) {
        for (var key of Object.keys(params)) {
          if (params[key] !== undefined && params[key] !== null && params[key] !== "") {
            url.searchParams.set(key, params[key]);
          }
        }
      }
      return url.toString();
    }

    async function apiGet(pathname, params) {
      var res = await fetch(apiUrl(pathname, params), { cache: "no-store" });
      if (!res.ok) {
        var text = await res.text().catch(function () { return res.statusText; });
        throw new Error("HTTP " + res.status + ": " + text);
      }
      return res.json();
    }

    function formatLineNumber(i) {
      var n = i + 1;
      return String(n).padStart(Math.max(3, String(Math.max(1, n)).length), " ");
    }

    function buildFileTree(files) {
      var root = { name: "", path: "", type: "dir", children: [] };
      files.forEach(function (file) {
        var parts = file.path.split("/");
        var node = root;
        for (var i = 0; i < parts.length - 1; i++) {
          var part = parts[i];
          var child = null;
          for (var j = 0; j < node.children.length; j++) {
            if (node.children[j].type === "dir" && node.children[j].name === part) {
              child = node.children[j];
              break;
            }
          }
          if (!child) {
            child = { name: part, path: parts.slice(0, i + 1).join("/"), type: "dir", children: [] };
            node.children.push(child);
          }
          node = child;
        }
        node.children.push({ name: parts[parts.length - 1], path: file.path, type: "file", language: file.language });
      });

      function sortNodes(nodes) {
        nodes.sort(function (a, b) {
          if (a.type === b.type) return a.name.localeCompare(b.name);
          return a.type === "dir" ? -1 : 1;
        });
        nodes.forEach(function (n) {
          if (n.children) sortNodes(n.children);
        });
      }
      sortNodes(root.children);
      return root.children;
    }

    function FileTreeNode({ node, selectedPath, onSelect }) {
      var isDir = node.type === "dir";
      var isSelected = !isDir && node.path === selectedPath;
      var _React$useState = React.useState(true);
      var expanded = _React$useState[0];
      var setExpanded = _React$useState[1];

      var caret = isDir
        ? React.createElement(
            "span",
            {
              className: "tree-caret",
              onClick: function (e) {
                e.stopPropagation();
                setExpanded(!expanded);
              },
            },
            expanded ? "▾" : "▸"
          )
        : React.createElement("span", { className: "tree-caret-placeholder" }, "");

      var children = isDir && expanded
        ? React.createElement(
            "ul",
            null,
            node.children.map(function (child, childIdx) {
              return React.createElement(FileTreeNode, {
                key: child.path || child.name + "-" + childIdx,
                node: child,
                selectedPath: selectedPath,
                onSelect: onSelect,
              });
            })
          )
        : null;

      return React.createElement(
        "li",
        { key: node.path || node.name, title: isDir ? node.path || node.name : node.path },
        React.createElement(
          "div",
          {
            className: "tree-row" + (isSelected ? " selected" : ""),
            onClick: isDir ? undefined : function () { onSelect(node.path); },
            style: isDir ? undefined : { cursor: "pointer" },
          },
          caret,
          React.createElement("span", { className: "tree-icon" }, isDir ? "📁" : "📄"),
          React.createElement("span", { className: "tree-name" }, node.name),
          !isDir && React.createElement("span", { className: "line" }, node.language)
        ),
        children
      );
    }

    function FileTree({ files, selectedPath, onSelect }) {
      if (!files || files.length === 0) {
        return React.createElement("div", { className: "dsh-code-panel-message" }, "当前工作区没有可显示的文件");
      }
      var tree = buildFileTree(files);
      return React.createElement(
        "div",
        { className: "dsh-code-panel-tree" },
        React.createElement(
          "ul",
          null,
          tree.map(function (node, idx) {
            return React.createElement(FileTreeNode, {
              key: node.path || node.name + "-" + idx,
              node: node,
              selectedPath: selectedPath,
              onSelect: onSelect,
            });
          })
        )
      );
    }

    // ── 面板组件 ─────────────────────────────────────────
    function CodePanel(props) {
      var useSessions = props.useSessions;
      var current = useSessions(function (s) { return s.current; });
      var cwd = useSessions(function (s) {
        return s.current ? s.byId[s.current] && s.byId[s.current].cwd : undefined;
      });

      var _React$useState = React.useState(false);
      var minimized = _React$useState[0];
      var setMinimized = _React$useState[1];
      var _React$useState2 = React.useState("");
      var root = _React$useState2[0];
      var setRoot = _React$useState2[1];
      var _React$useState3 = React.useState([]);
      var files = _React$useState3[0];
      var setFiles = _React$useState3[1];
      var _React$useState4 = React.useState("");
      var selectedPath = _React$useState4[0];
      var setSelectedPath = _React$useState4[1];
      var _React$useState5 = React.useState(null);
      var view = _React$useState5[0];
      var setView = _React$useState5[1];
      var _React$useState6 = React.useState(false);
      var treeLoading = _React$useState6[0];
      var setTreeLoading = _React$useState6[1];
      var _React$useState7 = React.useState("");
      var treeError = _React$useState7[0];
      var setTreeError = _React$useState7[1];
      var _React$useState8 = React.useState(false);
      var viewLoading = _React$useState8[0];
      var setViewLoading = _React$useState8[1];
      var _React$useState9 = React.useState("");
      var viewError = _React$useState9[0];
      var setViewError = _React$useState9[1];
      var _React$useState10 = React.useState(440);
      var width = _React$useState10[0];
      var setWidth = _React$useState10[1];
      var resizeRef = React.useRef(null);

      function onResizeMoveWindow(e) {
        if (!resizeRef.current) return;
        var dx = e.clientX - resizeRef.current.startX;
        var next = resizeRef.current.startWidth - dx;
        next = Math.max(280, Math.min(window.innerWidth - 32, next));
        setWidth(next);
      }

      function onResizeEndWindow() {
        if (!resizeRef.current) return;
        resizeRef.current = null;
        window.removeEventListener("pointermove", onResizeMoveWindow);
        window.removeEventListener("pointerup", onResizeEndWindow);
        window.removeEventListener("pointercancel", onResizeEndWindow);
      }

      function onResizeStart(e) {
        e.preventDefault();
        e.stopPropagation();
        resizeRef.current = { startX: e.clientX, startWidth: width };
        window.addEventListener("pointermove", onResizeMoveWindow);
        window.addEventListener("pointerup", onResizeEndWindow);
        window.addEventListener("pointercancel", onResizeEndWindow);
      }

      // 当当前会话 cwd 变化时，拉取目录树
      React.useEffect(function () {
        var cancelled = false;
        if (!cwd) {
          setRoot("");
          setFiles([]);
          setSelectedPath("");
          setView(null);
          return;
        }
        setRoot(cwd);
        setTreeLoading(true);
        setTreeError("");
        setSelectedPath("");
        setView(null);
        apiGet("/api/tree", { root: cwd, max_depth: 5 })
          .then(function (data) {
            if (cancelled) return;
            setFiles(data.files || []);
          })
          .catch(function (e) {
            if (cancelled) return;
            setTreeError("无法连接 Python 服务: " + e.message);
          })
          .finally(function () {
            if (!cancelled) setTreeLoading(false);
          });
        return function () {
          cancelled = true;
        };
      }, [cwd]);

      // 当选中文件变化时，拉取代码
      React.useEffect(function () {
        var cancelled = false;
        if (!root || !selectedPath) {
          setView(null);
          return;
        }
        setViewLoading(true);
        setViewError("");
        apiGet("/api/view", { root: root, path: selectedPath })
          .then(function (data) {
            if (cancelled) return;
            setView(data);
          })
          .catch(function (e) {
            if (cancelled) return;
            setViewError("读取文件失败: " + e.message);
          })
          .finally(function () {
            if (!cancelled) setViewLoading(false);
          });
        return function () {
          cancelled = true;
        };
      }, [root, selectedPath]);

      function handleRefresh() {
        if (!root) return;
        setTreeLoading(true);
        setTreeError("");
        apiGet("/api/tree", { root: root, max_depth: 5 })
          .then(function (data) {
            setFiles(data.files || []);
          })
          .catch(function (e) {
            setTreeError("刷新失败: " + e.message);
          })
          .finally(function () {
            setTreeLoading(false);
          });
      }

      if (minimized) {
        return React.createElement(
          "button",
          {
            className: "dsh-code-panel-minimized",
            onClick: function () { setMinimized(false); },
            title: "展开代码面板",
          },
          "代码面板"
        );
      }

      var codeLines = view ? view.content.split("\n") : [];

      return React.createElement(
        "div",
        { className: "dsh-code-panel-root", style: { pointerEvents: "auto", width: window.innerWidth <= 640 ? "calc(100vw - 16px)" : width } },
        React.createElement("div", {
          className: "dsh-code-panel-resizer",
          onPointerDown: onResizeStart,
          title: "左右拖动调整宽度",
        }),
        React.createElement(
          "div",
          { className: "dsh-code-panel-header" },
          React.createElement("div", { className: "dsh-code-panel-title" }, "代码面板"),
          React.createElement(
            "button",
            { className: "dsh-code-panel-btn", onClick: handleRefresh, title: "刷新文件列表" },
            "刷新"
          ),
          React.createElement(
            "button",
            { className: "dsh-code-panel-btn", onClick: function () { setMinimized(true); }, title: "最小化" },
            "—"
          )
        ),
        React.createElement(
          "div",
          { className: "dsh-code-panel-toolbar" },
          React.createElement(
            "select",
            {
              className: "dsh-code-panel-select",
              value: selectedPath,
              onChange: function (e) { setSelectedPath(e.target.value); },
              disabled: files.length === 0,
            },
            files.length === 0
              ? React.createElement("option", { value: "" }, "当前目录没有可显示的文件")
              : [
                  React.createElement("option", { key: "__empty__", value: "" }, "请选择文件"),
                  files.map(function (f) {
                    return React.createElement("option", { key: f.path, value: f.path }, f.path);
                  }),
                ]
          )
        ),
        React.createElement(
          "div",
          { className: "dsh-code-panel-body" },
          React.createElement(
            "div",
            { className: "dsh-code-panel-half dsh-code-panel-half-top" },
            React.createElement("div", { className: "dsh-code-panel-section-label" }, "文件代码"),
            selectedPath === ""
              ? React.createElement("div", { className: "dsh-code-panel-message" }, "未选择文件")
              : viewLoading && !view
                ? React.createElement("div", { className: "dsh-code-panel-message" }, "加载中…")
                : viewError
                  ? React.createElement("div", { className: "dsh-code-panel-message" }, viewError)
                  : React.createElement(
                      "pre",
                      { className: "dsh-code-panel-code" },
                      codeLines.map(function (line, i) {
                        return React.createElement(
                          "div",
                          { key: i },
                          React.createElement("span", { style: { color: "var(--dsw-alias-label-tertiary)", userSelect: "none", display: "inline-block", width: "3em" } }, formatLineNumber(i)),
                          " ",
                          line || " "
                        );
                      })
                    )
          ),
          React.createElement(
            "div",
            { className: "dsh-code-panel-half dsh-code-panel-half-bottom" },
            React.createElement("div", { className: "dsh-code-panel-section-label" }, "目录树"),
            treeLoading && files.length === 0
              ? React.createElement("div", { className: "dsh-code-panel-message" }, "加载中…")
              : treeError
                ? React.createElement("div", { className: "dsh-code-panel-message" }, treeError)
                : React.createElement(
                    "div",
                    { className: "dsh-code-panel-structure" },
                    React.createElement(FileTree, { files: files, selectedPath: selectedPath, onSelect: setSelectedPath })
                  )
          )
        )
      );
    }

    // ── 插件入口 ─────────────────────────────────────────
    function apply(ctx) {
      ctx.effect(function () {
        return ctx.slots.register(
          {
            name: "shell.overlay",
            id: "deepseek-code-panel",
            order: 100,
            label: "代码面板",
          },
          CodePanel
        );
      }, "deepseek-code-panel: overlay registration");
    }

    var inject = ["slots", "layout"];

    exports.apply = apply;
    exports.inject = inject;
    return module.exports;
  }
});
