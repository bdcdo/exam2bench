"""CLI principal para extração de questões de provas de concursos públicos."""

import argparse
from pathlib import Path

from .exporter import export_to_csv, export_to_jsonl
from .extractor import (
    TokenUsage,
    create_model,
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
        export_to_jsonl(questions, path)
    if fmt in ("csv", "both"):
        path = output_dir / f"{exam_name}.csv"
        export_to_csv(questions, path)

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
) -> tuple[Path, TokenUsage]:
    """Processa um par prova/gabarito e gera o output.

    Returns:
        Tupla (caminho do arquivo gerado, TokenUsage total).
    """
    print(f"\n{'='*60}")
    print(f"Processando: {exam_name}")
    print(f"{'='*60}")

    total_usage = TokenUsage()

    # Criar modelo
    print("\nInicializando modelo Gemini...")
    model = create_model(model_name) if model_name else create_model()

    # 1. Converter PDFs para imagens
    print(f"\nConvertendo prova para imagens...")
    prova_pages = pdf_to_base64_images(prova_path)
    print(f"  → {len(prova_pages)} páginas")

    print(f"\nConvertendo gabarito para imagens...")
    gabarito_pages = pdf_to_base64_images(gabarito_path)
    print(f"  → {len(gabarito_pages)} páginas")

    # 2. Extrair questões da prova
    print(f"\nExtraindo questões da prova...")
    page_extractions, exam_usage = extract_all_exam_pages(model, prova_pages, debug=debug)
    total_usage.add(exam_usage)

    # 3. Mesclar questões de múltiplas páginas
    print(f"\nMesclando questões...")
    questions = merge_multi_page_questions(page_extractions)
    print(f"  → {len(questions)} questões encontradas")

    # 4. Extrair gabarito
    print(f"\nExtraindo gabarito...")
    gabarito_extractions, gabarito_usage = extract_all_gabarito_pages(model, gabarito_pages)
    total_usage.add(gabarito_usage)
    gabarito_answers = collect_gabarito_answers(gabarito_extractions)
    print(f"  → {len(gabarito_answers)} respostas encontradas")

    # 5. Combinar questões com gabarito
    print(f"\nCombinando questões com gabarito...")
    merged_questions = merge_questions_with_gabarito(
        questions, gabarito_answers, exam_name
    )

    # Verificar questões sem resposta
    nullified = [q for q in merged_questions if q.nullified]
    if nullified:
        print(f"  Aviso: {len(nullified)} questão(ões) anulada(s)")

    # 6. Exportar
    output_path = _export(merged_questions, output_dir, exam_name, fmt)

    return output_path, total_usage


def process_single(
    prova_path: Path,
    gabarito_path: Path,
    output_dir: Path,
    fmt: str = "jsonl",
    model_name: str | None = None,
    debug: bool = False,
) -> None:
    """Processa um único par de PDFs."""
    exam_name = prova_path.stem
    output_path, usage = process_exam(
        prova_path, gabarito_path, exam_name, output_dir, fmt, model_name, debug
    )
    print(f"\nTokens utilizados:\n  {usage}")


def cmd_extract(args: argparse.Namespace) -> None:
    """Subcomando extract: pipeline PDF→dados."""
    exams_dir = Path(args.exams_dir)
    output_dir = Path(args.output_dir)

    # Modo single
    if args.single:
        if not args.gabarito:
            print("Erro: --gabarito é obrigatório com --single")
            return
        process_single(
            Path(args.single), Path(args.gabarito), output_dir,
            args.format, args.model, args.debug,
        )
        return

    print("=" * 60)
    print("exam2bench - Extrator de Questões de Concursos")
    print("=" * 60)

    if args.debug:
        print("\n[MODO DEBUG ATIVADO]")

    if not exams_dir.exists():
        print(f"\nErro: Diretório '{exams_dir}' não encontrado.")
        return

    # Encontrar pares de prova/gabarito
    pairs = find_exam_pairs(exams_dir, args.prova_suffix, args.gabarito_suffix)

    if not pairs:
        print(f"\nNenhum par prova/gabarito encontrado em '{exams_dir}'.")
        return

    print(f"\nEncontrados {len(pairs)} par(es) de prova/gabarito:")
    for _, _, name in pairs:
        print(f"  - {name}")

    # Processar cada par
    results = []
    skipped = []
    grand_total_usage = TokenUsage()

    for prova, gabarito, name in pairs:
        if not args.force and exam_already_processed(name, output_dir, args.format):
            print(f"\n→ Pulando '{name}' (já existe em {output_dir}/)")
            skipped.append(name)
            continue

        try:
            output_path, usage = process_exam(
                prova, gabarito, name, output_dir,
                args.format, args.model, args.debug,
            )
            results.append((name, output_path, None, usage))
            grand_total_usage.add(usage)
        except Exception as e:
            print(f"\nErro ao processar {name}: {e}")
            results.append((name, None, str(e), TokenUsage()))

    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)

    successful = [(name, path, usage) for name, path, err, usage in results if path]
    failed = [(name, err) for name, path, err, usage in results if err]

    if successful:
        print(f"\nProcessados com sucesso ({len(successful)}):")
        for name, path, usage in successful:
            print(f"  ✓ {name} → {path}")

    if skipped:
        print(f"\nPulados - já existem ({len(skipped)}):")
        for name in skipped:
            print(f"  ⊘ {name}")

    if failed:
        print(f"\nFalharam ({len(failed)}):")
        for name, err in failed:
            print(f"  ✗ {name}: {err}")

    print(f"\nTokens utilizados:\n  {grand_total_usage}")


def cmd_oab_build(args: argparse.Namespace) -> None:
    """Subcomando oab build: construir dataset OAB completo."""
    from products.oab.pipeline import build_oab_dataset

    build_oab_dataset(
        raw_dir=Path(args.raw_dir),
        pdf_dir=Path(args.pdf_dir),
        output_dir=Path(args.output_dir),
        fmt=args.format,
        force=args.force,
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
    build_parser.add_argument("--force", action="store_true", help="Reprocessar")
    build_parser.set_defaults(func=cmd_oab_build)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "oab" and not getattr(args, "oab_command", None):
        oab_parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
