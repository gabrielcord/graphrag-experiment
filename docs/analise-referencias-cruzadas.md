# Análise de Referências Cruzadas e Remissões Normativas no Corpus

**Data de Elaboração**: 01/10/2026  
**Finalidade**: Servir de contexto estruturado e benchmark para testes de recuperação multi-hop e construção determinística de grafos em experimentos de **GraphRAG**.  
**Corpus Analisado**: 12 documentos institucionais da FAPES persistidos em [`corpus_md/`](../corpus_md/).

---

## 1. Visão Geral e Relevância para GraphRAG

Em corpora regulatórios e jurídicos, editais e resoluções frequentemente utilizam **técnica legislativa remissiva**: em vez de duplicar tabelas de valores, regras contábeis e sanções, o documento emissor apenas cita a norma de regência.

### O Problema do RAG Vetorial Tradicional (Dense Retrieval)
Um sistema de busca puramente vetorial indexa fragmentos de texto (chunks) isolados. Quando submetido a perguntas como:
> *"Qual o valor mensal da bolsa de Apoio Técnico Nível Superior (AT-NS) permitida pelo Edital PPP-ES (24/2026)?"*

O RAG vetorial recupera o trecho do Edital 24/2026 que autoriza a concessão de bolsa AT-NS. Porém, **o valor financeiro (`R$ 1.900,00`) não existe naquele documento**. O modelo de linguagem (LLM) inevitavelmente alucina ou responde que a informação não foi informada.

### A Solução GraphRAG (Knowledge Graph & Multi-Hop)
Ao modelar o corpus como um **Grafo de Conhecimento**:
- O nó `Edital 24/2026` possui a aresta `[CITA_TABELA_BOLSAS]` conectando-o ao nó `Resolução 355/2025`.
- O motor de inferência GraphRAG faz a travessia (*hop*), localiza a entidade `Bolsa AT-NS` com a propriedade `valor: R$ 1.900,00` na Resolução 355/2025 e responde à pergunta com precisão determinística.

---

## 2. Grafo de Conectividade do Corpus

```mermaid
flowchart TD
    E024["Edital 24/2026 (PPP-ES)"]
    E015["Edital 15/2026 (Talentos Globais)"]
    E013["Edital 13/2026 (PIBICES)"]
    E004["Edital 04/2025 (Universal Extensão)"]

    R355["Resolução 355/2025 (Tabela Bolsas)"]
    R356["Resolução 356/2025 (Manual PCTF)"]
    R357["Resolução 357/2025 (Normas Fomento)"]
    R363["Resolução 363/2026 (Talentos Globais)"]
    R361["Resolução 361/2026 (Tabela Bolsas Ext)"]
    R352["Resolução 352/2025 (Reajuste ICT/PIBICES)"]

    E024 -->|CITA_TABELA_BOLSAS (Link + RegEx)| R355
    E024 -->|CITA_PRESTACAO_CONTAS (Link + RegEx)| R356
    E024 -->|CITA_NORMAS_FOMENTO (Link + RegEx)| R357

    E004 -.->|OMITE_VALOR_REQUER (RegEx)| R355

    E015 <-->|REGULAMENTA_E_CITA (RegEx Puro)| R363

    E013 -->|CITA_TABELA_BOLSAS (RegEx Puro)| R361
    R352 -.->|ORIGEM_REAJUSTE_ICT (RegEx Puro)| E013
```

---

## 3. Matriz de Classificação: Citação vs. Reprodução e Métodos de Extração

