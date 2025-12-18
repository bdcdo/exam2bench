"""Testes para o processador de PDF."""

import base64
from pathlib import Path

import pytest

from exam2bench.pdf_processor import image_to_base64, pdf_to_base64_images, pdf_to_images

# Diretório de exames para testes
EXAMS_DIR = Path(__file__).parent.parent / "exams"


class TestImageToBase64:
    """Testes para a função image_to_base64."""

    def test_converts_bytes_to_base64(self):
        """Deve converter bytes para string base64."""
        test_bytes = b"Hello, World!"
        result = image_to_base64(test_bytes)

        assert isinstance(result, str)
        assert result == base64.b64encode(test_bytes).decode("utf-8")

    def test_roundtrip_encoding(self):
        """Deve permitir decodificar de volta para os bytes originais."""
        original = b"\x89PNG\r\n\x1a\n"  # PNG header bytes
        encoded = image_to_base64(original)
        decoded = base64.b64decode(encoded)

        assert decoded == original


@pytest.mark.skipif(
    not any(EXAMS_DIR.glob("*-prova.pdf")),
    reason="Nenhum PDF de prova disponível para teste",
)
class TestPdfToImages:
    """Testes para a função pdf_to_images."""

    @pytest.fixture
    def sample_pdf(self) -> Path:
        """Retorna o primeiro PDF de prova disponível."""
        return next(EXAMS_DIR.glob("*-prova.pdf"))

    def test_returns_list_of_tuples(self, sample_pdf: Path):
        """Deve retornar lista de tuplas (page_num, bytes)."""
        result = pdf_to_images(sample_pdf)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(item, tuple) for item in result)
        assert all(len(item) == 2 for item in result)

    def test_page_numbers_start_at_one(self, sample_pdf: Path):
        """Números de página devem começar em 1."""
        result = pdf_to_images(sample_pdf)

        page_numbers = [page_num for page_num, _ in result]
        assert page_numbers[0] == 1
        assert page_numbers == list(range(1, len(result) + 1))

    def test_images_are_png_bytes(self, sample_pdf: Path):
        """Imagens devem ser bytes PNG válidos."""
        result = pdf_to_images(sample_pdf)

        for _, image_bytes in result:
            assert isinstance(image_bytes, bytes)
            # PNG começa com o magic number \x89PNG
            assert image_bytes[:4] == b"\x89PNG"


@pytest.mark.skipif(
    not any(EXAMS_DIR.glob("*-prova.pdf")),
    reason="Nenhum PDF de prova disponível para teste",
)
class TestPdfToBase64Images:
    """Testes para a função pdf_to_base64_images."""

    @pytest.fixture
    def sample_pdf(self) -> Path:
        """Retorna o primeiro PDF de prova disponível."""
        return next(EXAMS_DIR.glob("*-prova.pdf"))

    def test_returns_base64_strings(self, sample_pdf: Path):
        """Deve retornar strings base64 ao invés de bytes."""
        result = pdf_to_base64_images(sample_pdf)

        assert isinstance(result, list)
        assert len(result) > 0

        for page_num, image_b64 in result:
            assert isinstance(page_num, int)
            assert isinstance(image_b64, str)
            # Base64 deve ser decodificável
            decoded = base64.b64decode(image_b64)
            assert decoded[:4] == b"\x89PNG"
