"""CLI principal para extração de questões de provas de concursos públicos."""

import argparse
from collections.abc import Callable
from pathlib import Path

from .exporter import export_to_csv, export_to_jsonl
from .extractor import (
    MODEL_NAME,
    TokenUsage,
    extract_all_exam_pages,
    extract_all_gabarito_pages,
)
from .merger import (
    collect_gabarito_answers,
    merge_multi_page_questions,
    merge_questions_with_gabarito,
)
from .models import ExamQuestion
from .pairing import find_exam_pairs
from .pdf_processor import pdf_to_base64_images
from . import ui


def exam_already_processed(exam_name: str, output_dir: Path, fmt: str) -> bool:
    """Verifica se uma prova já foi processada."""
    if fmt == "csv":
        return (output_dir / f"{exam_name}.csv").exists()
    if fmt == "both":
        return (
            (output_dir / f"{exam_name}.jsonl").exists()
            and (output_dir / f"{exam_name}.csv").exists()
        )
    return (output_dir / f"{exam_name}.jsonl").exists()


def _export(questions: list[ExamQuestion], output_dir: Path, exam_name: str, fmt: str) -> Path:
    """Exporta questões no formato solicitado. Retorna o path principal."""
    output_dir.mkdir(parents=True, exist_ok=True)

    path = None

    if fmt in ("jsonl", "both"):
        path = output_dir / f"{exam_name}.jsonl"
        export_to_jsonl(questions, path, quiet=True)
    if fmt in ("csv", "both"):
        path = output_dir / f"{exam_name}.csv"
        export_to_csv(questions, path, quiet=True)

    if fmt == "both":
        return output_dir / f"{exam_name}.jsonl"
    if path is None:
        raise ValueError(f"Formato de exportação inválido: {fmt!r}")
    return path


def process_exam(
    prova_path: Path,
    gabarito_path: Path,
    exam_name: str,
    output_dir: Path,
    fmt: str = "jsonl",
    model_name: str | None = None,
    debug: bool = False,
    max_workers: int = 4,
    quiet: bool = False,
    on_page_done: Callable[[int, int], None] | None = None,
) -> tuple[Path, TokenUsage, int, int]:
    """Processa um par prova/gabarito e gera o output.

    Returns:
        Tupla (caminho, TokenUsage, total_questões, total_páginas_falhadas).
    """
    total_usage = TokenUsage()
    effective_model = model_name or MODEL_NAME
    log = ui.info if not quiet else lambda *a: None

    if not quiet:
        ui.header(f"Processando: {exam_name}")

    # Cache por página
    page_cache_base = output_dir / ".pages" / exam_name
    prova_cache = page_cache_base / "prova"
    gabarito_cache = page_cache_base / "gabarito"

    # 1. Converter PDFs para imagens
    log(f"Convertendo prova para imagens...")
    prova_pages = pdf_to_base64_images(prova_path)
    log(f"  {len(prova_pages)} páginas")

    log(f"Convertendo gabarito para imagens...")
    gabarito_pages = pdf_to_base64_images(gabarito_path)
    log(f"  {len(gabarito_pages)} páginas")

    # 2. Extrair questões da prova
    log(f"Extraindo questões ({max_workers} workers)...")
    page_extractions, exam_usage, prova_failed = extract_all_exam_pages(
        prova_pages, debug=debug, max_workers=max_workers,
        model_name=effective_model, on_page_done=on_page_done,
        cache_dir=prova_cache,
    )
    total_usage.add(exam_usage)

    # 3. Mesclar questões de múltiplas páginas
    questions, num_dupes = merge_multi_page_questions(page_extractions)
    log(f"  {len(questions)} questões encontradas")
    if num_dupes > 0:
        ui.warn(f"{num_dupes} duplicata(s) mesclada(s) (fronteira de página)")

    # 4. Extrair gabarito
    log(f"Extraindo gabarito ({max_workers} workers)...")
    gabarito_extractions, gabarito_usage, gabarito_failed = extract_all_gabarito_pages(
        gabarito_pages, max_workers=max_workers,
        model_name=effective_model, on_page_done=on_page_done,
        cache_dir=gabarito_cache,
    )
    total_usage.add(gabarito_usage)
    gabarito_answers = collect_gabarito_answers(gabarito_extractions)
    log(f"  {len(gabarito_answers)} respostas encontradas")

    # Reportar falhas (sempre, mesmo em quiet)
    all_failed = prova_failed + [f"gab-{p}" for p in gabarito_failed]
    if all_failed:
        ui.warn(f"{exam_name}: páginas falharam: {all_failed}")

    # 5. Combinar questões com gabarito
    merged_questions = merge_questions_with_gabarito(
        questions, gabarito_answers, exam_name
    )

    nullified = [q for q in merged_questions if q.nullified]
    if nullified and not quiet:
        ui.warn(f"{len(nullified)} questão(ões) anulada(s)")

    # 6. Exportar
    output_path = _export(merged_questions, output_dir, exam_name, fmt)

    return output_path, total_usage, len(merged_questions), len(prova_failed) + len(gabarito_failed)


