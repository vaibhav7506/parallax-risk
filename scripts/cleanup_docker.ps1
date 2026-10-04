<#
Inventory or remove one disposable Parallax Risk phase-verification stack.
Release images, build cache, normal project services and persistent data are retained.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 12)]
    [int]$Phase,
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskProject = "parallax-risk-phase$Phase-verification"
$taskDockerPrefix = @('--config', (Join-Path $taskRoot '.docker-local'))

function Invoke-TaskDocker {
    param([string[]]$Arguments)
    $taskLines = @(& docker @taskDockerPrefix @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: $($Arguments[0]) $($Arguments[1])"
    }
    return $taskLines
}

function Get-TaskLabel {
    param($Labels, [string]$Key)
    if ($null -eq $Labels) { return $null }
    $taskProperty = $Labels.PSObject.Properties[$Key]
    if ($null -eq $taskProperty) { return $null }
    return [string]$taskProperty.Value
}

$taskContainers = @()
foreach ($taskId in @(Invoke-TaskDocker -Arguments @('ps', '-aq', '--filter', "label=com.docker.compose.project=$taskProject"))) {
    $taskContainer = (Invoke-TaskDocker -Arguments @('container', 'inspect', $taskId) | ConvertFrom-Json)[0]
    $taskLabels = $taskContainer.Config.Labels
    $taskWorkingDirectory = Get-TaskLabel $taskLabels 'com.docker.compose.project.working_dir'
    if ($null -eq $taskWorkingDirectory) {
        if ((Get-TaskLabel $taskLabels 'io.parallax-risk.project') -ne 'parallax-risk' -or
            (Get-TaskLabel $taskLabels 'io.parallax-risk.purpose') -ne 'verification') {
            throw "Unproven verification ownership; retained container $taskId"
        }
        $taskWorkingDirectory = Get-TaskLabel $taskLabels 'io.parallax-risk.workspace'
    }
    if ([string]::IsNullOrWhiteSpace($taskWorkingDirectory) -or
        -not [string]::Equals([IO.Path]::GetFullPath($taskWorkingDirectory), $taskRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Workspace ownership mismatch; retained container $taskId"
    }
    $taskContainers += $taskContainer
}
$taskContainerIds = @($taskContainers | ForEach-Object { $_.Id })

$taskNetworks = @()
foreach ($taskId in @(Invoke-TaskDocker -Arguments @('network', 'ls', '-q', '--filter', "label=com.docker.compose.project=$taskProject"))) {
    $taskNetwork = (Invoke-TaskDocker -Arguments @('network', 'inspect', $taskId) | ConvertFrom-Json)[0]
    if ((Get-TaskLabel $taskNetwork.Labels 'com.docker.compose.network') -ne 'default') {
        throw "Unknown verification network purpose; retained $taskId"
    }
    foreach ($taskAttachment in $taskNetwork.Containers.PSObject.Properties) {
        if ($taskAttachment.Name -notin $taskContainerIds) {
            throw "Network has an unowned attachment; retained network $taskId"
        }
    }
    $taskNetworks += $taskNetwork
}

$taskVolumes = @()
foreach ($taskName in @(Invoke-TaskDocker -Arguments @('volume', 'ls', '-q', '--filter', "label=com.docker.compose.project=$taskProject"))) {
    $taskVolume = (Invoke-TaskDocker -Arguments @('volume', 'inspect', $taskName) | ConvertFrom-Json)[0]
    if ((Get-TaskLabel $taskVolume.Labels 'com.docker.compose.volume') -ne 'postgres_data') {
        throw "Unknown verification volume purpose; retained $taskName"
    }
    foreach ($taskUser in @(Invoke-TaskDocker -Arguments @('ps', '-aq', '--no-trunc', '--filter', "volume=$taskName"))) {
        if ($taskUser -notin $taskContainerIds) {
            throw "Volume is used by an unowned container; retained $taskName"
        }
    }
    $taskVolumes += $taskVolume
}

[pscustomobject]@{
    project = $taskProject
    mode = $(if ($Apply) { 'apply' } else { 'preview' })
    containers = @($taskContainers | ForEach-Object { $_.Name.TrimStart('/') })
    networks = @($taskNetworks | ForEach-Object { $_.Name })
    disposable_volumes = @($taskVolumes | ForEach-Object { $_.Name })
    images = 'retained: useful release/rollback images and shared cache'
} | ConvertTo-Json -Depth 4

if ($Apply) {
    # Ownership of all candidates is checked before the first mutation.
    foreach ($taskContainer in $taskContainers) {
        if ($taskContainer.State.Running) {
            Invoke-TaskDocker -Arguments @('container', 'stop', $taskContainer.Id) | Out-Null
        }
        Invoke-TaskDocker -Arguments @('container', 'rm', $taskContainer.Id) | Out-Null
    }
    foreach ($taskNetwork in $taskNetworks) {
        Invoke-TaskDocker -Arguments @('network', 'rm', $taskNetwork.Id) | Out-Null
    }
    foreach ($taskVolume in $taskVolumes) {
        Invoke-TaskDocker -Arguments @('volume', 'rm', $taskVolume.Name) | Out-Null
    }
}
