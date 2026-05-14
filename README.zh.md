# Enable Chrome AI ✨

由 [lcandy2](https://twitter.com/vanillaCitron) 研究并制作脚本。

[![Twitter](https://img.shields.io/twitter/follow/vanillaCitron)](https://twitter.com/vanillaCitron)

[English](README.md) | 中文

在 Google Chrome 中启用 Gemini、AI 历史搜索、DevTools AI 等创新功能——无需清除数据或重新安装。

<img width="512" alt="Google Chrome Gemini in Chrome" src="https://github.com/user-attachments/assets/a88c56a7-f20b-432a-926c-0184194225b4" />

轻量 Python 脚本，通过修改本地 Chrome 配置（`variations_country`、`variations_permanent_consistency_country` 和 `is_glic_eligible`）启用浏览器内置 AI 功能，无需额外开关。

## ✅ 环境要求
- Python `3.13+`（见 `.python-version` / `pyproject.toml`）
- 已安装 Google Chrome（Stable/Canary/Dev/Beta）

## ⚡️ 快速开始（uv）
1. 安装 uv（一次性）：
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - macOS & Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - 更多安装方式请参考 [uv 安装文档](https://docs.astral.sh/uv/getting-started/installation/)。
2. 安装依赖（自动创建虚拟环境）：`uv sync`。
3. 运行脚本：`uv run main.py`。
4. 补丁过程中 Chrome 会被关闭；重启后根据提示按 Enter 结束。

## ⚡️ 快速开始（pip）
1. 创建并激活虚拟环境。
2. 安装依赖：`python -m pip install psutil`。
3. 运行：`python main.py`。

## ↩️ 恢复 / 撤销
- 首次修改前，脚本会在 Chrome 的 `Local State` 旁创建备份：`Local State.enable-chrome-ai.bak`。
- 如需恢复原始文件，运行：`uv run main.py --restore` 或 `python main.py --restore`。
- 如果你已经自行管理备份，可以加 `--no-backup` 跳过备份创建。

## 🔧 做了什么
- 自动定位 Windows / macOS / Linux 上的 Chrome Stable / Canary / Dev / Beta 用户数据目录。
- 关闭顶层 Chrome 进程以避免文件锁，再在补丁后恢复。
- 首次修改前创建 `Local State.enable-chrome-ai.bak` 备份。
- 在 `Local State` 中递归查找并将所有 `is_glic_eligible` 设为 `true`。
- 在 `Local State` 中将 `variations_country` 设为 `"us"`。
- 在 `Local State` 中将 `variations_permanent_consistency_country` 设为 `["<版本号>", "us"]`。
- 重启补丁前已运行的 Chrome 版本。

## ⚠️ 已知限制 / 注意事项
- 脚本假设 `User Data/Local State` 已存在；若缺失可能直接失败（可先启动一次 Chrome 生成配置）。
- 只有在能从进程信息中取到可执行文件路径时，脚本才会自动重启 Chrome。
- macOS 上按进程名（`Google Chrome*`）识别，可能会终止不止"顶层"应用进程。
- Linux 上按可执行文件名 `chrome` 识别；若你的发行版/安装方式使用其他名字，可能不会关闭 Chrome（从而仍可能有文件锁）。

## 🛟 注意
- 脚本会修改现有 Chrome 配置，如需保险请先备份 `User Data`。
- 使用拥有该 Chrome 配置的同一系统用户运行，确保有写入权限。
- 与 Google 无关，风险自担。

## 💖 支持项目
如果这个脚本帮你省下了重装 Chrome 或清空配置的时间，可以通过 [GitHub Sponsors](https://github.com/sponsors/lcandy2) 小额支持维护。一次性赞助也很有帮助，可以支持我继续测试更多 Chrome 渠道和平台。

## 📜 许可
转载或基于本研究二次创作需要注明来源。

## 🙏 致谢
- [show-copilot](https://github.com/hzkaai/show-copilot)
