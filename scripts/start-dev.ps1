param(
  [int]$Port = 8000,
  [string]$BindHost = '0.0.0.0',
  [string]$EnvName = 'dify',
  [switch]$NoReload = $false,
  [string]$LogFormat = 'console',
  [string]$LogLevel = 'INFO'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# 功能: 输出信息日志并使用青色突出显示
function Write-Info($msg)  { Write-Host "[INFO] $msg"  -ForegroundColor Cyan }
# 功能: 输出完成日志并使用绿色突出显示
function Write-Ok($msg)    { Write-Host "[OK]   $msg"  -ForegroundColor Green }
# 功能: 输出警告日志并使用黄色突出显示
function Write-Warn($msg)  { Write-Host "[WARN] $msg"  -ForegroundColor Yellow }
# 功能: 输出错误日志并使用红色突出显示
function Write-Err($msg)   { Write-Host "[ERR]  $msg"  -ForegroundColor Red }

# Repo root = parent of this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir '..')
Set-Location $RepoRoot

if (-not (Test-Path 'app/main.py')) {
  Write-Err '未在仓库根目录下发现 app/main.py，请从项目根目录运行脚本或检查目录结构。'
  exit 1
}

# Apply default runtime env (non-destructive)
if (-not $env:LOG_FORMAT)         { $env:LOG_FORMAT = $LogFormat }
if (-not $env:LOG_LEVEL)          { $env:LOG_LEVEL = $LogLevel }
if (-not $env:AI_STREAM_ENABLED)  { $env:AI_STREAM_ENABLED = 'true' }
if (-not $env:PYTHONPATH)         { $env:PYTHONPATH = "$RepoRoot" }

# Show startup summary
Write-Info "工作目录: $RepoRoot"
Write-Info "环境: EnvName=$EnvName | LOG_FORMAT=$($env:LOG_FORMAT) | LOG_LEVEL=$($env:LOG_LEVEL) | AI_STREAM_ENABLED=$($env:AI_STREAM_ENABLED)"
Write-Info ("监听: http://{0}:{1} | WS: ws://{0}:{1}/service/ws | Docs: http://{0}:{1}/docs" -f $BindHost, $Port)

# Build uvicorn args
$uvArgs = @('app.main:app','--host', $BindHost, '--port', $Port)
if (-not $NoReload) { $uvArgs += '--reload' }

# 功能: 使用指定 Conda 环境运行 uvicorn，成功返回 $true，失败返回 $false
function Try-Run-Conda {
  param([string[]]$CmdArgs)
  if (-not $env:CONDA_EXE) { return $false }
  try {
    Write-Info "通过 conda run 启动 (env=$EnvName) ..."
    & $env:CONDA_EXE run -n $EnvName python -m uvicorn @CmdArgs
    return $true
  } catch {
    Write-Warn "conda run 启动失败: $($_.Exception.Message)"
    return $false
  }
}

# 功能: 使用当前 Python 解释器运行 uvicorn，成功返回 $true，失败返回 $false
function Try-Run-Python {
  param([string[]]$CmdArgs)
  try {
    Write-Info '通过本机 python 启动 ...'
    python -m uvicorn @CmdArgs
    return $true
  } catch {
    Write-Err "python 启动失败: $($_.Exception.Message)"
    return $false
  }
}

# Prefer conda run if available; fallback to python
if (-not (Try-Run-Conda -CmdArgs $uvArgs)) {
  if (-not (Try-Run-Python -CmdArgs $uvArgs)) {
    Write-Err "无法启动 uvicorn。请先确保已安装依赖并设置环境: conda activate $EnvName; pip install -r requirements.txt"
    exit 1
  }
}
