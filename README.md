# SEC MAIS — Plataforma de Dados de Políticas Públicas Educacionais

> **Secretaria de Educação do Estado da Bahia (SEC-BA)**  
> **Trabalho de Conclusão de Curso (TCC) — Engenharia de Dados**  
> Integração, higienização, modelagem dimensional e disponibilização analítica dos programas de apoio e incentivo estudantil da rede estadual da Bahia.

---

## 📌 Status do Projeto

| Sprint | Foco | Status | Entregas Principais |
|:---:|---|:---:|---|
| **Sprint 1** | Infraestrutura & Conectores | **Concluída ✅** | Conectores Oracle e PostgreSQL, verificação de VPN, arquitetura medalhão inicial e testes de rede. |
| **Sprint 2** | Pipeline, Qualidade & Integração | **Concluída ✅** | Extrações reais representativas, higienização Prata (regex CPF/matrícula/nome), deduplicação por chave de negócio, testes unitários com pytest e orquestrador nativo `pipeline_runner.py`. |
| **Sprint 3** | Modelagem Dimensional & DW | **Concluída ✅** | Star Schema Kimball na camada Ouro (`fato_beneficio_estudante` + 4 dimensões), padronização canônica de status (`ATIVO`, `INSCRITO`, `INATIVO`), DW em container Docker PostgreSQL, camada Marts com 6 visões analíticas e dupla persistência (Parquet + SQL). |

---

## 📋 Descrição do Projeto

O **SEC MAIS** é uma plataforma moderna de engenharia de dados construída para integrar e consolidar os dados das políticas públicas educacionais do Estado da Bahia voltadas à permanência, reforço e assistência aos estudantes da rede pública estadual:

| Programa | Órgão Gestor | Tecnologia de Origem | Base de Origem | Papel da Política Pública |
|---|---|---|---|---|
| **Bolsa Presença** | SEC-BA | Oracle 19c | `SIADIANTE` (banco relacional corporativo) | Transferência de renda e incentivo à frequência escolar de famílias em vulnerabilidade. Única base com registros financeiros diretos na fonte. |
| **Pé-de-Meia** | MEC / SEC-BA | PostgreSQL | `sigeduc` (sistema educacional estadual) | Incentivo financeiro e poupança estudantil para conclusão do Ensino Médio. |
| **Universidade Para Todos (UPT)** | SEC-BA | PostgreSQL | `upt` (instância dedicada na porta 5435) | Curso pré-vestibular preparatório para o ingresso de estudantes e egressos da rede pública no ensino superior. |

---

## ⚠️ AVISO DE INFRAESTRUTURA: VPN Corporativa e Conectividade

> **As bases Oracle e PostgreSQL da SEC-BA são acessíveis EXCLUSIVAMENTE via túnel VPN corporativo da rede estadual.**  
> Por questões de isolamento de rede do Windows com interfaces virtuais de containers, as etapas de **extração** rodam diretamente no host via Python nativo. Por outro lado, o **Data Warehouse Analítico (PostgreSQL DW)** da Camada Ouro e Marts opera de forma isolada em **container Docker** (`sec_mais_postgres_dw`) na porta `5432`.

---

## 🏗️ Arquitetura do Sistema e Engenharia de Dados

