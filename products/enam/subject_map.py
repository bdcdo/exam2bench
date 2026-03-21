"""Mapa de disciplinas do ENAM por edição.

O ENAM tem 80 questões cobrindo as seguintes áreas:
- Direito Constitucional
- Direito Administrativo
- Direito Processual Civil
- Direito Civil
- Direito Penal
- Direito Empresarial
- Direitos Humanos
- Noções Gerais de Direito
- Formação Humanística

A distribuição exata por questão varia entre edições.
Configure aqui o mapeamento quando disponível.
"""

# Formato: {edição: [(q_inicio, q_fim, area), ...]}
# Exemplo: {"20241": [(1, 16, "CONSTITUCIONAL"), (17, 26, "ADMINISTRATIVO"), ...]}
EDITION_SUBJECT_MAP: dict[str, list[tuple[int, int, str]]] = {}


def get_subject_for_question(edition: str, question_number: int) -> str | None:
    """Retorna a disciplina de uma questão, se o mapa estiver configurado."""
    ranges = EDITION_SUBJECT_MAP.get(edition)
    if not ranges:
        return None
    for start, end, subject in ranges:
        if start <= question_number <= end:
            return subject
    return None
