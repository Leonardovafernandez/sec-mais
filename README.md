# SEC MAIS — Plataforma de Dados de Políticas Públicas Educacionais

> **Secretaria de Educação do Estado da Bahia**  
> Integração de dados de programas de apoio a estudantes da rede estadual

---

## 📋 Descrição

O **SEC MAIS** é uma plataforma de engenharia de dados que integra e consolida informações
dos principais programas de políticas públicas educacionais do Estado da Bahia:

| Programa | Fonte | Descrição |
|---|---|---|
| **Bolsa Presença** | Oracle | Incentivo à frequência escolar |
| **Universidade Para Todos (UPT)** | PostgreSQL | Acesso à educação superior |
| **Mais Estudos** | Planilha | Atividades educacionais complementares |
| **Pé-de-Meia** | PostgreSQL | Poupança estudantil do ensino médio |

---

## ⚠️ AVISO IMPORTANTE: VPN Obrigatória

> **Os bancos de dados Oracle e PostgreSQL são acessíveis SOMENTE via VPN da rede estadual.**
> 
> Antes de qualquer processo de extração, **certifique-se de que a VPN está ativa**.  
> O sistema verifica automaticamente a conectividade antes de executar qualquer extração.

---

## 🏗️ Arquitetura

### Diagrama da Arquitetura Medalhão

```
┌──────────────────────────────────────────────────────────────────┐
│                        FONTES DE DADOS                           │
│                      (Requerem VPN ativa)                        │
│                                                                  │
│    ┌─────────────────┐          ┌─────────────────┐              │
│    │  Oracle DB      │          │  PostgreSQL DB  │              │
│    │                 │          │                 │              │
│    │ • Bolsa Presença│          │ • UPT           │              │
│    │ • Mais Estudos  │          │ • Pé-de-Meia    │              │
│    └────────┬────────┘          └────────┬────────┘              │
└─────────────┼────────────────────────────┼───────────────────────┘
              │   Python + SQLAlchemy      │
              └──────────────┬─────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     CAMADA BRONZE                                │
│              armazenamento/bronze/<programa>/                    │
│                                                                  │
│  Dados brutos • Formato Parquet • Particionado por data          │
└──────────────────────────┬───────────────────────────────────────┘
                           │  Apache Spark
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     CAMADA PRATA                                 │
│              armazenamento/prata/<programa>/                     │
│                                                                  │
│  Dados limpos • Tipagem correta • Sem duplicatas • Snake_case    │
└──────────────────────────┬───────────────────────────────────────┘
                           │  Apache Spark
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     CAMADA OURO                                  │
│               armazenamento/ouro/<programa>/                     │
│                                                                  │
│  Dados analíticos • Regras de negócio aplicadas • Para consumo   │
└──────────────────────────┬───────────────────────────────────────┘
                           │  dbt + DuckDB
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   CAMADA ANALÍTICA (dbt)                         │
│                                                                  │
│  staging/ → marts/ (dim_estudante, dim_programa, fct_beneficios) │
└──────────────────────────────────────────────────────────────────┘
```

### Stack Tecnológica

| Componente | Tecnologia | Propósito |
|---|---|---|
| Extração | Python + SQLAlchemy | Extração dos bancos Oracle e PostgreSQL |
| Orquestração | Apache Airflow | Agendamento e monitoramento dos pipelines |
| Transformação | Apache Spark (PySpark) | Processamento das camadas medalhão |
| Modelagem Analítica | dbt + DuckDB | Modelos dimensionais e marts |
| Armazenamento | Parquet local | Sem custos de nuvem |
| Configurações | python-dotenv + pydantic | Gerenciamento seguro de credenciais |
| Logging | loguru | Logging colorido e rotacionado |

---

## 🚀 Pré-requisitos

### Sistema
- Python 3.11+
- Java 11+ (para o Apache Spark)
- VPN da rede estadual configurada