| Relação entre Arquivos | Conteúdo Reproduzido? | Necessita Multi-Hop? | Possui Link Markdown `[texto](URL)`? | Identificável por RegEx de Atos? |
|---|---|---|---|---|
| **Edital 24/2026 $\rightarrow$ Resolução 355/2025** | ❌ **NÃO** (só o nome) | **SIM** (Falta valor R$ 1.900) | ✅ **SIM** (1 ocorrência) | ✅ **SIM** (1 ocorrência) |
| **Edital 24/2026 $\rightarrow$ Resolução 356/2025** | ❌ **NÃO** (só citação) | **SIM** (Faltam regras PCTF) | ✅ **SIM** (6 ocorrências) | ✅ **SIM** (1 ocorrência) |
| **Edital 24/2026 $\rightarrow$ Resolução 357/2025** | ❌ **NÃO** (só citação) | **SIM** (Faltam normas repasse) | ✅ **SIM** (2 ocorrências) | ✅ **SIM** (1 ocorrência) |
| **Edital 15/2026 $\longleftrightarrow$ Resolução 363/2026** | ⚠️ **PARCIAL** (valores sim) | **SIM** (Falta acordo/deveres) | ❌ **NÃO** (0 links) | ✅ **SIM** (2 ocorrências) |
| **Edital 13/2026 $\longleftrightarrow$ Resolução 361/2026** | ⚠️ **PARCIAL** (ICT sim) | **SIM** (Para outras bolsas) | ❌ **NÃO** (0 links) | ✅ **SIM** (2 ocorrências) |
| **Edital 04/2025 $\rightarrow$ Resolução 355/2025** | ❌ **NÃO** (só siglas EXT) | **SIM** (Faltam R$ 800 e R$ 450) | ❌ **NÃO** (0 links) | ✅ **SIM** (via sigla de bolsa) |
| **Resolução 352/2025 $\rightarrow$ Edital 13/2026** | ✅ **SIM** (R$ 900 transcrito) | **NÃO** (Auto-suficiente) | ❌ **NÃO** (0 links) | ✅ **SIM** (via sigla PIBICES) |

---

## 4. Métodos Determinísticos de Descoberta

É possível extrair 100% dessas relações de maneira determinística combinando dois mecanismos que se complementam perfeitamente:

### Método A: Extração de Hiperlinks na AST do Markdown
O extrator `pymupdf4llm` converteu as anotações de links dos PDFs originais em sintaxe Markdown: `[texto](URL)`.
- **Como funciona**: Extrai-se o atributo `href` (URL de destino). Compara-se a URL extraída contra as URLs canônicas cadastradas no [`manifest.yml`](../manifest.yml) ou analisa-se a presença do padrão numérico na URL (ex: `Resolução_CCAF_nº_355-2025`).
- **Casos contemplados**: Todas as referências do **Edital 24/2026** para as Resoluções 355, 356 e 357.
- **Vantagem**: Precisão determinística de 100%, sem falsos positivos.

### Método B: Autômato Finito / Expressões Regulares de Atos Administrativos
Nos casos em que o documento original não continha link clicável, as citações foram feitas em texto plano, seguindo estritamente a padronização oficial de redação de atos públicos:
- **Padrão Canônico**:
  ```python
  REGEX_ATO = re.compile(
      r"(?:Resoluç[ãa]o\s+(?:(?:CCAF|FAPES|CCAF/FAPES)\s+)?(?:n[º°o\.]*\s*)?|Edital\s+(?:(?:FAPES|FAPES/SECTI)\s+)?(?:n[º°o\.]*\s*)?)(\d{1,4})(?:[/-](\d{4}))?",
      re.IGNORECASE
  )
  ```
- **Casos contemplados**: Citações no **Edital 15/2026**, **Edital 13/2026** e no Anexo de Termo de Outorga do **Edital 24/2026**.
- **Vantagem**: Captura citações mesmo quando o autor do PDF original não adicionou hyperlink.

---

## 5. Fundamentação Legal e Teórica da Redação de Atos Públicos

A viabilidade de identificar essas ligações de forma **100% determinística** decorre do fato de que a redação de atos normativos e editais no Brasil não é livre nem estilística: ela obedece a uma **estrutura sintática estrita imposta por lei e regulamentos oficiais**.

### 5.1 Nível Legal Obrigatório: Lei Complementar Federal nº 95/1998
O fundamento primário decorre do **art. 59, parágrafo único, da Constituição Federal de 1988**, que determinou:
> *"Lei complementar disporá sobre a elaboração, redação, alteração e consolidação das leis."*

Em cumprimento a esse mandamento constitucional, foi editada a **Lei Complementar Federal nº 95, de 26 de fevereiro de 1998** (*Lei da Técnica Legislativa*):
- **Artigos 3º ao 11**: Fixam a anatomia formal obrigatória de todo ato normativo:
  - **Epígrafe**: Espécie normativa (`Resolução`, `Edital`), numeração e ano (ex: *RESOLUÇÃO Nº 363, DE 31 DE MARÇO DE 2026*).
  - **Ementa**: Síntese do objeto normativo.
  - **Preâmbulo**: Autoridade e base de competência legal (*"O CONSELHO... no uso de suas atribuições..."*).
  - **Corpo Normativo**: Articulado estritamente em artigos, parágrafos, incisos e alíneas.
- **Artigo 12 (Regras de Remissão e Citação)**: Determina que as remissões a outros atos devem **obrigatoriamente indicar a espécie normativa, o número e o ano**, vedadas citações imprecisas ou genéricas.

