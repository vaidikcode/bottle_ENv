# OpenEnv Submission Validator (PowerShell)
# Usage:
#   .\validate-submission.ps1 <ping_url> [repo_dir]
#
# Arguments:
#   ping_url   Your HuggingFace Space URL (e.g. https://your-space.hf.space)
#   repo_dir   Path to your repo (default: current directory)

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PingUrl,
    [Parameter(Mandatory = $false, Position = 1)]
    [string]$RepoDir = "."
)

$ErrorActionPreference = 'Stop'
$DOCKER_BUILD_TIMEOUT = 600
$pass = 0

function Log($msg) {
    Write-Host ("[" + (Get-Date -Format "HH:mm:ss") + "] $msg")
}
function Pass($msg) {
    Log "`e[32mPASSED`e[0m -- $msg"
    $global:pass++
}
function Fail($msg) {
    Log "`e[31mFAILED`e[0m -- $msg"
}
function Hint($msg) {
    Write-Host "  `e[33mHint:`e[0m $msg"
}
function Stop-At($step) {
    Write-Host "\n`e[31m`e[1mValidation stopped at $step. Fix the above before continuing.`e[0m"
    exit 1
}

Write-Host "\n`e[1m========================================`e[0m"
Write-Host "`e[1m  OpenEnv Submission Validator`e[0m"
Write-Host "`e[1m========================================`e[0m"
Log "Repo:     $RepoDir"
Log "Ping URL: $PingUrl"
Write-Host ""

# Step 1: Ping HF Space
Log "`e[1mStep 1/3: Pinging HF Space`e[0m ($PingUrl/reset) ..."
try {
    $response = Invoke-WebRequest -Uri "$PingUrl/reset" -Method POST -ContentType 'application/json' -Body '{}' -TimeoutSec 30 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Pass "HF Space is live and responds to /reset"
    } else {
        Fail "HF Space /reset returned HTTP $($response.StatusCode) (expected 200)"
        Hint "Make sure your Space is running and the URL is correct."
        Hint "Try opening $PingUrl in your browser first."
        Stop-At "Step 1"
    }
} catch {
    Fail "HF Space not reachable (connection failed or timed out)"
    Hint "Check your network connection and that the Space is running."
    Hint "Try: Invoke-WebRequest -Uri $PingUrl/reset -Method POST -ContentType 'application/json' -Body '{}'"
    Stop-At "Step 1"
}

# Step 2: Docker build
Log "`e[1mStep 2/3: Running docker build`e[0m ..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "docker command not found"
    Hint "Install Docker: https://docs.docker.com/get-docker/"
    Stop-At "Step 2"
}

$dockerfileRoot = Join-Path $RepoDir 'Dockerfile'
$dockerfileServer = Join-Path $RepoDir 'server/Dockerfile'
if (Test-Path $dockerfileRoot) {
    $dockerContext = $RepoDir
} elseif (Test-Path $dockerfileServer) {
    $dockerContext = Join-Path $RepoDir 'server'
} else {
    Fail "No Dockerfile found in repo root or server/ directory"
    Stop-At "Step 2"
}
Log "  Found Dockerfile in $dockerContext"

$buildOk = $false
try {
    $buildJob = Start-Job -ScriptBlock { param($ctx, $timeout) docker build $ctx } -ArgumentList $dockerContext, $DOCKER_BUILD_TIMEOUT
    if (Wait-Job $buildJob -Timeout $DOCKER_BUILD_TIMEOUT) {
        $buildOutput = Receive-Job $buildJob
        $buildOk = $true
    } else {
        Stop-Job $buildJob | Out-Null
        $buildOutput = "Docker build timed out after $DOCKER_BUILD_TIMEOUT seconds."
    }
} catch {
    $buildOutput = $_.Exception.Message
}

if ($buildOk) {
    Pass "Docker build succeeded"
} else {
    Fail "Docker build failed (timeout=${DOCKER_BUILD_TIMEOUT}s)"
    $buildOutput | Select-Object -Last 20 | ForEach-Object { Write-Host $_ }
    Stop-At "Step 2"
}

# Step 3: openenv validate
Log "`e[1mStep 3/3: Running openenv validate`e[0m ..."
if (-not (Get-Command openenv -ErrorAction SilentlyContinue)) {
    Fail "openenv command not found"
    Hint "Install it: pip install openenv-core"
    Stop-At "Step 3"
}

$validateOk = $false
try {
    Push-Location $RepoDir
    $validateOutput = openenv validate 2>&1
    if ($LASTEXITCODE -eq 0) {
        $validateOk = $true
    }
    Pop-Location
} catch {
    $validateOutput = $_.Exception.Message
    Pop-Location
}

if ($validateOk) {
    Pass "openenv validate passed"
    if ($validateOutput) { Log "  $validateOutput" }
} else {
    Fail "openenv validate failed"
    $validateOutput | ForEach-Object { Write-Host $_ }
    Stop-At "Step 3"
}

Write-Host "\n`e[1m========================================`e[0m"
Write-Host "`e[32m`e[1m  All 3/3 checks passed!`e[0m"
Write-Host "`e[32m`e[1m  Your submission is ready to submit.`e[0m"
Write-Host "`e[1m========================================`e[0m\n"
exit 0
