"""
Transformação Prata → Ouro para o programa Mais Estudos.

Aplica regras de negócio e prepara dados analíticos para consumo.
"""

from datetime import datetime

from loguru import logger
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from config.logging_config import configurar_logging
from config.settings import configuracoes_spark
from utils.storage import obter_caminho_programa, verificar_dados_disponiveis

NOME_PROGRAMA = "mais_estudos"


def criar_sessao_spark(nome_app: str = "sec_mais_prata_ouro_mais_estudos") -> SparkSession:
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


def transformar_prata_para_ouro_mais_estudos(
    spark: SparkSession | None = None,
    data_execucao: datetime | None = None,
) -> str:
    """
    Executa a transformação prata → ouro para o Mais Estudos.

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
        raise FileNotFoundError(f"Nenhum dado na camada prata para '{NOME_PROGRAMA}'.")

    sessao_criada = False
    if spark is None:
        spark = criar_sessao_spark()
        sessao_criada = True

    try:
        caminho_prata = str(obter_caminho_programa("prata", NOME_PROGRAMA))
        df: DataFrame = spark.read.parquet(caminho_prata)
        logger.info(f"📥 Registros na prata: {df.count()}")

        df = df.drop(*[c for c in ["_dt_processamento_prata", "_programa"] if c in df.columns])

        # ==========================================================================
        # REGRAS DE NEGÓCIO MAIS ESTUDOS - Adapte conforme o schema real
        # ==========================================================================
        #
        # 1. Categorização de atividades
        # if "nm_atividade" in df.columns:
        #     df = df.withColumn(
        #         "tipo_atividade",
        #         F.when(F.col("nm_atividade").contains("REFORCO"), "REFORCO_ESCOLAR")
        #         .when(F.col("nm_atividade").contains("ESPORTE"), "ATIVIDADE_ESPORTIVA")
        #         .when(F.col("nm_atividade").contains("CULTURA"), "ATIVIDADE_CULTURAL")
        #         .otherwise("OUTRO"),
        #     )
        #
        # 2. Total de horas por aluno
        # if "nr_horas" in df.columns and "cd_aluno" in df.columns:
        #     df_horas = df.groupBy("cd_aluno").agg(
        #         F.sum("nr_horas").alias("total_horas_atividades"),
        #         F.countDistinct("nm_atividade").alias("qt_atividades_distintas"),
        #     )
        #     df = df.join(df_horas, on="cd_aluno", how="left")
        # ==========================================================================

        df = df.withColumn("_dt_processamento_ouro", F.lit(data_execucao.isoformat()))
        df = df.withColumn("_programa", F.lit(NOME_PROGRAMA))

        caminho_ouro = str(obter_caminho_programa("ouro", NOME_PROGRAMA))
        (df.write.mode("overwrite").option("compression", "snappy").parquet(caminho_ouro))

        logger.info(f"✅ Transformação prata→ouro concluída para {NOME_PROGRAMA}")
        return caminho_ouro

    finally:
        if sessao_criada and spark:
            spark.stop()


if __name__ == "__main__":
    configurar_logging()
    try:
        caminho = transformar_prata_para_ouro_mais_estudos()
        logger.info(f"Transformação finalizada. Dados em: {caminho}")
    except Exception as e:
        logger.error(f"Falha: {e}")
        raise
