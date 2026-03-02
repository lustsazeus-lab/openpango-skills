#!/usr/bin/env python3
"""
skills/data-analysis/sandbox.py

Secure-ish data-analysis sandbox for running untrusted Python snippets with:
- subprocess isolation
- timeout / resource limits
- blocked outbound networking
- filesystem confinement to sandbox run directory
- CSV/JSON input mounting
- stdout/stderr capture
- base64 chart extraction

Note: This is a defense-in-depth sandbox for agent workflows, not a kernel-grade
container boundary. For high-risk workloads, run this inside an additional OS/
container sandbox.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MEMORY_LIMIT_MB = 512
DEFAULT_CPU_TIME_SECONDS = 15
MAX_STDIO_BYTES = 1_000_000
MAX_CHARTS = 10
CHART_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
ALLOWED_INPUT_SUFFIXES = {".csv", ".json"}


@dataclass
class SandboxConfig:
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB
    cpu_time_seconds: int = DEFAULT_CPU_TIME_SECONDS
    max_stdio_bytes: int = MAX_STDIO_BYTES
    cleanup: bool = True


class DataAnalysisSandbox:
    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
        python_executable: Optional[str] = None,
    ) -> None:
        self.config = config or SandboxConfig()
        self.python_executable = python_executable or os.environ.get("PYTHON", "python3")

    def execute(
        self,
        script: str,
        input_files: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute analysis script in an isolated run directory.

        Args:
            script: Python script source.
            input_files: iterable of CSV/JSON file paths to mount read-only.

        Returns:
            Structured result with status, stdout/stderr, and encoded charts.
        """
        run_dir = Path(tempfile.mkdtemp(prefix="openpango_data_analysis_"))
        input_dir = run_dir / "input"
        output_dir = run_dir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        user_script_path = run_dir / "user_script.py"
        runner_path = run_dir / "runner.py"

        try:
            mounted_inputs = self._mount_input_files(input_dir, input_files or [])
            user_script_path.write_text(script, encoding="utf-8")
            runner_path.write_text(self._build_runner_source(), encoding="utf-8")

            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUNBUFFERED": "1",
                "MPLBACKEND": "Agg",
                "OPENPANGO_SANDBOX_ROOT": str(run_dir),
                "OPENPANGO_SANDBOX_INPUT": str(input_dir),
                "OPENPANGO_SANDBOX_OUTPUT": str(output_dir),
            }

            command = [
                self.python_executable,
                "-I",  # isolated mode
                str(runner_path),
                str(user_script_path),
            ]

            result = subprocess.run(
                command,
                cwd=str(run_dir),
                env=env,
                capture_output=True,
                timeout=self.config.timeout_seconds,
                preexec_fn=self._build_preexec_fn(),
            )

            stdout = self._trim_bytes(result.stdout, self.config.max_stdio_bytes)
            stderr = self._trim_bytes(result.stderr, self.config.max_stdio_bytes)

            charts = self._collect_charts(output_dir)

            return {
                "status": "success" if result.returncode == 0 else "error",
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "mounted_inputs": mounted_inputs,
                "charts": charts,
            }

        except subprocess.TimeoutExpired as exc:
            return {
                "status": "timeout",
                "exit_code": None,
                "stdout": self._trim_bytes(exc.stdout or b"", self.config.max_stdio_bytes),
                "stderr": self._trim_bytes(exc.stderr or b"", self.config.max_stdio_bytes),
                "mounted_inputs": [],
                "charts": [],
                "error": f"execution exceeded timeout ({self.config.timeout_seconds}s)",
            }
        finally:
            if self.config.cleanup:
                shutil.rmtree(run_dir, ignore_errors=True)

    def _mount_input_files(self, input_dir: Path, input_files: Iterable[str]) -> List[str]:
        mounted: List[str] = []
        for raw_path in input_files:
            src = Path(raw_path).expanduser().resolve()
            if not src.exists() or not src.is_file():
                raise FileNotFoundError(f"Input file not found: {src}")
            if src.suffix.lower() not in ALLOWED_INPUT_SUFFIXES:
                raise ValueError(
                    f"Input file type not allowed: {src.name} (allowed: {sorted(ALLOWED_INPUT_SUFFIXES)})"
                )
            dst = input_dir / src.name
            shutil.copy2(src, dst)
            mounted.append(src.name)
        return mounted

    def _collect_charts(self, output_dir: Path) -> List[Dict[str, Any]]:
        charts: List[Dict[str, Any]] = []
        for path in sorted(output_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in CHART_SUFFIXES:
                continue
            payload = path.read_bytes()
            mime, _ = mimetypes.guess_type(path.name)
            charts.append(
                {
                    "filename": path.name,
                    "mime_type": mime or "application/octet-stream",
                    "base64": base64.b64encode(payload).decode("ascii"),
                    "size_bytes": len(payload),
                }
            )
            if len(charts) >= MAX_CHARTS:
                break
        return charts

    @staticmethod
    def _trim_bytes(value: bytes, max_len: int) -> str:
        return value[:max_len].decode("utf-8", errors="replace")

    def _build_preexec_fn(self):
        """Apply Unix resource limits in child process where supported."""

        def _apply_limits() -> None:
            try:
                import resource

                cpu = max(1, int(self.config.cpu_time_seconds))
                mem = max(64, int(self.config.memory_limit_mb)) * 1024 * 1024

                resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
                resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
                resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            except Exception:
                # Keep sandbox functional on non-Unix or limited runtimes.
                pass

        return _apply_limits

    @staticmethod
    def _build_runner_source() -> str:
        """Runner source executed in isolated subprocess."""
        return r'''#!/usr/bin/env python3
import builtins
import contextlib
import io
import os
import pathlib
import runpy
import socket
import subprocess
import sys
import traceback

SANDBOX_ROOT = os.path.realpath(os.environ["OPENPANGO_SANDBOX_ROOT"])
INPUT_DIR = os.path.realpath(os.environ["OPENPANGO_SANDBOX_INPUT"])
OUTPUT_DIR = os.path.realpath(os.environ["OPENPANGO_SANDBOX_OUTPUT"])


def _is_within(base: str, target: str) -> bool:
    base = os.path.realpath(base)
    target = os.path.realpath(target)
    return target == base or target.startswith(base + os.sep)


def _resolve_path(p: str) -> str:
    candidate = p
    if not os.path.isabs(candidate):
        candidate = os.path.join(os.getcwd(), candidate)
    return os.path.realpath(candidate)


_real_open = builtins.open
_real_os_open = os.open


def _guard_file_path(path: str, mode: str = "r") -> str:
    resolved = _resolve_path(path)
    write_mode = any(flag in mode for flag in ("w", "a", "x", "+"))

    if write_mode:
        if not _is_within(OUTPUT_DIR, resolved):
            raise PermissionError(f"write denied outside OUTPUT_DIR: {path}")
    else:
        if not _is_within(SANDBOX_ROOT, resolved):
            raise PermissionError(f"read denied outside sandbox: {path}")

    return resolved


def _safe_open(file, mode="r", *args, **kwargs):
    if isinstance(file, (str, bytes, os.PathLike)):
        file = _guard_file_path(os.fspath(file), mode)
    return _real_open(file, mode, *args, **kwargs)


def _safe_os_open(path, flags, mode=0o777, *, dir_fd=None):
    # Convert POSIX open flags to write/read intent.
    is_write = bool(
        flags & os.O_WRONLY
        or flags & os.O_RDWR
        or flags & os.O_APPEND
        or flags & os.O_CREAT
        or flags & os.O_TRUNC
    )
    access_mode = "w" if is_write else "r"
    safe_path = _guard_file_path(os.fspath(path), access_mode)
    return _real_os_open(safe_path, flags, mode, dir_fd=dir_fd)


builtins.open = _safe_open
os.open = _safe_os_open


# Block obvious shell/subprocess breakout routes.
def _blocked(*_args, **_kwargs):
    raise PermissionError("process/network operations are blocked inside data-analysis sandbox")


subprocess.Popen = _blocked
subprocess.run = _blocked
subprocess.call = _blocked
subprocess.check_call = _blocked
subprocess.check_output = _blocked
os.system = _blocked


# Block outbound network operations.
class _BlockedSocket:
    def __init__(self, *_args, **_kwargs):
        raise PermissionError("network access denied in data-analysis sandbox")


socket.socket = _BlockedSocket
socket.create_connection = _blocked
socket.socketpair = _blocked


# Patch selected mutating os helpers.
def _guard_mutation_path(path):
    rp = _resolve_path(path)
    if not _is_within(SANDBOX_ROOT, rp):
        raise PermissionError(f"mutation denied outside sandbox: {path}")
    return rp


_real_remove = os.remove
_real_unlink = os.unlink
_real_mkdir = os.mkdir
_real_makedirs = os.makedirs
_real_rename = os.rename
_real_replace = os.replace
_real_rmdir = os.rmdir


os.remove = lambda p, *a, **k: _real_remove(_guard_mutation_path(p), *a, **k)
os.unlink = lambda p, *a, **k: _real_unlink(_guard_mutation_path(p), *a, **k)
os.mkdir = lambda p, *a, **k: _real_mkdir(_guard_mutation_path(p), *a, **k)
os.makedirs = lambda p, *a, **k: _real_makedirs(_guard_mutation_path(p), *a, **k)
os.rename = lambda src, dst, *a, **k: _real_rename(_guard_mutation_path(src), _guard_mutation_path(dst), *a, **k)
os.replace = lambda src, dst, *a, **k: _real_replace(_guard_mutation_path(src), _guard_mutation_path(dst), *a, **k)
os.rmdir = lambda p, *a, **k: _real_rmdir(_guard_mutation_path(p), *a, **k)


# Help user code discover where to read/write.
os.chdir(SANDBOX_ROOT)


def main():
    if len(sys.argv) != 2:
        print("usage: runner.py <script_path>", file=sys.stderr)
        return 2

    script_path = sys.argv[1]

    # Expose convenience globals to executed script.
    globals_patch = {
        "INPUT_DIR": INPUT_DIR,
        "OUTPUT_DIR": OUTPUT_DIR,
        "SANDBOX_ROOT": SANDBOX_ROOT,
    }

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                source = f.read()

            code = compile(source, script_path, "exec")
            scope = {"__name__": "__main__", "__file__": script_path, **globals_patch}
            exec(code, scope, scope)
            exit_code = 0
        except Exception:
            traceback.print_exc()
            exit_code = 1

    sys.stdout.write(stdout_buffer.getvalue())
    sys.stderr.write(stderr_buffer.getvalue())
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
'''


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenPango data-analysis sandbox runner")
    parser.add_argument("script", help="Path to user Python script")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="CSV/JSON file to mount into sandbox input/",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)

    args = parser.parse_args()

    script_source = Path(args.script).read_text(encoding="utf-8")
    sandbox = DataAnalysisSandbox(config=SandboxConfig(timeout_seconds=args.timeout, cleanup=False))
    result = sandbox.execute(script_source, input_files=args.input)
    print(json.dumps(result, indent=2))
