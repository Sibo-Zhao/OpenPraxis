"""Rich 控制台输出格式化。"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()


def show_scene(role: str, task: str, constraints: list[str], hint: list[str]) -> None:
    """展示练习场景。"""
    body = f"[bold]角色[/bold]\n{role}\n\n[bold]任务[/bold]\n{task}\n\n"
    if constraints:
        body += f"[bold]约束[/bold]\n" + "\n".join(f"  • {c}" for c in constraints) + "\n\n"
    if hint:
        body += f"[bold]回答结构建议[/bold]\n" + "\n".join(f"  • {h}" for h in hint)
    _console.print(Panel(body, title="练习场景", border_style="blue"))


def show_tagger_summary(summary: str, capability_map: dict) -> None:
    """展示 Tagger 摘要与能力地图。"""
    _console.print(Panel(summary, title="摘要", border_style="green"))
    table = Table(title="能力地图")
    table.add_column("维度", style="cyan")
    table.add_column("分数", justify="right", style="yellow")
    for k, v in capability_map.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    _console.print(table)


def show_insight_cards(cards: list[dict]) -> None:
    """展示洞察卡片列表。"""
    for c in cards:
        _console.print(
            Panel(
                f"[bold]{c.get('insight_title', '')}[/bold]\n"
                f"{c.get('what_happened', '')}\n\n"
                f"[dim]升级模式[/dim] {c.get('upgrade_pattern', '')}\n"
                f"[dim]微练习[/dim] {c.get('micro_practice', '')}",
                title=f"Insight · {c.get('insight_type', '')}",
                border_style="magenta",
            )
        )


def show_performance(performance: dict, improvement_vectors: list[str]) -> None:
    """展示评估结果与改进向量。"""
    sig = performance.get("performance_signal", {})
    table = Table(title="评估")
    table.add_column("维度", style="cyan")
    table.add_column("分数", justify="right", style="yellow")
    for k, v in sig.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    _console.print(table)
    if improvement_vectors:
        _console.print("[bold]改进建议[/bold]")
        for v in improvement_vectors:
            _console.print(f"  • {v}")