A plataforma implementa uma **Arquitetura Medalhão** (Bronze → Prata → Ouro) estendida com **Camada Marts Dimensional (Kimball Star Schema)** e **Dupla Persistência**:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FONTES DE DADOS TRANSACIONAIS                              │
│                         (Requerem VPN da SEC-BA ativa no Host)                          │
│                                                                                         │
│   ┌───────────────────────────┐                      ┌──────────────────────────────┐   │
│   │     Oracle SIADIANTE      │                      │   PostgreSQL SIGEDUC / UPT   │   │
│   │   • Bolsa Presença        │                      │   • Pé-de-Meia (sigeduc)     │   │
│   │     (Filtro de Carga)     │                      │   • UPT (upt - porta 5435)   │   │
│   └─────────────┬─────────────┘                      └──────────────┬───────────────┘   │
└─────────────────┼───────────────────────────────────────────────────┼───────────────────┘
                  │               Python + SQLAlchemy                 │
                  └─────────────────────────┬─────────────────────────┘
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              CAMADA BRONZE (Raw Ingestion)                              │
│                        armazenamento/bronze/<programa>/                                 │
│                                                                                         │
│ • Dados brutos imutáveis (append-only) • Formato Apache Parquet (Snappy)                │
│ • Particionamento temporal Hive-style: ano=YYYY/mes=MM/dia=DD/                          │
│ • Preservação histórica para rastreabilidade e auditoria                                │
└───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │  Pandas + PyArrow (Higienização)
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            CAMADA PRATA (Cleaned & Curated)                             │
│                        armazenamento/prata/<programa>/                                  │
│                                                                                         │
│ • Higienização estrita de identificadores:                                              │
│     - MATRICULA: apenas dígitos numéricos (\D removido)                                 │
│     - CPF: limpeza e complementação LPAD 11 com validação                               │
│     - NOME / NOME_SOCIAL: caixa alta (UPPER) e normalização de espaços                  │
│ • Deduplicação determinística por chave de negócio                                      │
│ • Formato Parquet Snappy particionado em: ano=YYYY/mes=MM/                              │
└───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │  Modelagem Dimensional (Star Schema Kimball)
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      CAMADA OURO & MARTS (Double Persistence)                           │
│                                                                                         │
│  ┌─────────────────────────────────────────┐  ┌──────────────────────────────────────┐  │
│  │     Parquet Files (Data Lake Local)     │  │   PostgreSQL DW (Docker Container)   │  │
│  │          armazenamento/ouro/            │  │          schema ouro & marts         │  │
│  │                                         │  │                                      │  │
│  │ • fato_beneficio_estudante.parquet      │  │ • ouro.fato_beneficio_estudante      │  │
│  │ • dim_estudante.parquet                 │  │ • ouro.dim_estudante                 │  │
│  │ • dim_programa.parquet                  │  │ • ouro.dim_programa                  │  │
│  │ • dim_tempo.parquet                     │  │ • ouro.dim_tempo                     │  │
│  │ • dim_municipio.parquet                 │  │ • ouro.dim_municipio                 │  │
│  │                                         │  │ • marts.vw_* (6 Visões Analíticas)   │  │
│  └─────────────────────────────────────────┘  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⭐ Modelagem Dimensional da Camada Ouro (Star Schema Kimball)

A Camada Ouro foi projetada em torno de um grão unificado que resolve o problema de granularidades mistas entre os programas:

* **Grão (Grain):** Uma linha por **Estudante × Programa × Período de Referência** (mês quando existente na fonte; referência anual quando ausente).
* **Anonimização e LGPD:** O `id_estudante` é uma *Surrogate Key* derivada de Hash MD5 dos identificadores, e o CPF é mascarado no formato `***.456.789-**`.

### Entidades Dimensionais

1. **`ouro.fato_beneficio_estudante` (Tabela Fato):**
   * **PK:** `id_fato` (Hash MD5 único da concessão).
   * **FKs:** `id_estudante`, `id_programa`, `id_tempo`, `id_municipio`.
   * **Métricas:** `valor_registrado` (confiável para Bolsa Presença).
   * **Atributos:** `status` (padronizado: `ATIVO`, `INSCRITO`, `INATIVO`), `status_origem` (preservado para auditoria), `matricula_auditoria`, `origem_dado`, `data_carga`.
2. **`ouro.dim_estudante`:**
   * `id_estudante` (PK), `nome_estudante`, `nome_social`, `cpf_mascarado`, `matricula_conciliacao`, `total_programas_acumulados`.
3. **`ouro.dim_programa`:**
   * `id_programa` (PK: 1=Bolsa Presença, 2=Pé-de-Meia, 3=UPT), `nome_programa`, `orgao_gestor`, `publico_alvo`, `possui_valor_financeiro`, `regras_interpretacao`.
4. **`ouro.dim_tempo`:**
   * `id_tempo` (PK: `YYYYMM` para dados mensais ou `YYYY00` para referências anuais), `ano`, `mes`, `ano_mes`, `nome_mes`, `semestre`, `trimestre`, `tipo_periodo`.
