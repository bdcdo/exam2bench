"""Extrator de questões e gabaritos usando LangChain + Gemini."""

import time
from dataclasses import dataclass, field
from functools import wraps

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import GabaritoExtraction, PageExtraction

# Modelo Gemini a ser utilizado
MODEL_NAME = "gemini-3-pro-preview"

# Prompts para extração
EXAM_EXTRACTION_PROMPT = """Analise esta imagem de uma página de prova de concurso público brasileiro.

Se a página NÃO contiver questões de prova (é capa, instruções, folha de rascunho, etc.), retorne questoes=[].

Se contiver questões, para CADA questão visível extraia:
- numero: número da questão (inteiro)
- enunciado: texto completo da pergunta incluindo contextos e textos de apoio
- alternativas: lista com cada alternativa contendo letra (A, B, C, D, E) e texto

IMPORTANTE:
- Extraia TODAS as questões visíveis na página
- Preserve o texto exatamente como escrito
- NÃO inclua títulos de seção (ex: "DIREITO PENAL", "DIREITO CIVIL") no enunciado"""

GABARITO_EXTRACTION_PROMPT = """Analise esta imagem do gabarito de uma prova de concurso público brasileiro.

IMPORTANTE: Se houver múltiplos tipos de prova (Tipo 1/A, Tipo 2/B, Tipo 3/C, etc.),
extraia APENAS o gabarito do TIPO 1 ou TIPO A (sempre o primeiro tipo listado).

Para cada questão, extraia:
- numero: número da questão (inteiro)
- resposta: letra da alternativa correta (A, B, C, D ou E)

Extraia TODAS as respostas visíveis na página para o tipo de prova correto.

Se a questão estiver anulada ou sem resposta, NÃO inclua na lista."""


@dataclass
class TokenUsage:
    """Contabilização de tokens usados."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "TokenUsage") -> None:
        """Adiciona os tokens de outro TokenUsage."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens

    def __str__(self) -> str:
        return f"Input: {self.input_tokens:,} | Output: {self.output_tokens:,} | Total: {self.total_tokens:,}"


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator para retry com backoff exponencial."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2**attempt)
                    print(f"  Tentativa {attempt + 1} falhou: {e}. Retry em {delay}s...")
                    time.sleep(delay)

        return wrapper

    return decorator


def create_model() -> ChatGoogleGenerativeAI:
    """Cria instância do modelo Gemini.

    A API key deve estar configurada via variável de ambiente GOOGLE_API_KEY.
    """
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        thinking_level="low",  # Transcrição não precisa de raciocínio profundo
    )


def _create_image_message(prompt: str, image_base64: str) -> HumanMessage:
    """Cria mensagem com imagem para o modelo."""
    return HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "media", "data": image_base64, "mime_type": "image/png"},
        ]
    )


def _extract_token_usage(raw_response) -> TokenUsage:
    """Extrai informações de uso de tokens da resposta raw."""
    usage = TokenUsage()
    if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
        metadata = raw_response.usage_metadata
        usage.input_tokens = getattr(metadata, "input_tokens", 0) or 0
        usage.output_tokens = getattr(metadata, "output_tokens", 0) or 0
        usage.total_tokens = getattr(metadata, "total_tokens", 0) or 0
    return usage


@retry_with_backoff(max_retries=3)
def extract_exam_page(
    model: ChatGoogleGenerativeAI, image_base64: str, debug: bool = False
) -> tuple[PageExtraction, TokenUsage]:
    """Extrai questões de uma página de prova.

    Args:
        model: Instância do modelo Gemini.
        image_base64: Imagem da página em base64.
        debug: Se True, imprime a resposta raw do modelo.

    Returns:
        Tupla (PageExtraction, TokenUsage).
    """
    message = _create_image_message(EXAM_EXTRACTION_PROMPT, image_base64)

    # Usar structured output com include_raw para obter usage_metadata
    structured_model = model.with_structured_output(PageExtraction, include_raw=True)
    response = structured_model.invoke([message])

    result = response["parsed"]
    token_usage = _extract_token_usage(response["raw"])

    # DEBUG: Mostrar o resultado do structured output
    if debug:
        print(f"    [DEBUG] Structured output result:")
        print(f"      questoes count: {len(result.questoes)}")
        if result.questoes:
            for q in result.questoes[:3]:  # Mostra até 3 questões
                enunciado_preview = q.enunciado[:80] if q.enunciado else "(vazio)"
                print(f"      - Q{q.numero}: {enunciado_preview}...")
        print()

    return result, token_usage


@retry_with_backoff(max_retries=3)
def extract_gabarito_page(
    model: ChatGoogleGenerativeAI, image_base64: str
) -> tuple[GabaritoExtraction, TokenUsage]:
    """Extrai respostas de uma página de gabarito.

    Args:
        model: Instância do modelo Gemini.
        image_base64: Imagem da página em base64.

    Returns:
        Tupla (GabaritoExtraction, TokenUsage).
    """
    message = _create_image_message(GABARITO_EXTRACTION_PROMPT, image_base64)

    # Usar structured output com include_raw para obter usage_metadata
    structured_model = model.with_structured_output(GabaritoExtraction, include_raw=True)
    response = structured_model.invoke([message])

    result = response["parsed"]
    token_usage = _extract_token_usage(response["raw"])

    return result, token_usage


def extract_all_exam_pages(
    model: ChatGoogleGenerativeAI, pages: list[tuple[int, str]], debug: bool = False
) -> tuple[list[tuple[int, PageExtraction]], TokenUsage]:
    """Extrai questões de todas as páginas de uma prova.

    Args:
        model: Instância do modelo Gemini.
        pages: Lista de tuplas (número_página, imagem_base64).
        debug: Se True, imprime a resposta raw do modelo para cada página.

    Returns:
        Tupla (lista de (número_página, PageExtraction), TokenUsage total).
    """
    results = []
    total_usage = TokenUsage()

    for page_num, image_base64 in pages:
        print(f"  Processando página {page_num}...")
        try:
            extraction, usage = extract_exam_page(model, image_base64, debug=debug)
            results.append((page_num, extraction))
            total_usage.add(usage)
            if extraction.questoes:
                print(f"    → {len(extraction.questoes)} questão(ões) encontrada(s)")
            else:
                print("    → Página sem questões")
        except Exception as e:
            print(f"    → Erro na página {page_num}: {e}")
            results.append((page_num, PageExtraction(questoes=[])))

    return results, total_usage


def extract_all_gabarito_pages(
    model: ChatGoogleGenerativeAI, pages: list[tuple[int, str]]
) -> tuple[list[GabaritoExtraction], TokenUsage]:
    """Extrai respostas de todas as páginas de um gabarito.

    Args:
        model: Instância do modelo Gemini.
        pages: Lista de tuplas (número_página, imagem_base64).

    Returns:
        Tupla (lista de GabaritoExtraction, TokenUsage total).
    """
    results = []
    total_usage = TokenUsage()

    for page_num, image_base64 in pages:
        print(f"  Processando página {page_num} do gabarito...")
        try:
            extraction, usage = extract_gabarito_page(model, image_base64)
            results.append(extraction)
            total_usage.add(usage)
            print(f"    → {len(extraction.respostas)} resposta(s) encontrada(s)")
        except Exception as e:
            print(f"    → Erro na página {page_num}: {e}")
            results.append(GabaritoExtraction(respostas=[]))

    return results, total_usage
