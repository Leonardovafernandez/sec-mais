"""
DAG do Airflow - Pé-de-Meia.

Pipeline individual do programa Pé-de-Meia:
1. Verificação de VPN/conectividade com PostgreSQL
2. Extração dos dados → camada bronze
3. Transformação bronze → prata (Spark)
4. Transformação prata → ouro (Spark)

Agendamento: diário às 01:45.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator

args_padrao = {
    "owner": "sec_mais",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def verificar_vpn_postgres_task() -> bool:
    """Verifica conectividade com o PostgreSQL (requer VPN)."""
    from utils.vpn_check import verificar_vpn_postgres
    from config.logging_config import configurar_logging

    configurar_logging()
    acessivel = verificar_vpn_postgres()

    if not acessivel:
        raise ConnectionError(
            "PostgreSQL não está acessível. Verifique se a VPN está ativa."
        )
    return acessivel


def extrair_task(**context) -> str:
    from extracao.programas.pe_de_meia import extrair_pe_de_meia
    from config.logging_config import configurar_logging

    configurar_logging()
    arquivo = extrair_pe_de_meia(
        data_execucao=context["logical_date"], verificar_vpn=True
    )
    return str(arquivo)


def bronze_prata_task(**context) -> str:
    from transformacao.bronze_para_prata.pe_de_meia import transformar_bronze_para_prata_pe_de_meia
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_bronze_para_prata_pe_de_meia(data_execucao=context["logical_date"])


def prata_ouro_task(**context) -> str:
    from transformacao.prata_para_ouro.pe_de_meia import transformar_prata_para_ouro_pe_de_meia
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_prata_para_ouro_pe_de_meia(data_execucao=context["logical_date"])


with DAG(
    dag_id="pe_de_meia",
    description="Pipeline individual do programa Pé-de-Meia",
    default_args=args_padrao,
    schedule_interval="45 1 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["sec_mais", "pe_de_meia"],
    doc_md=__doc__,
) as dag:

    task_vpn = ShortCircuitOperator(
        task_id="verificar_vpn_postgres",
        python_callable=verificar_vpn_postgres_task,
    )

    task_extracao = PythonOperator(
        task_id="extrair_pe_de_meia",
        python_callable=extrair_task,
    )

    task_bronze_prata = PythonOperator(
        task_id="transformar_bronze_prata",
        python_callable=bronze_prata_task,
    )

    task_prata_ouro = PythonOperator(
        task_id="transformar_prata_ouro",
        python_callable=prata_ouro_task,
    )

    task_vpn >> task_extracao >> task_bronze_prata >> task_prata_ouro
