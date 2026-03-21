"""Extrai URLs de provas e gabaritos OAB do portal FGV.

O portal ASP.NET requer:
1. GET da página de cada edição para obter ViewState
2. POST com seleção da seccional (SP)
3. Parsing da página resultante para links de PDFs
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from http.cookiejar import CookieJar
import urllib.request
import urllib.parse

BASE_URL = "https://oab.fgv.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


class ASPFormParser(HTMLParser):
    """Extrai campos hidden do form ASP.NET."""

    def __init__(self):
        super().__init__()
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            d = dict(attrs)
            if d.get("type") == "hidden" and "name" in d:
                self.fields[d["name"]] = d.get("value", "")


class PDFLinkParser(HTMLParser):
    """Extrai links de PDFs da página."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._current_href = None
        self._current_text = []
        self._in_a = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            d = dict(attrs)
            href = d.get("href", "")
            if ".pdf" in href.lower():
                self._current_href = href
                self._current_text = []
                self._in_a = True

    def handle_data(self, data):
        if self._in_a:
            self._current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            text = " ".join(self._current_text).strip()
            if self._current_href:
                self.links.append((text, self._current_href))
            self._in_a = False
            self._current_href = None


def create_opener():
    """Cria opener com cookie jar para manter sessão."""
    cj = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get_page(opener, url):
    """GET request."""
    req = urllib.request.Request(url, headers=HEADERS)
    with opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def post_form(opener, url, data):
    """POST request."""
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers={
        **HEADERS,
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def scrape_edition(opener, edition: int) -> dict:
    """Extrai URLs de prova e gabarito para uma edição."""
    key = 603 + edition
    page_url = f"{BASE_URL}/home.aspx?key={key}"

    # Step 1: GET para obter ViewState
    html = get_page(opener, page_url)

    form_parser = ASPFormParser()
    form_parser.feed(html)

    # Step 2: POST com seleção de seccional SP
    post_data = {
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$listSeccional",
        "__EVENTARGUMENT": "",
        "ctl00$ContentPlaceHolder1$listSeccional": "OAB / SP",
    }
    # Adicionar campos hidden do form
    for name, value in form_parser.fields.items():
        post_data[name] = value

    result_html = post_form(opener, page_url, post_data)

    # Step 3: Extrair links de PDF
    link_parser = PDFLinkParser()
    link_parser.feed(result_html)

    prova_url = None
    gabarito_url = None

    for text, href in link_parser.links:
        full_url = href if href.startswith("http") else urljoin(BASE_URL + "/", href)
        text_lower = text.lower()

        # Prova Tipo 1 (1ª fase)
        if not prova_url and ("tipo 1" in text_lower or "tipo_1" in href.lower()):
            prova_url = full_url

        # Gabarito Preliminar (1ª fase, não 2ª fase)
        if not gabarito_url and "gabarito" in text_lower and "preliminar" in text_lower:
            if "2ª fase" not in text_lower and "prático" not in text_lower:
                gabarito_url = full_url

    # Fallback: procurar qualquer gabarito 1ª fase
    if not gabarito_url:
        for text, href in link_parser.links:
            full_url = href if href.startswith("http") else urljoin(BASE_URL + "/", href)
            text_lower = text.lower()
            if "gabarito" in text_lower and "2ª fase" not in text_lower and "prático" not in text_lower:
                if "justificado" not in text_lower and "padrão" not in text_lower:
                    gabarito_url = full_url
                    break

    return {
        "edition": edition,
        "key": key,
        "prova_url": prova_url,
        "gabarito_url": gabarito_url,
        "total_links": len(link_parser.links),
    }


def main():
    opener = create_opener()
    results = {}
    ok, fail = 0, 0

    print("=" * 60)
    print("Scraping URLs OAB — Edições 26 a 45")
    print("=" * 60)

    for ed in range(26, 46):
        print(f"\n[{ed}] Scraping key={603 + ed}...", end=" ", flush=True)
        try:
            info = scrape_edition(opener, ed)
            results[str(ed)] = info

            if info["prova_url"] and info["gabarito_url"]:
                print(f"OK ({info['total_links']} links)")
                ok += 1
            else:
                missing = []
                if not info["prova_url"]:
                    missing.append("prova")
                if not info["gabarito_url"]:
                    missing.append("gabarito")
                print(f"PARCIAL - falta: {', '.join(missing)}")
                fail += 1
        except Exception as e:
            print(f"ERRO: {e}")
            results[str(ed)] = {"edition": ed, "error": str(e)}
            fail += 1

    # Salvar JSON com URLs
    output_path = Path(__file__).resolve().parent / "oab_urls.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Resumo: {ok} completas, {fail} parciais/erro")
    print(f"URLs salvas em: {output_path}")

    # Imprimir lista para uso no download script
    print(f"\n{'=' * 60}")
    print("URLs para download_oab.py:")
    print("=" * 60)
    for ed_str, info in sorted(results.items(), key=lambda x: int(x[0])):
        ed = int(ed_str)
        prova = info.get("prova_url", "???")
        gab = info.get("gabarito_url", "???")
        print(f'    ({ed}, "{prova}", "{gab}"),')


if __name__ == "__main__":
    main()
