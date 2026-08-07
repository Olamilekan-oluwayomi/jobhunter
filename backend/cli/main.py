"""JobHunter CLI.

Typer-based command line interface with rich, colourful output.

Commands
-------
scrape         Run all scrapers and save new jobs
automate       Run the full automation once (scrape, insert, notify, log)
scheduler      Run the hourly scheduler in the foreground
stats          Show aggregate statistics
jobs           List / filter / search / sort jobs
search         Search jobs by keyword
save           Save a job to track it later
saved          List saved jobs
apply          Record an application for a job
status         Update a job's workflow status
match          Rank jobs against your profile (roles, skills, preferences)
export csv     Export jobs to a CSV file
export json    Export jobs to a JSON file
clean          Remove orphaned rows (and optionally all job data)
"""

import csv
import json
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from sqlalchemy.orm import Session

from api.schemas import ApplicationStatus
from cli.ui import (
    box,
    confirm,
    console,
    error,
    info,
    install_logging,
    render_jobs,
    status_pill,
    success,
    warn,
)
from config import get_settings
from database import SessionLocal
from database import repository as repo
from database.repository import WORKFLOW_STATUSES
from matching.scorer import JobProfile
from matching.service import RankingResult, rank_jobs
from scrapers.manager import ScraperManager, ScraperResult, build_scrapers

