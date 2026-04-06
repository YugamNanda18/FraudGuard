"""Sandbox execution engine -- ephemeral Docker containers with security isolation.

Implements ADR-004 (Sandboxing Strategy): Docker containers with seccomp,
capabilities drop, network isolation, and resource limits.

Agents Harvey, Jessica, Mike, and Rachel use this engine to execute
untrusted code in a fully isolated environment.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path

import docker
import docker.errors
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SandboxResult(BaseModel):
    """Result of a sandboxed execution."""

    exit_code: int
    stdout: str
    stderr: str
    output_files: dict[str, bytes] = {}
    duration_seconds: float
    timed_out: bool = False

    model_config = {"arbitrary_types_allowed": True}


class SandboxEngine:
    """Executes code in ephemeral Docker containers with security isolation.

    Each execution creates a new container, copies input files, runs the code,
    retrieves outputs, and destroys the container.  The container is **always**
    removed in a ``finally`` block to prevent resource leaks.

    Security posture (per ADR-004):
      - ``network_disabled=True`` (no network by default)
      - ``cap_drop=["ALL"]`` (no Linux capabilities)
      - ``security_opt=["no-new-privileges"]`` (prevent privilege escalation)
      - ``mem_limit`` / ``cpu_count`` enforced via cgroups
      - ``pids_limit=256`` to prevent fork bombs
      - Non-root user inside the container
    """

    SANDBOX_IMAGE: str = "fraudai-sandbox:latest"
    DEFAULT_TIMEOUT: int = 600  # 10 minutes (SEC-001)
    DEFAULT_MEM_LIMIT: str = "8g"
    DEFAULT_CPU_COUNT: int = 4
    WORKSPACE_DIR: str = "/workspace"
    OUTPUT_DIR: str = "/workspace/output"

    def __init__(
        self,
        docker_client: docker.DockerClient | None = None,
        image: str = SANDBOX_IMAGE,
        timeout: int = DEFAULT_TIMEOUT,
        mem_limit: str = DEFAULT_MEM_LIMIT,
        cpu_count: int = DEFAULT_CPU_COUNT,
        network_disabled: bool = True,
    ) -> None:
        self._client = docker_client or docker.from_env()
        self._image = image
        self._timeout = timeout
        self._mem_limit = mem_limit
        self._cpu_count = cpu_count
        self._network_disabled = network_disabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_python(
        self,
        code: str,
        input_files: dict[str, bytes] | None = None,
        timeout: int | None = None,
    ) -> SandboxResult:
        """Execute Python code in a sandboxed container.

        Args:
            code: Python source code to execute.
            input_files: Mapping of ``{filename: content}`` placed in
                ``/workspace/`` before execution.
            timeout: Override the default timeout (seconds).

        Returns:
            :class:`SandboxResult` with stdout, stderr, exit_code,
            output_files, and timing information.
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        command = ["python", "-c", code]
        return await self._run_container(
            command=command,
            input_files=input_files,
            timeout=effective_timeout,
        )

    async def execute_script(
        self,
        script_path: str,
        args: list[str] | None = None,
        input_files: dict[str, bytes] | None = None,
        timeout: int | None = None,
    ) -> SandboxResult:
        """Execute a pre-built analysis script in the sandbox.

        The script must already exist inside the sandbox image.

        Args:
            script_path: Path to the script **inside the container**.
            args: Command-line arguments forwarded to the script.
            input_files: Mapping of ``{filename: content}`` placed in
                ``/workspace/`` before execution.
            timeout: Override the default timeout (seconds).

        Returns:
            :class:`SandboxResult` with stdout, stderr, exit_code,
            output_files, and timing information.
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        command = ["python", script_path, *(args or [])]
        return await self._run_container(
            command=command,
            input_files=input_files,
            timeout=effective_timeout,
        )

    async def health_check(self) -> bool:
        """Check that Docker is reachable and the sandbox image exists.

        Returns:
            ``True`` if Docker responds to ``ping()`` and the configured
            sandbox image is present locally.
        """
        try:
            ping_ok: bool = await asyncio.to_thread(self._client.ping)
            if not ping_ok:
                return False
            await asyncio.to_thread(self._client.images.get, self._image)
            return True
        except (docker.errors.APIError, docker.errors.ImageNotFound):
            logger.warning("Sandbox health check failed: image '%s' not found", self._image)
            return False
        except Exception:
            logger.exception("Sandbox health check failed unexpectedly")
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_container(
        self,
        command: list[str],
        input_files: dict[str, bytes] | None,
        timeout: int,
    ) -> SandboxResult:
        """Create an ephemeral container, run *command*, and return results.

        The container is **always** removed in a ``finally`` block regardless
        of success, failure, or timeout.
        """
        container: docker.models.containers.Container | None = None
        tmpdir_obj = tempfile.TemporaryDirectory(prefix="fraudai-sandbox-")
        tmpdir = Path(tmpdir_obj.name)

        try:
            # --- Write input files to a host tmpdir ----------------------
            workspace_host = tmpdir / "workspace"
            workspace_host.mkdir()
            output_host = workspace_host / "output"
            output_host.mkdir()

            if input_files:
                for filename, content in input_files.items():
                    dest = workspace_host / filename
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)

            # --- Create and start container ------------------------------
            container = await asyncio.to_thread(
                self._client.containers.create,
                image=self._image,
                command=command,
                network_disabled=self._network_disabled,
                mem_limit=self._mem_limit,
                memswap_limit=self._mem_limit,  # No swap
                cpu_count=self._cpu_count,
                pids_limit=256,
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
                volumes={
                    str(workspace_host): {
                        "bind": self.WORKSPACE_DIR,
                        "mode": "rw",
                    },
                },
                working_dir=self.WORKSPACE_DIR,
                detach=True,
            )

            logger.info(
                "Sandbox container %s created (image=%s, timeout=%ds)",
                container.short_id,
                self._image,
                timeout,
            )

            await asyncio.to_thread(container.start)
            start_time = time.monotonic()

            # --- Wait for completion or timeout --------------------------
            timed_out = False
            try:
                wait_result: dict = await asyncio.to_thread(
                    container.wait,
                    timeout=timeout,
                )
                exit_code: int = wait_result.get("StatusCode", -1)
            except Exception:
                # Timeout or unexpected error -- kill the container
                timed_out = True
                exit_code = -1
                logger.warning(
                    "Sandbox container %s timed out after %ds, stopping",
                    container.short_id,
                    timeout,
                )
                try:
                    await asyncio.to_thread(container.stop, timeout=5)
                except Exception:
                    logger.debug(
                        "Failed to stop container %s gracefully, will force-remove",
                        container.short_id,
                    )

            duration = time.monotonic() - start_time

            # --- Collect stdout / stderr ---------------------------------
            stdout_bytes: bytes = await asyncio.to_thread(
                container.logs, stdout=True, stderr=False,
            )
            stderr_bytes: bytes = await asyncio.to_thread(
                container.logs, stdout=False, stderr=True,
            )

            # --- Collect output files from /workspace/output/ ------------
            collected_files: dict[str, bytes] = {}
            for fpath in output_host.rglob("*"):
                if fpath.is_file():
                    relative = fpath.relative_to(output_host)
                    collected_files[str(relative)] = fpath.read_bytes()

            logger.info(
                "Sandbox container %s finished "
                "(exit_code=%d, duration=%.2fs, timed_out=%s, output_files=%d)",
                container.short_id,
                exit_code,
                duration,
                timed_out,
                len(collected_files),
            )

            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                output_files=collected_files,
                duration_seconds=round(duration, 3),
                timed_out=timed_out,
            )

        finally:
            # --- ALWAYS remove the container -----------------------------
            if container is not None:
                try:
                    await asyncio.to_thread(container.remove, force=True)
                    logger.debug("Sandbox container %s removed", container.short_id)
                except Exception:
                    logger.exception("Failed to remove sandbox container %s", container.short_id)

            # --- Cleanup host tmpdir -------------------------------------
            try:
                tmpdir_obj.cleanup()
            except Exception:
                logger.debug("Tmpdir cleanup failed for %s", tmpdir)