5. **`ouro.dim_municipio`:**
   * `id_municipio` (PK), `nome_municipio`, `uf`.

---

## 📊 Camada Marts — Visões Analíticas Disponíveis

No schema `marts` do PostgreSQL DW, foram criadas 6 visões SQL voltadas para responder diretamente às perguntas de negócio e relatórios executivos do TCC:

| Visão | Atividade da Sprint 3 | Descrição / Pergunta de Negócio |
|---|:---:|---|
| **`marts.vw_participacao_programas`** | Atividade 1 | Participação quantitativa dos estudantes por programa, ano, período e status padronizado. |
| **`marts.vw_sobreposicao_matriculas`** | Atividade 2 | Mapeamento detalhado por estudante apontando a quantidade e quais programas recebe em conjunto. |
| **`marts.vw_resumo_sobreposicao`** | Atividade 2 (Resumo) | Resumo executivo da sobreposição de políticas (distribuição percentual de estudantes em 1, 2 ou 3 programas). |
| **`marts.vw_analise_financeira_bolsa_presenca`** | Atividade 3 | Consolidação dos recursos financeiros do Bolsa Presença (total, média, mínimo e máximo) por município. |
| **`marts.vw_cobertura_relacionamento_fontes`** | Atividade 5 | Avaliação da cobertura de matrículas e qualidade de preenchimento dos identificadores entre as fontes. |
| **`marts.vw_indicadores_executivos_sprint3`** | Atividade 10 | Quadro sintético com KPIs gerais (total de estudantes únicos, total de concessões, taxas de sobreposição e montante financeiro). |

---

## 🏷️ Padronização Canônica de Status

Para permitir a integração analítica de bases heterogêneas sem perder o detalhamento operacional, os status originais foram categorizados em 3 status canônicos:

| Status Canônico | Bolsa Presença (SIADIANTE) | Pé-de-Meia (SIGEDUC) | Universidade Para Todos (UPT) |
|:---:|---|---|---|
| **`ATIVO`** | `APTO_FASE1`, `APTO_FASE2`, `APTO_NOVO`, `AL_SEM_ATIV`, `AL_SEM_FREQ`, `RES_SEM_FREQ` | `EM ANDAMENTO`, `TRANSFERÊNCIA ENTRE MODALIDADES (EM <> EJA)`, `TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR DENTRO DA MESMA REDE` | `CONTEMPLADO` |
| **`INSCRITO`** | `AL_BLOQUEADO`, `BLQ_SEM_ATIV`, `BLQ_SEM_FREQ`, `BLQ_RES_SEM_FREQ` | `TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PÚBLICA`, `TRANSFERÊNCIA PARA OUTRA REDE NÃO IDENTIFICADA` | `RESERVA`, `INSCRITO` |
| **`INATIVO`** | `FAIXA_NAO_ENQUADRA`, `CPF_ALUNO_NAO_CONFERE`, `SEM_MATRICULA`, `CAD_DESATUALIZADO`, `CADASTRO_ANALISE`, `RESPONSAVEL_SEM_CPF`, `ESCOLA_NAO_ENQUADRA`, `CAD_SEM_RESPONSAVEL` | `TRANSFERÊNCIA PARA OUTRA UNIDADE ESCOLAR EM OUTRA REDE PRIVADA`, `ABANDONO`, `INFORMAÇÃO INCORRETA`, `ÓBITO INFORMADO` | `CANCELADO`, `DESCLASSIFICADO`, `ENCERRADO` |

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Propósito no Projeto | Justificativa Técnica |
|---|---|---|---|
| **Linguagem Base** | Python 3.11+ | Desenvolvimento de toda a pipeline | Amplo ecossistema analítico e alta interoperabilidade. |
| **Extração & Conectores** | SQLAlchemy, `oracledb`, `psycopg2-binary` | Conexão com Oracle e PostgreSQL corporativos | Conexões seguras com pools de conexão e suporte a SSL. |
| **Data Warehouse Analítico** | PostgreSQL 16 Alpine em Docker | Persistência relacional das camadas Ouro e Marts | Banco de dados analítico local leve, relacional, com índices otimizados e suporte a Star Schema. |
| **Processamento & Engenharia** | Pandas 2.1+, PyArrow | Higienização, deduplicação e modelagem dimensional | Alto desempenho sem necessidade de JVM ou dependência pesada de Hadoop/Spark no Windows. |
| **Armazenamento em Data Lake** | Apache Parquet (Snappy) | Armazenamento colunar local (Bronze, Prata, Ouro) | Compressão eficiente (~80%), tipagem estrita e preservação de metadados. |
| **Orquestração** | Python Runner (`pipeline_runner.py`) | Execução sequencial modular da esteira | Execução nativa no host Windows garantindo herança da VPN corporativa. |
| **Testes Automatizados** | `pytest` | Validação de transformações e qualidade de dados | 8 testes unitários e de integridade com 100% de aprovação. |
| **Análise e Visualização** | Jupyter Notebooks, Matplotlib, Seaborn | Relatórios executivos e evidências do TCC | Geração de gráficos, tabelas e evidências reprodutíveis para os relatórios das Sprints 2 e 3. |
| **Configuração & Segurança** | `pydantic-settings`, `python-dotenv` | Gestão segura de variáveis e credenciais | Segregação estrita entre credenciais UPT, Pé-de-Meia e DW local. |
| **Logging** | `loguru` | Rastreabilidade e auditoria da pipeline | Logs estruturados com rotação diária de arquivos. |

