#!/usr/bin/env python3
"""Check whether the AMD VM is ready for ingestion smoke testing.

This CLI catches the simple setup mistakes that waste the most time on the
shared AMD VM: missing `.env` values, missing local commands, missing repo
scripts, and optionally unhealthy Qdrant/Gateway endpoints. It does not start
containers or mutate data; it only reports readiness.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_ENV_PATH = ".env"
DEFAULT_GATEWAY_URL = "http://localhost:8080"
DEFAULT_QDRANT_URL = "http://localhost:6333"

REQUIRED_ENV_VARS = (
    "HF_TOKEN",
    "SEC_USER_AGENT",
    "INFERENCE_GATEWAY_URL",
    "QDRANT_URL",
    "QDRANT_COLLECTION",
    "SQLITE_DB_PATH",
)
SENSITIVE_ENV_VARS = {"HF_TOKEN", "AGENT_API_KEY"}
PLACEHOLDER_MARKERS = (
    "<",
    ">",
    "your-email@example.com",
    "your-huggingface-token",
    "your_huggingface_token",
)
REQUIRED_PATHS = (
    "infra/schema.sql",
    "infra/amd-gpu/docker-compose.yml",
    "infra/qdrant/init_collection.py",
    "services/ingestion-worker/ingest.py",
    "services/ingestion-worker/requirements.txt",
    "services/inference-gateway/requirements.txt",
)
REQUIRED_COMMANDS = ("docker", "python3", "sqlite3", "curl")
ROCM_COMMAND = "rocm-smi"


@dataclass(frozen=True)
class CheckResult:
    """One preflight check result.

    `level` is either `error` or `warning`. Errors make the CLI exit nonzero;
    warnings are useful signals but do not block local dry runs.
    """

    name: str
    ok: bool
    level: str
    message: str


def parse_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        raise FileNotFoundError(f"env file not found: {env_path}")

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = strip_inline_comment(value.strip()).strip("'\"")
        values[key] = value
    return values


def strip_inline_comment(value: str) -> str:
    if value.startswith("#"):
        return ""
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].strip()


def mask_env_value(name: str, value: str) -> str:
    if not value:
        return "<empty>"
    if name in SENSITIVE_ENV_VARS:
        return value[:4] + "..." if len(value) > 4 else "****"
    return value


def looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def validate_env_values(env_values: dict[str, str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name in REQUIRED_ENV_VARS:
        value = env_values.get(name, "")
        if name not in env_values:
            results.append(
                CheckResult(
                    name=f"env:{name}",
                    ok=False,
                    level="error",
                    message=f"{name} is missing from .env",
                )
            )
            continue
        if looks_like_placeholder(value):
            results.append(
                CheckResult(
                    name=f"env:{name}",
                    ok=False,
                    level="error",
                    message=f"{name} is unset or still a placeholder",
                )
            )
            continue
        results.append(
            CheckResult(
                name=f"env:{name}",
                ok=True,
                level="error",
                message=f"{name}={mask_env_value(name, value)}",
            )
        )

    user_agent = env_values.get("SEC_USER_AGENT", "")
    if user_agent and not re.search(r"[^@\s]+@[^@\s]+\.[^@\s]+", user_agent):
        results.append(
            CheckResult(
                name="env:SEC_USER_AGENT_EMAIL",
                ok=False,
                level="error",
                message="SEC_USER_AGENT must include a real contact email",
            )
        )
    return results


def check_env_file(env_path: Path) -> list[CheckResult]:
    try:
        values = parse_env_file(env_path)
    except FileNotFoundError as exc:
        return [
            CheckResult(
                name="env:file",
                ok=False,
                level="error",
                message=str(exc),
            )
        ]

    results = [
        CheckResult(
            name="env:file",
            ok=True,
            level="error",
            message=f"loaded {env_path}",
        )
    ]
    results.extend(validate_env_values(values))
    return results


def check_required_paths(repo_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative_path in REQUIRED_PATHS:
        path = repo_root / relative_path
        results.append(
            CheckResult(
                name=f"path:{relative_path}",
                ok=path.exists(),
                level="error",
                message="found" if path.exists() else f"missing {relative_path}",
            )
        )
    return results


def check_required_commands(require_rocm: bool = False) -> list[CheckResult]:
    results = [
        CheckResult(
            name=f"command:{command}",
            ok=shutil.which(command) is not None,
            level="error",
            message="found" if shutil.which(command) else f"{command} not found",
        )
        for command in REQUIRED_COMMANDS
    ]
    rocm_found = shutil.which(ROCM_COMMAND) is not None
    results.append(
        CheckResult(
            name=f"command:{ROCM_COMMAND}",
            ok=rocm_found,
            level="error" if require_rocm else "warning",
            message=(
                "found"
                if rocm_found
                else f"{ROCM_COMMAND} not found; expected on the AMD VM"
            ),
        )
    )
    return results


def request_json(url: str, timeout: float = 5.0) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed with {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc


def check_qdrant_health(qdrant_url: str, timeout: float = 5.0) -> CheckResult:
    health_url = f"{qdrant_url.rstrip('/')}/healthz"
    try:
        request_json(health_url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - surfaced as a preflight failure
        return CheckResult(
            name="online:qdrant",
            ok=False,
            level="error",
            message=str(exc),
        )
    return CheckResult(
        name="online:qdrant",
        ok=True,
        level="error",
        message=f"healthy at {health_url}",
    )


def check_gateway_health(gateway_url: str, timeout: float = 5.0) -> CheckResult:
    health_url = f"{gateway_url.rstrip('/')}/health"
    try:
        payload = request_json(health_url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - surfaced as a preflight failure
        return CheckResult(
            name="online:gateway",
            ok=False,
            level="error",
            message=str(exc),
        )

    status = str(payload.get("status", "unknown"))
    return CheckResult(
        name="online:gateway",
        ok=True,
        level="error",
        message=f"responded at {health_url} with status={status}",
    )


def collect_checks(
    *,
    repo_root: Path,
    env_path: Path,
    online: bool,
    require_rocm: bool,
    gateway_url: str,
    qdrant_url: str,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(check_env_file(env_path))
    results.extend(check_required_paths(repo_root))
    results.extend(check_required_commands(require_rocm=require_rocm))
    if online:
        results.append(check_qdrant_health(qdrant_url))
        results.append(check_gateway_health(gateway_url))
    return results


def has_blocking_failures(results: list[CheckResult]) -> bool:
    return any(result.level == "error" and not result.ok for result in results)


def format_result(result: CheckResult) -> str:
    if result.ok:
        status = "PASS"
    elif result.level == "warning":
        status = "WARN"
    else:
        status = "FAIL"
    return f"[{status}] {result.name}: {result.message}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight-check the AMD VM before ingestion smoke testing."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path. Defaults to the current directory.",
    )
    parser.add_argument(
        "--env-path",
        default=DEFAULT_ENV_PATH,
        help=f"Path to .env. Defaults to {DEFAULT_ENV_PATH}.",
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="Also check live Qdrant and Inference Gateway health endpoints.",
    )
    parser.add_argument(
        "--require-rocm",
        action="store_true",
        help="Treat missing rocm-smi as an error instead of a warning.",
    )
    parser.add_argument(
        "--gateway-url",
        default=DEFAULT_GATEWAY_URL,
        help=f"Inference Gateway URL. Defaults to {DEFAULT_GATEWAY_URL}.",
    )
    parser.add_argument(
        "--qdrant-url",
        default=DEFAULT_QDRANT_URL,
        help=f"Qdrant URL. Defaults to {DEFAULT_QDRANT_URL}.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    env_path = Path(args.env_path)
    if not env_path.is_absolute():
        env_path = repo_root / env_path

    results = collect_checks(
        repo_root=repo_root,
        env_path=env_path,
        online=args.online,
        require_rocm=args.require_rocm,
        gateway_url=args.gateway_url,
        qdrant_url=args.qdrant_url,
    )

    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        for result in results:
            print(format_result(result))

    return 1 if has_blocking_failures(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
