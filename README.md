# Show Copilot ✨

English | [中文](README.zh.md)

Tiny Python helper that nudges Microsoft Edge into Copilot mode by patching your local profile data—no browser flags required.

## ✅ Requirements
- Python `3.13+` (see `.python-version` / `pyproject.toml`)
- Microsoft Edge installed (Stable/Canary/Dev/Beta)

## ⚡️ Quick Start (uv)
1. Install uv (once, PowerShell): `irm https://astral.sh/uv/install.ps1 | iex` (see uv docs for other shells).
2. Install deps (creates venv automatically): `uv sync`.
3. Run the script: `uv run main.py`.
4. Edge will close while patching; after it restarts, press Enter to finish.

## ⚡️ Quick Start (pip)
1. Create and activate a venv.
2. Install deps: `python -m pip install psutil`.
3. Run: `python main.py`.

## 🔧 What Happens
- Finds Edge user data for Stable/Canary/Dev/Beta on Windows, macOS, and Linux.
- Kills top-level Edge processes to avoid file locks, then brings them back.
- Sets `variations_country: "US"` in `Local State`.
- Sets `browser.chat_ip_eligibility_status: true` in every profile `Preferences` (`Default` and `Profile X` folders).
- Restarts any Edge builds that were running before the patch.

## ⚠️ Caveats / Known Limitations
- The script expects `User Data/Local State` to exist and contain `variations_country`; if it’s missing, the run can fail (launch Edge once to generate it).
- Edge restart only happens if the executable path can be detected from running processes.
- On macOS, process detection is name-based (`Microsoft Edge*`) and may terminate more than just the “top-level” app process.
- On Linux, process detection expects an executable name of `msedge`; if your build uses a different name, Edge may not be closed (and files may remain locked).

## 🛟 Notes
- The script writes to your existing Edge profile; back up `User Data` if you want a safety net.
- Run as the same OS user who owns the Edge profile to ensure write access.
- Not affiliated with Microsoft—use at your own risk.
