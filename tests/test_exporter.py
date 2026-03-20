"""Testes para o módulo de exportação JSONL e CSV."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from exam2bench.exporter import export_to_csv, export_to_jsonl, questions_to_dataframe
from exam2bench.models import ExamAlternative, ExamQuestion


def _make_question(**overrides) -> ExamQuestion:
    """Helper para criar ExamQuestion de teste."""
    defaults = {
        "id": "test-001",
        "exam_source": "test",
        "question_number": 1,
        "statement": "Pergunta de teste",
        "alternatives": [
            ExamAlternative(letter="A", text="Opt A"),
            ExamAlternative(letter="B", text="Opt B"),
        ],
        "correct_answer": "A",
        "nullified": False,
        "metadata": {},
    }
    defaults.update(overrides)
    return ExamQuestion(**defaults)


class TestQuestionsToDataframe:
    """Testes para conversão de questões para DataFrame."""

    def test_converts_questions_to_dataframe(self):
        """Deve converter lista de questões para DataFrame."""
        questions = [
            _make_question(id="test-001", question_number=1),
            _make_question(id="test-002", question_number=2, correct_answer="B"),
        ]

        df = questions_to_dataframe(questions)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == [
            "id", "exam_source", "question_number", "statement",
            "alternatives", "correct_answer", "nullified", "metadata",
        ]

    def test_dataframe_is_sorted_by_question_number(self):
        """DataFrame deve estar ordenado por número da questão."""
        questions = [
            _make_question(id="t-003", question_number=3, statement="Terceira"),
            _make_question(id="t-001", question_number=1, statement="Primeira"),
            _make_question(id="t-002", question_number=2, statement="Segunda"),
        ]

        df = questions_to_dataframe(questions)

        assert list(df["question_number"]) == [1, 2, 3]
        assert list(df["statement"]) == ["Primeira", "Segunda", "Terceira"]

    def test_alternativas_are_json_serialized(self):
        """Alternativas devem ser serializadas como JSON."""
        questions = [_make_question()]

        df = questions_to_dataframe(questions)

        parsed = json.loads(df.iloc[0]["alternatives"])
        assert parsed == [
            {"letter": "A", "text": "Opt A"},
            {"letter": "B", "text": "Opt B"},
        ]

    def test_handles_none_correct_answer(self):
        """Deve lidar com correct_answer nulo (questão anulada)."""
        questions = [
            _make_question(correct_answer=None, nullified=True)
        ]

        df = questions_to_dataframe(questions)

        assert pd.isna(df.iloc[0]["correct_answer"])
        assert df.iloc[0]["nullified"] == True


class TestExportToCsv:
    """Testes para exportação para CSV."""

    def test_creates_csv_file(self):
        """Deve criar arquivo CSV."""
        questions = [_make_question()]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv(questions, output_path)

            assert output_path.exists()

    def test_csv_content_is_correct(self):
        """Conteúdo do CSV deve estar correto."""
        questions = [
            _make_question(
                id="math-001",
                exam_source="math-2025",
                question_number=1,
                statement="Qual é 2+2?",
                correct_answer="B",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv(questions, output_path)

            df = pd.read_csv(output_path)

            assert len(df) == 1
            assert df.iloc[0]["id"] == "math-001"
            assert df.iloc[0]["statement"] == "Qual é 2+2?"
            assert df.iloc[0]["correct_answer"] == "B"
            assert df.iloc[0]["exam_source"] == "math-2025"

    def test_csv_uses_utf8_encoding(self):
        """CSV deve usar encoding UTF-8 para caracteres especiais."""
        questions = [
            _make_question(
                statement="Questão com acentuação: é, ã, ç",
                alternatives=[ExamAlternative(letter="A", text="Opção com ñ e ü")],
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv(questions, output_path)

            df = pd.read_csv(output_path, encoding="utf-8")

            assert "acentuação" in df.iloc[0]["statement"]
            assert "ñ" in df.iloc[0]["alternatives"]

    def test_empty_questions_list(self):
        """Deve lidar com lista vazia de questões."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv([], output_path)

            assert output_path.exists()
            df = pd.read_csv(output_path)
            assert df.empty
            assert "id" in df.columns
            assert "statement" in df.columns


class TestExportToJsonl:
    """Testes para exportação para JSONL."""

    def test_creates_jsonl_file(self):
        """Deve criar arquivo JSONL."""
        questions = [_make_question()]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.jsonl"
            export_to_jsonl(questions, output_path)

            assert output_path.exists()

    def test_jsonl_is_valid(self):
        """Cada linha do JSONL deve ser um JSON válido."""
        questions = [
            _make_question(id="t-001", question_number=1),
            _make_question(id="t-002", question_number=2),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.jsonl"
            export_to_jsonl(questions, output_path)

            lines = output_path.read_text().strip().split("\n")
            assert len(lines) == 2

            for line in lines:
                data = json.loads(line)
                assert "id" in data
                assert "statement" in data
                assert "alternatives" in data

    def test_jsonl_roundtrip(self):
        """ExamQuestion serializado e desserializado deve ser idêntico."""
        original = _make_question(
            metadata={"area": "ETHICS", "edition": 25},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.jsonl"
            export_to_jsonl([original], output_path)

            line = output_path.read_text().strip()
            restored = ExamQuestion.model_validate_json(line)

            assert restored.id == original.id
            assert restored.statement == original.statement
            assert restored.correct_answer == original.correct_answer
            assert restored.metadata == original.metadata
            assert len(restored.alternatives) == len(original.alternatives)

    def test_jsonl_sorted_by_question_number(self):
        """JSONL deve estar ordenado por número da questão."""
        questions = [
            _make_question(id="t-003", question_number=3),
            _make_question(id="t-001", question_number=1),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.jsonl"
            export_to_jsonl(questions, output_path)

            lines = output_path.read_text().strip().split("\n")
            first = json.loads(lines[0])
            second = json.loads(lines[1])
            assert first["question_number"] == 1
            assert second["question_number"] == 3
