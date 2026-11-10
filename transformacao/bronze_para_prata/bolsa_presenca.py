"""
Transformação Bronze → Prata para o programa Bolsa Presença.

Lê os dados brutos da camada bronze, aplica padronizações
e limpeza, e persiste o resultado na camada prata.

Transformações aplicadas:
- Nomes de colunas em snake_case minúsculo
- Remoção de duplicatas
- Tratamento de valores nulos
- Padronização de tipos de dados
- Remoção de colunas de controle de extração
"""

from datetime import datetime

from loguru import logger
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, DoubleType, IntegerType, StringType

from config.logging_config import configurar_logging
from config.settings import configuracoes, configuracoes_spark
from utils.storage import obter_caminho_programa, verificar_dados_disponiveis

NOME_PROGRAMA = "bolsa_presenca"


def criar_sessao_spark(nome_app: str = "sec_mais_bronze_prata") -> SparkSession:
    """
    Cria e retorna uma sessão Spark configurada.

    Args:
        nome_app: Nome da aplicação Spark.

    Returns:
        SparkSession configurada.
    """
    spark = (
        SparkSession.builder.appName(nome_app)
        .master(configuracoes_spark.spark_master)
        .config("spark.sql.parquet.enableVectorizedReader", "true")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def transformar_bronze_para_prata_bolsa_presenca(
    spark: SparkSession | None = None,
    data_execucao: datetime | None = None,
) -> str:
    """
    Executa a transformação bronze → prata para o Bolsa Presença.

    Args:
        spark: Sessão Spark existente. Se None, cria uma nova.
        data_execucao: Data de execução para particionamento da saída.

    Returns:
        Caminho do diretório prata onde os dados foram salvos.

    Raises:
        FileNotFoundError: Se não houver dados na camada bronze.
    """
    if data_execucao is None:
        data_execucao = datetime.now()

    logger.info(f"🔄 Iniciando transformação bronze→prata: {NOME_PROGRAMA}")

    # Verifica disponibilidade de dados na bronze
    if not verificar_dados_disponiveis("bronze", NOME_PROGRAMA):
        raise FileNotFoundError(
            f"Nenhum dado encontrado na camada bronze para '{NOME_PROGRAMA}'. "
            "Execute a extração primeiro."
        )

    # Cria ou reutiliza sessão Spark
    sessao_criada = False
    if spark is None:
        spark = criar_sessao_spark()
        sessao_criada = True

    try:
        # --- Leitura da camada bronze ---
        caminho_bronze = str(obter_caminho_programa("bronze", NOME_PROGRAMA))
        logger.info(f"Lendo dados de: {caminho_bronze}")

        df: DataFrame = spark.read.parquet(caminho_bronze)
        total_bruto = df.count()
        logger.info(f"📥 Registros na bronze: {total_bruto}")

        # --- Padronização de nomes de colunas ---
        logger.info("Padronizando nomes de colunas...")
        for coluna in df.columns:
            novo_nome = coluna.lower().strip().replace(" ", "_").replace("-", "_")
            if coluna != novo_nome:
                df = df.withColumnRenamed(coluna, novo_nome)

        # --- Remoção de colunas de controle de extração ---
        colunas_controle = ["_data_extracao", "_programa"]
        colunas_existentes = df.columns
        colunas_remover = [c for c in colunas_controle if c in colunas_existentes]
        if colunas_remover:
            df = df.drop(*colunas_remover)

        # --- Remoção de duplicatas ---
        logger.info("Removendo duplicatas...")
        df = df.dropDuplicates()

        # --- Tratamento de nulos ---
        # Colunas de texto: substitui null por string vazia
        colunas_string = [
            field.name for field in df.schema.fields if isinstance(field.dataType, StringType)
        ]
        for coluna in colunas_string:
            df = df.withColumn(coluna, F.trim(F.col(coluna)))
            df = df.withColumn(
                coluna, F.when(F.col(coluna) == "", None).otherwise(F.col(coluna))
            )

        # --- Padronizações específicas do Bolsa Presença ---
        # TODO: Adicionar padronizações específicas após conhecer o schema real
        # Exemplo:
        # if "nm_aluno" in df.columns:
        #     df = df.withColumn("nm_aluno", F.upper(F.trim(F.col("nm_aluno"))))
        # if "vl_beneficio" in df.columns:
        #     df = df.withColumn("vl_beneficio", F.col("vl_beneficio").cast(DoubleType()))

        # --- Adiciona metadados de processamento ---
        df = df.withColumn("_dt_processamento_prata", F.lit(data_execucao.isoformat()))
        df = df.withColumn("_programa", F.lit(NOME_PROGRAMA))

        # --- Persistência na camada prata ---
        caminho_prata = str(obter_caminho_programa("prata", NOME_PROGRAMA))
        logger.info(f"Salvando dados em prata: {caminho_prata}")

        (
            df.write.mode("overwrite")
            .option("compression", "snappy")
            .partitionBy("_dt_processamento_prata")
            .parquet(caminho_prata)
        )

        total_prata = df.count()
        logger.info(f"📤 Registros na prata: {total_prata}")
        logger.info(f"✅ Transformação bronze→prata concluída para {NOME_PROGRAMA}")

        return caminho_prata

    finally:
        if sessao_criada and spark:
            spark.stop()


if __name__ == "__main__":
    configurar_logging()
    try:
        caminho = transformar_bronze_para_prata_bolsa_presenca()
        logger.info(f"Transformação finalizada. Dados em: {caminho}")
    except Exception as e:
        logger.error(f"Falha na transformação: {e}")
        raise
