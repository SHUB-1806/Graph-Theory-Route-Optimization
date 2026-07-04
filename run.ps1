$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path (Join-Path $Root "bin\route_engine.exe"))) { & (Join-Path $Root "build.ps1") }
python (Join-Path $Root "python\city_routes_gui.py")

