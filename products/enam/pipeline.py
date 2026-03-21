"""Orquestrador para construção do dataset ENAM completo."""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from exam2bench.exporter import export_to_csv, export_to_jsonl
from exam2bench.models import ExamQuestion
from exam2bench import ui

from .subject_map import get_subject_for_question


def _extract_edition_info(exam_name: str) -> dict:
    """Extrai metadados do nome do exame (ex: 'enam-20241' → edição '20241', ano 2024)."""
    m = re.search(r"enam-(\d{4})(\d)(r?)", exam_name)
    if not m:
        return {}
    year = int(m.group(1))
    semester = int(m.group(2))
    reapplication = bool(m.group(3))
    edition_id = f"{year}{semester}{'r' if reapplication else ''}"
    return {
        "edition": edition_id,
        "year": year,
        "semester": semester,
        "reapplication": reapplication,
        "source_format": "pdf",
    }


def _enrich_metadata(questions: list[ExamQuestion], exam_name: str) -> list[ExamQuestion]:
    """Enriquece questões com metadados de edição e matéria."""
    meta = _extract_edition_info(exam_name)
    for q in questions:
        q.metadata.update(meta)
        subject = get_subject_for_question(
            meta.get("edition", ""), q.question_number
        )
        if subject:
            q.metadata["subject"] = subject
    return questions


def _load_from_cache(cache_file: Path) -> list[ExamQuestion]:
    """Carrega questões de um arquivo cache JSONL."""
    with open(cache_file, encoding="utf-8") as f:
        return [
            ExamQuestion.model_validate_json(line)
            for line in f
            if line.strip()
        ]


def _process_one_exam(
    prova_path: Path,
    gabarito_path: Path,
    exam_name: str,
    cache_dir: Path,
    progress: ui.ExamProgress | None = None,
    task_id=None,
) -> tuple[list[ExamQuestion], int]:
    """Processa um único exame com progress bar. Retorna (questões, num_falhas)."""
    from exam2bench.cli import process_exam
    from exam2bench.pdf_processor import pdf_to_base64_images

    # Contar páginas para progress bar
    prova_pages = pdf_to_base64_images(prova_path)
    gabarito_pages = pdf_to_base64_images(gabarito_path)
    total_pages = len(prova_pages) + len(gabarito_pages)

    if progress and task_id is not None:
        progress.progress.update(task_id, total=total_pages)

    def on_page_done(page_num: int, count: int) -> None:
        if progress and task_id is not None:
            progress.page_done(task_id)

    output_path, _, num_q, num_failed = process_exam(
        prova_path, gabarito_path, exam_name,
        cache_dir, fmt="jsonl", max_workers=1,
        quiet=True, on_page_done=on_page_done,
    )

    questions = _load_from_cache(output_path)
    return _enrich_metadata(questions, exam_name), num_failed


def _process_pdf_exams(
    pdf_dir: Path, force: bool = False, max_workers: int = 4,
) -> list[ExamQuestion]:
    """Processa edições do ENAM a partir de PDFs."""
    from exam2bench.pairing import find_exam_pairs

    if not pdf_dir.exists():
        return []

    pairs = find_exam_pairs(pdf_dir, prova_suffix="-prova", gabarito_suffix="-gabarito")

    if not pairs:
        ui.info("Nenhum par de PDF encontrado")
        return []

    cache_dir = pdf_dir / ".cache"
    all_questions: list[ExamQuestion] = []
    to_process: list[tuple[Path, Path, str]] = []

    with ui.ExamProgress() as progress:
        # Separar cacheados dos pendentes
        for prova_path, gabarito_path, exam_name in pairs:
            cache_file = cache_dir / f"{exam_name}.jsonl"
            if cache_file.exists() and not force:
                questions = _load_from_cache(cache_file)
                questions = _enrich_metadata(questions, exam_name)
                all_questions.extend(questions)
                progress.exam_cached(exam_name, len(questions))
            else:
                to_process.append((prova_path, gabarito_path, exam_name))

        if not to_process:
            return all_questions

        # Criar tasks para exames pendentes (total inicial = 1, atualizado depois)
        exam_tasks = {}
        for prova, gabarito, name in to_process:
            tid = progress.add_exam(name, total_pages=1)
            exam_tasks[name] = tid

        # Processar pendentes em paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _process_one_exam, prova, gabarito, name, cache_dir,
                    progress, exam_tasks[name],
                ): name
                for prova, gabarito, name in to_process
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    questions, num_failed = future.result()
                    all_questions.extend(questions)
                    progress.exam_done(exam_tasks[name], len(questions), num_failed)
                except Exception as e:
                    progress.exam_error(exam_tasks[name], str(e)[:40])

    return all_questions


def _export_dataset(
    questions: list[ExamQuestion], output_dir: Path, fmt: str
) -> Path:
    """Exporta dataset completo e per-edition."""
    output_dir.mkdir(parents=True, exist_ok=True)

    questions.sort(
        key=lambda q: (q.metadata.get("edition", ""), q.question_number)
    )

    main_path = None
    if fmt in ("jsonl", "both"):
        main_path = output_dir / "enam-exams.jsonl"
        export_to_jsonl(questions, main_path, quiet=True)
    if fmt in ("csv", "both"):
        main_path = output_dir / "enam-exams.csv"
        export_to_csv(questions, main_path, quiet=True)

    # Per-edition
    editions: dict[str, list[ExamQuestion]] = {}
    for q in questions:
        editions.setdefault(q.exam_source, []).append(q)

    per_edition_dir = output_dir / "per-edition"
    per_edition_dir.mkdir(exist_ok=True)

    for source, qs in sorted(editions.items()):
        if fmt in ("jsonl", "both"):
            export_to_jsonl(qs, per_edition_dir / f"{source}.jsonl", quiet=True)
        if fmt in ("csv", "both"):
            export_to_csv(qs, per_edition_dir / f"{source}.csv", quiet=True)

    if fmt == "both":
        return output_dir / "enam-exams.jsonl"
    return main_path or output_dir / "enam-exams.jsonl"


def build_enam_dataset(
    pdf_dir: Path,
    output_dir: Path,
    fmt: str = "jsonl",
    force: bool = False,
    max_workers: int = 4,
) -> Path:
    """Constrói o dataset ENAM completo."""
    ui.header("ENAM Dataset Builder")

    # Processar PDFs
    ui.section(f"[1/2] Processando PDFs ({max_workers} workers)")
    questions = _process_pdf_exams(pdf_dir, force, max_workers)

    # Exportar
    ui.section("[2/2] Exportando dataset...")
    output_path = _export_dataset(questions, output_dir, fmt)

    # Resumo
    editions = {q.metadata.get("edition") for q in questions} - {None}
    ui.summary("Dataset ENAM gerado com sucesso!", {
        "Questões": str(len(questions)),
        "Edições": str(len(editions)),
        "Saída": str(output_path),
    })

    return output_path
