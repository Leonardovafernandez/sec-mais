# Guia Operacional do Data Warehouse Local em Docker

> **Secretaria da Educação do Estado da Bahia (SEC-BA)**  
> **Trabalho de Conclusão de Curso (TCC) — Engenharia de Dados**  
> Manual de Infraestrutura, Operação de Containers e Conectividade do PostgreSQL DW

---

## 1. Visão Geral do Container DW

O Data Warehouse do projeto **SEC MAIS** é executado localmente via **Docker Compose**, utilizando a imagem oficial leve `postgres:16-alpine`. 

Ele foi projetado para operar de forma totalmente independente e isolada dos bancos corporativos da SEC-BA, recebendo os dados já higienizados da Camada Ouro e disponibilizando as visões analíticas da Camada Marts para ferramentas de BI, notebooks e clientes SQL.

---

## 2. Configurações de Infraestrutura

A definição do serviço reside no arquivo [`sec-mais/docker-compose.yml`](file:///c:/Users/leonardo.fernandez/Desktop/FERNANDEZ/SEC%20MAIS/sec-mais/docker-compose.yml):

```yaml
version: '3.8'

services:
  postgres_dw:
    image: postgres:16-alpine
    container_name: sec_mais_postgres_dw
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${PG_DW_DATABASE:-sec_mais_dw}
      POSTGRES_USER: ${PG_DW_USER:-postgres}
      POSTGRES_PASSWORD: ${PG_DW_PASSWORD:-secmais_password}
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "${PG_DW_PORT:-5432}:5432"
    volumes:
      - sec_mais_pgdata:/var/lib/postgresql/data
      - ./docker/init_dw.sql:/docker-entrypoint-initdb.d/01_init_dw.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PG_DW_USER:-postgres} -d ${PG_DW_DATABASE:-sec_mais_dw}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  sec_mais_pgdata:
    name: sec_mais_pgdata
```

### Parâmetros de Conexão Padrão:
* **Host:** `localhost`
* **Porta:** `5432`
* **Banco de Dados:** `sec_mais_dw`
* **Usuário:** `postgres`
* **Senha:** `secmais_password` (ou o valor definido na variável `PG_DW_PASSWORD` do `.env`)
* **Volume Persistente:** `sec_mais_pgdata` (preserva os dados mesmo se o container for parado)

---

## 3. Comandos Operacionais Essenciais

Todos os comandos devem ser executados a partir do diretório raiz do projeto:

```powershell
cd "C:\Users\leonardo.fernandez\Desktop\FERNANDEZ\SEC MAIS\sec-mais"
```

### 3.1 Iniciar o Data Warehouse em Segundo Plano
```powershell
docker-compose up -d
```

### 3.2 Verificar o Status e a Saúde do Container
```powershell
docker-compose ps
```
*A saída deve indicar `Up (healthy)` para o serviço `postgres_dw`.*

### 3.3 Visualizar os Logs do Banco
```powershell
docker-compose logs -f postgres_dw
```

### 3.4 Parar o Container sem Perder os Dados
```powershell
docker-compose stop
```

### 3.5 Reiniciar o Container
```powershell
docker-compose start
```

### 3.6 Reinicialização Limpa (Reset Total do Banco)
Se desejar limpar completamente o banco e recomeçar do zero (apagando o volume persistente):
```powershell
docker-compose down -v
docker-compose up -d
```

---

## 4. Inicialização de Schemas e Visões Analíticas

O container é configurado para inicializar automaticamente:
1. **Script de Inicialização Automática:**  
   O arquivo [`sec-mais/docker/init_dw.sql`](file:///c:/Users/leonardo.fernandez/Desktop/FERNANDEZ/SEC%20MAIS/sec-mais/docker/init_dw.sql) é montado no diretório `/docker-entrypoint-initdb.d/` e executado na primeira subida do container, criando os schemas `ouro` e `marts`.
2. **Carga e Aplicação das Views:**  
   Durante a execução da pipeline (`python pipeline_runner.py` ou `python -m transformacao.modelagem_ouro`), as tabelas são criadas no schema `ouro` e o script [`sec-mais/docker/views_marts.sql`](file:///c:/Users/leonardo.fernandez/Desktop/FERNANDEZ/SEC%20MAIS/sec-mais/docker/views_marts.sql) é aplicado automaticamente para criar/recriar as 6 visões analíticas.

---

## 5. Como Conectar via Clientes SQL Externos

Você pode utilizar clientes SQL como **DBeaver**, **VS Code (extensão Database Client ou SQLTools)** ou **pgAdmin** para explorar as tabelas e views:

### Configuração no DBeaver:
1. Clique em **Nova Conexão** → Selecione **PostgreSQL**.
2. Preencha os campos da aba Geral:
   * **Host:** `localhost`
   * **Database:** `sec_mais_dw`
   * **Port:** `5432`
   * **Username:** `postgres`
   * **Password:** `secmais_password`
3. Clique em **Testar Conexão** → O DBeaver confirmará o sucesso da conexão.
4. Navegue pela árvore de objetos:
   * `sec_mais_dw` → `Schemas` → `ouro` (Tabelas: `fato_beneficio_estudante`, `dim_*`)
   * `sec_mais_dw` → `Schemas` → `marts` (Visões: `vw_*`)

### Conexão via Terminal Interativo (`psql` dentro do container):
```powershell
docker exec -it sec_mais_postgres_dw psql -U postgres -d sec_mais_dw
```

Comandos úteis dentro do `psql`:
```sql
\dn              -- Lista os schemas existentes (ouro, marts, public)
\dt ouro.*       -- Lista as tabelas dimensionais da camada ouro
\dv marts.*      -- Lista as visões analíticas da camada marts
SELECT COUNT(*) FROM ouro.fato_beneficio_estudante;
\q               -- Sair do psql
```

---

## 6. Troubleshooting e Resolução de Problemas

### 6.1 Conflito de Porta 5432 no Windows
* **Sintoma:** Erro ao executar `docker-compose up -d`: `Bind for 0.0.0.0:5432 failed: port is already allocated`.
* **Causa:** Existe outra instância do PostgreSQL instalada diretamente no Windows ocupando a porta 5432.
* **Solução:**
  1. Abra o arquivo `.env`.
  2. Altere a porta mapeada do DW local, por exemplo:
     ```ini
     PG_DW_PORT=5433
     ```
  3. Reinicie o container com `docker-compose up -d`.
  4. O banco responderá normalmente em `localhost:5433`.

### 6.2 Docker Desktop Não Inicializado
* **Sintoma:** `error during connect: This error may indicate that the docker daemon is not running`.
* **Solução:** Abra o aplicativo **Docker Desktop** no Windows, aguarde o ícone da baleia ficar verde (*Engine running*) e repita o comando `docker-compose up -d`.
