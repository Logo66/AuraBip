# run_autoroute.ps1 — FreeRouting-Pipeline fuer AuraBip audio v0.1
# Schritte: Fanout-Vias -> Specctra DSN -> FreeRouting (headless) -> SES-Import + Fill -> DRC
# Vorlage: aura_kruecke sensor_board (dort erprobt)

$wd  = "C:\Users\Ivo\AuraBip\hardware\route"
$prj = "C:\Users\Ivo\AuraBip\hardware\project"
$py  = "C:\Program Files\KiCad\10.0\bin\python.exe"
$cli = "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
$jar = "$wd\freerouting.jar"

$prep   = "$prj\aurabip.kicad_pcb"
$fanout = "$wd\aurabip_fanout.kicad_pcb"
$dsn    = "$wd\aurabip.dsn"
$ses    = "$wd\aurabip.ses"
$out    = "$prj\aurabip_routed.kicad_pcb"
$drc    = "$wd\drc.rpt"

Write-Host "[1/6] Fanout-Vias (ohne Stitching)..."
& $py "$wd\fanout.py" $prep $fanout --nostitch 2>$null | Out-Null
Get-Content "$wd\fanout.log" | Select-Object -First 2

Write-Host "[2/5] Specctra-DSN-Export..."
& $py "$wd\export_dsn.py" $fanout $dsn 2>$null | Out-Null

Write-Host "[3/5] FreeRouting (headless)..."
if (Test-Path $ses) { Move-Item $ses "$ses.bak" -Force }
$env:JAVA_TOOL_OPTIONS = "-Djava.awt.headless=true"
& java -jar $jar -de $dsn -do $ses -mp 30 | Out-Null
Remove-Item Env:\JAVA_TOOL_OPTIONS -ErrorAction SilentlyContinue

Write-Host "[4/6] SES-Import (Runde 1)..."
& $py "$wd\finalize.py" $fanout $ses $out 0.1 2>$null | Out-Null
Get-Content "$wd\finalize.log" | Select-Object -Last 2

# Runde 2: FreeRouting vollendet die Reste auf dem teilgerouteten Board
Write-Host "[5/6] FreeRouting Runde 2 (Kontinuation)..."
$dsn2 = "$wd\aurabip_r2.dsn"
$ses2 = "$wd\aurabip_r2.ses"
& $py "$wd\export_dsn.py" $out $dsn2 2>$null | Out-Null
if (Test-Path $ses2) { Remove-Item $ses2 -Force }
$env:JAVA_TOOL_OPTIONS = "-Djava.awt.headless=true"
& java -jar $jar -de $dsn2 -do $ses2 -mp 30 | Out-Null
Remove-Item Env:\JAVA_TOOL_OPTIONS -ErrorAction SilentlyContinue
if (Test-Path $ses2) {
  & $py "$wd\finalize.py" $out $ses2 $out 0.1 2>$null | Out-Null
  Get-Content "$wd\finalize.log" | Select-Object -Last 2
}

Write-Host "[5.4/6] Handroute (bekannte FreeRouting-Luecken)..."
& $py "$wd\handroute.py" $out $out 2>$null | Out-Null
Get-Content "$wd\handroute.log" | Select-Object -Last 1

Write-Host "[5.5/6] GND-Stitching (nach Routing)..."
& $py "$wd\stitch.py" $out $out 2>$null | Out-Null
Get-Content "$wd\stitch.log" | Select-Object -First 1

Write-Host "[6/6] DRC..."
& $cli pcb drc --severity-error --exit-code-violations -o $drc $out 2>&1 | Out-String | Write-Host
$c = Get-Content $drc -Raw
Write-Host "Verletzungstypen:"
[regex]::Matches($c,'\[(\w+)\]:') | ForEach-Object { $_.Groups[1].Value } | Group-Object | Sort-Object Count -Descending | ForEach-Object { "  {0,3}  {1}" -f $_.Count, $_.Name }
Write-Host "Fertig -> $out"
