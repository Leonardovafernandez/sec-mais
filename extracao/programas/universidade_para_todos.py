"""
Extrator do programa Universidade Para Todos (UPT).

Realiza a extração dos dados do programa Universidade Para Todos
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

NOME_PROGRAMA = "universidade_para_todos"

# =============================================================================
# QUERY DE EXTRAÇÃO - SGBD: Postgres 16 | Banco: UPT | Esquema: UPT
# =============================================================================
QUERY_UPT = """
    SELECT 
        dc.MATRICULA,
        dp.NOME AS NOME_ESTUDANTE,
        dp.NOME_SOCIAL AS NOME_SOCIAL_ESTUDANTE,
        u.CPF AS CPF_ESTUDANTE,
        i.ID AS NUMERO_INSCRICAO,
        si.STATUS AS STATUS_UPT
    FROM {schema}.USUARIO u
    LEFT JOIN {schema}.DADO_CANDIDATO dc ON u.ID = dc.USUARIO_ID
    LEFT JOIN {schema}.DADOS_PESSOAIS dp ON u.ID = dp.USUARIO_ID
    LEFT JOIN {schema}.INSCRICAO i ON u.ID = i.USUARIO_ID
    LEFT JOIN {schema}.VW_STATUS_INSCRICOES vsi ON i.ID = vsi.INSCRICAO_ID
    LEFT JOIN {schema}.STATUS_INSCRICAO si ON vsi.STATUS_INSCRICAO_ID = si.ID
"""
# =============================================================================


def extrair_universidade_para_todos(
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    data_execucao: datetime | None = None,
    verificar_vpn: bool = True,
) -> Path:
    """
    Extrai dados do programa Universidade Para Todos e salva na camada bronze.

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

    logger.info(f"🚀 Iniciando extração do UPT | Execução: {data_execucao}")

    from config.settings import configuracoes_postgres_upt

    if verificar_vpn:
        logger.info("Verificando conectividade VPN UPT...")
        if not verificar_vpn_postgres(host=configuracoes_postgres_upt.host, port=configuracoes_postgres_upt.port):
            raise ConnectionError(
                "VPN não está ativa ou host UPT inacessível. Verifique a conexão com a VPN."
            )

    params = {}
    if data_inicio:
        params["data_inicio"] = data_inicio
        params["data_fim"] = data_fim
        logger.info(f"Período de extração: {data_inicio} até {data_fim}")

    logger.info("Conectando ao banco PostgreSQL...")

    from config.settings import configuracoes_postgres_upt

    with ConectorPostgres(config=configuracoes_postgres_upt, verificar_vpn=False) as conector:
        schema = configuracoes_postgres_upt.schema or "UPT"
        query = QUERY_UPT.format(schema=schema)

        df = conector.executar_query(query, params=params if params else None)

    if df.empty:
        logger.warning("⚠️  Nenhum dado encontrado na extração do UPT")
    else:
        logger.info(f"📊 Dados extraídos: {len(df)} linhas, {len(df.columns)} colunas")

    df["_data_extracao"] = data_execucao
    df["_programa"] = NOME_PROGRAMA

    caminho_particao = obter_caminho_particao("bronze", NOME_PROGRAMA, data_execucao)
    nome_arquivo = f"upt_{data_execucao.strftime('%Y%m%d_%H%M%S')}.parquet"
    caminho_arquivo = caminho_particao / nome_arquivo

    logger.info(f"Salvando dados em: {caminho_arquivo}")

    df.to_parquet(caminho_arquivo, engine="pyarrow", compression="snappy", index=False)

    logger.info(f"✅ Extração UPT concluída! Arquivo: {caminho_arquivo}")
    return caminho_arquivo


if __name__ == "__main__":
    configurar_logging()
    try:
        arquivo = extrair_universidade_para_todos()
        logger.info(f"Extração finalizada: {arquivo}")
    except Exception as e:
        logger.error(f"Falha na extração: {e}")
        raise
