"""Download de provas e gabaritos do ENAM (Exame Nacional da Magistratura).

Fonte: FGV Conhecimento — https://conhecimento.fgv.br/concursos/enam/
Baixa Tipo 1 de cada edição + gabarito definitivo.
"""

import sys
import urllib.request
from pathlib import Path

DEST_DIR = Path(__file__).resolve().parent.parent / "products" / "enam" / "exams"

DOWNLOADS: list[tuple[str, str, str]] = [
    # (nome_local, url_prova, url_gabarito)
    (
        "enam-20241",
        "https://conhecimento.fgv.br/sites/default/files/concursos/magistraturacns001-tipo-1.pdf",
        "https://conhecimento.fgv.br/sites/default/files/concursos/enam2024_gabarito_definitivo_aposanulacao.pdf",
    ),
    (
        "enam-20241r",
        "https://conhecimento.fgv.br/sites/default/files/concursos/magistraturacns001-tipo-1_0.pdf",
        "https://conhecimento.fgv.br/sites/default/files/concursos/enam2024r_gabarito_definitivo.pdf",
    ),
    (
        "enam-20242",
        "https://conhecimento.fgv.br/sites/default/files/concursos/magistraturacns001-tipo-1_1.pdf",
        "https://conhecimento.fgv.br/sites/default/files/concursos/enam202402_recursos_gabarito_definitivo_0.pdf",
    ),
    (
        "enam-20251",
        "https://conhecimento.fgv.br/sites/default/files/concursos/magistraturacns001-tipo-1_2.pdf",
        "https://conhecimento.fgv.br/sites/default/files/concursos/gabarito-definitivo-enam-2025.1_v2.pdf",
    ),
    (
        "enam-20252",
        "https://conhecimento.fgv.br/sites/default/files/concursos/magistraturacns001-tipo-1_3.pdf",
        "https://conhecimento.fgv.br/sites/default/files/concursos/gabarito-definitivo-v2.pdf",
    ),
]


def download(url: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  [skip] {dest.name} já existe")
        return True
    print(f"  [download] {dest.name} ← {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"  [ERRO] {dest.name}: {e}")
        return False


def main() -> None:
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0

    for name, prova_url, gabarito_url in DOWNLOADS:
        print(f"\n{name}:")
        prova_ok = download(prova_url, DEST_DIR / f"{name}-prova.pdf")
        gab_ok = download(gabarito_url, DEST_DIR / f"{name}-gabarito.pdf")
        if prova_ok and gab_ok:
            ok += 1
        else:
            fail += 1

    print(f"\nResumo: {ok} edições OK, {fail} com erro")
    print(f"Destino: {DEST_DIR}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
