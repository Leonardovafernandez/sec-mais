"""
Script de diagnóstico e validação de acessos aos bancos de dados do SEC MAIS.

Testa a conexão e permissões com:
1. Oracle 19c (SIADIANTE / Bolsa Presença)
2. PostgreSQL 16 (UPT / Universidade Para Todos)
3. PostgreSQL 13 (SIGEDUC / Pé-de-Meia e Mais Estudos)

Execute com:
    python -m extracao.diagnostico_conexoes
"""

import sys
import pandas as pd
from loguru import logger
from sqlalchemy import text

from config.logging_config import configurar_logging
from config.settings import (
    configuracoes_oracle,
    configuracoes_postgres_upt,
    configuracoes_postgres_pdm,
)
from extracao.conectores.oracle_connector import ConectorOracle
from extracao.conectores.postgres_connector import ConectorPostgres


def testar_oracle():
    print("\n" + "=" * 60)
    print("🔍 1. TESTANDO ORACLE (SIADIANTE - Bolsa Presença)")
    print("=" * 60)
    print(f"Host: {configuracoes_oracle.host}:{configuracoes_oracle.port}")
    print(f"Service: {configuracoes_oracle.service} | User: {configuracoes_oracle.user}")
    print(f"Schema: {configuracoes_oracle.schema}")

    try:
        with ConectorOracle(verificar_vpn=False) as conn:
            # Teste básico
            df_ping = conn.executar_query("SELECT 1 AS PING FROM DUAL")
            print("  ✅ Conexão estabelecida com sucesso!")

            # Teste da tabela do Bolsa Presença
            schema = configuracoes_oracle.schema or "SIADIANTE"
            query = f"""
                SELECT COUNT(*) AS TOTAL 
                FROM {schema}.BENEFICIO_FAMILIA
            """
            df_total = conn.executar_query(query)
            total = df_total["TOTAL"].iloc[0]
            print(f"  ✅ Tabela {schema}.BENEFICIO_FAMILIA acessível! Total de registros: {total:,}")

            # Amostra de 3 linhas da query real
            from extracao.programas.bolsa_presenca import QUERY_BOLSA_PRESENCA
            query_amostra = f"""
                SELECT * FROM ({QUERY_BOLSA_PRESENCA.format(schema=schema)})
                WHERE ROWNUM <= 3
            """
            df_amostra = conn.executar_query(query_amostra)
            print(f"  ✅ Query real executada com sucesso! Colunas: {list(df_amostra.columns)}")
            return True
    except Exception as e:
        print(f"  ❌ Erro no Oracle: {e}")
        return False


def testar_upt():
    print("\n" + "=" * 60)
    print("🔍 2. TESTANDO POSTGRESQL (UPT - Universidade Para Todos)")
    print("=" * 60)
    print(f"Host: {configuracoes_postgres_upt.host}:{configuracoes_postgres_upt.port}")
    print(f"Database: {configuracoes_postgres_upt.database} | User: {configuracoes_postgres_upt.user}")
    print(f"Schema: {configuracoes_postgres_upt.schema}")

    try:
        with ConectorPostgres(config=configuracoes_postgres_upt, verificar_vpn=False) as conn:
            # Teste básico
            df_ping = conn.executar_query("SELECT 1 AS ping")
            print("  ✅ Conexão UPT estabelecida com sucesso!")

            # Teste de tabelas
            schema = configuracoes_postgres_upt.schema or "UPT"
            from extracao.programas.universidade_para_todos import QUERY_UPT
            query_amostra = f"{QUERY_UPT.format(schema=schema)} LIMIT 3"
            df_amostra = conn.executar_query(query_amostra)
            print(f"  ✅ Query UPT executada com sucesso! Colunas: {list(df_amostra.columns)}")
            return True
    except Exception as e:
        print(f"  ❌ Erro no PostgreSQL UPT: {e}")
        return False


def testar_sigeduc():
    print("\n" + "=" * 60)
    print("🔍 3. TESTANDO POSTGRESQL (SIGEDUC - Pé-de-Meia / Mais Estudos)")
    print("=" * 60)
    print(f"Host: {configuracoes_postgres_pdm.host}:{configuracoes_postgres_pdm.port}")
    print(f"Database: {configuracoes_postgres_pdm.database} | User: {configuracoes_postgres_pdm.user}")
    print(f"Schema configurado: {configuracoes_postgres_pdm.schema}")

    try:
        with ConectorPostgres(config=configuracoes_postgres_pdm, verificar_vpn=False) as conn:
            df_ping = conn.executar_query("SELECT 1 AS ping, current_user, current_database()")
            print(f"  ✅ Conectado como '{df_ping['current_user'].iloc[0]}' no banco '{df_ping['current_database'].iloc[0]}'!")

            # Verificar quais schemas o usuário tem permissão de USAGE
            query_schemas = """
                SELECT nspname, 
                       has_schema_privilege(current_user, nspname, 'USAGE') as tem_usage,
                       has_schema_privilege(current_user, nspname, 'CREATE') as tem_create
                FROM pg_namespace
                WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'
                ORDER BY nspname;
            """
            df_schemas = conn.executar_query(query_schemas)
            print("\n  📋 Esquemas encontrados no banco SIGEDUC:")
            for _, row in df_schemas.iterrows():
                priv = "✅ Acesso USAGE liberado" if row["tem_usage"] else "❌ SEM ACESSO"
                print(f"     - {row['nspname']}: {priv}")

            # Testar a query do Pé-de-Meia se o schema for acessível
            schema = configuracoes_postgres_pdm.schema or "integracao_sgp_beneficio_estudantil"
            schema_info = df_schemas[df_schemas["nspname"] == schema]
            if not schema_info.empty and schema_info["tem_usage"].iloc[0]:
                from extracao.programas.pe_de_meia import QUERY_PE_DE_MEIA
                query_amostra = f"{QUERY_PE_DE_MEIA.format(schema=schema)} LIMIT 3"
                df_amostra = conn.executar_query(query_amostra)
                print(f"\n  ✅ Query Pé-de-Meia executada com sucesso! Colunas: {list(df_amostra.columns)}")
                return True
            else:
                print(f"\n  ⚠️ O usuário '{configuracoes_postgres_pdm.user}' NÃO tem permissão no schema '{schema}'.")
                print("     Verifique se o usuário correto do Pé-de-Meia é outro ou solicite ao DBA:")
                print(f"     GRANT USAGE ON SCHEMA {schema} TO {configuracoes_postgres_pdm.user};")
                print(f"     GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {configuracoes_postgres_pdm.user};")
                return False
    except Exception as e:
        print(f"  ❌ Erro no PostgreSQL SIGEDUC: {e}")
        return False


def main():
    configurar_logging(nivel="WARNING")
    print("=" * 60)
    print("🚀 SEC MAIS - DIAGNÓSTICO DE BANCOS E PERMISSÕES")
    print("=" * 60)

    res_oracle = testar_oracle()
    res_upt = testar_upt()
    res_sigeduc = testar_sigeduc()

    print("\n" + "=" * 60)
    print("📊 RESUMO DO DIAGNÓSTICO:")
    print(f"  - Oracle (SIADIANTE / Bolsa Presença): {'✅ OK' if res_oracle else '❌ FALHOU'}")
    print(f"  - Postgres (UPT / Univ. Para Todos):  {'✅ OK' if res_upt else '❌ FALHOU'}")
    print(f"  - Postgres (SIGEDUC / Pé-de-Meia):     {'✅ OK' if res_sigeduc else '⚠️ PERMISSÃO OU CONFIG'}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

