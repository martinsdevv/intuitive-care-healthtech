-- Teste 3 — DDL (PostgreSQL > 10)

BEGIN;

CREATE SCHEMA IF NOT EXISTS healthtech;
SET search_path TO healthtech;

-- =========================================================
-- DIMENSÃO: operadora (CADOP)
-- =========================================================
CREATE TABLE IF NOT EXISTS operadora (
  registro_ans            INTEGER PRIMARY KEY,
  cnpj                    CHAR(14),
  razao_social            TEXT,
  nome_fantasia           TEXT,
  modalidade              TEXT,
  uf                      CHAR(2),
  cidade                  TEXT,
  logradouro              TEXT,
  numero                  TEXT,
  complemento             TEXT,
  bairro                  TEXT,
  cep                     TEXT,
  ddd                     TEXT,
  telefone                TEXT,
  fax                     TEXT,
  endereco_eletronico     TEXT,
  representante           TEXT,
  cargo_representante     TEXT,
  regiao_comercializacao  TEXT,
  data_registro_ans       DATE,

  CONSTRAINT operadora_cnpj_digits CHECK (cnpj IS NULL OR cnpj ~ '^[0-9]{14}$'),
  CONSTRAINT operadora_uf_len CHECK (uf IS NULL OR length(uf) = 2)
);

CREATE INDEX IF NOT EXISTS idx_operadora_uf ON operadora (uf);

-- =========================================================
-- FATO: despesas por operadora e trimestre
-- =========================================================
CREATE TABLE IF NOT EXISTS despesa_trimestral (
  registro_ans        INTEGER NOT NULL REFERENCES operadora(registro_ans),
  ano                 SMALLINT NOT NULL,
  trimestre           SMALLINT NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
  valor_despesas      NUMERIC(18,2) NOT NULL,

  -- flags do pipeline (mantidas para auditoria/qualidade)
  cnpj_valido             BOOLEAN,
  valor_positivo          BOOLEAN,
  razao_social_nao_vazia  BOOLEAN,
  erros                   TEXT,

  PRIMARY KEY (registro_ans, ano, trimestre)
);

CREATE INDEX IF NOT EXISTS idx_despesa_periodo
  ON despesa_trimestral (ano, trimestre);

CREATE INDEX IF NOT EXISTS idx_despesa_registro_periodo
  ON despesa_trimestral (registro_ans, ano, trimestre);

-- =========================================================
-- MATERIALIZADO: agregação do teste 2.3 (razao_social + uf)
-- =========================================================
CREATE TABLE IF NOT EXISTS despesa_agregada_operadora_uf (
  razao_social      TEXT NOT NULL,
  uf                CHAR(2) NOT NULL,
  total_despesas    NUMERIC(18,2) NOT NULL,
  media_trimestral  NUMERIC(18,2),
  desvio_padrao     NUMERIC(18,2),
  qtd_registros     INTEGER,

  PRIMARY KEY (razao_social, uf)
);

CREATE INDEX IF NOT EXISTS idx_agregada_uf
  ON despesa_agregada_operadora_uf (uf);

COMMIT;
