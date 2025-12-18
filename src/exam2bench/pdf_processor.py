"""Processador de PDF para conversão em imagens."""

import base64
from pathlib import Path

import fitz  # PyMuPDF

# Zoom factor para conversão PDF -> imagem
# 72 DPI é o padrão do PDF, multiplicamos para aumentar resolução
# 4.17 = 300 DPI (padrão profissional para OCR)
ZOOM_FACTOR = 300 / 72  # ~4.17


def pdf_to_images(pdf_path: Path) -> list[tuple[int, bytes]]:
    """Converte páginas de um PDF em imagens PNG.

    Args:
        pdf_path: Caminho para o arquivo PDF.

    Returns:
        Lista de tuplas (número_da_página, bytes_da_imagem).
        O número da página começa em 1.
    """
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(ZOOM_FACTOR, ZOOM_FACTOR)

    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        image_bytes = pix.tobytes("png")
        images.append((page_num + 1, image_bytes))

    doc.close()
    return images


def image_to_base64(image_bytes: bytes) -> str:
    """Converte bytes de imagem para string base64.

    Args:
        image_bytes: Bytes da imagem PNG.

    Returns:
        String base64 da imagem.
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def pdf_to_base64_images(pdf_path: Path) -> list[tuple[int, str]]:
    """Converte páginas de um PDF diretamente para imagens base64.

    Args:
        pdf_path: Caminho para o arquivo PDF.

    Returns:
        Lista de tuplas (número_da_página, base64_da_imagem).
    """
    images = pdf_to_images(pdf_path)
    return [(page_num, image_to_base64(img)) for page_num, img in images]
