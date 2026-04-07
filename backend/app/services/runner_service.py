"""Sandboxed-ish python runner. Local only — no auth, single-user dev tool."""
import asyncio
import sys
import tempfile
import os


async def run_python(code: str, timeout: float = 5.0) -> tuple[str, str, int]:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return "", f"Timed out after {timeout}s", 124
        return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode or 0
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
