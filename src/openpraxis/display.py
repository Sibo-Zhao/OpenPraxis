"""Rich console output formatting."""

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_console = Console()


def _score_style(score: int) -> str:
    """Return color style for numeric score."""
    if score >= 8:
        return "bold green"
    if score >= 6:
        return "bold yellow"
    return "bold red"


def _format_dimension(name: str) -> str:
    """Format snake_case dimension names into title text."""
    return name.replace("_", " ").title()


def show_scene(role: str, task: str, constraints: list[str], hint: list[str]) -> None:
    """Display practice scene."""
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style="bold bright_cyan", width=24)
    table.add_column(style="white")
    table.add_row("Role", role)
    table.add_row("Task", task)
    if constraints:
        table.add_row("Constraints", "\n".join(f"[cyan]•[/cyan] {c}" for c in constraints))
    if hint:
        table.add_row("Answer structure hint", "\n".join(f"[green]•[/green] {h}" for h in hint))

    _console.print(
        Panel(
            table,
            title="Practice scene",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 1),
        )
    )


def show_tagger_summary(summary: str, capability_map: dict) -> None:
    """Display Tagger summary and capability map."""
    summary_text = Text(summary, style="white")
    _console.print(
        Panel(
            summary_text,
            title="Summary",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 1),
        )
    )

    table = Table(title="Capability map", box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("Dimension", style="bold cyan")
    table.add_column("Score", justify="right")
    for k, v in capability_map.items():
        style = _score_style(v) if isinstance(v, int) else "yellow"
        table.add_row(_format_dimension(k), f"[{style}]{v}[/{style}]")
    _console.print(table)


def show_insight_cards(cards: list[dict]) -> None:
    """Display insight cards list."""
    for c in cards:
        intensity = c.get("intensity", "-")
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(style="bold bright_cyan", width=18)
        grid.add_column(style="white")
        grid.add_row("What happened", c.get("what_happened", ""))
        grid.add_row("Why it matters", c.get("why_it_matters", ""))
        grid.add_row("Upgrade pattern", c.get("upgrade_pattern", ""))
        grid.add_row("Micro practice", c.get("micro_practice", ""))

        concepts = c.get("concepts")
        if concepts:
            grid.add_row("Concepts", ", ".join(concepts))

        skills = c.get("skills")
        if skills:
            grid.add_row("Skills", ", ".join(skills))

        _console.print(
            Panel(
                Group(f"[bold]{c.get('insight_title', '')}[/bold]", "", grid),
                subtitle=f"Intensity: {intensity}",
                subtitle_align="right",
                title=f"Insight · {c.get('insight_type', '')}",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )


def show_performance(signal: dict, improvement_vectors: list[str]) -> None:
    """Display evaluation result and improvement vectors."""
    table = Table(title="Evaluation", box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("Dimension", style="bold cyan")
    table.add_column("Score", justify="right")
    for k, v in signal.items():
        style = _score_style(v) if isinstance(v, int) else "yellow"
        table.add_row(_format_dimension(k), f"[{style}]{v}[/{style}]")
    _console.print(table)
    if improvement_vectors:
        suggestions = "\n".join(f"[green]•[/green] {v}" for v in improvement_vectors)
        _console.print(
            Panel(
                suggestions,
                title="Improvement suggestions",
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
