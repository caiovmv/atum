# Migrations PostgreSQL (versionamento)

O projeto usa **versionamento de banco**: apenas migrations ainda não aplicadas são executadas.

- **Tabela de controle:** `schema_migrations` (colunas `version`, `applied_at`). O nome do arquivo sem `.sql` é a versão (ex.: `001_radio_sintonias`).
- **Ordem:** arquivos `.sql` são aplicados em ordem alfabética. Use prefixo numérico: `001_...`, `002_...`.
- **Quando roda:** na primeira conexão PostgreSQL da API (e em toda conexão, mas só as pendentes são executadas).

Regras para novas migrations:

1. Nome do arquivo: `NNN_descricao.sql` (ex.: `002_nova_tabela.sql`).
2. Use `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` quando fizer sentido.
3. Não altere ou remova arquivos já aplicados em produção; crie uma nova migration para mudanças.

Para aplicar em banco existente: reconstrua a imagem da API (`docker compose build api`) e reinicie; na primeira requisição que usar o banco as migrations pendentes rodam.
