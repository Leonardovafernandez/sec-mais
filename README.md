# SEC MAIS — Plataforma de Dados de Políticas Públicas Educacionais

> **Secretaria de Educação do Estado da Bahia (SEC-BA)**  
> **Trabalho de Conclusão de Curso (TCC) — Engenharia de Dados**  
> Integração, higienização e consolidação analítica de dados dos programas de apoio a estudantes da rede estadual da Bahia.

---

## 📌 Status do Projeto

| Sprint | Foco | Status | Entregas Principais |
|:---:|---|:---:|---|
| **Sprint 1** | Infraestrutura & Conectores | **Concluída ✅** | Conectores Oracle e PostgreSQL, verificação de VPN, arquitetura medalhão inicial. |
| **Sprint 2** | Pipeline, Qualidade & Integração | **Concluída ✅** | Extrações reais com amostragem, higienização Prata, particionamento Hive, Fato Ouro integrada, testes automatizados e orquestrador nativo. |
| **Sprint 3** | Modelagem Analítica & Consumo | *Em Planejamento ⏳* | Camada semântica/marts analíticos, dashboards de visualização e métricas de impacto educacional. |

---

## 📋 Descrição do Projeto

O **SEC MAIS** é uma plataforma moderna de engenharia de dados construída para integrar e unificar os dados transacionais dos programas de permanência, assistência estudantil e incentivo educacional do Estado da Bahia:

| Programa | Fonte / Banco | Tecnologia de Origem | Papel da Política Pública |
|---|---|---|---|
| **Bolsa Presença** | Oracle 19c (`SIADIANTE`) | Banco relacional corporativo SEC-BA | Transferência de renda e incentivo à frequência escolar da rede estadual. |
| **Pé-de-Meia** | PostgreSQL (`sigeduc`) | Banco relacional do sistema educacional | Poupança estudantil do ensino médio (MEC / SEC-BA). |
| **Universidade Para Todos (UPT)** | PostgreSQL (`upt`) | Banco relacional do sistema educacional | Preparatório e incentivo ao ingresso no ensino superior. |
| **Mais Estudos** | Planilha / Sistema Interno | Extração suplementar | Monitoria e reforço da aprendizagem escolar. |

---

## ⚠️ AVISO IMPORTANTE: VPN Corporativa Obrigatória

> **Os bancos de dados Oracle e PostgreSQL da SEC-BA são acessíveis EXCLUSIVAMENTE via túnel VPN da rede estadual.**  


---

## 🏗️ Arquitetura do Sistema

