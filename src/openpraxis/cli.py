"""Typer CLI 入口。"""

from pathlib import Path
from uuid import uuid4

import typer
from rich.console import Console

from openpraxis.config import get_settings
from openpraxis.db import (
    ensure_schema,
    get_connection,
    get_input_by_hash,
    create_input,
    get_scene,
    get_thread_by_scene_id,
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

app = typer.Typer(name="praxis", help="OpenPraxis - 将笔记转化为结构化实践与认知洞察")
console = Console()


def _hash_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


@app.command()
def add(
    file: Path = typer.Argument(..., exists=True, path_type=Path),
    type: str = typer.Option(None, "--type", "-t", help="report|interview|reflection|idea"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新处理（忽略重复 hash）"),
) -> None:
    """添加文件并运行 Tagger，可选进入 Practice。"""
    settings = get_settings()
    conn = get_connection(settings.db_path)
    ensure_schema(conn)
    raw_text = file.read_text(encoding="utf-8", errors="replace")
    file_hash = _hash_file(file)
    if not force:
        existing = get_input_by_hash(conn, file_hash)
        if existing:
            console.print("[yellow]相同内容已存在，使用 --force 强制重新处理。[/yellow]")
            conn.close()
            return
    input_id = str(uuid4())
    create_input(conn, input_id, str(file), file_hash, raw_text, type)
    graph = get_compiled_graph(str(settings.db_path))
    upsert_graph_thread(conn, input_id, input_id, status="running")
    initial: PraxisState = {
        "input_id": input_id,
        "raw_text": raw_text,
        "type_hint": type,
    }
    config = {"configurable": {"thread_id": input_id}}
    result = graph.invoke(initial, config=config)
    tagger_output = result.get("tagger_output")
    if tagger_output:
        save_tagger_output(conn, input_id, tagger_output)
        cap = tagger_output.capability_map.model_dump()
        show_tagger_summary(tagger_output.summary, cap)
    scene = result.get("scene")
    if scene:
        save_scene(conn, input_id, scene)
        upsert_graph_thread(conn, input_id, input_id, scene_id=scene.scene_id, status="interrupted")
        show_scene(
            scene.role,
            scene.task,
            scene.constraints,
            scene.expected_structure_hint,
        )
        console.print(f"\n[dim]使用 [bold]praxis answer {scene.scene_id}[/bold] 提交回答[/dim]")
    conn.close()


@app.command()
def practice(input_id: str = typer.Argument(...)) -> None:
    """对已有输入强制生成新的 Practice 场景。"""
    typer.echo(f"practice {input_id} (TODO: 实现)")


@app.command()
def answer(
    scene_id: str = typer.Argument(...),
    editor: bool = typer.Option(False, "--editor", "-e", help="用 $EDITOR 编辑"),
    file: Path | None = typer.Option(None, "--file", "-f", path_type=Path),
) -> None:
    """提交对某场景的回答并恢复图。"""
    settings = get_settings()
    conn = get_connection(settings.db_path)
    ensure_schema(conn)
    row = get_thread_by_scene_id(conn, scene_id)
    if not row:
        console.print("[red]未找到该 scene_id 对应的线程。[/red]")
        conn.close()
        raise typer.Exit(1)
    thread_id = row["thread_id"]
    input_id = row["input_id"]
    if editor:
        import tempfile
        import subprocess
        import os
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tf:
            tf.write("# 在此写下你的回答\n\n")
            tf.flush()
            editor_cmd = os.environ.get("EDITOR", "vim")
            subprocess.call([editor_cmd, tf.name])
            answer_text = Path(tf.name).read_text(encoding="utf-8", errors="replace")
            os.unlink(tf.name)
    elif file:
        answer_text = file.read_text(encoding="utf-8", errors="replace")
    else:
        console.print("请在 stdin 输入回答，以 EOF 结束（Ctrl+D）：")
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
    """查询并展示洞察卡片。"""
    settings = get_settings()
    conn = get_connection(settings.db_path)
    ensure_schema(conn)
    cards = get_insights(conn, input_id=input_id, insight_type=type, min_intensity=min_intensity)
    show_insight_cards(cards)
    conn.close()


@app.command()
def show(id: str = typer.Argument(...)) -> None:
    """展示完整链路：输入摘要 → Tagger → 场景 → 回答 → 评分 → 洞察卡。"""
    typer.echo(f"show {id} (TODO: 实现)")


@app.command()
def export(
    format: str = typer.Option("md", "--format", "-f", help="md|json"),
    output: Path | None = typer.Option(None, "--output", "-o", path_type=Path),
) -> None:
    """导出洞察卡片。"""
    typer.echo(f"export --format {format} (TODO: 实现)")


@app.command(name="list")
def list_inputs_cmd(
    type: str | None = typer.Option(None, "--type", "-t"),
    limit: int = typer.Option(50, "--limit", "-n"),
) -> None:
    """列出最近的输入。"""
    settings = get_settings()
    conn = get_connection(settings.db_path)
    ensure_schema(conn)
    rows = list_inputs(conn, input_type=type, limit=limit)
    from rich.table import Table
    table = Table(title="输入列表")
    table.add_column("id", style="dim")
    table.add_column("type")
    table.add_column("created_at")
    for r in rows:
        table.add_row(r["id"][:8] + "...", r["input_type"] or "-", r["created_at"])
    console.print(table)
    conn.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
