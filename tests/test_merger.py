"""Testes para o módulo de merge de questões e gabarito."""

import pytest

from exam2bench.merger import (
    MergedQuestion,
    collect_gabarito_answers,
    merge_multi_page_questions,
    merge_questions_with_gabarito,
)
from exam2bench.models import (
    Alternative,
    GabaritoAnswer,
    GabaritoExtraction,
    PageExtraction,
    Question,
)


class TestMergeMultiPageQuestions:
    """Testes para coleta de questões de múltiplas páginas."""

    def test_single_page_questions(self):
        """Questões de uma página devem ser retornadas intactas."""
        q1 = Question(
            numero=1,
            enunciado="Qual é a capital do Brasil?",
            alternativas=[
                Alternative(letra="A", texto="Rio de Janeiro"),
                Alternative(letra="B", texto="Brasília"),
            ],
        )
        q2 = Question(
            numero=2,
            enunciado="Qual é 2 + 2?",
            alternativas=[
                Alternative(letra="A", texto="3"),
                Alternative(letra="B", texto="4"),
            ],
        )

        extractions = [(1, PageExtraction(questoes=[q1, q2]))]

        result = merge_multi_page_questions(extractions)

        assert len(result) == 2
        assert result[0].numero == 1
        assert result[1].numero == 2

    def test_multiple_pages_questions(self):
        """Questões de múltiplas páginas devem ser concatenadas."""
        q1 = Question(
            numero=1,
            enunciado="Pergunta 1",
            alternativas=[Alternative(letra="A", texto="Resposta")],
        )
        q2 = Question(
            numero=2,
            enunciado="Pergunta 2",
            alternativas=[Alternative(letra="A", texto="Resposta")],
        )

        extractions = [
            (1, PageExtraction(questoes=[q1])),
            (2, PageExtraction(questoes=[q2])),
        ]

        result = merge_multi_page_questions(extractions)

        assert len(result) == 2
        assert result[0].numero == 1
        assert result[1].numero == 2

    def test_pages_without_questions_are_skipped(self):
        """Páginas sem questões devem ser ignoradas."""
        q1 = Question(
            numero=1,
            enunciado="Pergunta 1",
            alternativas=[Alternative(letra="A", texto="Resposta")],
        )

        extractions = [
            (1, PageExtraction(questoes=[])),  # Capa
            (2, PageExtraction(questoes=[q1])),
            (3, PageExtraction(questoes=[])),  # Página em branco
        ]

        result = merge_multi_page_questions(extractions)

        assert len(result) == 1
        assert result[0].numero == 1

    def test_pages_out_of_order_are_sorted(self):
        """Páginas fora de ordem devem ser ordenadas antes do merge."""
        q1 = Question(
            numero=1,
            enunciado="Primeira questão",
            alternativas=[Alternative(letra="A", texto="Resp")],
        )
        q2 = Question(
            numero=2,
            enunciado="Segunda questão",
            alternativas=[Alternative(letra="A", texto="Resp")],
        )

        # Páginas em ordem invertida
        extractions = [
            (2, PageExtraction(questoes=[q2])),
            (1, PageExtraction(questoes=[q1])),
        ]

        result = merge_multi_page_questions(extractions)

        assert len(result) == 2
        assert result[0].numero == 1
        assert result[1].numero == 2


class TestCollectGabaritoAnswers:
    """Testes para coleta de respostas do gabarito."""

    def test_single_page_gabarito(self):
        """Gabarito de uma página."""
        extraction = GabaritoExtraction(
            respostas=[
                GabaritoAnswer(numero=1, resposta="A"),
                GabaritoAnswer(numero=2, resposta="B"),
                GabaritoAnswer(numero=3, resposta="C"),
            ]
        )

        result = collect_gabarito_answers([extraction])

        assert result == {1: "A", 2: "B", 3: "C"}

    def test_multi_page_gabarito(self):
        """Gabarito de múltiplas páginas."""
        page1 = GabaritoExtraction(
            respostas=[
                GabaritoAnswer(numero=1, resposta="A"),
                GabaritoAnswer(numero=2, resposta="B"),
            ]
        )
        page2 = GabaritoExtraction(
            respostas=[
                GabaritoAnswer(numero=3, resposta="C"),
                GabaritoAnswer(numero=4, resposta="D"),
            ]
        )

        result = collect_gabarito_answers([page1, page2])

        assert result == {1: "A", 2: "B", 3: "C", 4: "D"}

    def test_empty_gabarito(self):
        """Gabarito vazio."""
        result = collect_gabarito_answers([GabaritoExtraction(respostas=[])])

        assert result == {}


class TestMergeQuestionsWithGabarito:
    """Testes para merge de questões com gabarito."""

    def test_all_questions_have_answers(self):
        """Todas as questões têm resposta no gabarito."""
        questions = [
            Question(
                numero=1,
                enunciado="Pergunta 1",
                alternativas=[
                    Alternative(letra="A", texto="Opt A"),
                    Alternative(letra="B", texto="Opt B"),
                ],
            ),
            Question(
                numero=2,
                enunciado="Pergunta 2",
                alternativas=[
                    Alternative(letra="A", texto="Opt A"),
                    Alternative(letra="B", texto="Opt B"),
                ],
            ),
        ]
        answers = {1: "A", 2: "B"}

        result = merge_questions_with_gabarito(questions, answers, "prova-teste")

        assert len(result) == 2
        assert result[0].resposta_correta == "A"
        assert result[1].resposta_correta == "B"
        assert all(q.prova_origem == "prova-teste" for q in result)

    def test_question_without_answer(self):
        """Questão sem resposta no gabarito (anulada)."""
        questions = [
            Question(
                numero=1,
                enunciado="Pergunta 1",
                alternativas=[Alternative(letra="A", texto="Opt")],
            ),
            Question(
                numero=2,
                enunciado="Pergunta 2 (anulada)",
                alternativas=[Alternative(letra="A", texto="Opt")],
            ),
        ]
        answers = {1: "A"}  # Questão 2 não tem resposta (anulada)

        result = merge_questions_with_gabarito(questions, answers, "prova")

        assert result[0].resposta_correta == "A"
        assert result[1].resposta_correta is None

    def test_alternatives_converted_to_dicts(self):
        """Alternativas devem ser convertidas para dicionários."""
        questions = [
            Question(
                numero=1,
                enunciado="Pergunta",
                alternativas=[
                    Alternative(letra="A", texto="Primeira"),
                    Alternative(letra="B", texto="Segunda"),
                ],
            ),
        ]

        result = merge_questions_with_gabarito(questions, {1: "A"}, "prova")

        assert result[0].alternativas == [
            {"letra": "A", "texto": "Primeira"},
            {"letra": "B", "texto": "Segunda"},
        ]
