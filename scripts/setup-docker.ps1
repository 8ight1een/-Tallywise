$ErrorActionPreference = 'Stop'

$log = Join-Path $PSScriptRoot 'setup-docker.log'

function Log($message) {
    $line = "[{0:HH:mm:ss}] {1}" -f (Get-Date), $message
    Add-Content -Path $log -Value $line -Encoding utf8
    Write-Host $line
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

Set-Content -Path $log -Value '' -Encoding utf8

if (-not $isAdmin) {
    Write-Host '需要管理员权限：请右键此脚本，选择「以管理员身份运行」。'
    exit 1
}

Log '检查开始'

$features = @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')
$needReboot = $false
$changed = $false

foreach ($name in $features) {
    $feature = Get-CimInstance -ClassName Win32_OptionalFeature -Filter "Name='$name'"
    if ($null -eq $feature) {
        Log "功能 $name 查不到，跳过"
        continue
    }
    if ($feature.InstallState -eq 1) {
        Log "功能 $name 已启用"
        continue
    }
    Log "正在启用功能 $name"
    $result = Enable-WindowsOptionalFeature -Online -FeatureName $name -All -NoRestart -WarningAction SilentlyContinue
    $changed = $true
    if ($result.RestartNeeded) {
        $needReboot = $true
        Log "功能 $name 启用成功，需要重启"
    }
}

if ($changed) {
    Log 'Windows 功能已改动，必须先重启电脑，然后再运行一次本脚本'
    Log '重启命令：Restart-Computer'
    exit 2
}

Log '更新 WSL 内核'
$update = & wsl --update 2>&1 | Out-String
Log ("wsl --update 输出: " + ($update.Trim() -replace '\s+', ' '))

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($null -ne $docker) {
    Log "docker 已安装: $($docker.Source)"
} else {
    Log '通过 winget 安装 Docker Desktop'
    & winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements --disable-interactivity
    $code = $LASTEXITCODE
    Log "winget 退出码: $code"
    if ($code -ne 0) {
        Log '安装失败，请检查上面的输出'
        exit 3
    }
    Log 'Docker Desktop 安装完成'
}

Log '全部完成'
Log '下一步：重启电脑，然后从开始菜单启动 Docker Desktop，等小鲸鱼图标变绿'
exit 0
