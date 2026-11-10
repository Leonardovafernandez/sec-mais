-- =============================================================================
-- Fato: Benefícios
-- Integra os 4 programas SEC MAIS em uma visão unificada de benefícios
-- =============================================================================
-- Esta tabela fato permite análises consolidadas como:
-- - Total de benefícios por estudante
-- - Estudantes que participam de múltiplos programas
-- - Evolução dos benefícios ao longo do tempo
-- - Distribuição geográfica dos beneficiários

{{
    config(
        materialized='table',
        tags=['marts', 'fato'],
        sort=['dt_referencia', 'cd_programa'],
        dist='cd_estudante'
    )
}}

WITH bolsa_presenca AS (
    SELECT
        cd_aluno                AS cd_estudante,
        nm_aluno                AS nm_estudante,
        'bolsa_presenca'        AS cd_programa,
        dt_referencia,
        -- Campos específicos (descomentar quando o schema real for conhecido)
        -- cd_escola,
        -- nm_escola,
        -- cd_municipio,
        -- nm_municipio,
        -- vl_beneficio         AS vl_beneficio,
        -- st_pagamento,
        -- nr_frequencia_percentual,
        NULL::DOUBLE             AS vl_beneficio,
        NULL::VARCHAR            AS nm_municipio,
        NULL::VARCHAR            AS nm_escola,
        dt_processamento_ouro
    FROM {{ ref('stg_bolsa_presenca') }}
),

universidade_para_todos AS (
    SELECT
        cd_beneficiario         AS cd_estudante,
        nm_beneficiario         AS nm_estudante,
        'universidade_para_todos' AS cd_programa,
        dt_referencia,
        -- vl_bolsa             AS vl_beneficio,
        -- nm_municipio,
        -- nm_instituicao       AS nm_escola,
        NULL::DOUBLE             AS vl_beneficio,
        NULL::VARCHAR            AS nm_municipio,
        NULL::VARCHAR            AS nm_escola,
        dt_processamento_ouro
    FROM {{ ref('stg_universidade_para_todos') }}
),

mais_estudos AS (
    SELECT
        cd_aluno                AS cd_estudante,
        nm_aluno                AS nm_estudante,
        'mais_estudos'          AS cd_programa,
        dt_referencia,
        -- NULL                 AS vl_beneficio,  -- Mais Estudos não tem valor monetário direto
        -- nm_municipio,
        -- nm_escola,
        NULL::DOUBLE             AS vl_beneficio,
        NULL::VARCHAR            AS nm_municipio,
        NULL::VARCHAR            AS nm_escola,
        dt_processamento_ouro
    FROM {{ ref('stg_mais_estudos') }}
),

pe_de_meia AS (
    SELECT
        cd_beneficiario         AS cd_estudante,
        nm_beneficiario         AS nm_estudante,
        'pe_de_meia'            AS cd_programa,
        dt_referencia,
        -- vl_deposito_mensal   AS vl_beneficio,
        -- nm_municipio,
        -- nm_escola,
        NULL::DOUBLE             AS vl_beneficio,
        NULL::VARCHAR            AS nm_municipio,
        NULL::VARCHAR            AS nm_escola,
        dt_processamento_ouro
    FROM {{ ref('stg_pe_de_meia') }}
),

-- União de todos os programas
todos_beneficios AS (
    SELECT * FROM bolsa_presenca
    UNION ALL
    SELECT * FROM universidade_para_todos
    UNION ALL
    SELECT * FROM mais_estudos
    UNION ALL
    SELECT * FROM pe_de_meia
),

-- Enriquecimento com as dimensões
final AS (
    SELECT
        -- Surrogate key do benefício
        {{ dbt_utils.generate_surrogate_key(['b.cd_estudante', 'b.cd_programa', 'b.dt_referencia']) }} AS sk_beneficio,

        -- Chaves estrangeiras para as dimensões
        e.sk_estudante,
        p.sk_programa,

        -- Atributos degenerados (descomentar quando disponíveis)
        b.cd_estudante,
        b.nm_estudante,
        b.cd_programa,
        b.dt_referencia,
        b.vl_beneficio,
        b.nm_municipio,
        b.nm_escola,

        -- Período (para facilitar análises temporais)
        EXTRACT(YEAR FROM b.dt_referencia)  AS ano_referencia,
        EXTRACT(MONTH FROM b.dt_referencia) AS mes_referencia,

        -- Metadados
        b.dt_processamento_ouro,
        CURRENT_TIMESTAMP AS dt_carga

    FROM todos_beneficios AS b
    LEFT JOIN {{ ref('dim_estudante') }} AS e
        ON b.cd_estudante = e.cd_estudante
    LEFT JOIN {{ ref('dim_programa') }} AS p
        ON b.cd_programa = p.cd_programa
)

SELECT * FROM final
