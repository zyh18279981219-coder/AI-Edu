$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$MysqlBase = "D:\develop\mysql-8.0.31-winx64"
$InstanceBase = Join-Path $ProjectRoot "output\mysql_design_instance"
$DataDir = Join-Path $InstanceBase "data"
$TmpDir = Join-Path $InstanceBase "tmp"
$IniPath = Join-Path $InstanceBase "my.ini"
$Port = 3307

New-Item -ItemType Directory -Force -Path $InstanceBase, $TmpDir | Out-Null

if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    & (Join-Path $MysqlBase "bin\mysqld.exe") `
        --initialize-insecure `
        --basedir=$MysqlBase `
        --datadir=$DataDir `
        --console
}

@"
[mysqld]
basedir=D:/develop/mysql-8.0.31-winx64
datadir=D:/pythonFile/AI-Education2/output/mysql_design_instance/data
port=$Port
bind-address=127.0.0.1
character-set-server=utf8mb4
collation-server=utf8mb4_0900_ai_ci
lower_case_table_names=1
max_allowed_packet=256M
pid-file=D:/pythonFile/AI-Education2/output/mysql_design_instance/mysql.pid
log-error=D:/pythonFile/AI-Education2/output/mysql_design_instance/mysql.log
tmpdir=D:/pythonFile/AI-Education2/output/mysql_design_instance/tmp
"@ | Set-Content -LiteralPath $IniPath -Encoding ASCII

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $existing) {
    Start-Process -FilePath (Join-Path $MysqlBase "bin\mysqld.exe") -ArgumentList "--defaults-file=$IniPath" -WindowStyle Hidden
}

$MysqlAdmin = Join-Path $MysqlBase "bin\mysqladmin.exe"
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $MysqlAdmin --host=127.0.0.1 --port=$Port --user=root --password= ping *> $null
    $pingExitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($pingExitCode -eq 0) {
        Write-Output "Local design MySQL is running at 127.0.0.1:$Port"
        exit 0
    }
}

Write-Error "Failed to start local design MySQL. Check $InstanceBase\mysql.log"
