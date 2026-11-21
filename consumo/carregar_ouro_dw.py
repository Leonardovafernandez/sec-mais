"""
Script de Carga da Camada Ouro para o Data Warehouse Analítico (PostgreSQL Docker)
Sprint 3: Modelagem Analítica e Consumo

Lê os dados da Camada Ouro (armazenamento/ouro/fct_estudantes_beneficios_integrados.parquet),
persiste na tabela `ouro.fct_estudantes_beneficios_integrados` no PostgreSQL local (container Docker),
e em seguida aplica as visões analíticas da camada `marts`.
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

# Adiciona o diretório raiz ao path para importação das configurações
PROJETO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJETO_ROOT))

from config.settings import configuracoes_postgres_dw, configuracoes
from config.logging_config import configurar_logging


def obter_engine_dw():
    """Cria e retorna o engine SQLAlchemy para o PostgreSQL local do DW."""
    conn_str = (
        f"postgresql+psycopg2://{configuracoes_postgres_dw.user}:{configuracoes_postgres_dw.password}"
        f"@{configuracoes_postgres_dw.host}:{configuracoes_postgres_dw.port}/{configuracoes_postgres_dw.database}"
    )
    return create_engine(conn_str)


def carregar_ouro_para_postgres():
    """Lê a base Ouro em Parquet e grava na tabela ouro.fct_estudantes_beneficios_integrados."""
    caminho_ouro = configuracoes.caminho_ouro / "fct_estudantes_beneficios_integrados.parquet"
    
    if not caminho_ouro.exists():
        logger.error(f"Arquivo da Camada Ouro não encontrado: {caminho_ouro}")
        logger.info("Execute primeiro a pipeline de integração (pipeline_runner.py ou notebook de evidências).")
        return False

    logger.info(f"📥 Lendo base analítica Ouro de: {caminho_ouro}")
    df_ouro = pd.read_parquet(caminho_ouro)
    total_registros = len(df_ouro)
    logger.info(f"Total de registros lidos da Ouro: {total_registros}")

    # Padroniza nomes das colunas para minúsculo no Postgres
    df_ouro.columns = [c.lower().strip() for c in df_ouro.columns]

    engine = obter_engine_dw()

    logger.info("🔌 Conectando ao PostgreSQL local (sec_mais_dw)...")
    with engine.begin() as conn:
        # Garante a criação dos schemas
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ouro;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts;"))

        logger.info("💾 Gravando dados na tabela ouro.fct_estudantes_beneficios_integrados...")
        df_ouro.to_sql(
            name="fct_estudantes_beneficios_integrados",
            con=conn,
            schema="ouro",
            if_exists="replace",
            index=False,
            chunksize=5000,
        )

        # Criação de índices para otimização das consultas e views
        logger.info("⚡ Criando índices analíticos...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fct_matricula ON ouro.fct_estudantes_beneficios_integrados (matricula);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fct_cpf ON ouro.fct_estudantes_beneficios_integrados (cpf_estudante);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fct_total_prog ON ouro.fct_estudantes_beneficios_integrados (total_programas_recebidos);"))

    logger.info(f"✅ Tabela ouro.fct_estudantes_beneficios_integrados carregada com sucesso ({total_registros} registros).")
    return True


def aplicar_views_marts():
    """Executa o script SQL com as visões analíticas da camada marts."""
    script_views = PROJETO_ROOT / "docker" / "views_marts.sql"
    if not script_views.exists():
        logger.warning(f"Script de views não encontrado: {script_views}")
        return False

    logger.info(f"📜 Aplicando visões analíticas de: {script_views}")
    conteudo_sql = script_views.read_text(encoding="utf-8")

    engine = obter_engine_dw()
    with engine.begin() as conn:
        conn.execute(text(conteudo_sql))

    logger.info("✅ Visões analíticas da camada marts criadas com sucesso:")
    logger.info("   - marts.vw_resumo_sobreposicao")
    logger.info("   - marts.vw_estudantes_multiplos_beneficios")
    logger.info("   - marts.vw_distribuicao_geografica_beneficios")
    logger.info("   - marts.vw_transicao_pe_de_meia_upt")
    return True


def consultar_amostra_views():
    """Consulta rápida para validação das views criadas."""
    engine = obter_engine_dw()
    with engine.connect() as conn:
        df_resumo = pd.read_sql("SELECT * FROM marts.vw_resumo_sobreposicao;", con=conn)
        logger.info("📊 Prévia da Visão marts.vw_resumo_sobreposicao:")
        print(df_resumo.to_string(index=False))


def main():
    configurar_logging()
    logger.info("🚀 Iniciando carga da Camada Ouro para o PostgreSQL DW (Sprint 3)...")
    sucesso = carregar_ouro_para_postgres()
    if sucesso:
        aplicar_views_marts()
        consultar_amostra_views()
        logger.info("🏁 Carga e criação de visões analíticas finalizadas com êxito!")


if __name__ == "__main__":
    main()
