"""Testes para o módulo de pareamento de PDFs."""

import tempfile
from pathlib import Path

from exam2bench.pairing import find_exam_pairs


class TestFindExamPairs:
    """Testes para descoberta de pares prova/gabarito."""

    def test_finds_default_suffix_pairs(self):
        """Deve encontrar pares com sufixos padrão (-prova/-gabarito)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "enam-2025-prova.pdf").touch()
            (d / "enam-2025-gabarito.pdf").touch()

            pairs = find_exam_pairs(d)

            assert len(pairs) == 1
            assert pairs[0][2] == "enam-2025"

    def test_finds_multiple_pairs(self):
        """Deve encontrar múltiplos pares."""
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            for name in ["exam-a", "exam-b"]:
                (d / f"{name}-prova.pdf").touch()
                (d / f"{name}-gabarito.pdf").touch()

            pairs = find_exam_pairs(d)

            assert len(pairs) == 2
            names = {p[2] for p in pairs}
            assert names == {"exam-a", "exam-b"}

    def test_skips_unmatched_provas(self, capsys):
        """Provas sem gabarito devem ser puladas com aviso."""
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "orphan-prova.pdf").touch()

            pairs = find_exam_pairs(d)

            assert len(pairs) == 0
            captured = capsys.readouterr()
            assert "Aviso" in captured.out

    def test_custom_suffixes(self):
        """Deve funcionar com sufixos customizados."""
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "oab-26-exam.pdf").touch()
            (d / "oab-26-answers.pdf").touch()

            pairs = find_exam_pairs(d, prova_suffix="-exam", gabarito_suffix="-answers")

            assert len(pairs) == 1
            assert pairs[0][2] == "oab-26"

    def test_empty_directory(self):
        """Diretório vazio retorna lista vazia."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pairs = find_exam_pairs(Path(tmpdir))
            assert pairs == []
