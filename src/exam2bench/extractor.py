"""Extrator de questões e gabaritos usando LangChain + Gemini."""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import GabaritoExtraction, PageExtraction
from . import ui

# Modelo Gemini a ser utilizado
MODEL_NAME = "gemini-3-pro-preview"

# Preços por milhão de tokens (USD)
MODEL_PRICING = {
    "pro": {"input": 2.00, "output": 12.00},
    "flash": {"input": 0.50, "output": 3.00},
}

# Prompts para extração
EXAM_EXTRACTION_PROMPT = """Analise esta imagem de uma página de prova de concurso público brasileiro.

Se a página NÃO contiver questões de prova (é capa, instruções, folha de rascunho, etc.), retorne questoes=[].

Se contiver questões, para CADA questão visível extraia:
- numero: número da questão (inteiro)
- enunciado: texto completo da pergunta incluindo contextos e textos de apoio
- alternativas: lista com cada alternativa contendo letra (A, B, C, D, E) e texto

IMPORTANTE:
- Extraia TODAS as questões visíveis na página
- TRANSCREVA LITERALMENTE o texto, sem corrigir erros ortográficos, gramaticais ou de digitação
- O texto pode conter trechos em latim misturados com português - transcreva exatamente como está
- NÃO altere, corrija ou "melhore" o texto de forma alguma
- NÃO inclua títulos de seção (ex: "DIREITO PENAL", "DIREITO CIVIL") no enunciado"""

GABARITO_EXTRACTION_PROMPT = """Analise esta imagem do gabarito de uma prova de concurso público brasileiro.

IMPORTANTE: Se houver múltiplos tipos de prova (Tipo 1/A, Tipo 2/B, Tipo 3/C, etc.),
extraia APENAS o gabarito do TIPO 1 ou TIPO A (sempre o primeiro tipo listado).

Para cada questão, extraia:
- numero: número da questão (inteiro)
- resposta: letra da alternativa correta (A, B, C, D ou E)

Extraia TODAS as respostas visíveis na página para o tipo de prova correto.

Se a questão estiver anulada ou sem resposta, NÃO inclua na lista."""


def _get_model_type(model_name: str) -> str:
    """Detecta o tipo do modelo (pro ou flash) pelo nome."""
    if "flash" in model_name.lower():
        return "flash"
    return "pro"


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

    def calculate_cost(self, model_name: str = MODEL_NAME) -> float:
        """Calcula o custo em USD baseado nos tokens usados.

        Args:
            model_name: Nome do modelo para determinar preços.

        Returns:
            Custo total em USD.
        """
        model_type = _get_model_type(model_name)
        pricing = MODEL_PRICING[model_type]

        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def __str__(self) -> str:
        cost = self.calculate_cost()
        return (
            f"Input: {self.input_tokens:,} | Output: {self.output_tokens:,} | "
            f"Total: {self.total_tokens:,} | Custo: ${cost:.4f}"
        )


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator para retry com backoff exponencial."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        print(f"  Tentativa {attempt + 1} OK")
                    return result
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2**attempt)
                    print(f"  Tentativa {attempt + 1} falhou: {e}. Retry em {delay}s...")
                    time.sleep(delay)

        return wrapper

    return decorator


