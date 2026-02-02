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

## 1.3 — Consolidação e Análise de Inconsistências

### Objetivo
Consolidar os dados normalizados dos 3 trimestres em um único CSV e gerar um ZIP final `consolidado_despesas.zip`.

**CSV final (colunas):**  
`RegistroANS, RazaoSocial, Trimestre, Ano, ValorDespesas`

> Observação: o dataset de Demonstrações Contábeis da ANS não fornece CNPJ nem Razão Social da operadora.  
> Por isso, `RegistroANS (REG_ANS)` é utilizado como identificador da operadora e `RazaoSocial` é mantida como "NÃO INFORMADA".

---

## Decisões Técnicas — 1.3

### Fonte de dados
- Entrada da consolidação é o staging gerado no 1.2 (`data/staging/...csv`).
- Evita reprocessar ZIP/CSV e garante consistência com as normalizações já aplicadas.

### Ausência de CNPJ e Razão Social no dataset
- O dataset não disponibiliza **CNPJ** nem **Razão Social**.
- `REG_ANS` é o identificador oficial da operadora junto à ANS e foi adotado como `RegistroANS`.
- `RazaoSocial` é mantida como "NÃO INFORMADA" para evitar inferência incorreta a partir de campos não destinados a isso.

### Chave de agregação
- Agregação por `(RegistroANS, Ano, Trimestre)`.
- Soma de `ValorDespesas` por chave.

### Métrica consolidada (ValorDespesas)
- `ValorDespesas` é calculado pela soma dos valores filtrados no staging para o trimestre/ano.

---

## Análise Crítica — Tratamento de Inconsistências (1.3)

### “CNPJs duplicados com razões sociais diferentes”
- Não aplicável diretamente: **CNPJ** e **Razão Social** não existem na fonte.
- No escopo do exercício, o identificador consolidado é `RegistroANS (REG_ANS)` e `RazaoSocial` é "NÃO INFORMADA".

### Valores zerados ou negativos
- Valores zerados: mantidos.
- Valores negativos: descartados.
- Justificativa: zeros podem representar ausência real; negativos distorcem `ValorDespesas` sem modelagem explícita de estornos.

### Trimestres com formatos de data inconsistentes
- Normalização feita no 1.2 e `Ano/Trimestre` persistidos no staging.
- O 1.3 usa `Ano/Trimestre` do staging, evitando parse de data novamente.

---

## Artefatos gerados (1.3)
- `data/final/consolidado_despesas.csv`
- `data/final/consolidado_despesas.zip`


## Teste 2 — Transformação, Enriquecimento e Validação

### Objetivo
Enriquecer o consolidado do Teste 1.3 com dados cadastrais oficiais (CADOP) e aplicar validações de qualidade, produzindo um CSV final para agregações. Começamos pelo 2.2, pois o CSV do teste 1.3 não contém CNPJ (decisão explicada abaixo)

---

## Decisões Técnicas — 2.2 (Enriquecimento / Join)

### Chave de join (decisão prática)
O enunciado menciona join por **CNPJ**, porém o CSV do Teste 1.3 não contém CNPJ (apenas `RegistroANS`).  
Decisão adotada:

1. Join por `RegistroANS` (consolidado) ↔ `Registro ANS` (CADOP)
2. Trazer o CNPJ real e campos do cadastro (Razão Social, Modalidade, UF)

Isso evita “inventar” CNPJ a partir de colunas que não representam CNPJ.

### Registros sem match no cadastro
- Mantidos no output (left join), com campos cadastrais vazios.
- Motivo: evitar perda de dados financeiros e permitir auditoria.

### Duplicidades no cadastro
- Se houver mais de um registro para o mesmo `Registro ANS`, escolhe-se o registro “mais completo” (maior número de campos não vazios entre CNPJ/RazãoSocial/Modalidade/UF).
- Motivo: saída determinística e com melhor qualidade média.

### Trade-off técnico — Estratégia de processamento do join
- CADOP carregado em memória como dicionário, visto que é pequeno e permite acesso rápido.
- Consolidado processado em streaming para manter consumo de RAM previsível.

Decisão: **dict em memória (cadastro) + streaming (consolidado)**.

---

## Decisões Técnicas — 2.1 (Validação)

### Validações aplicadas (após enriquecimento)
- CNPJ válido (formato + dígitos verificadores)
- ValorDespesas numérico e positivo
- RazaoSocial não vazia

### Trade-off técnico — Tratamento de CNPJ inválido
Opções consideradas:
- Descartar registros inválidos
- Corrigir automaticamente
- Marcar e manter

Decisão: **marcar e manter**, adicionando colunas de validação e lista de erros por linha.  
Motivo: pipeline auditável (não perde dados sem certeza).

---

## Artefatos gerados (2.2 e 2.1)
- `data/output/consolidado_despesas_final.csv`
