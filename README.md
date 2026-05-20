# Enable Chrome AI ✨

Researched and scripted by [lcandy2](https://twitter.com/vanillaCitron).

[![Twitter](https://img.shields.io/twitter/follow/vanillaCitron)](https://twitter.com/vanillaCitron)


English | [中文](README.zh.md)

Enable Gemini in Chrome, AI Powered History search, and DevTools AI Innovations in Google Chrome—without cleaning data or reinstalling.

<img width="512" alt="Google Chrome Gemini in Chrome" src="https://github.com/user-attachments/assets/a88c56a7-f20b-432a-926c-0184194225b4" />

Tiny Python helper that enables Chrome's built-in AI features by patching your local Chrome state and profile preferences, then restarting Chrome with the launch args needed by current Glic checks.

## ✅ Requirements
- Python `3.13+` (see `.python-version` / `pyproject.toml`)
- Google Chrome installed (Stable/Canary/Dev/Beta)

## ⚡️ Quick Start (uv)
1. Install uv (once):
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - macOS & Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - See [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for more options.
2. Install deps (creates venv automatically): `uv sync`.
3. Run the script: `uv run main.py`.
4. Chrome will close while patching; after it restarts, press Enter to finish.

## ⚡️ Quick Start (pip)
1. Create and activate a venv.
2. Install deps: `python -m pip install psutil`.
3. Run: `python main.py`.

## 🔧 What Happens
- Finds Chrome user data for Stable/Canary/Dev/Beta on Windows, macOS, and Linux.
- Kills top-level Chrome processes to avoid file locks, then brings them back.
- Sets all `is_glic_eligible` to `true` in `Local State` (recursive search).
- Sets `variations_country` to `"us"` in `Local State`.
- Sets `variations_permanent_consistency_country` to `["<version>", "us"]` in `Local State`.
- Sets `variations_permanent_overridden_country` to `"us"` in `Local State`.
- Sets safe-seed country values (`variations_safe_seed_permanent_consistency_country` and `variations_safe_seed_session_consistency_country`) to `"us"` in `Local State`.
- Adds current Glic entries to `browser.enabled_labs_experiments` while preserving existing flags.
- Patches each real profile `Preferences` file with current Glic/Gemini prefs: `sync.glic_rollout_eligibility`, `browser.gemini_settings`, and `glic.pinned_to_tabstrip`.
- Restarts any Chrome builds that were running before the patch with `--variations-override-country=us`, `--glic-dev`, and `--disable-features=GlicUseSessionCountryForFiltering`.

## ⚠️ Caveats / Known Limitations
- The script expects `User Data/Local State` to exist; if it's missing, the run can fail (launch Chrome once to generate it).
- Chrome restart only happens if the executable path can be detected from running processes.
- If Chrome was not running, start Chrome manually with the launch args printed by the script.
- Gemini in Chrome can still be blocked by Google account eligibility, sign-in state, enterprise policy, account region, or server-side rollout checks.
- On macOS, process detection targets known top-level Chrome app process names.
- On Linux, process detection expects an executable name of `chrome`; if your build uses a different name, Chrome may not be closed (and files may remain locked).

## 🛟 Notes
- The script writes to your existing Chrome profile; back up `User Data` if you want a safety net.
- Run as the same OS user who owns the Chrome profile to ensure write access.
- Not affiliated with Google—use at your own risk.

## 📜 License
Please credit this project when reposting or creating derivative works.

## 🙏 Acknowledgments
- [show-copilot](https://github.com/hzkaai/show-copilot)
