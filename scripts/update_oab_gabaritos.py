"""Re-baixa gabaritos definitivos para edições 35-45 (substituindo preliminares)."""

import sys
import urllib.request
from pathlib import Path

DEST_DIR = Path(__file__).resolve().parent.parent / "products" / "oab" / "exams"

# Gabaritos definitivos encontrados pelo agente (melhores que preliminares)
UPDATES: list[tuple[int, str]] = [
    (35, "http://oab.fgv.br/arq/638/474880_GABARITOS%20DEFINITIVOS_XXXV_EXAME_DE_ORDEM.pdf"),
    (36, "http://oab.fgv.br/arq/639/243215_GABARITOS%20DEFINITIVOS_XXXVI_EXAME_DE_ORDEM.pdf"),
    (37, "http://oab.fgv.br/arq/640/82353_GABARITOS%20DEFINITIVOS_XXXVII_EXAME_DE_ORDEM.pdf"),
    (38, "http://oab.fgv.br/arq/641/77411_GABARITOS%20DEFINITIVOS_XXXVIII_EXAME_DE_ORDEM_20230724.pdf"),
    (39, "http://oab.fgv.br/arq/642/86039_OABXXXIX%20definitivo%20v20231205.pdf"),
    (40, "http://oab.fgv.br/arq/643/244619_oab241_gabarito_definitivo%20(002)%20(1).pdf"),
    (41, "http://oab.fgv.br/arq/644/84844_oab242_gabarito_definitivo.pdf"),
    (42, "http://oab.fgv.br/arq/645/273585_OAB42%20Gabaritos%20para%20publica%c3%a7%c3%a3o%20-%20V20241203%20(003).pdf"),
    (43, "http://oab.fgv.br/arq/646/194143_oab251_gabarito_definitivo_ms.pdf"),
    (44, "http://oab.fgv.br/arq/647/158882_OAB44%20Gabaritos%20para%20publica%c3%a7%c3%a3o%20-%20definitivo.pdf"),
    (45, "http://oab.fgv.br/arq/648/85707_OAB45%20Gabaritos%20para%20publica%c3%a7%c3%a3o%20-%20v3.pdf"),
]


def main() -> None:
    ok, fail = 0, 0
    for edition, url in UPDATES:
        dest = DEST_DIR / f"oab-{edition}-gabarito.pdf"
        print(f"[{edition}] Atualizando gabarito definitivo...", end=" ")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                if len(data) < 5000:
                    print(f"ERRO (arquivo pequeno: {len(data)} bytes)")
                    fail += 1
                    continue
                dest.write_bytes(data)
                print("OK")
                ok += 1
        except Exception as e:
            print(f"ERRO: {e}")
            fail += 1

    print(f"\nResumo: {ok} atualizados, {fail} com erro")
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
