"""
Conector Oracle para o projeto SEC MAIS.

Gerencia conexões com o banco de dados Oracle, verificando
a conectividade via VPN antes de qualquer operação.

IMPORTANTE: Este módulo requer VPN ativa para funcionar,
pois o banco Oracle só é acessível na rede interna.
"""

from contextlib import contextmanager
from typing import Generator

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config.settings import configuracoes_oracle
from utils.vpn_check import exigir_vpn_oracle


class ConectorOracle:
    """
    Conector para o banco de dados Oracle.

    Gerencia o ciclo de vida da conexão com verificação de VPN,
    tratamento de erros e logging detalhado.

    Exemplo de uso:
        with ConectorOracle() as conector:
            df = conector.executar_query("SELECT * FROM minha_tabela")
    """

    def __init__(self, verificar_vpn: bool = True) -> None:
        """
        Inicializa o conector Oracle.

        Args:
            verificar_vpn: Se True, verifica a conectividade antes de conectar.
        """
        self._verificar_vpn = verificar_vpn
        self._engine: Engine | None = None
        self._configuracoes = configuracoes_oracle

    def _validar_configuracoes(self) -> None:
        """
        Valida se as configurações mínimas estão presentes.

        Raises:
            ValueError: Se alguma configuração obrigatória estiver ausente.
        """
        if not self._configuracoes.esta_configurado:
            raise ValueError(
                "Configurações do Oracle incompletas. "
                "Verifique as variáveis ORACLE_HOST, ORACLE_SERVICE, "
                "ORACLE_USER e ORACLE_PASSWORD no arquivo .env"
            )

    def _criar_engine(self) -> Engine:
        """
        Cria e retorna o engine SQLAlchemy para o Oracle.

        Returns:
            Engine SQLAlchemy configurado.

        Raises:
            ConnectionError: Se não for possível criar a engine.
        """
        try:
            # Tenta oracledb (driver moderno oficial da Oracle) ou cx_Oracle (legado)
            try:
                import oracledb
                dialeto = "oracle+oracledb"
            except ImportError:
                import cx_Oracle  # noqa: F401
                dialeto = "oracle+cx_oracle"

            dsn = self._configuracoes.dsn
            usuario = self._configuracoes.user
            # A senha não é logada por segurança

            logger.info(f"Criando conexão Oracle ({dialeto}): {usuario}@{dsn}")

            engine = create_engine(
                f"{dialeto}://{usuario}:{self._configuracoes.password}@{dsn}",
                pool_pre_ping=True,  # Verifica a conexão antes de usar
                pool_size=5,
                max_overflow=10,
                echo=False,
            )
            return engine

        except ImportError:
            raise ImportError(
                "Driver Oracle (oracledb) não encontrado. "
                "Instale com: pip install oracledb"
            )
        except Exception as e:
            raise ConnectionError(f"Falha ao criar engine Oracle: {e}") from e

    def conectar(self) -> None:
        """
        Estabelece a conexão com o Oracle.

        Raises:
            ConnectionError: Se a VPN não estiver ativa ou a conexão falhar.
            ValueError: Se as configurações estiverem incompletas.
        """
        self._validar_configuracoes()

        if self._verificar_vpn:
            logger.info("Verificando conectividade VPN antes de conectar ao Oracle...")
            exigir_vpn_oracle()

        self._engine = self._criar_engine()
        logger.info("✅ Conexão Oracle estabelecida com sucesso")

    def desconectar(self) -> None:
        """Encerra a conexão com o Oracle."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Conexão Oracle encerrada")

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
                "Sem conexão ativa. Use o context manager 'with ConectorOracle() as c:'"
            )

        logger.info(f"Executando query Oracle (primeiros 100 chars): {query[:100]}...")

        try:
            with self._engine.connect() as conn:
                if chunksize:
                    # Leitura em chunks para datasets grandes
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
            logger.error(f"❌ Erro ao executar query Oracle: {e}")
            raise

    def __enter__(self) -> "ConectorOracle":
        """Suporte ao context manager (with statement)."""
        self.conectar()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Encerra a conexão ao sair do context manager."""
        self.desconectar()
        if exc_type:
            logger.error(f"Erro durante operação Oracle: {exc_val}")
        return False  # Não suprime exceções


# Alias para compatibilidade
def criar_conector_oracle(verificar_vpn: bool = True) -> ConectorOracle:
    """
    Fábrica para criar um ConectorOracle.

    Args:
        verificar_vpn: Se True, verifica a VPN antes de conectar.

    Returns:
        Instância de ConectorOracle.
    """
    return ConectorOracle(verificar_vpn=verificar_vpn)
