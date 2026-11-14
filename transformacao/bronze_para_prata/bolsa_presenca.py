"""
Transformação Bronze → Prata para o programa Bolsa Presença (SIADIANTE).

Lê os dados brutos da camada bronze, aplica padronizações, higienização
de matrícula e CPF, regras de negócio e persiste o DataFrame
ESTUDANTE_BOLSA_PRESENCA na camada prata.

Estrutura final na Prata:
- MATRICULA
- NOME_ESTUDANTE
- CODSEC
- MUNICIPIO
- ANO
- MES
- VALOR
- STATUS_BOLSA_PRESENCA
- CPF_RESPONSAVEL
"""

from datetime import datetime
from pathlib import Path

from loguru import logger
import pandas as pd

from config.logging_config import configurar_logging
from config.settings import configuracoes_spark
from utils.storage import obter_caminho_programa, verificar_dados_disponiveis

NOME_PROGRAMA = "bolsa_presenca"


def padronizar_bolsa_presenca_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica regras de negócio e higienização via Pandas."""
    # Renomeia colunas para caixa alta e strip
    col_map = {c: c.strip().upper() for c in df.columns}
    df = df.rename(columns=col_map)

    # Mapeamento flexível de nomes de colunas
    if "NUMERO_MATRICULA" in df.columns and "MATRICULA" not in df.columns:
        df["MATRICULA"] = df["NUMERO_MATRICULA"]
    if "STATUS" in df.columns and "STATUS_BOLSA_PRESENCA" not in df.columns:
        df["STATUS_BOLSA_PRESENCA"] = df["STATUS"]

    # 1. Higienização da Matrícula (apenas dígitos numéricos, strip)
    if "MATRICULA" in df.columns:
        df["MATRICULA"] = (
            df["MATRICULA"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.strip()
        )
        df["MATRICULA"] = df["MATRICULA"].replace("", None)

    # 2. Padronização do Nome do Estudante (caixa alta, espaços únicos)
    if "NOME_ESTUDANTE" in df.columns:
        df["NOME_ESTUDANTE"] = (
            df["NOME_ESTUDANTE"]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"\s+", " ", regex=True)
        )

    # 3. Município (caixa alta)
    if "MUNICIPIO" in df.columns:
        df["MUNICIPIO"] = df["MUNICIPIO"].astype(str).str.strip().str.upper()

    # 4. Status Bolsa Presença (caixa alta)
    if "STATUS_BOLSA_PRESENCA" in df.columns:
        df["STATUS_BOLSA_PRESENCA"] = (
            df["STATUS_BOLSA_PRESENCA"].astype(str).str.strip().str.upper()
        )

    # 5. CPF Responsável (apenas dígitos numéricos, LPAD 11)
    if "CPF_RESPONSAVEL" in df.columns:
        df["CPF_RESPONSAVEL"] = (
            df["CPF_RESPONSAVEL"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.strip()
        )
        df["CPF_RESPONSAVEL"] = df["CPF_RESPONSAVEL"].apply(
            lambda x: x.zfill(11) if x and len(x) <= 11 and x != "None" else x
        )
        df["CPF_RESPONSAVEL"] = df["CPF_RESPONSAVEL"].replace(["", "None", "nan"], None)

    # Extração de ANO e MES a partir de DATA_INCLUSAO (TIMESTAMP) se aplicável
    if "DATA_INCLUSAO" in df.columns:
        dt = pd.to_datetime(df["DATA_INCLUSAO"], errors="coerce")
        if "ANO" not in df.columns or df["ANO"].isnull().all():
            df["ANO"] = dt.dt.year.fillna(2026).astype(int)
        if "MES" not in df.columns or df["MES"].isnull().all():
            df["MES"] = dt.dt.month.fillna(11).astype(int)

    # 6. Tipagem Numérica (ANO, MES, VALOR)
    if "ANO" in df.columns:
        df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce").fillna(0).astype(int)
    if "MES" in df.columns:
        df["MES"] = pd.to_numeric(df["MES"], errors="coerce").fillna(0).astype(int)
    if "VALOR" in df.columns:
        df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce").fillna(0.0).round(2)

    # 7. Remoção de duplicatas
    subset_dup = [c for c in ["MATRICULA", "ANO", "MES"] if c in df.columns]
    if subset_dup:
        df = df.drop_duplicates(subset=subset_dup)
    else:
        df = df.drop_duplicates()

    # 8. Seleção final das colunas da especificação
    colunas_especificadas = [
        "MATRICULA",
        "NOME_ESTUDANTE",
        "CODSEC",
        "MUNICIPIO",
        "ANO",
        "MES",
        "VALOR",
        "STATUS_BOLSA_PRESENCA",
        "CPF_RESPONSAVEL",
    ]
    colunas_presentes = [c for c in colunas_especificadas if c in df.columns]
    return df[colunas_presentes]


def transformar_bronze_para_prata_bolsa_presenca(
    spark=None,
    data_execucao: datetime | None = None,
) -> str:
    """Executa a transformação bronze → prata para o Bolsa Presença."""
    if data_execucao is None:
        data_execucao = datetime.now()

    logger.info(f"🔄 Iniciando transformação bronze→prata: {NOME_PROGRAMA}")

    if not verificar_dados_disponiveis("bronze", NOME_PROGRAMA):
        raise FileNotFoundError(
            f"Nenhum dado encontrado na camada bronze para '{NOME_PROGRAMA}'. Execute a extração primeiro."
        )

    caminho_bronze = Path(obter_caminho_programa("bronze", NOME_PROGRAMA))
    caminho_prata = Path(obter_caminho_programa("prata", NOME_PROGRAMA))
    caminho_prata.mkdir(parents=True, exist_ok=True)

    logger.info(f"📥 Lendo arquivos bronze de: {caminho_bronze}")

    # Processamento com Pandas/PyArrow (robusto e sem dependência de Hadoop local)
    df_bruto = pd.read_parquet(caminho_bronze)
    total_bruto = len(df_bruto)
    logger.info(f"Total de registros lidos da bronze: {total_bruto}")

    # Aplicação das regras de negócio
    df_prata = padronizar_bolsa_presenca_pandas(df_bruto)
    total_prata = len(df_prata)
    logger.info(f"📤 Registros após padronização e desduplicação: {total_prata}")

    # Metadados de controle
    df_prata["_DT_PROCESSAMENTO_PRATA"] = data_execucao.isoformat()
    df_prata["_PROGRAMA"] = NOME_PROGRAMA

    # Persistência na camada prata particionado
    arquivo_saida = caminho_prata / f"estudante_bolsa_presenca_{data_execucao.strftime('%Y%m%d_%H%M%S')}.parquet"
    df_prata.to_parquet(arquivo_saida, engine="pyarrow", compression="snappy", index=False)

    logger.info(f"✅ Camada Prata gerada com sucesso: {arquivo_saida}")
    return str(arquivo_saida)


if __name__ == "__main__":
    configurar_logging()
    try:
        caminho = transformar_bronze_para_prata_bolsa_presenca()
        logger.info(f"Transformação finalizada. Dados em: {caminho}")
    except Exception as e:
        logger.error(f"Falha na transformação: {e}")
        raise
