# Decisões Técnicas — HealthTech

## Nota Geral sobre Identificadores (CNPJ vs RegistroANS)

O dataset de Demonstrações Contábeis da ANS **não contém CNPJ nem Razão Social**.
Por isso, o pipeline foi arquitetado em **duas fases distintas**:

1. **Teste 1 — Consolidação Financeira**: usa `RegistroANS` como identificador técnico.
2. **Teste 2 — Enriquecimento Cadastral**: resolve CNPJ, Razão Social, UF e Modalidade via CADOP.

Essa separação evita inferência incorreta de dados cadastrais e garante auditabilidade.

---

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
- `data/output/teste1/consolidado_despesas.csv`
- `data/output/teste1/consolidado_despesas.zip`


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
- Mantém-se registros duplicados que contenham valor gasto diferentes uns dos outros.
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
- `data/output/teste2/consolidado_despesas_final.csv`
- `data/output/teste2/consolidado_despesas_final.zip`

---

## 2.3 — Agregação com Múltiplas Estratégias

### Objetivo
Agrupar o output validado do Teste 2.2/2.1 por **(RazaoSocial, UF)** e calcular:
- **Total de despesas** por operadora/UF
- **Média trimestral** por operadora/UF
- **Desvio padrão** das despesas (para identificar alta variabilidade)

Ao final, ordenar por **total_despesas (desc)**, salvar em `despesas_agregadas.csv` e compactar em `Teste_Agregacao_{meu_nome}.zip`.

---

## Decisões Técnicas — 2.3

### Fonte e pré-condições
- Entrada: `data/output/teste2/consolidado_despesas_final.csv`
- A agregação utiliza as colunas já enriquecidas (RazaoSocial, UF) e aproveita as flags de qualidade geradas no Teste 2.1.

### Filtragem de qualidade antes da agregação
- Linhas com `valor_positivo=1` e `razao_social_nao_vazia=1` são consideradas válidas para análise.
- Linhas sem UF são descartadas.

Motivo: evitar grupos vazios e reduzir ruído estatístico (ex.: operadoras sem cadastro/enriquecimento).

### Estratégia de cálculo — streaming + estatística online (Welford)
Opções avaliadas:

**(A) Armazenar lista de valores por grupo**
- Implementação simples.
- Custo de memória cresce com o número de linhas (pior caso: alto).

**(B) Estatística online por grupo (escolhido)**
- Processa o CSV em streaming (linha a linha).
- Mantém, por grupo, apenas: `n`, `mean`, `m2` e `total` (algoritmo de Welford).
- Memória proporcional ao número de grupos (operadora/UF), não ao número de linhas.

Decisão: **Streaming + Welford por grupo**, reduzindo uso de RAM e mantendo cálculo correto de média e desvio padrão em 1 passagem.

### Precisão numérica
- `Decimal` é usado para totais/médias/desvio padrão, evitando erros de ponto flutuante em valores financeiros.

### Trade-off técnico — Ordenação
Após a agregação, os resultados são materializados e ordenados em memória por `total_despesas` (desc).

Justificativa:
- O número de grupos agregados é muito menor que o número de linhas do CSV.
- Ordenar apenas os grupos reduz custo e mantém o código simples/auditável.
- Alternativas (ordenar incrementalmente ou em disco) foram consideradas desnecessárias para o volume do exercício.

---

## Artefatos gerados (2.3)
- `data/output/teste2/despesas_agregadas.csv`
- `delivery/Teste_Agregacao_Gabriel_Martins.zip`

---

## Teste 3 — Banco de Dados e Análise (PostgreSQL)

### Objetivo
Persistir os dados consolidados e agregados dos Testes 1 e 2 em um banco relacional (PostgreSQL > 10), estruturando tabelas adequadas e respondendo consultas analíticas conforme solicitado no enunciado.

As fontes utilizadas são:
- Consolidado final de despesas (Teste 2.2 / 2.1)
- Agregação por Razão Social e UF (Teste 2.3)
- Cadastro oficial de operadoras (CADOP)

---

## Decisões Técnicas — 3.2 (Modelagem e DDL)

### Trade-off técnico — Normalização

**Opção A — Tabela única desnormalizada**
- Queries analíticas mais simples.
- Redundância elevada de dados cadastrais.
- Atualizações de cadastro propagam inconsistências.
- Menor clareza conceitual entre fatos e dimensões.

**Opção B — Modelo normalizado (escolhida)**
- Separação clara entre:
  - Dimensão `operadora` (dados cadastrais / CADOP)
  - Fato `despesa_trimestral` (valores financeiros por período)
