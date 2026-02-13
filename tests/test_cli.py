"""CLI command parsing and output tests."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from openpraxis.cli import app
from openpraxis.db import (
    create_input,
    create_response,
    ensure_schema,
    get_connection,
    save_insight,
    save_scene,
    save_tagger_output,
    update_response_performance,
    upsert_graph_thread,
)
from openpraxis.models import (
    CapabilityMap,
    InputType,
    InsightCard,
    InsightType,
    PracticePerformance,
    PracticeScene,
    PracticeSeed,
    PerformanceSignal,
    RoutingPolicy,
    SceneType,
    Sensitivity,
    Tags,
    TaggerOutput,
)

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "add" in result.output
    assert "list" in result.output
    assert "--provider" in result.output


def test_add_help() -> None:
    result = runner.invoke(app, ["add", "--help"])
    assert result.exit_code == 0
    assert "file" in result.output.lower() or "FILE" in result.output


def test_list_help() -> None:
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0


def test_answer_help() -> None:
    result = runner.invoke(app, ["answer", "--help"])
    assert result.exit_code == 0
    assert "scene" in result.output.lower() or "SCENE" in result.output


def test_practice_help() -> None:
    result = runner.invoke(app, ["practice", "--help"])
    assert result.exit_code == 0


def test_show_help() -> None:
    result = runner.invoke(app, ["show", "--help"])
    assert result.exit_code == 0


def test_export_help() -> None:
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0


def test_insight_help() -> None:
    result = runner.invoke(app, ["insight", "--help"])
    assert result.exit_code == 0


# --- Functional tests with mock graph and DB ---

def _make_tagger_output() -> TaggerOutput:
    return TaggerOutput(
        input_type=InputType.REPORT,
        summary="A technical report on RAG pipeline architecture.",
        tags=Tags(topics=["RAG"], domains=["ML System"], difficulty=3, sensitivity=Sensitivity.NORMAL),
        capability_map=CapabilityMap(
            concept_understanding=7, structuring=5,
            tradeoff_thinking=4, system_thinking=6, communication=5,
        ),
        routing_policy=RoutingPolicy.RECOMMEND,
        practice_seed=PracticeSeed(
            preferred_scene=SceneType.EXPLAIN,
            skills=["failure-mode framing"],
            concepts=["retrieval"],
            constraints=["3 minutes"],
        ),
    )


def _make_scene() -> PracticeScene:
    return PracticeScene(
        scene_id="test-scene-001",
        scene_type=SceneType.EXPLAIN,
        role="Tech Lead",
        task="Explain RAG failure modes in 3 minutes.",
        constraints=["3 minutes", "Include 1 failure mode"],
        rubric=["clarity", "reasoning_depth", "decision_quality", "communication"],
        expected_structure_hint=["Definition", "Example", "Mitigation"],
    )


def _make_performance() -> PracticePerformance:
    return PracticePerformance(
        performance_signal=PerformanceSignal(
            clarity=7, reasoning_depth=6, decision_quality=6, communication=7,
        ),
        improvement_vectors=["Add concrete examples"],
    )


def _make_insight_card() -> InsightCard:
    return InsightCard(
        insight_title="Structured expression gap",
        insight_type=InsightType.STRUCTURING_GAP,
        what_happened="Answer did not follow definition-example-mitigation",
        why_it_matters="Unclear structure reduces credibility",
        upgrade_pattern="Always do definition -> example -> mitigation",
        micro_practice="State three points in 30 seconds",
        concepts=["RAG"],
        skills=["structuring"],
        scenes=["test-scene-001"],
        intensity=2,
    )


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary DB and patch get_settings to use it."""
    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    ensure_schema(conn)
    conn.close()

    mock_settings = MagicMock()
    mock_settings.db_path = db_path
    mock_settings.data_dir = tmp_path
    mock_settings.color = True

    with patch("openpraxis.cli.get_settings", return_value=mock_settings):
        yield db_path


@pytest.fixture
def populated_db(tmp_db):
    """DB with an input, tagger output, scene, response, and insight."""
    conn = get_connection(tmp_db)
    ensure_schema(conn)

    input_id = "test-input-001"
    create_input(conn, input_id, "/tmp/test.md", "hash123", "RAG report content")
    save_tagger_output(conn, input_id, _make_tagger_output())

    scene = _make_scene()
    save_scene(conn, input_id, scene)
    upsert_graph_thread(conn, "thread-001", input_id, scene_id=scene.scene_id, status="interrupted")

    resp_id = create_response(conn, scene.scene_id, "My answer about RAG failure modes")
    perf = _make_performance()
    update_response_performance(conn, resp_id, perf)

    card = _make_insight_card()
    save_insight(conn, input_id, scene.scene_id, resp_id, card)

    conn.close()
    return tmp_db


