"""
Script de verificação de conectividade com as fontes de dados.

Execute este script antes de qualquer extração para confirmar
que a VPN está ativa e os bancos de dados estão acessíveis.

Uso:
    python -m extracao.verificacao_conexao
    # ou
    python extracao/verificacao_conexao.py
"""

import sys
from datetime import datetime

from loguru import logger

from config.logging_config import configurar_logging
from config.settings import configuracoes, configuracoes_oracle, configuracoes_postgres
from utils.vpn_check import verificar_host, verificar_todas_fontes


def imprimir_separador(char: str = "=", largura: int = 60) -> None:
    """Imprime uma linha separadora."""
    print(char * largura)


def imprimir_status(nome: str, acessivel: bool, detalhes: str = "") -> None:
    """Imprime o status de uma verificação de forma formatada."""
    icone = "✅" if acessivel else "❌"
    status = "ACESSÍVEL" if acessivel else "INACESSÍVEL"
    print(f"  {icone}  {nome:<30} {status}")
    if detalhes:
        print(f"       {detalhes}")


def verificar_configuracoes() -> dict[str, bool]:
    """
    Verifica se as configurações estão preenchidas no .env.

    Returns:
        Dicionário com status de cada banco.
    """
    return {
        "oracle_configurado": configuracoes_oracle.esta_configurado,
        "postgres_configurado": configuracoes_postgres.esta_configurado,
    }


def executar_verificacao_completa() -> bool:
    """
    Executa verificação completa de conectividade e configurações.

    Returns:
        True se tudo estiver acessível, False caso contrário.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    imprimir_separador()
    print(f"  SEC MAIS - Verificação de Conectividade")
    print(f"  Executado em: {agora}")
    print(f"  Ambiente: {configuracoes.ambiente}")
    imprimir_separador()

    # --- Verificação de configurações ---
    print("\n📋 CONFIGURAÇÕES NO .ENV:")
    config_status = verificar_configuracoes()

    imprimir_status("Oracle configurado", config_status["oracle_configurado"],
                    f"Host: {configuracoes_oracle.host or '(não definido)'}")
    imprimir_status("PostgreSQL configurado", config_status["postgres_configurado"],
                    f"Host: {configuracoes_postgres.host or '(não definido)'}")

    if not any(config_status.values()):
        print("\n⚠️  AVISO: Nenhuma fonte está configurada no .env")
        print("   Copie o arquivo .env.example para .env e preencha as credenciais.")
        print()
        return False

    # --- Verificação de conectividade ---
    print("\n🔍 CONECTIVIDADE DE REDE (requer VPN):")

    resultados_rede = {}

    # Oracle
    if configuracoes_oracle.host:
        resultado_oracle = verificar_host(configuracoes_oracle.host, configuracoes_oracle.port)
        resultados_rede["oracle"] = resultado_oracle.acessivel
        imprimir_status(
            f"Oracle ({configuracoes_oracle.host}:{configuracoes_oracle.port})",
            resultado_oracle.acessivel,
            resultado_oracle.mensagem if not resultado_oracle.acessivel else "",
        )
    else:
        print("  ⏭️  Oracle: pulado (host não configurado)")
        resultados_rede["oracle"] = False

    # PostgreSQL
    if configuracoes_postgres.host:
        resultado_pg = verificar_host(configuracoes_postgres.host, configuracoes_postgres.port)
        resultados_rede["postgres"] = resultado_pg.acessivel
        imprimir_status(
            f"PostgreSQL ({configuracoes_postgres.host}:{configuracoes_postgres.port})",
            resultado_pg.acessivel,
            resultado_pg.mensagem if not resultado_pg.acessivel else "",
        )
    else:
        print("  ⏭️  PostgreSQL: pulado (host não configurado)")
        resultados_rede["postgres"] = False

    # --- Resumo ---
    print()
    imprimir_separador("-")
    total_acessiveis = sum(1 for v in resultados_rede.values() if v)
    total = len(resultados_rede)

    print(f"\n📊 RESUMO: {total_acessiveis}/{total} fontes acessíveis")

    if total_acessiveis == total and total > 0:
        print("✅ Todas as fontes estão acessíveis. Pronto para extração!")
    elif total_acessiveis > 0:
        print("⚠️  Algumas fontes estão inacessíveis.")
        print("   Verifique se a VPN está ativa e as configurações estão corretas.")
    else:
        print("❌ Nenhuma fonte está acessível.")
        print("   Verifique se a VPN está ativa e as configurações no .env estão corretas.")

    imprimir_separador()
    print()

    return total_acessiveis == total and total > 0


if __name__ == "__main__":
    configurar_logging(nivel="WARNING")  # Silencia logs do loguru no modo script
    sucesso = executar_verificacao_completa()
    sys.exit(0 if sucesso else 1)
