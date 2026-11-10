"""
DAG do Airflow - Pipeline Completa SEC MAIS.

Orquestra todos os 4 programas em paralelo:
- Bolsa Presença
- Universidade Para Todos (UPT)
- Mais Estudos
- Pé-de-Meia

Fluxo para cada programa:
1. Verificação de VPN (pré-condição global)
2. Extração → Bronze
3. Transformação Bronze → Prata
4. Transformação Prata → Ouro

Os 4 programas executam em paralelo após a verificação de VPN.
Agendamento: diário às 02:00 (horário local).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator

# Argumentos padrão para todas as tasks
args_padrao = {
    "owner": "sec_mais",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def verificar_vpn_task() -> bool:
    """
    Task de verificação de VPN.
    
    Verifica se ambas as fontes de dados estão acessíveis.
    Se nenhuma estiver, interrompe o pipeline (ShortCircuit).

    Returns:
        True se ao menos uma fonte estiver acessível.
    """
    from utils.vpn_check import verificar_todas_fontes
    from config.logging_config import configurar_logging

    configurar_logging()
    status = verificar_todas_fontes()
    acessiveis = any(status.values())

    if not acessiveis:
        raise ConnectionError(
            "❌ Nenhuma fonte de dados acessível. "
            "Verifique se a VPN está ativa. Pipeline interrompida."
        )

    return acessiveis


# --- Tasks de Extração ---

def extrair_bolsa_presenca_task(**context) -> str:
    """Task de extração do Bolsa Presença."""
    from extracao.programas.bolsa_presenca import extrair_bolsa_presenca
    from config.logging_config import configurar_logging

    configurar_logging()
    data_execucao = context["logical_date"]
    arquivo = extrair_bolsa_presenca(data_execucao=data_execucao, verificar_vpn=True)
    return str(arquivo)


def extrair_upt_task(**context) -> str:
    """Task de extração do UPT."""
    from extracao.programas.universidade_para_todos import extrair_universidade_para_todos
    from config.logging_config import configurar_logging

    configurar_logging()
    data_execucao = context["logical_date"]
    arquivo = extrair_universidade_para_todos(data_execucao=data_execucao, verificar_vpn=True)
    return str(arquivo)


def extrair_mais_estudos_task(**context) -> str:
    """Task de extração do Mais Estudos."""
    from extracao.programas.mais_estudos import extrair_mais_estudos
    from config.logging_config import configurar_logging

    configurar_logging()
    data_execucao = context["logical_date"]
    arquivo = extrair_mais_estudos(data_execucao=data_execucao, verificar_vpn=True)
    return str(arquivo)


def extrair_pe_de_meia_task(**context) -> str:
    """Task de extração do Pé-de-Meia."""
    from extracao.programas.pe_de_meia import extrair_pe_de_meia
    from config.logging_config import configurar_logging

    configurar_logging()
    data_execucao = context["logical_date"]
    arquivo = extrair_pe_de_meia(data_execucao=data_execucao, verificar_vpn=True)
    return str(arquivo)


# --- Tasks de Transformação Bronze → Prata ---

def bronze_prata_bolsa_presenca_task(**context) -> str:
    """Task de transformação bronze→prata do Bolsa Presença."""
    from transformacao.bronze_para_prata.bolsa_presenca import transformar_bronze_para_prata_bolsa_presenca
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_bronze_para_prata_bolsa_presenca(data_execucao=context["logical_date"])


def bronze_prata_upt_task(**context) -> str:
    """Task de transformação bronze→prata do UPT."""
    from transformacao.bronze_para_prata.universidade_para_todos import transformar_bronze_para_prata_upt
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_bronze_para_prata_upt(data_execucao=context["logical_date"])


def bronze_prata_mais_estudos_task(**context) -> str:
    """Task de transformação bronze→prata do Mais Estudos."""
    from transformacao.bronze_para_prata.mais_estudos import transformar_bronze_para_prata_mais_estudos
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_bronze_para_prata_mais_estudos(data_execucao=context["logical_date"])


def bronze_prata_pe_de_meia_task(**context) -> str:
    """Task de transformação bronze→prata do Pé-de-Meia."""
    from transformacao.bronze_para_prata.pe_de_meia import transformar_bronze_para_prata_pe_de_meia
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_bronze_para_prata_pe_de_meia(data_execucao=context["logical_date"])


# --- Tasks de Transformação Prata → Ouro ---

def prata_ouro_bolsa_presenca_task(**context) -> str:
    """Task de transformação prata→ouro do Bolsa Presença."""
    from transformacao.prata_para_ouro.bolsa_presenca import transformar_prata_para_ouro_bolsa_presenca
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_prata_para_ouro_bolsa_presenca(data_execucao=context["logical_date"])


def prata_ouro_upt_task(**context) -> str:
    """Task de transformação prata→ouro do UPT."""
    from transformacao.prata_para_ouro.universidade_para_todos import transformar_prata_para_ouro_upt
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_prata_para_ouro_upt(data_execucao=context["logical_date"])


def prata_ouro_mais_estudos_task(**context) -> str:
    """Task de transformação prata→ouro do Mais Estudos."""
    from transformacao.prata_para_ouro.mais_estudos import transformar_prata_para_ouro_mais_estudos
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_prata_para_ouro_mais_estudos(data_execucao=context["logical_date"])


def prata_ouro_pe_de_meia_task(**context) -> str:
    """Task de transformação prata→ouro do Pé-de-Meia."""
    from transformacao.prata_para_ouro.pe_de_meia import transformar_prata_para_ouro_pe_de_meia
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_prata_para_ouro_pe_de_meia(data_execucao=context["logical_date"])


# =============================================================================
# Definição da DAG
# =============================================================================

with DAG(
    dag_id="pipeline_completa_sec_mais",
    description="Pipeline completa SEC MAIS - todos os 4 programas em paralelo",
    default_args=args_padrao,
    schedule_interval="0 2 * * *",  # Diariamente às 02:00
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["sec_mais", "pipeline_completa"],
    doc_md=__doc__,
) as dag:

    # ----- Verificação de VPN (pré-condição global) -----
    task_verificar_vpn = ShortCircuitOperator(
        task_id="verificar_vpn",
        python_callable=verificar_vpn_task,
        doc_md="Verifica conectividade com as fontes de dados (requer VPN).",
    )

    # ----- BOLSA PRESENÇA -----
    task_extrair_bp = PythonOperator(
        task_id="extrair_bolsa_presenca",
        python_callable=extrair_bolsa_presenca_task,
    )
    task_bronze_prata_bp = PythonOperator(
        task_id="bronze_prata_bolsa_presenca",
        python_callable=bronze_prata_bolsa_presenca_task,
    )
    task_prata_ouro_bp = PythonOperator(
        task_id="prata_ouro_bolsa_presenca",
        python_callable=prata_ouro_bolsa_presenca_task,
    )

    # ----- UNIVERSIDADE PARA TODOS -----
    task_extrair_upt = PythonOperator(
        task_id="extrair_universidade_para_todos",
        python_callable=extrair_upt_task,
    )
    task_bronze_prata_upt = PythonOperator(
        task_id="bronze_prata_universidade_para_todos",
        python_callable=bronze_prata_upt_task,
    )
    task_prata_ouro_upt = PythonOperator(
        task_id="prata_ouro_universidade_para_todos",
        python_callable=prata_ouro_upt_task,
    )

    # ----- MAIS ESTUDOS -----
    task_extrair_me = PythonOperator(
        task_id="extrair_mais_estudos",
        python_callable=extrair_mais_estudos_task,
    )
    task_bronze_prata_me = PythonOperator(
        task_id="bronze_prata_mais_estudos",
        python_callable=bronze_prata_mais_estudos_task,
    )
    task_prata_ouro_me = PythonOperator(
        task_id="prata_ouro_mais_estudos",
        python_callable=prata_ouro_mais_estudos_task,
    )

    # ----- PÉ-DE-MEIA -----
    task_extrair_pdm = PythonOperator(
        task_id="extrair_pe_de_meia",
        python_callable=extrair_pe_de_meia_task,
    )
    task_bronze_prata_pdm = PythonOperator(
        task_id="bronze_prata_pe_de_meia",
        python_callable=bronze_prata_pe_de_meia_task,
    )
    task_prata_ouro_pdm = PythonOperator(
        task_id="prata_ouro_pe_de_meia",
        python_callable=prata_ouro_pe_de_meia_task,
    )

    # ==========================================================================
    # Definição das dependências
    # VPN → (os 4 programas em paralelo, cada um: extração → b→p → p→o)
    # ==========================================================================

    task_verificar_vpn >> [task_extrair_bp, task_extrair_upt, task_extrair_me, task_extrair_pdm]

    task_extrair_bp >> task_bronze_prata_bp >> task_prata_ouro_bp
    task_extrair_upt >> task_bronze_prata_upt >> task_prata_ouro_upt
    task_extrair_me >> task_bronze_prata_me >> task_prata_ouro_me
    task_extrair_pdm >> task_bronze_prata_pdm >> task_prata_ouro_pdm
