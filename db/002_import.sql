-- Teste 3 — Importação / Saneamento
--
-- Estratégia:
-- 1) staging (TEXT) para importar sem quebrar
-- 2) saneamento/conversão para tabelas finais tipadas
-- 3) rejeitados em tabela de auditoria
--
-- IMPORTANTE:
-- - Este script usa \copy (psql). Rode com: psql -d <seu_banco> -f db/002_import.sql
-- - Ajuste os caminhos dos CSVs nas linhas de \copy se necessário.
-- - CSVs esperados com HEADER, delimitador ';' e UTF-8.

BEGIN;

SET search_path TO healthtech;

-- =========================================================
-- 0) Auditoria: rejeitados
-- =========================================================
CREATE TABLE IF NOT EXISTS import_rejeitados (
  origem     TEXT NOT NULL,
  motivo     TEXT NOT NULL,
  payload    JSONB NOT NULL,
  criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 1) STAGING TABLES
-- =========================================================

DROP TABLE IF EXISTS stg_cadop;
CREATE UNLOGGED TABLE stg_cadop (
  registro_operadora TEXT,
  cnpj TEXT,
  razao_social TEXT,
  nome_fantasia TEXT,
  modalidade TEXT,
  logradouro TEXT,
  numero TEXT,
  complemento TEXT,
  bairro TEXT,
  cidade TEXT,
  uf TEXT,
  cep TEXT,
  ddd TEXT,
  telefone TEXT,
  fax TEXT,
  endereco_eletronico TEXT,
  representante TEXT,
  cargo_representante TEXT,
  regiao_de_comercializacao TEXT,
  data_registro_ans TEXT
);

DROP TABLE IF EXISTS stg_despesa_trimestral;
CREATE UNLOGGED TABLE stg_despesa_trimestral (
  registro_ans TEXT,
  cnpj TEXT,
  razao_social TEXT,
  modalidade TEXT,
  uf TEXT,
  trimestre TEXT,
  ano TEXT,
  valor_despesas TEXT,
  cnpj_valido TEXT,
  valor_positivo TEXT,
  razao_social_nao_vazia TEXT,
  erros TEXT
);

DROP TABLE IF EXISTS stg_despesa_agregada;
CREATE UNLOGGED TABLE stg_despesa_agregada (
  razao_social TEXT,
  uf TEXT,
  total_despesas TEXT,
  media_trimestral TEXT,
  desvio_padrao TEXT,
  qtd_registros TEXT
);

-- =========================================================
-- 2) IMPORTAÇÃO (psql \copy)
-- =========================================================
-- Ajuste os caminhos conforme sua estrutura:
-- - CADOP: data/raw/Relatorio_cadop.csv
-- - Consolidado final: data/output/teste2/consolidado_despesas_final.csv
-- - Agregadas: data/output/teste2/despesas_agregadas.csv

TRUNCATE stg_cadop;
\copy healthtech.stg_cadop FROM 'data/raw/Relatorio_cadop.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8', QUOTE '"');

TRUNCATE stg_despesa_trimestral;
\copy healthtech.stg_despesa_trimestral FROM 'data/output/teste2/consolidado_despesas_final.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8', QUOTE '"');

TRUNCATE stg_despesa_agregada;
\copy healthtech.stg_despesa_agregada FROM 'data/output/teste2/despesas_agregadas.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8', QUOTE '"');

-- =========================================================
-- 3) SANEAMENTO / UPSERT PARA TABELAS FINAIS
-- =========================================================

