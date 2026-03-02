# Scripts dl-torrent

## serve.ps1 — Build, API Web e Download Runner

Execute a partir da **raiz do projeto** (`dl-torrent`):

```powershell
.\scripts\serve.ps1 [ build | start | stop | restart ]
```

| Ação      | Descrição |
|-----------|-----------|
| `restart` | **(padrão)** Para API (8000) e Runner (9092), faz build do frontend, inicia o Runner em background e a API em primeiro plano. |
| `start`   | Inicia o **Download Runner** (porta 9092) em background e a **API Web** (porta 8000) em primeiro plano. |
| `stop`    | Encerra os processos nas portas 8000 (API) e 9092 (Runner). |
| `build`   | Apenas build do frontend (`npm run build` em `frontend/`). |

**Exemplos:**

```powershell
.\scripts\serve.ps1              # restart (parar + build + subir os dois)
.\scripts\serve.ps1 restart       # idem
.\scripts\serve.ps1 start        # sobe Runner + API (sem build)
.\scripts\serve.ps1 stop         # para API e Runner
.\scripts\serve.ps1 build        # só build do frontend
```

- **API Web:** http://localhost:8000  
- **Download Runner:** http://127.0.0.1:9092 (a API usa `DOWNLOAD_RUNNER_URL` para falar com o Runner)

Ao rodar `start` ou `restart`, o Runner sobe em background e o terminal fica preso na API (Ctrl+C encerra só a API; use `.\scripts\serve.ps1 stop` para encerrar os dois).
