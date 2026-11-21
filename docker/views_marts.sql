-- ==============================================================================
-- SPRINT 3: MODELAGEM ANALÍTICA E DISPONIBILIZAÇÃO (VIEWS NO POSTGRESQL DW)
-- Baseado no Star Schema Kimball: ouro.fato_beneficio_estudante e dimensões
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- ATIVIDADE 1: Visão da Participação dos Estudantes nos Programas Selecionados
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW marts.vw_participacao_programas AS
SELECT
    dp.nome_programa,
    dp.orgao_gestor,
    f.ano,
    COALESCE(dt.nome_mes, 'Referência Anual') AS periodo_referencia,
    f.status,
    COUNT(DISTINCT f.id_estudante) AS total_estudantes_participantes,
    dp.possui_valor_financeiro,
    dp.regras_interpretacao
FROM ouro.fato_beneficio_estudante f
JOIN ouro.dim_programa dp ON f.id_programa = dp.id_programa
LEFT JOIN ouro.dim_tempo dt ON f.id_tempo = dt.id_tempo
GROUP BY dp.nome_programa, dp.orgao_gestor, f.ano, dt.nome_mes, f.status, dp.possui_valor_financeiro, dp.regras_interpretacao
ORDER BY dp.nome_programa, f.ano, total_estudantes_participantes DESC;

COMMENT ON VIEW marts.vw_participacao_programas IS 'Atividade 1: Visão agregada da participação discente por programa, período e situação cadastral.';


-- ------------------------------------------------------------------------------
-- ATIVIDADE 2: Estrutura para Identificar a Quantidade de Programas por Matrícula
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW marts.vw_sobreposicao_matriculas AS
WITH programas_por_aluno AS (
    SELECT
        f.id_estudante,
        f.matricula,
        de.nome_estudante,
        de.cpf_mascarado,
        COUNT(DISTINCT f.id_programa) AS qtd_programas_associados,
        BOOL_OR(f.id_programa = 1) AS recebe_bolsa_presenca,
        BOOL_OR(f.id_programa = 2) AS recebe_pe_de_meia,
        BOOL_OR(f.id_programa = 3) AS recebe_upt,
        STRING_AGG(DISTINCT f.programa, ' + ' ORDER BY f.programa) AS combinacao_programas
    FROM ouro.fato_beneficio_estudante f
    JOIN ouro.dim_estudante de ON f.id_estudante = de.id_estudante
    GROUP BY f.id_estudante, f.matricula, de.nome_estudante, de.cpf_mascarado
)
SELECT
    id_estudante,
    COALESCE(matricula, 'SEM MATRÍCULA REGISTRADA') AS matricula_conciliacao,
    nome_estudante,
    cpf_mascarado,
    qtd_programas_associados,
    combinacao_programas,
    recebe_bolsa_presenca,
    recebe_pe_de_meia,
    recebe_upt,
    CASE 
        WHEN qtd_programas_associados >= 2 THEN 'SOBREPOSIÇÃO MULTI-PROGRAMA'
        ELSE 'PROGRAMA ÚNICO'
    END AS classificacao_atendimento
FROM programas_por_aluno
ORDER BY qtd_programas_associados DESC, nome_estudante;

COMMENT ON VIEW marts.vw_sobreposicao_matriculas IS 'Atividade 2: Estrutura analítica que mapeia a quantidade de políticas públicas acumuladas por estudante/matrícula.';


-- Resumo Agregado da Atividade 2 (Distribuição da Sobreposição)
CREATE OR REPLACE VIEW marts.vw_resumo_sobreposicao AS
SELECT
    qtd_programas_associados,
    combinacao_programas,
    COUNT(*) AS total_estudantes,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ())::numeric, 2) AS percentual_representatividade
FROM (
    SELECT
        f.id_estudante,
        COUNT(DISTINCT f.id_programa) AS qtd_programas_associados,
        STRING_AGG(DISTINCT f.programa, ' + ' ORDER BY f.programa) AS combinacao_programas
    FROM ouro.fato_beneficio_estudante f
    GROUP BY f.id_estudante
) sub
GROUP BY qtd_programas_associados, combinacao_programas
ORDER BY qtd_programas_associados DESC, total_estudantes DESC;

COMMENT ON VIEW marts.vw_resumo_sobreposicao IS 'Atividade 2 (Resumo): Quantitativo e percentual de estudantes por nível de sobreposição de benefícios.';