-- ---------------------------------------------------------
-- 3.1) CADOP -> operadora
-- Regras:
-- - registro_operadora: obrigatório e numérico (senão rejeita)
-- - cnpj: mantém só dígitos; se não tiver 14, vira NULL (não rejeita)
-- - uf: valida [A-Z]{2}, senão NULL
-- - data_registro_ans: tenta YYYY-MM-DD e DD/MM/YYYY, senão NULL
-- ---------------------------------------------------------
WITH cleaned AS (
  SELECT
    NULLIF(trim(registro_operadora), '') AS registro_raw,
    regexp_replace(COALESCE(cnpj, ''), '\D', '', 'g') AS cnpj_digits,
    NULLIF(trim(razao_social), '') AS razao_social,
    NULLIF(trim(nome_fantasia), '') AS nome_fantasia,
    NULLIF(trim(modalidade), '') AS modalidade,
    NULLIF(trim(logradouro), '') AS logradouro,
    NULLIF(trim(numero), '') AS numero,
    NULLIF(trim(complemento), '') AS complemento,
    NULLIF(trim(bairro), '') AS bairro,
    NULLIF(trim(cidade), '') AS cidade,
    upper(NULLIF(trim(uf), '')) AS uf,
    NULLIF(trim(cep), '') AS cep,
    NULLIF(trim(ddd), '') AS ddd,
    NULLIF(trim(telefone), '') AS telefone,
    NULLIF(trim(fax), '') AS fax,
    NULLIF(trim(endereco_eletronico), '') AS endereco_eletronico,
    NULLIF(trim(representante), '') AS representante,
    NULLIF(trim(cargo_representante), '') AS cargo_representante,
    NULLIF(trim(regiao_de_comercializacao), '') AS regiao_comercializacao,
    NULLIF(trim(data_registro_ans), '') AS data_registro_raw,
    to_jsonb(stg_cadop.*) AS payload
  FROM stg_cadop
),
typed AS (
  SELECT
    CASE WHEN registro_raw ~ '^[0-9]+$' THEN registro_raw::int ELSE NULL END AS registro_ans,
    CASE WHEN cnpj_digits ~ '^[0-9]{14}$' THEN cnpj_digits::char(14) ELSE NULL END AS cnpj,
    razao_social, nome_fantasia, modalidade,
    logradouro, numero, complemento, bairro, cidade,
    CASE WHEN uf ~ '^[A-Z]{2}$' THEN uf::char(2) ELSE NULL END AS uf,
    cep, ddd, telefone, fax,
    endereco_eletronico, representante, cargo_representante, regiao_comercializacao,
    CASE
      WHEN data_registro_raw ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(data_registro_raw, 'YYYY-MM-DD')
      WHEN data_registro_raw ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(data_registro_raw, 'DD/MM/YYYY')
      ELSE NULL
    END AS data_registro_ans,
    payload
  FROM cleaned
),
rej AS (
  INSERT INTO import_rejeitados (origem, motivo, payload)
  SELECT 'cadop', 'registro_operadora ausente/invalido', payload
  FROM typed
  WHERE registro_ans IS NULL
  RETURNING 1
)
INSERT INTO operadora (
  registro_ans, cnpj, razao_social, nome_fantasia, modalidade, uf, cidade, logradouro, numero,
  complemento, bairro, cep, ddd, telefone, fax, endereco_eletronico, representante, cargo_representante,
  regiao_comercializacao, data_registro_ans
)
SELECT
  registro_ans, cnpj, razao_social, nome_fantasia, modalidade, uf, cidade, logradouro, numero,
  complemento, bairro, cep, ddd, telefone, fax, endereco_eletronico, representante, cargo_representante,
  regiao_comercializacao, data_registro_ans
FROM typed
WHERE registro_ans IS NOT NULL
ON CONFLICT (registro_ans) DO UPDATE SET
  cnpj = COALESCE(EXCLUDED.cnpj, operadora.cnpj),
  razao_social = COALESCE(EXCLUDED.razao_social, operadora.razao_social),
  nome_fantasia = COALESCE(EXCLUDED.nome_fantasia, operadora.nome_fantasia),
  modalidade = COALESCE(EXCLUDED.modalidade, operadora.modalidade),
  uf = COALESCE(EXCLUDED.uf, operadora.uf),
  cidade = COALESCE(EXCLUDED.cidade, operadora.cidade),
  logradouro = COALESCE(EXCLUDED.logradouro, operadora.logradouro),
  numero = COALESCE(EXCLUDED.numero, operadora.numero),
  complemento = COALESCE(EXCLUDED.complemento, operadora.complemento),
  bairro = COALESCE(EXCLUDED.bairro, operadora.bairro),
  cep = COALESCE(EXCLUDED.cep, operadora.cep),
  ddd = COALESCE(EXCLUDED.ddd, operadora.ddd),
  telefone = COALESCE(EXCLUDED.telefone, operadora.telefone),
  fax = COALESCE(EXCLUDED.fax, operadora.fax),
  endereco_eletronico = COALESCE(EXCLUDED.endereco_eletronico, operadora.endereco_eletronico),
  representante = COALESCE(EXCLUDED.representante, operadora.representante),
  cargo_representante = COALESCE(EXCLUDED.cargo_representante, operadora.cargo_representante),
  regiao_comercializacao = COALESCE(EXCLUDED.regiao_comercializacao, operadora.regiao_comercializacao),
  data_registro_ans = COALESCE(EXCLUDED.data_registro_ans, operadora.data_registro_ans);

