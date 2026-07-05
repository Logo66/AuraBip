# export_fab.ps1 — PCBWay-Fertigungspaket aus dem gerouteten Board
# Erzeugt: Gerber, Bohrdaten, Pick&Place (beide Seiten), BOM-CSV, Upload-ZIP
# Ausfuehren NUR wenn DRC sauber und die VERIFY-Tickets T-H1..T-H9 erledigt sind!

$cli = "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
$py  = "C:\Program Files\KiCad\10.0\bin\python.exe"
$hw  = "C:\Users\Ivo\AuraBip\hardware"
$pcb = "$hw\project\aurabip_routed.kicad_pcb"
$out = "$hw\production"

if (-not (Test-Path $pcb)) { Write-Host "FEHLER: $pcb fehlt"; exit 1 }
New-Item -ItemType Directory -Force "$out\gerber" | Out-Null

Write-Host "[1/4] Gerber..."
& $cli pcb export gerbers --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" `
    --subtract-soldermask -o "$out\gerber" $pcb | Out-Null

Write-Host "[2/4] Bohrdaten..."
& $cli pcb export drill --format excellon --drill-origin absolute --excellon-separate-th `
    -o "$out\gerber" $pcb | Out-Null

Write-Host "[3/4] Pick&Place..."
& $cli pcb export pos --format csv --units mm --side front -o "$out\aurabip-top-pos.csv" $pcb | Out-Null
& $cli pcb export pos --format csv --units mm --side back  -o "$out\aurabip-bottom-pos.csv" $pcb | Out-Null

Write-Host "[4/4] BOM + ZIP..."
& $py "$hw\scripts\make_bom_pcbway.py"
Compress-Archive -Path "$out\gerber\*" -DestinationPath "$out\aurabip_gerber.zip" -Force

Write-Host "Fertig -> $out"
Write-Host "PCBWay-Upload: aurabip_gerber.zip + aurabip-bom.csv + beide pos.csv"
