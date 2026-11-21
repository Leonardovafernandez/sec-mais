"""
Módulo de Modelagem Dimensional da Camada Ouro (Star Schema Kimball)
Sprint 3: Construção das estruturas analíticas e disponibilização.

Transforma os dados da Camada Prata na modelagem dimensional:
- Fato: fato_beneficio_estudante (Grão: Estudante x Programa x Período)
- Dimensões: dim_estudante, dim_programa, dim_tempo, dim_municipio

Persistência dupla:
1. Arquivos locais Apache Parquet em armazenamento/ouro/
2. Tabelas relacionais no PostgreSQL Docker (schema ouro)
3. Visões analíticas no PostgreSQL Docker (schema marts)
"""

import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from loguru import logger

# Raiz do projeto
PROJETO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJETO_ROOT))

from config.settings import configuracoes, configuracoes_postgres_dw
from config.logging_config import configurar_logging
from utils.status_mapping import mapear_status

DIR_STORAGE = configuracoes.caminho_armazenamento
DIR_PRATA = configuracoes.caminho_prata
DIR_OURO = configuracoes.caminho_ouro


def gerar_hash_id(valor: str, prefixo: str = "EST") -> str:
    """Gera um identificador surrogate pseudo-anônimo e determinístico."""
    if not valor or pd.isna(valor) or str(valor).strip() in ["", "None", "nan"]:
        return None
    hash_obj = hashlib.sha256(str(valor).strip().encode("utf-8"))
    return f"{prefixo}_{hash_obj.hexdigest()[:12].upper()}"


def mascarar_cpf(cpf: str) -> str:
    """Aplica máscara LGPD no CPF (ex: ***.456.789-**)."""
    if not cpf or pd.isna(cpf) or len(str(cpf)) != 11:
        return None
    c = str(cpf)
    return f"***.{c[3:6]}.{c[6:9]}-**"


def carregar_dados_prata():
    """Lê os arquivos Parquet mais recentes da Camada Prata."""
    logger.info("📥 Lendo dados higienizados da Camada Prata...")
    
    # 1. Bolsa Presença
    arqs_bp = list((DIR_PRATA / "bolsa_presenca").glob("**/*.parquet"))
    df_bp = pd.read_parquet(sorted(arqs_bp, key=lambda f: f.stat().st_mtime, reverse=True)[0]) if arqs_bp else pd.DataFrame()
    
    # 2. Pé-de-Meia
    arqs_pdm = list((DIR_PRATA / "pe_de_meia").glob("**/*.parquet"))
    df_pdm = pd.read_parquet(sorted(arqs_pdm, key=lambda f: f.stat().st_mtime, reverse=True)[0]) if arqs_pdm else pd.DataFrame()
    
    # 3. UPT
    arqs_upt = list((DIR_PRATA / "universidade_para_todos").glob("**/*.parquet"))
    df_upt = pd.read_parquet(sorted(arqs_upt, key=lambda f: f.stat().st_mtime, reverse=True)[0]) if arqs_upt else pd.DataFrame()

    logger.info(f"Registros lidos da Prata: BP={len(df_bp):,}, PDM={len(df_pdm):,}, UPT={len(df_upt):,}")
    return df_bp, df_pdm, df_upt


