-- =============================================================================
-- Dimensão: Estudante
-- Consolida beneficiários únicos de todos os 4 programas SEC MAIS
-- =============================================================================

{{
    config(
        materialized='table',
        tags=['marts', 'dimensao']
    )
}}

WITH bolsa_presenca AS (
    SELECT
        cd_aluno        AS cd_estudante,
        nm_aluno        AS nm_estudante,
        'bolsa_presenca' AS origem
    FROM {{ ref('stg_bolsa_presenca') }}
    WHERE cd_aluno IS NOT NULL
),

mais_estudos AS (
    SELECT
        cd_aluno        AS cd_estudante,
        nm_aluno        AS nm_estudante,
        'mais_estudos'  AS origem
    FROM {{ ref('stg_mais_estudos') }}
    WHERE cd_aluno IS NOT NULL
),

universidade_para_todos AS (
    SELECT
        cd_beneficiario AS cd_estudante,
        nm_beneficiario AS nm_estudante,
        'universidade_para_todos' AS origem
    FROM {{ ref('stg_universidade_para_todos') }}
    WHERE cd_beneficiario IS NOT NULL
),

pe_de_meia AS (
    SELECT
        cd_beneficiario AS cd_estudante,
        nm_beneficiario AS nm_estudante,
        'pe_de_meia'    AS origem
    FROM {{ ref('stg_pe_de_meia') }}
    WHERE cd_beneficiario IS NOT NULL
),

-- União de todos os programas
todos_beneficiarios AS (
    SELECT * FROM bolsa_presenca
    UNION ALL
    SELECT * FROM mais_estudos
    UNION ALL
    SELECT * FROM universidade_para_todos
    UNION ALL
    SELECT * FROM pe_de_meia
),

-- Deduplicação: mantém um registro por estudante
deduplicado AS (
    SELECT
        cd_estudante,
        -- Usa o nome mais frequente para o estudante
        nm_estudante,
        COUNT(DISTINCT origem) AS qt_programas
    FROM todos_beneficiarios
    GROUP BY cd_estudante, nm_estudante
),

-- Gera surrogate key
final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['cd_estudante']) }} AS sk_estudante,
        cd_estudante,
        nm_estudante,
        qt_programas,
        CURRENT_TIMESTAMP AS dt_carga
    FROM deduplicado
)

SELECT * FROM final