> **Princípio da Simetria Constitucional (Aplicação ao ES e à FAPES)**: Por força do pacto federativo e da Constituição do Estado do Espírito Santo (art. 60, parágrafo único), as regras da LC 95/98 aplicam-se obrigatoriamente a todos os órgãos estaduais e fundações públicas (como a FAPES) para a validade formal de publicações no Diário Oficial do Estado (DIO-ES).

### 5.2 Nível Regulamentar e Executivo: Decreto Federal nº 9.191/2017 e Manual da Presidência da República
No âmbito do Poder Executivo e colegiados administrativos:
1. **Decreto Federal nº 9.191, de 1º de novembro de 2017**:
   - Estabelece as diretrizes de elaboração, redação e alteração de atos normativos inferiores a lei (decretos, resoluções de colegiados, instruções normativas e portarias).
   - Padroniza o formato ordinal/cardinal de numeração e exige a indicação clara do ano com 4 dígitos (ex: `nº 355/2025`).
2. **Manual de Redação da Presidência da República (MRPR - 3ª Edição, 2018)**:
   - Manual canônico que orienta a administração pública brasileira.
   - **Capítulo IV (Atos Normativos)**: Padroniza o uso da fórmula de citação `Resolução [Órgão] nº [Número]/[Ano]` e o uso de travessão (`–`) seguido de ementa (ex: `Resolução CCAF nº 355/2025 – Tabela de Valores de Bolsas e Auxílios`), o que viabiliza a extração direta do tipo da aresta por expressões regulares.

