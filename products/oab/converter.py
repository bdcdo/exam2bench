"""Conversor de arquivos .txt raw (legal-nlp/oab-exams) para ExamQuestion."""

import re
from pathlib import Path

from exam2bench.models import ExamAlternative, ExamQuestion

from .area_map import normalize_area

# Regex para separar questões: "Questão N" opcionalmente seguido de "NULL"
QUESTION_SPLIT_RE = re.compile(r"(?=^Questão\s+\d+)", re.MULTILINE)
QUESTION_HEADER_RE = re.compile(r"^Questão\s+(\d+)\s*(NULL)?\s*$", re.MULTILINE)
AREA_RE = re.compile(r"^AREA[ \t]*(.*?)[ \t]*$", re.MULTILINE)
OPTIONS_RE = re.compile(r"^OPTIONS\s*$", re.MULTILINE)
ALT_RE = re.compile(
    r"^([A-E])(:CORRECT)?\)\s*(.*)",
    re.MULTILINE,
)


def _parse_alternatives(options_text: str) -> tuple[list[ExamAlternative], str | None]:
    """Parse das alternativas a partir do bloco OPTIONS.

    Returns:
        Tupla (lista de alternativas, letra da resposta correta ou None).
    """
    alternatives = []
    correct = None

    # Encontra todas as alternativas
    matches = list(ALT_RE.finditer(options_text))

    for i, match in enumerate(matches):
        letter = match.group(1)
        is_correct = match.group(2) is not None  # ":CORRECT"
        # Texto vai até o início da próxima alternativa ou fim do bloco
        start = match.start(3)
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(options_text)

        text = options_text[start:end].strip()
        # Limpa quebras de linha internas, preservando espaço
        text = re.sub(r"\s*\n\s*", " ", text).strip()

        alternatives.append(ExamAlternative(letter=letter, text=text))
        if is_correct:
            correct = letter

    return alternatives, correct


def parse_raw_oab_file(file_path: Path) -> list[ExamQuestion]:
    """Converte um arquivo .txt raw do OAB para lista de ExamQuestion.

    Args:
        file_path: Caminho do arquivo .txt (ex: 2010-01.txt).

    Returns:
        Lista de ExamQuestion extraídas do arquivo.
    """
    content = file_path.read_text(encoding="utf-8")

    # Extrair edition e year do nome do arquivo (ex: 2010-01.txt)
    stem = file_path.stem  # "2010-01"
    parts = stem.split("-")
    year = int(parts[0])
    edition = int(parts[1].rstrip("a"))  # Remove sufixo "a" de "06a", "20a"

    exam_source = f"oab-{edition}"

    # Separar blocos de questões
    blocks = QUESTION_SPLIT_RE.split(content)

    questions = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Parse do header
        header_match = QUESTION_HEADER_RE.match(block)
        if not header_match:
            continue

        question_number = int(header_match.group(1))
        is_nullified = header_match.group(2) is not None  # "NULL"

        # Extrair área
        area_match = AREA_RE.search(block)
        area = normalize_area(area_match.group(1)) if area_match else "NI"

        # Separar enunciado e alternativas pelo marcador OPTIONS
        options_split = OPTIONS_RE.split(block)
        if len(options_split) < 2:
            continue

        # Enunciado: entre AREA e OPTIONS
        pre_options = options_split[0]
        # Remove header e AREA line do enunciado
        statement_text = pre_options
        if area_match:
            statement_text = pre_options[area_match.end():]
        else:
            statement_text = pre_options[header_match.end():]

        statement = re.sub(r"\s*\n\s*", " ", statement_text).strip()
        if not statement:
            continue

        # Parse das alternativas
        options_text = options_split[1]
        alternatives, correct_from_tag = _parse_alternatives(options_text)

        # Determinar resposta correta
        correct_answer = None if is_nullified else correct_from_tag

        questions.append(
            ExamQuestion(
                id=f"{exam_source}-{question_number:03d}",
                exam_source=exam_source,
                question_number=question_number,
                statement=statement,
                alternatives=alternatives,
                correct_answer=correct_answer,
                nullified=is_nullified,
                metadata={
                    "area": area,
                    "edition": edition,
                    "year": year,
                    "source_format": "raw_text",
                },
            )
        )

    return questions