### Dependências Python
```bash
pip install -r requirements.txt
```

### Configuração do Ambiente
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite com suas credenciais (NUNCA commite o .env!)
notepad .env   # Windows
nano .env      # Linux/Mac
```

---

## ⚙️ Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd sec-mais

# 2. Crie um ambiente virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as credenciais
cp .env.example .env
# Edite o .env com suas credenciais

# 5. Instale o pacote em modo desenvolvimento
pip install -e .
```

---

## 🔧 Como Executar

### 1. Verificar Conectividade (sempre primeiro!)

```bash
# Verifica se a VPN está ativa e os bancos estão acessíveis
python -m extracao.verificacao_conexao
```

### 2. Executar Extração Manualmente

```bash
# Extração individual por programa
python -m extracao.programas.bolsa_presenca
python -m extracao.programas.universidade_para_todos
python -m extracao.programas.mais_estudos
python -m extracao.programas.pe_de_meia
```

### 3. Executar Transformações Spark

```bash
# Bronze → Prata
python -m transformacao.bronze_para_prata.bolsa_presenca

# Prata → Ouro
python -m transformacao.prata_para_ouro.bolsa_presenca
```

### 4. Iniciar o Airflow

```bash
# Inicializa o banco do Airflow
airflow db init

# Inicia o scheduler
airflow scheduler

# Em outro terminal, inicia a interface web
airflow webserver --port 8080

# Acesse em: http://localhost:8080
```

### 5. Executar o dbt

```bash
cd dbt_sec_mais

# Instalar dependências dbt
dbt deps

# Testar conexão
dbt debug

# Executar os modelos
dbt run

# Testar os modelos
dbt test

# Gerar documentação
dbt docs generate
dbt docs serve
```

### 6. Executar os Testes

```bash
# Executa todos os testes
pytest tests/ -v

# Com cobertura de código
pytest tests/ -v --cov=. --cov-report=html
```

---

## 📁 Estrutura do Projeto

```
sec-mais/
├── armazenamento/           # Dados locais (não versionados)
│   ├── bronze/              # Dados brutos extraídos
│   ├── prata/               # Dados padronizados
│   └── ouro/                # Dados analíticos
├── extracao/                # Extração das fontes
│   ├── conectores/          # Oracle e PostgreSQL
│   ├── programas/           # Um arquivo por programa
│   └── verificacao_conexao.py
├── transformacao/           # Transformações Spark
│   ├── bronze_para_prata/
│   └── prata_para_ouro/
├── dbt_sec_mais/            # Projeto dbt
│   ├── models/
│   │   ├── staging/         # Views sobre a camada ouro
│   │   └── marts/           # Dimensões e fatos
│   └── macros/
├── airflow/
│   └── dags/                # DAGs de orquestração
├── config/                  # Configurações centralizadas
├── utils/                   # Utilitários (storage, vpn_check)
├── tests/                   # Testes automatizados
├── docs/                    # Documentação
├── .env.example             # Template de configurações
├── requirements.txt
└── README.md
```

---

## 🔐 Segurança e Credenciais

- **Nunca** commite o arquivo `.env` (já está no `.gitignore`)
- As credenciais são lidas exclusivamente via variáveis de ambiente
- Os dados de armazenamento (`bronze/`, `prata/`, `ouro/`) também estão no `.gitignore`
- Use o arquivo `.env.example` como referência para as variáveis necessárias

---

## 🤝 Contribuindo

1. Certifique-se de ter a VPN ativa
2. Execute `python -m extracao.verificacao_conexao` para verificar conectividade
3. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
4. Execute os testes antes de commitar: `pytest tests/`
5. Abra um Pull Request com descrição detalhada das mudanças

---

## 📞 Suporte

Em caso de problemas com conectividade (VPN), entre em contato com o time de TI da SEC-BA.

Para questões sobre o projeto, consulte a [documentação de arquitetura](docs/arquitetura.md).
