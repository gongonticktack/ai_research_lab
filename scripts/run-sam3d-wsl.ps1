$ErrorActionPreference = 'Stop'
$labRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$windowsPath = $labRoot.Replace('\', '/')
$converted = & wsl -d Ubuntu-22.04 -- wslpath -u $windowsPath
if ($LASTEXITCODE -ne 0 -or -not $converted) { throw 'Cannot convert project path for WSL.' }
$linuxRoot = $converted.Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot start Ubuntu-22.04. See environment setup in README.' }
& wsl -d Ubuntu-22.04 --cd $linuxRoot -- bash scripts/run-sam3d.sh
exit $LASTEXITCODE