def construir_dimensao_programa() -> pd.DataFrame:
    """Constrói a dimensão dim_programa com regras de negócio e limites de interpretação."""
    dados_programas = [
        {
            "id_programa": 1,
            "codigo_programa": "BOLSA_PRESENCA",
            "nome_programa": "Bolsa Presença",
            "orgao_gestor": "SEC-BA",
            "publico_alvo": "Famílias cadastradas no CadÚnico em condição de vulnerabilidade com filhos na rede estadual",
            "possui_valor_financeiro": True,
            "regras_interpretacao": "O campo valor_registrado reflete o valor previsto/concedido no sistema SIADIANTE; não representa quitação ou homologação bancária de saque.",
            "unidade_tempo": "MENSAL"
        },
        {
            "id_programa": 2,
            "codigo_programa": "PE_DE_MEIA",
            "nome_programa": "Pé-de-Meia",
            "orgao_gestor": "MEC / SEC-BA",
            "publico_alvo": "Estudantes do Ensino Médio público beneficiários do CadÚnico",
            "possui_valor_financeiro": False,
            "regras_interpretacao": "A fonte SIGEDUC registra a situação e elegibilidade escolar do aluno. Os valores e depósitos da poupança estudantil são operados pela CAIXA e não constam nesta fonte.",
            "unidade_tempo": "ANUAL"
        },
        {
            "id_programa": 3,
            "codigo_programa": "UNIVERSIDADE_PARA_TODOS",
            "nome_programa": "Universidade Para Todos (UPT)",
            "orgao_gestor": "SEC-BA",
            "publico_alvo": "Estudantes da 3ª série do Ensino Médio e egressos da rede pública estadual da Bahia",
            "possui_valor_financeiro": False,
            "regras_interpretacao": "Registra a inscrição, seleção e participação no curso preparatório pré-vestibular; não envolve transferência financeira direta aos candidatos.",
            "unidade_tempo": "ANUAL"
        }
    ]
    return pd.DataFrame(dados_programas)


def construir_dimensao_municipio(df_bp: pd.DataFrame) -> pd.DataFrame:
    """Constrói a dimensão dim_municipio a partir das fontes disponíveis."""
    municipios = []
    if not df_bp.empty and "MUNICIPIO" in df_bp.columns:
        muns_unicos = df_bp["MUNICIPIO"].dropna().unique()
        for i, m in enumerate(sorted(muns_unicos), start=1):
            municipios.append({
                "id_municipio": i,
                "nome_municipio": str(m).strip().upper(),
                "uf": "BA"
            })
            
    # Município padrão para dados sem informação
    municipios.append({
        "id_municipio": 0,
        "nome_municipio": "NÃO INFORMADO",
        "uf": "BA"
    })
    return pd.DataFrame(municipios).drop_duplicates(subset=["nome_municipio"])


def construir_dimensao_tempo(df_bp: pd.DataFrame, df_pdm: pd.DataFrame, df_upt: pd.DataFrame) -> pd.DataFrame:
    """Constrói a dimensão dim_tempo com granularidade mensal e anual."""
    meses_nomes = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    
    anos = set()
    for df in [df_bp, df_pdm, df_upt]:
        if not df.empty and "ANO" in df.columns:
            anos.update(df["ANO"].dropna().astype(int).unique())
    if not anos:
        anos = {2026}

    linhas_tempo = []
    for ano in sorted(anos):
        # Entrada genérica de nível anual (quando não há mês na fonte)
        linhas_tempo.append({
            "id_tempo": ano * 100,  # ex: 202600
            "ano": ano,
            "mes": None,
            "ano_mes": f"{ano}",
            "nome_mes": "Referência Anual",
            "semestre": None,
            "trimestre": None,
            "tipo_periodo": "ANUAL"
        })
        # Entradas mensais
        for mes in range(1, 13):
            linhas_tempo.append({
                "id_tempo": ano * 100 + mes,  # ex: 202611
                "ano": ano,
                "mes": mes,
                "ano_mes": f"{ano}-{mes:02d}",
                "nome_mes": meses_nomes[mes],
                "semestre": 1 if mes <= 6 else 2,
                "trimestre": (mes - 1) // 3 + 1,
                "tipo_periodo": "MENSAL"
            })
            
    return pd.DataFrame(linhas_tempo)


