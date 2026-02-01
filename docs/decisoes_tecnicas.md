# Decisões Técnicas — HealthTech

Este documento registra as decisões técnicas tomadas ao longo da implementação dos testes propostos, bem como os trade-offs avaliados.  
O objetivo é explicitar **por que** determinadas escolhas foram feitas, considerando robustez e clareza.

---

## Teste 1.1 — Download dos arquivos da ANS

### Objetivo
Baixar automaticamente os arquivos de Demonstrações Contábeis mais recentes (últimos 3 trimestres disponíveis) a partir do FTP público da ANS, de forma confiável e reproduzível.

---

## Decisões Técnicas — 1.1

### Uso de `requests.Session` com User-Agent explícito
- Reutilização de conexão HTTP.
- Evita bloqueios por ausência de User-Agent.
- Facilita extensões futuras (retry, proxy).

### Descoberta dinâmica de anos e arquivos
- Anos e arquivos são descobertos via parsing do HTML do FTP.
- Evita hardcode e torna o pipeline resiliente a atualizações futuras.

### Parsing simples de HTML
- Extração manual de `href` suficiente para o padrão estável do FTP.
- Evita dependências externas desnecessárias.

### Identificação de trimestre por heurísticas
- Inferência baseada no nome do arquivo (`1T2025`, `2007_1_trimestre`, etc.).
- Fallback para ano da pasta quando necessário.
- Permite agrupar corretamente arquivos historicamente inconsistentes.

### Download com arquivo temporário
- Uso de `.part` para garantir atomicidade.
- Evita arquivos corrompidos em falhas/interrupções.

---

## Teste de Integração 1.1 — Download Completo (Exploratório)

**Arquivo:** `backend/tests/test_ans_download.py`

Teste exploratório utilizado durante o desenvolvimento para:
- Validar acessibilidade de todos os ZIPs do FTP.
- Detectar links quebrados ou problemas sistêmicos.
- Confirmar que as heurísticas de download cobrem o conjunto real de arquivos.

Esse teste não faz parte do pipeline principal e é executado sob demanda.

---

## Teste 1.2 — Processamento e Normalização de Arquivos

### Objetivo
Processar os arquivos ZIP dos trimestres selecionados, extraindo e normalizando apenas os dados de **Despesas com Eventos/Sinistros**, lidando automaticamente com variações de formato, encoding e estrutura de colunas.

---

## Decisões Técnicas — 1.2

### Estratégia geral
- Reutilização do output do Teste 1.1 (`data/raw`).
- Pipeline definido como:  
  `raw (ZIP) → extracted (CSV) → staging (CSV normalizado)`.

### Formato dos arquivos
- Inventário amostral confirmou que todos os ZIPs contêm **1 CSV**.
- Apesar disso, a implementação mantém fallback para outros formatos por segurança.

### Separador e quoting
- CSVs utilizam `;` como delimitador e `"` como quote.
- Parser configurado explicitamente para evitar ambiguidades.

### Encoding
- Arquivos históricos utilizam `latin-1`.
- Arquivos recentes utilizam `utf-8-sig`.
- Estratégia adotada: tentativa em cascata (`utf-8-sig → utf-8 → latin-1`).

### Datas
- Formatos observados: `DD/MM/YYYY` e `YYYY-MM-DD`.
- Datas normalizadas para ISO (`YYYY-MM-DD`) internamente.

### Estrutura de colunas
- Layout histórico: 5 colunas.
- Layout recente: 6 colunas (adição de `VL_SALDO_INICIAL`).
- Schema canônico definido com ambas as colunas.
- Valores ausentes são preenchidos de forma consistente.

### Valores monetários
- Variação entre vírgula decimal e valores inteiros.
- Normalização para decimal controlado antes de agregações.

### Identificação de “Despesas com Eventos/Sinistros”
- O recorte não é identificável pelo nome do arquivo.
- Filtro realizado por conteúdo da coluna `DESCRICAO`.
- Matching case-insensitive após normalização de texto.
- Opcionalmente extensível para códigos contábeis.

---

## Trade-off Técnico — Processamento em Memória vs Incremental

### Opções avaliadas

**Processamento em memória**
- Implementação mais simples.
- Alto risco de consumo excessivo de RAM (CSVs de 30–70MB).
- Menor resiliência a falhas.

**Processamento incremental (escolhido)**
- Leitura em streaming linha a linha.
- Consumo de memória previsível.
- Maior robustez e possibilidade de reprocessamento parcial.
- Geração de staging intermediário para auditoria.

### Decisão
Foi adotado **processamento incremental**, considerando o volume dos dados e a necessidade de robustez.

---

## Teste de Integração 1.2 — Inventário (Exploratório)

**Arquivo:** `backend/tests/test_ans_zips.py`

Teste exploratório utilizado para:
- Validar o conteúdo real dos ZIPs.
- Identificar padrões de formato, tamanho e estrutura.
- Reduzir suposições antes da implementação do service 1.2.

Assim como o teste 1.1 exploratório, não faz parte do pipeline principal.

---

## Próximo Passo — Teste 1.3

Consolidação dos dados normalizados e geração do artefato final conforme especificação.
