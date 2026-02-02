# Teste Técnico — Intuitive Care

Este repositório contém a implementação do teste técnico proposto para alinhamento da vaga de estágio na empresa Intuitive Care. Estão integrados 4 testes, sendo eles:

1. Teste de Integração com API Pública
2. Teste de Transformação e Validação dos Dados
3. Teste de Banco de Dados e Análise
4. Teste de API e Interface Web

---

## Estrutura do Projeto

```text
.
├── backend/        # API em Python e lógica dos Testes 1, 2 e 4
├── frontend/       # Interface web em Vue.js (Teste 4)
├── db/             # Scripts SQL e consultas analíticas (Teste 3)
├── data/
│   └── output/     # Arquivos finais gerados (CSVs e ZIPs)
├── docs/           # Decisões técnicas e documentação da API
├── delivery/       # ZIP final para entrega
└── README.md       # Este arquivo
```

---

## Configuração do Ambiente de Desenvolvimento

- Da raiz do projeto, digite:
```bash
python -m venv venv
```

- Ative o ambiente virtual
- Linux/Mac:
```bash
source venv/bin/activate
```

- Windows:
```bash
venv\Scripts\activate
```

- Instale as dependências
```bash
pip install -r requirements.txt
```

- Crie um arquivo `.env` com as variáveis de ambiente necessárias (segue .env.example na raiz do projeto)

- Para rodar cada teste, execute o arquivo correspondente na pasta `backend/scripts` (onde X é o numero do teste): 

```bash
python run_testX.py --clean
```

- Ou execute na raiz do projeto:
```bash
python backend/scripts/run_testX.py --clean
```

- A flag `--clean` remove os arquivos gerados anteriormente antes de executar o teste. Utilize para um teste limpo evitando duplicação de dados.

---

## Progresso dos Testes

Aqui consta o que foi feito em cada teste, incluindo os trade-offs técnicos decididos. A especificação de cada escolha de trade-off está disponível em `docs/decisoes_tecnicas.md`. 


Os dados brutos e normalizados estão disponiveis na pasta `data/`, contendo os dados "crus" (raw), zips extraídos (extracted), arquivos finais (output) dentre outros. Mantive assim para facilitar a visualização por parte do avaliador.

### Teste 1 — Integração com API 


- [x] 1.1 - Acesso à api e download dos arquivos de Demonstrações Contábeis dos últimos 3 trimestres. 

Codigo: `backend/src/app/services/ans_download.py`
- [x] 1.2 - Extração e normalização de arquivos de acordo com o formato de cada um (CSV, TXT e XLSX). 
 
Codigo: `backend/src/app/services/ans_normalization.py`
- [x] 1.3 - Consolidação dos dados e geração do arquivo final em CSV e ZIP. 

Codigo: `backend/src/app/services/ans_consolidate.py` 


Documentação: tratamento de inconsistências em `docs/decisoes_tecnicas.md` 


**Trade-offs**
- Processamento incremental dos arquivos para reduzir uso de memória e permitir escalabilidade.


**Rodar Teste**
- Arquivo: `backend/scripts/run_test1.py`
- Exemplo:
  - `python backend/scripts/run_test1.py`
  - `python backend/scripts/run_test1.py --clean`


**Saídas:**
- `data/output/teste1/consolidado_despesas.csv`
- `data/output/teste1/consolidado_despesas.zip`

---

### Teste 2 — Transformação e Validação de Dados

A sequência de etapas começou pelo **2.2** (enunciado pede join por CNPJ, mas o consolidado do Teste 1 usa `RegistroANS`).  
Detalhes e trade-offs em `docs/decisoes_tecnicas.md`.

- [x] **2.2 — Enriquecimento de Dados com Tratamento de Falhas**  
  Código: `backend/src/app/services/ans_enrich_validate.py`

- [x] **2.1 — Validação de Dados com Estratégias Diferentes**  
  Código: `backend/src/app/services/ans_enrich_validate.py`

- [x] **2.3 — Agregação com Múltiplas Estratégias**  
  Código: `backend/src/app/services/ans_agregate.py`

**Documentação**: decisões técnicas e tratamento de inconsistências em `docs/decisoes_tecnicas.md`.

**Trade-offs**
- CADOP carregado em memória como dicionário (arquivo pequeno, acesso O(1) e simplifica o join).
- Consolidado processado em streaming (consumo previsível de RAM).
- Registros inválidos não são descartados: são marcados com flags (`cnpj_valido`, `valor_positivo`, etc.) e lista `erros` por linha.
- Na agregação, ordenação é feita após reduzir o dataset (ordenamos apenas os grupos agregados, não as linhas cruas).

**Rodar Teste**
- Arquivo: `backend/scripts/run_test2.py`
- Exemplo:
  - `python backend/scripts/run_test2.py`
  - `python backend/scripts/run_test2.py --clean`

**Saídas**
- `data/output/teste2/consolidado_despesas_final.csv`
- `data/output/teste2/consolidado_despesas_final.zip`
- `data/output/teste2/despesas_agregadas.csv`
- `delivery/Teste_Agregacao_Gabriel_Martins.zip`
