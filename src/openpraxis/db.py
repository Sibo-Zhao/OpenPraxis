"""SQLite schema + CRUD."""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from openpraxis.models import (
    InsightCard,
    PracticePerformance,
    PracticeScene,
    TaggerOutput,
)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS inputs (
    id          TEXT PRIMARY KEY,
    file_path   TEXT,
    file_hash   TEXT NOT NULL UNIQUE,
    raw_text    TEXT NOT NULL,
    input_type  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    type_hint   TEXT
);

CREATE TABLE IF NOT EXISTS tagger_outputs (
    input_id    TEXT PRIMARY KEY REFERENCES inputs(id),
    output_json TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scenes (
    scene_id    TEXT PRIMARY KEY,
    input_id    TEXT NOT NULL REFERENCES inputs(id),
    scene_json  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS responses (
    id          TEXT PRIMARY KEY,
    scene_id    TEXT NOT NULL REFERENCES scenes(scene_id),
    answer_text TEXT NOT NULL,
    perf_json   TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS insights (
    id          TEXT PRIMARY KEY,
    input_id    TEXT NOT NULL REFERENCES inputs(id),
    scene_id    TEXT REFERENCES scenes(scene_id),
    response_id TEXT REFERENCES responses(id),
    card_json   TEXT NOT NULL,
    insight_type TEXT NOT NULL,
    intensity   INTEGER NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS graph_threads (
    thread_id   TEXT PRIMARY KEY,
    input_id    TEXT NOT NULL REFERENCES inputs(id),
    scene_id    TEXT REFERENCES scenes(scene_id),
    status      TEXT NOT NULL DEFAULT 'running',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_graph_threads_input_id ON graph_threads(input_id);
CREATE INDEX IF NOT EXISTS idx_graph_threads_scene_id ON graph_threads(scene_id);
"""


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    """Return database connection."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def create_input(
    conn: sqlite3.Connection,
    input_id: str,
    file_path: str | None,
    file_hash: str,
    raw_text: str,
    type_hint: str | None = None,
) -> None:
    """Insert into inputs table."""
    conn.execute(
        "INSERT INTO inputs (id, file_path, file_hash, raw_text, type_hint) VALUES (?, ?, ?, ?, ?)",
        (input_id, file_path, file_hash, raw_text, type_hint),
    )
    conn.commit()


def get_input_by_id(conn: sqlite3.Connection, input_id: str) -> sqlite3.Row | None:
    """Get inputs by id."""
    cur = conn.execute("SELECT * FROM inputs WHERE id = ?", (input_id,))
    return cur.fetchone()


def get_input_by_hash(conn: sqlite3.Connection, file_hash: str) -> sqlite3.Row | None:
    """Get inputs by file_hash (for dedup)."""
    cur = conn.execute("SELECT * FROM inputs WHERE file_hash = ?", (file_hash,))
    return cur.fetchone()


def save_tagger_output(
    conn: sqlite3.Connection, input_id: str, output: TaggerOutput
) -> None:
    """Insert into tagger_outputs."""
    conn.execute(
        "INSERT OR REPLACE INTO tagger_outputs (input_id, output_json) VALUES (?, ?)",
        (input_id, output.model_dump_json()),
    )
    conn.execute(
        "UPDATE inputs SET input_type = ? WHERE id = ?",
        (output.input_type.value, input_id),
    )
    conn.commit()


def save_scene(conn: sqlite3.Connection, input_id: str, scene: PracticeScene) -> None:
    """Insert into scenes."""
    conn.execute(
        "INSERT INTO scenes (scene_id, input_id, scene_json) VALUES (?, ?, ?)",
        (scene.scene_id, input_id, scene.model_dump_json()),
    )
    conn.commit()


def get_scene(conn: sqlite3.Connection, scene_id: str) -> PracticeScene | None:
    """Get scene by scene_id."""
    cur = conn.execute("SELECT scene_json FROM scenes WHERE scene_id = ?", (scene_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return PracticeScene.model_validate_json(row["scene_json"])


def create_response(
    conn: sqlite3.Connection, scene_id: str, answer_text: str
) -> str:
    """Insert into responses, return response id."""
    resp_id = str(uuid4())
    conn.execute(
        "INSERT INTO responses (id, scene_id, answer_text) VALUES (?, ?, ?)",
        (resp_id, scene_id, answer_text),
    )
    conn.commit()
    return resp_id


def update_response_performance(
    conn: sqlite3.Connection, response_id: str, performance: PracticePerformance
) -> None:
    """Update response perf_json."""
    conn.execute(
        "UPDATE responses SET perf_json = ? WHERE id = ?",
        (performance.model_dump_json(), response_id),
    )
    conn.commit()


def save_insight(
    conn: sqlite3.Connection,
    input_id: str,
    scene_id: str | None,
    response_id: str | None,
    card: InsightCard,
) -> None:
    """Insert into insights."""
    card_id = str(uuid4())
    conn.execute(
        """INSERT INTO insights (id, input_id, scene_id, response_id, card_json, insight_type, intensity)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            card_id,
            input_id,
            scene_id,
            response_id,
            card.model_dump_json(),
            card.insight_type.value,
            card.intensity,
        ),
    )
    conn.commit()


def upsert_graph_thread(
    conn: sqlite3.Connection,
    thread_id: str,
    input_id: str,
    scene_id: str | None = None,
    status: str = "running",
) -> None:
    """Insert or update graph_threads."""
    conn.execute(
        """INSERT INTO graph_threads (thread_id, input_id, scene_id, status)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(thread_id) DO UPDATE SET
             scene_id = excluded.scene_id,
             status = excluded.status,
             updated_at = datetime('now')""",
        (thread_id, input_id, scene_id, status),
    )
    conn.commit()


def get_thread_by_scene_id(
    conn: sqlite3.Connection, scene_id: str
) -> sqlite3.Row | None:
    """Get graph_threads by scene_id."""
    cur = conn.execute(
        "SELECT * FROM graph_threads WHERE scene_id = ?", (scene_id,)
    )
    return cur.fetchone()


def get_thread_by_input_id(
    conn: sqlite3.Connection, input_id: str
) -> sqlite3.Row | None:
    """Get graph_threads by input_id."""
    cur = conn.execute(
        "SELECT * FROM graph_threads WHERE input_id = ?", (input_id,)
    )
    return cur.fetchone()


def list_inputs(
    conn: sqlite3.Connection,
    input_type: str | None = None,
    limit: int = 50,
) -> list[sqlite3.Row]:
    """List inputs, optionally filter by type."""
    if input_type:
        cur = conn.execute(
            "SELECT * FROM inputs WHERE input_type = ? ORDER BY created_at DESC LIMIT ?",
            (input_type, limit),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM inputs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    return list(cur.fetchall())


def get_tagger_output(conn: sqlite3.Connection, input_id: str) -> TaggerOutput | None:
    """Get parsed TaggerOutput for an input."""
    cur = conn.execute(
        "SELECT output_json FROM tagger_outputs WHERE input_id = ?", (input_id,)
    )
    row = cur.fetchone()
    if row is None:
        return None
    return TaggerOutput.model_validate_json(row["output_json"])


def get_scenes_by_input(conn: sqlite3.Connection, input_id: str) -> list[PracticeScene]:
    """Get all scenes for an input."""
    cur = conn.execute(
        "SELECT scene_json FROM scenes WHERE input_id = ? ORDER BY created_at", (input_id,)
    )
    return [PracticeScene.model_validate_json(r["scene_json"]) for r in cur.fetchall()]


def get_response_by_scene(conn: sqlite3.Connection, scene_id: str) -> sqlite3.Row | None:
    """Get the latest response for a scene."""
    cur = conn.execute(
        "SELECT * FROM responses WHERE scene_id = ? ORDER BY created_at DESC LIMIT 1",
        (scene_id,),
    )
    return cur.fetchone()


def get_all_insights(conn: sqlite3.Connection) -> list[dict]:
    """Get all insight cards with input_id info."""
    cur = conn.execute(
        "SELECT input_id, card_json FROM insights ORDER BY created_at DESC"
    )
    rows = cur.fetchall()
    result = []
    for r in rows:
        card = json.loads(r["card_json"])
        card["_input_id"] = r["input_id"]
        result.append(card)
    return result


def get_insights(
    conn: sqlite3.Connection,
    input_id: str | None = None,
    insight_type: str | None = None,
    min_intensity: int | None = None,
) -> list[dict]:
    """Query insight cards."""
    sql = "SELECT card_json FROM insights WHERE 1=1"
    params: list = []
    if input_id:
        sql += " AND input_id = ?"
        params.append(input_id)
    if insight_type:
        sql += " AND insight_type = ?"
        params.append(insight_type)
    if min_intensity is not None:
        sql += " AND intensity >= ?"
        params.append(min_intensity)
    sql += " ORDER BY created_at DESC"
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    return [json.loads(r["card_json"]) for r in rows]
