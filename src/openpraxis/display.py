"""Rich console output formatting."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()


def show_scene(role: str, task: str, constraints: list[str], hint: list[str]) -> None:
    """Display practice scene."""
    body = f"[bold]Role[/bold]\n{role}\n\n[bold]Task[/bold]\n{task}\n\n"
    if constraints:
        body += f"[bold]Constraints[/bold]\n" + "\n".join(f"  • {c}" for c in constraints) + "\n\n"
    if hint:
        body += f"[bold]Answer structure hint[/bold]\n" + "\n".join(f"  • {h}" for h in hint)
    _console.print(Panel(body, title="Practice scene", border_style="blue"))


def show_tagger_summary(summary: str, capability_map: dict) -> None:
    """Display Tagger summary and capability map."""
    _console.print(Panel(summary, title="Summary", border_style="green"))
    table = Table(title="Capability map")
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", justify="right", style="yellow")
    for k, v in capability_map.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    _console.print(table)


def show_insight_cards(cards: list[dict]) -> None:
    """Display insight cards list."""
    for c in cards:
        _console.print(
            Panel(
                f"[bold]{c.get('insight_title', '')}[/bold]\n"
                f"{c.get('what_happened', '')}\n\n"
                f"[dim]Upgrade pattern[/dim] {c.get('upgrade_pattern', '')}\n"
                f"[dim]Micro practice[/dim] {c.get('micro_practice', '')}",
                title=f"Insight · {c.get('insight_type', '')}",
                border_style="magenta",
            )
        )


def show_performance(signal: dict, improvement_vectors: list[str]) -> None:
    """Display evaluation result and improvement vectors."""
    table = Table(title="Evaluation")
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", justify="right", style="yellow")
    for k, v in signal.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    _console.print(table)
    if improvement_vectors:
        _console.print("[bold]Improvement suggestions[/bold]")
        for v in improvement_vectors:
            _console.print(f"  • {v}")
