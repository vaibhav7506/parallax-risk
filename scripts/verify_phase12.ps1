<# Verify the current Phase 12 release against isolated PostgreSQL; always scoped cleanup. #>
[CmdletBinding()]
param([switch]$Focused)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskArtifacts = Join-Path $taskRoot 'artifacts/local/phase12'
$taskCache = Join-Path $taskArtifacts ('pytest-cache-' + [guid]::NewGuid().ToString('N'))
$taskTemp = Join-Path $taskArtifacts ('pytest-temp-' + [guid]::NewGuid().ToString('N'))
$taskProject = 'parallax-risk-phase12-verification'
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
$taskDocker = @('--config', (Join-Path $taskRoot '.docker-local'))
$taskCompose = @('compose', '-p', $taskProject, '-f', 'docker-compose.yml', '-f', 'scripts/compose.verify.yml')
$taskVariables = @('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'PARALLAX_DATABASE_URL', 'PARALLAX_TEST_DATABASE_URL', 'PARALLAX_SERVICE_CREDENTIALS')
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
    $env:POSTGRES_USER = 'phase12_test'
    $env:POSTGRES_PASSWORD = 'phase12_ephemeral_only'
    $env:POSTGRES_DB = 'parallax_risk_test'
    $env:PARALLAX_DATABASE_URL = 'postgresql+psycopg://phase12_test:phase12_ephemeral_only@postgres:5432/parallax_risk_test'
    $env:PARALLAX_TEST_DATABASE_URL = 'postgresql+psycopg://phase12_test:phase12_ephemeral_only@127.0.0.1:55432/parallax_risk_test'
    $taskToken = 'synthetic-phase12-verification-credential-' + 'x' * 32
    $taskDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::ASCII.GetBytes($taskToken))).ToLowerInvariant()
    $taskCredentialFile = Join-Path $taskArtifacts 'ephemeral-api-key.txt'
    [IO.File]::WriteAllText($taskCredentialFile, $taskToken)
    $env:PARALLAX_SERVICE_CREDENTIALS = '[{"sha256":"PLACEHOLDER_DIGEST","subject":"verification","roles":["reader","analyst","validator","approver","operator"]}]'.Replace('PLACEHOLDER_DIGEST', $taskDigest)
    Invoke-TaskCheck 'docker' ($taskDocker + @('ps', '-a', '--format', '{{.ID}} {{.Names}} {{.Label "com.docker.compose.project"}}')) 'docker-before.log'
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('config', '--quiet')) 'compose-config.log'
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('up', '--wait', '--wait-timeout', '180', 'postgres')) 'postgres-start.log'
    $taskApiUrl = $env:PARALLAX_DATABASE_URL
    $env:PARALLAX_DATABASE_URL = $env:PARALLAX_TEST_DATABASE_URL
    Invoke-TaskCheck $taskPython @('scripts/migrate_governance.py') 'migration-before-api.log'
    $env:PARALLAX_DATABASE_URL = $taskApiUrl
    if ($Focused) {
        Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('up', '--wait', '--wait-timeout', '180', 'postgres')) 'focused-compose-start.log'
    } else {
        Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('up', '--build', '--wait', '--wait-timeout', '180')) 'compose-start.log'
    }
    if (-not $Focused) {
    foreach ($taskEndpoint in @('health', 'ready', 'version')) {
        $taskResponse = Invoke-RestMethod -Uri "http://127.0.0.1:58000/$taskEndpoint" -TimeoutSec 15
        $taskResponse | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskArtifacts "$taskEndpoint.json")
        if ($taskEndpoint -eq 'health' -and $taskResponse.status -ne 'ok') { throw 'Liveness failed' }
        if ($taskEndpoint -eq 'ready' -and ($taskResponse.status -ne 'ready' -or $taskResponse.database -ne 'connected')) { throw 'Readiness failed' }
        if ($taskEndpoint -eq 'version' -and ($taskResponse.name -ne 'Parallax Risk' -or $taskResponse.version -ne '0.12.0' -or $taskResponse.phase -ne 12)) { throw 'Version mismatch' }
    }
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('exec', '-T', 'api', 'parallax-risk', 'check-db')) 'container-database.log'
    Invoke-TaskCheck $taskPython @('scripts/demo_service.py', '--server', 'http://127.0.0.1:58000', '--credential-file', $taskCredentialFile, '--subject', 'verification') 'http-demo.log'
    Invoke-TaskCheck (Join-Path $taskRoot '.venv/Scripts/parallax-risk.exe') @('xva','--server','http://127.0.0.1:58000','--credential-file',$taskCredentialFile,'--input',(Join-Path $taskArtifacts 'demo/xva-input.json'),'--idempotency-key','verification-cli-replay','--wait-seconds','180') 'cli-xva.log'
    Invoke-TaskCheck (Join-Path $taskRoot '.venv/Scripts/parallax-risk.exe') @('query','--server','http://127.0.0.1:58000','--credential-file',$taskCredentialFile,'--path','/v1/governance/model','--limit','2') 'cli-governance.log'
    $taskHashCode = 'import hashlib,json,pathlib,parallax_risk; p=pathlib.Path(parallax_risk.__file__).parent; print(json.dumps({"src/parallax_risk/"+f.relative_to(p).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob("*")) if f.is_file() and (f.suffix==".py" or f.name=="py.typed")},sort_keys=True))'
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('exec', '-T', 'api', 'python', '-c', $taskHashCode)) 'image-source-hashes.json'
    }
    if ($Focused) {
        Invoke-TaskCheck $taskPython @('-m', 'pytest', 'tests/unit/test_service_wire.py', 'tests/integration/test_service_postgres.py', 'tests/integration/test_architecture.py', '-q', '--no-cov', '--tb=short', '--basetemp', $taskTemp, '-o', "cache_dir=$taskCache") 'focused-postgres.log'
    } else {
    Invoke-TaskCheck $taskPython @('-m', 'pytest' , '-q', '--basetemp', $taskTemp, '-o', "cache_dir=$taskCache") 'pytest-windows.log'
    Invoke-TaskCheck $taskPython @('-m', 'coverage', 'json', '-o', (Join-Path $taskArtifacts 'coverage-windows.json')) 'coverage-windows.log'
    $taskLinuxCode = @'
import subprocess, sys, json, pathlib
subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '-r', 'requirements-dev.lock'], check=True)
subprocess.run([sys.executable, '-m', 'pytest', '-q', '-o', 'cache_dir=/tmp/pytest_cache', '-o', 'addopts=-ra --strict-markers --cov=parallax_risk --cov-report=term --cov-report=json:/tmp/phase12-coverage.json --cov-fail-under=95'], check=True)
print('PARALLAX_COVERAGE_TOTALS='+json.dumps(json.loads(pathlib.Path('/tmp/phase12-coverage.json').read_text())['totals'],sort_keys=True))
'@
    $taskRun = @('run', '--rm', '--name', 'parallax-risk-phase12-tests', '--user', '0',
        '--label', "com.docker.compose.project=$taskProject",
        '--label', 'io.parallax-risk.project=parallax-risk',
        '--label', 'io.parallax-risk.purpose=verification',
        '--label', "io.parallax-risk.workspace=$taskRoot",
        '--network', "${taskProject}_default", '--mount', "type=bind,source=$taskRoot,target=/workspace,readonly",
        '--workdir', '/workspace', '--env', 'COVERAGE_FILE=/tmp/.coverage',
        '--env', 'HYPOTHESIS_STORAGE_DIRECTORY=/tmp/hypothesis',
        '--env', 'PARALLAX_TEST_DATABASE_URL=postgresql+psycopg://phase12_test:phase12_ephemeral_only@postgres:5432/parallax_risk_test',
        'parallax-risk:0.12.0', 'python', '-c', $taskLinuxCode)
    Invoke-TaskCheck 'docker' ($taskDocker + $taskRun) 'pytest-linux.log'
    Invoke-TaskCheck 'docker' ($taskDocker + @('image', 'inspect', 'parallax-risk:0.12.0', '--format', '{{.Id}}')) 'image-identity.log'
    Invoke-TaskCheck 'docker' ($taskDocker + $taskCompose + @('exec', '-T', 'api', 'id', '-u')) 'runtime-user.log'
    }
    $env:PARALLAX_DATABASE_URL = $env:PARALLAX_TEST_DATABASE_URL
    Invoke-TaskCheck $taskPython @('scripts/migrate_governance.py') 'migration-demo.log'

    'All requested Phase 12 Docker/database checks passed.' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskArtifacts 'verification-result.txt')
} catch {
    'Verification failed; inspect the command logs.' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskArtifacts 'verification-result.txt')
    throw
} finally {
    try {
        & (Join-Path $taskRoot 'scripts/cleanup_docker.ps1') -Phase 12 -Apply | Tee-Object -FilePath (Join-Path $taskArtifacts 'cleanup.log')
        Invoke-TaskCheck 'docker' ($taskDocker + @('ps', '-a', '--format', '{{.ID}} {{.Names}} {{.Label "com.docker.compose.project"}}')) 'docker-after.log'
    } finally {
        if (Test-Path -LiteralPath $taskCredentialFile) { Remove-Item -LiteralPath $taskCredentialFile }
        foreach ($taskName in $taskVariables) {
            [Environment]::SetEnvironmentVariable($taskName, $taskOriginalEnvironment[$taskName], 'Process')
        }
        Pop-Location
    }
}
