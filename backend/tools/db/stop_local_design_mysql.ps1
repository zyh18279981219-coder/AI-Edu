$ErrorActionPreference = "Stop"

$MysqlBase = "D:\develop\mysql-8.0.31-winx64"
$Port = 3307
$MysqlAdmin = Join-Path $MysqlBase "bin\mysqladmin.exe"

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $existing) {
    Write-Output "Local design MySQL is not running on 127.0.0.1:$Port"
    exit 0
}

$oldPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $MysqlAdmin --host=127.0.0.1 --port=$Port --user=root --password= shutdown *> $null
$shutdownExitCode = $LASTEXITCODE
$ErrorActionPreference = $oldPreference
if ($shutdownExitCode -ne 0) {
    Write-Error "Failed to stop local design MySQL."
}
Write-Output "Local design MySQL stopped."
