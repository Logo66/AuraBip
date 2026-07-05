# -*- coding: utf-8 -*-
"""News-Seite AuraBip bauen: HTML mit eingebetteten Renderings."""
import os

D = os.path.dirname(os.path.abspath(__file__))
top = open(os.path.join(D, "news_top.b64")).read()
bot = open(os.path.join(D, "news_bottom.b64")).read()
per = open(os.path.join(D, "news_persp.b64")).read()

html = """<title>AuraBip — Vario mit FANET | Projekt-News</title>
<style>
:root{
  --ground:#0f1d21; --panel:#15282e; --line:#24404a;
  --ink:#e8e4d8; --muted:#8fa3a6; --accent:#ff7a3d; --ok:#7fbf6b;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:16px/1.65 "Segoe UI",system-ui,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:0 20px 80px}
.eyebrow{letter-spacing:.18em;text-transform:uppercase;font-size:12px;
  color:var(--accent);font-weight:600;margin:48px 0 10px}
h1{font-size:clamp(34px,6vw,54px);line-height:1.05;margin:0 0 14px;
  font-weight:800;letter-spacing:-.02em;text-wrap:balance}
.lede{font-size:19px;color:var(--muted);max-width:62ch;margin:0 0 36px}
.hero{background:var(--panel);border:1px solid var(--line);border-radius:6px;
  overflow:hidden;margin:0}
.hero img{display:block;width:100%;height:auto}
.hero figcaption{padding:10px 16px;font-size:13px;color:var(--muted)}
h2{font-size:24px;margin:56px 0 16px;letter-spacing:-.01em}
p{max-width:68ch}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:640px){.grid2{grid-template-columns:1fr}}
figure{margin:0}
figure.card{background:var(--panel);border:1px solid var(--line);
  border-radius:6px;overflow:hidden}
figure.card img{display:block;width:100%;height:auto}
figure.card figcaption{padding:8px 14px;font-size:13px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:15px}
td,th{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;
  vertical-align:top}
th{color:var(--muted);font-weight:600;width:36%}
td{font-variant-numeric:tabular-nums}
.status{display:grid;gap:10px;margin:20px 0;padding:0;list-style:none}
.status li{display:flex;gap:12px;align-items:baseline;background:var(--panel);
  border:1px solid var(--line);border-radius:6px;padding:12px 16px}
.badge{flex:none;font-size:11px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;padding:3px 9px;border-radius:3px}
.done .badge{background:rgba(127,191,107,.15);color:var(--ok)}
.open .badge{background:rgba(255,122,61,.14);color:var(--accent)}
.status b{font-weight:600}
.status span.det{color:var(--muted);font-size:14px;display:block}
.explode{background:var(--panel);border:1px solid var(--line);border-radius:6px;
  padding:18px 10px 6px}
.explode svg{display:block;width:100%;height:auto}
.foot{margin-top:64px;padding-top:18px;border-top:1px solid var(--line);
  font-size:13px;color:var(--muted)}
</style>
<div class="wrap">
  <p class="eyebrow">KIE Engineering &middot; Projekt-News &middot; Juli 2026</p>
  <h1>AuraBip: das kompakte Vario, das dich am Himmel sichtbar macht</h1>
  <p class="lede">Elektronische Sichtbarkeit wird f&uuml;r Gleitschirme kommen &mdash;
  der diskutierte europ&auml;ische Standard hei&szlig;t ADS-L. Wir bauen ein Ger&auml;t,
  das Variometer, GPS, Sprachausgabe und 868-MHz-Funk in eine Handfl&auml;che packt:
  heute FANET/OGN, f&uuml;r ADS-L vorbereitet &mdash; entwickelt in der Schweiz,
  gefertigt in Kleinserie.</p>

  <figure class="hero">
    <img src="data:image/jpeg;base64,__PER__" alt="AuraBip Platine, 3D-Ansicht">
    <figcaption>Konstruktionsstand der AuraBip-Hauptplatine (52&thinsp;&times;&thinsp;52&thinsp;mm,
    4 Lagen). 3D-Rendering direkt aus den Fertigungsdaten.</figcaption>
  </figure>

  <h2>Was im Ger&auml;t steckt</h2>
  <table>
    <tr><th>Instant-Vario</th><td>Barometer BMP581 (50&thinsp;Hz) + Beschleunigungssensor,
      Kalman-gekoppelt &mdash; Ansprechzeit unter 100&thinsp;ms statt der tr&auml;gen Sekunde
      reiner Baro-Varios</td></tr>
    <tr><th>Sichtbarkeit</th><td>868-MHz-Sender (SX1262) meldet die Position ins offene
      FANET/OGN-Netz. Die Funk-Hardware beherrscht auch GFSK &mdash; damit ist das Ger&auml;t
      f&uuml;r den kommenden <b>ADS-L</b>-Standard vorbereitet (Firmware-Update, sobald er
      f&uuml;r Gleitschirme greift)</td></tr>
    <tr><th>GPS</th><td>GNSS-Modul mit integrierter Antenne, thermisch und
      hochfrequent sauber vom Rest getrennt</td></tr>
    <tr><th>Ton &amp; Sprache</th><td>Class-D-Verst&auml;rker mit 28-mm-Lautsprecher in
      geschlossener Akustikkammer mit Reflexkanal &mdash; Varioton und Sprachansagen,
      h&ouml;rbar auch im Fahrtwind</td></tr>
    <tr><th>Anbindung</th><td>Bluetooth zu XCTrack/XCSoar (LK8EX1 + NMEA), USB-C zum Laden</td></tr>
    <tr><th>Display (Variante vision)</th><td>1.32&Prime;-OLED, 128&thinsp;&times;&thinsp;96,
      16 Graustufen &mdash; im Deckel, per Kabel angebunden</td></tr>
    <tr><th>Sensor-Insel</th><td>Druck- und Klimasensor sitzen auf einer
      freigefr&auml;sten Insel im Board &mdash; die Eigenw&auml;rme der Elektronik
      verf&auml;lscht die Messung nicht</td></tr>
    <tr><th>Laufzeit</th><td>1500-mAh-Akku, rund 10 Stunden; Laden auch im
      ausgeschalteten Zustand</td></tr>
    <tr><th>Gr&ouml;sse</th><td>Geh&auml;use ca. 63&thinsp;&times;&thinsp;63&thinsp;&times;&thinsp;24&thinsp;mm,
      verschraubter Deckel mit Dichtsitz, Klett-Montage am Cockpit</td></tr>
    <tr><th>Preisziel</th><td>audio (ohne Display) 149&ndash;169&thinsp;CHF &middot;
      vision (mit Display) 199&ndash;229&thinsp;CHF</td></tr>
  </table>

  <h2>Die Platine von beiden Seiten</h2>
  <div class="grid2">
    <figure class="card">
      <img src="data:image/jpeg;base64,__TOP__" alt="Platine Vorderseite">
      <figcaption>Vorderseite: Prozessor, GPS (oben), Sensor-Insel (rechts),
      Audio &amp; Stromversorgung (unten)</figcaption>
    </figure>
    <figure class="card">
      <img src="data:image/jpeg;base64,__BOT__" alt="Platine Rueckseite">
      <figcaption>R&uuml;ckseite: FANET-Funkmodul und Antennenanschluss &mdash;
      durch eine durchgehende Masselage geschirmt</figcaption>
    </figure>
  </div>

  <h2>Geh&auml;use: Explosionsansicht</h2>
  <div class="explode">
  <svg viewBox="0 0 860 640" xmlns="http://www.w3.org/2000/svg" role="img"
       aria-label="Explosionszeichnung des AuraBip-Gehaeuses">
    <line x1="430" y1="20" x2="430" y2="620" stroke="#24404a" stroke-width="1" stroke-dasharray="2 6"/>
    <g stroke="#3d5a64" stroke-width="1.5">
      <rect x="290" y="30" width="280" height="46" rx="6" fill="#1d3a43"/>
      <circle cx="500" cy="53" r="17" fill="#142b32"/>
      <line x1="486" y1="53" x2="514" y2="53" stroke-width="2"/>
      <line x1="488" y1="46" x2="512" y2="46" stroke-width="2"/>
      <line x1="488" y1="60" x2="512" y2="60" stroke-width="2"/>
      <rect x="330" y="42" width="90" height="22" rx="2" fill="#0b161a"/>
      <circle cx="305" cy="41" r="4" fill="#0b161a"/>
      <circle cx="555" cy="41" r="4" fill="#0b161a"/>
      <circle cx="305" cy="65" r="4" fill="#0b161a"/>
      <circle cx="555" cy="65" r="4" fill="#0b161a"/>
      <rect x="345" y="120" width="120" height="34" rx="3" fill="#0b161a"/>
      <rect x="356" y="126" width="98" height="22" fill="#10242b"/>
      <circle cx="470" cy="222" r="34" fill="#1d3a43"/>
      <circle cx="470" cy="222" r="22" fill="#142b32"/>
      <circle cx="470" cy="222" r="7" fill="#0b161a"/>
      <circle cx="330" cy="222" r="30" fill="#16323a"/>
      <circle cx="330" cy="222" r="20" fill="#1d3a43"/>
      <rect x="280" y="330" width="300" height="52" rx="4" fill="#173d2a"/>
      <rect x="300" y="340" width="60" height="32" fill="#0b161a"/>
      <rect x="380" y="338" width="44" height="20" fill="#c8c2b0"/>
      <rect x="470" y="340" width="70" height="30" fill="#10242b"/>
      <rect x="546" y="336" width="26" height="18" fill="#0b161a" stroke="#ff7a3d"/>
      <rect x="300" y="430" width="255" height="30" rx="5" fill="#203038"/>
      <rect x="270" y="505" width="320" height="80" rx="8" fill="#1d3a43"/>
      <rect x="286" y="516" width="288" height="58" rx="4" fill="#10242b"/>
      <rect x="286" y="560" width="120" height="12" fill="#142b32" stroke="#ff7a3d" stroke-width="1"/>
      <rect x="590" y="530" width="14" height="22" fill="#0b161a"/>
    </g>
    <g stroke="#8fa3a6" stroke-width="1" stroke-dasharray="3 4">
      <line x1="570" y1="53" x2="640" y2="53"/>
      <line x1="465" y1="137" x2="640" y2="137"/>
      <line x1="504" y1="222" x2="640" y2="222"/>
      <line x1="330" y1="252" x2="330" y2="272"/>
      <line x1="580" y1="356" x2="640" y2="356"/>
      <line x1="555" y1="445" x2="640" y2="445"/>
      <line x1="604" y1="541" x2="640" y2="541"/>
    </g>
    <g font-family="Segoe UI,sans-serif">
      <g font-size="13" fill="#e8e4d8">
        <text x="648" y="50">Deckel mit Trichter-Gitter</text>
        <text x="648" y="134">1.32&#8243;-OLED-Modul</text>
        <text x="648" y="219">Lautsprecher 28&#8201;mm (K&#8201;28&#8201;WP)</text>
        <text x="648" y="353">Hauptplatine 52&#8201;&#215;&#8201;52&#8201;mm</text>
        <text x="648" y="442">Akku, flach im Schacht</text>
        <text x="648" y="538">Basis mit Nut-Dichtsitz</text>
      </g>
      <g font-size="11" fill="#8fa3a6">
        <text x="648" y="66">4&#215; M2-Inbus &#183; Display-Fenster (vision)</text>
        <text x="648" y="150">liegt in der Deckeltasche, Kabel zur Platine</text>
        <text x="648" y="235">dahinter: Kammerdeckel, dicht verklebt</text>
        <text x="230" y="290">Kammerdeckel (3. Druckteil)</text>
        <text x="648" y="369">FANET-Funk unten, Sensor-Insel rechts</text>
        <text x="648" y="458">LiPo 504050 &#183; 1500&#8201;mAh &#183; laedt auch im Aus</text>
        <text x="648" y="554">Antennen-Nische (orange), USB-C-Tasche,</text>
        <text x="648" y="568">Gewinde-Inserts, Sensor-Belueftung</text>
      </g>
    </g>
  </svg>
  </div>
  <p style="color:var(--muted);font-size:14px">Schemadarstellung. Das Geh&auml;use
  entsteht parametrisch in Fusion&thinsp;360 und wird f&uuml;r die erste Serie
  3D-gedruckt; die Akustikkammer mit Reflexkanal ist Teil des Deckels.</p>

  <h2>Wo das Projekt steht</h2>
  <ul class="status">
    <li class="done"><span class="badge">Fertig</span><div><b>Elektronik-Design komplett</b>
      <span class="det">Schaltplan gepr&uuml;ft (0 Fehler), alle kritischen Bauteil-Pinouts
      gegen die Original-Datenbl&auml;tter verifiziert, Teileliste mit Bezugsquellen steht</span></div></li>
    <li class="done"><span class="badge">Fertig</span><div><b>Platine konstruiert</b>
      <span class="det">52&thinsp;&times;&thinsp;52&thinsp;mm, 4 Lagen, doppelseitig
      best&uuml;ckt, Design-Regeln der Fertigung eingehalten</span></div></li>
    <li class="done"><span class="badge">Fertig</span><div><b>Geh&auml;use konstruiert</b>
      <span class="det">Verschraubt, abgedichtet, mit Akustikkammer &mdash; zwei
      Varianten (mit/ohne Display)</span></div></li>
    <li class="open"><span class="badge">L&auml;uft</span><div><b>Letzte Leiterbahnen</b>
      <span class="det">&gt;&thinsp;90&thinsp;% geroutet; die letzten Verbindungen
      werden von Hand gelegt</span></div></li>
    <li class="open"><span class="badge">N&auml;chster Schritt</span><div><b>Prototypen-Charge</b>
      <span class="det">Fertigung &amp; Best&uuml;ckung bei PCBWay, danach Feldtest:
      FANET-Reichweite, GPS-Empfang, Klang</span></div></li>
    <li class="open"><span class="badge">Geplant</span><div><b>CE/Funk-Konformit&auml;t</b>
      <span class="det">Pr&uuml;fung mit vorzertifizierten Funkmodulen, vor dem
      Verkaufsstart</span></div></li>
  </ul>

  <p class="foot">Stand Juli 2026. Renderings zeigen den Konstruktionsstand, kein
  Serienprodukt. AuraBip ist Teil des Flight-Buddy-&Ouml;kosystems von KIE Engineering
  (Kr&uuml;cke, WindBuddy). &Auml;nderungen vorbehalten.</p>
</div>
"""
html = html.replace("__PER__", per).replace("__TOP__", top).replace("__BOT__", bot)
out = os.path.join(D, "aurabip-news-2026-07.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("HTML:", len(html) // 1024, "KB ->", out)