- Menor redundância.
- Atualizações no cadastro não exigem reprocessar fatos.
- Queries analíticas continuam simples com JOINs bem definidos.

**Decisão:** adotado **modelo normalizado**, considerando:
- Volume maior de dados no fato (despesas).
- Baixa frequência de atualização do cadastro (CADOP).
- Melhor organização sem impacto relevante de performance.

---

### Trade-off técnico — Tipos de dados

**Valores monetários**
Opções avaliadas:
- `FLOAT`: rápido, porém impreciso para valores financeiros.
- `INTEGER` (centavos): preciso, mas reduz legibilidade e flexibilidade.
- `NUMERIC(18,2)` (escolhido): precisão exata e semântica clara.

**Decisão:** `NUMERIC(18,2)` para todos os valores financeiros.

**Datas**
- O dataset de despesas não possui datas completas, apenas `Ano` e `Trimestre`.
- Persistir como `(ano SMALLINT, trimestre SMALLINT)` evita parsing artificial e ambiguidades.
- Datas reais (ex.: cadastro CADOP) são armazenadas como `DATE`.

---

## Decisões Técnicas — 3.3 (Importação e Saneamento)

### Estratégia de importação
- Uso de tabelas de *staging* com colunas `TEXT`.
- Importação via `\copy` (client-side), facilitando execução local.
- Conversão e validação realizadas na passagem para tabelas finais tipadas.

### Tratamento de inconsistências

**Valores NULL em campos obrigatórios**
- Campos obrigatórios: `RegistroANS`, `Ano`, `Trimestre`, `ValorDespesas`.
- Registros com ausência nesses campos são rejeitados.
- Motivo: não é possível garantir integridade analítica.

**Strings em campos numéricos**
- Tentativa de conversão automática:
  - Remoção de separadores de milhar.
  - Conversão de vírgula decimal para ponto.
- Falha na conversão → registro rejeitado.

**Datas em formatos inconsistentes**
- Tentativa de parse nos formatos:
  - `YYYY-MM-DD`
  - `DD/MM/YYYY`
- Falha no parse → valor convertido para `NULL` (quando não chave analítica).

**Auditoria**
- Registros rejeitados são armazenados em tabela específica de rejeições,
  contendo o payload original e o motivo da rejeição.
- Decisão visa rastreabilidade e não descarte silencioso de dados.

---

## Decisões Técnicas — 3.4 (Consultas Analíticas)

### Query 1 — Crescimento percentual entre trimestres

**Desafio**
Operadoras podem não possuir dados em todos os trimestres.

**Decisão**
- Para cada operadora, considera-se:
  - Primeiro trimestre disponível no dataset.
  - Último trimestre disponível no dataset.
- O crescimento é calculado apenas se o valor inicial for positivo.

Motivo:
- Evita excluir operadoras incompletas.
- Mantém análise coerente com os dados realmente disponíveis.

---

### Query 2 — Distribuição por UF

**Estratégia**
- Primeiro agrega-se por `(Operadora, UF)`.
- Em seguida:
  - Soma total por UF.
  - Média de despesas por operadora dentro da UF.

Motivo:
- Evita distorções causadas por diferentes quantidades de registros por operadora.
- Mantém interpretação estatística correta.

---

### Query 3 — Operadoras acima da média em múltiplos trimestres

**Trade-off técnico**
Opções avaliadas:
- Subqueries aninhadas complexas.
- CTEs com etapas explícitas (escolhido).

**Decisão**
Uso de CTEs para:
- Identificar os 3 trimestres analisados.
- Calcular média global por trimestre.
- Comparar operadoras individualmente.
- Contar quantos trimestres cada operadora ficou acima da média.

Motivo:
- Código mais legível e auditável.
- Boa performance com índices adequados.
- Manutenibilidade superior para alterações futuras.


## Teste 4 — API e Interface Web

### Objetivo
Expor uma API em Python com rotas para consultar:
- operadoras (paginadas, com busca)
- detalhes por CNPJ
- histórico de despesas por operadora
- estatísticas agregadas (total, média, top 5, distribuição por UF)

E construir um frontend em Vue.js consumindo essas rotas.

---

## Trade-offs Técnicos — Backend (Teste 4)

### 4.2.1 — Framework: FastAPI (escolhido)

**Opções avaliadas**
- Flask
- FastAPI

**Por que FastAPI**
- Tipagem e contratos via Pydantic → reduz ambiguidade entre backend e frontend.
- Docs automáticos (OpenAPI/Swagger) → acelera validação das rotas e facilita demonstração.
- Performance adequada e ergonomia (routing/validation) sem aumentar muito a complexidade.

