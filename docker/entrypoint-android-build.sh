#!/bin/sh
set -e

ANDROID_CMDLINE_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"

# Usar JDK 17 do sistema (instalado no Dockerfile; Gradle nao suporta JDK 25)
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
[ ! -d "$JAVA_HOME" ] && JAVA_HOME=$(ls -d /usr/lib/jvm/java-17-openjdk-* 2>/dev/null | head -1)

# Instalar Android SDK em /opt/android-sdk se volume vazio
if [ ! -f /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager ]; then
    echo "Instalando Android SDK em /opt/android-sdk..."
    mkdir -p /opt/android-sdk/cmdline-tools
    curl -fsSL "$ANDROID_CMDLINE_URL" -o /tmp/cmdline-tools.zip
    unzip -q /tmp/cmdline-tools.zip -d /tmp/
    mv /tmp/cmdline-tools /opt/android-sdk/cmdline-tools/latest
    rm /tmp/cmdline-tools.zip

    echo "Instalando plataformas e build-tools..."
    yes | /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk \
        "platform-tools" \
        "platforms;android-34" \
        "build-tools;34.0.0" \
        > /dev/null 2>&1
    echo "Android SDK instalado."
fi

# Bubblewrap espera estrutura antiga (tools/bin); cmdline-tools usa cmdline-tools/latest/bin
if [ ! -d /opt/android-sdk/tools ]; then
    ln -sf cmdline-tools/latest /opt/android-sdk/tools
fi

export JAVA_HOME
export ANDROID_HOME=/opt/android-sdk
export PATH="${JAVA_HOME}/bin:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${PATH}"

# Config bubblewrap para automação (evita prompts interativos)
mkdir -p /root/.bubblewrap
printf '%s\n' "{\"jdkPath\":\"$JAVA_HOME\",\"androidSdkPath\":\"/opt/android-sdk\"}" > /root/.bubblewrap/config.json

exec "$@"
