#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Dentiva Pro — headless Linux development/CI bootstrap.
#
# Creates an isolated virtual environment with the pinned development
# dependencies and makes PySide6 importable on a *headless* machine that has no
# X server and no GUI system libraries (libGL/libEGL/libdbus/libxkbcommon).
#
#   ./tools/dev/setup_headless_linux.sh
#   source /tmp/dentiva-venv/bin/activate
#   export QT_QPA_PLATFORM=offscreen
#   pytest -q
#
# IMPORTANT — scope of the stub libraries
#   When the real system libraries are missing, this script builds *minimal stub
#   shared objects* (a handful of no-op symbols) purely so that the Qt modules
#   can be loaded for OFFSCREEN tests (geometry, layout audit, PDF rendering,
#   screenshot export). They are:
#     * created outside the repository (default: /tmp/dentiva-stubs),
#     * never committed and never shipped,
#     * never used by the Windows release build, which links the genuine Qt
#       binaries, the genuine Windows printing stack and real system fonts.
#   On GitHub-hosted Ubuntu runners (which ship the real libraries and xvfb) no
#   stubs are built at all.
# ---------------------------------------------------------------------------
set -euo pipefail

VENV="${DENTIVA_VENV:-/tmp/dentiva-venv}"
STUBS="${DENTIVA_STUBS:-/tmp/dentiva-stubs}"
FONTS="${DENTIVA_FONTS:-/tmp/dentiva-fonts}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "==> Repository      : ${REPO_ROOT}"
echo "==> Virtualenv      : ${VENV}"
echo "==> Stub dir        : ${STUBS}"

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v gcc >/dev/null    || { echo "gcc is required (only for headless stubs)" >&2; exit 1; }

# ---------------------------------------------------------------- 1. venv ---
if [ ! -x "${VENV}/bin/python" ]; then
  echo "==> Creating virtualenv"
  python3 -m venv "${VENV}"
fi
"${VENV}/bin/python" -m pip install --quiet --upgrade pip setuptools wheel
echo "==> Installing development dependencies"
"${VENV}/bin/python" -m pip install --quiet -r "${REPO_ROOT}/requirements-dev.txt"

# ------------------------------------------------- 2. headless Qt stubs ------
needs_stubs() {
  for lib in libGL.so.1 libEGL.so.1 libdbus-1.so.3 libxkbcommon.so.0; do
    if ! ldconfig -p 2>/dev/null | grep -q "${lib}"; then
      return 0
    fi
  done
  return 1
}

if "${VENV}/bin/python" - <<'PY'
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6 import QtWidgets  # noqa: F401
except Exception:
    raise SystemExit(1)
raise SystemExit(0)
PY
then
  echo "==> Qt imports cleanly — no stubs required"
  exit 0
fi

if ! needs_stubs; then
  echo "!!  Qt failed to import although the system libraries appear present." >&2
  exit 1
fi

echo "==> Building headless stub libraries (dev/test only, never shipped)"
mkdir -p "${STUBS}"
SITE="$("${VENV}/bin/python" -c 'import PySide6,os;print(os.path.dirname(PySide6.__file__))')"

"${VENV}/bin/python" - "${SITE}" "${STUBS}" <<'PY'
import os, re, subprocess, sys

site, stubs = sys.argv[1], sys.argv[2]
so_files = []
for root, _dirs, files in os.walk(site):
    for f in files:
        if f.endswith(".so") or ".so." in f:
            so_files.append(os.path.join(root, f))

symbols = set()
for f in so_files:
    out = subprocess.run(["nm", "-D", "--undefined-only", f],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "U":
            symbols.add(parts[1])

def undefined(prefixes, versioned):
    return sorted({
        s for s in symbols
        if any(s.startswith(p) for p in prefixes)
        and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s.split("@")[0])
        and (("@" in s) == versioned)
    })

def build(libname, names, version=None):
    if not names:
        return 0
    base = libname.replace(".", "_")
    src = os.path.join(stubs, f"stub_{base}.c")
    with open(src, "w") as fh:
        for n in names:
            fh.write(f"long long {n}(void) {{ return 0; }}\n")
    cmd = ["gcc", "-shared", "-fPIC", "-w", "-o", os.path.join(stubs, libname),
           src, "-Wl,-soname," + libname]
    if version:
        vmap = os.path.join(stubs, f"stub_{base}.map")
        with open(vmap, "w") as fh:
            fh.write(f"{version} {{\n  global:\n")
            for n in names:
                fh.write(f"    {n};\n")
            fh.write("  local: *;\n};\n")
        cmd += ["-Wl,--version-script", vmap]
    subprocess.run(cmd, check=True)
    return len(names)

# Versioned symbol groups (map file required for symbol versioning).
by_version = {}
for s in symbols:
    if "@" in s:
        name, ver = s.split("@", 1)
        ver = ver.split("@@")[-1]
        by_version.setdefault(ver, set()).add(name)
total = 0
for ver, names in by_version.items():
    if ver.startswith("LIBDBUS"):
        total += build("libdbus-1.so.3", sorted(names), version=ver)
    elif ver.startswith("V_"):
        n = build("libxkbcommon.so.0", sorted(names), version=ver)
        total += n
# Unversioned groups.
for lib, prefixes in (
    ("libEGL.so.1", ("egl", "EGL", "gl", "glX")),
    ("libGL.so.1", ("gl", "glX")),
):
    if not os.path.exists(os.path.join(stubs, lib)):
        total += build(lib, undefined(prefixes, versioned=False))
print(f"   stub symbols defined: {total}")
PY

# ------------------------------------------------------ 3. verify again ------
export LD_LIBRARY_PATH="${STUBS}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
if QT_QPA_PLATFORM=offscreen "${VENV}/bin/python" - <<'PY'
from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import QCoreApplication
app = QtWidgets.QApplication([])
pix = QtGui.QPixmap(64, 64)
print("   Qt offscreen OK:", QCoreApplication.applicationName() or "(unnamed)", pix.size().width())
PY
then
  echo "==> Headless Qt verified."
  echo "    Use: export LD_LIBRARY_PATH=${STUBS}\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
  echo "         export QT_QPA_PLATFORM=offscreen"
else
  echo "!!  Qt still fails to import in headless mode" >&2
  exit 1
fi

# --------------------------------------------------------- 4. test fonts -----
if [ ! -d "${FONTS}" ]; then
  echo "==> Fetching Unicode test fonts (SIL OFL 1.1) into ${FONTS}"
  mkdir -p "${FONTS}"
  tmp="$(mktemp -d)"
  if git clone --depth 1 --filter=blob:none --sparse https://github.com/google/fonts.git "${tmp}/fonts" >/dev/null 2>&1; then
    ( cd "${tmp}/fonts" && git sparse-checkout set ofl/notosansbengali ofl/notosans >/dev/null 2>&1 || true )
    cp "${tmp}/fonts/ofl/notosansbengali/"*.ttf "${FONTS}/" 2>/dev/null || true
    cp "${tmp}/fonts/ofl/notosans/"NotoSans*.ttf "${FONTS}/" 2>/dev/null || true
    cp "${tmp}/fonts/ofl/notosansbengali/OFL.txt" "${FONTS}/OFL-NotoSansBengali.txt" 2>/dev/null || true
  fi
  rm -rf "${tmp}"
  ls -1 "${FONTS}" 2>/dev/null | sed 's/^/    /'
fi

echo "==> Done."
