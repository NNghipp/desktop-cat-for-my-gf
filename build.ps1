$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $catPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $catPython)) {
        throw 'Chưa có môi trường .venv. Hãy làm theo README.md trước.'
    }
    & $catPython tools/build_exe.py
    if ($LASTEXITCODE -ne 0) { throw 'Kiểm thử hoặc đóng gói EXE thất bại.' }
    Write-Host 'Đã tạo dist\DesktopCat.exe'
} finally {
    Pop-Location
}