-- ---------------------------------------------------------
-- 3.2) Consolidado final -> despesa_trimestral
-- Regras:
-- - Obrigatórios: registro_ans, ano, trimestre, valor_despesas (senão rejeita)
-- - valor_despesas: replace ',' -> '.' e remove lixo (milhar, R$, espaços) via regex
-- - flags booleanas: aceita 1/0, true/false, t/f, yes/no
-- - Se operadora não existir no CADOP: cria placeholder mínimo para manter o fato
-- ---------------------------------------------------------

-- 3.2.1) garantir dimensão para todos os registro_ans presentes no fato
WITH reg AS (
  SELECT DISTINCT
    CASE WHEN NULLIF(trim(registro_ans), '') ~ '^[0-9]+$' THEN trim(registro_ans)::int ELSE NULL END AS registro_ans,
    upper(NULLIF(trim(uf), '')) AS uf_raw
  FROM stg_despesa_trimestral
),
faltantes AS (
  SELECT r.registro_ans, r.uf_raw
  FROM reg r
  LEFT JOIN operadora o ON o.registro_ans = r.registro_ans
  WHERE r.registro_ans IS NOT NULL AND o.registro_ans IS NULL
)
INSERT INTO operadora (registro_ans, uf)
SELECT
  registro_ans,
  CASE WHEN uf_raw ~ '^[A-Z]{2}$' THEN uf_raw::char(2) ELSE NULL END
FROM faltantes
ON CONFLICT (registro_ans) DO NOTHING;

-- 3.2.2) converter / rejeitar / upsert no fato
WITH cleaned AS (
  SELECT
    NULLIF(trim(registro_ans), '') AS registro_raw,
    NULLIF(trim(ano), '') AS ano_raw,
    NULLIF(trim(trimestre), '') AS trimestre_raw,
    NULLIF(trim(valor_despesas), '') AS valor_raw,
    NULLIF(trim(cnpj_valido), '') AS cnpj_valido_raw,
    NULLIF(trim(valor_positivo), '') AS valor_positivo_raw,
    NULLIF(trim(razao_social_nao_vazia), '') AS razao_social_nao_vazia_raw,
    erros,
    to_jsonb(stg_despesa_trimestral.*) AS payload
  FROM stg_despesa_trimestral
),
typed AS (
  SELECT
    CASE WHEN registro_raw ~ '^[0-9]+$' THEN registro_raw::int ELSE NULL END AS registro_ans,
    CASE WHEN ano_raw ~ '^[0-9]+$' THEN ano_raw::smallint ELSE NULL END AS ano,
    CASE WHEN trimestre_raw ~ '^[0-9]+$' THEN trimestre_raw::smallint ELSE NULL END AS trimestre,
    CASE
      WHEN valor_raw IS NULL THEN NULL
      ELSE (regexp_replace(replace(valor_raw, ',', '.'), '[^0-9\.-]', '', 'g'))::numeric(18,2)
    END AS valor_despesas,
    CASE
      WHEN lower(cnpj_valido_raw) IN ('1','true','t','yes','y') THEN true
      WHEN lower(cnpj_valido_raw) IN ('0','false','f','no','n') THEN false
      ELSE NULL
    END AS cnpj_valido,
    CASE
      WHEN lower(valor_positivo_raw) IN ('1','true','t','yes','y') THEN true
      WHEN lower(valor_positivo_raw) IN ('0','false','f','no','n') THEN false
      ELSE NULL
    END AS valor_positivo,
    CASE
      WHEN lower(razao_social_nao_vazia_raw) IN ('1','true','t','yes','y') THEN true
      WHEN lower(razao_social_nao_vazia_raw) IN ('0','false','f','no','n') THEN false
      ELSE NULL
    END AS razao_social_nao_vazia,
    erros,
    payload
  FROM cleaned
),
rej AS (
  INSERT INTO import_rejeitados (origem, motivo, payload)
  SELECT 'despesa_trimestral', 'campo obrigatorio ausente/invalido', payload
  FROM typed
  WHERE registro_ans IS NULL OR ano IS NULL OR trimestre IS NULL OR valor_despesas IS NULL
  RETURNING 1
)
INSERT INTO despesa_trimestral (
  registro_ans, ano, trimestre, valor_despesas,
  cnpj_valido, valor_positivo, razao_social_nao_vazia, erros
)
SELECT
  registro_ans, ano, trimestre, valor_despesas,
  cnpj_valido, valor_positivo, razao_social_nao_vazia, erros
