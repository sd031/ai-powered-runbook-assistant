#!/usr/bin/env python3
"""
AI Runbook Assistant — CLI

Commands:
  python cli.py ingest                  Ingest all docs in ./docs
  python cli.py ask "your question"     Ask a single question
  python cli.py interactive             Start REPL mode
  python cli.py stats                   Show DB stats
"""
from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()

app = typer.Typer(
    help="AI-Powered Runbook Assistant — RAG over your team's markdown runbooks.",
    add_completion=False,
)
console = Console()


def _dirs() -> tuple[str, str]:
    runbooks_dir = os.getenv("RUNBOOKS_DIR", "./docs")
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    return runbooks_dir, persist_dir


@app.command()
def ingest(
    runbooks_dir: str = typer.Option(
        None, "--dir", "-d", help="Directory containing markdown runbooks"
    ),
    clear: bool = typer.Option(
        False, "--clear", "-c", help="Clear existing vector DB before ingesting"
    ),
):
    """Ingest markdown runbooks into ChromaDB vector store."""
    from src.ingest import clear_collection, ingest_directory

    rdir, pdir = _dirs()
    if runbooks_dir:
        rdir = runbooks_dir

    Path(pdir).mkdir(parents=True, exist_ok=True)

    if clear:
        clear_collection(pdir)

    console.print(
        Panel(
            f"[bold blue]Ingesting runbooks from:[/bold blue] [cyan]{rdir}[/cyan]\n"
            f"[bold blue]Vector DB path:[/bold blue] [cyan]{pdir}[/cyan]",
            title="[bold]AI Runbook Assistant[/bold]",
            expand=False,
        )
    )

    total = ingest_directory(rdir, pdir)
    console.print(
        f"\n[bold green]✓ Ingestion complete![/bold green] "
        f"Stored [cyan]{total}[/cyan] chunks in ChromaDB."
    )


@app.command()
def ask(
    question: str = typer.Argument(..., help="The incident question to answer"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of context chunks to retrieve"),
    show_sources: bool = typer.Option(True, "--sources/--no-sources"),
    show_context: bool = typer.Option(False, "--context", help="Show raw retrieved chunks"),
):
    """Ask a question and get an AI-generated answer from your runbooks."""
    from src.query import ask as rag_ask

    _, pdir = _dirs()

    console.print(
        Panel(
            f"[bold yellow]{question}[/bold yellow]",
            title="[bold]❓ Incident Question[/bold]",
            expand=False,
        )
    )

    with console.status("[bold green]Searching runbooks and generating answer...[/bold green]"):
        result = rag_ask(question, pdir, top_k=top_k)

    console.print(
        Panel(
            Markdown(result.answer),
            title="[bold green]🤖 Answer[/bold green]",
            expand=False,
        )
    )

    if show_sources and result.sources:
        table = Table(
            title="📚 Sources Used",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Runbook File", style="cyan")
        for src in result.sources:
            table.add_row(src)
        console.print(table)

    if show_context:
        console.print("\n[dim]── Retrieved Context Chunks ──[/dim]")
        for i, (chunk, dist) in enumerate(
            zip(result.context_chunks, result.distances), 1
        ):
            console.print(
                Panel(
                    chunk,
                    title=f"[dim]Chunk {i}  (distance: {dist:.4f})[/dim]",
                    expand=False,
                )
            )


@app.command()
def interactive():
    """Start an interactive Q&A REPL against your runbooks."""
    from src.query import ask as rag_ask

    _, pdir = _dirs()

    console.print(
        Panel(
            "[bold blue]AI Runbook Assistant[/bold blue] — Interactive Mode\n"
            "Type your incident question and press [bold]Enter[/bold].\n"
            "Commands: [yellow]exit[/yellow] / [yellow]quit[/yellow] to stop, "
            "[yellow]clear[/yellow] to clear screen.",
            title="[bold]Welcome[/bold]",
            expand=False,
        )
    )

    while True:
        try:
            question = Prompt.ask("\n[bold yellow]Question[/bold yellow]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if question.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break
        if question.lower() == "clear":
            console.clear()
            continue
        if not question.strip():
            continue

        with console.status("[bold green]Thinking...[/bold green]"):
            result = rag_ask(question, pdir)

        console.print(
            Panel(
                Markdown(result.answer),
                title="[bold green]🤖 Answer[/bold green]",
                expand=False,
            )
        )
        if result.sources:
            console.print(
                f"[dim]📚 Sources: {', '.join(result.sources)}[/dim]"
            )


@app.command()
def stats():
    """Show vector database statistics."""
    from src.ingest import collection_stats

    _, pdir = _dirs()
    info = collection_stats(pdir)

    if "error" in info:
        console.print(f"[red]Error:[/red] {info['error']}")
        raise typer.Exit(1)

    table = Table(title="📊 Vector DB Stats", show_header=True, header_style="bold blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Collection", info["collection"])
    table.add_row("Total Chunks", str(info["total_chunks"]))
    table.add_row("DB Path", pdir)
    console.print(table)


if __name__ == "__main__":
    app()