---

## 📁 Estrutura de Diretórios do Projeto

```text
sec-mais/
├── armazenamento/                  # Data Lake Medalhão Local (ignorado no Git)
│   ├── bronze/                     # Dados brutos extraídos (Parquet particionado por dia)
│   ├── prata/                      # Dados higienizados e deduplicados (Parquet por mês)
│   └── ouro/                       # Tabelas dimensionais do Star Schema (Parquet)
│       ├── fato_beneficio_estudante.parquet
│       ├── dim_estudante.parquet
│       ├── dim_programa.parquet
│       ├── dim_tempo.parquet
│       └── dim_municipio.parquet
├── docker/                         # Configuração e DDLs do Data Warehouse local
│   ├── init_dw.sql                 # Script de inicialização dos schemas ouro e marts
│   └── views_marts.sql             # Definição das 6 visões analíticas da camada marts
├── docker-compose.yml              # Subida do container PostgreSQL 16 DW local
├── docs/                           # Documentação detalhada da arquitetura e processos
│   ├── arquitetura.md              # Arquitetura geral e decisões de engenharia
│   ├── modelagem_dimensional.md    # Documentação formal do Star Schema (Atividade 8)
│   ├── regras_negocio_e_status.md  # Mapeamento de status e regras dos programas
│   ├── camada_marts_e_visoes.md    # Catálogo e dicionário das visões analíticas
│   ├── qualidade_e_testes.md       # Regras de higienização e suíte de testes
│   └── guia_execucao_docker.md     # Guia de operação do PostgreSQL DW em Docker
├── extracao/                       # Módulos de extração e conectores corporativos
│   ├── conectores/                 # Drivers Oracle e PostgreSQL com pool e SSL
│   ├── programas/                  # Scripts de extração (bolsa_presenca, pe_de_meia, upt)
│   └── diagnostico_conexoes.py     # Diagnóstico de conectividade de rede e VPN
├── transformacao/                  # Regras de transformação e engenharia de dados
│   ├── modelagem_ouro.py           # Construtor do Star Schema e carga no PostgreSQL DW
│   └── transformar_prata.py        # Higienização e deduplicação Bronze -> Prata
├── utils/                          # Módulos utilitários e de domínio
│   ├── status_mapping.py           # Mapeamento canônico (ATIVO, INSCRITO, INATIVO)
│   ├── storage.py                  # Gerenciamento de diretórios do Data Lake
│   └── vpn_check.py                # Verificação de conectividade de portas de banco
├── tests/                          # Suíte de testes automatizados com pytest
│   ├── test_transformacao_prata.py # 8 testes de higienização, nulos e integridade
│   └── conftest.py
├── notebooks/                      # Notebooks executivos e acadêmicos do TCC
│   ├── 05_evidencias_sprint2_qualidade_e_metricas.ipynb
│   └── 06_evidencias_sprint3_modelagem_analitica_e_entrega.ipynb
├── config/                         # Configurações com Pydantic Settings
│   ├── settings.py                 # Validação de variáveis (.env)
│   └── logging_config.py           # Configuração de logs com Loguru
├── pipeline_runner.py              # Orquestrador central executável fim a fim
├── requirements.txt                # Dependências Python
├── .env.example                    # Modelo seguro de variáveis de ambiente
└── README.md                       # Documentação mestre do repositório
```

