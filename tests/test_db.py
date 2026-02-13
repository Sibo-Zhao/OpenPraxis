"""SQLite CRUD 与建表测试。"""

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from openpraxis.db import (
    ensure_schema,
    get_connection,
    create_input,
    get_input_by_id,
    get_input_by_hash,
    save_tagger_output,
    save_scene,
    get_scene,
    create_response,
    update_response_performance,
    save_insight,
    upsert_graph_thread,
    get_thread_by_scene_id,
    list_inputs,
    get_insights,
)
from openpraxis.models import (
    CapabilityMap,
    InsightCard,
    InsightType,
    InputType,
    PracticePerformance,
    PracticeScene,
    PerformanceSignal,
    PracticeSeed,
    RoutingPolicy,
    SceneType,
    Sensitivity,
    Tags,
    TaggerOutput,
)


@pytest.fixture
def memory_conn() -> sqlite3.Connection:
    conn = get_connection(Path(":memory:"))
    ensure_schema(conn)
    return conn


@pytest.fixture
def sample_tagger_output() -> TaggerOutput:
    return TaggerOutput(
        input_type=InputType.REPORT,
        summary="Test summary",
        tags=Tags(topics=["A"], domains=["B"], difficulty=2, sensitivity=Sensitivity.NORMAL),
        capability_map=CapabilityMap(
            concept_understanding=5,
            structuring=5,
            tradeoff_thinking=5,
            system_thinking=5,
            communication=5,
        ),
        routing_policy=RoutingPolicy.NONE,
        practice_seed=PracticeSeed(
            preferred_scene=SceneType.EXPLAIN,
            skills=[],
            concepts=[],
            constraints=[],
        ),
    )


def test_ensure_schema(memory_conn: sqlite3.Connection) -> None:
    cur = memory_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='inputs'"
    )
    assert cur.fetchone() is not None


def test_create_and_get_input(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(
        memory_conn,
        input_id=input_id,
        file_path="/tmp/x.md",
        file_hash="abc123",
        raw_text="hello",
        type_hint="report",
    )
    row = get_input_by_id(memory_conn, input_id)
    assert row is not None
    assert row["raw_text"] == "hello"
    assert row["type_hint"] == "report"


def test_get_input_by_hash(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(
        memory_conn,
        input_id=input_id,
        file_path=None,
        file_hash="hash1",
        raw_text="content",
    )
    row = get_input_by_hash(memory_conn, "hash1")
    assert row is not None
    assert row["id"] == input_id


def test_save_tagger_output(
    memory_conn: sqlite3.Connection, sample_tagger_output: TaggerOutput
) -> None:
    input_id = str(uuid4())
    create_input(
        memory_conn,
        input_id=input_id,
        file_path=None,
        file_hash="h2",
        raw_text="x",
    )
    save_tagger_output(memory_conn, input_id, sample_tagger_output)
    cur = memory_conn.execute(
        "SELECT output_json FROM tagger_outputs WHERE input_id = ?", (input_id,)
    )
    row = cur.fetchone()
    assert row is not None


def test_save_and_get_scene(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(
        memory_conn,
        input_id=input_id,
        file_path=None,
        file_hash="h3",
        raw_text="y",
    )
    scene = PracticeScene(
        scene_id="scene-1",
        scene_type=SceneType.EXPLAIN,
        role="Dev",
        task="Explain",
        constraints=[],
        rubric=[],
        expected_structure_hint=[],
    )
    save_scene(memory_conn, input_id, scene)
    loaded = get_scene(memory_conn, "scene-1")
    assert loaded is not None
    assert loaded.scene_id == "scene-1"
    assert loaded.role == "Dev"


def test_create_response(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(
        memory_conn,
        input_id=input_id,
        file_path=None,
        file_hash="h4",
        raw_text="z",
    )
    scene = PracticeScene(
        scene_id="scene-2",
        scene_type=SceneType.EXPLAIN,
        role="R",
        task="T",
        constraints=[],
        rubric=[],
        expected_structure_hint=[],
    )
    save_scene(memory_conn, input_id, scene)
    resp_id = create_response(memory_conn, "scene-2", "My answer")
    assert resp_id is not None
    cur = memory_conn.execute("SELECT answer_text FROM responses WHERE id = ?", (resp_id,))
    assert cur.fetchone()["answer_text"] == "My answer"


def test_upsert_graph_thread(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(
        memory_conn,
        input_id=input_id,
        file_path=None,
        file_hash="h5",
        raw_text="w",
    )
    upsert_graph_thread(memory_conn, "thread-1", input_id, scene_id="scene-x", status="interrupted")
    row = get_thread_by_scene_id(memory_conn, "scene-x")
    assert row is not None
    assert row["thread_id"] == "thread-1"
    assert row["input_id"] == input_id


def test_list_inputs(memory_conn: sqlite3.Connection) -> None:
    for i in range(3):
        create_input(
            memory_conn,
            input_id=str(uuid4()),
            file_path=None,
            file_hash=f"hash-{i}",
            raw_text=f"content {i}",
        )
    rows = list_inputs(memory_conn, limit=10)
    assert len(rows) >= 3


def test_get_insights(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(
        memory_conn,
        input_id=input_id,
        file_path=None,
        file_hash="h6",
        raw_text="v",
    )
    card = InsightCard(
        insight_title="Test",
        insight_type=InsightType.STRUCTURING_GAP,
        what_happened="x",
        why_it_matters="y",
        upgrade_pattern="z",
        micro_practice="m",
        concepts=[],
        skills=[],
        scenes=[],
        intensity=2,
    )
    save_insight(memory_conn, input_id, None, None, card)
    cards = get_insights(memory_conn, input_id=input_id)
    assert len(cards) == 1
    assert cards[0]["insight_title"] == "Test"