app = typer.Typer(
    name="jobhunter",
    help="JobHunter — aggregate, browse and track remote jobs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
export_app = typer.Typer(
    help="Export jobs to a file (CSV or JSON).",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(export_app, name="export")


@app.callback()
def main_callback(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show debug logging.")] = False,
) -> None:
    install_logging(verbosity=1 if verbose else 0)


EXPORT_FIELDS = [
    "id",
    "title",
    "company",
    "location",
    "salary",
    "description",
    "url",
    "source",
    "posted_at",
]


@app.command()
def scrape(
    sources: Annotated[
        str | None,
        typer.Option("--source", "-s", help="Scrape only these sources (comma-separated)."),
    ] = None,
):
    """Run every scraper concurrently, save new jobs, then print statistics."""
    box("Starting scrape")

    scrapers, disabled = build_scrapers(sources)
    if not scrapers and not disabled:
        error("No scrapers matched the requested sources.")
        raise typer.Exit(1)

    manager = ScraperManager(scrapers=scrapers, disabled_sources=disabled)
    fetched = _run_scrapers(manager)
    results = manager.results

    db: Session = SessionLocal()
    try:
        saved = 0
        new_by_source: dict[str, int] = {}
        for job in fetched:
            if repo.save_job(db, job):
                saved += 1
                new_by_source[job["source"]] = new_by_source.get(job["source"], 0) + 1
    finally:
        db.close()

    success(f"Scrape finished — {len(fetched)} job(s) fetched, {saved} new saved.")
    _render_scrape_summary(results, new_by_source)
    stats()


def _run_scrapers(manager: ScraperManager) -> list[dict]:
    """Run scrapers concurrently with a live per-source progress display.

    Each scraper runs in its own thread; a single failed or unavailable
    source never blocks the others. Returns every normalized job dict for
    later persistence; per-source details live in ``manager.results``.
    """
    started = time.perf_counter()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        transient=False,
    )
    tasks = {
        scraper.source: progress.add_task(scraper.source, total=1) for scraper in manager.scrapers
    }

    def on_source_done(result: ScraperResult | None) -> None:
        if result is None:
            return
        task = tasks.get(result.source)
        if task is None:
            return
        color = (
            "green"
            if result.status == "OK"
            else ("yellow" if result.status in ("UNAVAILABLE", "DISABLED", "EMPTY") else "red")
        )
        progress.update(
            task,
            description=f"[{color}]{result.source} ({result.status})[/]",
            completed=1,
        )

    with progress:
        fetched = manager.fetch_all(on_source_done=on_source_done)

    elapsed = time.perf_counter() - started
    info(f"Scraped all sources in {elapsed:.1f}s")
    return fetched


def _render_scrape_summary(
    results: dict[str, ScraperResult], new_by_source: dict[str, int]
) -> None:
    """Print the per-source Raw | Parsed | New | Status summary table."""
    from rich.table import Table

    table = Table(title="Scrape summary", header_style="bold blue", border_style="blue")
    table.add_column("Source", style="cyan")
    table.add_column("Raw", justify="right", style="white")
    table.add_column("Parsed", justify="right", style="green")
    table.add_column("New", justify="right", style="green")
    table.add_column("Status", style="white")

    for source in sorted(results):
        result = results[source]
        color = (
            "green"
            if result.status == "OK"
            else ("yellow" if result.status in ("UNAVAILABLE", "DISABLED", "EMPTY") else "red")
        )
        table.add_row(
            source,
            str(result.raw),
            str(result.parsed),
            str(new_by_source.get(source, 0)),
            f"[{color}]{result.status}[/]",
        )
    console.print(table)

    for source in sorted(results):
        result = results[source]
        if result.status != "OK" and result.message:
            warn(f"{source}: {result.message}")


@app.command()
def stats():
    """Show aggregate statistics about the job database."""
    db: Session = SessionLocal()
    try:
        counts = repo.get_stats(db)
    finally:
        db.close()
    _render_stats(counts)


def _render_stats(counts: dict) -> None:
    from rich.columns import Columns
    from rich.panel import Panel
    from rich.table import Table

    box("Statistics")
    columns = Columns(
        [
            Panel(
                f"[bold green]{counts['total_jobs']}[/] jobs",
                title="Database",
                border_style="green",
            ),
            Panel(
                f"[bold cyan]{counts['sources']}[/] sources",
                title="Sources",
                border_style="cyan",
            ),
            Panel(
                f"[bold yellow]{counts['total_saved']}[/] saved",
                title="Saved",
                border_style="yellow",
            ),
            Panel(
                f"[bold magenta]{counts['total_applications']}[/] applied",
                title="Applications",
                border_style="magenta",
            ),
        ],
        padding=1,
    )
    console.print(columns)

    if counts.get("by_source"):
        table = Table(title="Jobs per source", header_style="bold blue", border_style="blue")
        table.add_column("Source", style="cyan")
        table.add_column("Jobs", justify="right", style="green")
        for src, count in sorted(counts["by_source"].items(), key=lambda x: -x[1]):
            table.add_row(src, str(count))
        console.print(table)

    if counts.get("by_status"):
        table = Table(
            title="Applications per status", header_style="bold blue", border_style="blue"
        )
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for status, count in sorted(counts["by_status"].items(), key=lambda x: -x[1]):
            table.add_row(status, str(count))
        console.print(table)


@app.command()
def jobs(
    page: Annotated[int, typer.Option(help="Page number (1-indexed).")] = 1,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Jobs per page.")] = 20,
    search: Annotated[
        str | None,
        typer.Option(
            "--search", "-q", help="Full-text search across title, company, location, description."
        ),
    ] = None,
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Filter by source name.")
    ] = None,
    company: Annotated[
        str | None, typer.Option("--company", "-c", help="Filter by company name.")
    ] = None,
    location: Annotated[
        str | None, typer.Option("--location", "-l", help="Filter by location.")
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Filter by workflow status: saved, applied, interview, rejected, offer.",
        ),
    ] = None,
    sort_by: Annotated[
        str, typer.Option("--sort-by", help="Sort field: posted_at, created_at, title, company.")
    ] = "posted_at",
    order: Annotated[str, typer.Option("--order", help="Sort order: asc or desc.")] = "desc",
):
    """Browse jobs with pagination, filtering, search and sorting."""
    if status is not None and status not in WORKFLOW_STATUSES:
        error("Invalid --status value. Use one of: " + ", ".join(WORKFLOW_STATUSES) + ".")
        raise typer.Exit(1)

    db: Session = SessionLocal()
    try:
        rows, total = repo.list_jobs(
            db,
            page=page,
            page_size=limit,
            search=search,
            source=source,
            company=company,
            location=location,
            status=status,
            sort_by=sort_by,
            order=order,
        )
    finally:
        db.close()

    if not rows and page == 1:
        warn("No jobs found.")
        return
    render_jobs(rows, title=f"Jobs — page {page} ({total} total)")
    info(f"{len(rows)} of {total} jobs shown (page {page}/{max(1, -(-total // limit))}).")


