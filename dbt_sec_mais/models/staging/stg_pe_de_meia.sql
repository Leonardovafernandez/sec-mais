-- =============================================================================
-- Staging: Pé-de-Meia
-- Fonte: Camada Ouro (Parquet local)
-- =============================================================================

{{
    config(
        materialized='view',
        tags=['staging', 'pe_de_meia']
    )
}}

WITH fonte AS (

    SELECT *
    FROM read_parquet(
        '{{ var("storage_base_path") }}/ouro/pe_de_meia/**/*.parquet'
    )

),

renomeado AS (

    SELECT
        -- Identificação do beneficiário
        cd_beneficiario::VARCHAR    AS cd_beneficiario,
        nm_beneficiario::VARCHAR    AS nm_beneficiario,

        -- Poupança e situação
        -- cd_escola::VARCHAR       AS cd_escola,
        -- nm_escola::VARCHAR       AS nm_escola,
        -- cd_serie::VARCHAR        AS cd_serie,
        -- vl_poupanca_acumulada::DOUBLE AS vl_poupanca_acumulada,
        -- vl_deposito_mensal::DOUBLE AS vl_deposito_mensal,
        -- st_situacao::VARCHAR     AS st_situacao,

        dt_referencia::DATE         AS dt_referencia,

        -- Metadados
        _dt_processamento_ouro::VARCHAR AS dt_processamento_ouro,
        'pe_de_meia'                AS nm_programa

    FROM fonte

)

SELECT * FROM renomeado
