"""
Extrator do programa Bolsa Presença.

Realiza a extração dos dados do programa Bolsa Presença
do banco Oracle, salvando os dados brutos na camada bronze
no formato Parquet, particionados por data de execução.

IMPORTANTE: Requer VPN ativa para acessar o banco Oracle.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

from config.logging_config import configurar_logging
from config.settings import configuracoes
from extracao.conectores.oracle_connector import ConectorOracle
from utils.storage import obter_caminho_particao
from utils.vpn_check import verificar_vpn_oracle

# Nome do programa (usado para organizar o armazenamento)
NOME_PROGRAMA = "bolsa_presenca"

# =============================================================================
# QUERY DE EXTRAÇÃO - Preencha com a query real após obter acesso ao banco
# =============================================================================
# Esta query é um placeholder. Substitua pela query real do programa.
# Exemplo de estrutura esperada:
#
# QUERY_BOLSA_PRESENCA = """
#     SELECT
#         cd_aluno,
#         nm_aluno,
#         cd_escola,
#         nm_escola,
#         cd_municipio,
#         nm_municipio,
#         dt_referencia,
#         vl_beneficio,
#         st_pagamento,
#         dt_pagamento,
#         cd_turma,
#         nr_frequencia_percentual
#     FROM
#         {schema}.tb_bolsa_presenca
#     WHERE
#         dt_referencia >= :data_inicio
#         AND dt_referencia <= :data_fim
# """
QUERY_BOLSA_PRESENCA = """
    -- TODO: Substituir pela query real do programa Bolsa Presença
    -- Esta query é um placeholder para desenvolvimento
    SELECT
        1 AS cd_aluno,
        'ALUNO EXEMPLO' AS nm_aluno,
        SYSDATE AS dt_referencia
    FROM DUAL
"""
# =============================================================================


def extrair_bolsa_presenca(
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    data_execucao: datetime | None = None,
    verificar_vpn: bool = True,
) -> Path:
    """
    Extrai dados do programa Bolsa Presença e salva na camada bronze.

    Args:
        data_inicio: Data de início para filtro da extração.
                     Se None, extrai todos os dados disponíveis.
        data_fim: Data de fim para filtro da extração.
                  Se None, usa a data atual.
        data_execucao: Data de execução para particionamento.
                       Se None, usa a data/hora atual.
        verificar_vpn: Se True, verifica VPN antes de extrair.

    Returns:
        Path do arquivo Parquet salvo.

    Raises:
        ConnectionError: Se a VPN não estiver ativa.
        Exception: Se a extração falhar.
    """
    if data_execucao is None:
        data_execucao = datetime.now()

    if data_fim is None:
        data_fim = datetime.now()

    logger.info(f"🚀 Iniciando extração do Bolsa Presença | Execução: {data_execucao}")

    # --- Verificação de VPN ---
    if verificar_vpn:
        logger.info("Verificando conectividade VPN...")
        if not verificar_vpn_oracle():
            raise ConnectionError(
                "VPN não está ativa. Ative a VPN antes de executar a extração do Bolsa Presença."
            )

    # --- Extração ---
    params = {}
    if data_inicio:
        params["data_inicio"] = data_inicio
        params["data_fim"] = data_fim
        logger.info(f"Período de extração: {data_inicio} até {data_fim}")

    logger.info("Conectando ao banco Oracle...")

    with ConectorOracle(verificar_vpn=False) as conector:
        # Ajusta schema na query se necessário
        from config.settings import configuracoes_oracle
        schema = configuracoes_oracle.schema or "PUBLIC"
        query = QUERY_BOLSA_PRESENCA.format(schema=schema)

        df = conector.executar_query(query, params=params if params else None)

    # --- Validação básica ---
    if df.empty:
        logger.warning("⚠️  Nenhum dado encontrado na extração do Bolsa Presença")
    else:
        logger.info(f"📊 Dados extraídos: {len(df)} linhas, {len(df.columns)} colunas")

    # --- Metadados de controle ---
    df["_data_extracao"] = data_execucao
    df["_programa"] = NOME_PROGRAMA

    # --- Persistência na camada bronze ---
    caminho_particao = obter_caminho_particao("bronze", NOME_PROGRAMA, data_execucao)
    nome_arquivo = f"bolsa_presenca_{data_execucao.strftime('%Y%m%d_%H%M%S')}.parquet"
    caminho_arquivo = caminho_particao / nome_arquivo

    logger.info(f"Salvando dados em: {caminho_arquivo}")

    df.to_parquet(
        caminho_arquivo,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )

    logger.info(f"✅ Extração concluída! Arquivo salvo em: {caminho_arquivo}")
    return caminho_arquivo


if __name__ == "__main__":
    configurar_logging()
    try:
        arquivo = extrair_bolsa_presenca()
        logger.info(f"Extração finalizada: {arquivo}")
    except Exception as e:
        logger.error(f"Falha na extração: {e}")
        raise
