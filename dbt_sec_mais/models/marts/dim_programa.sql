-- =============================================================================
-- Dimensão: Programa
-- Catálogo dos 4 programas SEC MAIS com metadados
-- =============================================================================

{{
    config(
        materialized='table',
        tags=['marts', 'dimensao']
    )
}}

WITH programas AS (

    SELECT *
    FROM (VALUES
        (
            'bolsa_presenca',
            'Bolsa Presença',
            'Programa de incentivo à frequência escolar dos alunos da rede estadual da Bahia',
            'Oracle',
            TRUE
        ),
        (
            'universidade_para_todos',
            'Universidade Para Todos (UPT)',
            'Programa de acesso à educação superior para estudantes da rede pública da Bahia',
            'PostgreSQL',
            TRUE
        ),
        (
            'mais_estudos',
            'Mais Estudos',
            'Programa de atividades educacionais complementares em período contraturno',
            'Oracle',
            TRUE
        ),
        (
            'pe_de_meia',
            'Pé-de-Meia',
            'Programa de poupança estudantil para alunos do ensino médio da rede estadual',
            'PostgreSQL',
            TRUE
        )
    ) AS t(cd_programa, nm_programa, ds_programa, nm_fonte_dados, fl_ativo)

)

SELECT
    {{ dbt_utils.generate_surrogate_key(['cd_programa']) }} AS sk_programa,
    cd_programa,
    nm_programa,
    ds_programa,
    nm_fonte_dados,
    fl_ativo,
    CURRENT_TIMESTAMP AS dt_carga
FROM programas