### Arquitetura Medalhão Implementada

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          FONTES DE DADOS TRANSACIONAIS                           │
│                      (Requerem VPN da SEC-BA ativa no Host)                      │
│                                                                                  │
│   ┌────────────────────────┐                    ┌────────────────────────────┐   │
│   │   Oracle SIADIANTE     │                    │  PostgreSQL SIGEDUC / UPT  │   │
│   │   • Bolsa Presença     │                    │  • Pé-de-Meia              │   │
│   │   (Filtro ROWNUM <= 100k)                   │  • UPT                     │   │
│   └───────────┬────────────┘                    └─────────────┬──────────────┘   │
└───────────────┼───────────────────────────────────────────────┼──────────────────┘
                │            Python + SQLAlchemy                │
                └───────────────────────┬───────────────────────┘
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           CAMADA BRONZE (Raw Ingestion)                          │
│                     armazenamento/bronze/<programa>/                             │
│                                                                                  │
│ • Dados brutos imutáveis (append-only) • Formato Apache Parquet                  │
│ • Particionamento temporal Hive-style: ano=YYYY/mes=MM/dia=DD/                   │
│ • Preservação histórica para fins de rastreabilidade e auditoria                 │
└───────────────────────────────────────┬──────────────────────────────────────────┘
                                        │  Pandas + PyArrow (Higienização)
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        CAMADA PRATA (Cleaned & Curated)                          │
│                     armazenamento/prata/<programa>/                              │
│                                                                                  │
│ • Higienização estrita de identificadores:                                       │
│     - MATRICULA: apenas dígitos numéricos                                        │
│     - CPF: remoção de máscara e complementação LPAD 11 zeros                     │
│     - NOME: caixa alta (UPPER) e eliminação de espaços duplicados                │
│ • Deduplicação por chave composta de negócio:                                    │
│     - Bolsa Presença: (MATRICULA, ANO, MES)                                      │
│     - Pé-de-Meia: (MATRICULA, ANO)                                               │
│     - UPT: (NUMERO_INSCRICAO)                                                    │
│ • Formato Parquet com compressão Snappy, particionado em: ano=YYYY/mes=MM/       │
└───────────────────────────────────────┬──────────────────────────────────────────┘
                                        │  Merge Relacional (Full Outer Join)
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                       CAMADA OURO (Integrated Analytical)                        │
│                           armazenamento/ouro/                                    │
│                                                                                  │
│ • Tabela Fato Consolidada: fct_estudantes_beneficios_integrados.parquet          │
│ • Visão 360º do estudante: unificação através da MATRICULA única                 │
│ • Flags booleanas de benefício: BENEFICIO_PE_DE_MEIA, BENEFICIO_UPT, etc.        │
│ • Atributo métrico: TOTAL_PROGRAMAS_RECEBIDOS (contagem de apoios acumulados)    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Propósito no Projeto | Justificativa Técnica |
|---|---|---|---|
| **Linguagem Base** | Python 3.11+ | Desenvolvimento de toda a pipeline | Amplo ecossistema de dados e interoperabilidade com drivers C/C++. |
| **Extração & Conectores** | SQLAlchemy, `oracledb`, `psycopg2-binary` | Conexão com Oracle e PostgreSQL | Drivers otimizados para pools de conexão e consultas corporativas. |
| **Processamento & Engenharia** | Pandas 2.1+, PyArrow | Higienização, deduplicação e cruzamentos | Alternativa leve e de altíssimo desempenho ao PySpark local em Windows, sem overhead de JVM/Hadoop. |
| **Armazenamento** | Apache Parquet (Snappy) | Armazenamento colunar local | Redução drástica de espaço em disco (~80%), tipagem forte e leitura seletiva de colunas. |
| **Orquestração** | Python Pipeline Runner (`pipeline_runner.py`) | Execução sequencial modular da esteira | Execução nativa no host Windows garantindo herança da VPN corporativa (substitui o Airflow). |
| **Agendamento** | Windows Task Scheduler / Cron | Disparo periódico dos processos | Automação sem necessidade de daemons pesados consumindo RAM continuamente. |
| **Testes de Qualidade** | `pytest`, Profiling Pandas | Validação de transformações e dados | Cobertura de testes unitários de expressões regulares e integridade relacional. |
| **Configuração & Segurança** | `pydantic-settings`, `python-dotenv` | Gestão segura de variáveis e credenciais | Segregação estrita entre credenciais UPT e Pé-de-Meia via `.env`. |
| **Logging** | `loguru` | Rastreabilidade e depuração | Logs estruturados com rotação de arquivos e saída colorida no terminal. |

---

## ⚖️ Decisão de Engenharia: Orquestração e Viabilidade Técnica

Durante o desenvolvimento da Sprint 2, foi realizada uma avaliação prática de viabilidade entre o **Apache Airflow** e um **Orquestrador Python Nativo**:

1. **Incompatibilidade do Apache Airflow no Ambiente Windows:**
   - O Airflow não possui suporte nativo para Microsoft Windows, dependendo de chamadas POSIX e compilação de código C/C++ (*MSVC Build Tools*) durante o `pip install`, o que gerava falhas constantes de instalação em dependências como `pyyaml`, `psutil` e `greenlet`.
2. **Isolamento de Rede da VPN Corporativa SEC-BA:**
   - A alternativa usual de rodar o Airflow dentro de contêineres Docker ou no WSL2 (subsistema Linux) encontrou uma barreira de infraestrutura corporativa: a VPN da SEC-BA opera exclusivamente na interface de rede do host Windows. Contêineres virtuais e máquinas WSL2 ficavam isolados (*vEthernet*), incapazes de resolver os IPs internos da SEC.
3. **Solução Implementada:**
   - Adotou-se o **`pipeline_runner.py`**, um executor modular em Python que roda nativamente no host Windows, preservando o túnel de rede da VPN, executando as etapas com controle transacional de erros, gerando logs rotacionados e permitindo agendamento direto pelo **Agendador de Tarefas do Windows (Task Scheduler)**.

---

## 📁 Estrutura de Diretórios Atualizada

