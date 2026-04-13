# =============================================================================
# clean_synthetics.ps1
# Descripcion : Elimina todas las carpetas *_SYNTH_NNN (tres digitos) y su
#               contenido en las rutas de history y ticks de MT5.
#
# Uso:
#   .\scripts\clean_synthetics.ps1                               # Borra todos los simbolos
#   .\scripts\clean_synthetics.ps1 -WhatIf                      # Simulacion - todos los simbolos
#   .\scripts\clean_synthetics.ps1 -Symbol "AUDCAD.QDL"         # Borra solo ese simbolo
#   .\scripts\clean_synthetics.ps1 -Symbol "AUDCAD.QDL" -WhatIf # Simulacion - solo ese simbolo
# =============================================================================

param(
    [string]$Symbol = "",
    [switch]$WhatIf
)

$MT5_BASE = "C:\Users\Alberto Veiga\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\bases\Custom"

$targets = @(
    (Join-Path $MT5_BASE "history"),
    (Join-Path $MT5_BASE "ticks")
)

if ($Symbol -ne "") {
    $escaped = [regex]::Escape($Symbol)
    $pattern = [regex]"^${escaped}_SYNTH_\d{3}$"
    Write-Host "[INFO] Filtrando por simbolo: $Symbol"
} else {
    $pattern = [regex]'^.+_SYNTH_\d{3}$'
    Write-Host "[INFO] Sin filtro de simbolo - se procesaran todos"
}

$total = 0

foreach ($dir in $targets) {
    if (-not (Test-Path $dir)) {
        Write-Host "[WARN] No existe: $dir"
        continue
    }

    $folders = Get-ChildItem -Path $dir -Directory | Where-Object { $_.Name -match $pattern }

    if ($folders.Count -eq 0) {
        Write-Host "[INFO] Sin carpetas SYNTH en: $dir"
        continue
    }

    foreach ($folder in $folders) {
        $fullPath = $folder.FullName
        if ($WhatIf) {
            Write-Host "[WHATIF] Borraria: $fullPath"
        } else {
            Remove-Item -Path $fullPath -Recurse -Force
            Write-Host "[OK] Eliminado: $fullPath"
        }
        $total++
    }
}

if ($total -eq 0) {
    Write-Host "`n[INFO] No se encontraron carpetas. No se ha borrado nada."
} elseif ($WhatIf) {
    Write-Host "`n[WHATIF] Total carpetas que se borrarian: $total"
} else {
    Write-Host "`n[OK] Total carpetas eliminadas: $total"
}