def create_model(model_name: str = MODEL_NAME) -> ChatGoogleGenerativeAI:
    """Cria instância do modelo Gemini.

    Args:
        model_name: Nome do modelo Gemini a utilizar.

    A API key deve estar configurada via variável de ambiente GOOGLE_API_KEY.
    """
    return ChatGoogleGenerativeAI(
        model=model_name,
        thinking_level="low",
        safety_settings={
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        },
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
        # Pode ser dict ou objeto com atributos
        if isinstance(metadata, dict):
            usage.input_tokens = metadata.get("input_tokens", 0) or 0
            usage.output_tokens = metadata.get("output_tokens", 0) or 0
            usage.total_tokens = metadata.get("total_tokens", 0) or 0
        else:
            usage.input_tokens = getattr(metadata, "input_tokens", 0) or 0
            usage.output_tokens = getattr(metadata, "output_tokens", 0) or 0
            usage.total_tokens = getattr(metadata, "total_tokens", 0) or 0
    return usage


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
    if result is None:
        raise ValueError("Structured output retornou None")
    token_usage = _extract_token_usage(response["raw"])

    # DEBUG: Mostrar o resultado do structured output
    if debug:
        print(f"    [DEBUG] Structured output result:")
        print(f"      questoes count: {len(result.questoes)}")
        if result.questoes:
            for q in result.questoes[:3]:  # Mostra até 3 questões
                enunciado_preview = q.enunciado[:80] if q.enunciado else "(vazio)"
                print(f"      - Q{q.numero}: {enunciado_preview}...")
        print(f"      tokens: {token_usage}")
        print()

    return result, token_usage


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
    if result is None:
        raise ValueError("Structured output retornou None")
    token_usage = _extract_token_usage(response["raw"])

    return result, token_usage


def _load_page_cache(cache_dir: Path, page_num: int, model_class: type) -> object | None:
    """Tenta carregar extração de página do cache."""
    cache_file = cache_dir / f"page-{page_num:02d}.json"
    if cache_file.exists():
        return model_class.model_validate_json(cache_file.read_text(encoding="utf-8"))
    return None


def _save_page_cache(cache_dir: Path, page_num: int, extraction: object) -> None:
    """Salva extração de página no cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"page-{page_num:02d}.json"
    cache_file.write_text(extraction.model_dump_json(), encoding="utf-8")


def extract_all_exam_pages(
    pages: list[tuple[int, str]],
    debug: bool = False,
    max_workers: int = 4,
    model_name: str = MODEL_NAME,
    on_page_done: Callable[[int, int], None] | None = None,
    cache_dir: Path | None = None,
) -> tuple[list[tuple[int, PageExtraction]], TokenUsage, list[int]]:
    """Extrai questões de todas as páginas de uma prova.

    Args:
        pages: Lista de tuplas (número_página, imagem_base64).
        debug: Se True, imprime a resposta raw do modelo para cada página.
        max_workers: Número de threads concorrentes para chamadas à API.
        model_name: Nome do modelo Gemini a utilizar.
        on_page_done: Callback (page_num, num_questions) chamado após cada página.
        cache_dir: Diretório para cache por página. Se None, sem cache.

    Returns:
        Tupla (extractions, usage, failed_pages).
    """
    total_usage = TokenUsage()
    results: list[tuple[int, PageExtraction]] = []
    failed_pages: list[int] = []

    # Carregar páginas cacheadas
    pages_to_process: list[tuple[int, str]] = []
    for page_num, image_base64 in pages:
        if cache_dir:
            cached = _load_page_cache(cache_dir, page_num, PageExtraction)
            if cached is not None:
                results.append((page_num, cached))
                if on_page_done:
                    on_page_done(page_num, len(cached.questoes))
                continue
        pages_to_process.append((page_num, image_base64))

    if not pages_to_process:
        results.sort(key=lambda x: x[0])
        return results, total_usage, failed_pages

    def _process_page(page_num: int, image_base64: str) -> tuple[int, PageExtraction, TokenUsage]:
        model = create_model(model_name)
        last_error = None
        for attempt in range(3):
            try:
                extraction, usage = extract_exam_page(model, image_base64, debug=debug)
                if attempt > 0:
                    ui.info(f"  Pg {page_num}: OK (tentativa {attempt + 1})")
                if on_page_done:
                    on_page_done(page_num, len(extraction.questoes))
                if cache_dir:
                    _save_page_cache(cache_dir, page_num, extraction)
                return page_num, extraction, usage
            except Exception as e:
                last_error = e
                if attempt < 2:
                    delay = 1.0 * (2 ** attempt)
                    time.sleep(delay)
        # Todas as tentativas falharam
        ui.warn(f"  Pg {page_num}: falhou 3x — {last_error}")
        raise last_error  # type: ignore[misc]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_page, page_num, img): page_num
            for page_num, img in pages_to_process
        }
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                pn, extraction, usage = future.result()
                results.append((pn, extraction))
                total_usage.add(usage)
            except Exception:
                failed_pages.append(page_num)
                if on_page_done:
                    on_page_done(page_num, 0)
                results.append((page_num, PageExtraction(questoes=[])))

    results.sort(key=lambda x: x[0])
    failed_pages.sort()
    return results, total_usage, failed_pages


def extract_all_gabarito_pages(
    pages: list[tuple[int, str]],
    max_workers: int = 4,
    model_name: str = MODEL_NAME,
    on_page_done: Callable[[int, int], None] | None = None,
    cache_dir: Path | None = None,
) -> tuple[list[GabaritoExtraction], TokenUsage, list[int]]:
    """Extrai respostas de todas as páginas de um gabarito.

    Args:
        pages: Lista de tuplas (número_página, imagem_base64).
        max_workers: Número de threads concorrentes para chamadas à API.
        model_name: Nome do modelo Gemini a utilizar.
        on_page_done: Callback (page_num, num_answers) chamado após cada página.
        cache_dir: Diretório para cache por página. Se None, sem cache.

    Returns:
        Tupla (extractions, usage, failed_pages).
    """
    total_usage = TokenUsage()
    results: list[tuple[int, GabaritoExtraction]] = []
    failed_pages: list[int] = []

    # Carregar páginas cacheadas
    pages_to_process: list[tuple[int, str]] = []
    for page_num, image_base64 in pages:
        if cache_dir:
            cached = _load_page_cache(cache_dir, page_num, GabaritoExtraction)
            if cached is not None:
                results.append((page_num, cached))
                if on_page_done:
                    on_page_done(page_num, len(cached.respostas))
                continue
        pages_to_process.append((page_num, image_base64))

    if not pages_to_process:
        results.sort(key=lambda x: x[0])
        return [ext for _, ext in results], total_usage, failed_pages

    def _process_page(page_num: int, image_base64: str) -> tuple[int, GabaritoExtraction, TokenUsage]:
        model = create_model(model_name)
        last_error = None
        for attempt in range(3):
            try:
                extraction, usage = extract_gabarito_page(model, image_base64)
                if attempt > 0:
                    ui.info(f"  Gabarito pg {page_num}: OK (tentativa {attempt + 1})")
                if on_page_done:
                    on_page_done(page_num, len(extraction.respostas))
                if cache_dir:
                    _save_page_cache(cache_dir, page_num, extraction)
                return page_num, extraction, usage
            except Exception as e:
                last_error = e
                if attempt < 2:
                    delay = 1.0 * (2 ** attempt)
                    time.sleep(delay)
        ui.warn(f"  Gabarito pg {page_num}: falhou 3x — {last_error}")
        raise last_error  # type: ignore[misc]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_page, page_num, img): page_num
            for page_num, img in pages_to_process
        }
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                pn, extraction, usage = future.result()
                results.append((pn, extraction))
                total_usage.add(usage)
            except Exception:
                failed_pages.append(page_num)
                if on_page_done:
                    on_page_done(page_num, 0)
                results.append((page_num, GabaritoExtraction(respostas=[])))

    results.sort(key=lambda x: x[0])
    failed_pages.sort()
    return [ext for _, ext in results], total_usage, failed_pages
