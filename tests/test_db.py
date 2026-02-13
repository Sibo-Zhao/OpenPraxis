"""SQLite CRUD and schema tests."""

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
    get_tagger_output,
    save_scene,
    get_scene,
    get_scenes_by_input,
    get_response_by_scene,
    get_all_insights,
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


def test_get_tagger_output(
    memory_conn: sqlite3.Connection, sample_tagger_output: TaggerOutput
) -> None:
    input_id = str(uuid4())
    create_input(memory_conn, input_id, None, "h7", "content")
    save_tagger_output(memory_conn, input_id, sample_tagger_output)
    loaded = get_tagger_output(memory_conn, input_id)
    assert loaded is not None
    assert loaded.summary == "Test summary"
    assert loaded.input_type == InputType.REPORT


def test_get_tagger_output_not_found(memory_conn: sqlite3.Connection) -> None:
    assert get_tagger_output(memory_conn, "nonexistent") is None


def test_get_scenes_by_input(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(memory_conn, input_id, None, "h8", "content")
    s1 = PracticeScene(
        scene_id="scene-a", scene_type=SceneType.EXPLAIN,
        role="R", task="T", constraints=[], rubric=[], expected_structure_hint=[],
    )
    s2 = PracticeScene(
        scene_id="scene-b", scene_type=SceneType.CRITIQUE,
        role="R2", task="T2", constraints=[], rubric=[], expected_structure_hint=[],
    )
    save_scene(memory_conn, input_id, s1)
    save_scene(memory_conn, input_id, s2)
    scenes = get_scenes_by_input(memory_conn, input_id)
    assert len(scenes) == 2


def test_get_response_by_scene(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(memory_conn, input_id, None, "h9", "content")
    scene = PracticeScene(
        scene_id="scene-resp", scene_type=SceneType.EXPLAIN,
        role="R", task="T", constraints=[], rubric=[], expected_structure_hint=[],
    )
    save_scene(memory_conn, input_id, scene)
    create_response(memory_conn, "scene-resp", "My answer")
    resp = get_response_by_scene(memory_conn, "scene-resp")
    assert resp is not None
    assert resp["answer_text"] == "My answer"


def test_get_response_by_scene_not_found(memory_conn: sqlite3.Connection) -> None:
    assert get_response_by_scene(memory_conn, "nonexistent") is None


def test_get_all_insights(memory_conn: sqlite3.Connection) -> None:
    input_id = str(uuid4())
    create_input(memory_conn, input_id, None, "h10", "content")
    card = InsightCard(
        insight_title="All test",
        insight_type=InsightType.STRUCTURING_GAP,
        what_happened="x", why_it_matters="y",
        upgrade_pattern="z", micro_practice="m",
        concepts=[], skills=[], scenes=[], intensity=1,
    )
    save_insight(memory_conn, input_id, None, None, card)
    all_cards = get_all_insights(memory_conn)
    assert len(all_cards) >= 1
    assert all_cards[0]["_input_id"] == input_id
