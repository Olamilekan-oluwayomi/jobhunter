"""Shared Rich UI helpers for the JobHunter CLI."""

import logging
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

#: Default console; `soft_wrap` keeps long rows readable in terminals.
console = Console(soft_wrap=True, highlight=False)
error_console = Console(stderr=True)

LOG_LEVEL_STYLES = {
    "DEBUG": "dim",
    "INFO": "cyan",
    "WARNING": "bold yellow",
    "ERROR": "bold red",
    "CRITICAL": "bold white on red",
}


class RichLogHandler(logging.Handler):
    """Render logging records as coloured Rich lines beneath the app."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = record.levelname
            style = LOG_LEVEL_STYLES.get(level, "")
            label = record.levelname[0]
            time = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            message = record.getMessage()

            if record.exc_info:
                message += (
                    "\n" + self.formatter.formatException(record.exc_info) if self.formatter else ""
                )
            target = error_console if record.levelno >= logging.ERROR else console
            target.print(f"[{style}]{label}[/] [dim]{time}[/] {message}")
        except Exception:
            self.handleError(record)

    def format_message(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def install_logging(verbosity: int = 0) -> None:
    """Route Python logging through a Rich handler for tidy terminal output.

    `verbosity` raises the root level (0 = INFO, 1 = DEBUG, 2 = TRACE).
    """
    handler = RichLogHandler()
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logging.basicConfig(level=logging.DEBUG, handlers=[handler], force=True)
    # Keep noisy third-party loggers quiet unless tracing.
    for noisy in ("urllib3", "requests", "asyncio", "alembic", "sqlalchemy"):
        logging.getLogger(noisy).setLevel(logging.DEBUG if verbosity >= 1 else logging.WARNING)
    if verbosity >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("cli").setLevel(logging.INFO)


def box(text: str, title: str = "JobHunter") -> None:
    """Render a centered banner panel."""
    console.print(
        Panel(Text(f":hammer: {text}", style="bold cyan"), title=title, border_style="cyan")
    )


def success(message: str) -> None:
    console.print(f"[bold green]✓[/] {message}")


def info(message: str) -> None:
    console.print(f"[bold blue]>[/] {message}")


def warn(message: str) -> None:
    console.print(f"[bold yellow]⚠[/] {message}")


def error(message: str) -> None:
    error_console.print(f"[bold red]✗[/] {message}")


def job_table(title: str = "Jobs") -> Table:
    table = Table(title=title, header_style="bold cyan", border_style="cyan", show_lines=False)
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("Location", style="magenta")
    table.add_column("Posted", style="green", no_wrap=False)
    table.add_column("Source", style="blue")
    return table


def render_jobs(jobs: list, title: str = "Jobs") -> None:
    table = job_table(title)
    for job in jobs:
        posted = job.posted_at.strftime("%Y-%m-%d") if job.posted_at else "—"
        location = job.location if getattr(job, "location", None) else "—"
        table.add_row(
            str(job.id),
            (job.title or "—")[:80],
            (job.company or "—")[:30],
            (location or "—")[:30],
            posted,
            job.source,
        )
    console.print(table)


def status_pill(status: str) -> str:
    colors = {
        "applied": "cyan",
        "interviewing": "yellow",
        "offer": "green",
        "rejected": "red",
    }
    return f"[{colors.get(status, 'white')}]{status}[/]"


def confirm(message: str) -> bool:
    from rich.prompt import Prompt

    answer = Prompt.ask(message, choices=["y", "n"], default="n")
    return answer.strip().lower().startswith("y")