FROM typed
WHERE registro_ans IS NOT NULL
  AND ano IS NOT NULL
  AND trimestre IS NOT NULL
  AND valor_despesas IS NOT NULL
ON CONFLICT (registro_ans, ano, trimestre) DO UPDATE SET
  valor_despesas = EXCLUDED.valor_despesas,
  cnpj_valido = COALESCE(EXCLUDED.cnpj_valido, despesa_trimestral.cnpj_valido),
  valor_positivo = COALESCE(EXCLUDED.valor_positivo, despesa_trimestral.valor_positivo),
  razao_social_nao_vazia = COALESCE(EXCLUDED.razao_social_nao_vazia, despesa_trimestral.razao_social_nao_vazia),
  erros = COALESCE(EXCLUDED.erros, despesa_trimestral.erros);

-- ---------------------------------------------------------
-- 3.3) Agregadas (teste 2.3) -> despesa_agregada_operadora_uf
-- Regras:
-- - Obrigatórios: razao_social, uf, total_despesas (senão rejeita)
-- - monetários: mesmo saneamento (vírgula->ponto + regex)
-- - qtd_registros: int quando possível, senão NULL
-- ---------------------------------------------------------
WITH cleaned AS (
  SELECT
    NULLIF(trim(razao_social), '') AS razao_social,
    upper(NULLIF(trim(uf), '')) AS uf_raw,
    NULLIF(trim(total_despesas), '') AS total_raw,
    NULLIF(trim(media_trimestral), '') AS media_raw,
    NULLIF(trim(desvio_padrao), '') AS dp_raw,
    NULLIF(trim(qtd_registros), '') AS qtd_raw,
    to_jsonb(stg_despesa_agregada.*) AS payload
  FROM stg_despesa_agregada
),
typed AS (
  SELECT
    razao_social,
    CASE WHEN uf_raw ~ '^[A-Z]{2}$' THEN uf_raw::char(2) ELSE NULL END AS uf,
    CASE
      WHEN total_raw IS NULL THEN NULL
      ELSE (regexp_replace(replace(total_raw, ',', '.'), '[^0-9\.-]', '', 'g'))::numeric(18,2)
    END AS total_despesas,
    CASE
      WHEN media_raw IS NULL OR media_raw = '' THEN NULL
      ELSE (regexp_replace(replace(media_raw, ',', '.'), '[^0-9\.-]', '', 'g'))::numeric(18,2)
    END AS media_trimestral,
    CASE
      WHEN dp_raw IS NULL OR dp_raw = '' THEN NULL
      ELSE (regexp_replace(replace(dp_raw, ',', '.'), '[^0-9\.-]', '', 'g'))::numeric(18,2)
    END AS desvio_padrao,
    CASE WHEN qtd_raw ~ '^[0-9]+$' THEN qtd_raw::int ELSE NULL END AS qtd_registros,
    payload
  FROM cleaned
),
rej AS (
  INSERT INTO import_rejeitados (origem, motivo, payload)
  SELECT 'despesa_agregada', 'razao_social/uf/total invalidos', payload
  FROM typed
  WHERE razao_social IS NULL OR uf IS NULL OR total_despesas IS NULL
  RETURNING 1
)
INSERT INTO despesa_agregada_operadora_uf (
  razao_social, uf, total_despesas, media_trimestral, desvio_padrao, qtd_registros
)
SELECT
  razao_social, uf, total_despesas, media_trimestral, desvio_padrao, qtd_registros
FROM typed
WHERE razao_social IS NOT NULL
  AND uf IS NOT NULL
  AND total_despesas IS NOT NULL
ON CONFLICT (razao_social, uf) DO UPDATE SET
  total_despesas = EXCLUDED.total_despesas,
  media_trimestral = COALESCE(EXCLUDED.media_trimestral, despesa_agregada_operadora_uf.media_trimestral),
  desvio_padrao = COALESCE(EXCLUDED.desvio_padrao, despesa_agregada_operadora_uf.desvio_padrao),
  qtd_registros = COALESCE(EXCLUDED.qtd_registros, despesa_agregada_operadora_uf.qtd_registros);

COMMIT;

-- =========================================================
-- Sanity checks rápidas (rode manualmente)
-- =========================================================
-- SELECT COUNT(*) AS operadoras FROM operadora;
-- SELECT COUNT(*) AS fatos FROM despesa_trimestral;
-- SELECT COUNT(*) AS agregadas FROM despesa_agregada_operadora_uf;
-- SELECT origem, motivo, COUNT(*) FROM import_rejeitados GROUP BY 1,2 ORDER BY 3 DESC;