-- ------------------------------------------------------------------------------
-- ATIVIDADE 3: Análise dos Valores Financeiros Individualizados Existentes e Confiáveis
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW marts.vw_analise_financeira_bolsa_presenca AS
SELECT
    COALESCE(dm.nome_municipio, f.municipio, 'NÃO INFORMADO') AS municipio,
    f.ano,
    COALESCE(f.mes, 11) AS mes,
    COUNT(DISTINCT f.id_estudante) AS total_beneficiarios_com_valor,
    ROUND(AVG(f.valor_registrado)::numeric, 2) AS valor_medio_registrado,
    ROUND(MIN(f.valor_registrado)::numeric, 2) AS valor_minimo,
    ROUND(MAX(f.valor_registrado)::numeric, 2) AS valor_maximo,
    ROUND(SUM(f.valor_registrado)::numeric, 2) AS total_recursos_registrados_siadiante,
    'VALOR REGISTRADO NO SIADIANTE (ORACLE) - APENAS BOLSA PRESENÇA APRESENTA VALORES NA FONTE' AS nota_metodologica
FROM ouro.fato_beneficio_estudante f
LEFT JOIN ouro.dim_municipio dm ON f.id_municipio = dm.id_municipio
WHERE f.id_programa = 1  -- Bolsa Presença
  AND f.valor_registrado IS NOT NULL
GROUP BY COALESCE(dm.nome_municipio, f.municipio, 'NÃO INFORMADO'), f.ano, f.mes
ORDER BY total_recursos_registrados_siadiante DESC;

COMMENT ON VIEW marts.vw_analise_financeira_bolsa_presenca IS 'Atividade 3: Análise agregada dos valores financeiros individualizados confiáveis do Bolsa Presença (SIADIANTE).';


-- ------------------------------------------------------------------------------
-- ATIVIDADE 5: Cobertura e Qualidade dos Relacionamentos entre as Fontes
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW marts.vw_cobertura_relacionamento_fontes AS
SELECT
    f.origem_dado,
    f.programa,
    COUNT(*) AS total_registros_fato,
    COUNT(DISTINCT f.id_estudante) AS estudantes_distintos,
    SUM(CASE WHEN f.matricula IS NOT NULL AND f.matricula <> '' THEN 1 ELSE 0 END) AS registros_com_matricula,
    SUM(CASE WHEN f.matricula IS NULL OR f.matricula = '' THEN 1 ELSE 0 END) AS registros_sem_matricula,
    ROUND((SUM(CASE WHEN f.matricula IS NOT NULL AND f.matricula <> '' THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) AS taxa_conformidade_matricula,
    CASE
        WHEN f.origem_dado = 'UPT (PostgreSQL)' THEN 'Inscrições abertas a egressos externos da rede estadual podem não possuir matrícula escolar ativa'
        WHEN f.origem_dado = 'SIADIANTE (Oracle)' THEN '100% dos registros possuem matrícula de rede validada'
        ELSE 'Matrículas de ensino médio migradas do SIGEDUC'
    END AS diagnostico_causa_ausencia
FROM ouro.fato_beneficio_estudante f
GROUP BY f.origem_dado, f.programa;

COMMENT ON VIEW marts.vw_cobertura_relacionamento_fontes IS 'Atividade 5: Avaliação da cobertura, qualidade de preenchimento e integridade referencial entre as fontes.';


-- ------------------------------------------------------------------------------
-- ATIVIDADE 10: Indicadores Executivos e Síntese de Entrega do Projeto Aplicado
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW marts.vw_indicadores_executivos_sprint3 AS
SELECT
    (SELECT COUNT(DISTINCT id_estudante) FROM ouro.dim_estudante) AS total_estudantes_unicos_atendidos,
    (SELECT COUNT(*) FROM ouro.fato_beneficio_estudante) AS total_concessoes_registradas,
    (SELECT COUNT(DISTINCT id_estudante) FROM ouro.fato_beneficio_estudante WHERE id_programa = 1) AS beneficiarios_bolsa_presenca,
    (SELECT COUNT(DISTINCT id_estudante) FROM ouro.fato_beneficio_estudante WHERE id_programa = 2) AS beneficiarios_pe_de_meia,
    (SELECT COUNT(DISTINCT id_estudante) FROM ouro.fato_beneficio_estudante WHERE id_programa = 3) AS inscritos_universidade_para_todos,
    (SELECT COUNT(*) FROM marts.vw_sobreposicao_matriculas WHERE qtd_programas_associados >= 2) AS total_estudantes_em_multiplos_programas,
    (SELECT ROUND((COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT id_estudante) FROM ouro.dim_estudante))::numeric, 2) FROM marts.vw_sobreposicao_matriculas WHERE qtd_programas_associados >= 2) AS percentual_taxa_sobreposicao,
    (SELECT ROUND(SUM(valor_registrado)::numeric, 2) FROM ouro.fato_beneficio_estudante WHERE id_programa = 1) AS montante_financeiro_bolsa_presenca;

COMMENT ON VIEW marts.vw_indicadores_executivos_sprint3 IS 'Atividade 10: Quadro sintético de indicadores globais do TCC SEC MAIS pronto para apresentação.';
