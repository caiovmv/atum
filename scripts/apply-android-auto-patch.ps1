# Reaplica alterações de Android Auto após bubblewrap update.
# O bubblewrap update sobrescreve build.gradle e AndroidManifest.xml.
# Este script restaura as dependências e o AtumMediaBrowserService.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AndroidDir = Join-Path $ProjectRoot "android-twa"
$BuildGradle = Join-Path $AndroidDir "app\build.gradle"
$Manifest = Join-Path $AndroidDir "app\src\main\AndroidManifest.xml"

if (-not (Test-Path $BuildGradle)) {
    Write-Error "build.gradle nao encontrado: $BuildGradle"
}
if (-not (Test-Path $Manifest)) {
    Write-Error "AndroidManifest.xml nao encontrado: $Manifest"
}

Write-Host "Aplicando patch Android Auto..." -ForegroundColor Cyan

# 1. build.gradle: adicionar dependencias se nao existirem
$gradleContent = Get-Content $BuildGradle -Raw

if ($gradleContent -notmatch "androidx\.media:media") {
    $insert = @"

    implementation 'androidx.media:media:1.7.0'
    implementation 'com.google.android.exoplayer:exoplayer:2.19.1'
    implementation 'com.squareup.okhttp3:okhttp:4.12.0'
"@
    $gradleContent = $gradleContent -replace "(implementation 'com\.google\.androidbrowserhelper:androidbrowserhelper:[^']+')\r?\n", "`$1$insert`n"
    Set-Content $BuildGradle $gradleContent -NoNewline
    Write-Host "  build.gradle: dependencias Android Auto adicionadas" -ForegroundColor Green
} else {
    Write-Host "  build.gradle: dependencias ja presentes" -ForegroundColor Gray
}

# 2. AndroidManifest.xml: adicionar AtumMediaBrowserService se nao existir
$manifestContent = Get-Content $Manifest -Raw
$mediaServiceBlock = @'
        <service
            android:name=".AtumMediaBrowserService"
            android:exported="true">
            <intent-filter>
                <action android:name="android.media.browse.MediaBrowserService" />
            </intent-filter>
        </service>

'@

if ($manifestContent -notmatch "AtumMediaBrowserService") {
    $manifestContent = $manifestContent -replace '(\s+<service\s+android:name="\.DelegationService")', "$mediaServiceBlock`$1"
    Set-Content $Manifest $manifestContent -NoNewline
    Write-Host "  AndroidManifest: AtumMediaBrowserService adicionado" -ForegroundColor Green
} else {
    Write-Host "  AndroidManifest: AtumMediaBrowserService ja presente" -ForegroundColor Gray
}

Write-Host "Patch Android Auto aplicado." -ForegroundColor Cyan
