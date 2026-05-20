# Enable Chrome AI ✨

由 [lcandy2](https://twitter.com/vanillaCitron) 研究并制作脚本。

[![Twitter](https://img.shields.io/twitter/follow/vanillaCitron)](https://twitter.com/vanillaCitron)

[English](README.md) | 中文

在 Google Chrome 中启用 Gemini、AI 历史搜索、DevTools AI 等创新功能——无需清除数据或重新安装。

<img width="512" alt="Google Chrome Gemini in Chrome" src="https://github.com/user-attachments/assets/a88c56a7-f20b-432a-926c-0184194225b4" />

轻量 Python 脚本，通过修改本地 Chrome 状态和 profile 偏好设置，并用当前 Glic 检查需要的启动参数重启 Chrome 来启用浏览器内置 AI 功能。

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

## 🔧 做了什么
- 自动定位 Windows / macOS / Linux 上的 Chrome Stable / Canary / Dev / Beta 用户数据目录。
- 关闭顶层 Chrome 进程以避免文件锁，再在补丁后恢复。
- 在 `Local State` 中递归查找并将所有 `is_glic_eligible` 设为 `true`。
- 在 `Local State` 中将 `variations_country` 设为 `"us"`。
- 在 `Local State` 中将 `variations_permanent_consistency_country` 设为 `["<版本号>", "us"]`。
- 在 `Local State` 中将 `variations_permanent_overridden_country` 设为 `"us"`。
- 在 `Local State` 中将 safe-seed 国家值（`variations_safe_seed_permanent_consistency_country` 和 `variations_safe_seed_session_consistency_country`）设为 `"us"`。
- 在保留已有 flags 的同时，把当前 Glic 相关项追加到 `browser.enabled_labs_experiments`。
- 遍历真实 profile 的 `Preferences`，写入当前 Glic/Gemini 入口相关偏好：`sync.glic_rollout_eligibility`、`browser.gemini_settings` 和 `glic.pinned_to_tabstrip`。
- 用 `--variations-override-country=us`、`--glic-dev` 和 `--disable-features=GlicUseSessionCountryForFiltering` 重启补丁前已运行的 Chrome 版本。

## ⚠️ 已知限制 / 注意事项
- 脚本假设 `User Data/Local State` 已存在；若缺失可能直接失败（可先启动一次 Chrome 生成配置）。
- 只有在能从进程信息中取到可执行文件路径时，脚本才会自动重启 Chrome。
- 如果运行脚本时 Chrome 没有启动，请使用脚本打印出的启动参数手动启动 Chrome。
- Gemini in Chrome 仍可能被 Google 账号资格、登录状态、企业策略、账号地区或服务端灰度规则阻止。
- macOS 上仅按已知顶层 Chrome 应用进程名识别。
- Linux 上按可执行文件名 `chrome` 识别；若你的发行版/安装方式使用其他名字，可能不会关闭 Chrome（从而仍可能有文件锁）。

## 🛟 注意
- 脚本会修改现有 Chrome 配置，如需保险请先备份 `User Data`。
- 使用拥有该 Chrome 配置的同一系统用户运行，确保有写入权限。
- 与 Google 无关，风险自担。

## 📜 许可
转载或基于本研究二次创作需要注明来源。

## 🙏 致谢
- [show-copilot](https://github.com/hzkaai/show-copilot)
