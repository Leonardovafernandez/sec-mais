"""
Transformação Prata → Ouro para o programa Bolsa Presença.

Lê os dados padronizados da camada prata, aplica regras de negócio,
agregações e enriquecimentos, gerando dados prontos para consumo
analítico na camada ouro.
"""

from datetime import datetime

from loguru import logger
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from config.logging_config import configurar_logging
from config.settings import configuracoes_spark
from utils.storage import obter_caminho_programa, verificar_dados_disponiveis

NOME_PROGRAMA = "bolsa_presenca"


def criar_sessao_spark(nome_app: str = "sec_mais_prata_ouro_bp") -> SparkSession:
    """Cria e retorna uma sessão Spark configurada."""
    spark = (
        SparkSession.builder.appName(nome_app)
        .master(configuracoes_spark.spark_master)
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def transformar_prata_para_ouro_bolsa_presenca(
    spark: SparkSession | None = None,
    data_execucao: datetime | None = None,
) -> str:
    """
    Executa a transformação prata → ouro para o Bolsa Presença.

    Aplica:
    - Regras de negócio específicas do programa
    - Agregações por escola, município e período
    - Cálculo de indicadores de frequência e pagamento
    - Preparação para consumo pelo dbt

    Args:
        spark: Sessão Spark existente. Se None, cria uma nova.
        data_execucao: Data de execução para controle.

    Returns:
        Caminho do diretório ouro onde os dados foram salvos.
    """
    if data_execucao is None:
        data_execucao = datetime.now()

    logger.info(f"⭐ Iniciando transformação prata→ouro: {NOME_PROGRAMA}")

    if not verificar_dados_disponiveis("prata", NOME_PROGRAMA):
        raise FileNotFoundError(
            f"Nenhum dado na camada prata para '{NOME_PROGRAMA}'. "
            "Execute a transformação bronze→prata primeiro."
        )

    sessao_criada = False
    if spark is None:
        spark = criar_sessao_spark()
        sessao_criada = True

    try:
        caminho_prata = str(obter_caminho_programa("prata", NOME_PROGRAMA))
        logger.info(f"Lendo dados de: {caminho_prata}")

        df: DataFrame = spark.read.parquet(caminho_prata)
        logger.info(f"📥 Registros na prata: {df.count()}")

        # Remove colunas de metadados internos para a camada ouro
        colunas_meta = ["_dt_processamento_prata", "_programa"]
        df = df.drop(*[c for c in colunas_meta if c in df.columns])

        # ==========================================================================
        # REGRAS DE NEGÓCIO - Adapte conforme o schema real do programa
        # ==========================================================================
        #
        # Exemplo de transformações para Bolsa Presença:
        #
        # 1. Classificação de frequência
        # if "nr_frequencia_percentual" in df.columns:
        #     df = df.withColumn(
        #         "categoria_frequencia",
        #         F.when(F.col("nr_frequencia_percentual") >= 75, "APROVADO")
        #         .when(F.col("nr_frequencia_percentual") >= 50, "RISCO")
        #         .otherwise("REPROVADO_FALTA"),
        #     )
        #
        # 2. Flag de pagamento
        # if "st_pagamento" in df.columns:
        #     df = df.withColumn(
        #         "fl_pagamento_realizado",
        #         F.when(F.col("st_pagamento") == "PAGO", True).otherwise(False),
        #     )
        #
        # 3. Extração de ano/mês da data de referência
        # if "dt_referencia" in df.columns:
        #     df = df.withColumn("ano_referencia", F.year(F.col("dt_referencia")))
        #     df = df.withColumn("mes_referencia", F.month(F.col("dt_referencia")))
        #
        # 4. Agregação por escola
        # df_escola = df.groupBy("cd_escola", "nm_escola", "ano_referencia", "mes_referencia").agg(
        #     F.count("cd_aluno").alias("qt_alunos"),
        #     F.avg("nr_frequencia_percentual").alias("media_frequencia"),
        #     F.sum("vl_beneficio").alias("total_beneficio"),
        # )
        # ==========================================================================

        # Metadados da camada ouro
        df = df.withColumn("_dt_processamento_ouro", F.lit(data_execucao.isoformat()))
        df = df.withColumn("_programa", F.lit(NOME_PROGRAMA))

        # Salva na camada ouro
        caminho_ouro = str(obter_caminho_programa("ouro", NOME_PROGRAMA))
        logger.info(f"Salvando dados em ouro: {caminho_ouro}")

        (
            df.write.mode("overwrite")
            .option("compression", "snappy")
            .parquet(caminho_ouro)
        )

        total_ouro = df.count()
        logger.info(f"📤 Registros na ouro: {total_ouro}")
        logger.info(f"✅ Transformação prata→ouro concluída para {NOME_PROGRAMA}")

        return caminho_ouro

    finally:
        if sessao_criada and spark:
            spark.stop()


if __name__ == "__main__":
    configurar_logging()
    try:
        caminho = transformar_prata_para_ouro_bolsa_presenca()
        logger.info(f"Transformação finalizada. Dados em: {caminho}")
    except Exception as e:
        logger.error(f"Falha: {e}")
        raise
