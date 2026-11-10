"""
Transformação Bronze → Prata para o programa Mais Estudos.

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

NOME_PROGRAMA = "mais_estudos"


def criar_sessao_spark(nome_app: str = "sec_mais_bronze_prata_mais_estudos") -> SparkSession:
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


def transformar_bronze_para_prata_mais_estudos(
    spark: SparkSession | None = None,
    data_execucao: datetime | None = None,
) -> str:
    """
    Executa a transformação bronze → prata para o Mais Estudos.

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
        df: DataFrame = spark.read.parquet(caminho_bronze)
        logger.info(f"📥 Registros na bronze: {df.count()}")

        # Padronização de colunas
        for coluna in df.columns:
            novo_nome = coluna.lower().strip().replace(" ", "_").replace("-", "_")
            if coluna != novo_nome:
                df = df.withColumnRenamed(coluna, novo_nome)

        # Remove colunas de controle
        df = df.drop(*[c for c in ["_data_extracao", "_programa"] if c in df.columns])

        # Remove duplicatas
        df = df.dropDuplicates()

        # Trata nulos em strings
        colunas_string = [f.name for f in df.schema.fields if isinstance(f.dataType, StringType)]
        for col in colunas_string:
            df = df.withColumn(col, F.trim(F.col(col)))
            df = df.withColumn(col, F.when(F.col(col) == "", None).otherwise(F.col(col)))

        # TODO: Padronizações específicas do Mais Estudos após conhecer o schema real
        # Exemplo:
        # if "nr_horas" in df.columns:
        #     df = df.withColumn("nr_horas", F.col("nr_horas").cast("integer"))
        # if "nm_atividade" in df.columns:
        #     df = df.withColumn("nm_atividade", F.upper(F.trim(F.col("nm_atividade"))))

        # Metadados
        df = df.withColumn("_dt_processamento_prata", F.lit(data_execucao.isoformat()))
        df = df.withColumn("_programa", F.lit(NOME_PROGRAMA))

        # Salva na prata
        caminho_prata = str(obter_caminho_programa("prata", NOME_PROGRAMA))
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
        caminho = transformar_bronze_para_prata_mais_estudos()
        logger.info(f"Transformação finalizada. Dados em: {caminho}")
    except Exception as e:
        logger.error(f"Falha: {e}")
        raise
