"""
Extrator do programa Mais Estudos.

Realiza a extração dos dados do programa Mais Estudos
do banco Oracle, salvando os dados brutos na camada bronze
no formato Parquet, particionados por data de execução.

IMPORTANTE: Requer VPN ativa para acessar o banco Oracle.
"""

from datetime import datetime
from pathlib import Path

from loguru import logger

from config.logging_config import configurar_logging
from extracao.conectores.oracle_connector import ConectorOracle
from utils.storage import obter_caminho_particao
from utils.vpn_check import verificar_vpn_oracle

NOME_PROGRAMA = "mais_estudos"

# =============================================================================
# QUERY DE EXTRAÇÃO - Preencha com a query real após obter acesso ao banco
# =============================================================================
# Exemplo de estrutura esperada:
#
# QUERY_MAIS_ESTUDOS = """
#     SELECT
#         cd_aluno,
#         nm_aluno,
#         cd_escola,
#         nm_escola,
#         nm_atividade,
#         dt_inicio,
#         dt_fim,
#         nr_horas,
#         st_situacao,
#         cd_municipio,
#         nm_municipio,
#         dt_referencia
#     FROM
#         {schema}.tb_mais_estudos
#     WHERE
#         dt_referencia >= :data_inicio
# """
QUERY_MAIS_ESTUDOS = """
    -- TODO: Substituir pela query real do programa Mais Estudos
    SELECT
        1 AS cd_aluno,
        'ALUNO EXEMPLO' AS nm_aluno,
        SYSDATE AS dt_referencia
    FROM DUAL
"""
# =============================================================================


def extrair_mais_estudos(
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    data_execucao: datetime | None = None,
    verificar_vpn: bool = True,
) -> Path:
    """
    Extrai dados do programa Mais Estudos e salva na camada bronze.

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

    logger.info(f"🚀 Iniciando extração do Mais Estudos | Execução: {data_execucao}")

    if verificar_vpn:
        logger.info("Verificando conectividade VPN...")
        if not verificar_vpn_oracle():
            raise ConnectionError(
                "VPN não está ativa. Ative a VPN antes de executar a extração do Mais Estudos."
            )

    params = {}
    if data_inicio:
        params["data_inicio"] = data_inicio
        params["data_fim"] = data_fim
        logger.info(f"Período de extração: {data_inicio} até {data_fim}")

    logger.info("Conectando ao banco Oracle...")

    with ConectorOracle(verificar_vpn=False) as conector:
        from config.settings import configuracoes_oracle
        schema = configuracoes_oracle.schema or "PUBLIC"
        query = QUERY_MAIS_ESTUDOS.format(schema=schema)

        df = conector.executar_query(query, params=params if params else None)

    if df.empty:
        logger.warning("⚠️  Nenhum dado encontrado na extração do Mais Estudos")
    else:
        logger.info(f"📊 Dados extraídos: {len(df)} linhas, {len(df.columns)} colunas")

    df["_data_extracao"] = data_execucao
    df["_programa"] = NOME_PROGRAMA

    caminho_particao = obter_caminho_particao("bronze", NOME_PROGRAMA, data_execucao)
    nome_arquivo = f"mais_estudos_{data_execucao.strftime('%Y%m%d_%H%M%S')}.parquet"
    caminho_arquivo = caminho_particao / nome_arquivo

    logger.info(f"Salvando dados em: {caminho_arquivo}")

    df.to_parquet(caminho_arquivo, engine="pyarrow", compression="snappy", index=False)

    logger.info(f"✅ Extração Mais Estudos concluída! Arquivo: {caminho_arquivo}")
    return caminho_arquivo


if __name__ == "__main__":
    configurar_logging()
    try:
        arquivo = extrair_mais_estudos()
        logger.info(f"Extração finalizada: {arquivo}")
    except Exception as e:
        logger.error(f"Falha na extração: {e}")
        raise
