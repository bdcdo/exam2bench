# exam2bench

Extrator de questões de provas de concursos públicos brasileiros para avaliação de LLMs.

Transforma PDFs de provas e gabaritos em CSVs estruturados, permitindo criar benchmarks para avaliar modelos de linguagem.

## Funcionalidades

- Converte PDFs de provas em imagens de alta qualidade (300 DPI)
- Utiliza Google Gemini para extrair questões de forma estruturada
- Lida com páginas pré/pós-textuais automaticamente
- Extrai gabaritos de múltiplos tipos de prova (usa o Tipo 1/A)
- Combina questões com respostas corretas
- Exporta para CSV em formato padronizado
- Contabiliza tokens utilizados na extração

## Instalação

Requer Python 3.11+.

```bash
# Clone o repositório
git clone https://github.com/bdcdo/exam2bench.git
cd exam2bench

# Instale as dependências com uv
uv sync
```

## Configuração

Configure sua API key do Google AI:

```bash
export GOOGLE_API_KEY="sua-api-key"
```

## Uso

### Convenção de Nomes dos PDFs

Os PDFs devem seguir a convenção de nomes:
- Prova: `nome-prova.pdf`
- Gabarito: `nome-gabarito.pdf`

Exemplo:
```
exams/
├── vunesp-2025-tj-sp-prova.pdf
├── vunesp-2025-tj-sp-gabarito.pdf
├── cespe-2024-pf-prova.pdf
└── cespe-2024-pf-gabarito.pdf
```

### Executando

Coloque os PDFs na pasta `exams/` e execute:

```bash
uv run exam2bench
```

Para modo debug (mostra detalhes da extração):

```bash
uv run exam2bench --debug
```

Os CSVs serão gerados na pasta `output/`.

### Saída

O CSV gerado contém as seguintes colunas:

| Coluna | Descrição |
|--------|-----------|
| `numero` | Número da questão |
| `pergunta` | Texto completo do enunciado |
| `alternativas` | Alternativas em JSON: `[{"letra": "A", "texto": "..."}]` |
| `resposta_correta` | Letra da resposta correta (A, B, C, D ou E) |
| `prova_origem` | Identificador da prova |

Exemplo:
```csv
numero,pergunta,alternativas,resposta_correta,prova_origem
1,"Qual é a capital do Brasil?","[{""letra"": ""A"", ""texto"": ""Rio de Janeiro""}, {""letra"": ""B"", ""texto"": ""Brasília""}]",B,vunesp-2025-tj-sp
```

Ao final da execução, é exibido um resumo com o total de tokens utilizados:
```
Tokens utilizados:
  Input: 1,234,567 | Output: 12,345 | Total: 1,246,912
```

## Estrutura do Projeto

```
exam2bench/
├── src/
│   └── exam2bench/
│       ├── __init__.py
│       ├── main.py           # CLI e orquestração
│       ├── models.py         # Modelos Pydantic
│       ├── pdf_processor.py  # PDF → imagens
│       ├── extractor.py      # LangChain + Gemini
│       ├── merger.py         # Merge questões + gabarito
│       └── exporter.py       # Exportação CSV
├── tests/
│   ├── test_pdf_processor.py
│   ├── test_merger.py
│   └── test_exporter.py
├── exams/                    # PDFs de entrada
├── output/                   # CSVs gerados
└── pyproject.toml
```

## Testes

```bash
uv run pytest -v
```

## Tecnologias

- [LangChain](https://python.langchain.com/) - Framework para LLMs
- [Google Gemini](https://ai.google.dev/) - Modelo de visão/linguagem
- [PyMuPDF](https://pymupdf.readthedocs.io/) - Processamento de PDFs
- [Pydantic](https://docs.pydantic.dev/) - Validação de dados estruturados
- [Pandas](https://pandas.pydata.org/) - Manipulação de dados

## Licença

MIT
