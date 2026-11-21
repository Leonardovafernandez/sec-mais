"""
Configurações do projeto SEC MAIS.

Este módulo centraliza todas as configurações do projeto,
lendo valores do arquivo .env via pydantic-settings.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Diretório raiz do projeto (dois níveis acima deste arquivo)
PROJETO_ROOT = Path(__file__).parent.parent


# Caminhos possíveis para o .env (tanto na raiz do repo quanto um nível acima)
ARQUIVOS_ENV = (
    str(PROJETO_ROOT / ".env"),
    str(PROJETO_ROOT.parent / ".env"),
    ".env",
)


class ConfiguracoesOracle(BaseSettings):
    """Configurações de conexão com o banco Oracle."""

    model_config = SettingsConfigDict(
        env_prefix="ORACLE_",
        env_file=ARQUIVOS_ENV,
        extra="ignore",
    )

    host: str = Field(default="", description="Host do servidor Oracle")
    port: int = Field(default=1521, description="Porta do servidor Oracle")
    service: str = Field(default="", description="Nome do serviço Oracle")
    user: str = Field(default="", description="Usuário do banco Oracle")
    password: str = Field(default="", description="Senha do banco Oracle")
    schema_name: str = Field(default="", validation_alias="ORACLE_SCHEMA", description="Schema padrão do Oracle")

    @property
    def schema(self) -> str:
        """Alias para schema_name evitando shadowing no Pydantic."""
        return self.schema_name

    @property
    def dsn(self) -> str:
        """Retorna a string de conexão DSN para o Oracle."""
        return f"{self.host}:{self.port}/{self.service}"

    @property
    def esta_configurado(self) -> bool:
        """Verifica se as configurações mínimas estão preenchidas."""
        return bool(self.host and self.service and self.user and self.password)


class ConfiguracoesPostgres(BaseSettings):
    """Configurações de conexão com o banco PostgreSQL (genérica)."""

    model_config = SettingsConfigDict(
        env_prefix="PG_",
        env_file=ARQUIVOS_ENV,
        extra="ignore",
    )

    host: str = Field(default="", description="Host do servidor PostgreSQL")
    port: int = Field(default=5432, description="Porta do servidor PostgreSQL")
    database: str = Field(default="", description="Nome do banco de dados PostgreSQL")
    user: str = Field(default="", description="Usuário do banco PostgreSQL")
    password: str = Field(default="", description="Senha do banco PostgreSQL")
    schema_name: str = Field(default="public", validation_alias="PG_SCHEMA", description="Schema padrão do PostgreSQL")
    sslmode: str = Field(default="prefer", description="Modo SSL do PostgreSQL")

    @property
    def schema(self) -> str:
        """Alias para schema_name evitando shadowing no Pydantic."""
        return self.schema_name

    @property
    def connection_string(self) -> str:
        """Retorna a string de conexão SQLAlchemy para o PostgreSQL."""
        ssl_param = f"?sslmode={self.sslmode}" if self.sslmode else ""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}{ssl_param}"
        )

    @property
    def esta_configurado(self) -> bool:
        """Verifica se as configurações mínimas estão preenchidas."""
        return bool(self.host and self.database and self.user and self.password)


class ConfiguracoesPostgresUPT(ConfiguracoesPostgres):
    """Configurações de conexão específicas para o banco UPT (PostgreSQL 16)."""

    model_config = SettingsConfigDict(
        env_prefix="PG_UPT_",
        env_file=ARQUIVOS_ENV,
        extra="ignore",
    )
    database: str = Field(default="upt")
    schema_name: str = Field(default="upt", validation_alias="PG_UPT_SCHEMA")
    sslmode: str = Field(default="disable", validation_alias="PG_UPT_SSLMODE")


class ConfiguracoesPostgresPDM(ConfiguracoesPostgres):
    """Configurações de conexão específicas para o banco Pé de Meia - SIGEDUC (PostgreSQL 13)."""

    model_config = SettingsConfigDict(
        env_prefix="PG_PDM_",
        env_file=ARQUIVOS_ENV,
        extra="ignore",
    )
    database: str = Field(default="sigeduc")
    schema_name: str = Field(
        default="integracao_sgp_beneficio_estudantil",
        validation_alias="PG_PDM_SCHEMA",
    )
    sslmode: str = Field(default="prefer", validation_alias="PG_PDM_SSLMODE")


class ConfiguracoesPostgresDW(ConfiguracoesPostgres):
    """Configurações de conexão para o Data Warehouse Analítico local (PostgreSQL Docker - Sprint 3)."""

    model_config = SettingsConfigDict(
        env_prefix="PG_DW_",
        env_file=ARQUIVOS_ENV,
        extra="ignore",
    )
    database: str = Field(default="sec_mais_dw")
    schema_name: str = Field(default="ouro", validation_alias="PG_DW_SCHEMA")
    sslmode: str = Field(default="disable", validation_alias="PG_DW_SSLMODE")


class ConfiguracoesSpark(BaseSettings):
    """Configurações do Apache Spark."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    spark_master: str = Field(default="local[*]", description="Master URL do Spark")
    spark_app_name: str = Field(default="sec_mais", description="Nome da aplicação Spark")


class Configuracoes(BaseSettings):
    """Configurações gerais do projeto SEC MAIS."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Ambiente de execução
    ambiente: str = Field(default="desenvolvimento", description="Ambiente de execução")
    log_level: str = Field(default="INFO", description="Nível de log")

    # Caminho base de armazenamento (usa padrão relativo ao projeto se vazio)
    storage_base_path: Optional[str] = Field(
        default=None, description="Caminho base para armazenamento"
    )

    @property
    def caminho_armazenamento(self) -> Path:
        """Retorna o caminho base de armazenamento."""
        if self.storage_base_path:
            return Path(self.storage_base_path)
        return PROJETO_ROOT / "armazenamento"

    @property
    def caminho_bronze(self) -> Path:
        """Retorna o caminho da camada bronze."""
        return self.caminho_armazenamento / "bronze"

    @property
    def caminho_prata(self) -> Path:
        """Retorna o caminho da camada prata."""
        return self.caminho_armazenamento / "prata"

    @property
    def caminho_ouro(self) -> Path:
        """Retorna o caminho da camada ouro."""
        return self.caminho_armazenamento / "ouro"


# Instâncias singleton das configurações
configuracoes = Configuracoes()
configuracoes_oracle = ConfiguracoesOracle()
configuracoes_postgres = ConfiguracoesPostgres()
configuracoes_postgres_upt = ConfiguracoesPostgresUPT()
configuracoes_postgres_pdm = ConfiguracoesPostgresPDM()
configuracoes_postgres_dw = ConfiguracoesPostgresDW()
configuracoes_spark = ConfiguracoesSpark()
