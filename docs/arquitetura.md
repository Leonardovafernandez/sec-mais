# Arquitetura do Projeto SEC MAIS

## Visão Geral

O SEC MAIS é uma plataforma de engenharia de dados desenvolvida para a Secretaria de Educação
do Estado da Bahia (SEC-BA), com o objetivo de integrar e consolidar dados de quatro programas
de políticas públicas educacionais voltados para estudantes da rede estadual.

---

## 1. Arquitetura Medalhão

O projeto implementa a **Arquitetura Medalhão** (Medallion Architecture), um padrão amplamente
adotado em engenharia de dados que organiza os dados em três camadas progressivas de qualidade:

### 1.1 Camada Bronze — Dados Brutos

**Localização:** `armazenamento/bronze/<programa>/`

**Propósito:** Preservar os dados exatamente como extraídos das fontes de origem, sem qualquer
transformação. Funciona como uma "zona de pouso" (landing zone) auditável.

**Características:**
- Formato: Apache Parquet (compressão Snappy)
- Particionamento: `ano=YYYY/mes=MM/dia=DD/`
- Inclui colunas de controle: `_data_extracao`, `_programa`
- Dados podem conter valores nulos, duplicatas, tipos inconsistentes
- Versionamento: cada execução cria um novo arquivo (histórico preservado)

**Subdiretórios:**
```
bronze/
├── bolsa_presenca/
├── universidade_para_todos/
├── mais_estudos/
└── pe_de_meia/
```

### 1.2 Camada Prata — Dados Padronizados

**Localização:** `armazenamento/prata/<programa>/`

**Propósito:** Dados limpos, padronizados e prontos para uso analítico básico.

**Transformações aplicadas:**
- Nomes de colunas em `snake_case` minúsculo
- Remoção de duplicatas (`dropDuplicates()`)
- Tipagem correta (strings, datas, números)
- Remoção de espaços extras em strings
- Substituição de strings vazias por `NULL`
- Remoção de colunas de controle de extração

**Tecnologia:** Apache Spark (PySpark)

### 1.3 Camada Ouro — Dados Analíticos

**Localização:** `armazenamento/ouro/<programa>/`

**Propósito:** Dados prontos para consumo analítico, com regras de negócio aplicadas.

**Transformações aplicadas:**
- Derivações e classificações de negócio
- Indicadores calculados (ex: faixas de frequência, categorias de situação)
- Enriquecimentos e joins necessários
- Preparação para consumo pelo dbt

**Tecnologia:** Apache Spark (PySpark)

---

## 2. Fluxo de Dados

```
Oracle / PostgreSQL
       │
       │ (via VPN)
       │ Verificação de conectividade
       ▼
   Extração (Python + SQLAlchemy)
       │
       │ Parquet particionado por data
       ▼
   BRONZE (dados brutos)
       │
       │ Spark: limpeza, padronização
       ▼
   PRATA (dados limpos)
       │
       │ Spark: regras de negócio
       ▼
   OURO (dados analíticos)
       │
       │ dbt + DuckDB: modelagem dimensional
       ▼
   MARTS (dim_*, fct_*)
       │
       ▼
   Consumo (dashboards, relatórios, análises)
```

---

## 3. Fontes de Dados

### Oracle Database
Hospeda os programas:
- **Bolsa Presença** — `tb_bolsa_presenca`
- **Mais Estudos** — `tb_mais_estudos`

**Acesso:** Requer VPN ativa. Conexão via `cx_Oracle` + SQLAlchemy.

### PostgreSQL
Hospeda os programas:
- **Universidade Para Todos (UPT)** — `tb_universidade_para_todos`
- **Pé-de-Meia** — `tb_pe_de_meia`

**Acesso:** Requer VPN ativa. Conexão via `psycopg2` + SQLAlchemy.

---

## 4. Orquestração (Apache Airflow)

### DAGs Disponíveis

