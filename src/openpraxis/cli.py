"""Typer CLI entrypoint."""

import json
from pathlib import Path
from uuid import uuid4

import typer
from rich.console import Console
from rich.table import Table

from openpraxis.config import get_settings
from openpraxis.db import (
    ensure_schema,
    get_connection,
    get_input_by_hash,
    get_input_by_id,
    create_input,
    get_scene,
    get_scenes_by_input,
    get_tagger_output,
    get_thread_by_scene_id,
    get_response_by_scene,
    get_all_insights,
    list_inputs,
    get_insights,
    save_tagger_output,
    save_scene,
    upsert_graph_thread,
    create_response,
    update_response_performance,
    save_insight,
)
from openpraxis.display import show_scene, show_tagger_summary, show_insight_cards, show_performance
from openpraxis.graph import get_compiled_graph, PraxisState

app = typer.Typer(name="praxis", help="OpenPraxis - Turn notes into structured practice and cognitive insights")
console = Console()


def _hash_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _get_conn():
    settings = get_settings()
    conn = get_connection(settings.db_path)
    ensure_schema(conn)
    return settings, conn


@app.command()
def add(
    file: Path = typer.Argument(..., exists=True, path_type=Path),
    type: str = typer.Option(None, "--type", "-t", help="report|interview|reflection|idea"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reprocessing (ignore duplicate hash)"),
) -> None:
    """Add file and run Tagger, optionally enter Practice."""
    settings, conn = _get_conn()
    raw_text = file.read_text(encoding="utf-8", errors="replace")
    file_hash = _hash_file(file)
    if not force:
        existing = get_input_by_hash(conn, file_hash)
        if existing:
            console.print("[yellow]Same content already exists; use --force to reprocess.[/yellow]")
            conn.close()
            return
    input_id = str(uuid4())
    thread_id = str(uuid4())
    create_input(conn, input_id, str(file), file_hash, raw_text, type)
    graph = get_compiled_graph(str(settings.db_path))
    upsert_graph_thread(conn, thread_id, input_id, status="running")
    initial: PraxisState = {
        "input_id": input_id,
        "raw_text": raw_text,
        "type_hint": type,
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(initial, config=config)
    tagger_output = result.get("tagger_output")
    if tagger_output:
        save_tagger_output(conn, input_id, tagger_output)
        cap = tagger_output.capability_map.model_dump()
        show_tagger_summary(tagger_output.summary, cap)
    scene = result.get("scene")
    if scene:
        save_scene(conn, input_id, scene)
        upsert_graph_thread(conn, thread_id, input_id, scene_id=scene.scene_id, status="interrupted")
        show_scene(
            scene.role,
            scene.task,
            scene.constraints,
            scene.expected_structure_hint,
        )
        console.print(f"\n[dim]Use [bold]praxis answer {scene.scene_id}[/bold] to submit your answer[/dim]")
    else:
        upsert_graph_thread(conn, thread_id, input_id, status="completed")
    conn.close()


@app.command()
def practice(input_id: str = typer.Argument(...)) -> None:
    """Force generate a new Practice scene for existing input."""
    settings, conn = _get_conn()
    row = get_input_by_id(conn, input_id)
    if not row:
        console.print(f"[red]Input {input_id} not found.[/red]")
        conn.close()
        raise typer.Exit(1)
    raw_text = row["raw_text"]
    type_hint = row["type_hint"]
    tagger_out = get_tagger_output(conn, input_id)
    if not tagger_out:
        console.print("[red]No tagger output found for this input. Run 'praxis add' first.[/red]")
        conn.close()
        raise typer.Exit(1)
    thread_id = str(uuid4())
    graph = get_compiled_graph(str(settings.db_path))
    upsert_graph_thread(conn, thread_id, input_id, status="running")
    initial: PraxisState = {
        "input_id": input_id,
        "raw_text": raw_text,
        "type_hint": type_hint,
        "tagger_output": tagger_out,
        "should_practice": True,
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(initial, config=config)
    scene = result.get("scene")
    if scene:
        save_scene(conn, input_id, scene)
        upsert_graph_thread(conn, thread_id, input_id, scene_id=scene.scene_id, status="interrupted")
        show_scene(
            scene.role,
            scene.task,
            scene.constraints,
            scene.expected_structure_hint,
        )
        console.print(f"\n[dim]Use [bold]praxis answer {scene.scene_id}[/bold] to submit your answer[/dim]")
    conn.close()


@app.command()
def answer(
    scene_id: str = typer.Argument(...),
    editor: bool = typer.Option(False, "--editor", "-e", help="Edit with $EDITOR"),
    file: Path | None = typer.Option(None, "--file", "-f", path_type=Path),
) -> None:
    """Submit answer for a scene and resume the graph."""
    settings, conn = _get_conn()
    row = get_thread_by_scene_id(conn, scene_id)
    if not row:
        console.print("[red]No thread found for this scene_id.[/red]")
        conn.close()
        raise typer.Exit(1)
    thread_id = row["thread_id"]
    input_id = row["input_id"]
    if editor:
        import tempfile
        import subprocess
        import os
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tf:
            tf.write("# Write your answer here\n\n")
            tf.flush()
            editor_cmd = os.environ.get("EDITOR", "vim")
            subprocess.call([editor_cmd, tf.name])
            answer_text = Path(tf.name).read_text(encoding="utf-8", errors="replace")
            os.unlink(tf.name)
    elif file:
        answer_text = file.read_text(encoding="utf-8", errors="replace")
    else:
        console.print("Enter your answer on stdin, end with EOF (Ctrl+D):")
        answer_text = ""
        try:
            while True:
                line = input()
                answer_text += line + "\n"
        except EOFError:
            pass
    from langgraph.types import Command
    graph = get_compiled_graph(str(settings.db_path))
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(Command(resume=answer_text), config=config)
    performance = result.get("performance")
    insights = result.get("insights", [])
    scene = get_scene(conn, scene_id)
    if scene and performance:
        resp_id = create_response(conn, scene_id, answer_text)
        update_response_performance(conn, resp_id, performance)
        for card in insights:
            save_insight(conn, input_id, scene_id, resp_id, card)
        show_performance(
            performance.performance_signal.model_dump(),
            performance.improvement_vectors,
        )
        show_insight_cards([c.model_dump() for c in insights])
    upsert_graph_thread(conn, thread_id, input_id, scene_id=scene_id, status="completed")
    conn.close()


@app.command()
def insight(
    input_id: str | None = typer.Argument(None),
    type: str | None = typer.Option(None, "--type", "-t"),
    min_intensity: int | None = typer.Option(None, "--min-intensity"),
) -> None:
    """Query and display insight cards."""
    _settings, conn = _get_conn()
    cards = get_insights(conn, input_id=input_id, insight_type=type, min_intensity=min_intensity)
    if not cards:
        console.print("[dim]No insight cards found.[/dim]")
    else:
        show_insight_cards(cards)
    conn.close()


@app.command()
def show(id: str = typer.Argument(...)) -> None:
    """Show full pipeline: input summary -> Tagger -> scene -> answer -> score -> insight cards."""
    _settings, conn = _get_conn()

    # Auto-detect whether id is input_id or scene_id
    inp = get_input_by_id(conn, id)
    scene_lookup = None
    if not inp:
        scene_lookup = get_scene(conn, id)
        if scene_lookup:
            # Find the input_id via scenes table
            cur = conn.execute("SELECT input_id FROM scenes WHERE scene_id = ?", (id,))
            row = cur.fetchone()
            if row:
                inp = get_input_by_id(conn, row["input_id"])

    if not inp:
        console.print(f"[red]ID {id} not found as input_id or scene_id.[/red]")
        conn.close()
        raise typer.Exit(1)

    input_id = inp["id"]
    console.print(f"[bold]Input[/bold] {input_id[:8]}...")
    console.print(f"[dim]File:[/dim] {inp['file_path'] or '(none)'}")
    console.print(f"[dim]Type:[/dim] {inp['input_type'] or '(untagged)'}")
    console.print()

    # Tagger output
    tagger_out = get_tagger_output(conn, input_id)
    if tagger_out:
        show_tagger_summary(tagger_out.summary, tagger_out.capability_map.model_dump())
        console.print()

    # Scenes
    scenes = get_scenes_by_input(conn, input_id)
    for sc in scenes:
        show_scene(sc.role, sc.task, sc.constraints, sc.expected_structure_hint)
        # Response for this scene
        resp = get_response_by_scene(conn, sc.scene_id)
        if resp:
            console.print(f"\n[bold]Answer[/bold] (preview):")
            preview = resp["answer_text"][:500]
            console.print(f"  {preview}{'...' if len(resp['answer_text']) > 500 else ''}\n")
            if resp["perf_json"]:
                from openpraxis.models import PracticePerformance
                perf = PracticePerformance.model_validate_json(resp["perf_json"])
                show_performance(
                    perf.performance_signal.model_dump(),
                    perf.improvement_vectors,
                )
                console.print()

    # Insight cards
    cards = get_insights(conn, input_id=input_id)
    if cards:
        show_insight_cards(cards)

    conn.close()


@app.command()
def export(
    format: str = typer.Option("md", "--format", "-fmt", help="md|json"),
    output: Path | None = typer.Option(None, "--output", "-o", path_type=Path),
) -> None:
    """Export insight cards."""
    _settings, conn = _get_conn()
    cards = get_all_insights(conn)
    conn.close()

    # Strip internal metadata key for export
    export_cards = []
    for c in cards:
        card = {k: v for k, v in c.items() if not k.startswith("_")}
        export_cards.append(card)

    if not export_cards:
        console.print("[dim]No insight cards to export.[/dim]")
        return

    if format == "json":
        text = json.dumps(export_cards, indent=2, ensure_ascii=False)
    else:
        # Markdown format
        lines = ["# OpenPraxis Insight Cards\n"]
        for i, card in enumerate(export_cards, 1):
            lines.append(f"## {i}. {card.get('insight_title', 'Untitled')}")
            lines.append(f"**Type:** {card.get('insight_type', '')}  ")
            lines.append(f"**Intensity:** {card.get('intensity', '')}  \n")
            lines.append(f"**What happened:** {card.get('what_happened', '')}\n")
            lines.append(f"**Why it matters:** {card.get('why_it_matters', '')}\n")
            lines.append(f"**Upgrade pattern:** {card.get('upgrade_pattern', '')}\n")
            lines.append(f"**Micro practice:** {card.get('micro_practice', '')}\n")
            if card.get("concepts"):
                lines.append(f"**Concepts:** {', '.join(card['concepts'])}\n")
            if card.get("skills"):
                lines.append(f"**Skills:** {', '.join(card['skills'])}\n")
            lines.append("---\n")
        text = "\n".join(lines)

    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Exported {len(export_cards)} cards to {output}[/green]")
    else:
        console.print(text)


@app.command(name="list")
def list_inputs_cmd(
    type: str | None = typer.Option(None, "--type", "-t"),
    limit: int = typer.Option(50, "--limit", "-n"),
) -> None:
    """List recent inputs."""
    _settings, conn = _get_conn()
    rows = list_inputs(conn, input_type=type, limit=limit)
    table = Table(title="Input list")
    table.add_column("id", style="dim")
    table.add_column("type")
    table.add_column("file", style="dim")
    table.add_column("created_at")
    for r in rows:
        file_name = Path(r["file_path"]).name if r["file_path"] else "-"
        table.add_row(
            r["id"][:8] + "...",
            r["input_type"] or "-",
            file_name,
            r["created_at"],
        )
    console.print(table)
    conn.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
