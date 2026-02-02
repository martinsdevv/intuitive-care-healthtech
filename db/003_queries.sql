-- Teste 3 — Queries Analíticas

SET search_path TO healthtech;

-- =========================================================
-- Query 1
-- Quais as 5 operadoras com maior crescimento percentual de despesas
-- entre o primeiro e o último trimestre analisado?
--
-- Tratamento do desafio (faltam trimestres):
-- - Para cada operadora, usamos o primeiro e o último trimestre DISPONÍVEL no dataset carregado,
--   ao invés de exigir presença nos mesmos 2 trimestres globais.
-- - Se valor inicial <= 0, crescimento percentual fica indefinido; esses casos são excluídos.
-- =========================================================
WITH ranked AS (
  SELECT
    d.registro_ans,
    d.ano,
    d.trimestre,
    d.valor_despesas,
    row_number() OVER (PARTITION BY d.registro_ans ORDER BY d.ano, d.trimestre) AS rn_first,
    row_number() OVER (PARTITION BY d.registro_ans ORDER BY d.ano DESC, d.trimestre DESC) AS rn_last
  FROM despesa_trimestral d
),
first_last AS (
  SELECT
    registro_ans,
    MAX(CASE WHEN rn_first = 1 THEN valor_despesas END) AS valor_inicial,
    MAX(CASE WHEN rn_last  = 1 THEN valor_despesas END) AS valor_final
  FROM ranked
  GROUP BY registro_ans
),
calc AS (
  SELECT
    o.registro_ans,
    COALESCE(o.razao_social, '(sem razao_social)') AS razao_social,
    o.uf,
    fl.valor_inicial,
    fl.valor_final,
    ((fl.valor_final - fl.valor_inicial) / NULLIF(fl.valor_inicial, 0)) * 100.0 AS crescimento_percentual
  FROM first_last fl
  JOIN operadora o ON o.registro_ans = fl.registro_ans
  WHERE fl.valor_inicial IS NOT NULL
    AND fl.valor_final IS NOT NULL
    AND fl.valor_inicial > 0
)
SELECT
  registro_ans,
  razao_social,
  uf,
  valor_inicial,
  valor_final,
  crescimento_percentual
FROM calc
ORDER BY crescimento_percentual DESC
LIMIT 5;

-- =========================================================
-- Query 2
-- Qual a distribuição de despesas por UF? Liste os 5 estados com maiores
-- despesas totais e calcule também a média de despesas por operadora em cada UF.
--
-- Estratégia:
-- 1) Total por (UF, operadora)
-- 2) Agrega por UF: total + média por operadora + contagem de operadoras
-- =========================================================
WITH por_operadora_uf AS (
  SELECT
    o.uf,
    d.registro_ans,
    SUM(d.valor_despesas) AS total_operadora_uf
  FROM despesa_trimestral d
  JOIN operadora o ON o.registro_ans = d.registro_ans
  WHERE o.uf IS NOT NULL
  GROUP BY o.uf, d.registro_ans
),
por_uf AS (
  SELECT
    uf,
    SUM(total_operadora_uf) AS total_despesas_uf,
    AVG(total_operadora_uf) AS media_despesas_por_operadora_uf,
    COUNT(*) AS qtd_operadoras_na_uf
  FROM por_operadora_uf
  GROUP BY uf
)
SELECT
  uf,
  total_despesas_uf,
  media_despesas_por_operadora_uf,
  qtd_operadoras_na_uf
FROM por_uf
ORDER BY total_despesas_uf DESC
LIMIT 5;

-- =========================================================
-- Query 3
-- Quantas operadoras tiveram despesas acima da média geral em pelo menos
-- 2 dos 3 trimestres analisados?
--
-- Observação:
-- - Usamos os 3 primeiros períodos (ano,trimestre) disponíveis ordenados.
-- - Calculamos a média global por período.
-- - Contamos, por operadora, em quantos períodos ela ficou acima da média.
-- =========================================================
WITH periodos AS (
  SELECT ano, trimestre
  FROM (
    SELECT DISTINCT ano, trimestre
    FROM despesa_trimestral
    ORDER BY ano, trimestre
  ) p
  LIMIT 3
),
media_por_periodo AS (
  SELECT d.ano, d.trimestre, AVG(d.valor_despesas) AS media_geral_periodo
  FROM despesa_trimestral d
  JOIN periodos p USING (ano, trimestre)
  GROUP BY d.ano, d.trimestre
),
comparacao AS (
  SELECT
    d.registro_ans,
    d.ano,
    d.trimestre,
    (d.valor_despesas > m.media_geral_periodo) AS acima_media
  FROM despesa_trimestral d
  JOIN media_por_periodo m USING (ano, trimestre)
),
contagem AS (
  SELECT
    registro_ans,
    COUNT(*) FILTER (WHERE acima_media) AS qtd_trimestres_acima
  FROM comparacao
  GROUP BY registro_ans
)
SELECT
  COUNT(*) AS operadoras_acima_media_em_pelo_menos_2_trimestres
FROM contagem
WHERE qtd_trimestres_acima >= 2;
