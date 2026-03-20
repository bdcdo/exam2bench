"""Testes para o conversor de arquivos raw OAB."""

from pathlib import Path

import pytest

from products.oab.converter import parse_raw_oab_file


SAMPLE_NORMAL = """\
Questão 1

AREA ETHICS

Júlio e Lauro constituíram o mesmo advogado para, juntos, ajuizarem
ação de interesse comum.

Nessa situação hipotética, deve o advogado

OPTIONS

A:CORRECT) optar, com prudência e discernimento, por um dos mandatos,
e renunciar ao outro, resguardando o sigilo profissional.

B) manter com os constituintes contrato de prestação de serviços
jurídicos no interesse da causa.

C) assumir o patrocínio de ambos, em ações individuais.

D) designar, por substabelecimento com reservas, um advogado
de sua confiança.


Questão 2

AREA CONSTITUTIONAL

De acordo com a Constituição Federal, assinale a opção correta.

OPTIONS

A) Primeira opção.

B) Segunda opção.

C:CORRECT) Terceira opção.

D) Quarta opção.
"""

SAMPLE_NULL = """\
Questão 1

AREA ETHICS

Pergunta normal sobre ética.

OPTIONS

A:CORRECT) Resposta A.

B) Resposta B.

C) Resposta C.

D) Resposta D.


Questão 2 NULL

AREA TAXES

Questão anulada sobre tributos.

OPTIONS

A) Opção A.

B:CORRECT) Opção B.

C) Opção C.

D) Opção D.
"""

SAMPLE_EMPTY_AREA = """\
Questão 1

AREA

Pergunta sem área identificada.

OPTIONS

A:CORRECT) Resposta A.

B) Resposta B.

C) Resposta C.

D) Resposta D.
"""


def _write_sample(tmp_path: Path, content: str, filename: str = "2010-01.txt") -> Path:
    """Escreve conteúdo de exemplo em arquivo temporário."""
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


class TestParseRawOabFile:
    """Testes para parsing de arquivos .txt raw."""

    def test_parses_normal_questions(self, tmp_path):
        """Deve extrair questões normais corretamente."""
        path = _write_sample(tmp_path, SAMPLE_NORMAL)
        questions = parse_raw_oab_file(path)

        assert len(questions) == 2

        q1 = questions[0]
        assert q1.question_number == 1
        assert q1.correct_answer == "A"
        assert q1.nullified is False
        assert q1.metadata["area"] == "ETHICS"
        assert q1.exam_source == "oab-1"
        assert q1.id == "oab-1-001"
        assert len(q1.alternatives) == 4
        assert q1.alternatives[0].letter == "A"
        assert "prudência" in q1.alternatives[0].text

        q2 = questions[1]
        assert q2.question_number == 2
        assert q2.correct_answer == "C"
        assert q2.metadata["area"] == "CONSTITUTIONAL"

    def test_parses_nullified_questions(self, tmp_path):
        """Deve marcar questões NULL corretamente."""
        path = _write_sample(tmp_path, SAMPLE_NULL)
        questions = parse_raw_oab_file(path)

        assert len(questions) == 2

        q1 = questions[0]
        assert q1.nullified is False
        assert q1.correct_answer == "A"

        q2 = questions[1]
        assert q2.nullified is True
        assert q2.correct_answer is None
        assert q2.metadata["area"] == "TAXES"

    def test_handles_empty_area(self, tmp_path):
        """Deve marcar AREA vazia como 'NI'."""
        path = _write_sample(tmp_path, SAMPLE_EMPTY_AREA)
        questions = parse_raw_oab_file(path)

        assert len(questions) == 1
        assert questions[0].metadata["area"] == "NI"

    def test_extracts_metadata(self, tmp_path):
        """Deve extrair edition e year do nome do arquivo."""
        path = _write_sample(tmp_path, SAMPLE_NORMAL, filename="2018-25.txt")
        questions = parse_raw_oab_file(path)

        assert questions[0].metadata["edition"] == 25
        assert questions[0].metadata["year"] == 2018
        assert questions[0].metadata["source_format"] == "raw_text"
        assert questions[0].exam_source == "oab-25"

    def test_handles_edition_with_suffix(self, tmp_path):
        """Deve lidar com nomes como 2012-06a.txt."""
        path = _write_sample(tmp_path, SAMPLE_NORMAL, filename="2012-06a.txt")
        questions = parse_raw_oab_file(path)

        assert questions[0].metadata["edition"] == 6
        assert questions[0].metadata["year"] == 2012

    def test_statement_is_clean(self, tmp_path):
        """Enunciado não deve conter quebras de linha internas."""
        path = _write_sample(tmp_path, SAMPLE_NORMAL)
        questions = parse_raw_oab_file(path)

        assert "\n" not in questions[0].statement

    def test_alternatives_text_is_clean(self, tmp_path):
        """Texto das alternativas não deve conter quebras de linha internas."""
        path = _write_sample(tmp_path, SAMPLE_NORMAL)
        questions = parse_raw_oab_file(path)

        for alt in questions[0].alternatives:
            assert "\n" not in alt.text


class TestParseRealFile:
    """Testes com arquivo real (só roda se os dados existirem)."""

    RAW_DIR = Path(__file__).parent.parent / "products" / "oab" / "raw"

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "products" / "oab" / "raw" / "2010-01.txt").exists(),
        reason="Arquivo raw 2010-01.txt não disponível",
    )
    def test_parse_real_2010_01(self):
        """Deve extrair ~80 questões da edição 1."""
        path = self.RAW_DIR / "2010-01.txt"
        questions = parse_raw_oab_file(path)

        # Edição 1 tem 80 questões
        assert len(questions) >= 75  # margem para parsing issues
        assert all(q.exam_source == "oab-1" for q in questions)
        assert all(q.metadata["year"] == 2010 for q in questions)

        # Primeiras questões são de ETHICS
        ethics = [q for q in questions if q.metadata["area"] == "ETHICS"]
        assert len(ethics) > 0

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "products" / "oab" / "raw" / "2012-09.txt").exists(),
        reason="Arquivo raw 2012-09.txt não disponível",
    )
    def test_parse_real_with_null_questions(self):
        """Deve detectar questões anuladas na edição 9."""
        path = self.RAW_DIR / "2012-09.txt"
        questions = parse_raw_oab_file(path)

        nullified = [q for q in questions if q.nullified]
        assert len(nullified) >= 2  # Questões 3, 26, 27 são NULL
