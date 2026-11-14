"""
Módulo de Testes Automatizados — Sprint 2
Validação de Transformações, Higienizações e Integridade Relacional

Atividade 8 — Implementar testes das transformações e dos relacionamentos entre as fontes.
"""

import pytest
import pandas as pd
import numpy as np


# ==============================================================================
# FUNÇÕES DE HIGIENIZAÇÃO SOB TESTE
# ==============================================================================
def limpar_matricula(s):
    val = pd.Series(s).astype(str).str.replace(r"\D", "", regex=True).str.strip()
    return val.replace({"": None, "nan": None, "None": None, "null": None})


def limpar_cpf(s):
    val = pd.Series(s).astype(str).str.replace(r"\D", "", regex=True).str.strip()
    val = val.replace({"": None, "nan": None, "None": None, "null": None})
    return val.apply(lambda x: str(x).zfill(11) if pd.notna(x) and str(x).isdigit() and len(str(x)) <= 11 else None)


def limpar_nome(s):
    val = pd.Series(s).astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True)
    return val.replace({"": None, "NAN": None, "NONE": None, "NULL": None})


# ==============================================================================
# 1. TESTES UNITÁRIOS DE HIGIENIZAÇÃO DE CAMPOS
# ==============================================================================
class TestHigienizacaoTransformacao:
    """Testes unitários das regras de higienização da Camada Prata."""

    def test_limpeza_matricula_remove_caracteres_nao_numericos(self):
        dados = [" 2023.01.987 ", "847291-X", "99812", "0012345"]
        resultado = limpar_matricula(dados).tolist()
        esperado = ["202301987", "847291", "99812", "0012345"]
        assert resultado == esperado

    def test_limpeza_matricula_trata_vazios_e_nulos(self):
        dados = ["", "   ", None, "nan", "null"]
        resultado = limpar_matricula(dados).tolist()
        assert all(v is None for v in resultado)

    def test_limpeza_cpf_formata_lpad_11(self):
        dados = ["123.456.789-00", "9876543210", " 111.222.333-44 "]
        resultado = limpar_cpf(dados).tolist()
        esperado = ["12345678900", "09876543210", "11122233344"]
        assert resultado == esperado

    def test_limpeza_cpf_rejeita_comprimento_invalido_ou_nulo(self):
        dados = ["12345678901234", "", None, "nan", "NULL"]
        resultado = limpar_cpf(dados).tolist()
        assert all(v is None for v in resultado)

    def test_limpeza_nome_converte_para_upper_e_remove_espacos_duplos(self):
        dados = ["   joão  da   silva  ", "maria  oliveira", "ana   clara  "]
        resultado = limpar_nome(dados).tolist()
        esperado = ["JOÃO DA SILVA", "MARIA OLIVEIRA", "ANA CLARA"]
        assert resultado == esperado


# ==============================================================================
# 2. TESTES DE INTEGRIDADE E UNICIDADE DE CHAVES
# ==============================================================================
class TestIntegridadeChavesPrata:
    """Validação de integridade de chaves e deduplicação."""

    def test_unicidade_chave_bolsa_presenca(self):
        df_amostra = pd.DataFrame({
            "MATRICULA": ["1001", "1001", "1002"],
            "ANO": [2026, 2026, 2026],
            "MES": [11, 11, 11],
            "VALOR": [150.0, 150.0, 150.0]
        })
        df_dedup = df_amostra.drop_duplicates(subset=["MATRICULA", "ANO", "MES"])
        assert len(df_dedup) == 2
        assert len(df_dedup[df_dedup["MATRICULA"] == "1001"]) == 1

    def test_unicidade_chave_pe_de_meia(self):
        df_amostra = pd.DataFrame({
            "MATRICULA": ["2001", "2001", "2002"],
            "ANO": [2026, 2026, 2026],
            "STATUS_PE_DE_MEIA": ["ATIVO", "ATIVO", "ATIVO"]
        })
        df_dedup = df_amostra.drop_duplicates(subset=["MATRICULA", "ANO"])
        assert len(df_dedup) == 2


# ==============================================================================
# 3. TESTES DE RELACIONAMENTO E INTEGRACAO ENTRE FONTES (CAMADA OURO)
# ==============================================================================
class TestRelacionamentosEntreFontes:
    """Validação da integração analítica entre os 3 programas."""

    def test_cruzamento_e_contagem_beneficios(self):
        # Estudante 1: Recebe Bolsa Presença + Pé-de-Meia + UPT (3 programas)
        # Estudante 2: Recebe apenas Pé-de-Meia (1 programa)
        # Estudante 3: Recebe apenas UPT (1 programa)
        df_bp = pd.DataFrame({"MATRICULA": ["EST_1"], "BENEFICIO_BOLSA_PRESENCA": [True]})
        df_pdm = pd.DataFrame({"MATRICULA": ["EST_1", "EST_2"], "BENEFICIO_PE_DE_MEIA": [True, True]})
        df_upt = pd.DataFrame({"MATRICULA": ["EST_1", "EST_3"], "BENEFICIO_UPT": [True, True]})

        # Full Outer Join
        base = df_pdm.merge(df_upt, on="MATRICULA", how="outer")
        base = base.merge(df_bp, on="MATRICULA", how="outer")

        base["BENEFICIO_PE_DE_MEIA"] = base["BENEFICIO_PE_DE_MEIA"].fillna(False)
        base["BENEFICIO_UPT"] = base["BENEFICIO_UPT"].fillna(False)
        base["BENEFICIO_BOLSA_PRESENCA"] = base["BENEFICIO_BOLSA_PRESENCA"].fillna(False)

        base["TOTAL_PROGRAMAS"] = (
            base["BENEFICIO_PE_DE_MEIA"].astype(int) +
            base["BENEFICIO_UPT"].astype(int) +
            base["BENEFICIO_BOLSA_PRESENCA"].astype(int)
        )

        est_1 = base[base["MATRICULA"] == "EST_1"].iloc[0]
        assert est_1["TOTAL_PROGRAMAS"] == 3
        assert est_1["BENEFICIO_PE_DE_MEIA"] is True
        assert est_1["BENEFICIO_BOLSA_PRESENCA"] is True
        assert est_1["BENEFICIO_UPT"] is True

        est_2 = base[base["MATRICULA"] == "EST_2"].iloc[0]
        assert est_2["TOTAL_PROGRAMAS"] == 1
        assert est_2["BENEFICIO_PE_DE_MEIA"] is True
        assert est_2["BENEFICIO_BOLSA_PRESENCA"] is False

        assert len(base) == 3

