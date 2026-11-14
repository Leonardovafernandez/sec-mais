"""
Conector PostgreSQL para o projeto SEC MAIS.

Gerencia conexões com o banco de dados PostgreSQL, verificando
a conectividade via VPN antes de qualquer operação.

IMPORTANTE: Este módulo requer VPN ativa para funcionar,
pois o banco PostgreSQL só é acessível na rede interna.
"""

from contextlib import contextmanager

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config.settings import configuracoes_postgres, ConfiguracoesPostgres
from utils.vpn_check import exigir_vpn_postgres


class ConectorPostgres:
    """
    Conector para o banco de dados PostgreSQL.

    Gerencia o ciclo de vida da conexão com verificação de VPN,
    tratamento de erros e logging detalhado.

    Exemplo de uso:
        with ConectorPostgres() as conector:
            df = conector.executar_query("SELECT * FROM minha_tabela")
    """

    def __init__(
        self,
        config: ConfiguracoesPostgres | None = None,
        verificar_vpn: bool = True,
    ) -> None:
        """
        Inicializa o conector PostgreSQL.

        Args:
            config: Instância de configurações (UPT, PDM ou genérica).
            verificar_vpn: Se True, verifica a conectividade antes de conectar.
        """
        self._verificar_vpn = verificar_vpn
        self._engine: Engine | None = None
        self._configuracoes = config if config is not None else configuracoes_postgres

    def _validar_configuracoes(self) -> None:
        """
        Valida se as configurações mínimas estão presentes.

        Raises:
            ValueError: Se alguma configuração obrigatória estiver ausente.
        """
        if not self._configuracoes.esta_configurado:
            raise ValueError(
                "Configurações do PostgreSQL incompletas. "
                "Verifique as variáveis PG_HOST, PG_DATABASE, "
                "PG_USER e PG_PASSWORD no arquivo .env"
            )

    def _criar_engine(self) -> Engine:
        """
        Cria e retorna o engine SQLAlchemy para o PostgreSQL.

        Returns:
            Engine SQLAlchemy configurado.

        Raises:
            ConnectionError: Se não for possível criar a engine.
        """
        try:
            conn_str = self._configuracoes.connection_string
            schema = self._configuracoes.schema
            usuario = self._configuracoes.user
            host = self._configuracoes.host

            logger.info(f"Criando conexão PostgreSQL: {usuario}@{host}/{self._configuracoes.database}")

            connect_args = {
                "options": f"-csearch_path={schema}",
                "connect_timeout": 10,
            }
            if getattr(self._configuracoes, "sslmode", None):
                connect_args["sslmode"] = self._configuracoes.sslmode

            engine = create_engine(
                conn_str,
                pool_pre_ping=True,  # Verifica a conexão antes de usar
                pool_size=5,
                max_overflow=10,
                echo=False,
                connect_args=connect_args,
            )
            return engine

        except ImportError:
            raise ImportError(
                "Pacote psycopg2 não encontrado. "
                "Instale com: pip install psycopg2-binary"
            )
        except Exception as e:
            raise ConnectionError(f"Falha ao criar engine PostgreSQL: {e}") from e

    def conectar(self) -> None:
        """
        Estabelece a conexão com o PostgreSQL.

        Raises:
            ConnectionError: Se a VPN não estiver ativa ou a conexão falhar.
            ValueError: Se as configurações estiverem incompletas.
        """
        self._validar_configuracoes()

        if self._verificar_vpn:
            logger.info("Verificando conectividade VPN antes de conectar ao PostgreSQL...")
            exigir_vpn_postgres()

        self._engine = self._criar_engine()
        logger.info("✅ Conexão PostgreSQL estabelecida com sucesso")

    def desconectar(self) -> None:
        """Encerra a conexão com o PostgreSQL."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Conexão PostgreSQL encerrada")

    def executar_query(
        self,
        query: str,
        params: dict | None = None,
        chunksize: int | None = None,
    ) -> pd.DataFrame:
        """
        Executa uma query SQL e retorna o resultado como DataFrame.

        Args:
            query: Query SQL a executar.
            params: Parâmetros para a query (evita SQL injection).
            chunksize: Se fornecido, lê em chunks desse tamanho.

        Returns:
            DataFrame pandas com o resultado da query.

        Raises:
            RuntimeError: Se não houver conexão ativa.
            Exception: Se a query falhar.
        """
        if not self._engine:
            raise RuntimeError(
                "Sem conexão ativa. Use o context manager 'with ConectorPostgres() as c:'"
            )

        logger.info(f"Executando query PostgreSQL (primeiros 100 chars): {query[:100]}...")

        try:
            with self._engine.connect() as conn:
                if chunksize:
                    chunks = []
                    for chunk in pd.read_sql(
                        text(query), conn, params=params, chunksize=chunksize
                    ):
                        chunks.append(chunk)
                        logger.debug(f"Chunk lido: {len(chunk)} linhas")
                    df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
                else:
                    df = pd.read_sql(text(query), conn, params=params)

            logger.info(f"✅ Query executada com sucesso: {len(df)} linhas retornadas")
            return df

        except Exception as e:
            logger.error(f"❌ Erro ao executar query PostgreSQL: {e}")
            raise

    def executar_comando(self, comando: str, params: dict | None = None) -> None:
        """
        Executa um comando SQL sem retorno (INSERT, UPDATE, DELETE, DDL).

        Args:
            comando: Comando SQL a executar.
            params: Parâmetros para o comando.

        Raises:
            RuntimeError: Se não houver conexão ativa.
        """
        if not self._engine:
            raise RuntimeError("Sem conexão ativa.")

        try:
            with self._engine.begin() as conn:
                conn.execute(text(comando), params or {})
            logger.info("✅ Comando SQL executado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao executar comando PostgreSQL: {e}")
            raise

    def __enter__(self) -> "ConectorPostgres":
        """Suporte ao context manager (with statement)."""
        self.conectar()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Encerra a conexão ao sair do context manager."""
        self.desconectar()
        if exc_type:
            logger.error(f"Erro durante operação PostgreSQL: {exc_val}")
        return False


def criar_conector_postgres(verificar_vpn: bool = True) -> ConectorPostgres:
    """
    Fábrica para criar um ConectorPostgres.

    Args:
        verificar_vpn: Se True, verifica a VPN antes de conectar.

    Returns:
        Instância de ConectorPostgres.
    """
    return ConectorPostgres(verificar_vpn=verificar_vpn)
