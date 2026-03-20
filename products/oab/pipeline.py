"""Orquestrador para construção do dataset OAB completo."""

from pathlib import Path

from exam2bench.exporter import export_to_csv, export_to_jsonl
from exam2bench.models import ExamQuestion

from .area_map import get_area_for_question
from .converter import parse_raw_oab_file


def _convert_legacy_exams(raw_dir: Path) -> list[ExamQuestion]:
    """Converte edições 1-25 dos arquivos .txt raw.

    Args:
        raw_dir: Diretório com arquivos .txt.

    Returns:
        Lista de ExamQuestion de todas as edições legado.
    """
    all_questions = []
    txt_files = sorted(raw_dir.glob("*.txt"))

    if not txt_files:
        print(f"  Aviso: Nenhum arquivo .txt encontrado em {raw_dir}")
        return all_questions

    for txt_file in txt_files:
        print(f"  Convertendo {txt_file.name}...")
        questions = parse_raw_oab_file(txt_file)
        print(f"    → {len(questions)} questões")
        all_questions.extend(questions)

    return all_questions


def _process_pdf_exams(pdf_dir: Path, force: bool = False) -> list[ExamQuestion]:
    """Processa edições 26+ dos PDFs via pipeline core.

    Args:
        pdf_dir: Diretório com PDFs de provas e gabaritos.
        force: Reprocessar mesmo se já existe.

    Returns:
        Lista de ExamQuestion das edições processadas via PDF.
    """
    from exam2bench.cli import process_exam
    from exam2bench.pairing import find_exam_pairs

    if not pdf_dir.exists():
        return []

    # PDFs OAB usam sufixos diferentes: prova sem sufixo, gabarito com "-as"
    pairs = find_exam_pairs(pdf_dir, prova_suffix="-prova", gabarito_suffix="-gabarito")

    if not pairs:
        print(f"  Nenhum par de PDF encontrado em {pdf_dir}")
        return []

    all_questions = []
    for prova_path, gabarito_path, exam_name in pairs:
        print(f"  Processando PDF: {exam_name}...")
        # Extrair edição do nome (ex: "oab-26" → 26)
        try:
            output_dir = pdf_dir / ".cache"
            cache_file = output_dir / f"{exam_name}.jsonl"

            if cache_file.exists() and not force:
                print(f"    → Usando cache")
                with open(cache_file, encoding="utf-8") as f:
                    questions = [ExamQuestion.model_validate_json(line) for line in f if line.strip()]
                all_questions.extend(questions)
                continue

            output_path, _ = process_exam(
                prova_path, gabarito_path, exam_name,
                output_dir, fmt="jsonl",
            )

            # Ler de volta
            with open(output_path, encoding="utf-8") as f:
                questions = [ExamQuestion.model_validate_json(line) for line in f if line.strip()]

            # Aplicar metadados de área se disponível
            for q in questions:
                edition = q.metadata.get("edition")
                if edition:
                    area = get_area_for_question(edition, q.question_number)
                    if area:
                        q.metadata["area"] = area

            all_questions.extend(questions)
        except Exception as e:
            print(f"    → Erro: {e}")

    return all_questions


def _export_dataset(
    questions: list[ExamQuestion], output_dir: Path, fmt: str
) -> Path:
    """Exporta o dataset completo e arquivos individuais por edição."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ordenar por edição + número
    questions.sort(
        key=lambda q: (q.metadata.get("edition", 0), q.question_number)
    )

    # Exportar dataset completo
    if fmt in ("jsonl", "both"):
        main_path = output_dir / "oab-exams.jsonl"
        export_to_jsonl(questions, main_path)
    if fmt in ("csv", "both"):
        main_path = output_dir / "oab-exams.csv"
        export_to_csv(questions, main_path)

    # Exportar por edição
    editions: dict[str, list[ExamQuestion]] = {}
    for q in questions:
        editions.setdefault(q.exam_source, []).append(q)

    per_edition_dir = output_dir / "per-edition"
    per_edition_dir.mkdir(exist_ok=True)

    for source, qs in sorted(editions.items()):
        if fmt in ("jsonl", "both"):
            export_to_jsonl(qs, per_edition_dir / f"{source}.jsonl")
        if fmt in ("csv", "both"):
            export_to_csv(qs, per_edition_dir / f"{source}.csv")

    if fmt == "both":
        return output_dir / "oab-exams.jsonl"
    return output_dir / f"oab-exams.{'jsonl' if fmt == 'jsonl' else 'csv'}"


def build_oab_dataset(
    raw_dir: Path,
    pdf_dir: Path,
    output_dir: Path,
    fmt: str = "jsonl",
    force: bool = False,
) -> Path:
    """Constrói o dataset OAB completo.

    Args:
        raw_dir: Diretório com arquivos .txt raw (edições 1-25).
        pdf_dir: Diretório com PDFs (edições 26+).
        output_dir: Diretório de saída.
        fmt: Formato de saída (jsonl, csv, both).
        force: Reprocessar.

    Returns:
        Caminho do arquivo principal gerado.
    """
    print("=" * 60)
    print("OAB Dataset Builder")
    print("=" * 60)

    all_questions: list[ExamQuestion] = []

    # 1. Converter edições legado (raw .txt)
    print(f"\n[1/3] Convertendo edições legado de {raw_dir}...")
    legacy = _convert_legacy_exams(raw_dir)
    all_questions.extend(legacy)
    print(f"  Total legado: {len(legacy)} questões")

    # 2. Processar PDFs (edições 26+)
    print(f"\n[2/3] Processando PDFs de {pdf_dir}...")
    pdf_questions = _process_pdf_exams(pdf_dir, force)
    all_questions.extend(pdf_questions)
    print(f"  Total PDF: {len(pdf_questions)} questões")

    # 3. Exportar
    print(f"\n[3/3] Exportando dataset...")
    output_path = _export_dataset(all_questions, output_dir, fmt)

    # Resumo
    editions = {q.metadata.get("edition") for q in all_questions} - {None}
    print(f"\n{'='*60}")
    print(f"Dataset OAB gerado com sucesso!")
    print(f"  Questões: {len(all_questions)}")
    print(f"  Edições: {len(editions)} ({min(editions or {0})} a {max(editions or {0})})")
    print(f"  Saída: {output_path}")
    print(f"{'='*60}")

    return output_path
