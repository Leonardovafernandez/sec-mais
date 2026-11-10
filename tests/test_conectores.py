"""
Testes para os conectores e configurações do projeto SEC MAIS.

Verifica:
- Carregamento correto das configurações
- Funcionamento da verificação de VPN (com mocks)
- Inicialização dos conectores (sem conexão real)
"""

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Testes de Configurações
# =============================================================================

class TestConfiguracoes:
    """Testes para as configurações do projeto."""

    def test_importar_configuracoes(self):
        """Verifica se o módulo de configurações é importável."""
        from config.settings import (
            Configuracoes,
            ConfiguracoesOracle,
            ConfiguracoesPostgres,
            ConfiguracoesSpark,
        )
        assert Configuracoes is not None
        assert ConfiguracoesOracle is not None
        assert ConfiguracoesPostgres is not None
        assert ConfiguracoesSpark is not None

    def test_configuracoes_padrao(self):
        """Verifica os valores padrão das configurações."""
        from config.settings import ConfiguracoesSpark
        spark_cfg = ConfiguracoesSpark()
        assert spark_cfg.spark_master == "local[*]"
        assert spark_cfg.spark_app_name == "sec_mais"

    def test_oracle_dsn(self):
        """Verifica a geração correta do DSN Oracle."""
        from config.settings import ConfiguracoesOracle
        cfg = ConfiguracoesOracle(host="servidor-oracle", port=1521, service="ORCL")
        assert cfg.dsn == "servidor-oracle:1521/ORCL"

    def test_postgres_connection_string(self):
        """Verifica a geração correta da connection string do PostgreSQL."""
        from config.settings import ConfiguracoesPostgres
        cfg = ConfiguracoesPostgres(
            host="servidor-pg",
            port=5432,
            database="meu_banco",
            user="usuario",
            password="senha123",
        )
        conn_str = cfg.connection_string
        assert "servidor-pg" in conn_str
        assert "meu_banco" in conn_str
        assert "usuario" in conn_str

    def test_oracle_esta_configurado_false(self):
        """Verifica que Oracle retorna não configurado quando campos estão vazios."""
        from config.settings import ConfiguracoesOracle
        cfg = ConfiguracoesOracle()
        assert cfg.esta_configurado is False

    def test_oracle_esta_configurado_true(self):
        """Verifica que Oracle retorna configurado quando campos estão preenchidos."""
        from config.settings import ConfiguracoesOracle
        cfg = ConfiguracoesOracle(
            host="host",
            service="service",
            user="user",
            password="pass",
        )
        assert cfg.esta_configurado is True

    def test_caminho_armazenamento(self):
        """Verifica que os caminhos de armazenamento são Path válidos."""
        from pathlib import Path
        from config.settings import Configuracoes

        cfg = Configuracoes()
        assert isinstance(cfg.caminho_armazenamento, Path)
        assert isinstance(cfg.caminho_bronze, Path)
        assert isinstance(cfg.caminho_prata, Path)
        assert isinstance(cfg.caminho_ouro, Path)
        assert cfg.caminho_bronze.name == "bronze"
        assert cfg.caminho_prata.name == "prata"
        assert cfg.caminho_ouro.name == "ouro"


# =============================================================================
# Testes de Verificação de VPN
# =============================================================================

