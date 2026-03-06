# Banco de dados (PostgreSQL)

O projeto usa **PostgreSQL** quando `DATABASE_URL` está definido. O schema e as migrations garantem que você **nunca fique sem as tabelas certas**, seja zerando o banco ou subindo o projeto do zero.

## Como o banco é criado e atualizado

Há dois momentos em que o schema é aplicado:

1. **Init do Postgres (só em volume novo)**  
   No Docker, o arquivo `scripts/schema_postgres.sql` é montado em `/docker-entrypoint-initdb.d/01-schema.sql`. Quando o **volume do Postgres é criado pela primeira vez**, o container executa esse script e cria todas as tabelas do schema principal (incluindo `schema_migrations` e tabelas de rádio).

2. **Toda conexão da API**  
   Sempre que a API abre uma conexão com o banco (`db_postgres`), ela:
   - reaplica o **schema principal** (`scripts/schema_postgres.sql`) com `CREATE TABLE IF NOT EXISTS` (não apaga nada);
   - aplica só as **migrations pendentes** em `scripts/migrations/` e registra cada uma na tabela `schema_migrations`.

Assim, tanto em **projeto novo** quanto em **banco zerado**, o banco fica completo após o Postgres subir e a API conectar.

## Cenários que estão cobertos

| Cenário | O que acontece |
|--------|------------------|
| **Subir o projeto do zero** (`git clone` + `docker compose up`) | Postgres sobe com volume novo → init executa `01-schema.sql` (= `schema_postgres.sql`) → todas as tabelas são criadas. Na primeira requisição, a API conecta, reaplica o schema (idempotente) e roda as migrations pendentes (registrando em `schema_migrations`). |
| **Zerar o banco** (apagar o volume do Postgres e subir de novo) | Igual ao item acima: volume novo → init roda o schema → API aplica migrations pendentes. Banco volta ao estado esperado. |
| **Banco já existente** (sem as tabelas de rádio ou de uma migration nova) | Na primeira conexão da API, as migrations ainda não aplicadas rodam (por exemplo `001_radio_sintonias.sql`) e são registradas em `schema_migrations`. Não é preciso rodar SQL à mão. |

## O que você precisa garantir

- **Postgres em execução** e **`DATABASE_URL`** configurado (no Docker isso já vem no `docker-compose`).
- Ao subir **do zero**, subir pelo menos o **Postgres** (e depois a API). Ex.: `docker compose up -d postgres` e em seguida os outros serviços.

Se o Postgres não estiver no ar ou `DATABASE_URL` não estiver definido, a API falha ao acessar o banco (erro explícito). Não há cenário em que “o projeto sobe sem banco” sem aviso: ou o banco existe e é atualizado (schema + migrations), ou a aplicação indica que não consegue conectar.

## Versionamento (migrations)

- Tabela de controle: **`schema_migrations`** (coluna `version` = nome do arquivo sem `.sql`).
- Migrations em **`scripts/migrations/`** (ex.: `001_radio_sintonias.sql`) são aplicadas em ordem alfabética **apenas uma vez**; as já aplicadas são ignoradas.
- Detalhes em [scripts/migrations/README.md](../scripts/migrations/README.md).

## Resumo

- **Zerar o banco:** remover o volume do Postgres e subir de novo; o init + a API recriam e atualizam tudo.
- **Projeto do zero:** `docker compose up` com volume novo; o init aplica o schema e a API aplica as migrations na primeira conexão.
- O banco não fica “sem tabelas” desde que o Postgres esteja rodando e a API consiga conectar (e tenha acesso a `scripts/schema_postgres.sql` e `scripts/migrations/` no build/ambiente).
