[CmdletBinding()]
param(
    [switch]$SkipFirefoxTrust
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$certificateDirectory = Join-Path $repoRoot "frontend\certificates"
$certificatePath = Join-Path $certificateDirectory "localhost.pem"
$privateKeyPath = Join-Path $certificateDirectory "localhost-key.pem"

function Resolve-Mkcert {
    $command = Get-Command mkcert -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $wingetLink = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\mkcert.exe"
    if (Test-Path -LiteralPath $wingetLink) {
        return $wingetLink
    }

    $wingetPackages = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path -LiteralPath $wingetPackages) {
        $packageBinary = Get-ChildItem -LiteralPath $wingetPackages -Recurse -Filter "mkcert.exe" -File -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName
        if ($packageBinary) {
            return $packageBinary
        }
    }

    throw "mkcert is not installed. Run: winget install --id FiloSottile.mkcert -e"
}

function Enable-FirefoxEnterpriseRoots {
    $profilesRoot = Join-Path $env:APPDATA "Mozilla\Firefox\Profiles"
    if (-not (Test-Path -LiteralPath $profilesRoot)) {
        Write-Host "[https] Firefox profile directory was not found; skipping Firefox trust preference."
        return
    }

    $preference = 'user_pref("security.enterprise_roots.enabled", true);'
    $profiles = Get-ChildItem -LiteralPath $profilesRoot -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "prefs.js") }

    foreach ($profile in $profiles) {
        $userJsPath = Join-Path $profile.FullName "user.js"
        $existingLines = if (Test-Path -LiteralPath $userJsPath) {
            Get-Content -LiteralPath $userJsPath
        } else {
            @()
        }
        $retainedLines = @($existingLines | Where-Object { $_ -notmatch 'security\.enterprise_roots\.enabled' })
        $updatedLines = @($retainedLines + $preference)
        [System.IO.File]::WriteAllLines($userJsPath, $updatedLines, [System.Text.UTF8Encoding]::new($false))
        Write-Host "[https] Enabled Windows trusted roots for Firefox profile: $($profile.Name)"
    }
}

$mkcert = Resolve-Mkcert
New-Item -ItemType Directory -Force -Path $certificateDirectory | Out-Null

Write-Host "[https] Installing the local development CA in the current user's trust store..."
& $mkcert -install
if ($LASTEXITCODE -ne 0) {
    throw "mkcert could not install the local development CA."
}

$caRoot = ((& $mkcert -CAROOT | Select-Object -Last 1) -as [string]).Trim()
$caCertificate = Join-Path $caRoot "rootCA.pem"
if (-not (Test-Path -LiteralPath $caCertificate)) {
    throw "mkcert root certificate was not found at $caCertificate"
}

# Explicitly use the current-user store. This works without changing the
# machine-wide store and is the store Firefox reads when enterprise roots are enabled.
certutil -user -addstore -f Root $caCertificate | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "The mkcert CA could not be added to the current user's trusted root store."
}

Write-Host "[https] Generating a certificate for localhost, 127.0.0.1, and ::1..."
& $mkcert -cert-file $certificatePath -key-file $privateKeyPath localhost 127.0.0.1 ::1
if ($LASTEXITCODE -ne 0) {
    throw "mkcert could not generate the localhost certificate."
}

if (-not $SkipFirefoxTrust) {
    Enable-FirefoxEnterpriseRoots
}

Write-Host "[https] Trusted certificate ready: $certificatePath"
Write-Host "[https] Restart Firefox completely before opening https://127.0.0.1:3000."
