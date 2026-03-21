"""Módulo para merge de questões extraídas e gabarito."""

from .models import (
    ExamAlternative,
    ExamQuestion,
    GabaritoExtraction,
    PageExtraction,
    Question,
)


def merge_multi_page_questions(
    extractions: list[tuple[int, PageExtraction]]
) -> tuple[list[Question], int]:
    """Coleta e mescla questões de todas as páginas.

    Questões na fronteira entre páginas são extraídas parcialmente em cada uma.
    Quando detectada duplicata por número, concatena os enunciados e mantém
    as alternativas da versão mais completa.

    Args:
        extractions: Lista de tuplas (número_página, PageExtraction).

    Returns:
        Tupla (questões mescladas, número de duplicatas mescladas).
    """
    sorted_extractions = sorted(extractions, key=lambda x: x[0])

    seen: dict[int, Question] = {}
    total = 0
    for _, extraction in sorted_extractions:
        for q in extraction.questoes:
            total += 1
            if q.numero not in seen:
                seen[q.numero] = q
            else:
                existing = seen[q.numero]
                seen[q.numero] = Question(
                    numero=q.numero,
                    enunciado=existing.enunciado + " " + q.enunciado,
                    alternativas=q.alternativas if len(q.alternativas) >= len(existing.alternativas) else existing.alternativas,
                )

    merged = sorted(seen.values(), key=lambda q: q.numero)
    return merged, total - len(merged)


def collect_gabarito_answers(
    extractions: list[GabaritoExtraction],
) -> dict[int, str]:
    """Coleta todas as respostas do gabarito em um dicionário.

    Args:
        extractions: Lista de GabaritoExtraction de todas as páginas.

    Returns:
        Dicionário {número_questão: letra_resposta}.
    """
    answers: dict[int, str] = {}
    for extraction in extractions:
        for answer in extraction.respostas:
            answers[answer.numero] = answer.resposta
    return answers


def merge_questions_with_gabarito(
    questions: list[Question],
    gabarito_answers: dict[int, str],
    exam_source: str,
    nullified_questions: set[int] | None = None,
    metadata: dict | None = None,
) -> list[ExamQuestion]:
    """Combina questões com suas respostas corretas.

    Args:
        questions: Lista de questões extraídas.
        gabarito_answers: Dicionário {número_questão: letra_resposta}.
        exam_source: Nome/identificador da prova.
        nullified_questions: Conjunto de números de questões anuladas.
        metadata: Metadados extras para todas as questões.

    Returns:
        Lista de ExamQuestion com todas as informações.
    """
    nullified = nullified_questions or set()
    base_metadata = metadata or {}
    merged = []

    for question in questions:
        is_nullified = question.numero in nullified
        correct = None if is_nullified else gabarito_answers.get(question.numero)

        # Se não tem resposta no gabarito e não está explicitamente anulada,
        # marca como anulada (comportamento legado)
        if correct is None and not is_nullified:
            is_nullified = True

        merged.append(
            ExamQuestion(
                id=f"{exam_source}-{question.numero:03d}",
                exam_source=exam_source,
                question_number=question.numero,
                statement=question.enunciado,
                alternatives=[
                    ExamAlternative(letter=alt.letra, text=alt.texto)
                    for alt in question.alternativas
                ],
                correct_answer=correct,
                nullified=is_nullified,
                metadata=dict(base_metadata),
            )
        )
    return merged
