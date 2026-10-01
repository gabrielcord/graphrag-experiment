# GraphRAG Experiment: Pipeline de Ingestão de Corpus

Ferramentas de linha de comando (CLI) em Python (3.11+) para aquisição e pré-processamento de documentos jurídicos/institucionais para experimentos com GraphRAG.

Projetado em estrita conformidade com a [Constituição do Projeto](.specify/memory/constitution.md): código mínimo (KISS/YAGNI), interface exclusiva via CLI, sem casos de borda especulativos e foco na proteção do servidor de origem (*polite crawling*).

---

## 🚀 Como Rodar

### 1. Pré-requisitos e Instalação

Certifique-se de ter o Python 3.11+ instalado. Instale as dependências declaradas em `requirements.txt` (`PyYAML` e `pymupdf4llm`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 2. Download do Corpus de PDFs (`src.download_corpus`)

Faz o download sequencial e cortês dos PDFs listados em [`manifest.yml`](manifest.yml) para o diretório local `corpus/` (ignorado no Git via `.gitignore`, preservando `corpus/.gitkeep`).

#### Execução Padrão (Zero Configuração)
```bash
python3 -m src.download_corpus
```

#### Customizando Parâmetros
```bash
python3 -m src.download_corpus \
  --manifest manifest.yml \
  --corpus-dir corpus \
  --delay 1.0 \
  --max-retries 3
```

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `manifest_path` | Posicional (opcional) | `manifest.yml` | Caminho do arquivo YAML com a lista de documentos. |
| `--manifest`, `-m` | Opção | `None` | Flag alternativa para o manifesto (sobrescreve o posicional). |
| `--corpus-dir` | Opção | `corpus` | Diretório onde os arquivos PDF são armazenados. |
| `--delay` | Float | `1.0` | Intervalo em segundos entre downloads sucessivos. |
| `--max-retries` | Int | `3` | Tentativas com *exponential backoff* em caso de erros transitórios (429, 5xx, timeouts). |

---

### 3. Extração de PDF para Markdown (`src.parse_corpus`)

Lê os PDFs baixados em `corpus/` sequencialmente (um a um) sob controle de [`manifest.yml`](manifest.yml), converte o conteúdo estrutural de cada PDF para Markdown puro usando **PyMuPDF4LLM** e persiste os arquivos em `corpus_md/`.

Diferente da pasta de PDFs binários, a pasta [`corpus_md/`](corpus_md/) é **versionada no Git** (não ignorada pelo `.gitignore`), permitindo acesso direto aos textos estruturados sem reprocessar arquivos binários.

#### Execução Padrão (Zero Configuração)
```bash
python3 -m src.parse_corpus
```

#### Customizando Parâmetros
```bash
python3 -m src.parse_corpus \
  --manifest manifest.yml \
  --corpus-dir corpus \
  --output-dir corpus_md
```

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `manifest` | Posicional (opcional) | `manifest.yml` | Caminho do manifesto YAML de documentos. |
| `--manifest`, `-m` | Opção | `None` | Flag alternativa para indicar o manifesto. |
| `--corpus-dir`, `-c` | Opção | `corpus` | Diretório de origem contendo os PDFs baixados. |
| `--output-dir`, `-o` | Opção | `corpus_md` | Diretório de destino para os arquivos Markdown (versionado no Git). |

---

## 📄 Formato do Manifesto YAML (`manifest.yml`)

O manifesto é uma sequência YAML de nível raiz contendo os metadados canônicos dos documentos:

```yaml
- selection_id: edital-004-2025
  url: https://fapes.es.gov.br/media/Editais/Edital_04-2025_-_Universal_Extens%C3%A3o-1.pdf
  title: EDITAL FAPES Nº 04/2025 - UNIVERSAL DE EXTENSÃO III
  group: Editais Encerrados 2025
  source_id: editais-encerrados

- selection_id: resolucao-352-2025
  url: https://fapes.es.gov.br/media/Resolu%C3%A7%C3%B5es/Resolu%C3%A7%C3%A3o_CCAF_n%C2%BA_352-2025_-_Reajuste_de_Bolsas.pdf
  title: RESOLUÇÃO Nº 352 - DE 15 DE ABRIL DE 2025
  group: Resoluções CCAF
  source_id: resolucoes
```

- Cada PDF de entrada é resolvido como `<corpus-dir>/<selection_id>.pdf`.
- Cada arquivo Markdown de saída é salvo deterministicamente como `<output-dir>/<selection_id>.md`.

---

## 🛡️ Princípios e Garantias do Pipeline

1. **Separação de Armazenamento no Git**:
   - `corpus/`: Arquivos binários PDF grandes e transitórios — ignorados no Git via `.gitignore`, com estrutura garantida por `corpus/.gitkeep`.
   - `corpus_md/`: Arquivos de texto Markdown limpos e leves gerados por `pymupdf4llm` — **totalmente versionados e rastreados pelo Git**.
2. **Processamento Sequencial Estrito**: Tanto o download quanto o parsing executam documento a documento, garantindo previsibilidade de recursos e observabilidade em tempo real.
3. **Resiliência e Idempotência**:
   - Falhas em arquivos específicos (PDF ausente ou corrompido) são reportadas em `stderr` sem abortar o processamento do lote.
   - Re-execuções sobrescrevem arquivos existentes de forma idempotente e limpa.

---

## 🧪 Rodando os Testes

Para executar a suíte completa de testes automatizados:

```bash
python3 -m unittest discover tests
```
