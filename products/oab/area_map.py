"""Mapeamento de áreas jurídicas da OAB."""

# Lista canônica das 17 áreas jurídicas da OAB
VALID_AREAS = [
    "ETHICS",
    "CONSTITUTIONAL",
    "CIVIL",
    "CIVIL-PROCEDURE",
    "ADMINISTRATIVE",
    "LABOUR",
    "CRIMINAL",
    "CRIMINAL-PROCEDURE",
    "LABOUR-PROCEDURE",
    "TAXES",
    "BUSINESS",
    "HUMAN-RIGHTS",
    "CHILDREN",
    "CONSUMER",
    "INTERNATIONAL",
    "ENVIRONMENTAL",
    "PHILOSOPHY",
]

# Correções de typos conhecidos nos arquivos raw
AREA_CORRECTIONS = {
    "PHILOSHOPY": "PHILOSOPHY",
}

# Mapeamento de áreas para edições 26+ (processadas via PDF).
# Formato: {edition: [(start_question, end_question, area), ...]}
# A OAB segue uma ordem fixa de áreas, mas os ranges podem variar por edição.
# Preencher manualmente uma vez por edição (informação pública nos editais).
EDITION_AREA_MAP: dict[int, list[tuple[int, int, str]]] = {
    # Exemplo (preencher com dados reais):
    # 26: [
    #     (1, 8, "ETHICS"),
    #     (9, 15, "CONSTITUTIONAL"),
    #     ...
    # ],
}


def normalize_area(area: str) -> str:
    """Normaliza o nome de uma área jurídica.

    Args:
        area: Nome da área como encontrado no arquivo raw.

    Returns:
        Nome normalizado ou "NI" (Not Identified) se inválido/vazio.
    """
    area = area.strip()
    if not area:
        return "NI"

    area = AREA_CORRECTIONS.get(area, area)

    if area in VALID_AREAS:
        return area
    return "NI"


def get_area_for_question(edition: int, question_number: int) -> str | None:
    """Retorna a área de uma questão para edições com mapeamento configurado.

    Args:
        edition: Número da edição.
        question_number: Número da questão.

    Returns:
        Nome da área ou None se não há mapeamento.
    """
    ranges = EDITION_AREA_MAP.get(edition)
    if not ranges:
        return None

    for start, end, area in ranges:
        if start <= question_number <= end:
            return area
    return None
