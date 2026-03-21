"""Interface de usuário com rich para o exam2bench."""

from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn
from rich.rule import Rule
from rich.table import Table

console = Console()


class ExamProgress:
    """Gerencia progress bars para processamento de exames."""

    def __init__(self):
        self.progress = Progress(
            TextColumn("  {task.fields[name]:<14s}", style="cyan"),
            BarColumn(bar_width=26),
            TextColumn("{task.percentage:>4.0f}%"),
            TextColumn("{task.fields[status]}"),
            console=console,
        )

    def __enter__(self):
        self.progress.__enter__()
        return self

    def __exit__(self, *args):
        self.progress.__exit__(*args)

    def add_exam(self, name: str, total_pages: int) -> TaskID:
        """Adiciona um exame com N páginas totais."""
        return self.progress.add_task(
            name, total=total_pages, name=name, status="",
        )

    def page_done(self, task_id: TaskID) -> None:
        """Avança a barra em 1 página."""
        self.progress.advance(task_id)

    def update_status(self, task_id: TaskID, status: str) -> None:
        """Atualiza o texto de status de um exame."""
        self.progress.update(task_id, status=status)

    def exam_done(self, task_id: TaskID, num_questions: int, num_failed: int = 0) -> None:
        """Marca exame como concluído."""
        if num_failed > 0:
            status = f"[yellow]{num_questions}q (!{num_failed} falhas)[/yellow]"
        else:
            status = f"[green]{num_questions}q[/green]"
        self.progress.update(
            task_id, completed=self.progress.tasks[task_id].total,
            status=status,
        )

    def exam_error(self, task_id: TaskID, error: str) -> None:
        """Marca exame com erro."""
        self.progress.update(
            task_id, status=f"[red]erro: {error}[/red]",
        )

    def exam_cached(self, name: str, num_questions: int) -> None:
        """Mostra exame carregado do cache (barra completa instantânea)."""
        tid = self.progress.add_task(
            name, total=1, completed=1, name=name,
            status=f"[dim]{num_questions}q (cache)[/dim]",
        )
        return tid


def header(title: str) -> None:
    """Imprime cabeçalho formatado."""
    console.print()
    console.print(Rule(title, style="bold"))
    console.print()


def section(text: str) -> None:
    """Imprime seção."""
    console.print(f"[bold]{text}[/bold]")


def summary(title: str, items: dict[str, str]) -> None:
    """Imprime resumo final formatado."""
    console.print()
    console.print(Rule(style="green"))
    console.print(f"[bold green]{title}[/bold green]")
    for key, value in items.items():
        console.print(f"  {key}: {value}")
    console.print()


def error(text: str) -> None:
    """Imprime erro."""
    console.print(f"[bold red]Erro:[/bold red] {text}")


def info(text: str) -> None:
    """Imprime informação."""
    console.print(f"  {text}")


def warn(text: str) -> None:
    """Imprime aviso."""
    console.print(f"  [yellow]Aviso:[/yellow] {text}")
