<# Verify the current Phase 4 release against isolated PostgreSQL; always scoped cleanup. #>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskArtifacts = Join-Path $taskRoot 'artifacts/local/phase4'
$taskCache = Join-Path $taskArtifacts ('pytest-cache-' + [guid]::NewGuid().ToString('N'))
$taskProject = 'parallax-risk-phase4-verification'
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
$taskDocker = @('--config', (Join-Path $taskRoot '.docker-local'))
$taskCompose = @('compose', '-p', $taskProject, '-f', 'docker-compose.yml', '-f', 'scripts/compose.verify.yml')
$taskVariables = @('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'PARALLAX_DATABASE_URL', 'PARALLAX_TEST_DATABASE_URL')
$taskOriginalEnvironment = @{}
foreach ($taskName in $taskVariables) {
    $taskOriginalEnvironment[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process')
}
New-Item -ItemType Directory -Force -Path $taskArtifacts | Out-Null
'Verification in progress; no successful result is recorded yet.' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskArtifacts 'verification-result.txt')

function Invoke-TaskCheck {
    param([string]$Executable, [string[]]$Arguments, [string]$Log)
    $taskPreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $taskArtifacts $Log)
    $taskExit = $LASTEXITCODE
    $ErrorActionPreference = $taskPreviousPreference
    if ($taskExit -ne 0) { throw "Verification command failed ($taskExit); see $Log" }
}

Push-Location $taskRoot
try {
    $env:POSTGRES_USER = 'phase4_test'
    $env:POSTGRES_PASSWORD = 'phase4_ephemeral_only'
    $env:POSTGRES_DB = 'parallax_risk_test'
    $env:PARALLAX_DATABASE_URL = 'postgresql+psycopg://phase4_test:phase4_ephemeral_only@postgres:5432/parallax_risk_test'
    $env:PARALLAX_TEST_DATABASE_URL = 'postgresql+psycopg://phase4_test:phase4_ephemeral_only@127.0.0.1:55432/parallax_risk_test'
    Invoke-TaskCheck 'docker' ($taskDocker + @('ps', '-a', '--format', '{{.ID}} {{.Names}} {{.Label "com.docker.compose.project"}}')) 'docker-before.log'
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('config', '--quiet')) 'compose-config.log'
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('up', '--build', '--wait', '--wait-timeout', '180')) 'compose-start.log'
    foreach ($taskEndpoint in @('health', 'ready', 'version')) {
        $taskResponse = Invoke-RestMethod -Uri "http://127.0.0.1:58000/$taskEndpoint" -TimeoutSec 15
        $taskResponse | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskArtifacts "$taskEndpoint.json")
        if ($taskEndpoint -eq 'health' -and $taskResponse.status -ne 'ok') { throw 'Liveness failed' }
        if ($taskEndpoint -eq 'ready' -and ($taskResponse.status -ne 'ready' -or $taskResponse.database -ne 'connected')) { throw 'Readiness failed' }
        if ($taskEndpoint -eq 'version' -and ($taskResponse.name -ne 'Parallax Risk' -or $taskResponse.version -ne '0.4.0' -or $taskResponse.phase -ne 4)) { throw 'Version mismatch' }
    }
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('exec', '-T', 'api', 'parallax-risk', 'check-db')) 'container-database.log'
    Invoke-TaskCheck $taskPython @('-m', 'pytest', '-q', '-o', "cache_dir=$taskCache") 'pytest-windows.log'
    $taskLinuxCode = @'
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '-r', 'requirements-dev.lock'], check=True)
subprocess.run([sys.executable, '-m', 'pytest', '-q', '-o', 'cache_dir=/tmp/pytest_cache', '-o', 'addopts=-ra --strict-markers --cov=parallax_risk --cov-report=term --cov-fail-under=95'], check=True)
'@
    $taskRun = @('run', '--rm', '--name', 'parallax-risk-phase4-tests', '--user', '0',
        '--label', "com.docker.compose.project=$taskProject",
        '--label', 'io.parallax-risk.project=parallax-risk',
        '--label', 'io.parallax-risk.purpose=verification',
        '--label', "io.parallax-risk.workspace=$taskRoot",
        '--network', "${taskProject}_default", '--mount', "type=bind,source=$taskRoot,target=/workspace,readonly",
        '--workdir', '/workspace', '--env', 'COVERAGE_FILE=/tmp/.coverage',
        '--env', 'HYPOTHESIS_STORAGE_DIRECTORY=/tmp/hypothesis',
        '--env', 'PARALLAX_TEST_DATABASE_URL=postgresql+psycopg://phase4_test:phase4_ephemeral_only@postgres:5432/parallax_risk_test',
        'parallax-risk:0.4.0', 'python', '-c', $taskLinuxCode)
    Invoke-TaskCheck 'docker' ($taskDocker + $taskRun) 'pytest-linux.log'
    Invoke-TaskCheck 'docker' ($taskDocker + @('image', 'inspect', 'parallax-risk:0.4.0', '--format', '{{.Id}}')) 'image-identity.log'
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('exec', '-T', 'api', 'id', '-u')) 'runtime-user.log'
    'All Phase 4 Docker/database checks passed.' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskArtifacts 'verification-result.txt')
} catch {
    'Verification failed; inspect the command logs.' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskArtifacts 'verification-result.txt')
    throw
} finally {
    try {
        & (Join-Path $taskRoot 'scripts/cleanup_docker.ps1') -Phase 4 -Apply | Tee-Object -FilePath (Join-Path $taskArtifacts 'cleanup.log')
        Invoke-TaskCheck 'docker' ($taskDocker + @('ps', '-a', '--format', '{{.ID}} {{.Names}} {{.Label "com.docker.compose.project"}}')) 'docker-after.log'
    } finally {
        foreach ($taskName in $taskVariables) {
            [Environment]::SetEnvironmentVariable($taskName, $taskOriginalEnvironment[$taskName], 'Process')
        }
        Pop-Location
    }
}
