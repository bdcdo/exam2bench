"""Download de provas e gabaritos do OAB (edições 26–45).

URLs extraídas do portal FGV: https://oab.fgv.br/
Baixa Caderno de Prova Tipo 1 + Gabarito Preliminar/Definitivo de cada edição.
"""

import sys
import urllib.request
from pathlib import Path

DEST_DIR = Path(__file__).resolve().parent.parent / "products" / "oab" / "exams"

# (edição, url_prova, url_gabarito)
DOWNLOADS: list[tuple[int, str, str]] = [
    (26, "https://oab.fgv.br/arq/629/882160_CADERNO_TIPO_1_XXVI_EXAME.pdf",
         "https://oab.fgv.br/arq/629/85363_GABARITOS%20PRELIMIARES_XXVI_EXAME_DE_ORDEM%20(1).pdf"),
    (27, "https://oab.fgv.br/arq/630/963413_CADERNO_TIPO_1_XXVII_EXAME.pdf",
         "https://oab.fgv.br/arq/630/339272_GABARITOS%20PRELIMIARES_XXVII_EXAME_DE_ORDEM.pdf"),
    (28, "https://oab.fgv.br/arq/631/1338368_CADERNO_TIPO_1_XXVIII_EXAME%20-%20ENVIO.pdf",
         "http://oab.fgv.br/arq/631/283981_339414_GABARITOS_RETIFICADOS_XXVIII_EXAME_DE_ORDEM.pdf"),
    (29, "https://oab.fgv.br/arq/632/831410_CADERNO_TIPO_1_XXIX__EXAME%20-%20ENVIO3.pdf",
         "https://oab.fgv.br/arq/632/85462_GABARITOS%20PRELIMINARES_XXIX_EXAME_DE_ORDEM.pdf"),
    (30, "https://oab.fgv.br/arq/633/3286678_OAB193%20Advogado%20(EOU)%20Tipo%201.pdf",
         "https://oab.fgv.br/arq/633/97164_GABARITOS%20PRELIMINARES_XXX_EXAME_DE_ORDEM.pdf"),
    (31, "https://oab.fgv.br/arq/634/1063219_OAB201%20Advogado%20(ADVG)%20Tipo%201.pdf",
         "https://oab.fgv.br/arq/634/70919_GABARITOS%20PRELIMINARES_XXXI_EXAME_DE_ORDEM.pdf"),
    (32, "http://oab.fgv.br/arq/635/801338_OAB211%20Advogado%20(ADVG)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/635/590557_GABARITOS%20PRELIMINARES_XXXII_EXAME_DE_ORDEM_Proposta2_ANULACOES.pdf"),
    (33, "http://oab.fgv.br/arq/636/876260_OAB212%20Advogado%20(EOU)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/636/475460_GABARITOS%20PRELIMINARES_XXXIII_EXAME_DE_ORDEM_COMANULACAO.pdf"),
    (34, "http://oab.fgv.br/arq/637/466708_OAB221%20Advogado%20(EOU)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/637/76291_GABARITOS%20PRELIMINARES_XXXIV_EXAME_DE_ORDEM.pdf"),
    (35, "http://oab.fgv.br/arq/638/686848_OAB222%20Advogado%20(EOU)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/638/80040_GABARITOS%20PRELIMINARES_XXXV_EXAME_DE_ORDEM.pdf"),
    (36, "http://oab.fgv.br/arq/639/527735_Advogado(EOU)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/639/75766_GABARITOS%20PRELIMINARES_XXXVI_EXAME_DE_ORDEM.pdf"),
    (37, "http://oab.fgv.br/arq/640/641232_Advogado(EOU)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/640/77817_GABARITOS%20PRELIMINARES_XXXVII_EXAME_DE_ORDEM.pdf"),
    (38, "http://oab.fgv.br/arq/641/1180933_OABXXXVIII%20-%20Prova%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/641/675049_OABXXXVIII%20-%20Gabaritos%20para%20publica%c3%a7%c3%a3o.pdf"),
    (39, "http://oab.fgv.br/arq/642/1108259_ADVOGADO%20OAB(CNS01)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/642/631883_OABXXXIX%20Gabaritos%20para%20publica%c3%a7%c3%a3o%20-%20V20231119.pdf"),
    (40, "http://oab.fgv.br/arq/643/341069_ADVOGADO%20OAB(CNS01)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/643/603863_OABXL%20Gabaritos%20para%20publica%c3%a7%c3%a3o.pdf"),
    (41, "http://oab.fgv.br/arq/644/552356_ADVOGADO%20OAB(CNS01)%20Tipo%201%20(1).pdf",
         "http://oab.fgv.br/arq/644/255635_OAB41%20Gabaritos%20para%20publica%c3%a7%c3%a3o%20-%20v20240728.pdf"),
    (42, "http://oab.fgv.br/arq/645/402439_OAB%2042%20-%20ADVOGADO%20OAB(CNS01)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/645/674526_OAB42%20Gabaritos%20-%20V20241203.pdf"),
    (43, "http://oab.fgv.br/arq/646/838452_ADVOGADO%20OAB(CNS01)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/646/410294_OAB43%20Gabaritos%20para%20publica%c3%a7%c3%a3o%20-%20V20250430.pdf"),
    (44, "http://oab.fgv.br/arq/647/519680_ADVOGADO%20OAB(CNS01)%20Tipo%201%20(2).pdf",
         "http://oab.fgv.br/arq/647/253404_OAB44%20Gabaritos%20para%20publica%c3%a7%c3%a3o.pdf"),
    (45, "http://oab.fgv.br/arq/648/405589_ADVOGADO%20OAB(CNS01)%20Tipo%201.pdf",
         "http://oab.fgv.br/arq/648/335844_OAB45%20Gabaritos%20para%20publica%c3%a7%c3%a3o%20-%20v2.pdf"),
]


def download(url: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  [skip] {dest.name} já existe")
        return True
    print(f"  [download] {dest.name}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            if len(data) < 5000:
                print(f"  [ERRO] arquivo muito pequeno ({len(data)} bytes)")
                return False
            dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"  [ERRO] {dest.name}: {e}")
        return False


def main() -> None:
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0

    for edition, prova_url, gabarito_url in DOWNLOADS:
        print(f"\nEdição {edition}:")
        prova_ok = download(prova_url, DEST_DIR / f"oab-{edition}-prova.pdf")
        gab_ok = download(gabarito_url, DEST_DIR / f"oab-{edition}-gabarito.pdf")
        if prova_ok and gab_ok:
            ok += 1
        else:
            fail += 1

    print(f"\nResumo: {ok} edições OK, {fail} com erro")
    print(f"Destino: {DEST_DIR}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
