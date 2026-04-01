import json
import subprocess
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "storefront-sandbox"
SANDBOX_TIMEOUT = 10  # seconds


@dataclass
class SandboxResult:
    success: bool
    output: str
    error: str | None


def run_in_sandbox(code: str, provider_data: dict) -> SandboxResult:
    stdin_payload = json.dumps({"code": code, "provider": provider_data})

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--runtime=runsc",
                "--network=none",
                "-i",
                SANDBOX_IMAGE,
            ],
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT,
        )

        if result.returncode != 0:
            error = result.stderr.strip()
            logger.error("Sandbox container failed (exit %d): %s", result.returncode, error)
            return SandboxResult(success=False, output="", error=error)

        output = result.stdout.strip()
        logger.info("Sandbox executed successfully. Output: %r", output)
        return SandboxResult(success=True, output=output, error=None)

    except subprocess.TimeoutExpired:
        logger.error("Sandbox timed out after %ds", SANDBOX_TIMEOUT)
        return SandboxResult(success=False, output="", error=f"Execution timed out after {SANDBOX_TIMEOUT}s")

    except Exception as exc:
        logger.error("Sandbox error: %s", exc, exc_info=True)
        return SandboxResult(success=False, output="", error=str(exc))