```text
sec-mais/
├── armazenamento/                  # Armazenamento Medalhão Local (ignorado no Git)
│   ├── bronze/                     # Dados brutos extraídos (Parquet por data de extração)
│   │   ├── bolsa_presenca/         # ano=YYYY/mes=MM/dia=DD/
│   │   ├── pe_de_meia/             # ano=YYYY/mes=MM/dia=DD/
│   │   └── universidade_para_todos/# ano=YYYY/mes=MM/dia=DD/
│   ├── prata/                      # Dados higienizados e deduplicados (Parquet Snappy)
│   │   ├── bolsa_presenca/         # ano=YYYY/mes=MM/estudante_bolsa_presenca_*.parquet
│   │   ├── pe_de_meia/             # ano=YYYY/mes=MM/estudantes_pe_de_meia_*.parquet
│   │   └── universidade_para_todos/# ano=YYYY/mes=MM/estudante_upt_*.parquet
│   └── ouro/                       # Base analítica integrada
│       └── fct_estudantes_beneficios_integrados.parquet
├── extracao/                       # Módulos de extração e conectores
│   ├── conectores/                 # Conectores Oracle e PostgreSQL (com suporte a sslmode)
│   ├── programas/                  # Scripts de extração por programa
│   │   ├── bolsa_presenca.py       # Extração com amostragem representativa (ROWNUM <= 100k)
│   │   ├── pe_de_meia.py           # Extração do SIGEDUC (Postgres)
│   │   └── universidade_para_todos.py # Extração do UPT (Postgres dedicado porta 5435)
│   ├── diagnostico_conexoes.py     # Diagnóstico completo de conectividade e VPN
│   └── verificacao_conexao.py      # Teste rápido de portas
├── transformacao/                  # Regras de higienização e transformação
│   └── bronze_para_prata/          # Padronizações em Pandas/PyArrow
├── notebooks/                      # Notebooks analíticos e de validação
│   └── 05_evidencias_sprint2_qualidade_e_metricas.ipynb  # Notebook mestre com as 10 Atividades
├── tests/                          # Suíte de testes automatizados
│   ├── test_transformacao_prata.py # Testes de CPF, matrícula, nomes, chaves e Fato Ouro
│   └── conftest.py
├── config/                         # Configurações centralizadas
│   ├── settings.py                 # Pydantic Settings (segregação PG_UPT_* e PG_PDM_*)
│   └── logging_config.py           # Configuração Loguru
├── utils/                          # Utilitários de sistema
│   ├── storage.py                  # Gerenciamento de pastas e caminhos medalhão
│   └── vpn_check.py                # Verificadores de socket para Oracle e Postgres
├── pipeline_runner.py              # Orquestrador central executável da pipeline
├── requirements.txt                # Dependências do projeto
├── setup.py                        # Instalação do pacote sec-mais
├── .env.example                    # Modelo seguro de variáveis de ambiente
└── README.md                       # Documentação principal
```

---

## 🚀 Instalação e Configuração

### 1. Clonar o Repositório e Criar o Ambiente Virtual

```powershell
# Acesse o diretório do projeto
cd "C:\Users\leonardo.fernandez\Desktop\FERNANDEZ\SEC MAIS\sec-mais"

# Crie o ambiente virtual com Python 3.11+
python -m venv .venv

# Ative o ambiente virtual
.venv\Scripts\activate
```

### 2. Instalar as Dependências

```powershell
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente (`.env`)

Crie uma cópia do arquivo `.env.example` nomeada como `.env`:

```powershell
copy .env.example .env
```

Edite o `.env` com as credenciais corporativas. Observe que o PostgreSQL do UPT e do Pé-de-Meia possuem configurações segregadas:

```ini
# Oracle (Bolsa Presença / SIADIANTE)
ORACLE_HOST=exemple
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=banco
ORACLE_USER=seu_usuario
ORACLE_PASSWORD=sua_senha

# PostgreSQL (Pé-de-Meia / SIGEDUC)
PG_PDM_HOST=exemple
PG_PDM_PORT=5432
PG_PDM_DATABASE=banco
PG_PDM_USER=seu_usuario
PG_PDM_PASSWORD=sua_senha

# PostgreSQL (Universidade Para Todos / UPT)
PG_UPT_HOST=exemple
PG_UPT_PORT=5432
PG_UPT_DATABASE=upbancot
PG_UPT_USER=seu_usuario
PG_UPT_PASSWORD=sua_senha
PG_UPT_SSLMODE=disable
```

---

## 🏃 Como Executar

### 1. Diagnóstico de Conexões e VPN (Obrigatório)

Antes de iniciar qualquer extração, valide se a VPN está conectada e se todas as portas dos bancos estão acessíveis:

```powershell
python -m extracao.diagnostico_conexoes
```

### 2. Executar Extração dos Dados (Camada Bronze)

```powershell
# Extração do Bolsa Presença (Oracle)
python -m extracao.programas.bolsa_presenca

