"""
Extrator do programa Pé-de-Meia.

Realiza a extração dos dados do programa Pé-de-Meia
do banco PostgreSQL, salvando os dados brutos na camada bronze
no formato Parquet, particionados por data de execução.

IMPORTANTE: Requer VPN ativa para acessar o banco PostgreSQL.
"""

from datetime import datetime
from pathlib import Path

from loguru import logger

from config.logging_config import configurar_logging
from extracao.conectores.postgres_connector import ConectorPostgres
from utils.storage import obter_caminho_particao
from utils.vpn_check import verificar_vpn_postgres

NOME_PROGRAMA = "pe_de_meia"

# =============================================================================
# QUERY DE EXTRAÇÃO - SGBD: Postgres 13.13 | Banco: SIGEDUC | Esquema: integracao_sgp_beneficio_estudantil
# =============================================================================
QUERY_PE_DE_MEIA = """
    SELECT 
        em.CO_MATRICULA_REDE AS MATRICULA,
        es.ESTUDANTE_NOME AS NOME_ESTUDANTE,
        es.ESTUDANTE_CPF AS CPF_ESTUDANTE,
        em.NU_ANO_MATRICULA AS ANO,
        em.ESTUDANTE_MATRICULA_SITUACAO_DESCRICAO AS STATUS_PE_DE_MEIA
    FROM {schema}.ESTUDANTES_SGP es
    INNER JOIN {schema}.ESTUDANTES_SGP_MATRICULAS em
        ON es.ID_SGP_ESTUDANTE = em.ID_SGP_ESTUDANTE
"""
# =============================================================================


def extrair_pe_de_meia(
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    data_execucao: datetime | None = None,
    verificar_vpn: bool = True,
) -> Path:
    """
    Extrai dados do programa Pé-de-Meia e salva na camada bronze.

    Args:
        data_inicio: Data de início para filtro da extração.
        data_fim: Data de fim para filtro da extração.
        data_execucao: Data de execução para particionamento.
        verificar_vpn: Se True, verifica VPN antes de extrair.

    Returns:
        Path do arquivo Parquet salvo.

    Raises:
        ConnectionError: Se a VPN não estiver ativa.
    """
    if data_execucao is None:
        data_execucao = datetime.now()

    if data_fim is None:
        data_fim = datetime.now()

    logger.info(f"🚀 Iniciando extração do Pé-de-Meia | Execução: {data_execucao}")

    if verificar_vpn:
        logger.info("Verificando conectividade VPN...")
        if not verificar_vpn_postgres():
            raise ConnectionError(
                "VPN não está ativa. Ative a VPN antes de executar a extração do Pé-de-Meia."
            )

    params = {}
    if data_inicio:
        params["data_inicio"] = data_inicio
        params["data_fim"] = data_fim
        logger.info(f"Período de extração: {data_inicio} até {data_fim}")

    logger.info("Conectando ao banco PostgreSQL...")

    from config.settings import configuracoes_postgres_pdm

    with ConectorPostgres(config=configuracoes_postgres_pdm, verificar_vpn=False) as conector:
        schema = configuracoes_postgres_pdm.schema or "integracao_sgp_beneficio_estudantil"
        query = QUERY_PE_DE_MEIA.format(schema=schema)

        df = conector.executar_query(query, params=params if params else None)

    if df.empty:
        logger.warning("⚠️  Nenhum dado encontrado na extração do Pé-de-Meia")
    else:
        logger.info(f"📊 Dados extraídos: {len(df)} linhas, {len(df.columns)} colunas")

    df["_data_extracao"] = data_execucao
    df["_programa"] = NOME_PROGRAMA

    caminho_particao = obter_caminho_particao("bronze", NOME_PROGRAMA, data_execucao)
    nome_arquivo = f"pe_de_meia_{data_execucao.strftime('%Y%m%d_%H%M%S')}.parquet"
    caminho_arquivo = caminho_particao / nome_arquivo

    logger.info(f"Salvando dados em: {caminho_arquivo}")

    df.to_parquet(caminho_arquivo, engine="pyarrow", compression="snappy", index=False)

    logger.info(f"✅ Extração Pé-de-Meia concluída! Arquivo: {caminho_arquivo}")
    return caminho_arquivo


if __name__ == "__main__":
    configurar_logging()
    try:
        arquivo = extrair_pe_de_meia()
        logger.info(f"Extração finalizada: {arquivo}")
    except Exception as e:
        logger.error(f"Falha na extração: {e}")
        raise