---

### 4.2.2 — Estratégia de Paginação: Offset-based (page/limit) (escolhido)

**Opções avaliadas**
- Offset-based (page/limit)
- Cursor-based
- Keyset pagination

**Decisão**
- O enunciado explicitamente pede `page` e `limit`, e o dataset é estável no contexto do teste.
- Simplifica o frontend e reduz complexidade de implementação.

**Trade-off**
- Em offsets altos, performance pode degradar; e atualizações concorrentes podem gerar “pulo/duplicação”.
- Para produção e datasets muito grandes, keyset pagination seria preferível.

---

### 4.2.3 — /api/estatisticas: Cache em memória por TTL (escolhido)

**Opções avaliadas**
- Calcular sempre na hora
- Cachear por X minutos
- Pré-calcular e armazenar em tabela

**Decisão**
- As estatísticas são agregações potencialmente caras; o dataset do teste muda pouco.
- Cache simples em memória com TTL (ex.: 5 min) reduz carga e mantém consistência aceitável.

**Trade-off**
- Cache in-memory não é compartilhado entre múltiplas instâncias.
- Em produção, opções como Redis (cache distribuído) ou materialização seriam consideradas.

---

### 4.2.4 — Estrutura de Resposta: Dados + Metadados (escolhido)

**Opções avaliadas**
- Apenas `[{...}, {...}]`
- `{ data: [...], total: 100, page: 1, limit: 10 }`

**Decisão**
- Metadados simplificam paginação e UX no frontend (total, página atual, limite).
- Evita inferências ambíguas no cliente.

---

## Qualidade e Manutenibilidade — Camadas (Router / Service / Repository)

**Decisão**
- Routers ficam “finos”: apenas HTTP (parâmetros, status codes, response model).
- `services/`: normalização, regras e orquestração (ex.: validação de CNPJ, cache de estatísticas).
- `repositories/`: consultas SQL (único lugar com acesso ao DB).

**Benefícios**
- Código mais testável (services/repos podem ser testados sem FastAPI).
- Queries centralizadas e fáceis de auditar.
- Evolução simples (trocar query/índice sem tocar no contrato HTTP).

---

## Segurança — SQL Injection

**Decisão**
- Consultas feitas com `sqlalchemy.text()` + parâmetros bindados (`:param`), nunca concatenando input do usuário no SQL.

**Justificativa**
- Parâmetros bindados evitam que `q/cnpj` alterem a estrutura da query (mitiga SQL injection).
- Regra: *input do usuário entra apenas como valor em params*.

---

## Tratamento de Erros (Backend)

**Padrões**
- `422` para entradas inválidas (ex.: CNPJ com dígitos insuficientes).
- `404` para recurso não encontrado.
- `500` para erros inesperados com mensagem genérica (não expor detalhes internos).

**Decisão**
- Retornar mensagens específicas quando o usuário pode agir (corrigir input).
- Mensagem genérica em `500` para não vazar stacktrace/SQL; logs ficam no servidor.

---

## Trade-offs Técnicos — Frontend (Teste 4)

### 4.3.1 — Estratégia de Busca/Filtro: Server-side (escolhido)
- Busca via `q` na API, evitando carregar todas as operadoras no cliente.
- Melhor escala e UX estável com paginação.

### 4.3.2 — Gerenciamento de Estado: Composables (Vue 3) (escolhido)
- Escopo do teste é pequeno; composables reduzem boilerplate.
- Se crescer (múltiplas telas/fluxos), Pinia seria o próximo passo natural.

### 4.3.3 — Performance da Tabela
- Paginação server-side (limitando render).
- Virtualização só seria necessária com listagens muito grandes no cliente.

### 4.3.4 — Erros, Loading e Dados vazios

**Erros de rede/API**
- 4xx: mensagens específicas (ex.: “CNPJ inválido”, “Operadora não encontrada”).
- 5xx: mensagem genérica (“Erro interno, tente novamente”) + botão de retry.
- Falha de rede/timeout: “Servidor indisponível / sem conexão”.

**Loading**
- Estado `loading` por tela:
  - listagem: skeleton/spinner na tabela
  - detalhes: placeholders + spinner no gráfico/histórico

**Dados vazios**
- Listagem sem resultados: “Nenhuma operadora encontrada para o filtro”.
- Histórico vazio: “Sem despesas registradas para esta operadora”.

**Análise crítica (genérico vs específico)**
- Específico quando o usuário consegue corrigir o problema.
- Genérico em `500` por segurança e para reduzir ruído; logs garantem rastreabilidade.