def test_list_empty(tmp_db) -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Input list" in result.output


def test_list_with_data(populated_db) -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "report" in result.output


def test_insight_empty(tmp_db) -> None:
    result = runner.invoke(app, ["insight"])
    assert result.exit_code == 0
    assert "No insight cards found" in result.output


def test_insight_with_data(populated_db) -> None:
    result = runner.invoke(app, ["insight"])
    assert result.exit_code == 0
    assert "Structured expression gap" in result.output


def test_insight_filter_by_type(populated_db) -> None:
    result = runner.invoke(app, ["insight", "--type", "structuring_gap"])
    assert result.exit_code == 0
    assert "Structured expression gap" in result.output


def test_insight_filter_no_match(populated_db) -> None:
    result = runner.invoke(app, ["insight", "--type", "metric_gap"])
    assert result.exit_code == 0
    assert "No insight cards found" in result.output


def test_show_by_input_id(populated_db) -> None:
    result = runner.invoke(app, ["show", "test-input-001"])
    assert result.exit_code == 0
    assert "test-inpu..." in result.output or "Input" in result.output
    assert "report" in result.output


def test_show_by_scene_id(populated_db) -> None:
    result = runner.invoke(app, ["show", "test-scene-001"])
    assert result.exit_code == 0
    assert "Tech Lead" in result.output


def test_show_not_found(tmp_db) -> None:
    result = runner.invoke(app, ["show", "nonexistent"])
    assert result.exit_code == 1


def test_export_json(populated_db) -> None:
    result = runner.invoke(app, ["export", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) >= 1
    assert data[0]["insight_title"] == "Structured expression gap"


def test_export_md(populated_db) -> None:
    result = runner.invoke(app, ["export", "--format", "md"])
    assert result.exit_code == 0
    assert "# OpenPraxis Insight Cards" in result.output
    assert "Structured expression gap" in result.output


def test_export_to_file(populated_db, tmp_path) -> None:
    out_file = tmp_path / "export.json"
    result = runner.invoke(app, ["export", "--format", "json", "--output", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert len(data) >= 1


def test_export_empty(tmp_db) -> None:
    result = runner.invoke(app, ["export", "--format", "json"])
    assert result.exit_code == 0
    assert "No insight cards to export" in result.output


def test_add_with_mock_graph(tmp_db, tmp_path, mock_llm, mock_tagger_output, mock_scene) -> None:
    """Test add command with mocked graph invocation."""
    test_file = tmp_path / "input.md"
    test_file.write_text("Test RAG report content")

    # Mock graph to return tagger output + scene (simulating interrupt)
    mock_result = {
        "tagger_output": mock_tagger_output,
        "scene": mock_scene,
    }
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = mock_result

    with patch("openpraxis.cli.get_compiled_graph", return_value=mock_graph):
        result = runner.invoke(app, ["add", str(test_file)])

    assert result.exit_code == 0
    assert "Summary" in result.output or "Practice scene" in result.output


def test_add_duplicate(tmp_db, tmp_path) -> None:
    """Test that adding same file twice warns about duplicate."""
    test_file = tmp_path / "dup.md"
    test_file.write_text("Duplicate content")

    # Insert an input with the same hash
    import hashlib
    h = hashlib.sha256()
    h.update(test_file.read_bytes())
    file_hash = h.hexdigest()

    conn = get_connection(tmp_db)
    ensure_schema(conn)
    create_input(conn, str(uuid4()), str(test_file), file_hash, "Duplicate content")
    conn.close()

    result = runner.invoke(app, ["add", str(test_file)])
    assert result.exit_code == 0
    assert "already exists" in result.output


def test_global_provider_override_option(tmp_db, tmp_path, mock_tagger_output, mock_scene) -> None:
    test_file = tmp_path / "provider.md"
    test_file.write_text("Provider override test")

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"tagger_output": mock_tagger_output, "scene": mock_scene}

    with patch("openpraxis.cli.get_compiled_graph", return_value=mock_graph), \
         patch("openpraxis.cli.set_runtime_llm_overrides") as mock_overrides:
        result = runner.invoke(app, ["--provider", "kimi", "add", str(test_file)])

    assert result.exit_code == 0
    mock_overrides.assert_called_once_with(
        provider="kimi",
        api_key=None,
        base_url=None,
        model=None,
        temperature=None,
    )