def construir_dimensao_estudante(df_bp: pd.DataFrame, df_pdm: pd.DataFrame, df_upt: pd.DataFrame) -> pd.DataFrame:
    """Constrói a dimensão dim_estudante unificada com chaves protegidas para LGPD."""
    estudantes_dict = {}

    def processar_origem(df, col_mat, col_nome, col_cpf, col_social=None):
        if df.empty:
            return
        for _, row in df.iterrows():
            mat = str(row.get(col_mat, "")).strip() if pd.notna(row.get(col_mat)) else ""
            cpf = str(row.get(col_cpf, "")).strip() if pd.notna(row.get(col_cpf)) else ""
            nome = str(row.get(col_nome, "")).strip().upper() if pd.notna(row.get(col_nome)) else "SEM NOME"
            social = str(row.get(col_social, "")).strip().upper() if col_social and pd.notna(row.get(col_social)) else None

            # Chave natural para identificação única (prioriza matrícula, fallback CPF)
            chave_natural = mat if mat and mat not in ["None", "nan", ""] else cpf
            if not chave_natural or chave_natural in ["None", "nan", ""]:
                continue

            id_est = gerar_hash_id(chave_natural, prefixo="EST")
            if id_est not in estudantes_dict:
                estudantes_dict[id_est] = {
                    "id_estudante": id_est,
                    "nome_estudante": nome,
                    "nome_social": social,
                    "matricula_conciliacao": mat if mat else None,
                    "cpf_mascarado": mascarar_cpf(cpf) if cpf else None,
                    "tem_matricula": bool(mat and mat not in ["None", "nan"]),
                    "tem_cpf": bool(cpf and cpf not in ["None", "nan"]),
                }
            else:
                # Enriquece dados cadastrais
                if not estudantes_dict[id_est]["nome_social"] and social:
                    estudantes_dict[id_est]["nome_social"] = social
                if not estudantes_dict[id_est]["matricula_conciliacao"] and mat:
                    estudantes_dict[id_est]["matricula_conciliacao"] = mat
                    estudantes_dict[id_est]["tem_matricula"] = True
                if not estudantes_dict[id_est]["cpf_mascarado"] and cpf:
                    estudantes_dict[id_est]["cpf_mascarado"] = mascarar_cpf(cpf)
                    estudantes_dict[id_est]["tem_cpf"] = True

    processar_origem(df_bp, "MATRICULA", "NOME_ESTUDANTE", "CPF_RESPONSAVEL")
    processar_origem(df_pdm, "MATRICULA", "NOME_ESTUDANTE", "CPF_ESTUDANTE")
    processar_origem(df_upt, "MATRICULA", "NOME_ESTUDANTE", "CPF_ESTUDANTE", "NOME_SOCIAL_ESTUDANTE")

    return pd.DataFrame(list(estudantes_dict.values()))