class TestVerificacaoVPN:
    """Testes para o módulo de verificação de VPN."""

    def test_importar_modulo_vpn(self):
        """Verifica se o módulo de VPN é importável."""
        from utils.vpn_check import (
            verificar_host,
            verificar_vpn_oracle,
            verificar_vpn_postgres,
            verificar_todas_fontes,
        )
        assert verificar_host is not None

    def test_verificar_host_sem_host(self):
        """Verifica comportamento com host vazio."""
        from utils.vpn_check import verificar_host
        resultado = verificar_host("", 1521)
        assert resultado.acessivel is False
        assert "não configurado" in resultado.mensagem

    @patch("socket.socket")
    def test_verificar_host_sucesso(self, mock_socket_class):
        """Verifica retorno True quando a conexão TCP é bem-sucedida."""
        from utils.vpn_check import verificar_host

        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Sucesso
        mock_socket_class.return_value = mock_sock

        resultado = verificar_host("servidor.interno.gov.br", 1521)
        assert resultado.acessivel is True

    @patch("socket.socket")
    def test_verificar_host_falha(self, mock_socket_class):
        """Verifica retorno False quando a conexão TCP falha."""
        from utils.vpn_check import verificar_host

        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket_class.return_value = mock_sock

        resultado = verificar_host("servidor.interno.gov.br", 1521)
        assert resultado.acessivel is False

    @patch("utils.vpn_check.verificar_host")
    def test_verificar_todas_fontes(self, mock_verificar):
        """Verifica o retorno do dict com status de todas as fontes."""
        from utils.vpn_check import verificar_todas_fontes, ResultadoConexao

        # Simula host configurado e acessível
        mock_verificar.return_value = ResultadoConexao(
            host="host", porta=1521, acessivel=True, mensagem="OK"
        )

        with patch("config.settings.configuracoes_oracle") as mock_oracle_cfg, \
             patch("config.settings.configuracoes_postgres") as mock_pg_cfg:
            mock_oracle_cfg.host = "oracle-host"
            mock_oracle_cfg.port = 1521
            mock_pg_cfg.host = "pg-host"
            mock_pg_cfg.port = 5432

            status = verificar_todas_fontes()
            assert isinstance(status, dict)
            assert "oracle" in status
            assert "postgres" in status


# =============================================================================
# Testes dos Conectores (sem conexão real)
# =============================================================================

class TestConectorOracle:
    """Testes para o conector Oracle (mocked)."""

    def test_importar_conector(self):
        """Verifica se o conector Oracle é importável."""
        from extracao.conectores.oracle_connector import ConectorOracle
        assert ConectorOracle is not None

    def test_conector_sem_configuracoes_lanca_erro(self):
        """Verifica que conectar sem configurações lança ValueError."""
        from extracao.conectores.oracle_connector import ConectorOracle

        conector = ConectorOracle(verificar_vpn=False)
        # Sem configurações preenchidas, deve lançar ValueError
        with pytest.raises(ValueError, match="Configurações do Oracle incompletas"):
            conector.conectar()

    @patch("utils.vpn_check.verificar_vpn_oracle", return_value=False)
    def test_conector_sem_vpn_lanca_erro(self, mock_vpn):
        """Verifica que conectar sem VPN lança ConnectionError."""
        from extracao.conectores.oracle_connector import ConectorOracle
        from config.settings import ConfiguracoesOracle

        with patch("extracao.conectores.oracle_connector.configuracoes_oracle") as mock_cfg:
            mock_cfg.esta_configurado = True
            mock_cfg.host = "host"
            mock_cfg.port = 1521
            conector = ConectorOracle(verificar_vpn=True)

            with pytest.raises(ConnectionError):
                conector.conectar()


class TestConectorPostgres:
    """Testes para o conector PostgreSQL (mocked)."""

    def test_importar_conector(self):
        """Verifica se o conector PostgreSQL é importável."""
        from extracao.conectores.postgres_connector import ConectorPostgres
        assert ConectorPostgres is not None

    def test_conector_sem_configuracoes_lanca_erro(self):
        """Verifica que conectar sem configurações lança ValueError."""
        from extracao.conectores.postgres_connector import ConectorPostgres

        conector = ConectorPostgres(verificar_vpn=False)
        with pytest.raises(ValueError, match="Configurações do PostgreSQL incompletas"):
            conector.conectar()


# =============================================================================
# Testes de Utilitários de Armazenamento
# =============================================================================

class TestStorage:
    """Testes para os utilitários de armazenamento."""

    def test_importar_storage(self):
        """Verifica se o módulo de storage é importável."""
        from utils.storage import (
            obter_caminho_camada,
            obter_caminho_programa,
            verificar_dados_disponiveis,
            resumo_armazenamento,
        )
        assert obter_caminho_camada is not None

    def test_programa_invalido_lanca_erro(self):
        """Verifica que programa inválido lança ValueError."""
        from utils.storage import obter_caminho_programa
        with pytest.raises(ValueError, match="Programa 'invalido' não reconhecido"):
            obter_caminho_programa("bronze", "invalido")

    def test_caminhos_por_camada(self):
        """Verifica que os caminhos por camada são gerados corretamente."""
        from pathlib import Path
        from utils.storage import obter_caminho_programa

        for camada in ("bronze", "prata", "ouro"):
            caminho = obter_caminho_programa(camada, "bolsa_presenca")  # type: ignore
            assert isinstance(caminho, Path)
            assert camada in str(caminho)
            assert "bolsa_presenca" in str(caminho)
