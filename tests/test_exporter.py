"""Testes para o módulo de exportação CSV."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from exam2bench.exporter import export_to_csv, questions_to_dataframe
from exam2bench.merger import MergedQuestion


class TestQuestionsToDataframe:
    """Testes para conversão de questões para DataFrame."""

    def test_converts_questions_to_dataframe(self):
        """Deve converter lista de questões para DataFrame."""
        questions = [
            MergedQuestion(
                numero=1,
                enunciado="Pergunta 1",
                alternativas=[{"letra": "A", "texto": "Opt A"}],
                resposta_correta="A",
                prova_origem="prova-teste",
            ),
            MergedQuestion(
                numero=2,
                enunciado="Pergunta 2",
                alternativas=[{"letra": "A", "texto": "Opt A"}],
                resposta_correta="B",
                prova_origem="prova-teste",
            ),
        ]

        df = questions_to_dataframe(questions)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == [
            "numero",
            "pergunta",
            "alternativas",
            "resposta_correta",
            "prova_origem",
        ]

    def test_dataframe_is_sorted_by_numero(self):
        """DataFrame deve estar ordenado por número da questão."""
        questions = [
            MergedQuestion(
                numero=3,
                enunciado="Terceira",
                alternativas=[],
                resposta_correta="A",
                prova_origem="prova",
            ),
            MergedQuestion(
                numero=1,
                enunciado="Primeira",
                alternativas=[],
                resposta_correta="A",
                prova_origem="prova",
            ),
            MergedQuestion(
                numero=2,
                enunciado="Segunda",
                alternativas=[],
                resposta_correta="A",
                prova_origem="prova",
            ),
        ]

        df = questions_to_dataframe(questions)

        assert list(df["numero"]) == [1, 2, 3]
        assert list(df["pergunta"]) == ["Primeira", "Segunda", "Terceira"]

    def test_alternativas_are_json_serialized(self):
        """Alternativas devem ser serializadas como JSON."""
        alternativas = [
            {"letra": "A", "texto": "Opção A"},
            {"letra": "B", "texto": "Opção B"},
        ]
        questions = [
            MergedQuestion(
                numero=1,
                enunciado="Pergunta",
                alternativas=alternativas,
                resposta_correta="A",
                prova_origem="prova",
            ),
        ]

        df = questions_to_dataframe(questions)

        # Deve ser possível deserializar o JSON
        parsed = json.loads(df.iloc[0]["alternativas"])
        assert parsed == alternativas

    def test_handles_none_resposta_correta(self):
        """Deve lidar com resposta_correta nula (questão anulada)."""
        questions = [
            MergedQuestion(
                numero=1,
                enunciado="Questão anulada",
                alternativas=[],
                resposta_correta=None,
                prova_origem="prova",
            ),
        ]

        df = questions_to_dataframe(questions)

        assert pd.isna(df.iloc[0]["resposta_correta"])


class TestExportToCsv:
    """Testes para exportação para CSV."""

    def test_creates_csv_file(self):
        """Deve criar arquivo CSV."""
        questions = [
            MergedQuestion(
                numero=1,
                enunciado="Pergunta",
                alternativas=[{"letra": "A", "texto": "Opt"}],
                resposta_correta="A",
                prova_origem="prova",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv(questions, output_path)

            assert output_path.exists()

    def test_csv_content_is_correct(self):
        """Conteúdo do CSV deve estar correto."""
        questions = [
            MergedQuestion(
                numero=1,
                enunciado="Qual é 2+2?",
                alternativas=[
                    {"letra": "A", "texto": "3"},
                    {"letra": "B", "texto": "4"},
                ],
                resposta_correta="B",
                prova_origem="matematica-2025",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv(questions, output_path)

            # Ler de volta
            df = pd.read_csv(output_path)

            assert len(df) == 1
            assert df.iloc[0]["numero"] == 1
            assert df.iloc[0]["pergunta"] == "Qual é 2+2?"
            assert df.iloc[0]["resposta_correta"] == "B"
            assert df.iloc[0]["prova_origem"] == "matematica-2025"

            # Verificar alternativas
            alts = json.loads(df.iloc[0]["alternativas"])
            assert alts[0]["letra"] == "A"
            assert alts[1]["texto"] == "4"

    def test_csv_uses_utf8_encoding(self):
        """CSV deve usar encoding UTF-8 para caracteres especiais."""
        questions = [
            MergedQuestion(
                numero=1,
                enunciado="Questão com acentuação: é, ã, ç",
                alternativas=[{"letra": "A", "texto": "Opção com ñ e ü"}],
                resposta_correta="A",
                prova_origem="prova",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv(questions, output_path)

            df = pd.read_csv(output_path, encoding="utf-8")

            assert "acentuação" in df.iloc[0]["pergunta"]
            assert "ñ" in df.iloc[0]["alternativas"]

    def test_empty_questions_list(self):
        """Deve lidar com lista vazia de questões."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            export_to_csv([], output_path)

            assert output_path.exists()
            # CSV vazio não tem colunas, apenas verificamos que o arquivo existe
            content = output_path.read_text()
            assert content == "" or content == "\n"
