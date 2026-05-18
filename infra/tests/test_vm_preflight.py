"""Tests for the AMD VM preflight checker.

The tests keep network and machine-specific checks mocked so the preflight
logic can be trusted before the team runs it on the real AMD VM.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "ops" / "vm_preflight.py"
SPEC = importlib.util.spec_from_file_location("vm_preflight", MODULE_PATH)
assert SPEC is not None
vm_preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = vm_preflight
SPEC.loader.exec_module(vm_preflight)


def write_env(path: Path, **values: str) -> Path:
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def valid_env_values() -> dict[str, str]:
    return {
        "HF_TOKEN": "hf_real_token",
        "SEC_USER_AGENT": "FinContextAgent/0.1 teammate@example.com",
        "INFERENCE_GATEWAY_URL": "http://localhost:8080",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION": "fincontext_chunks",
        "SQLITE_DB_PATH": "./fincontext.db",
    }


def test_parse_env_file_strips_inline_comments(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "HF_TOKEN= # your HuggingFace token\n"
        "QDRANT_COLLECTION=fincontext_chunks # collection name\n",
        encoding="utf-8",
    )

    values = vm_preflight.parse_env_file(env_path)

    assert values["HF_TOKEN"] == ""
    assert values["QDRANT_COLLECTION"] == "fincontext_chunks"


def test_check_env_file_flags_placeholders(tmp_path):
    env_path = write_env(
        tmp_path / ".env",
        HF_TOKEN="",
        SEC_USER_AGENT="FinContextAgent/0.1 your-email@example.com",
        INFERENCE_GATEWAY_URL="http://localhost:8080",
        QDRANT_URL="http://localhost:6333",
        QDRANT_COLLECTION="fincontext_chunks",
        SQLITE_DB_PATH="./fincontext.db",
    )

    results = vm_preflight.check_env_file(env_path)
    failures = {result.name: result.message for result in results if not result.ok}

    assert failures["env:HF_TOKEN"] == "HF_TOKEN is unset or still a placeholder"
    assert failures["env:SEC_USER_AGENT"] == (
        "SEC_USER_AGENT is unset or still a placeholder"
    )


def test_check_env_file_accepts_real_required_values(tmp_path):
    env_path = write_env(tmp_path / ".env", **valid_env_values())

    results = vm_preflight.check_env_file(env_path)

    assert all(result.ok for result in results)


def test_validate_env_values_requires_sec_contact_email():
    values = valid_env_values()
    values["SEC_USER_AGENT"] = "FinContextAgent/0.1 no-email"

    results = vm_preflight.validate_env_values(values)
    failures = {result.name: result.message for result in results if not result.ok}

    assert failures["env:SEC_USER_AGENT_EMAIL"] == (
        "SEC_USER_AGENT must include a real contact email"
    )


def test_check_required_paths_reports_missing_files(tmp_path):
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra" / "schema.sql").write_text("-- schema\n", encoding="utf-8")

    results = vm_preflight.check_required_paths(tmp_path)
    by_name = {result.name: result for result in results}

    assert by_name["path:infra/schema.sql"].ok
    assert not by_name["path:infra/amd-gpu/docker-compose.yml"].ok


def test_check_required_commands_treats_rocm_as_warning(monkeypatch):
    def fake_which(command):
        if command == "rocm-smi":
            return None
        return f"/usr/bin/{command}"

    monkeypatch.setattr(vm_preflight.shutil, "which", fake_which)

    results = vm_preflight.check_required_commands()
    rocm = next(result for result in results if result.name == "command:rocm-smi")

    assert not rocm.ok
    assert rocm.level == "warning"


def test_check_required_commands_can_require_rocm(monkeypatch):
    def fake_which(command):
        if command == "rocm-smi":
            return None
        return f"/usr/bin/{command}"

    monkeypatch.setattr(vm_preflight.shutil, "which", fake_which)

    results = vm_preflight.check_required_commands(require_rocm=True)
    rocm = next(result for result in results if result.name == "command:rocm-smi")

    assert not rocm.ok
    assert rocm.level == "error"


def test_check_gateway_health_reports_response_status(monkeypatch):
    monkeypatch.setattr(
        vm_preflight,
        "request_json",
        lambda url, timeout=5.0: {"status": "ok"},
    )

    result = vm_preflight.check_gateway_health("http://gateway.local/")

    assert result.ok
    assert result.message == (
        "responded at http://gateway.local/health with status=ok"
    )


def test_has_blocking_failures_ignores_warnings():
    results = [
        vm_preflight.CheckResult(
            name="command:rocm-smi",
            ok=False,
            level="warning",
            message="missing locally",
        )
    ]

    assert not vm_preflight.has_blocking_failures(results)
