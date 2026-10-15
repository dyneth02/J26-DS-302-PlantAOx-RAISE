"""Shared helper for invoking Linux-only bioinformatics tools (CD-HIT,
GraphPart/EMBOSS) from Windows via WSL.

These tools are installed in a user-space micromamba environment
(``pu_aop``) inside WSL Ubuntu, not system-wide -- the CI/dev machine's WSL
distro has no root access available to this pipeline, so `apt install` was
not an option. See IMPLEMENTATION_STATUS.md for the exact setup steps if
this environment needs to be recreated.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

WSL_DISTRO = "Ubuntu"
CONDA_ENV = "pu_aop"
MAMBA_ROOT_PREFIX = "$HOME/micromamba"
MICROMAMBA_BIN = "$HOME/micromamba/bin/micromamba"


def to_wsl_path(windows_path: Path) -> str:
    """Translate an absolute Windows path to its /mnt/<drive>/... WSL path."""
    resolved = Path(windows_path).resolve()
    drive_letter = resolved.drive.rstrip(":").lower()
    rest = str(resolved)[len(resolved.drive) + 1 :].replace("\\", "/")
    return f"/mnt/{drive_letter}/{rest}"


def run_in_conda_env(
    args: list[str],
    env_name: str = CONDA_ENV,
    wsl_distro: str = WSL_DISTRO,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    """Run ``args`` (e.g. ["cd-hit", "-i", ..., "-o", ...]) inside the WSL
    micromamba environment. Each arg is shell-quoted individually so paths
    containing spaces (this repo lives under "SLIIT Research") survive the
    trip through `bash -lc`.
    """
    quoted_args = " ".join(shlex.quote(a) for a in args)
    inner_cmd = (
        f"export MAMBA_ROOT_PREFIX={MAMBA_ROOT_PREFIX}; "
        f"{MICROMAMBA_BIN} run -n {env_name} {quoted_args}"
    )
    cmd = ["wsl.exe", "-d", wsl_distro, "-e", "bash", "-lc", inner_cmd]
    # WSL subprocesses emit UTF-8; subprocess.run's text=True otherwise
    # decodes with the Windows console's locale encoding (cp1252 here),
    # which crashes on non-ASCII bytes some Linux tools print (GraphPart's
    # progress output included).
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )


def check_tool_available(tool: str, env_name: str = CONDA_ENV, wsl_distro: str = WSL_DISTRO) -> bool:
    # `which` is a real executable (unlike the `command` shell builtin), so it
    # can be exec'd directly by `micromamba run` without an extra shell layer.
    result = run_in_conda_env(["which", tool], env_name, wsl_distro)
    return result.returncode == 0 and bool(result.stdout.strip())
