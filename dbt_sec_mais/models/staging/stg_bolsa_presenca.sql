-- =============================================================================
-- Staging: Bolsa Presença
-- Fonte: Camada Ouro (Parquet local)
-- =============================================================================
-- Este model lê os arquivos Parquet da camada ouro e prepara os dados
-- para consumo pela camada marts, aplicando tipagens e renomeações.

{{
    config(
        materialized='view',
        tags=['staging', 'bolsa_presenca']
    )
}}

WITH fonte AS (

    SELECT *
    FROM read_parquet(
        '{{ var("storage_base_path") }}/ouro/bolsa_presenca/**/*.parquet'
    )

),

renomeado AS (

    SELECT
        -- Identificação do aluno
        cd_aluno::VARCHAR           AS cd_aluno,
        nm_aluno::VARCHAR           AS nm_aluno,

        -- Escola
        -- cd_escola::VARCHAR       AS cd_escola,
        -- nm_escola::VARCHAR       AS nm_escola,

        -- Localização
        -- cd_municipio::VARCHAR    AS cd_municipio,
        -- nm_municipio::VARCHAR    AS nm_municipio,

        -- Período e benefício
        -- dt_referencia::DATE      AS dt_referencia,
        -- vl_beneficio::DOUBLE     AS vl_beneficio,
        -- st_pagamento::VARCHAR    AS st_pagamento,
        -- nr_frequencia_percentual::DOUBLE AS nr_frequencia_percentual,

        dt_referencia::DATE         AS dt_referencia,

        -- Metadados de controle
        _dt_processamento_ouro::VARCHAR AS dt_processamento_ouro,
        'bolsa_presenca'            AS nm_programa

    FROM fonte

)

SELECT * FROM renomeado
