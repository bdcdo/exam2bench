"""Módulo para merge de questões extraídas e gabarito."""

from dataclasses import dataclass

from .models import GabaritoExtraction, PageExtraction, Question


@dataclass
class MergedQuestion:
    """Questão final com todas as informações."""

    numero: int
    enunciado: str
    alternativas: list[dict]  # [{"letra": "A", "texto": "..."}]
    resposta_correta: str | None
    prova_origem: str


def merge_multi_page_questions(
    extractions: list[tuple[int, PageExtraction]]
) -> list[Question]:
    """Coleta todas as questões de todas as páginas.

    Args:
        extractions: Lista de tuplas (número_página, PageExtraction).

    Returns:
        Lista de questões ordenadas por página.
    """
    sorted_extractions = sorted(extractions, key=lambda x: x[0])

    all_questions: list[Question] = []
    for _, extraction in sorted_extractions:
        all_questions.extend(extraction.questoes)

    return all_questions


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
    prova_name: str,
) -> list[MergedQuestion]:
    """Combina questões com suas respostas corretas.

    Args:
        questions: Lista de questões extraídas.
        gabarito_answers: Dicionário {número_questão: letra_resposta}.
        prova_name: Nome/identificador da prova.

    Returns:
        Lista de MergedQuestion com todas as informações.
    """
    merged = []
    for question in questions:
        merged.append(
            MergedQuestion(
                numero=question.numero,
                enunciado=question.enunciado,
                alternativas=[
                    {"letra": alt.letra, "texto": alt.texto}
                    for alt in question.alternativas
                ],
                resposta_correta=gabarito_answers.get(question.numero),
                prova_origem=prova_name,
            )
        )
    return merged
