# GraphRAG Experiment: PDF Corpus Downloader

Ferramenta CLI em Python (3.11+) para download sequencial e cortês de documentos PDF a partir de um manifesto estruturado em YAML para um diretório local `corpus/`.

Projetado de acordo com a [Constituição do Projeto](.specify/memory/constitution.md): código mínimo (KISS/YAGNI), interface exclusiva via CLI, sem casos de borda especulativos e foco na proteção do servidor de origem (*polite crawling*).

---

## 🚀 Como Rodar

### 1. Pré-requisitos e Instalação

Certifique-se de ter o Python 3.11+ instalado. Instale a única dependência externa (`PyYAML`):

```bash
pip install -r requirements.txt
```

Ou usando `uv` (opcional):
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

### 2. Executando o Downloader

#### Execução Padrão (Zero Configuração)
Basta rodar o comando abaixo sem parâmetros. Ele usará automaticamente o manifesto fixo [`manifest.yml`](manifest.yml) da raiz do projeto e salvará os PDFs na pasta [`corpus/`](corpus/):

```bash
python3 -m src.download_corpus
```

#### Executando com Manifesto Customizado
Você pode passar o caminho de outro arquivo YAML diretamente como argumento posicional ou via `--manifest`:

```bash
# Como argumento posicional:
python3 -m src.download_corpus outro_manifesto.yml

# Ou via flag:
python3 -m src.download_corpus --manifest outro_manifesto.yml
```

#### Customizando Intervalos e Pastas
Para proteger o servidor ou alterar a pasta de destino:

```bash
python3 -m src.download_corpus \
  --corpus-dir corpus \
  --delay 1.0 \
  --max-retries 3
```

---

## ⚙️ Opções da Linha de Comando (CLI)

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `manifest_path` | Posicional (opcional) | `manifest.yml` | Caminho do arquivo YAML com a lista de documentos. |
| `--manifest` | Opção | `None` | Flag alternativa para indicar o manifesto YAML (sobrescreve o posicional). |
| `--corpus-dir` | Opção | `corpus` | Diretório de destino onde os PDFs são salvos. |
| `--delay` | Float | `1.0` | Intervalo em segundos entre downloads sucessivos para não sobrecarregar o servidor. |
| `--max-retries` | Int | `3` | Tentativas com *exponential backoff* em caso de erros transitórios (429, 5xx, timeouts). |
| `-h`, `--help` | Flag | - | Exibe a mensagem de ajuda e sai. |

---

## 📄 Formato do Manifesto YAML (`manifest.yml`)

O manifesto é uma lista direta (sequência YAML de nível raiz) de documentos, sem necessidade de chaves envoltórias como `items:`:

```yaml
- selection_id: edital-004-2025
  url: https://fapes.es.gov.br/media/Editais/Edital_04-2025.pdf
  title: EDITAL FAPES Nº 04/2025 - UNIVERSAL DE EXTENSÃO III
  group: Editais Encerrados 2025
  source_id: editais-encerrados

- selection_id: resolucao-352-2025
  url: https://fapes.es.gov.br/media/Resolucoes/Resolucao_352.pdf
  title: RESOLUÇÃO Nº 352 - DE 15 DE ABRIL DE 2025
  group: Resoluções CCAF
  source_id: resolucoes
```

- Cada documento é salvo deterministicamente como `<selection_id>.pdf`.

---

## 🛡️ Características Principais

- **Execução Estritamente Sequencial**: Processa um documento por vez, sem concorrência destrutiva contra o servidor.
- **Pausa Educada (*Polite Delay*)**: Intervalo configurável (`--delay`, padrão 1s) entre requisições.
- **Exponential Backoff**: Em erros de *rate limit* (HTTP 429), instabilidade do servidor (5xx) ou timeouts de rede, o sistema dobra o tempo de espera ($delay \times 2^{tentativa}$) por até 3 tentativas antes de pular o item sem travar o lote.
- **Sobrescrita Atômica Idempotente**: Faz o download primeiro em `.tmp` e utiliza `os.replace` atômico para garantir que re-execuções não corrompam arquivos existentes.
- **Preservação de Pasta no Git**: A pasta `corpus/` possui o marcador `.gitkeep` rastreado no Git, enquanto todos os PDFs baixados são automaticamente ignorados pelo `.gitignore`.

---

## 🧪 Rodando os Testes

Para executar a suíte completa de testes unitários (17 testes com mocks de rede, parsing e backoff):

```bash
python3 -m unittest discover tests
```
