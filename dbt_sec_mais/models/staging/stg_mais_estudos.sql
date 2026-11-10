-- =============================================================================
-- Staging: Mais Estudos
-- Fonte: Camada Ouro (Parquet local)
-- =============================================================================

{{
    config(
        materialized='view',
        tags=['staging', 'mais_estudos']
    )
}}

WITH fonte AS (

    SELECT *
    FROM read_parquet(
        '{{ var("storage_base_path") }}/ouro/mais_estudos/**/*.parquet'
    )

),

renomeado AS (

    SELECT
        -- Identificação do aluno
        cd_aluno::VARCHAR           AS cd_aluno,
        nm_aluno::VARCHAR           AS nm_aluno,

        -- Atividade
        -- cd_escola::VARCHAR       AS cd_escola,
        -- nm_escola::VARCHAR       AS nm_escola,
        -- nm_atividade::VARCHAR    AS nm_atividade,
        -- nr_horas::INTEGER        AS nr_horas,
        -- st_situacao::VARCHAR     AS st_situacao,

        dt_referencia::DATE         AS dt_referencia,

        -- Metadados
        _dt_processamento_ouro::VARCHAR AS dt_processamento_ouro,
        'mais_estudos'              AS nm_programa

    FROM fonte

)

SELECT * FROM renomeado