def construir_fato_beneficio_estudante(
    df_bp: pd.DataFrame,
    df_pdm: pd.DataFrame,
    df_upt: pd.DataFrame,
    df_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Constrói a tabela fato_beneficio_estudante no grão: Estudante x Programa x Período."""
    logger.info("🔨 Construindo fato_beneficio_estudante (Grão: Estudante x Programa x Período)...")
    
    # Mapa de municípios para lookup rápido de ID
    map_mun = dict(zip(df_municipio["nome_municipio"], df_municipio["id_municipio"])) if not df_municipio.empty else {}
    linhas_fato = []
    agora_iso = datetime.now().isoformat()

    # 1. Bolsa Presença (id_programa = 1)
    if not df_bp.empty:
        for _, row in df_bp.iterrows():
            mat = str(row.get("MATRICULA", "")).strip()
            if not mat or mat in ["None", "nan"]:
                continue
            id_est = gerar_hash_id(mat, "EST")
            ano = int(row.get("ANO", 2026)) if pd.notna(row.get("ANO")) else 2026
            mes = int(row.get("MES", 11)) if pd.notna(row.get("MES")) else 11
            mun = str(row.get("MUNICIPIO", "NÃO INFORMADO")).strip().upper()
            id_mun = map_mun.get(mun, 0)
            id_tempo = ano * 100 + mes
            status_orig = str(row.get("STATUS_BOLSA_PRESENCA", "CONCEDIDO")).strip().upper()
            valor = float(row.get("VALOR", 150.0)) if pd.notna(row.get("VALOR")) else 0.0

            linhas_fato.append({
                "id_fato": hashlib.md5(f"{id_est}_1_{ano}_{mes}".encode()).hexdigest(),
                "id_estudante": id_est,
                "id_programa": 1,
                "id_tempo": id_tempo,
                "id_municipio": id_mun,
                "programa": "Bolsa Presença",
                "ano": ano,
                "mes": mes,
                "status": mapear_status("bolsa_presenca", status_orig),
                "status_origem": status_orig,
                "valor_registrado": valor,
                "municipio": mun,
                "matricula": mat,
                "origem_dado": "SIADIANTE (Oracle)",
                "data_atualizacao": agora_iso
            })

    # 2. Pé-de-Meia (id_programa = 2)
    if not df_pdm.empty:
        for _, row in df_pdm.iterrows():
            mat = str(row.get("MATRICULA", "")).strip()
            cpf = str(row.get("CPF_ESTUDANTE", "")).strip()
            chave = mat if mat and mat not in ["None", "nan"] else cpf
            if not chave or chave in ["None", "nan"]:
                continue
            id_est = gerar_hash_id(chave, "EST")
            ano = int(row.get("ANO", 2026)) if pd.notna(row.get("ANO")) else 2026
            id_tempo = ano * 100  # Sem mês na fonte
            status_orig = str(row.get("STATUS_PE_DE_MEIA", "ATIVO")).strip().upper()

            linhas_fato.append({
                "id_fato": hashlib.md5(f"{id_est}_2_{ano}_0".encode()).hexdigest(),
                "id_estudante": id_est,
                "id_programa": 2,
                "id_tempo": id_tempo,
                "id_municipio": 0,
                "programa": "Pé-de-Meia",
                "ano": ano,
                "mes": None,  # Mês ausente nesta fonte
                "status": mapear_status("pe_de_meia", status_orig),
                "status_origem": status_orig,
                "valor_registrado": None,  # Fonte não possui valores financeiros
                "municipio": "NÃO INFORMADO",
                "matricula": mat if mat and mat not in ["None", "nan"] else None,
                "origem_dado": "SIGEDUC (PostgreSQL)",
                "data_atualizacao": agora_iso
            })

    # 3. Universidade Para Todos - UPT (id_programa = 3)
    if not df_upt.empty:
        for _, row in df_upt.iterrows():
            mat = str(row.get("MATRICULA", "")).strip()
            cpf = str(row.get("CPF_ESTUDANTE", "")).strip()
            chave = mat if mat and mat not in ["None", "nan"] else cpf
            if not chave or chave in ["None", "nan"]:
                continue
            id_est = gerar_hash_id(chave, "EST")
            ano = 2026
            id_tempo = ano * 100  # Sem mês na fonte
            status_orig = str(row.get("STATUS_UPT", "INSCRITO")).strip().upper()

            linhas_fato.append({
                "id_fato": hashlib.md5(f"{id_est}_3_{ano}_0".encode()).hexdigest(),
                "id_estudante": id_est,
                "id_programa": 3,
                "id_tempo": id_tempo,
                "id_municipio": 0,
                "programa": "Universidade Para Todos",
                "ano": ano,
                "mes": None,  # Mês ausente nesta fonte
                "status": mapear_status("upt", status_orig),
                "status_origem": status_orig,
                "valor_registrado": None,  # Fonte não possui valores financeiros
                "municipio": "NÃO INFORMADO",
                "matricula": mat if mat and mat not in ["None", "nan"] else None,
                "origem_dado": "UPT (PostgreSQL)",
                "data_atualizacao": agora_iso
            })

    df_fato = pd.DataFrame(linhas_fato)
    return df_fato.drop_duplicates(subset=["id_fato"])


def executar_modelagem_ouro():
    """Executa o pipeline completo de modelagem dimensional da Camada Ouro."""
    logger.info("=" * 70)
    logger.info("   INICIANDO MODELAGEM DIMENSIONAL OURO (STAR SCHEMA KIMBALL)")
    logger.info("=" * 70)

    # 1. Carrega dados higienizados da Prata
    df_bp, df_pdm, df_upt = carregar_dados_prata()

    # 2. Constrói Dimensões
    logger.info("Construindo dimensões analíticas...")
    dim_prog = construir_dimensao_programa()
    dim_mun = construir_dimensao_municipio(df_bp)
    dim_tempo = construir_dimensao_tempo(df_bp, df_pdm, df_upt)
    dim_est = construir_dimensao_estudante(df_bp, df_pdm, df_upt)

    # 3. Constrói Fato
    fato_benef = construir_fato_beneficio_estudante(df_bp, df_pdm, df_upt, dim_mun)

    # Atualiza em dim_estudante o total de programas associados
    prog_por_est = fato_benef.groupby("id_estudante")["id_programa"].nunique()
    dim_est["total_programas_acumulados"] = dim_est["id_estudante"].map(prog_por_est).fillna(1).astype(int)

    # 4. Persistência Física Local em Parquet (armazenamento/ouro/)
    logger.info("💾 Gravando arquivos Parquet na Camada Ouro...")
    DIR_OURO.mkdir(parents=True, exist_ok=True)
    
    tabelas_ouro = {
        "fato_beneficio_estudante": fato_benef,
        "dim_estudante": dim_est,
        "dim_programa": dim_prog,
        "dim_tempo": dim_tempo,
        "dim_municipio": dim_mun,
    }

    for nome_tab, df_tab in tabelas_ouro.items():
        caminho_arq = DIR_OURO / f"{nome_tab}.parquet"
        df_tab.to_parquet(caminho_arq, engine="pyarrow", compression="snappy", index=False)
        logger.info(f"   - {caminho_arq.name}: {len(df_tab):,} registros | {round(caminho_arq.stat().st_size / 1024, 1)} KB")

    # 5. Persistência no Banco PostgreSQL Docker (Schema ouro)
    logger.info("🔌 Persistindo Star Schema no PostgreSQL DW (Docker)...")
    try:
        conn_str = (
            f"postgresql+psycopg2://{configuracoes_postgres_dw.user}:{configuracoes_postgres_dw.password}"
            f"@{configuracoes_postgres_dw.host}:{configuracoes_postgres_dw.port}/{configuracoes_postgres_dw.database}"
        )
        engine = create_engine(conn_str)
        
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ouro;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts;"))

            for nome_tab, df_tab in tabelas_ouro.items():
                logger.info(f"   Inserindo {nome_tab} no PostgreSQL (schema ouro)...")
                df_tab.to_sql(
                    name=nome_tab,
                    con=conn,
                    schema="ouro",
                    if_exists="replace",
                    index=False,
                    chunksize=5000,
                )

            # Índices de performance
            logger.info("   Criando índices otimizados...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fato_estudante ON ouro.fato_beneficio_estudante (id_estudante);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fato_programa ON ouro.fato_beneficio_estudante (id_programa);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fato_tempo ON ouro.fato_beneficio_estudante (id_tempo);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fato_municipio ON ouro.fato_beneficio_estudante (id_municipio);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_dim_est_id ON ouro.dim_estudante (id_estudante);"))

        logger.info("✅ Tabelas da Camada Ouro persistidas no PostgreSQL com sucesso!")

        # 6. Aplica as Views da Camada Marts
        aplicar_views_marts(engine)

    except Exception as e:
        logger.warning(f"⚠️ Não foi possível persistir no PostgreSQL local (verifique Docker): {e}")

    logger.info("🏁 Modelagem Dimensional Ouro concluída com êxito!")
    return tabelas_ouro


def aplicar_views_marts(engine):
    """Executa o script SQL para recriar as visões analíticas da camada marts."""
    script_views = PROJETO_ROOT / "docker" / "views_marts.sql"
    if script_views.exists():
        logger.info(f"📜 Aplicando visões analíticas em {script_views.name}...")
        conteudo_sql = script_views.read_text(encoding="utf-8")
        with engine.begin() as conn:
            conn.execute(text(conteudo_sql))
        logger.info("✅ Visões analíticas da camada marts aplicadas com sucesso!")


if __name__ == "__main__":
    configurar_logging()
    executar_modelagem_ouro()