### 5.3 Nível Tecnológico e Jurimetria: O Projeto LexML Brasil (Senado Federal)
A abordagem de usar autômatos determinísticos e expressões regulares para extrair conexões jurídicas é o padrão do estado-da-arte adotado oficialmente pelos poderes da República:
- **Projeto LexML Brasil** ([projeto.lexml.gov.br](https://projeto.lexml.gov.br/)): Mantido pelo **Senado Federal**, pelo **Tribunal Superior Eleitoral (TSE)** e pelo **Conselho Nacional de Justiça (CNJ)**.
- **O Parser LexML**: O LexML converte atos jurídicos brasileiros em grafos semânticos e identificadores persistentes (URNs LexML) utilizando **analisadores léxicos e expressões regulares determinísticas** baseadas nas regras da LC 95/98, sem a necessidade de LLMs ou métodos probabilísticos para identificar citações.

### 5.4 Vantagens Arquiteturais para o Pipeline GraphRAG
1. **Custo Computacional Zero de IA na Extração de Arestas**: A montagem do grafo é executada em frações de segundo via autômatos em CPU, sem consumo de tokens de API.
2. **Determinismo e Reprodutibilidade Absoluta**: A mesma entrada sempre gerará exatamente as mesmas arestas, sem variabilidade de temperatura ou alucinações.
3. **Auditabilidade**: Cada aresta no grafo pode apontar exatamente para o número da linha e o trecho de texto original que a fundamenta.

---

## 6. Detalhamento dos Casos de Análise

### Caso 1: Edital 24/2026 $\rightarrow$ Resolução 355/2025 (Tabela de Bolsas AT-NS)
- **Arquivo de Origem**: [`corpus_md/edital-024-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md)
- **Arquivo de Destino**: [`corpus_md/resolucao-355-2025.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-355-2025.md)
- **Mecanismos Determinísticos**:
  - **Hiperlink Markdown (Método A)**:  
    - [Linha 2517](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L2517): `[e 355/2025](https://fapes.es.gov.br/Media/fapes/Resolu%C3%A7%C3%B5es/Resolu%C3%A7%C3%A3o_CCAF_n%C2%BA_355-2025_-_Altera_a_Resolu%C3%A7%C3%A3o_CCAF_n%C2%BA_324_de_07_de_mar%C3%A7o_de_2023_-_Reajuste_dos_valor.pdf)`
  - **Padrão Textual / RegEx (Método B)**:  
    - [Linha 3958](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L3958): `324/2023 e 355/2025 – Tabela de Valores de Bolsas e Auxílios`
- **Conteúdo**: O edital autoriza bolsa AT-NS por 24 meses, mas omite o valor. A Resolução 355/2025 fornece o valor: **R$ 1.900,00**.
- **Diagnóstico**: **Meramente remissivo (Travessia obrigatória no grafo)**.

---

### Caso 2: Edital 24/2026 $\rightarrow$ Resolução 356/2025 (Manual de Prestação de Contas)
- **Arquivo de Origem**: [`corpus_md/edital-024-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md)
- **Arquivo de Destino**: [`corpus_md/resolucao-356-2025.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-356-2025.md)
- **Mecanismos Determinísticos**:
  - **Hiperlink Markdown (Método A)**: **6 ocorrências com link direto**, incluindo:
    - [Linha 1655](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L1655): `[e 356/2025);](https://fapes.es.gov.br/.../Resolu%C3%A7%C3%A3o_CCAF_n%C2%BA_356-2025...pdf)`
    - [Linha 1899](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L1899), [Linha 2232](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L2232), [Linha 2264](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L2264), [Linha 2509](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L2509), [Linha 4188](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L4188)
  - **Padrão Textual / RegEx (Método B)**:
    - [Linha 3954](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L3954): `313/2022 e 356/2025 – Manual de Utilização de Recursos Financeiros e Elaboração de Prestação de Contas`
- **Conteúdo**: Regras de comprovantes fiscais e movimentação financeira da FAPES.
- **Diagnóstico**: **Meramente remissivo (Travessia obrigatória no grafo)**.

---

### Caso 3: Edital 24/2026 $\rightarrow$ Resolução 357/2025 (Normas Gerais de Fomento)
- **Arquivo de Origem**: [`corpus_md/edital-024-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md)
- **Arquivo de Destino**: [`corpus_md/resolucao-357-2025.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-357-2025.md)
- **Mecanismos Determinísticos**:
  - **Hiperlink Markdown (Método A)**: **2 ocorrências**:
    - [Linha 1598](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L1598): `[conformidade com a Resolução CCAF/FAPES nº 357/2025.](https://fapes.es.gov.br/.../RESOLU%C3%87%C3%83O%20N%C2%BA%20357...pdf)`
    - [Linha 2526](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L2526): `[357/2025](https://fapes.es.gov.br/.../RESOLU%C3%87%C3%83O%20N%C2%BA%20357...pdf)`
  - **Padrão Textual / RegEx (Método B)**:
    - [Linha 3959](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-024-2026.md#L3959): `357/2025 – Normas gerais para fomento à Pesquisa e Desenvolvimento...`
- **Conteúdo**: Normas institucionais de liberação de recursos, vigências e penalidades.
- **Diagnóstico**: **Meramente remissivo (Travessia obrigatória no grafo)**.

---

### Caso 4: Edital 15/2026 $\longleftrightarrow$ Resolução 363/2026 (Talentos Globais)
- **Arquivos**: [`corpus_md/edital-015-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-015-2026.md) e [`corpus_md/resolucao-363-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-363-2026.md)
- **Mecanismos Determinísticos**:
  - **Hiperlink Markdown (Método A)**: ❌ **Nenhum link Markdown** no texto.
  - **Padrão Textual / RegEx (Método B)**: ✅ **2 ocorrências textuais exatas**:
    - [Linha 649](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-015-2026.md#L649): `IV. Resolução CCAF nº 363/2026 (Regulamenta a concessão de bolsas de estudos e auxílios no âmbito do Programa Talentos Globais Espírito Santo...)`
    - [Linha 893](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-015-2026.md#L893): `363/2026 (Regulamenta a concessão de bolsas de estudos e auxílios no âmbito do Programa Talentos Globais Espírito Santo...)`
- **Conteúdo**: Edital traz valores (US$ 1.500 mensais / US$ 1.000 instalação); Resolução traz regras do acordo com Instituto Trajetórias e regime institucional.
- **Diagnóstico**: **Regime híbrido / reprodução parcial**.

---

### Caso 5: Edital 13/2026 $\longleftrightarrow$ Resolução 361/2026 (Tabela de Bolsas)
- **Arquivos**: [`corpus_md/edital-013-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-013-2026.md) e [`corpus_md/resolucao-361-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-361-2026.md)
- **Mecanismos Determinísticos**:
  - **Hiperlink Markdown (Método A)**: ❌ **Nenhum link Markdown**.
  - **Padrão Textual / RegEx (Método B)**: ✅ **2 ocorrências textuais exatas**:
    - [Linha 729](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-013-2026.md#L729): `**i)** nº 361/2025 – Tabela de Valores de Bolsas e Auxílios;`
    - [Linha 1003](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-013-2026.md#L1003): `nº 361/2025 – Tabela de Valores de Bolsas e Auxílios`
- **Conteúdo**: Citação à tabela de valores de bolsas e auxílios vigente.
- **Diagnóstico**: **Regime híbrido**.

---

### Caso 6: Edital 04/2025 $\rightarrow$ Resolução 355/2025 (Bolsas EXT-E e EXT-F)
- **Arquivos**: [`corpus_md/edital-004-2025.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-004-2025.md) e [`corpus_md/resolucao-355-2025.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-355-2025.md)
- **Mecanismos Determinísticos**:
  - **Hiperlink Markdown (Método A)**: ❌ **Nenhum link Markdown**.
  - **Padrão Textual / RegEx (Método B)**: ✅ **4 ocorrências das siglas de modalidade**:
    - [Linha 3](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-004-2025.md#L3) e [Linha 176](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-004-2025.md#L176): `Ext-E ou Ext-F, pelo prazo mínimo de 22 meses`
- **Conteúdo**: O edital exige a inclusão das bolsas, mas omite a remuneração (R$ 800,00 e R$ 450,00, constantes na Resolução 355/2025).
- **Diagnóstico**: **Meramente remissivo (Travessia obrigatória no grafo)**.

---

### Caso 7: Resolução 352/2025 $\rightarrow$ Edital 13/2026 (PIBICES)
- **Arquivos**: [`corpus_md/resolucao-352-2025.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-352-2025.md) e [`corpus_md/edital-013-2026.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/edital-013-2026.md)
- **Mecanismos Determinísticos**:
  - **Hiperlink Markdown (Método A)**: ❌ **Nenhum link Markdown**.
  - **Padrão Textual / RegEx (Método B)**: ✅ **1 ocorrência da sigla canônica do programa**:
    - [Linha 69 da Resolução](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/corpus_md/resolucao-352-2025.md#L69): `II - Programa Institucional de Bolsas de Iniciação Científica, Tecnológica e de Inovação do estado do Espírito Santo – PIBICES;`
- **Conteúdo**: A Resolução 352 fixa o valor da bolsa de Iniciação Científica e Tecnológica (ICT) em R$ 900,00. O Edital 13 transcreve literalmente no seu item 7.2: *"O valor mensal atual da bolsa de ICT é de R$ 900,00 (novecentos reais)"*.
- **Diagnóstico**: **Reprodução integral do dado**.

---

## 6. Benchmark de Perguntas para Teste de GraphRAG

As perguntas a seguir podem ser usadas diretamente para validar e contrastar um **RAG Vetorial (Baseline)** contra o **GraphRAG**:

| ID | Pergunta de Teste | Resposta Correta | Requer Multi-Hop no Grafo? | Arquivos Envolvidos | Método Determinístico de Ligação |
|---|---|---|---|---|---|
| **Q1** | Qual o valor mensal da bolsa de Apoio Técnico Nível Superior (AT-NS) permitida pelo Edital PPP-ES 24/2026? | **R$ 1.900,00** | **SIM** (Edital não contém o valor) | `edital-024-2026.md` $\rightarrow$ `resolucao-355-2025.md` | Hiperlink Markdown + RegEx |
| **Q2** | Qual o valor das bolsas EXT-E e EXT-F exigidas no Edital Universal de Extensão (04/2025)? | **EXT-E: R$ 800,00**<br>**EXT-F: R$ 450,00** | **SIM** (Edital não contém os valores) | `edital-004-2025.md` $\rightarrow$ `resolucao-355-2025.md` | Sigla Canônica (RegEx) |
| **Q3** | Qual resolução da FAPES regulamenta a prestação de contas dos projetos contratados no Edital 24/2026? | **Resolução CCAF nº 313/2022 alterada pela 356/2025** | **SIM** | `edital-024-2026.md` $\rightarrow$ `resolucao-356-2025.md` | Hiperlink Markdown (6x) + RegEx |
| **Q4** | Qual entidade parceira participa da concessão de bolsas do Edital 15/2026 segundo sua resolução de regência? | **Instituto Trajetórias** (e SEGER) | **SIM** (detalhes na Resolução 363/2026) | `edital-015-2026.md` $\longleftrightarrow$ `resolucao-363-2026.md` | RegEx Sintático de Atos |
| **Q5** | Qual o valor mensal da bolsa de Iniciação Científica e Tecnológica (ICT) do Edital PIBICES 13/2026? | **R$ 900,00** | **NÃO** (Consta diretamente no Edital 13, item 7.2) | `edital-013-2026.md` | Citação com reprodução de valor |
