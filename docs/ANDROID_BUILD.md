# Build APK Android (Bubblewrap + TWA)

Guia para gerar o APK do Atum a partir da PWA usando Bubblewrap.

## Pré-requisitos

- Node.js 18+
- JDK 17
- Android SDK (via [Android Studio](https://developer.android.com/studio) ou `sdkmanager`)
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) (para tunnel HTTPS local)
- PWA em URL HTTPS (use o script ou deploy em produção)

## Build via Docker Compose (recomendado)

Usa o frontend e a API já rodando em Docker. O tunnel (cloudflared) e o build (JDK 25 + Android SDK) rodam em containers. JDK e Android SDK são instalados em volumes na primeira execução e reutilizados nas próximas.

```powershell
.\scripts\android-build-docker.ps1
```

O script irá:
1. Fazer build das imagens frontend e android-build
2. Subir frontend + cloudflared (e dependências: postgres, redis, api)
3. Obter a URL do tunnel
4. Rodar bubblewrap update e build no container android-build
5. Gerar o APK em `android-twa/app/build/outputs/apk/debug/`
6. Encerrar o tunnel ao final

**Pré-requisitos:** Apenas Docker. JDK 25 e Android SDK são instalados automaticamente no container e persistidos nos volumes `android_build_jdk`, `android_build_sdk` e `android_build_bubblewrap`.

## Opção rápida: script local (sem Docker)

Para testar localmente sem Docker:

```powershell
.\scripts\android-build.ps1
```

O script irá:
1. Fazer build do frontend
2. Servir a PWA localmente
3. Expor via Cloudflare Tunnel (HTTPS)
4. Mostrar a URL e instruções para `bubblewrap init` e `bubblewrap build`

**Importante:** Mantenha o terminal aberto enquanto roda o bubblewrap em outro terminal. O tunnel Cloudflare expira quando o script encerra.

**Nota:** JDK — "Yes" para instalar; Android SDK — "No" e use `C:\Users\Caio Villela\AppData\Local\Android\Sdk`.

## Passo a passo

### 1. Instalar Bubblewrap

```bash
npm install -g @bubblewrap/cli
```

### 2. Inicializar projeto

```bash
bubblewrap init --manifest=https://SEU-DOMINIO.com/manifest.webmanifest
```

O assistente pergunta:
- **Instalar JDK?** — escolha "Yes" para instalar JDK 17+
- **Instalar Android SDK?** — escolha "No" e informe o caminho: `C:\Users\Caio Villela\AppData\Local\Android\Sdk`
- **Package name:** ex: `com.atum.media`
- **Nome do app:** Atum
- **Launcher icon:** pode usar o ícone do manifest
- **Assinatura:** debug (teste) ou release (Play Store)

### 3. Configurar minSdkVersion 28 (Android 9)

Editar `app/build.gradle` no projeto gerado:

```gradle
android {
    defaultConfig {
        minSdk 28   // Android 9+
        targetSdk 34
        // ...
    }
}
```

### 4. Build

```bash
bubblewrap build
```

Gera APK em `app/build/outputs/` (debug ou release conforme configurado).

### 5. Digital Asset Links (remover barra de endereço)

Para TWA sem barra de endereço, sirva `assetlinks.json` em:

```
https://SEU-DOMINIO.com/.well-known/assetlinks.json
```

1. Obter SHA256 do certificado:
   ```bash
   keytool -list -v -keystore seu-keystore.jks -alias seu-alias
   ```
2. Copiar `frontend/public/.well-known/assetlinks.json.example` para `assetlinks.json`
3. Substituir `REPLACE_WITH_SHA256_FROM_KEYSTORE` pelo fingerprint (formato `AA:BB:CC:...`)
4. O build do frontend copia `.well-known/` para `dist/`; o nginx já está configurado para servir

### 6. Assinatura (Play Store)

Para publicar na Play Store:
- Crie uma keystore de release
- Configure no Bubblewrap ou no `build.gradle`
- Assine o AAB antes do upload

## Estrutura gerada

```
twa-project/
├── app/
│   ├── build.gradle   # minSdk 28 aqui
│   └── src/
├── twa-manifest.json
└── package.json
```

## Referências

- [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap)
- [Trusted Web Activity](https://developer.chrome.com/docs/android/trusted-web-activity/)
- [Digital Asset Links](https://developer.android.com/training/app-links/verify-android-applinks)
