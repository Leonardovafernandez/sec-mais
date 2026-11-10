"""
Testes para as transformações Spark do projeto SEC MAIS.

Verifica:
- Importação dos módulos de transformação
- Lógica de padronização de colunas (sem Spark real)
- Utilitários de verificação de dados
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Testes de Importação dos Módulos de Transformação
# =============================================================================

class TestImportacaoTransformacoes:
    """Verifica se todos os módulos de transformação são importáveis."""

    def test_importar_bronze_prata_bolsa_presenca(self):
        """Importa o módulo bronze→prata do Bolsa Presença."""
        from transformacao.bronze_para_prata.bolsa_presenca import (
            transformar_bronze_para_prata_bolsa_presenca,
        )
        assert transformar_bronze_para_prata_bolsa_presenca is not None

    def test_importar_bronze_prata_upt(self):
        """Importa o módulo bronze→prata do UPT."""
        from transformacao.bronze_para_prata.universidade_para_todos import (
            transformar_bronze_para_prata_upt,
        )
        assert transformar_bronze_para_prata_upt is not None

    def test_importar_bronze_prata_mais_estudos(self):
        """Importa o módulo bronze→prata do Mais Estudos."""
        from transformacao.bronze_para_prata.mais_estudos import (
            transformar_bronze_para_prata_mais_estudos,
        )
        assert transformar_bronze_para_prata_mais_estudos is not None

    def test_importar_bronze_prata_pe_de_meia(self):
        """Importa o módulo bronze→prata do Pé-de-Meia."""
        from transformacao.bronze_para_prata.pe_de_meia import (
            transformar_bronze_para_prata_pe_de_meia,
        )
        assert transformar_bronze_para_prata_pe_de_meia is not None

    def test_importar_prata_ouro_bolsa_presenca(self):
        """Importa o módulo prata→ouro do Bolsa Presença."""
        from transformacao.prata_para_ouro.bolsa_presenca import (
            transformar_prata_para_ouro_bolsa_presenca,
        )
        assert transformar_prata_para_ouro_bolsa_presenca is not None

    def test_importar_prata_ouro_upt(self):
        """Importa o módulo prata→ouro do UPT."""
        from transformacao.prata_para_ouro.universidade_para_todos import (
            transformar_prata_para_ouro_upt,
        )
        assert transformar_prata_para_ouro_upt is not None

    def test_importar_prata_ouro_mais_estudos(self):
        """Importa o módulo prata→ouro do Mais Estudos."""
        from transformacao.prata_para_ouro.mais_estudos import (
            transformar_prata_para_ouro_mais_estudos,
        )
        assert transformar_prata_para_ouro_mais_estudos is not None

    def test_importar_prata_ouro_pe_de_meia(self):
        """Importa o módulo prata→ouro do Pé-de-Meia."""
        from transformacao.prata_para_ouro.pe_de_meia import (
            transformar_prata_para_ouro_pe_de_meia,
        )
        assert transformar_prata_para_ouro_pe_de_meia is not None


# =============================================================================
# Testes de Lógica de Padronização de Nomes de Colunas
# =============================================================================

class TestPadronizacaoColunas:
    """Testa a lógica de padronização de nomes de colunas (sem Spark)."""

    def _padronizar_nome(self, nome: str) -> str:
        """Replica a lógica de padronização de nomes de colunas."""
        return nome.lower().strip().replace(" ", "_").replace("-", "_")

    def test_colunas_maiusculas(self):
        """Verifica conversão de maiúsculas para minúsculas."""
        assert self._padronizar_nome("NM_ALUNO") == "nm_aluno"
        assert self._padronizar_nome("CD_ESCOLA") == "cd_escola"

    def test_colunas_com_espacos(self):
        """Verifica substituição de espaços por underscore."""
        assert self._padronizar_nome("nome aluno") == "nome_aluno"
        assert self._padronizar_nome("data referencia") == "data_referencia"

    def test_colunas_com_hifen(self):
        """Verifica substituição de hífen por underscore."""
        assert self._padronizar_nome("nm-aluno") == "nm_aluno"

    def test_colunas_com_espacos_extras(self):
        """Verifica remoção de espaços extras."""
        assert self._padronizar_nome("  NM_ALUNO  ") == "nm_aluno"

    def test_colunas_ja_padronizadas(self):
        """Verifica que colunas já padronizadas não mudam."""
        assert self._padronizar_nome("nm_aluno") == "nm_aluno"


# =============================================================================
# Testes de Verificação de Dados Disponíveis
# =============================================================================

class TestVerificacaoDados:
    """Testa os utilitários de verificação de disponibilidade de dados."""

    def test_verificar_dados_diretorio_inexistente(self):
        """Verifica retorno False para diretório inexistente."""
        from utils.storage import verificar_dados_disponiveis

        with patch("utils.storage.obter_caminho_programa") as mock_caminho:
            mock_caminho.return_value = Path("/caminho/que/nao/existe")
            resultado = verificar_dados_disponiveis("bronze", "bolsa_presenca")
            assert resultado is False

    def test_listar_arquivos_diretorio_vazio(self):
        """Verifica retorno de lista vazia para diretório sem Parquets."""
        import tempfile
        from utils.storage import listar_arquivos

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("utils.storage.obter_caminho_programa") as mock_caminho:
                mock_caminho.return_value = Path(tmpdir)
                arquivos = listar_arquivos("bronze", "bolsa_presenca")
                assert arquivos == []

    def test_resumo_armazenamento_estrutura(self):
        """Verifica a estrutura do resumo de armazenamento."""
        from utils.storage import resumo_armazenamento

        with patch("utils.storage.listar_arquivos", return_value=[]):
            resumo = resumo_armazenamento()
            assert isinstance(resumo, dict)
            assert "bronze" in resumo
            assert "prata" in resumo
            assert "ouro" in resumo
            for camada in resumo:
                assert isinstance(resumo[camada], dict)
                assert "bolsa_presenca" in resumo[camada]
                assert "universidade_para_todos" in resumo[camada]
                assert "mais_estudos" in resumo[camada]
                assert "pe_de_meia" in resumo[camada]


# =============================================================================
# Testes de Extratores (sem conexão real)
# =============================================================================

class TestExtratores:
    """Testa a importação e estrutura dos extratores."""

    def test_importar_extrator_bolsa_presenca(self):
        """Verifica importação do extrator Bolsa Presença."""
        from extracao.programas.bolsa_presenca import extrair_bolsa_presenca, NOME_PROGRAMA
        assert extrair_bolsa_presenca is not None
        assert NOME_PROGRAMA == "bolsa_presenca"

    def test_importar_extrator_upt(self):
        """Verifica importação do extrator UPT."""
        from extracao.programas.universidade_para_todos import (
            extrair_universidade_para_todos, NOME_PROGRAMA
        )
        assert extrair_universidade_para_todos is not None
        assert NOME_PROGRAMA == "universidade_para_todos"

    def test_importar_extrator_mais_estudos(self):
        """Verifica importação do extrator Mais Estudos."""
        from extracao.programas.mais_estudos import extrair_mais_estudos, NOME_PROGRAMA
        assert extrair_mais_estudos is not None
        assert NOME_PROGRAMA == "mais_estudos"

    def test_importar_extrator_pe_de_meia(self):
        """Verifica importação do extrator Pé-de-Meia."""
        from extracao.programas.pe_de_meia import extrair_pe_de_meia, NOME_PROGRAMA
        assert extrair_pe_de_meia is not None
        assert NOME_PROGRAMA == "pe_de_meia"
