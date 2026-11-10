-- =============================================================================
-- Staging: Universidade Para Todos (UPT)
-- Fonte: Camada Ouro (Parquet local)
-- =============================================================================

{{
    config(
        materialized='view',
        tags=['staging', 'universidade_para_todos']
    )
}}

WITH fonte AS (

    SELECT *
    FROM read_parquet(
        '{{ var("storage_base_path") }}/ouro/universidade_para_todos/**/*.parquet'
    )

),

renomeado AS (

    SELECT
        -- Identificação do beneficiário
        cd_beneficiario::VARCHAR    AS cd_beneficiario,
        nm_beneficiario::VARCHAR    AS nm_beneficiario,

        -- Instituição e curso
        -- cd_instituicao::VARCHAR  AS cd_instituicao,
        -- nm_instituicao::VARCHAR  AS nm_instituicao,
        -- nm_curso::VARCHAR        AS nm_curso,

        -- Período e benefício
        -- dt_inicio_beneficio::DATE AS dt_inicio_beneficio,
        -- dt_fim_beneficio::DATE   AS dt_fim_beneficio,
        -- vl_bolsa::DOUBLE         AS vl_bolsa,
        -- st_situacao::VARCHAR     AS st_situacao,

        dt_referencia::DATE         AS dt_referencia,

        -- Metadados
        _dt_processamento_ouro::VARCHAR AS dt_processamento_ouro,
        'universidade_para_todos'   AS nm_programa

    FROM fonte

)

SELECT * FROM renomeado
