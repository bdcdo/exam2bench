"""Modelos Pydantic para extração estruturada de questões de concursos."""

from typing import Any

from pydantic import BaseModel, Field


# --- Modelos internos (usados pelo Gemini para extração) ---


class Alternative(BaseModel):
    """Uma alternativa de resposta (modelo interno de extração)."""

    letra: str = Field(description="Letra da alternativa (A, B, C, etc.)")
    texto: str = Field(description="Texto completo da alternativa")


class Question(BaseModel):
    """Uma questão completa de prova."""

    numero: int = Field(description="Número da questão")
    enunciado: str = Field(description="Texto completo do enunciado da questão")
    alternativas: list[Alternative] = Field(
        default_factory=list, description="Lista de alternativas de resposta"
    )


class PageExtraction(BaseModel):
    """Resultado da extração de uma página de prova."""

    questoes: list[Question] = Field(
        default_factory=list, description="Lista de questões encontradas na página"
    )


class GabaritoAnswer(BaseModel):
    """Uma resposta do gabarito."""

    numero: int = Field(description="Número da questão")
    resposta: str = Field(description="Letra da alternativa correta (A, B, C, D ou E)")


class GabaritoExtraction(BaseModel):
    """Resultado da extração de uma página de gabarito."""

    respostas: list[GabaritoAnswer] = Field(
        default_factory=list, description="Lista de respostas corretas"
    )


# --- Modelo de saída unificado ---


class ExamAlternative(BaseModel):
    """Uma alternativa no formato de saída."""

    letter: str = Field(description="Letra da alternativa (A, B, C, etc.)")
    text: str = Field(description="Texto completo da alternativa")


class ExamQuestion(BaseModel):
    """Questão de prova no formato de saída unificado."""

    id: str = Field(description="ID único: {exam_source}-{question_number:03d}")
    exam_source: str = Field(description="Identificador da prova de origem")
    question_number: int = Field(description="Número da questão na prova")
    statement: str = Field(description="Texto completo do enunciado")
    alternatives: list[ExamAlternative] = Field(
        default_factory=list, description="Alternativas de resposta"
    )
    correct_answer: str | None = Field(
        default=None, description="Letra da resposta correta (None se anulada)"
    )
    nullified: bool = Field(
        default=False, description="True se a questão foi anulada"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadados extensíveis"
    )
