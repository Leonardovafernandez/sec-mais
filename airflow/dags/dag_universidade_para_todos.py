"""
DAG do Airflow - Universidade Para Todos (UPT).

Pipeline individual do programa UPT:
1. Verificação de VPN/conectividade com PostgreSQL
2. Extração dos dados → camada bronze
3. Transformação bronze → prata (Spark)
4. Transformação prata → ouro (Spark)

Agendamento: diário às 01:30.
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
    from extracao.programas.universidade_para_todos import extrair_universidade_para_todos
    from config.logging_config import configurar_logging

    configurar_logging()
    arquivo = extrair_universidade_para_todos(
        data_execucao=context["logical_date"], verificar_vpn=True
    )
    return str(arquivo)


def bronze_prata_task(**context) -> str:
    from transformacao.bronze_para_prata.universidade_para_todos import transformar_bronze_para_prata_upt
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_bronze_para_prata_upt(data_execucao=context["logical_date"])


def prata_ouro_task(**context) -> str:
    from transformacao.prata_para_ouro.universidade_para_todos import transformar_prata_para_ouro_upt
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_prata_para_ouro_upt(data_execucao=context["logical_date"])


with DAG(
    dag_id="universidade_para_todos",
    description="Pipeline individual do programa Universidade Para Todos (UPT)",
    default_args=args_padrao,
    schedule_interval="30 1 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["sec_mais", "universidade_para_todos", "upt"],
    doc_md=__doc__,
) as dag:

    task_vpn = ShortCircuitOperator(
        task_id="verificar_vpn_postgres",
        python_callable=verificar_vpn_postgres_task,
    )

    task_extracao = PythonOperator(
        task_id="extrair_universidade_para_todos",
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
