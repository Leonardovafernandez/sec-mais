"""
DAG do Airflow - Bolsa Presença.

Pipeline individual do programa Bolsa Presença:
1. Verificação de VPN/conectividade com Oracle
2. Extração dos dados → camada bronze
3. Transformação bronze → prata (Spark)
4. Transformação prata → ouro (Spark)

Agendamento: diário às 01:00.
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


def verificar_vpn_oracle_task() -> bool:
    """Verifica conectividade com o Oracle (requer VPN)."""
    from utils.vpn_check import verificar_vpn_oracle
    from config.logging_config import configurar_logging

    configurar_logging()
    acessivel = verificar_vpn_oracle()

    if not acessivel:
        raise ConnectionError(
            "Oracle não está acessível. Verifique se a VPN está ativa."
        )
    return acessivel


def extrair_task(**context) -> str:
    from extracao.programas.bolsa_presenca import extrair_bolsa_presenca
    from config.logging_config import configurar_logging

    configurar_logging()
    arquivo = extrair_bolsa_presenca(
        data_execucao=context["logical_date"], verificar_vpn=True
    )
    return str(arquivo)


def bronze_prata_task(**context) -> str:
    from transformacao.bronze_para_prata.bolsa_presenca import transformar_bronze_para_prata_bolsa_presenca
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_bronze_para_prata_bolsa_presenca(data_execucao=context["logical_date"])


def prata_ouro_task(**context) -> str:
    from transformacao.prata_para_ouro.bolsa_presenca import transformar_prata_para_ouro_bolsa_presenca
    from config.logging_config import configurar_logging

    configurar_logging()
    return transformar_prata_para_ouro_bolsa_presenca(data_execucao=context["logical_date"])


with DAG(
    dag_id="bolsa_presenca",
    description="Pipeline individual do programa Bolsa Presença",
    default_args=args_padrao,
    schedule_interval="0 1 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["sec_mais", "bolsa_presenca"],
    doc_md=__doc__,
) as dag:

    task_vpn = ShortCircuitOperator(
        task_id="verificar_vpn_oracle",
        python_callable=verificar_vpn_oracle_task,
    )

    task_extracao = PythonOperator(
        task_id="extrair_bolsa_presenca",
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
