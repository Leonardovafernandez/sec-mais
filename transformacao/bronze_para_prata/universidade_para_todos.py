"""
Transformação Bronze → Prata para o programa Universidade Para Todos (UPT).

Lê os dados brutos da camada bronze, aplica padronizações
e limpeza, e persiste o resultado na camada prata.
"""

from datetime import datetime

from loguru import logger
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from config.logging_config import configurar_logging
from config.settings import configuracoes_spark
from utils.storage import obter_caminho_programa, verificar_dados_disponiveis

NOME_PROGRAMA = "universidade_para_todos"


def criar_sessao_spark(nome_app: str = "sec_mais_bronze_prata_upt") -> SparkSession:
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


def transformar_bronze_para_prata_upt(
    spark: SparkSession | None = None,
    data_execucao: datetime | None = None,
) -> str:
    """
    Executa a transformação bronze → prata para o UPT.

    Args:
        spark: Sessão Spark existente. Se None, cria uma nova.
        data_execucao: Data de execução para particionamento.

    Returns:
        Caminho do diretório prata onde os dados foram salvos.
    """
    if data_execucao is None:
        data_execucao = datetime.now()

    logger.info(f"🔄 Iniciando transformação bronze→prata: {NOME_PROGRAMA}")

    if not verificar_dados_disponiveis("bronze", NOME_PROGRAMA):
        raise FileNotFoundError(
            f"Nenhum dado na camada bronze para '{NOME_PROGRAMA}'. Execute a extração primeiro."
        )

    sessao_criada = False
    if spark is None:
        spark = criar_sessao_spark()
        sessao_criada = True

    try:
        caminho_bronze = str(obter_caminho_programa("bronze", NOME_PROGRAMA))
        logger.info(f"Lendo dados de: {caminho_bronze}")

        df: DataFrame = spark.read.parquet(caminho_bronze)
        logger.info(f"📥 Registros na bronze: {df.count()}")

        # Padronização de colunas
        for coluna in df.columns:
            novo_nome = coluna.lower().strip().replace(" ", "_").replace("-", "_")
            if coluna != novo_nome:
                df = df.withColumnRenamed(coluna, novo_nome)

        # Remove colunas de controle
        colunas_controle = ["_data_extracao", "_programa"]
        df = df.drop(*[c for c in colunas_controle if c in df.columns])

        # Remove duplicatas
        df = df.dropDuplicates()

        # Trata nulos em colunas de texto
        colunas_string = [
            f.name for f in df.schema.fields if isinstance(f.dataType, StringType)
        ]
        for col in colunas_string:
            df = df.withColumn(col, F.trim(F.col(col)))
            df = df.withColumn(col, F.when(F.col(col) == "", None).otherwise(F.col(col)))

        # TODO: Padronizações específicas do UPT após conhecer o schema real
        # Exemplo:
        # if "nm_beneficiario" in df.columns:
        #     df = df.withColumn("nm_beneficiario", F.upper(F.trim(F.col("nm_beneficiario"))))
        # if "cd_cpf" in df.columns:
        #     df = df.withColumn("cd_cpf", F.regexp_replace(F.col("cd_cpf"), r"\D", ""))

        # Metadados
        df = df.withColumn("_dt_processamento_prata", F.lit(data_execucao.isoformat()))
        df = df.withColumn("_programa", F.lit(NOME_PROGRAMA))

        # Salva na prata
        caminho_prata = str(obter_caminho_programa("prata", NOME_PROGRAMA))
        logger.info(f"Salvando dados em prata: {caminho_prata}")

        (
            df.write.mode("overwrite")
            .option("compression", "snappy")
            .partitionBy("_dt_processamento_prata")
            .parquet(caminho_prata)
        )

        logger.info(f"✅ Transformação bronze→prata concluída para {NOME_PROGRAMA}")
        return caminho_prata

    finally:
        if sessao_criada and spark:
            spark.stop()


if __name__ == "__main__":
    configurar_logging()
    try:
        caminho = transformar_bronze_para_prata_upt()
        logger.info(f"Transformação finalizada. Dados em: {caminho}")
    except Exception as e:
        logger.error(f"Falha: {e}")
        raise
