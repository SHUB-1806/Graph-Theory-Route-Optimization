$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Bin = Join-Path $Root "bin"
$Data = Join-Path $Root "data"
New-Item -ItemType Directory -Force -Path $Bin, $Data | Out-Null

Write-Host "Building the C++ route engine..." -ForegroundColor Cyan
g++ -std=c++11 -O2 -Wall -Wextra (Join-Path $Root "cpp\route_engine.cpp") -o (Join-Path $Bin "route_engine.exe")
if ($LASTEXITCODE -ne 0) { throw "C++ compilation failed." }

Write-Host "Generating the deterministic 500-city network..." -ForegroundColor Cyan
& (Join-Path $Bin "route_engine.exe") generate $Data 500 42
if ($LASTEXITCODE -ne 0) { throw "Graph generation failed." }
Write-Host "Build complete. Run .\run.ps1" -ForegroundColor Green

