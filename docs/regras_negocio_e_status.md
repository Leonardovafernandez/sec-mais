# Regras de Negócio, Valoração Financeira e Mapeamento Canônico de Status

> **Secretaria da Educação do Estado da Bahia (SEC-BA)**  
> **Trabalho de Conclusão de Curso (TCC) — Engenharia de Dados**  
> Documento Normativo de Regras de Tratamento, Auditoria e Padronização Semântica

---

## 1. Visão das Políticas Públicas Selecionadas

O projeto SEC MAIS concentra-se nas três políticas públicas de maior impacto discente na rede pública estadual da Bahia:

### 1.1 Bolsa Presença
* **Objetivo:** Programa de transferência direta de renda condicionado à frequência escolar mensal mínima (geralmente 75% a 85%) de estudantes de famílias cadastradas no CadÚnico e em situação de vulnerabilidade socioeconômica.
* **Sistema de Origem:** `SIADIANTE` (banco de dados corporativo Oracle 19c da SEC-BA).
* **Tabela Transacional:** `beneficio_familia` (tabela incremental com cargas mensais de ~600.000 registros por competência).
* **Natureza dos Dados:** Apresenta dados cadastrais, matrícula escolar, município da escola, status de aptidão do mês e o campo nominal `VALOR`.

### 1.2 Pé-de-Meia
* **Objetivo:** Programa do Governo Federal (MEC) executado em cooperação com a SEC-BA, funcionando como poupança e incentivo financeiro para permanência e conclusão do Ensino Médio regular e EJA.
* **Sistema de Origem:** `sigeduc` (banco de dados PostgreSQL corporativo da SEC-BA).
* **Tabela Transacional:** `aluno_pdm` (dados de estudantes elegíveis, matrículas e movimentações escolares).
* **Natureza dos Dados:** Dados cadastrais, situação de matrícula e motivos de movimentação/transferência escolar.

### 1.3 Universidade Para Todos (UPT)
* **Objetivo:** Projeto estadual preparatório para vestibulares e ENEM, oferecendo aulas de reforço e material didático a estudantes do 3º ano do Ensino Médio e egressos da rede pública estadual.
* **Sistema de Origem:** `upt` (banco de dados PostgreSQL dedicado na porta 5435 da SEC-BA).
* **Tabela Transacional:** `DADO_CANDIDATO`, `DADOS_PESSOAIS`, `INSCRICAO` e `VW_STATUS_INSCRICOES`.
* **Natureza dos Dados:** Inscrições no processo seletivo anual, polo/município, situação da vaga e classificação do candidato.

---

## 2. A Necessidade da Padronização Canônica de Status

Cada sistema transacional de origem adota terminologias próprias e códigos operacionais altamente específicos:
* No **Bolsa Presença**, há códigos de bloqueio por falta de frequência (`BLQ_SEM_FREQ`), alertas de inconsistência (`AL_SEM_ATIV`), pendências de CPF (`CPF_ALUNO_NAO_CONFERE`) e fases de aptidão (`APTO_FASE1`).
* No **Pé-de-Meia**, há situações de transferência entre redes, abandono escolar e continuidade de estudos (`EM ANDAMENTO`).
* No **UPT**, há situações do processo seletivo como `CONTEMPLADO`, `RESERVA`, `DESCLASSIFICADO` e `CANCELADO`.

Se essas strings fossem comparadas diretamente, seria impossível responder a perguntas gerenciais simples, tais como: *"Quantos estudantes estão efetivamente ativos recebendo pelo menos um benefício?"*.

### Solução de Engenharia: Três Status Canônicos
Foi estabelecido um mapeamento padronizado para **3 status canônicos universais**:
1. **`ATIVO`:** O estudante está com a matrícula regular e atendendo aos critérios de participação e concessão da política.
2. **`INSCRITO`:** O estudante manifestou interesse, está na lista de espera, em reserva ou com pendência temporária/bloqueio passível de regularização.
3. **`INATIVO`:** O estudante foi desligado, abandonou, transferiu-se para rede privada, foi desclassificado ou não atende aos requisitos normativos do programa.

> **Princípio de Auditoria:** O valor padronizado é gravado na coluna `status`, mas o valor original exato é preservado inalterado na coluna `status_origem` em todas as tabelas e arquivos da Camada Ouro.