def process_single(
    prova_path: Path,
    gabarito_path: Path,
    output_dir: Path,
    fmt: str = "jsonl",
    model_name: str | None = None,
    debug: bool = False,
    max_workers: int = 4,
) -> None:
    """Processa um único par de PDFs."""
    exam_name = prova_path.stem
    output_path, usage, num_questions, num_failed = process_exam(
        prova_path, gabarito_path, exam_name, output_dir, fmt, model_name, debug,
        max_workers=max_workers,
    )
    items = {
        "Questões": str(num_questions),
        "Saída": str(output_path),
        "Tokens": str(usage),
    }
    if num_failed > 0:
        items["Falhas"] = f"{num_failed} página(s)"
    ui.summary("Concluído!", items)


def cmd_extract(args: argparse.Namespace) -> None:
    """Subcomando extract: pipeline PDF→dados."""
    exams_dir = Path(args.exams_dir)
    output_dir = Path(args.output_dir)

    # Modo single
    if args.single:
        if not args.gabarito:
            ui.error("--gabarito é obrigatório com --single")
            return
        process_single(
            Path(args.single), Path(args.gabarito), output_dir,
            args.format, args.model, args.debug, args.workers,
        )
        return

    ui.header("exam2bench - Extrator de Questões de Concursos")

    if args.debug:
        ui.warn("MODO DEBUG ATIVADO")

    if not exams_dir.exists():
        ui.error(f"Diretório '{exams_dir}' não encontrado.")
        return

    pairs = find_exam_pairs(exams_dir, args.prova_suffix, args.gabarito_suffix)

    if not pairs:
        ui.error(f"Nenhum par prova/gabarito encontrado em '{exams_dir}'.")
        return

    ui.info(f"Encontrados {len(pairs)} par(es):")
    for _, _, name in pairs:
        ui.info(f"  - {name}")

    results = []
    skipped = []
    grand_total_usage = TokenUsage()

    for prova, gabarito, name in pairs:
        if not args.force and exam_already_processed(name, output_dir, args.format):
            ui.info(f"Pulando '{name}' (já processado)")
            skipped.append(name)
            continue

        try:
            output_path, usage, num_q, _ = process_exam(
                prova, gabarito, name, output_dir,
                args.format, args.model, args.debug, args.workers,
            )
            results.append((name, output_path, None, usage))
            grand_total_usage.add(usage)
        except Exception as e:
            ui.error(f"Erro ao processar {name}: {e}")
            results.append((name, None, str(e), TokenUsage()))

    # Resumo
    successful = [(name, path) for name, path, err, _ in results if path]
    failed = [(name, err) for name, _, err, _ in results if err]

    items = {}
    if successful:
        items["Processados"] = ", ".join(n for n, _ in successful)
    if skipped:
        items["Pulados"] = ", ".join(skipped)
    if failed:
        items["Falharam"] = ", ".join(f"{n}: {e}" for n, e in failed)
    items["Tokens"] = str(grand_total_usage)

    ui.summary("RESUMO", items)


