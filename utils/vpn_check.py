"""
Utilitário para verificação de conectividade VPN/rede.

Verifica se as fontes de dados estão acessíveis antes de
iniciar qualquer processo de extração, garantindo que a VPN
esteja ativa quando necessário.
"""

import socket
from typing import NamedTuple

from loguru import logger

from config.settings import configuracoes_oracle, configuracoes_postgres


class ResultadoConexao(NamedTuple):
    """Resultado da verificação de conectividade de um host."""

    host: str
    porta: int
    acessivel: bool
    mensagem: str


def verificar_host(host: str, porta: int, timeout: float = 5.0) -> ResultadoConexao:
    """
    Verifica se um host:porta está acessível via TCP.

    Args:
        host: Endereço do host a verificar.
        porta: Número da porta TCP.
        timeout: Tempo máximo de espera em segundos.

    Returns:
        ResultadoConexao com o status da verificação.
    """
    if not host:
        return ResultadoConexao(
            host=host,
            porta=porta,
            acessivel=False,
            mensagem="Host não configurado (verifique o arquivo .env)",
        )

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        resultado = sock.connect_ex((host, porta))
        sock.close()

        if resultado == 0:
            return ResultadoConexao(
                host=host,
                porta=porta,
                acessivel=True,
                mensagem=f"Conexão bem-sucedida com {host}:{porta}",
            )
        else:
            return ResultadoConexao(
                host=host,
                porta=porta,
                acessivel=False,
                mensagem=(
                    f"Falha na conexão com {host}:{porta} (código: {resultado}). "
                    "Verifique se a VPN está ativa."
                ),
            )
    except socket.timeout:
        return ResultadoConexao(
            host=host,
            porta=porta,
            acessivel=False,
            mensagem=(
                f"Timeout ao conectar em {host}:{porta}. "
                "Verifique se a VPN está ativa e o host está correto."
            ),
        )
    except socket.gaierror as e:
        return ResultadoConexao(
            host=host,
            porta=porta,
            acessivel=False,
            mensagem=f"Erro de DNS ao resolver {host}: {e}. VPN pode estar inativa.",
        )
    except OSError as e:
        return ResultadoConexao(
            host=host,
            porta=porta,
            acessivel=False,
            mensagem=f"Erro de rede ao conectar em {host}:{porta}: {e}",
        )


def verificar_vpn_oracle() -> bool:
    """
    Verifica se o banco Oracle está acessível (VPN ativa).

    Returns:
        True se acessível, False caso contrário.
    """
    resultado = verificar_host(configuracoes_oracle.host, configuracoes_oracle.port)

    if resultado.acessivel:
        logger.info(f"✅ Oracle acessível: {resultado.mensagem}")
    else:
        logger.warning(f"❌ Oracle inacessível: {resultado.mensagem}")

    return resultado.acessivel


def verificar_vpn_postgres(host: str | None = None, port: int | None = None) -> bool:
    """
    Verifica se o banco PostgreSQL está acessível (VPN ativa).

    Args:
        host: Host específico a verificar (opcional, padrão configuracoes_postgres.host).
        port: Porta específica (opcional, padrão configuracoes_postgres.port).

    Returns:
        True se acessível, False caso contrário.
    """
    alvo_host = host or configuracoes_postgres.host
    alvo_port = port or configuracoes_postgres.port
    resultado = verificar_host(alvo_host, alvo_port)

    if resultado.acessivel:
        logger.info(f"✅ PostgreSQL acessível: {resultado.mensagem}")
    else:
        logger.warning(f"❌ PostgreSQL inacessível: {resultado.mensagem}")

    return resultado.acessivel


def verificar_todas_fontes() -> dict[str, bool]:
    """
    Verifica conectividade com todas as fontes de dados configuradas.

    Returns:
        Dicionário com o status de cada fonte.
    """
    logger.info("🔍 Verificando conectividade com as fontes de dados...")

    status = {
        "oracle": verificar_vpn_oracle(),
        "postgres": verificar_vpn_postgres(),
    }

    total = len(status)
    acessiveis = sum(1 for v in status.values() if v)

    logger.info(f"📊 Resultado: {acessiveis}/{total} fontes acessíveis")

    if acessiveis == 0:
        logger.error(
            "🚫 Nenhuma fonte de dados acessível. "
            "Verifique se a VPN está ativa e as configurações no .env estão corretas."
        )
    elif acessiveis < total:
        logger.warning(
            "⚠️  Algumas fontes estão inacessíveis. "
            "Verifique a VPN e as configurações no .env."
        )

    return status


def exigir_vpn_oracle() -> None:
    """
    Verifica VPN para Oracle e lança exceção se não estiver acessível.

    Raises:
        ConnectionError: Se o Oracle não estiver acessível.
    """
    if not verificar_vpn_oracle():
        raise ConnectionError(
            f"Oracle não está acessível em {configuracoes_oracle.host}:{configuracoes_oracle.port}. "
            "Certifique-se de que a VPN está ativa antes de executar a extração."
        )


def exigir_vpn_postgres() -> None:
    """
    Verifica VPN para PostgreSQL e lança exceção se não estiver acessível.

    Raises:
        ConnectionError: Se o PostgreSQL não estiver acessível.
    """
    if not verificar_vpn_postgres():
        raise ConnectionError(
            f"PostgreSQL não está acessível em {configuracoes_postgres.host}:{configuracoes_postgres.port}. "
            "Certifique-se de que a VPN está ativa antes de executar a extração."
        )
