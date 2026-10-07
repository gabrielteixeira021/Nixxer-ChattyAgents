from __future__ import annotations

import inspect
from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend import persona_main
from src.backend.api.persona import get_persona_db
from src.backend.db.database import Base
from src.backend.db.models import AgentState, Character, User
from src.backend.persona_main import DEFAULT_HOST, DEFAULT_PORT, app, run


@pytest.fixture
def persona_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def persona_app(persona_db):
    async def override_get_db():
        yield persona_db

    app.dependency_overrides[get_persona_db] = override_get_db
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


async def _get(persona_app, path: str):
    transport = ASGITransport(app=persona_app)
    async with AsyncClient(
        transport=transport, base_url="http://persona.test"
    ) as client:
        return await client.get(path)


def test_service_defaults_to_loopback():
    signature = inspect.signature(run)

    assert DEFAULT_HOST == "127.0.0.1"
    assert DEFAULT_PORT == 8765
    assert "host" not in signature.parameters
    assert signature.parameters["port"].default == 8765


@pytest.mark.asyncio
async def test_lifespan_initializes_only_persistence(monkeypatch):
    calls = []
    monkeypatch.setattr(persona_main.settings, "TESTING", False)
    monkeypatch.setattr(persona_main, "init_db", lambda: calls.append("database"))

    async with persona_main.lifespan(app):
        assert calls == ["database"]

    assert calls == ["database"]


@pytest.mark.asyncio
async def test_health_reports_domain_and_database_readiness(persona_app):
    response = await _get(persona_app, "/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "sophia-persona-engine",
        "api_version": "v1",
        "persona_schema_version": 1,
        "components": {"persona_engine": "ready", "database": "ready"},
    }


@pytest.mark.asyncio
async def test_health_returns_stable_503_when_database_fails(
    persona_app, persona_db, monkeypatch
):
    def fail_execute(*args, **kwargs):
        raise SQLAlchemyError("sensitive database detail")

    monkeypatch.setattr(persona_db, "execute", fail_execute)
    response = await _get(persona_app, "/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "persona_runtime_unavailable",
            "message": "Persona Engine persistence is unavailable",
        }
    }
    assert "sensitive" not in response.text


@pytest.mark.asyncio
async def test_snapshot_reads_character_state_and_active_user(persona_app, persona_db):
    character = Character(
        name="SophIA",
        nickname="Sophia",
        description="Companion de {{user}}.",
        persona_prompt="Curiosa e calorosa.",
        dynamic_persona=True,
    )
    user = User(
        name="Gabriel",
        gender="Unknown",
        persona_description="Arquiteto e idealizador.",
        is_active=True,
    )
    persona_db.add_all([character, user])
    persona_db.flush()
    persona_db.add(
        AgentState(
            character_id=character.id,
            location="Desktop",
            mood="Atenta",
            stats={
                "energy": 90,
                "hunger": 0,
                "relationship": {"score": 75},
            },
        )
    )
    persona_db.commit()

    response = await _get(persona_app, f"/v1/personas/{character.id}/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert body["character_name"] == "Sophia"
    assert body["mood"] == "Atenta"
    assert body["dynamic"] is True
    assert body["revision"] == 1
    assert "Companion de Gabriel." in body["system_prompt"]
    assert "Loc:Desktop | Mood:Atenta" in body["system_prompt"]


@pytest.mark.asyncio
async def test_snapshot_returns_stable_errors(persona_app, persona_db):
    missing = await _get(persona_app, "/v1/personas/999/snapshot")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "character_not_found"

    invalid = Character(name="", description="invalid")
    persona_db.add(invalid)
    persona_db.commit()
    malformed = await _get(persona_app, f"/v1/personas/{invalid.id}/snapshot")
    assert malformed.status_code == 422
    assert malformed.json() == {
        "detail": {
            "code": "invalid_persona",
            "message": "Stored character cannot satisfy the Persona v1 contract",
        }
    }

    invalid_path = await _get(persona_app, "/v1/personas/0/snapshot")
    assert invalid_path.status_code == 422
    assert invalid_path.json()["detail"]["code"] == "request_validation_error"


@pytest.mark.asyncio
async def test_snapshot_returns_stable_503_when_database_fails(
    persona_app, persona_db, monkeypatch
):
    def fail_get(*args, **kwargs):
        raise SQLAlchemyError("sensitive database detail")

    monkeypatch.setattr(persona_db, "get", fail_get)
    response = await _get(persona_app, "/v1/personas/1/snapshot")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "persona_runtime_unavailable",
            "message": "Persona Engine persistence is unavailable",
        }
    }
    assert "sensitive" not in response.text


def test_runtime_paths_match_versioned_openapi_contract():
    contract_path = Path("docs/en/api/persona-v1.openapi.yaml")
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    runtime = app.openapi()

    assert runtime["info"]["title"] == contract["info"]["title"]
    assert runtime["info"]["version"] == contract["info"]["version"]
    assert set(runtime["paths"]) == set(contract["paths"])
    for path, path_contract in contract["paths"].items():
        contract_get = path_contract["get"]
        runtime_get = runtime["paths"][path]["get"]
        assert runtime_get["operationId"] == contract_get["operationId"]
        assert set(runtime_get["responses"]) == set(contract_get["responses"])
        for status, response_contract in contract_get["responses"].items():
            expected_ref = response_contract["content"]["application/json"]["schema"]
            actual_ref = runtime_get["responses"][status]["content"][
                "application/json"
            ]["schema"]
            assert actual_ref == expected_ref

    contract_parameter = contract["paths"]["/v1/personas/{character_id}/snapshot"][
        "get"
    ]["parameters"][0]
    runtime_parameter = runtime["paths"]["/v1/personas/{character_id}/snapshot"]["get"][
        "parameters"
    ][0]
    assert runtime_parameter["name"] == contract_parameter["name"]
    assert runtime_parameter["in"] == contract_parameter["in"]
    assert runtime_parameter["required"] == contract_parameter["required"]
    assert runtime_parameter["schema"]["type"] == contract_parameter["schema"]["type"]
    assert (
        runtime_parameter["schema"]["minimum"]
        == contract_parameter["schema"]["minimum"]
    )

    def without_generated_metadata(value):
        if isinstance(value, dict):
            return {
                key: without_generated_metadata(item)
                for key, item in value.items()
                if key not in {"title"}
            }
        if isinstance(value, list):
            return [without_generated_metadata(item) for item in value]
        return value

    for name, schema in contract["components"]["schemas"].items():
        assert (
            without_generated_metadata(runtime["components"]["schemas"][name]) == schema
        )