# Extração do Pé-de-Meia (PostgreSQL)
python -m extracao.programas.pe_de_meia

# Extração do UPT (PostgreSQL)
python -m extracao.programas.universidade_para_todos
```

### 3. Executar a Pipeline Completa Automatizada

O orquestrador `pipeline_runner.py` lê os dados da Camada Bronze, executa a higienização, persiste na Camada Prata e consolida a base Ouro integrada:

```powershell
# Executa fluxo fim a fim (Prata + Ouro + Testes)
python pipeline_runner.py

# Ou execute etapas específicas:
python pipeline_runner.py --etapa prata
python pipeline_runner.py --etapa ouro
python pipeline_runner.py --etapa testes
```

### 4. Executar os Testes Automatizados

Para rodar a suíte de validações e asserções de qualidade da Sprint 2:

```powershell
pytest tests/test_transformacao_prata.py -v
```

### 5. Executar o Notebook de Evidências da Sprint 2

Abra o arquivo `notebooks/05_evidencias_sprint2_qualidade_e_metricas.ipynb` no VS Code ou Jupyter e clique em **"Run All"**.  
O notebook executa as 10 atividades em sequência e gera todos os quadros e tabelas formais prontos para o relatório acadêmico:
- **Atividade 1:** Inventário de arquivos brutos na Camada Bronze.
- **Atividades 2 e 3:** Amostras de higienização de Matrícula, CPF e Nomes (Antes vs Depois).
- **Atividade 4:** Relatório de Qualidade de Dados (*Data Quality Profiling* com auditoria de nulos).
- **Atividade 5:** Inventário físico dos arquivos particionados na Camada Prata.
- **Atividade 6:** Amostra e gravação da base integrada na Camada Ouro.
- **Atividade 7:** Quadro de viabilidade técnica dos componentes de orquestração.
- **Atividade 8:** Relatório de execução dos testes de transformações e integridade.
- **Atividade 9:** Quadro consolidado de métricas quantitativas da Sprint 2.
- **Atividade 10:** Matriz de documentação de processos e decisões de tratamento.

---

## 🧪 Regras de Qualidade e Higienização

1. **Matrícula do Estudante:**
   - Remoção de qualquer caractere não numérico (`\D`).
   - Eliminação de espaços em branco e valores vazios convertidos em `NULL`.
2. **Cadastro de Pessoa Física (CPF):**
   - Limpeza de pontos e traços.
   - Formatação estrita com 11 dígitos via `LPAD 11` (preenchimento com zeros à esquerda).
   - Validação de comprimento para anulação de registros espúrios.
3. **Nomes (Estudante, Nome Social e Responsável):**
   - Conversão integral para caixa alta (`UPPER`).
   - Normalização de múltiplos espaços em branco intermediários para um único espaço.
4. **Deduplicação de Registros:**
   - Deduplicação determinística com base na chave de negócio de cada programa antes da persistência na camada Prata.
5. **Integração Relacional Multi-Fonte:**
   - Realização de *Full Outer Join* por matrícula única.
   - Atribuição de flags booleanas (`True`/`False`) para cada benefício.
   - Cômputo do total de benefícios simultâneos recebidos por estudante (`TOTAL_PROGRAMAS_RECEBIDOS >= 1`).

---

## 🔐 Governança, LGPD e Segurança

- O arquivo `.env` contendo credenciais sensíveis nunca é enviado ao controle de versão (protegido via `.gitignore`).
- Os diretórios locais da camada medalhão (`armazenamento/bronze/`, `prata/`, `ouro/`) são mantidos localmente sob estrito sigilo de dados públicos educacionais, respeitando os preceitos da Lei Geral de Proteção de Dados (LGPD - Lei nº 13.709/2018).
- As extrações contam com limites de amostragem controlada para desenvolvimento seguro e eficiente.

---

## 👥 Autoria e Agradecimentos

- **Autor:** Leonardo Fernandez
- **Instituição:** Secretaria da Educação do Estado da Bahia (SEC-BA)
- **Finalidade:** Trabalho de Conclusão de Curso (TCC) em Engenharia de Dados
