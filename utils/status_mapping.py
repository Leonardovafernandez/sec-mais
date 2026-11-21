"""
Mapeamento e padronização dos status de benefícios estudantis para o projeto SEC MAIS.

Define as regras de conversão dos status de origem para os 3 status canônicos:
- ATIVO: Estudante ativo no programa e recebendo (Bolsa Presença, Pé-de-Meia) ou usufruindo (UPT) do benefício.
- INSCRITO: Estudante elegível/válido, mas por algum motivo não está recebendo ou usufruindo efetivamente no período.
- INATIVO: Estudante que deixou de cumprir critérios ou encerrou sua participação.
"""

# 1. Bolsa Presença (SIADIANTE / Oracle)
MAPA_STATUS_BOLSA_PRESENCA = {
    # ATIVO
    "APTO_FASE1": "ATIVO",
    "APTO_FASE2": "ATIVO",
    "APTO_NOVO": "ATIVO",
    "AL_SEM_ATIV": "ATIVO",
    "AL_SEM_FREQ": "ATIVO",
    "RES_SEM_FREQ": "ATIVO",
    # INSCRITO
    "AL_BLOQUEADO": "INSCRITO",
    "BLQ_SEM_ATIV": "INSCRITO",
    "BLQ_SEM_FREQ": "INSCRITO",
    "BLQ_RES_SEM_FREQ": "INSCRITO",
    # INATIVO
    "FAIXA_NAO_ENQUADRA": "INATIVO",
    "CPF_ALUNO_NAO_CONFERE": "INATIVO",
    "SEM_MATRICULA": "INATIVO",
    "CAD_DESATUALIZADO": "INATIVO",
    "CADASTRO_ANALISE": "INATIVO",
    "RESPONSAVEL_SEM_CPF": "INATIVO",
    "ESCOLA_NAO_ENQUADRA": "INATIVO",
    "CAD_SEM_RESPONSAVEL": "INATIVO",
}

# 2. Pé-de-Meia (SIGEDUC / PostgreSQL)
MAPA_STATUS_PE_DE_MEIA = {
    # ATIVO
    "EM ANDAMENTO": "ATIVO",
    "TRANSFERÊNCIA ENTRE MODALIDADES (EM <> EJA)": "ATIVO",
    "TRANSFERENCIA ENTRE MODALIDADES (EM <> EJA)": "ATIVO",
    "TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR DENTRO DA MESMA REDE": "ATIVO",
    "TRANSFERENCIA PARA OUTRA UNIDADE ESCOLAR DENTRO DA MESMA REDE": "ATIVO",
    # INSCRITO
    "TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PÚBLICA": "INSCRITO",
    "TRANSFERENCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PUBLICA": "INSCRITO",
    "TRANSFERÊNCIA PARA OUTRA REDE NÃO IDENTIFICADA": "INSCRITO",
    "TRANSFERENCIA PARA OUTRA REDE NAO IDENTIFICADA": "INSCRITO",
    # INATIVO
    "TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PRIVADA": "INATIVO",
    "TRANSFERENCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PRIVADA": "INATIVO",
    "ABANDONO": "INATIVO",
    "INFORMAÇÃO INCORRETA": "INATIVO",
    "INFORMACAO INCORRETA": "INATIVO",
    "ÓBITO INFORMADO": "INATIVO",
    "OBITO INFORMADO": "INATIVO",
}

# 3. Universidade Para Todos - UPT (UPT / PostgreSQL)
MAPA_STATUS_UPT = {
    # ATIVO
    "CONTEMPLADO": "ATIVO",
    # INSCRITO
    "RESERVA": "INSCRITO",
    "INSCRITO": "INSCRITO",
    # INATIVO
    "CANCELADO": "INATIVO",
    "DESCLASSIFICADO": "INATIVO",
    "ENCERRADO": "INATIVO",
}


def mapear_status(programa: str, status_origem: str) -> str:
    """Retorna ATIVO, INSCRITO ou INATIVO a partir do status original do programa."""
    if not status_origem or str(status_origem).strip() in ["", "None", "nan", "NULL"]:
        return "INATIVO"
    
    st_limpo = str(status_origem).strip().upper()
    prog_key = str(programa).strip().lower()
    
    if "bolsa" in prog_key or "bp" in prog_key:
        return MAPA_STATUS_BOLSA_PRESENCA.get(st_limpo, "INATIVO")
    elif "meia" in prog_key or "pdm" in prog_key:
        return MAPA_STATUS_PE_DE_MEIA.get(st_limpo, "INATIVO")
    elif "universidade" in prog_key or "upt" in prog_key:
        return MAPA_STATUS_UPT.get(st_limpo, "INATIVO")
    
    return "INATIVO"
