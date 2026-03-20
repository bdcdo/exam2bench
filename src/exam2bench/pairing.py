"""Módulo para pareamento de PDFs de prova e gabarito."""

from pathlib import Path


def find_exam_pairs(
    exams_dir: Path,
    prova_suffix: str = "-prova",
    gabarito_suffix: str = "-gabarito",
) -> list[tuple[Path, Path, str]]:
    """Encontra pares de prova/gabarito no diretório.

    Args:
        exams_dir: Diretório contendo os PDFs.
        prova_suffix: Sufixo do arquivo de prova (antes de .pdf).
        gabarito_suffix: Sufixo do arquivo de gabarito (antes de .pdf).

    Returns:
        Lista de tuplas (caminho_prova, caminho_gabarito, nome_base).
    """
    pairs = []
    provas = list(exams_dir.glob(f"*{prova_suffix}.pdf"))

    for prova in sorted(provas):
        base_name = prova.stem.removesuffix(prova_suffix)
        gabarito = exams_dir / f"{base_name}{gabarito_suffix}.pdf"

        if gabarito.exists():
            pairs.append((prova, gabarito, base_name))
        else:
            print(f"Aviso: Gabarito não encontrado para {prova.name}")

    return pairs
