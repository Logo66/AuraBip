# PCBWay-Bestellparameter AuraBip v0.1 (für die Offerte)

## PCB (Instant Quote → Standard PCB)
| Parameter | Wert |
|---|---|
| Board size | 52 × 52 mm |
| Quantity | **10** (Prototypen-Charge) |
| Layers | **4** |
| Material | FR-4, TG150 |
| Thickness | 1.6 mm |
| Min track/spacing | **5/5 mil** (0.127 mm Schmalspur-Züge!) |
| Min hole size | 0.3 mm |
| Solder mask | Grün (oder nach Geschmack) |
| Silkscreen | Weiß |
| Surface finish | **ENIG** (0.4-mm-Pitch BMP581 + Stamp-Holes — kein HASL!) |
| Via process | Tenting vias |
| Kupfer | 1 oz außen / 0.5 oz innen (Standard) |
| Besonderheit | **Interne Fräskontur** (Sensor-Insel, C-Schlitz 1 mm) — ist in Edge.Cuts enthalten |

## Assembly (Turnkey, nur Vorderseite)
| Parameter | Wert |
|---|---|
| Seiten | **Nur Top** (Bottom = 4 Teile Handbestückung durch uns: E22, C14, C15) |
| Anzahl | 10 Boards bestücken |
| Teile-Beschaffung | Turnkey (PCBWay beschafft); **U5 (Quectel L96) + U10 (E22) ggf. als Consigned/selbst liefern**, falls Beschaffung teuer |
| Stencil | Ja (framework-los reicht) |
| Dateien | aurabip_gerber.zip · aurabip-bom.csv · aurabip-top-pos.csv (+ bottom-pos nur zur Referenz) |

## Hinweise für die Review durch PCBWay
- 0402-Passive, TQFN-16 (0.5 P), LGA-10 (0.4 P!), LGA-14 (0.5 P), DFN-4
- USB-C-Buchse ragt 1.2 mm über die Kante (Absicht)
- NPTH: Schalter-Justierstifte + USB-Schild
- Bottom-Bauteile im Pick&Place enthalten, aber NICHT bestücken

## Nach Offerten-Eingang prüfen (T-H1)
- [ ] Alle BOM-Zeilen gematcht? (Passive ohne MPN → PCBWay-Vorschlag akzeptieren, X7R/1% reicht)
- [ ] L96 + E22 lieferbar/Preis ok? Sonst consigned liefern
- [ ] ME6217C33M5G verfügbar? (Fallback: AP2112K-3.3, pinkompatibel, dann aber LoRa-TX + BLE-Peak nicht gleichzeitig — FW drosseln)
- [ ] Keine Design-Rückfragen zu Schmalspur/Fräsung offen