def cmd_oab_build(args: argparse.Namespace) -> None:
    """Subcomando oab build: construir dataset OAB completo."""
    from products.oab.pipeline import build_oab_dataset

    build_oab_dataset(
        raw_dir=Path(args.raw_dir),
        pdf_dir=Path(args.pdf_dir),
        output_dir=Path(args.output_dir),
        fmt=args.format,
        force=args.force,
        max_workers=args.workers,
    )


def cmd_enam_build(args: argparse.Namespace) -> None:
    """Subcomando enam build: construir dataset ENAM completo."""
    from products.enam.pipeline import build_enam_dataset

    build_enam_dataset(
        pdf_dir=Path(args.pdf_dir),
        output_dir=Path(args.output_dir),
        fmt=args.format,
        force=args.force,
        max_workers=args.workers,
    )


def cmd_build_all(args: argparse.Namespace) -> None:
    """Subcomando build-all: construir ENAM e OAB (ENAM primeiro)."""
    from products.enam.pipeline import build_enam_dataset
    from products.oab.pipeline import build_oab_dataset

    build_enam_dataset(
        pdf_dir=Path(args.enam_pdf_dir),
        output_dir=Path(args.enam_output_dir),
        fmt=args.format,
        force=args.force,
        max_workers=args.workers,
    )

    build_oab_dataset(
        raw_dir=Path(args.oab_raw_dir),
        pdf_dir=Path(args.oab_pdf_dir),
        output_dir=Path(args.oab_output_dir),
        fmt=args.format,
        force=args.force,
        max_workers=args.workers,
    )


