"""
Utilitário para gerenciamento do armazenamento local.

Fornece funções para resolver caminhos das camadas medalhão,
criar diretórios, listar arquivos e verificar disponibilidade de dados.
"""

from datetime import datetime
from pathlib import Path
from typing import Literal

from loguru import logger

from config.settings import configuracoes

# Tipo para as camadas medalhão
CamadaMedalhao = Literal["bronze", "prata", "ouro"]

# Mapeamento dos programas para nomes de diretório
PROGRAMAS = {
    "bolsa_presenca": "bolsa_presenca",
    "universidade_para_todos": "universidade_para_todos",
    "mais_estudos": "mais_estudos",
    "pe_de_meia": "pe_de_meia",
}


def obter_caminho_camada(camada: CamadaMedalhao) -> Path:
    """
    Retorna o caminho base de uma camada medalhão.

    Args:
        camada: Nome da camada ('bronze', 'prata' ou 'ouro').

    Returns:
        Path da camada.
    """
    mapeamento = {
        "bronze": configuracoes.caminho_bronze,
        "prata": configuracoes.caminho_prata,
        "ouro": configuracoes.caminho_ouro,
    }
    return mapeamento[camada]


def obter_caminho_programa(camada: CamadaMedalhao, programa: str) -> Path:
    """
    Retorna o caminho de um programa em uma camada específica.

    Args:
        camada: Nome da camada ('bronze', 'prata' ou 'ouro').
        programa: Nome do programa (ex: 'bolsa_presenca').

    Returns:
        Path do programa na camada.

    Raises:
        ValueError: Se o programa não for reconhecido.
    """
    if programa not in PROGRAMAS:
        raise ValueError(
            f"Programa '{programa}' não reconhecido. "
            f"Programas válidos: {list(PROGRAMAS.keys())}"
        )
    return obter_caminho_camada(camada) / PROGRAMAS[programa]


def garantir_diretorio(caminho: Path) -> Path:
    """
    Cria o diretório (e pais) se não existir.

    Args:
        caminho: Caminho do diretório a criar.

    Returns:
        O mesmo caminho recebido.
    """
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def obter_caminho_particao(
    camada: CamadaMedalhao,
    programa: str,
    data_execucao: datetime | None = None,
) -> Path:
    """
    Retorna o caminho de partição por data de execução.

    Args:
        camada: Nome da camada.
        programa: Nome do programa.
        data_execucao: Data de execução (usa a data atual se None).

    Returns:
        Path da partição.
    """
    if data_execucao is None:
        data_execucao = datetime.now()

    base = obter_caminho_programa(camada, programa)
    particao = base / f"ano={data_execucao.year}" / f"mes={data_execucao.month:02d}" / f"dia={data_execucao.day:02d}"
    return garantir_diretorio(particao)


def listar_arquivos(
    camada: CamadaMedalhao,
    programa: str,
    extensao: str = ".parquet",
) -> list[Path]:
    """
    Lista arquivos de um programa em uma camada.

    Args:
        camada: Nome da camada.
        programa: Nome do programa.
        extensao: Extensão dos arquivos (ex: '.parquet').

    Returns:
        Lista de Paths dos arquivos encontrados.
    """
    caminho = obter_caminho_programa(camada, programa)

    if not caminho.exists():
        logger.warning(f"Diretório não encontrado: {caminho}")
        return []

    arquivos = list(caminho.rglob(f"*{extensao}"))
    logger.debug(f"Encontrados {len(arquivos)} arquivos em {caminho}")
    return sorted(arquivos)


def verificar_dados_disponiveis(
    camada: CamadaMedalhao,
    programa: str,
    extensao: str = ".parquet",
) -> bool:
    """
    Verifica se há dados disponíveis para um programa em uma camada.

    Args:
        camada: Nome da camada.
        programa: Nome do programa.
        extensao: Extensão dos arquivos.

    Returns:
        True se houver dados, False caso contrário.
    """
    arquivos = listar_arquivos(camada, programa, extensao)
    disponivel = len(arquivos) > 0

    if disponivel:
        logger.info(f"✅ Dados disponíveis em {camada}/{programa}: {len(arquivos)} arquivo(s)")
    else:
        logger.warning(f"⚠️  Nenhum dado encontrado em {camada}/{programa}")

    return disponivel


def obter_ultimo_arquivo(
    camada: CamadaMedalhao,
    programa: str,
    extensao: str = ".parquet",
) -> Path | None:
    """
    Retorna o arquivo mais recente de um programa em uma camada.

    Args:
        camada: Nome da camada.
        programa: Nome do programa.
        extensao: Extensão dos arquivos.

    Returns:
        Path do arquivo mais recente ou None se não houver arquivos.
    """
    arquivos = listar_arquivos(camada, programa, extensao)
    if not arquivos:
        return None
    return max(arquivos, key=lambda p: p.stat().st_mtime)


def resumo_armazenamento() -> dict:
    """
    Gera um resumo do estado atual do armazenamento.

    Returns:
        Dicionário com contagem de arquivos por camada e programa.
    """
    resumo = {}

    for camada in ("bronze", "prata", "ouro"):
        resumo[camada] = {}
        for programa in PROGRAMAS:
            arquivos = listar_arquivos(camada, programa)  # type: ignore[arg-type]
            resumo[camada][programa] = len(arquivos)

    return resumo
