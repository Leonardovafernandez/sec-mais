"""
Transformação Bronze → Prata para o programa Pé-de-Meia (SIGEDUC).

Lê os dados brutos da camada bronze, aplica padronizações, higienização
de matrícula e CPF, regras de negócio e persiste o DataFrame
ESTUDANTES_PE_DE_MEIA na camada prata.

Estrutura final na Prata:
- MATRICULA
- NOME_ESTUDANTE
- CPF_ESTUDANTE
- ANO
- STATUS_PE_DE_MEIA
"""

from datetime import datetime
from pathlib import Path

from loguru import logger
import pandas as pd

from config.logging_config import configurar_logging
from utils.storage import obter_caminho_programa, verificar_dados_disponiveis

NOME_PROGRAMA = "pe_de_meia"


def padronizar_pe_de_meia_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica regras de negócio e higienização via Pandas."""
    col_map = {c: c.strip().upper() for c in df.columns}
    df = df.rename(columns=col_map)

    # Mapeamento de possíveis variações de nomes de colunas
    if "CO_MATRICULA_REDE" in df.columns and "MATRICULA" not in df.columns:
        df["MATRICULA"] = df["CO_MATRICULA_REDE"]
    if "ESTUDANTE_NOME" in df.columns and "NOME_ESTUDANTE" not in df.columns:
        df["NOME_ESTUDANTE"] = df["ESTUDANTE_NOME"]
    if "ESTUDANTE_CPF" in df.columns and "CPF_ESTUDANTE" not in df.columns:
        df["CPF_ESTUDANTE"] = df["ESTUDANTE_CPF"]
    if "NU_ANO_MATRICULA" in df.columns and "ANO" not in df.columns:
        df["ANO"] = df["NU_ANO_MATRICULA"]
    if "ESTUDANTE_MATRICULA_SITUACAO_DESCRICAO" in df.columns and "STATUS_PE_DE_MEIA" not in df.columns:
        df["STATUS_PE_DE_MEIA"] = df["ESTUDANTE_MATRICULA_SITUACAO_DESCRICAO"]

    # 1. Higienização da Matrícula (apenas dígitos numéricos)
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

    # 3. CPF do Estudante (apenas dígitos numéricos, LPAD 11)
    if "CPF_ESTUDANTE" in df.columns:
        df["CPF_ESTUDANTE"] = (
            df["CPF_ESTUDANTE"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.strip()
        )
        df["CPF_ESTUDANTE"] = df["CPF_ESTUDANTE"].apply(
            lambda x: x.zfill(11) if x and len(x) <= 11 and x != "None" else x
        )
        df["CPF_ESTUDANTE"] = df["CPF_ESTUDANTE"].replace(["", "None", "nan"], None)

    # 4. Ano (int)
    if "ANO" in df.columns:
        df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce").fillna(0).astype(int)

    # 5. Status Pé-de-Meia (caixa alta)
    if "STATUS_PE_DE_MEIA" in df.columns:
        df["STATUS_PE_DE_MEIA"] = (
            df["STATUS_PE_DE_MEIA"].astype(str).str.strip().str.upper()
        )

    # 6. Remoção de duplicatas
    subset_dup = [c for c in ["MATRICULA", "ANO"] if c in df.columns]
    if subset_dup:
        df = df.drop_duplicates(subset=subset_dup)
    else:
        df = df.drop_duplicates()

    # 7. Seleção final das colunas
    colunas_especificadas = [
        "MATRICULA",
        "NOME_ESTUDANTE",
        "CPF_ESTUDANTE",
        "ANO",
        "STATUS_PE_DE_MEIA",
    ]
    colunas_presentes = [c for c in colunas_especificadas if c in df.columns]
    return df[colunas_presentes]


def transformar_bronze_para_prata_pe_de_meia(
    spark=None,
    data_execucao: datetime | None = None,
) -> str:
    """Executa a transformação bronze → prata para o Pé-de-Meia."""
    if data_execucao is None:
        data_execucao = datetime.now()

    logger.info(f"🔄 Iniciando transformação bronze→prata: {NOME_PROGRAMA}")

    if not verificar_dados_disponiveis("bronze", NOME_PROGRAMA):
        raise FileNotFoundError(
            f"Nenhum dado na camada bronze para '{NOME_PROGRAMA}'. Execute a extração primeiro."
        )

    caminho_bronze = Path(obter_caminho_programa("bronze", NOME_PROGRAMA))
    caminho_prata = Path(obter_caminho_programa("prata", NOME_PROGRAMA))
    caminho_prata.mkdir(parents=True, exist_ok=True)

    logger.info(f"📥 Lendo arquivos bronze de: {caminho_bronze}")

    df_bruto = pd.read_parquet(caminho_bronze)
    total_bruto = len(df_bruto)
    logger.info(f"Total de registros lidos da bronze: {total_bruto}")

    df_prata = padronizar_pe_de_meia_pandas(df_bruto)
    total_prata = len(df_prata)
    logger.info(f"📤 Registros após padronização e desduplicação: {total_prata}")

    df_prata["_DT_PROCESSAMENTO_PRATA"] = data_execucao.isoformat()
    df_prata["_PROGRAMA"] = NOME_PROGRAMA

    arquivo_saida = caminho_prata / f"estudantes_pe_de_meia_{data_execucao.strftime('%Y%m%d_%H%M%S')}.parquet"
    df_prata.to_parquet(arquivo_saida, engine="pyarrow", compression="snappy", index=False)

    logger.info(f"✅ Camada Prata gerada com sucesso: {arquivo_saida}")
    return str(arquivo_saida)


if __name__ == "__main__":
    configurar_logging()
    try:
        caminho = transformar_bronze_para_prata_pe_de_meia()
        logger.info(f"Transformação finalizada. Dados em: {caminho}")
    except Exception as e:
        logger.error(f"Falha na transformação: {e}")
        raise