def main():
    """Função principal do CLI."""
    parser = argparse.ArgumentParser(
        prog="exam2bench",
        description="exam2bench - Extrator de Questões de Concursos para Benchmarks de LLMs",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcomandos disponíveis")

    # --- Subcomando: extract ---
    extract_parser = subparsers.add_parser(
        "extract", help="Pipeline PDF→dados estruturados"
    )
    extract_parser.add_argument(
        "--exams-dir", default="exams", help="Diretório com PDFs (default: exams)"
    )
    extract_parser.add_argument(
        "--output-dir", default="output", help="Diretório de saída (default: output)"
    )
    extract_parser.add_argument(
        "--format", choices=["jsonl", "csv", "both"], default="jsonl",
        help="Formato de saída (default: jsonl)",
    )
    extract_parser.add_argument(
        "--prova-suffix", default="-prova",
        help="Sufixo do arquivo de prova (default: -prova)",
    )
    extract_parser.add_argument(
        "--gabarito-suffix", default="-gabarito",
        help="Sufixo do arquivo de gabarito (default: -gabarito)",
    )
    extract_parser.add_argument(
        "--model", default=None,
        help="Modelo Gemini a utilizar (default: gemini-3-pro-preview)",
    )
    extract_parser.add_argument(
        "--workers", type=int, default=4,
        help="Workers concorrentes para chamadas à API (default: 4)",
    )
    extract_parser.add_argument("--force", action="store_true", help="Reprocessar")
    extract_parser.add_argument("--debug", action="store_true", help="Modo verbose")
    extract_parser.add_argument(
        "--single", metavar="PATH", help="Processar um PDF único de prova"
    )
    extract_parser.add_argument(
        "--gabarito", metavar="PATH", help="Gabarito para --single"
    )
    extract_parser.set_defaults(func=cmd_extract)

    # --- Subcomando: oab build ---
    oab_parser = subparsers.add_parser("oab", help="Comandos do produto OAB")
    oab_subparsers = oab_parser.add_subparsers(dest="oab_command")

    build_parser = oab_subparsers.add_parser(
        "build", help="Construir dataset OAB completo"
    )
    build_parser.add_argument(
        "--raw-dir", default="products/oab/raw",
        help="Diretório com arquivos .txt raw (default: products/oab/raw)",
    )
    build_parser.add_argument(
        "--pdf-dir", default="products/oab/exams",
        help="Diretório com PDFs de edições 26+ (default: products/oab/exams)",
    )
    build_parser.add_argument(
        "--output-dir", default="products/oab/output",
        help="Diretório de saída (default: products/oab/output)",
    )
    build_parser.add_argument(
        "--format", choices=["jsonl", "csv", "both"], default="jsonl",
        help="Formato de saída (default: jsonl)",
    )
    build_parser.add_argument(
        "--workers", type=int, default=4,
        help="Workers concorrentes para chamadas à API (default: 4)",
    )
    build_parser.add_argument("--force", action="store_true", help="Reprocessar")
    build_parser.set_defaults(func=cmd_oab_build)

    # --- Subcomando: enam build ---
    enam_parser = subparsers.add_parser("enam", help="Comandos do produto ENAM")
    enam_subparsers = enam_parser.add_subparsers(dest="enam_command")

    enam_build_parser = enam_subparsers.add_parser(
        "build", help="Construir dataset ENAM completo"
    )
    enam_build_parser.add_argument(
        "--pdf-dir", default="products/enam/exams",
        help="Diretório com PDFs (default: products/enam/exams)",
    )
    enam_build_parser.add_argument(
        "--output-dir", default="products/enam/output",
        help="Diretório de saída (default: products/enam/output)",
    )
    enam_build_parser.add_argument(
        "--format", choices=["jsonl", "csv", "both"], default="jsonl",
        help="Formato de saída (default: jsonl)",
    )
    enam_build_parser.add_argument(
        "--workers", type=int, default=4,
        help="Workers concorrentes para chamadas à API (default: 4)",
    )
    enam_build_parser.add_argument("--force", action="store_true", help="Reprocessar")
    enam_build_parser.set_defaults(func=cmd_enam_build)

    # --- Subcomando: build-all ---
    build_all_parser = subparsers.add_parser(
        "build-all", help="Construir datasets ENAM e OAB (ENAM primeiro)",
    )
    build_all_parser.add_argument(
        "--enam-pdf-dir", default="products/enam/exams",
        help="Diretório com PDFs ENAM (default: products/enam/exams)",
    )
    build_all_parser.add_argument(
        "--enam-output-dir", default="products/enam/output",
        help="Diretório de saída ENAM (default: products/enam/output)",
    )
    build_all_parser.add_argument(
        "--oab-raw-dir", default="products/oab/raw",
        help="Diretório com .txt raw OAB (default: products/oab/raw)",
    )
    build_all_parser.add_argument(
        "--oab-pdf-dir", default="products/oab/exams",
        help="Diretório com PDFs OAB (default: products/oab/exams)",
    )
    build_all_parser.add_argument(
        "--oab-output-dir", default="products/oab/output",
        help="Diretório de saída OAB (default: products/oab/output)",
    )
    build_all_parser.add_argument(
        "--format", choices=["jsonl", "csv", "both"], default="jsonl",
        help="Formato de saída (default: jsonl)",
    )
    build_all_parser.add_argument(
        "--workers", type=int, default=4,
        help="Workers concorrentes para chamadas à API (default: 4)",
    )
    build_all_parser.add_argument("--force", action="store_true", help="Reprocessar")
    build_all_parser.set_defaults(func=cmd_build_all)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "oab" and not getattr(args, "oab_command", None):
        oab_parser.print_help()
        return

    if args.command == "enam" and not getattr(args, "enam_command", None):
        enam_parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
