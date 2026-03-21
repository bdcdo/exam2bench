"""Exportador de questões para JSONL e CSV."""

import json
from pathlib import Path

import pandas as pd

from .models import ExamQuestion


def export_to_jsonl(
    questions: list[ExamQuestion], output_path: Path, quiet: bool = False,
) -> None:
    """Exporta questões para arquivo JSONL (um JSON por linha).

    Args:
        questions: Lista de ExamQuestion.
        output_path: Caminho do arquivo JSONL de saída.
        quiet: Se True, suprime output.
    """
    sorted_questions = sorted(questions, key=lambda q: q.question_number)

    with open(output_path, "w", encoding="utf-8") as f:
        for question in sorted_questions:
            f.write(question.model_dump_json() + "\n")


def export_to_csv(
    questions: list[ExamQuestion], output_path: Path, quiet: bool = False,
) -> None:
    """Exporta questões para arquivo CSV.

    Args:
        questions: Lista de ExamQuestion.
        output_path: Caminho do arquivo CSV de saída.
        quiet: Se True, suprime output.
    """
    df = questions_to_dataframe(questions)
    df.to_csv(output_path, index=False, encoding="utf-8")


def questions_to_dataframe(questions: list[ExamQuestion]) -> pd.DataFrame:
    """Converte questões para DataFrame do pandas.

    Args:
        questions: Lista de ExamQuestion.

    Returns:
        DataFrame com as questões.
    """
    rows = []
    for q in questions:
        rows.append(
            {
                "id": q.id,
                "exam_source": q.exam_source,
                "question_number": q.question_number,
                "statement": q.statement,
                "alternatives": json.dumps(
                    [a.model_dump() for a in q.alternatives], ensure_ascii=False
                ),
                "correct_answer": q.correct_answer,
                "nullified": q.nullified,
                "metadata": json.dumps(q.metadata, ensure_ascii=False),
            }
        )

    columns = [
        "id", "exam_source", "question_number", "statement",
        "alternatives", "correct_answer", "nullified", "metadata",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if not df.empty:
        df = df.sort_values("question_number").reset_index(drop=True)
    return df
