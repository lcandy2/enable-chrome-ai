# Show Copilot ✨

[English](README.md) | 中文

轻量 Python 脚本，通过修改本地 Edge 配置让浏览器直接进入 Copilot/Chat 模式，无需额外开关。

## ✅ 环境要求
- Python `3.13+`（见 `.python-version` / `pyproject.toml`）
- 已安装 Microsoft Edge（Stable/Canary/Dev/Beta）

## ⚡️ 快速开始（uv）
1. 安装 uv（PowerShell，一次性）：`irm https://astral.sh/uv/install.ps1 | iex`（其他 shell 请参考 uv 文档）。
2. 安装依赖（自动创建虚拟环境）：`uv sync`。
3. 运行脚本：`uv run main.py`。
4. 补丁过程中 Edge 会被关闭；重启后根据提示按 Enter 结束。

## ⚡️ 快速开始（pip）
1. 创建并激活虚拟环境。
2. 安装依赖：`python -m pip install psutil`。
3. 运行：`python main.py`。

## 🔧 做了什么
- 自动定位 Windows / macOS / Linux 上的 Edge Stable / Canary / Dev / Beta 用户数据目录。
- 关闭顶层 Edge 进程以避免文件锁，再在补丁后恢复。
- 在 `Local State` 写入 `variations_country: "US"`。
- 在所有配置目录（`Default`、`Profile X`）的 `Preferences` 中写入 `browser.chat_ip_eligibility_status: true`。
- 重启补丁前已运行的 Edge 版本。

## ⚠️ 已知限制 / 注意事项
- 脚本假设 `User Data/Local State` 已存在且包含 `variations_country`；若缺失可能直接失败（可先启动一次 Edge 生成配置）。
- 只有在能从进程信息中取到可执行文件路径时，脚本才会自动重启 Edge。
- macOS 上按进程名（`Microsoft Edge*`）识别，可能会终止不止“顶层”应用进程。
- Linux 上按可执行文件名 `msedge` 识别；若你的发行版/安装方式使用其他名字，可能不会关闭 Edge（从而仍可能有文件锁）。

## 🛟 注意
- 脚本会修改现有 Edge 配置，如需保险请先备份 `User Data`。
- 使用拥有该 Edge 配置的同一系统用户运行，确保有写入权限。
- 与 Microsoft 无关，风险自担。
