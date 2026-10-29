<#
.SYNOPSIS
    Genera el Word del informe de ETL y EDA en DocumentosFInales sin sobrescribir archivos (spec 002, T044).
.EXAMPLE
    scripts\informe\generar_word.ps1 -Fecha 2026-10-27
#>
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{4}-\d{2}-\d{2}$')][string]$Fecha,
    [string]$Destino = (Join-Path $PSScriptRoot '..\..\..\DocumentosFInales'),
    [string]$Pandoc = 'pandoc',
    [string]$Python = (Join-Path $PSScriptRoot '..\..\.venv-ml\Scripts\python.exe')
)
$ErrorActionPreference = 'Stop'
$raiz = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$md = Join-Path $raiz 'datos\eda\informe_etl_eda.md'
if (-not (Test-Path $md)) { throw "No existe $md; ejecute antes informe-etl-eda." }
if (-not (Get-Command $Pandoc -ErrorAction SilentlyContinue)) {
    $alterno = Join-Path $env:USERPROFILE 'Documents\anaconda\Scripts\pandoc.exe'
    if (Test-Path $alterno) { $Pandoc = $alterno } else { throw 'No se encontró pandoc.' }
}
$salida = Join-Path (Resolve-Path $Destino) "Informe_Fase2_ETL_EDA_AvocadoIA_$Fecha.docx"
if (Test-Path $salida) { throw "Ya existe $salida; no se sobrescribe. Use otra fecha o renombre el archivo." }
$temporal = Join-Path ([IO.Path]::GetTempPath()) "informe_etl_eda_$([guid]::NewGuid()).docx"
& $Pandoc $md -o $temporal --toc --toc-depth=2 -V 'toc-title=Contenido' --resource-path=(Join-Path $raiz 'datos\eda')
if ($LASTEXITCODE -ne 0) { throw 'pandoc falló.' }
& $Python -P (Join-Path $PSScriptRoot 'formatear_docx.py') $temporal $salida
if ($LASTEXITCODE -ne 0) { throw 'El formateo del Word falló.' }
Remove-Item $temporal
Write-Host "Informe Word: $salida"
