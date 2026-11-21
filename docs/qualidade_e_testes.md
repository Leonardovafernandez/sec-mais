# Qualidade de Dados e Suíte de Testes Automatizados

> **Secretaria da Educação do Estado da Bahia (SEC-BA)**  
> **Trabalho de Conclusão de Curso (TCC) — Engenharia de Dados**  
> Documento de Validação, Asserções de Qualidade e Testes Unitários

---

## 1. Princípios de Data Quality no Projeto SEC MAIS

A integração de bases heterogêneas da administração pública estadual enfrenta desafios críticos de consistência:
* Matrículas com caracteres alfanuméricos residuais, pontos ou traços de dígitos verificadores.
* CPFs sem preenchimento de zeros à esquerda (*leading zeros*) ou contendo caracteres não numéricos.
* Nomes próprios grafados com variações de caixa (maiúsculas/minúsculas) e múltiplos espaços em branco.
* Presença de dados nulos espúrios representados como strings (`"nan"`, `"None"`, `"null"`, `""`).

Para assegurar a confiabilidade da Camada Prata e a integridade da Camada Ouro, foi implementada uma suíte abrangente de **testes automatizados com `pytest`** no arquivo [`sec-mais/tests/test_transformacao_prata.py`](file:///c:/Users/leonardo.fernandez/Desktop/FERNANDEZ/SEC%20MAIS/sec-mais/tests/test_transformacao_prata.py).

---

## 2. Estrutura da Suíte de Testes Automatizados

A suíte organiza-se em 3 classes de testes principais, cobrindo 8 casos de teste essenciais:

```
tests/test_transformacao_prata.py
├── TestHigienizacaoTransformacao (Testes Unitários de Expressões Regulares e Tipos)
│   ├── test_limpeza_matricula_remove_caracteres_nao_numericos
│   ├── test_limpeza_matricula_trata_vazios_e_nulos
│   ├── test_limpeza_cpf_formata_lpad_11
│   ├── test_limpeza_cpf_rejeita_comprimento_invalido_ou_nulo
│   └── test_limpeza_nome_converte_para_upper_e_remove_espacos_duplos
├── TestIntegridadeChavesPrata (Testes de Deduplicação e Unicidade)
│   ├── test_unicidade_chave_bolsa_presenca
│   └── test_unicidade_chave_pe_de_meia
└── TestRelacionamentosEntreFontes (Testes de Cruzamento Relacional e Integridade)
    └── test_cruzamento_e_contagem_beneficios
```

---

## 3. Detalhamento dos 8 Testes Unitários

### 3.1 Testes de Higienização de Campos

#### Teste 1: `test_limpeza_matricula_remove_caracteres_nao_numericos`
* **Entrada de Teste:** `[" 2023.01.987 ", "847291-X", "99812", "0012345"]`
* **Resultado Esperado:** `["202301987", "847291", "99812", "0012345"]`
* **Objetivo:** Garantir que pontos, traços, letras e espaços sejam removidos, preservando o valor numérico puro da matrícula.

#### Teste 2: `test_limpeza_matricula_trata_vazios_e_nulos`
* **Entrada de Teste:** `["", "   ", None, "nan", "null"]`
* **Resultado Esperado:** `[None, None, None, None, None]`
* **Objetivo:** Assegurar que quaisquer variações de ausência de dados sejam estritamente convertidas para `None` nativo (SQL `NULL`), sem resíduos de espaços ou strings espúrias.

#### Teste 3: `test_limpeza_cpf_formata_lpad_11`
* **Entrada de Teste:** `["123.456.789-00", "9876543210", " 111.222.333-44 "]`
* **Resultado Esperado:** `["12345678900", "09876543210", "11122233344"]`
* **Objetivo:** Validar a remoção de máscaras e a complementação de zeros à esquerda (`zfill(11)`) para CPFs que perderam o zero inicial no banco de origem.

#### Teste 4: `test_limpeza_cpf_rejeita_comprimento_invalido_ou_nulo`
* **Entrada de Teste:** `["12345678901234", "", None, "nan", "NULL"]`
* **Resultado Esperado:** `[None, None, None, None, None]`
* **Objetivo:** Garantir que CPFs com mais de 11 dígitos (erros de digitação) ou nulos sejam sumariamente invalidados.

#### Teste 5: `test_limpeza_nome_converte_para_upper_e_remove_espacos_duplos`
* **Entrada de Teste:** `["   joão  da   silva  ", "maria  oliveira", "ana   clara  "]`
* **Resultado Esperado:** `["JOÃO DA SILVA", "MARIA OLIVEIRA", "ANA CLARA"]`
* **Objetivo:** Uniformizar a grafia dos nomes para viabilizar agrupamentos textuais consistentes.

---

### 3.2 Testes de Deduplicação e Chaves de Negócio

#### Teste 6: `test_unicidade_chave_bolsa_presenca`
* **Cenário:** Simulação de lote contendo matrículas duplicadas na mesma competência `(ANO, MES)`.
* **Validação:** Aplicação de `drop_duplicates(subset=["MATRICULA", "ANO", "MES"])` garantindo a redução exata da cardinalidade para registros únicos por competência.

#### Teste 7: `test_unicidade_chave_pe_de_meia`
* **Cenário:** Simulação de movimentações múltiplas do mesmo estudante no mesmo ano letivo.
* **Validação:** Aplicação de `drop_duplicates(subset=["MATRICULA", "ANO"])` assegurando um único registro discente por exercício anual.

---

### 3.3 Testes de Cruzamento Relacional e Contagem

#### Teste 8: `test_cruzamento_e_contagem_beneficios`
* **Cenário:** Cruzamento relacional de três amostras simuladas (Bolsa Presença, Pé-de-Meia e UPT) contendo estudantes exclusivos de um único programa e estudantes que acumulam benefícios.
* **Validação:** Execução de *Full Outer Join* por matrícula e validação da métrica calculada `TOTAL_PROGRAMAS_RECEBIDOS`, verificando se estudantes com sobreposição recebem a contagem exata (ex: valor 2 ou 3).

---

## 4. Resolução de Caso de Borda Crítico (Lição Aprendida)

Durante o desenvolvimento da Sprint 3, identificou-se um comportamento sutil na biblioteca **Pandas**:
* Quando uma `pd.Series` de strings contendo apenas valores nulos/vazios recebia `.replace({"": None})`, o Pandas inferia automaticamente o tipo de retorno como `float64`, convertendo o `None` em `np.nan`.
* Como em Python `np.nan is None` é avaliado como `False`, a asserção `assert all(v is None for v in resultado)` falhava.
* **Ajuste Técnico Definitivo:** A função `limpar_matricula` foi reescrita utilizando verificação booleana estrita:
  ```python
  def limpar_matricula(s):
      val = pd.Series(s).astype(str).str.replace(r"\D", "", regex=True).str.strip()
      return val.apply(lambda x: str(x) if pd.notna(x) and str(x).isdigit() and len(str(x)) > 0 and x not in ["nan", "None", "null"] else None)
  ```
* Essa implementação garantiu que 100% dos valores nulos retornem o tipo `NoneType`, estabilizando os testes unitários.

---

## 5. Como Executar os Testes

Para executar a suíte completa com saída detalhada:

```powershell
cd "C:\Users\leonardo.fernandez\Desktop\FERNANDEZ\SEC MAIS\sec-mais"
pytest tests/test_transformacao_prata.py -v
```

### Saída Esperada:
```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\leonardo.fernandez\Desktop\FERNANDEZ\SEC MAIS\sec-mais
collected 8 items

tests/test_transformacao_prata.py::TestHigienizacaoTransformacao::test_limpeza_matricula_remove_caracteres_nao_numericos PASSED [ 12%]
tests/test_transformacao_prata.py::TestHigienizacaoTransformacao::test_limpeza_matricula_trata_vazios_e_nulos PASSED [ 25%]
tests/test_transformacao_prata.py::TestHigienizacaoTransformacao::test_limpeza_cpf_formata_lpad_11 PASSED [ 37%]
tests/test_transformacao_prata.py::TestHigienizacaoTransformacao::test_limpeza_cpf_rejeita_comprimento_invalido_ou_nulo PASSED [ 50%]
tests/test_transformacao_prata.py::TestHigienizacaoTransformacao::test_limpeza_nome_converte_para_upper_e_remove_espacos_duplos PASSED [ 62%]
tests/test_transformacao_prata.py::TestIntegridadeChavesPrata::test_unicidade_chave_bolsa_presenca PASSED [ 75%]
tests/test_transformacao_prata.py::TestIntegridadeChavesPrata::test_unicidade_chave_pe_de_meia PASSED [ 87%]
tests/test_transformacao_prata.py::TestRelacionamentosEntreFontes::test_cruzamento_e_contagem_beneficios PASSED [100%]

============================== 8 passed in 0.55s ==============================
```