@app.command()
def search(
    term: Annotated[str, typer.Argument(help="Keyword to search for.")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results.")] = 20,
    source: Annotated[str | None, typer.Option("--source", "-s", help="Filter by source.")] = None,
):
    """Search jobs by keyword across title, company, location and description."""
    db: Session = SessionLocal()
    try:
        rows, total = repo.list_jobs(db, page=1, page_size=limit, search=term, source=source)
    finally:
        db.close()

    if not rows:
        warn(f"No jobs matched “{term}”.")
        return
    render_jobs(rows, title=f"“{term}” — {total} match(es)")
    info(f"Showing {len(rows)} of {total}.")


@app.command()
def match(
    min_score: Annotated[
        int, typer.Option("--min-score", help="Only show jobs scoring at least this (0-100).")
    ] = 0,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum matches shown.")] = 10,
):
    """Rank jobs against your profile (roles, skills, preferences)."""
    settings = get_settings()
    profile = JobProfile(
        roles=tuple(settings.profile_roles),
        skills=tuple(settings.profile_skills),
        preferences=tuple(settings.profile_preferences),
    )

    db: Session = SessionLocal()
    try:
        result = rank_jobs(db, profile, min_score=min_score, limit=limit)
        _render_match_table(result, profile, min_score)
    finally:
        db.close()


def _render_match_table(result: RankingResult, profile: JobProfile, min_score: int) -> None:
    from rich.table import Table

    box("Top Matches")
    info(
        "Profile: "
        + "; ".join(
            [
                f"roles: {', '.join(profile.roles)}",
                f"skills: {', '.join(profile.skills)}",
                f"preferences: {', '.join(profile.preferences)}",
            ]
        )
    )

    if not result.items:
        warn(f"No jobs scored at least {min_score}.")
        return

    table = Table(header_style="bold blue", border_style="blue")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Title", style="cyan")
    table.add_column("Company", style="white")
    table.add_column("Matched skills", style="green", max_width=40)
    table.add_column("Missing skills", style="dim", max_width=40)
    for entry in result.items:
        table.add_row(
            str(entry.score.score),
            (entry.job.title or "—")[:70],
            (entry.job.company or "—")[:30],
            ", ".join(entry.score.matched_skills) or "—",
            ", ".join(entry.score.missing_skills[:6]) or "—",
        )
    console.print(table)
    info(
        f"Scored {result.total_scored} job(s); {result.total_matched} matched "
        f">= {min_score}; showing top {len(result.items)}."
    )


@app.command()
def save(job_id: Annotated[int, typer.Argument(help="ID of the job to save.")]):
    """Save a job so you can track it later."""
    db: Session = SessionLocal()
    try:
        job = repo.get_job(db, job_id)
        if job is None:
            error(f"Job {job_id} does not exist.")
            raise typer.Exit(1)
        entry = repo.create_saved_job(db, job_id)
        title, company = job.title, job.company
        score = job.match_score.score if job.match_score is not None else None
        already_saved = entry is None
    finally:
        db.close()

    if already_saved:
        info(f"Job #{job_id} was already saved.")
    else:
        success(f"Saved job #{job_id}")
    _render_job_confirmation(title, company, score)


def _render_job_confirmation(title: str, company: str, score: int | None) -> None:
    console.print(f"[bold]{title}[/]")
    console.print(company)
    if score is not None:
        console.print(f"Match: [green]{score}[/]")


@app.command()
def saved():
    """List saved jobs with their match score and current status."""
    db: Session = SessionLocal()
    try:
        entries = repo.list_saved_jobs(db)
        rows = [
            {
                "id": entry.job.id,
                "score": entry.job.match_score.score if entry.job.match_score is not None else None,
                "title": entry.job.title,
                "company": entry.job.company,
                "location": entry.job.location,
                "status": entry.job.applications[0].status if entry.job.applications else "saved",
            }
            for entry in entries
        ]
    finally:
        db.close()

    if not rows:
        info("No saved jobs yet.")
        return
    _render_saved_table(rows)
    info(f"{len(rows)} saved job(s).")


def _render_saved_table(rows: list[dict]) -> None:
    from rich.table import Table

    table = Table(title="Saved Jobs", header_style="bold green", border_style="green")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("Location", style="magenta")
    table.add_column("Status")
    for row in rows:
        table.add_row(
            str(row["id"]),
            str(row["score"]) if row["score"] is not None else "—",
            (row["title"] or "—")[:70],
            (row["company"] or "—")[:30],
            (row["location"] or "—")[:30],
            status_pill(row["status"]),
        )
    console.print(table)


@app.command()
def apply(
    job_id: Annotated[int, typer.Argument(help="ID of the job to apply to.")],
    status: Annotated[
        ApplicationStatus, typer.Option("--status", help="Application status.")
    ] = "applied",
    notes: Annotated[str | None, typer.Option("--notes", help="Optional notes.")] = None,
):
    """Record (or update) an application for a job."""
    db: Session = SessionLocal()
    try:
        job = repo.get_job(db, job_id)
        if job is None:
            error(f"Job {job_id} does not exist.")
            raise typer.Exit(1)
        entry = repo.upsert_application(db, job_id, status, notes)
        title, company = job.title, job.company
        applied_status, applied_at = entry.status, entry.applied_at
    finally:
        db.close()

    success("Application recorded")
    console.print(f"[bold]{title}[/]")
    console.print(company)
    console.print(f"Status: {status_pill(applied_status)}")
    console.print(f"Applied: {applied_at.strftime('%Y-%m-%d') if applied_at else '—'}")


@app.command()
def status(
    job_id: Annotated[int, typer.Argument(help="ID of the job to update.")],
    status: Annotated[
        str,
        typer.Argument(help="Workflow status: saved, applied, interview, rejected, offer."),
    ],
):
    """Update a job's workflow status."""
    if status not in WORKFLOW_STATUSES:
        error("Invalid status. Use one of: " + ", ".join(WORKFLOW_STATUSES) + ".")
        raise typer.Exit(1)

    db: Session = SessionLocal()
    try:
        job = repo.get_job(db, job_id)
        if job is None:
            error(f"Job {job_id} does not exist.")
            raise typer.Exit(1)
        if status == "saved":
            repo.create_saved_job(db, job_id)
        else:
            repo.upsert_application(db, job_id, status)
        title, company = job.title, job.company
    finally:
        db.close()

    success(f"Job #{job_id} status updated")
    console.print(f"[bold]{title}[/]")
    console.print(company)
    console.print(f"Status: {status_pill(status)}")


@export_app.command("csv")
def export_csv(
    output: Annotated[Path, typer.Argument(help="Output .csv path.")],
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Only export one source.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum rows.")] = 5000,
):
    """Export jobs to a CSV file."""
    db: Session = SessionLocal()
    try:
        rows, _ = repo.list_jobs(db, page=1, page_size=limit, source=source, sort_by="posted_at")
    finally:
        db.close()

    if not rows:
        warn("Nothing to export.")
        return

    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for job in rows:
            writer.writerow(_job_to_dict(job))
    success(f"Exported {len(rows)} jobs to {output}.")


@export_app.command("json")
def export_json(
    output: Annotated[Path, typer.Argument(help="Output .json path.")],
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Only export one source.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum rows.")] = 5000,
    indent: Annotated[int, typer.Option("--indent", help="JSON indent (pretty-print).")] = 2,
):
    """Export jobs to a JSON file."""
    db: Session = SessionLocal()
    try:
        rows, _ = repo.list_jobs(db, page=1, page_size=limit, source=source, sort_by="posted_at")
    finally:
        db.close()

    data = [_job_to_dict(job) for job in rows]
    if not data:
        warn("Nothing to export.")
        return

    with output.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=indent)
    success(f"Exported {len(data)} jobs to {output}.")


