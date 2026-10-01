# Dentiva Pro — Developer environment (Phase 1)

## 1. Supported workstation for the product
Windows 10 (1809+) / Windows 11, x64. No Python installed by the end user — the
frozen application ships its own interpreter inside the installer.

## 2. Development workstation
Python 3.11, `pip`, git. Layout after `tools/dev/setup_headless_linux.sh` (Linux) or
`python -m venv .venv && pip install -r requirements-dev.txt` (Windows):

```
requirements.txt          # production runtime deps (pinned)
requirements-dev.txt      # -r requirements.txt + ruff, mypy, pytest, pytest-qt, ...
requirements-build.txt    # -r requirements.txt + PyInstaller (+ hashes)
pyproject.toml            # packaging metadata, tool config (ruff/mypy/pytest/coverage)
```

## 3. Headless Linux/CI setup (used by the development sandbox and Linux CI)
`tools/dev/setup_headless_linux.sh`:
1. creates/updates a venv at `$DENTIVA_VENV` (default `/tmp/dentiva-venv`);
2. installs `requirements-dev.txt`;
3. **detects** whether Qt can be imported. If (and only if) `libGL.so.1`,
   `libEGL.so.1`, `libdbus-1.so.3` or `libxkbcommon.so.0` are missing, it builds
   minimal stub shared libraries in `$DENTIVA_STUBS` (default `/tmp/dentiva-stubs`)
   and exports `LD_LIBRARY_PATH` — this lets Qt load for the `offscreen` platform in
   a container without GUI system libraries. On GitHub-hosted Ubuntu runners (which
   have the real libraries and `xvfb`) no stubs are built.
4. downloads/creates the Bengali/Latin test fonts into the cache (via a sparse clone
   of `google/fonts` or a cached copy).

Usage:
```bash
./tools/dev/setup_headless_linux.sh          # create/update env
source /tmp/dentiva-venv/bin/activate
export QT_QPA_PLATFORM=offscreen
pytest -q                                    # non-Qt + Qt-offscreen tests
```

**Important:** stubs are a *development/CI convenience* for headless import and
geometry tests. The Windows release uses genuine Qt binaries, genuine Windows
printing and genuine system fonts — no stub is ever shipped.

## 4. Windows CI capabilities used
`windows-latest` runners provide: the MSVC runtime, the Windows printing subsystem
with **Microsoft Print to PDF** and **Microsoft XPS Document Writer** (used for real
print-path tests), PowerShell for installer assertions, and Inno Setup via
`choco install innosetup`.

## 5. Common commands
```bash
pytest -q                      # default suite (excludes stress/slow)
pytest -m stress               # stress suite (nightly/release)
pytest --cov=dentiva --cov-report=term-missing
ruff check . && ruff format --check .
mypy dentiva
python -m dentiva --version
python -m dentiva --selftest   # headless end-to-end diagnostics (works on any OS)
python tools/build/make_ico.py # regenerate the multi-resolution icon
python tools/trace_report.py   # traceability vs tests; fails on untested requirements
```

## 6. Directory hygiene
- Generated artifacts (`build/`, `dist/`, `.pytest_cache/`, `__pycache__/`,
  `*.pyc`, `coverage.xml`, `.mypy_cache/`, `.ruff_cache/`) are git-ignored, **except**
  the final release `.exe` in `dist/` when the repository fallback is used.
- Developer venvs and stub libraries are created **outside** the repository
  (`/tmp`), so they never enter version control or the patch set.
- Clinic data, logs, drafts and backups live in the per-user data directory and are
  never committed.
