"""Testes para o módulo de merge de questões e gabarito."""

import pytest

from exam2bench.merger import (
    collect_gabarito_answers,
    merge_multi_page_questions,
    merge_questions_with_gabarito,
)
from exam2bench.models import (
    Alternative,
    ExamAlternative,
    ExamQuestion,
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

        result, num_dupes = merge_multi_page_questions(extractions)

        assert len(result) == 2
        assert result[0].numero == 1
        assert result[1].numero == 2
        assert num_dupes == 0

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

        result, num_dupes = merge_multi_page_questions(extractions)

        assert len(result) == 2
        assert result[0].numero == 1
        assert result[1].numero == 2
        assert num_dupes == 0

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

        result, num_dupes = merge_multi_page_questions(extractions)

        assert len(result) == 1
        assert result[0].numero == 1
        assert num_dupes == 0

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

        result, num_dupes = merge_multi_page_questions(extractions)

        assert len(result) == 2
        assert result[0].numero == 1
        assert result[1].numero == 2
        assert num_dupes == 0

    def test_split_question_across_pages_is_merged(self):
        """Questão na fronteira entre páginas: concatena enunciados, mantém alternativas mais completas."""
        q1 = Question(
            numero=1, enunciado="Pergunta 1",
            alternativas=[Alternative(letra="A", texto="Resp")],
        )
        # Questão 2 dividida: primeira metade na pg 1, segunda metade na pg 2
        q2_part1 = Question(
            numero=2, enunciado="Início do enunciado da questão 2",
            alternativas=[],
        )
        q2_part2 = Question(
            numero=2, enunciado="continuação e final do enunciado.",
            alternativas=[
                Alternative(letra="A", texto="Opção A"),
                Alternative(letra="B", texto="Opção B"),
            ],
        )
        q3 = Question(
            numero=3, enunciado="Pergunta 3",
            alternativas=[Alternative(letra="A", texto="Resp")],
        )

        extractions = [
            (1, PageExtraction(questoes=[q1, q2_part1])),
            (2, PageExtraction(questoes=[q2_part2, q3])),
        ]

        result, num_dupes = merge_multi_page_questions(extractions)

        assert len(result) == 3
        assert num_dupes == 1
        # Enunciado concatenado
        assert result[1].enunciado == "Início do enunciado da questão 2 continuação e final do enunciado."
        # Alternativas da versão mais completa (pg 2)
        assert len(result[1].alternativas) == 2


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
        assert result[0].correct_answer == "A"
        assert result[1].correct_answer == "B"
        assert all(q.exam_source == "prova-teste" for q in result)

    def test_question_without_answer_is_nullified(self):
        """Questão sem resposta no gabarito deve ser marcada como anulada."""
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

        assert result[0].correct_answer == "A"
        assert result[0].nullified is False
        assert result[1].correct_answer is None
        assert result[1].nullified is True

    def test_explicit_nullified_questions(self):
        """Questões explicitamente marcadas como anuladas."""
        questions = [
            Question(
                numero=1,
                enunciado="Pergunta normal",
                alternativas=[Alternative(letra="A", texto="Opt")],
            ),
            Question(
                numero=2,
                enunciado="Questão anulada",
                alternativas=[Alternative(letra="A", texto="Opt")],
            ),
        ]
        answers = {1: "A", 2: "B"}

        result = merge_questions_with_gabarito(
            questions, answers, "prova", nullified_questions={2}
        )

        assert result[0].correct_answer == "A"
        assert result[0].nullified is False
        assert result[1].correct_answer is None
        assert result[1].nullified is True

    def test_alternatives_converted_to_exam_alternatives(self):
        """Alternativas devem ser convertidas para ExamAlternative."""
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

        assert len(result[0].alternatives) == 2
        assert isinstance(result[0].alternatives[0], ExamAlternative)
        assert result[0].alternatives[0].letter == "A"
        assert result[0].alternatives[0].text == "Primeira"
        assert result[0].alternatives[1].letter == "B"
        assert result[0].alternatives[1].text == "Segunda"

    def test_generates_correct_id(self):
        """ID deve ser gerado como {exam_source}-{question_number:03d}."""
        questions = [
            Question(
                numero=1,
                enunciado="Pergunta",
                alternativas=[Alternative(letra="A", texto="Opt")],
            ),
        ]

        result = merge_questions_with_gabarito(questions, {1: "A"}, "oab-25")

        assert result[0].id == "oab-25-001"

    def test_metadata_passed_through(self):
        """Metadados devem ser passados para as questões."""
        questions = [
            Question(
                numero=1,
                enunciado="Pergunta",
                alternativas=[Alternative(letra="A", texto="Opt")],
            ),
        ]

        result = merge_questions_with_gabarito(
            questions, {1: "A"}, "oab-25",
            metadata={"edition": 25, "year": 2018},
        )

        assert result[0].metadata == {"edition": 25, "year": 2018}
