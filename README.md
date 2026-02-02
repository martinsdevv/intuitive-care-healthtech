# Teste Técnico — Intuitive Care

Este repositório contém a implementação do teste técnico proposto para alinhamento da vaga de estágio na empresa **Intuitive Care**.

Testes contemplados:

1. **Integração com API Pública (ANS)**
2. **Transformação, Enriquecimento e Validação de Dados**
3. **Banco de Dados e Análise (SQL)** *(a implementar)*
4. **API + Interface Web (Frontend)** *(a implementar)*

---

## Estrutura do Projeto

```text
.
├── backend/
│   ├── scripts/                 # Entrypoints (run_test1.py, run_test2.py, ...)
│   ├── src/app/
│   │   ├── api/                 # API (Teste 4)
│   │   ├── core/                # Config/Paths/Tipos compartilhados
│   │   ├── domain/              # Modelos e validações
│   │   └── usecases/            # Etapas do pipeline (Testes 1 e 2)
│   └── tests/                   # Testes (exploratórios/integration)
├── frontend/                    # Interface web em Vue.js (Teste 4)
├── db/                          # Scripts SQL e consultas (Teste 3)
├── data/
│   ├── raw/                     # Zips baixados da ANS + CADOP local
│   ├── extracted/               # Conteúdo extraído dos zips
│   ├── staging/                 # Arquivo intermediário normalizado
│   └── output/
│       ├── teste1/              # Saídas do Teste 1
│       └── teste2/              # Saídas do Teste 2
├── docs/                        # Decisões técnicas e documentação
├── delivery/                    # Artefatos finais de entrega (ZIP)
└── README.md
```

---

## Arquitetura (visão rápida)

O projeto segue um **pipeline orientado a artefatos**:

- cada etapa lê o(s) arquivo(s) do estágio anterior
- processa em streaming sempre que possível
- gera um novo artefato em `data/output/...` (ou `data/staging/...`)
- o diretório `delivery/` é reservado para **artefatos finais** (gerados pelo runner)

**Camadas:**

- `domain/`: regras puras (ex.: validação de CNPJ, parsing numérico)
- `usecases/`: orquestração das etapas do pipeline (Testes 1 e 2)
- `scripts/`: entrypoints que executam o pipeline completo por teste
- `api/`: camada de API (Teste 4)
- `db/`: scripts SQL (Teste 3)

---

## Configuração do Ambiente de Desenvolvimento

Da raiz do projeto:

```bash
python -m venv venv
```

Ative o ambiente virtual:

**Linux/Mac**
```bash
source venv/bin/activate
```

**Windows**
```bash
venv\Scripts\activate
```

Instale dependências:

```bash
pip install -r requirements.txt
```

---

## Como Rodar os Testes

Os entrypoints ficam em `backend/scripts`.

> Dica: a flag `--clean` remove os arquivos gerados anteriormente para executar um teste limpo, evitando duplicação de dados.

Exemplos:

```bash
python backend/scripts/run_test1.py --clean
python backend/scripts/run_test2.py --clean --nome Gabriel_Martins
```

---

## Progresso dos Testes

A especificação de cada trade-off e decisão técnica está em `docs/decisoes_tecnicas.md`.

Os dados brutos e intermediários ficam em `data/` (`raw`, `extracted`, `staging`, `output/...`) para facilitar auditoria.

---

### Teste 1 — Integração com API (ANS)

- [x] **1.1 — Download** dos arquivos de Demonstrações Contábeis (últimos 3 trimestres)  
  Código: `backend/src/app/usecases/ans_download.py`

- [x] **1.2 — Extração + Normalização** (filtro: Despesas com Eventos/Sinistros)  
  Código: `backend/src/app/usecases/ans_normalization.py`

- [x] **1.3 — Consolidação** (CSV final + ZIP)  
  Código: `backend/src/app/usecases/ans_consolidate.py`

**Rodar**
- Arquivo: `backend/scripts/run_test1.py`
- Exemplo:
  - `python backend/scripts/run_test1.py`
  - `python backend/scripts/run_test1.py --clean`

**Saídas**
- `data/output/teste1/consolidado_despesas.csv`
- `data/output/teste1/consolidado_despesas.zip`

---

### Teste 2 — Transformação, Enriquecimento e Validação

A sequência começou pelo **2.2**, pois o consolidado do Teste 1 utiliza `RegistroANS` (a fonte não possui CNPJ).  
Detalhes em `docs/decisoes_tecnicas.md`.

- [x] **2.2 — Enriquecimento (Join com CADOP)**  
  Código: `backend/src/app/usecases/ans_enrich_validate.py`

- [x] **2.1 — Validação**  
  Código: `backend/src/app/usecases/ans_enrich_validate.py`

- [x] **2.3 — Agregação (RazaoSocial + UF)**  
  Código: `backend/src/app/usecases/ans_agregate.py`

**Trade-offs principais**
- CADOP carregado em memória como dicionário (pequeno, acesso O(1)).
- Consolidado processado em streaming (RAM previsível).
- Registros inválidos **não são descartados**: são marcados com flags (`cnpj_valido`, `valor_positivo`, etc.) + campo `erros`.
- Na agregação, a ordenação acontece **após reduzir** o dataset (ordenamos apenas os grupos agregados).

**Rodar**
- Arquivo: `backend/scripts/run_test2.py`
- Exemplo:
  - `python backend/scripts/run_test2.py`
  - `python backend/scripts/run_test2.py --clean --nome Gabriel_Martins`


**Saídas**
- `data/output/teste2/consolidado_despesas_final.csv`
- `data/output/teste2/consolidado_despesas_final.zip`
- `data/output/teste2/despesas_agregadas.csv`
- `data/output/teste2/Teste_<nome>.zip` *(zip técnico do teste2, usado como fonte para entrega)*
- `delivery/Teste_Agregacao_<nome>.zip` *(artefato final de entrega)*

---

### Teste 3 — Banco de Dados e Análise (PostgreSQL)

Este teste utiliza os CSVs gerados no Teste 2 para persistência em banco relacional
(PostgreSQL > 10) e execução de consultas analíticas.

**Fontes**
- `data/output/teste2/consolidado_despesas_final.csv`
- `data/output/teste2/despesas_agregadas.csv`
- `data/raw/Relatorio_cadop.csv` (CADOP)

**Modelo**
- Abordagem normalizada:
  - Dimensão: dados cadastrais da operadora (CADOP)
  - Fato: despesas trimestrais por operadora
- Tabela adicional com a agregação do Teste 2.3 para validação e análise rápida.

**Scripts**
- `db/001_ddl.sql` — schema, tabelas e índices
- `db/002_import.sql` — staging, carga dos CSVs, saneamento e rejeições
- `db/003_queries.sql` — consultas analíticas solicitadas no enunciado

**Execução (psql)**
```bash
psql -U postgres -d <seu_banco> -f db/001_ddl.sql
psql -U postgres -d <seu_banco> -f db/002_import.sql
psql -U postgres -d <seu_banco> -f db/003_queries.sql
```

> As decisões técnicas e trade-offs do Teste 3 estão documentados em
docs/decisoes_tecnicas.md.
---

### Teste 4 — API + Interface Web *(a implementar)*

- [ ] API em `backend/src/app/api`
- [ ] Frontend Vue em `frontend/`

---

## Testes Automatizados (Pytest)

Os testes em `backend/tests` são **exploratórios** e marcados com `@pytest.mark.integration`.

Para rodar:

```bash
pytest backend/tests -m integration -s
```
