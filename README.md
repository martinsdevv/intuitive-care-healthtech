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

## Progresso dos Testes

Aqui consta o que foi feito em cada teste, incluindo os trade-offs técnicos decididos. A especificação de cada escolha de trade-off está disponível em `docs/decisoes_tecnicas.md`. Para rodar cada teste, execute o arquivo correspondente na pasta `backend/scripts`: 

```bash
python <nome_arquivo>.py
```

Os dados brutos e normalizados estão disponiveis na pasta `data/`, contendo os dados "crus" (raw), zips extraídos (extracted), arquivos finais (output) dentre outros. Mantive assim para facilitar a visualização por parte do avaliador.

### Teste 1 — Integração com API 


- [x] Acesso à api e download dos arquivos de Demonstrações Contábeis dos últimos 3 trimestres. 

Codigo: `backend/src/app/services/ans_download.py`
- [x] Extração e normalização de arquivos de acordo com o formato de cada um (CSV, TXT e XLSX). 
 
Codigo: `backend/src/app/services/ans_normalization.py`
- [ ] Consolidação dos dados e geração do arquivo final em CSV e ZIP. 

Codigo: `backend/src/app/services/ans_consolidate.py` 


Documentação: tratamento de inconsistências em `docs/decisoes_tecnicas.md` 


**Trade-offs**
- Processamento incremental dos arquivos para reduzir uso de memória e permitir escalabilidade.


**Rodar Teste**
- Arquivo: `backend/scripts/run_test1.py`


**Saídas:**
- `data/output/consolidado_despesas.csv`
- `data/output/consolidado_despesas.zip`

---

### Teste 2 — Transformação e Validação dos Dados
- [ ] Validação de CNPJ, valores monetários e razão social
- [ ] Enriquecimento dos dados com informações cadastrais da ANS
- [ ] Agregação por operadora, trimestre e ano

**Saída esperada:**
- `data/output/despesas_agregadas.csv`

---

### Teste 3 — Banco de Dados e Análise
- [ ] Criação do modelo relacional e índices
- [ ] Importação dos dados consolidados para o banco
- [ ] Consultas analíticas solicitadas no teste

Os scripts SQL estão disponíveis no diretório `db/`.

---

### Teste 4 — API e Interface Web
- [ ] Implementação da API REST para exposição dos dados
- [ ] Paginação, busca e estatísticas agregadas
- [ ] Interface web em Vue.js para visualização das informações
- [ ] Coleção Postman e documentação da API

---

## Como Executar (Resumo)

Cada etapa do teste pode ser executada de forma isolada.

Instruções detalhadas estão disponíveis nos READMEs específicos de cada diretório:
- `backend/README.md`
- `frontend/README.md`
- `db/README.md`

---

## Decisões Técnicas

As principais decisões técnicas e trade-offs adotados durante o desenvolvimento estão documentados em:
- `docs/decisions.md`

---

## Entrega

O arquivo final para submissão está disponível em:
- `delivery/Teste_Gabriel_Martins.zip`
