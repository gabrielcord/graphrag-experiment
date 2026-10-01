<!--
SYNC IMPACT REPORT
==================
Version Change: [CONSTITUTION_VERSION] -> 1.0.0 (Initial Ratification)
Modified Principles: None (Initial adoption)
Added Sections:
  - Core Principles:
    - I. Padrão de Linguagem Python (Python-First)
    - II. Código Mínimo (KISS & YAGNI)
    - III. Sem Casos de Borda Especulativos (Foco no Concreto)
  - Technology Stack & Constraints
  - Development Workflow & Quality Gates
  - Governance
Removed Sections: None (Replaced template placeholders)
Follow-up TODOs: None
-->

# GraphRAG Experiment Constitution

## Core Principles

### I. Padrão de Linguagem Python (Python-First)
Todo o código da aplicação, scripts, ferramentas e experimentos DEVE (MUST) ser implementado exclusivamente em Python (3.11+).
- Bibliotecas padrão e convenções idiomáticas do ecossistema Python DEVEM (MUST) ser priorizadas.
- Ferramentas externas ou linguagens adicionais NÃO DEVEM (MUST NOT) ser introduzidas sem justificativa crítica e emenda constitucional.
- **Racional**: Garante uniformidade técnica, simplicidade de ambiente e interoperabilidade nativa com os ecossistemas de IA, dados e GraphRAG.

### II. Código Mínimo (KISS & YAGNI)
Desenvolvedores e agentes DEVEM (MUST) escrever estritamente a quantidade mínima de código necessária para resolver o problema especificado.
- Abstrações prematuras, camadas indiretas desnecessárias, padrões complexos e funções utilitárias sem uso imediato NÃO DEVEM (MUST NOT) ser criados.
- Cada linha de código adicionada DEVE (MUST) atender diretamente a um requisito funcional ativo.
- Soluções diretas e concisas DEVEM (MUST) sempre prevalecer sobre arquiteturas especulativas ou superdimensionadas.
- **Racional**: Menos código implica em menor superfície de bugs, manutenção facilitada, leitura rápida e eliminação de débito técnico precoce.

### III. Sem Casos de Borda Especulativos (Foco no Concreto)
O código NÃO DEVE (MUST NOT) tentar prever ou cobrir casos de borda, falhas teóricas ou exceções que ainda não tenham ocorrido ou que não estejam explicitamente documentadas em testes ou especificações.
- Tratamento de exceções e ramificações condicionais DEVEM (MUST) cobrir apenas cenários reais, observados ou formalmente requeridos.
- Novos casos de borda só DEVEM (MUST) ser incorporados quando evidenciados por uma falha concreta, teste quebrado ou nova especificação deliberada.
- **Racional**: Evita código morto, caminhos lógicos não testados e esforço desperdiçado em contingências hipotéticas que podem nunca se concretizar.

## Technology Stack & Constraints

- **Linguagem Principal**: Python 3.11+.
- **Dependências Mínimas**: Dependências externas DEVEM (MUST) ser mantidas no menor número possível, priorizando sempre que viável a biblioteca padrão do Python.
- **Arquitetura Concisa**: Preferir funções e módulos planos a hierarquias de classes profundas ("Flat is better than nested; Simple is better than complex").

## Development Workflow & Quality Gates

- **Delimitação Estrita de Escopo**: Nenhuma funcionalidade deve implementar comportamentos além dos especificados no ciclo atual.
- **Testes Focados**: Casos de teste DEVEM (MUST) verificar estritamente o comportamento requerido, sem especular sobre cenários de exceção hipotéticos.
- **Portão de Constituição (Constitution Check)**: Durante as fases de planejamento (`speckit-plan`) e implementação (`speckit-implement`), qualquer código considerado prolixo, redundante ou preventivo além do necessário DEVE (MUST) ser rejeitado e simplificado.

## Governance

- **Precedência**: Esta constituição se sobrepõe a quaisquer práticas informais, preferências ad-hoc ou convenções não documentadas.
- **Procedimento de Emenda**: Emendas exigem atualização deste documento (`.specify/memory/constitution.md`), incremento semântico de versão e registro no Relatório de Impacto de Sincronização (Sync Impact Report).
- **Revisão de Conformidade**: Todas as especificações, planos e implementações DEVEM (MUST) validar aderência estrita a estes princípios antes da conclusão de tarefas.
- **Política de Versionamento**:
  - MAJOR: Remoção, atenuação ou mudança incompatível em princípios existentes.
  - MINOR: Adição de novos princípios, seções ou expansão substantiva de governança.
  - PATCH: Ajustes redacionais, correções tipográficas e clarificações não semânticas.

**Version**: 1.0.0 | **Ratified**: 2026-09-30 | **Last Amended**: 2026-09-30
