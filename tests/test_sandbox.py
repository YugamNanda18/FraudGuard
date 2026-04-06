"""Tests for the sandbox execution engine.

All Docker SDK interactions are mocked -- no real Docker daemon is required.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fraudai.tools.sandbox import SandboxEngine, SandboxResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_docker_client() -> MagicMock:
    """Return a mock ``docker.DockerClient``."""
    client = MagicMock()
    client.ping.return_value = True
    # Images
    client.images.get.return_value = MagicMock(tags=["fraudai-sandbox:latest"])
    return client


@pytest.fixture()
def mock_container() -> MagicMock:
    """Return a mock Docker container with sane defaults."""
    container = MagicMock()
    container.short_id = "abc123"
    container.start.return_value = None
    container.wait.return_value = {"StatusCode": 0}
    container.logs.return_value = b""
    container.stop.return_value = None
    container.remove.return_value = None
    return container


@pytest.fixture()
def engine(mock_docker_client: MagicMock) -> SandboxEngine:
    """Return a ``SandboxEngine`` with a mocked Docker client."""
    return SandboxEngine(docker_client=mock_docker_client)


# ---------------------------------------------------------------------------
# SandboxResult model
# ---------------------------------------------------------------------------


class TestSandboxResult:
    def test_defaults(self) -> None:
        result = SandboxResult(
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=1.0,
        )
        assert result.exit_code == 0
        assert result.stdout == "ok"
        assert result.stderr == ""
        assert result.output_files == {}
        assert result.timed_out is False

    def test_with_output_files(self) -> None:
        result = SandboxResult(
            exit_code=0,
            stdout="",
            stderr="",
            output_files={"report.json": b'{"ok": true}'},
            duration_seconds=2.5,
        )
        assert "report.json" in result.output_files
        assert result.duration_seconds == 2.5


# ---------------------------------------------------------------------------
# execute_python
# ---------------------------------------------------------------------------


class TestExecutePython:
    async def test_basic_execution(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}

        def _logs_side_effect(stdout: bool = True, stderr: bool = True) -> bytes:
            if stdout and not stderr:
                return b"hello world\n"
            return b""

        mock_container.logs.side_effect = _logs_side_effect

        result = await engine.execute_python("print('hello world')")

        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert result.timed_out is False

        # Container must have been created and started
        mock_docker_client.containers.create.assert_called_once()
        mock_container.start.assert_called_once()
        # Container must ALWAYS be removed
        mock_container.remove.assert_called_once_with(force=True)

    async def test_with_input_files(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        input_files = {
            "data.csv": b"col1,col2\n1,2\n3,4\n",
            "config.json": b'{"threshold": 0.5}',
        }

        result = await engine.execute_python(
            "import pandas as pd; df = pd.read_csv('/workspace/data.csv')",
            input_files=input_files,
        )

        assert result.exit_code == 0
        mock_container.remove.assert_called_once_with(force=True)

    async def test_nonzero_exit_code(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 1}

        def _logs_side_effect(stdout: bool = True, stderr: bool = True) -> bytes:
            if not stdout and stderr:
                return b"NameError: name 'foo' is not defined\n"
            return b""

        mock_container.logs.side_effect = _logs_side_effect

        result = await engine.execute_python("foo()")

        assert result.exit_code == 1
        assert "NameError" in result.stderr
        assert result.timed_out is False
        mock_container.remove.assert_called_once_with(force=True)


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    async def test_container_stopped_on_timeout(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        # Simulate timeout by raising an exception from container.wait
        mock_container.wait.side_effect = Exception("read timeout")
        mock_container.logs.return_value = b""

        result = await engine.execute_python(
            "import time; time.sleep(9999)",
            timeout=5,
        )

        assert result.timed_out is True
        assert result.exit_code == -1
        # Container should be stopped and then removed
        mock_container.stop.assert_called_once_with(timeout=5)
        mock_container.remove.assert_called_once_with(force=True)

    async def test_custom_timeout_passed(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        """When caller provides a custom timeout it overrides the engine default."""
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        await engine.execute_python("pass", timeout=30)

        # wait() should have been called with the custom timeout
        mock_container.wait.assert_called_once_with(timeout=30)


# ---------------------------------------------------------------------------
# Security options
# ---------------------------------------------------------------------------


class TestSecurityOptions:
    async def test_network_disabled(
        self,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        engine = SandboxEngine(docker_client=mock_docker_client, network_disabled=True)
        await engine.execute_python("pass")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["network_disabled"] is True

    async def test_network_enabled_when_configured(
        self,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        engine = SandboxEngine(docker_client=mock_docker_client, network_disabled=False)
        await engine.execute_python("pass")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["network_disabled"] is False

    async def test_cap_drop_all(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        await engine.execute_python("pass")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["cap_drop"] == ["ALL"]

    async def test_no_new_privileges(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        await engine.execute_python("pass")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert "no-new-privileges" in create_kwargs.kwargs["security_opt"]

    async def test_memory_limit(
        self,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        engine = SandboxEngine(docker_client=mock_docker_client, mem_limit="4g")
        await engine.execute_python("pass")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["mem_limit"] == "4g"
        assert create_kwargs.kwargs["memswap_limit"] == "4g"

    async def test_cpu_count(
        self,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        engine = SandboxEngine(docker_client=mock_docker_client, cpu_count=2)
        await engine.execute_python("pass")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["cpu_count"] == 2

    async def test_pids_limit(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        await engine.execute_python("pass")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["pids_limit"] == 256


# ---------------------------------------------------------------------------
# Cleanup -- container must ALWAYS be removed
# ---------------------------------------------------------------------------


class TestCleanup:
    async def test_container_removed_on_success(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        await engine.execute_python("pass")

        mock_container.remove.assert_called_once_with(force=True)

    async def test_container_removed_on_failure(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.return_value = b""

        await engine.execute_python("exit(1)")

        mock_container.remove.assert_called_once_with(force=True)

    async def test_container_removed_on_timeout(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.side_effect = Exception("timeout")
        mock_container.logs.return_value = b""

        await engine.execute_python("pass", timeout=1)

        mock_container.remove.assert_called_once_with(force=True)

    async def test_container_removed_even_if_logs_fail(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        """If collecting logs raises, the container is still removed."""
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = Exception("connection reset")

        with pytest.raises(Exception, match="connection reset"):
            await engine.execute_python("pass")

        mock_container.remove.assert_called_once_with(force=True)


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_healthy(self, engine: SandboxEngine, mock_docker_client: MagicMock) -> None:
        mock_docker_client.ping.return_value = True
        mock_docker_client.images.get.return_value = MagicMock()

        assert await engine.health_check() is True

    async def test_docker_not_running(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
    ) -> None:
        import docker.errors

        mock_docker_client.ping.side_effect = docker.errors.APIError("connection refused")

        assert await engine.health_check() is False

    async def test_image_not_found(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
    ) -> None:
        import docker.errors

        mock_docker_client.ping.return_value = True
        mock_docker_client.images.get.side_effect = docker.errors.ImageNotFound("not found")

        assert await engine.health_check() is False

    async def test_ping_returns_false(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
    ) -> None:
        mock_docker_client.ping.return_value = False

        assert await engine.health_check() is False


# ---------------------------------------------------------------------------
# execute_script
# ---------------------------------------------------------------------------


class TestExecuteScript:
    async def test_basic_script(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        result = await engine.execute_script("/scripts/analyze.py", args=["--mode", "fast"])

        assert result.exit_code == 0
        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["command"] == [
            "python",
            "/scripts/analyze.py",
            "--mode",
            "fast",
        ]
        mock_container.remove.assert_called_once_with(force=True)

    async def test_script_no_args(
        self,
        engine: SandboxEngine,
        mock_docker_client: MagicMock,
        mock_container: MagicMock,
    ) -> None:
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b""

        await engine.execute_script("/scripts/check.py")

        create_kwargs = mock_docker_client.containers.create.call_args
        assert create_kwargs.kwargs["command"] == ["python", "/scripts/check.py"]


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------


class TestEngineDefaults:
    def test_default_values(self, mock_docker_client: MagicMock) -> None:
        engine = SandboxEngine(docker_client=mock_docker_client)
        assert engine._image == "fraudai-sandbox:latest"
        assert engine._timeout == 600
        assert engine._mem_limit == "8g"
        assert engine._cpu_count == 4
        assert engine._network_disabled is True

    def test_custom_values(self, mock_docker_client: MagicMock) -> None:
        engine = SandboxEngine(
            docker_client=mock_docker_client,
            image="custom:v1",
            timeout=120,
            mem_limit="2g",
            cpu_count=1,
            network_disabled=False,
        )
        assert engine._image == "custom:v1"
        assert engine._timeout == 120
        assert engine._mem_limit == "2g"
        assert engine._cpu_count == 1
        assert engine._network_disabled is False