---

## 3. Matriz De-Para Completa de Mapeamento de Status

A lógica centralizada no módulo [`sec-mais/utils/status_mapping.py`](file:///c:/Users/leonardo.fernandez/Desktop/FERNANDEZ/SEC%20MAIS/sec-mais/utils/status_mapping.py) implementa as seguintes equivalências:

### 3.1 Bolsa Presença (SIADIANTE)

| Status de Origem (`status_origem`) | Status Canônico (`status`) | Justificativa de Negócio |
|---|:---:|---|
| `APTO_FASE1` | **`ATIVO`** | Estudante apto e validado na 1ª fase de processamento da folha. |
| `APTO_FASE2` | **`ATIVO`** | Estudante apto na 2ª fase de processamento. |
| `APTO_NOVO` | **`ATIVO`** | Novo estudante ingressante aprovado nos critérios da política. |
| `AL_SEM_ATIV` | **`ATIVO`** | Alerta de falta de atividade, porém mantido na folha regular. |
| `AL_SEM_FREQ` | **`ATIVO`** | Alerta de frequência em observação, benefício ainda ativo. |
| `RES_SEM_FREQ` | **`ATIVO`** | Alerta residual com concessão ativa no mês de referência. |
| `AL_BLOQUEADO` | **`INSCRITO`** | Benefício temporariamente bloqueado para análise social. |
| `BLQ_SEM_ATIV` | **`INSCRITO`** | Bloqueado por ausência temporária de lançamento de notas/atividades. |
| `BLQ_SEM_FREQ` | **`INSCRITO`** | Bloqueado por infrequência escolar (passível de reversão). |
| `BLQ_RES_SEM_FREQ`| **`INSCRITO`** | Bloqueio residual em regularização. |
| `FAIXA_NAO_ENQUADRA`| **`INATIVO`** | Renda per capita familiar ultrapassou o teto do programa. |
| `CPF_ALUNO_NAO_CONFERE`| **`INATIVO`** | Inconsistência cadastral na Receita Federal que impede o pagamento. |
| `SEM_MATRICULA` | **`INATIVO`** | Estudante sem vínculo de matrícula ativo na rede estadual. |
| `CAD_DESATUALIZADO`| **`INATIVO`** | Cadastro Único desatualizado há mais de 24 meses. |
| `CADASTRO_ANALISE`| **`INATIVO`** | Cadastro reprovado ou retido nos cruzamentos socioeconômicos. |
| `RESPONSAVEL_SEM_CPF`| **`INATIVO`** | Impossibilidade legal de emissão de cartão bancário de pagamento. |
| `ESCOLA_NAO_ENQUADRA`| **`INATIVO`** | Unidade escolar fora da cobertura do programa estadual. |
| `CAD_SEM_RESPONSAVEL`| **`INATIVO`** | Ausência de responsável legal identificado no CadÚnico. |

---

### 3.2 Pé-de-Meia (SIGEDUC)

| Status de Origem (`status_origem`) | Status Canônico (`status`) | Justificativa de Negócio |
|---|:---:|---|
| `EM ANDAMENTO` | **`ATIVO`** | Vínculo discente ativo e em acompanhamento no Ensino Médio. |
| `TRANSFERÊNCIA ENTRE MODALIDADES (EM <> EJA)` | **`ATIVO`** | Estudante permanece na rede pública estadual, apenas mudou de modalidade. |
| `TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR DENTRO DA MESMA REDE` | **`ATIVO`** | Estudante mudou de colégio, mas permanece sob a jurisdição da SEC-BA. |
| `TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PÚBLICA` | **`INSCRITO`** | Mudança para rede municipal ou outro estado (registro aguarda confirmação externa). |
| `TRANSFERÊNCIA PARA OUTRA REDE NÃO IDENTIFICADA` | **`INSCRITO`** | Situação cadastral pendente de validação de destino. |
| `TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PRIVADA` | **`INATIVO`** | Saída da rede pública (perda do critério de elegibilidade). |
| `ABANDONO` | **`INATIVO`** | Evasão escolar confirmada pelo sistema acadêmico. |
| `INFORMAÇÃO INCORRETA`| **`INATIVO`** | Registro inconsistente ou duplicado anulado pela escola. |
| `ÓBITO INFORMADO` | **`INATIVO`** | Cancelamento definitivo do cadastro. |

---

### 3.3 Universidade Para Todos (UPT)

| Status de Origem (`status_origem`) | Status Canônico (`status`) | Justificativa de Negócio |
|---|:---:|---|
| `CONTEMPLADO` | **`ATIVO`** | Candidato selecionado, matriculado e frequentando o cursinho UPT. |
| `RESERVA` | **`INSCRITO`** | Candidato classificado na lista de espera aguardando convocação. |
| `INSCRITO` | **`INSCRITO`** | Inscrição confirmada no processo seletivo anual. |
| `CANCELADO` | **`INATIVO`** | Desistência formal do curso pré-vestibular. |
| `DESCLASSIFICADO` | **`INATIVO`** | Candidato não comprovou documentação ou descumpriu edital. |
| `ENCERRADO` | **`INATIVO`** | Turma ou ciclo letivo finalizado. |

---

## 4. Metodologia de Valoração Financeira dos Benefícios

Uma das decisões de modelagem mais importantes da Sprint 3 foi o tratamento do campo financeiro `valor_registrado`:

### 4.1 O caso do Bolsa Presença (SIADIANTE)
* No sistema SIADIANTE, a tabela `beneficio_familia` armazena o valor financeiro nominal individualizado por estudante em cada folha de pagamento mensal (valores típicos de R\$ 150,00, R\$ 200,00, etc., acrescidos de cotas complementares quando aplicável).
* **Tratamento:** O campo é capturado e persistido como `valor_registrado` na tabela fato, permitindo cálculos de soma, média e impacto orçamentário por município na visão `marts.vw_analise_financeira_bolsa_presenca`.

### 4.2 O caso do Pé-de-Meia e do Universidade Para Todos
* **Pé-de-Meia:** Os pagamentos dos incentivos e poupança do Pé-de-Meia são realizados **diretamente pela Caixa Econômica Federal e Ministério da Educação (MEC)**. A base disponível na SEC-BA reflete o acompanhamento acadêmico, elegibilidade e frequência discente, **não contendo a tabela de ordens de pagamento financeiras liquidadas**.
* **UPT:** É um programa de **serviço educacional** (curso preparatório com aulas presenciais, professores universitários e material didático), não envolvendo transferência monetária direta para a conta do estudante.
* **Decisão Arquitetural:** 
  > A Camada Ouro e as visões analíticas **NÃO realizam estimativas ou imputações artificiais de valores** para Pé-de-Meia e UPT. Nessas políticas, o `valor_registrado` é mantido como `NULL`, e as análises focam estritamente em **participação discente, assiduidade, sobreposição e situação cadastral**. Essa decisão garante a integridade estatística e auditoria do TCC, evitando inferências financeiras sem lastro de liquidação na fonte.

---

## 5. Regras de Higienização de Identificadores (Camada Prata)

Para que o cruzamento entre as bases ocorra de forma confiável, a Camada Prata executa regras estritas de normalização:

1. **Matrícula Escolar (`limpar_matricula`):**
   * Expressão regular: `re.sub(r'\D', '', s)`.
   * Remoção de pontuações, traços de dígito verificador e espaços em branco.
   * Valores vazios (`""`, `"nan"`, `"None"`, `"null"`) são convertidos para `None` nativo (SQL `NULL`).
2. **Cadastro de Pessoa Física (`limpar_cpf`):**
   * Remoção de máscaras e pontuações (`.` e `-`).
   * Complementação com zeros à esquerda via `zfill(11)` para garantir 11 dígitos padronizados.
   * Validação de comprimento: registros com mais de 11 dígitos ou caracteres inválidos são rejeitados e convertidos em `None`.
3. **Nomes de Estudantes e Responsáveis (`limpar_nome`):**
   * Remoção de espaços nas extremidades via `strip()`.
   * Conversão compulsória para caixa alta via `upper()`.
   * Redução de múltiplos espaços intermediários (`re.sub(r'\s+', ' ', s)`) para um único caractere de espaço.
4. **Deduplicação Determinística:**
   * Aplicação de `drop_duplicates` sobre as chaves primárias de negócio de cada programa antes da persistência no Data Lake.
