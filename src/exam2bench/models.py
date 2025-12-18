"""Modelos Pydantic para extração estruturada de questões de concursos."""

from pydantic import BaseModel, Field


class Alternative(BaseModel):
    """Uma alternativa de resposta."""

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
