"""Exportador de questões para CSV."""

import json
from pathlib import Path

import pandas as pd

from .merger import MergedQuestion


def export_to_csv(questions: list[MergedQuestion], output_path: Path) -> None:
    """Exporta questões para arquivo CSV.

    Args:
        questions: Lista de questões mescladas com gabarito.
        output_path: Caminho do arquivo CSV de saída.
    """
    rows = []
    for question in questions:
        rows.append(
            {
                "numero": question.numero,
                "pergunta": question.enunciado,
                "alternativas": json.dumps(
                    question.alternativas, ensure_ascii=False
                ),
                "resposta_correta": question.resposta_correta,
                "prova_origem": question.prova_origem,
            }
        )

    df = pd.DataFrame(rows)

    # Ordenar por número da questão (se houver dados)
    if not df.empty:
        df = df.sort_values("numero").reset_index(drop=True)

    # Exportar para CSV
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Exportadas {len(rows)} questões para {output_path}")


def questions_to_dataframe(questions: list[MergedQuestion]) -> pd.DataFrame:
    """Converte questões para DataFrame do pandas.

    Args:
        questions: Lista de questões mescladas.

    Returns:
        DataFrame com as questões.
    """
    rows = []
    for question in questions:
        rows.append(
            {
                "numero": question.numero,
                "pergunta": question.enunciado,
                "alternativas": json.dumps(
                    question.alternativas, ensure_ascii=False
                ),
                "resposta_correta": question.resposta_correta,
                "prova_origem": question.prova_origem,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("numero").reset_index(drop=True)
    return df