@app.command()
def clean(
    purge_all: Annotated[
        bool, typer.Option("--purge-all", help="Delete ALL jobs, saved entries and applications.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompts.")] = False,
):
    """Remove orphaned saved/application rows, or purge all data with --purge-all."""
    db: Session = SessionLocal()
    try:
        if purge_all:
            if not yes and not confirm(
                "[bold orange1]Permanently delete ALL jobs, saved jobs and"
                " applications?[/] This cannot be undone."
            ):
                info("Aborted.")
                return
            removed = repo.purge_all_data(db)
            success("Purged database: " + ", ".join(f"{k}={v}" for k, v in removed.items()))
            return

        removed_saved = repo.purge_orphaned_saved(db)
        removed_apps = repo.purge_orphaned_applications(db)
    finally:
        db.close()

    if removed_saved == 0 and removed_apps == 0:
        info("Nothing to clean — no orphaned rows.")
        return
    success(
        f"Removed {removed_saved} orphaned saved job(s) and {removed_apps} orphaned application(s)."
    )


def _job_to_dict(job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "description": job.description,
        "url": job.url,
        "source": job.source,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
    }


def _render_automation_report(report) -> None:
    from rich.table import Table

    box("Automated run")
    info(f"Started: [bold]{report.started_at.strftime('%Y-%m-%d %H:%M:%S')}[/]")
    info(f"Duration: [bold]{report.duration_seconds:.1f}s[/]")
    console.print(
        f"Fetched: [bold cyan]{report.total_fetched}[/] · "
        f"New: [bold green]{report.new_jobs}[/] · "
        f"Already existed: [bold yellow]{report.already_exists}[/]"
    )

    if report.by_source:
        table = Table(title="Per-source", header_style="bold blue", border_style="blue")
        table.add_column("Source", style="cyan")
        table.add_column("Fetched", justify="right", style="green")
        table.add_column("New", justify="right", style="green")
        table.add_column("Exists", justify="right", style="yellow")
        table.add_column("Status", style="white")
        for source, stat in sorted(report.by_source.items()):
            status = stat.get("status", "OK")
            color = (
                "green"
                if status == "OK"
                else ("yellow" if status in ("UNAVAILABLE", "DISABLED", "EMPTY") else "red")
            )
            table.add_row(
                source,
                str(stat["fetched"]),
                str(stat["new"]),
                str(stat["exists"]),
                f"[{color}]{status}[/]",
            )
        console.print(table)

    if report.failed_sources:
        warn("Unavailable sources: " + ", ".join(report.failed_sources))

    notified = report.notified or {}
    if notified.get("channels_enabled"):
        info(
            f"Notifications: matched [bold]{notified.get('matched', 0)}[/] · "
            f"Discord [bold]{notified.get('discord', 0)}[/] · "
            f"Telegram [bold]{notified.get('telegram', 0)}[/]"
        )
    else:
        info("Notifications: disabled (no channels configured).")


@app.command()
def automate():
    """Run the full automation once: scrape, insert new jobs, notify, log."""
    from scheduler.jobs import run_automation

    report = run_automation(triggered_by="cli")
    _render_automation_report(report)


@app.command()
def scheduler():
    """Run the hourly scheduler in the foreground (Ctrl+C to stop)."""
    from scheduler.runner import Scheduler

    box("Hourly scheduler")
    info("Press Ctrl+C to stop.")
    runner_ = Scheduler()
    runner_.run_forever()


if __name__ == "__main__":
    app()
