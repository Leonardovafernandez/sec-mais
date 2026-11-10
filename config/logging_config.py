"""
Configuração de logging para o projeto SEC MAIS.

Utiliza loguru para logging colorido no console e
rotacionamento automático de arquivos de log.
"""

import sys
from pathlib import Path

from loguru import logger


def configurar_logging(
    nivel: str = "INFO",
    caminho_log: Path | None = None,
    rotacao: str = "10 MB",
    retencao: str = "30 days",
) -> None:
    """
    Configura o sistema de logging do projeto.

    Args:
        nivel: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        caminho_log: Caminho para o arquivo de log. Se None, usa o padrão do projeto.
        rotacao: Tamanho máximo do arquivo antes de rotacionar (ex: "10 MB").
        retencao: Tempo de retenção dos logs rotacionados (ex: "30 days").
    """
    # Remove handlers padrão do loguru
    logger.remove()

    # Formato para o console (colorido)
    formato_console = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Formato para o arquivo (sem cores)
    formato_arquivo = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # Handler do console
    logger.add(
        sys.stdout,
        format=formato_console,
        level=nivel,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Handler do arquivo de log
    if caminho_log is None:
        # Encontra o diretório raiz do projeto
        raiz = Path(__file__).parent.parent
        caminho_log = raiz / "logs" / "sec_mais_{time:YYYY-MM-DD}.log"

    # Garante que o diretório de logs existe
    caminho_log.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(caminho_log),
        format=formato_arquivo,
        level=nivel,
        rotation=rotacao,
        retention=retencao,
        compression="zip",
        backtrace=True,
        diagnose=True,
        encoding="utf-8",
    )

    logger.info(f"Logging configurado. Nível: {nivel}")


def obter_logger(nome: str):
    """
    Retorna um logger com o nome do módulo especificado.

    Args:
        nome: Nome do módulo (geralmente __name__).

    Returns:
        Logger configurado.
    """
    return logger.bind(modulo=nome)