| DAG | Agendamento | Descrição |
|---|---|---|
| `pipeline_completa_sec_mais` | 02:00 diário | Todos os 4 programas em paralelo |
| `bolsa_presenca` | 01:00 diário | Apenas Bolsa Presença |
| `universidade_para_todos` | 01:30 diário | Apenas UPT |
| `mais_estudos` | 01:15 diário | Apenas Mais Estudos |
| `pe_de_meia` | 01:45 diário | Apenas Pé-de-Meia |

### Fluxo de Tarefas (por programa)

```
verificar_vpn → extrair → bronze_prata → prata_ouro
```

O `verificar_vpn` usa `ShortCircuitOperator`: se a VPN não estiver ativa,
o pipeline inteiro é interrompido sem erro (marcado como "skipped").

---

## 5. Modelagem Analítica (dbt)

### Camada Staging

Views que leem diretamente dos Parquets da camada ouro via DuckDB:

- `stg_bolsa_presenca` — Dados do Bolsa Presença
- `stg_universidade_para_todos` — Dados do UPT
- `stg_mais_estudos` — Dados do Mais Estudos
- `stg_pe_de_meia` — Dados do Pé-de-Meia

### Camada Marts

Tabelas dimensionais e de fatos:

- `dim_estudante` — Beneficiários únicos consolidados de todos os programas
- `dim_programa` — Catálogo dos 4 programas com metadados
- `fct_beneficios` — Fato principal: um registro por benefício, com chaves para as dimensões

---

## 6. Decisões Técnicas

### 6.1 Por que não usar Docker para extração?

As bases Oracle e PostgreSQL são acessíveis **exclusivamente via VPN corporativa**.
Em Windows, containers Docker não herdam automaticamente a configuração da VPN da máquina host.
Portanto, os processos de extração rodam **diretamente na máquina local** com Python.

As transformações Spark e o Airflow também rodam localmente, eliminando qualquer dependência
de containers e garantindo acesso à VPN.

### 6.2 Por que armazenamento local em vez de nuvem?

Decisão de custo zero: os dados são armazenados localmente em `armazenamento/`.
O formato Parquet com compressão Snappy oferece:
- Excelente relação espaço/desempenho
- Compatibilidade nativa com Spark e DuckDB
- Leitura colunar eficiente para análises

### 6.3 Por que DuckDB no dbt?

O DuckDB lê arquivos Parquet diretamente do sistema de arquivos, sem necessidade de um
servidor de banco de dados separado. É ideal para análises locais com alto desempenho.

### 6.4 Por que pydantic-settings para configurações?

- Validação de tipos em tempo de execução
- Leitura automática de variáveis de ambiente e arquivos `.env`
- Erros claros quando configurações obrigatórias estão ausentes
- Suporte a valores padrão seguros

---

## 7. Configurações Necessárias

### Arquivo `.env` (baseado em `.env.example`)

```ini
# Oracle (Bolsa Presença e Mais Estudos)
ORACLE_HOST=<ip-ou-hostname-do-oracle>
ORACLE_PORT=1521
ORACLE_SERVICE=<nome-do-servico>
ORACLE_USER=<usuario>
ORACLE_PASSWORD=<senha>
ORACLE_SCHEMA=<schema>

# PostgreSQL (UPT e Pé-de-Meia)
PG_HOST=<ip-ou-hostname-do-postgres>
PG_PORT=5432
PG_DATABASE=<nome-do-banco>
PG_USER=<usuario>
PG_PASSWORD=<senha>
PG_SCHEMA=<schema>
```

### Pré-requisitos do Sistema

- **Java 11+** instalado e `JAVA_HOME` configurado (para o Spark)
- **Python 3.11+**
- **Oracle Instant Client** instalado (para `cx_Oracle`)
- **VPN** configurada e ativa durante as extrações

---

## 8. Monitoramento e Logs

Os logs são gerados com `loguru` em dois destinos:

1. **Console** — Colorido, em tempo real, com nível configurável via `LOG_LEVEL`
2. **Arquivo** — `logs/sec_mais_YYYY-MM-DD.log`, com rotação automática (10 MB) e
   retenção de 30 dias, comprimido em `.zip`

O Airflow fornece monitoramento adicional das DAGs via interface web (`http://localhost:8080`).
