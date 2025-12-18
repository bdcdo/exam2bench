"""CLI principal para extração de questões de provas de concursos públicos."""

import argparse
from pathlib import Path

from .exporter import export_to_csv
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
from .pdf_processor import pdf_to_base64_images

# Diretórios padrão
EXAMS_DIR = Path("exams")
OUTPUT_DIR = Path("output")


def find_exam_pairs(exams_dir: Path) -> list[tuple[Path, Path, str]]:
    """Encontra pares de prova/gabarito no diretório.

    Convenção de nomes:
    - Prova: *-prova.pdf
    - Gabarito: *-gabarito.pdf

    Args:
        exams_dir: Diretório contendo os PDFs.

    Returns:
        Lista de tuplas (caminho_prova, caminho_gabarito, nome_base).
    """
    pairs = []
    provas = list(exams_dir.glob("*-prova.pdf"))

    for prova in provas:
        # Extrai nome base: vunesp-2025-tj-sp-juiz-substituto-prova.pdf
        # -> vunesp-2025-tj-sp-juiz-substituto
        base_name = prova.stem.replace("-prova", "")
        gabarito = exams_dir / f"{base_name}-gabarito.pdf"

        if gabarito.exists():
            pairs.append((prova, gabarito, base_name))
        else:
            print(f"Aviso: Gabarito não encontrado para {prova.name}")

    return pairs


def process_exam(
    prova_path: Path, gabarito_path: Path, exam_name: str, debug: bool = False
) -> tuple[Path, TokenUsage]:
    """Processa um par prova/gabarito e gera o CSV.

    Args:
        prova_path: Caminho do PDF da prova.
        gabarito_path: Caminho do PDF do gabarito.
        exam_name: Nome identificador do exame.
        debug: Se True, imprime a resposta raw do modelo.

    Returns:
        Tupla (caminho do CSV gerado, TokenUsage total).
    """
    print(f"\n{'='*60}")
    print(f"Processando: {exam_name}")
    print(f"{'='*60}")

    total_usage = TokenUsage()

    # Criar modelo
    print("\nInicializando modelo Gemini...")
    model = create_model()

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
    questions_without_answer = [
        q for q in merged_questions if q.resposta_correta is None
    ]
    if questions_without_answer:
        print(
            f"  Aviso: {len(questions_without_answer)} questão(ões) sem resposta no gabarito"
        )

    # 6. Exportar para CSV
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"{exam_name}.csv"
    export_to_csv(merged_questions, output_path)

    return output_path, total_usage


def main():
    """Função principal do CLI."""
    parser = argparse.ArgumentParser(
        description="exam2bench - Extrator de Questões de Concursos"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativa modo debug: imprime resposta raw do modelo Gemini",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("exam2bench - Extrator de Questões de Concursos")
    print("=" * 60)

    if args.debug:
        print("\n[MODO DEBUG ATIVADO]")

    # Verificar diretório de exames
    if not EXAMS_DIR.exists():
        print(f"\nErro: Diretório '{EXAMS_DIR}' não encontrado.")
        print("Crie o diretório e adicione os PDFs seguindo a convenção:")
        print("  - Prova: *-prova.pdf")
        print("  - Gabarito: *-gabarito.pdf")
        return

    # Encontrar pares de prova/gabarito
    pairs = find_exam_pairs(EXAMS_DIR)

    if not pairs:
        print(f"\nNenhum par prova/gabarito encontrado em '{EXAMS_DIR}'.")
        print("Certifique-se de que os PDFs seguem a convenção de nomes:")
        print("  - Prova: nome-prova.pdf")
        print("  - Gabarito: nome-gabarito.pdf")
        return

    print(f"\nEncontrados {len(pairs)} par(es) de prova/gabarito:")
    for prova, gabarito, name in pairs:
        print(f"  - {name}")

    # Processar cada par
    results = []
    grand_total_usage = TokenUsage()

    for prova, gabarito, name in pairs:
        try:
            output_path, usage = process_exam(prova, gabarito, name, debug=args.debug)
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

    if failed:
        print(f"\nFalharam ({len(failed)}):")
        for name, err in failed:
            print(f"  ✗ {name}: {err}")

    # Mostrar uso de tokens
    print(f"\nTokens utilizados:")
    print(f"  {grand_total_usage}")


if __name__ == "__main__":
    main()