---

## 🚀 Guia de Instalação e Execução

### 1. Preparação do Ambiente Virtual Python

```powershell
# Acesse o diretório do projeto
cd "C:\Users\leonardo.fernandez\Desktop\FERNANDEZ\SEC MAIS\sec-mais"

# Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

### 2. Subida do Data Warehouse Local (Docker Compose)

Certifique-se de que o Docker Desktop esteja em execução e execute:

```powershell
docker-compose up -d
```

O container `sec_mais_postgres_dw` será iniciado na porta local `5432` com o banco `sec_mais_dw` e os schemas `ouro` e `marts` criados.

### 3. Configurar Variáveis de Ambiente (`.env`)

Crie seu arquivo `.env` a partir de `.env.example`:

```powershell
copy .env.example .env
```

Preencha as credenciais corporativas da VPN e do DW local (`PG_DW_*`).

### 4. Executar Extração com VPN Conectada

Com o túnel da VPN ativo no Windows:

```powershell
python -m extracao.programas.bolsa_presenca
python -m extracao.programas.pe_de_meia
python -m extracao.programas.universidade_para_todos
```

### 5. Executar a Pipeline Completa Automatizada

O orquestrador `pipeline_runner.py` executa todo o fluxo: higieniza para a camada Prata, constrói o Star Schema na camada Ouro, grava os Parquets, popula o PostgreSQL DW, aplica as views do Marts e valida os testes unitários:

```powershell
# Execução fim a fim
python pipeline_runner.py

# Ou etapas individuais:
python pipeline_runner.py --etapa prata
python pipeline_runner.py --etapa ouro
python pipeline_runner.py --etapa dw
python pipeline_runner.py --etapa testes
```

### 6. Executar os Testes Automatizados

```powershell
pytest tests/test_transformacao_prata.py -v
```

### 7. Visualizar as Evidências nos Notebooks

Para gerar os quadros e gráficos formais do TCC:
* **Sprint 2:** [notebooks/05_evidencias_sprint2_qualidade_e_metricas.ipynb](file:///c:/Users/leonardo.fernandez/Desktop/FERNANDEZ/SEC%20MAIS/sec-mais/notebooks/05_evidencias_sprint2_qualidade_e_metricas.ipynb)
* **Sprint 3:** [notebooks/06_evidencias_sprint3_modelagem_analitica_e_entrega.ipynb](file:///c:/Users/leonardo.fernandez/Desktop/FERNANDEZ/SEC%20MAIS/sec-mais/notebooks/06_evidencias_sprint3_modelagem_analitica_e_entrega.ipynb)

---

## 🔐 Governança de Dados, LGPD e Segurança

* **Mascaramento e Anonimização:** O CPF é mascarado no formato `***.456.789-**` na dimensão estudante, e as chaves de relacionamento utilizam identificadores surrogate hash sem expor dados pessoais diretamente nas consultas de apresentação.
* **Segurança de Credenciais:** As credenciais dos bancos de dados nunca são versionadas no Git (protegidas via `.gitignore`).
* **Segregação de Perfis:** O acesso aos bancos transacionais de origem é estritamente de leitura (`SELECT`), enquanto o Data Warehouse analítico local opera em ambiente isolado.

---

## 👥 Autoria e Agradecimentos

* **Autor:** Leonardo Fernandez
* **Orientação e Revisão:** Colegiado do Curso de Engenharia de Dados
* **Instituição:** Secretaria da Educação do Estado da Bahia (SEC-BA)
* **Finalidade:** Trabalho de Conclusão de Curso (TCC) em Engenharia de Dados
