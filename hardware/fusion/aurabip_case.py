# AuraBip — parametrisches Gehäuse für Fusion 360
# © 2026 KIE Engineering. Proprietär.
#
# Ausführen in Fusion 360: UTILITIES -> ADD-INS (Shift+S) -> Skripte ->
# "+" -> diesen Ordner wählen -> aurabip_case ausführen.
# Erzeugt ein neues Dokument mit zwei Körpern: "Basis" und "Deckel".
#
# VARIANT unten umschalten:
#   "audio"  = ohne Display (geschlossener Deckel mit Lautsprechergitter)
#   "vision" = mit Fenster + Auflage für Waveshare 1.32" OLED (SSD1327)
#
# Einbau-Annahmen (bei Änderung nur PARAMS anpassen):
#   Platine 52x52x1.6, Bauteile oben max 8 mm (JST-Stecker!), unten 3.2 mm
#   (E22-Modul), Akku 504050 52x42x5 im Schacht unter der Platine,
#   Lautsprecher Visaton K 28 WP (D28.3, Tiefe ~5.4) im Deckel,
#   868-MHz-Flexantenne (~100x12) an der Innenwand unten/rechts,
#   mind. 15 mm von der GNSS-Antenne (oben) entfernt.

import adsk.core
import adsk.fusion
import traceback

VARIANT = "vision"          # "audio" oder "vision"

PARAMS = {
    # Platine
    "pcb_w": 52.0, "pcb_h": 52.0, "pcb_t": 1.6,
    "pcb_clear": 0.6,        # Luft rund um die Platine
    "top_clear": 8.0,        # Bauraum ueber der Platine (JST-Stecker!)
    "bot_clear": 3.4,        # Bauraum unter der Platine (E22 3.0)
    # Akku 504050
    "bat_w": 52.0, "bat_h": 42.0, "bat_t": 5.0,
    "bat_clear": 0.4,
    # Gehaeuse
    "wall": 1.8, "floor": 1.6, "lid": 1.8,
    "corner_r": 4.0,
    "ledge": 2.0,            # Platinen-Auflagesteg
    # Antennen-Kanal (Flexantenne an der Innenwand, unten = weg vom GNSS)
    "ant_chan_d": 2.2,       # zusaetzliche Tiefe der Wandnische
    "ant_chan_l": 102.0,     # Laenge (laeuft um die untere Ecke)
    "ant_chan_h": 13.0,
    # Lautsprecher K 28 WP
    "spk_d": 28.5, "spk_depth": 5.6, "spk_grill_d": 22.0,
    # Display Waveshare 1.32" (nur vision)
    "disp_mod_w": 32.6, "disp_mod_h": 28.3, "disp_mod_t": 4.6,
    "disp_win_w": 27.4, "disp_win_h": 20.7,   # Sichtfenster +0.5 Rand
    # Durchbrueche (Positionen in Platinen-Koordinaten, Ursprung Ecke
    # oben links wie im KiCad-Layout, x nach rechts, y nach unten)
    "usb_x": 12.0, "usb_w": 10.0, "usb_h": 3.8,     # Unterkante
    "sw1_y": 45.5, "sw1_w": 9.5, "sw1_h": 4.2,      # linke Kante, Schieber
    "rst_x": 47.0, "rst_y": 34.0, "rst_d": 1.6,     # Nadelloch Deckel
    "vent_y1": 19.6, "vent_y2": 27.0,               # Sensor-Insel rechte Kante
}


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        doc = app.documents.add(
            adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        root.name = f"AuraBip Gehaeuse ({VARIANT})"

        p = PARAMS
        # Innenraum
        in_w = p["pcb_w"] + 2 * p["pcb_clear"]                # x
        in_h = p["pcb_h"] + 2 * p["pcb_clear"]                # y
        z_bat = p["bat_t"] + 2 * p["bat_clear"]               # Akkuschacht
        z_pcb_bot = z_bat + p["bot_clear"]                    # Unterkante PCB
        z_pcb_top = z_pcb_bot + p["pcb_t"]
        in_depth_base = z_pcb_top + 2.0                       # Basis bis knapp ueber PCB
        lid_cavity = p["top_clear"] - 2.0                     # Rest im Deckel
        out_w = in_w + 2 * p["wall"]
        out_h = in_h + 2 * p["wall"]

        sketches = root.sketches
        planes = root.constructionPlanes
        extrudes = root.features.extrudeFeatures
        fillets = root.features.filletFeatures
        combines = root.features.combineFeatures

        def rect_sketch(plane, x1, y1, x2, y2, r=0.0):
            sk = sketches.add(plane)
            lines = sk.sketchCurves.sketchLines
            if r > 0:
                # Rechteck mit Eckenradius: der Einfachheit halber als
                # Rechteck; Radien kommen spaeter als Kantenfillets
                pass
            lines.addTwoPointRectangle(
                adsk.core.Point3D.create(x1 / 10.0, y1 / 10.0, 0),
                adsk.core.Point3D.create(x2 / 10.0, y2 / 10.0, 0))
            return sk

        def extrude_sk(sk, dist_mm, op, participant=None):
            prof = sk.profiles.item(0)
            inp = extrudes.createInput(prof, op)
            inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(
                dist_mm / 10.0))
            if participant is not None:
                inp.participantBodies = [participant]
            return extrudes.add(inp)

        xy = root.xYConstructionPlane
        NB = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation

        # ================= BASIS =================
        # Aussenklotz
        sk = rect_sketch(xy, 0, 0, out_w, out_h)
        base = extrude_sk(sk, p["floor"] + in_depth_base, NB).bodies.item(0)
        base.name = "Basis"

        # Innenraum ausraeumen (ab floor)
        off = planes.createInput()
        off.setByOffset(xy, adsk.core.ValueInput.createByReal(p["floor"] / 10.0))
        pl_floor = planes.add(off)
        sk = rect_sketch(pl_floor, p["wall"], p["wall"],
                         p["wall"] + in_w, p["wall"] + in_h)
        extrude_sk(sk, in_depth_base, CUT, base)

        # Akkuschacht-Stege: Auflagerahmen fuer die Platine auf Hoehe z_pcb_bot
        # (Steg rundum, unterbrochen ist fuers 3D-Drucken unnoetig)
        off = planes.createInput()
        off.setByOffset(xy, adsk.core.ValueInput.createByReal(
            (p["floor"] + z_bat + p["bot_clear"] - 1.0) / 10.0))
        pl_ledge = planes.add(off)
        sk = sketches.add(pl_ledge)
        lines = sk.sketchCurves.sketchLines
        lines.addTwoPointRectangle(
            adsk.core.Point3D.create(p["wall"] / 10.0, p["wall"] / 10.0, 0),
            adsk.core.Point3D.create((p["wall"] + in_w) / 10.0,
                                     (p["wall"] + in_h) / 10.0, 0))
        lines.addTwoPointRectangle(
            adsk.core.Point3D.create((p["wall"] + p["ledge"]) / 10.0,
                                     (p["wall"] + p["ledge"]) / 10.0, 0),
            adsk.core.Point3D.create((p["wall"] + in_w - p["ledge"]) / 10.0,
                                     (p["wall"] + in_h - p["ledge"]) / 10.0, 0))
        prof = None
        for i in range(sk.profiles.count):
            pr = sk.profiles.item(i)
            if pr.profileLoops.count == 2:
                prof = pr
        inp = extrudes.createInput(prof, JOIN)
        inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.1))
        inp.participantBodies = [base]
        extrudes.add(inp)

        # --- Durchbrueche Basis ---
        zx = root.xZConstructionPlane  # Wand unten/oben schneiden wir per Box
        # USB-C: Unterwand (y = out_h), Hoehe auf PCB-Oberkante zentriert
        z_usb = p["floor"] + z_pcb_top + 1.6  # Steckermitte ~1.6 ueber PCB
        sk = rect_sketch(xy, p["wall"] + p["pcb_clear"] + p["usb_x"] - p["usb_w"] / 2,
                         out_h - p["wall"] - 0.1,
                         p["wall"] + p["pcb_clear"] + p["usb_x"] + p["usb_w"] / 2,
                         out_h + 0.1)
        ex = extrude_sk(sk, z_usb + p["usb_h"], CUT, base)
        # (Der Schnitt geht vom Boden hoch — fuer v1 ok: unten ist eh Akku-
        #  schachtwand; wer es huebsch will, setzt die Skizze auf z_usb.)

        # Schiebeschalter: linke Wand (x=0)
        sk = rect_sketch(xy, -0.1, p["wall"] + p["pcb_clear"] + p["sw1_y"] - p["sw1_w"] / 2,
                         p["wall"] + 0.1,
                         p["wall"] + p["pcb_clear"] + p["sw1_y"] + p["sw1_w"] / 2)
        extrude_sk(sk, p["floor"] + z_pcb_top + p["sw1_h"], CUT, base)

        # Sensor-Belueftung: rechte Wand, 3 Schlitze auf Hoehe der Insel
        for i in range(3):
            yy = p["wall"] + p["pcb_clear"] + p["vent_y1"] + 1.5 + i * 2.6
            sk = rect_sketch(xy, out_w - p["wall"] - 0.1, yy,
                             out_w + 0.1, yy + 1.4)
            extrude_sk(sk, p["floor"] + z_pcb_top + 2.0, CUT, base)

        # Antennen-Nische: Innenseite Unterwand (weit weg von GNSS oben)
        sk = rect_sketch(xy, p["wall"] + 2.0, out_h - p["wall"] - 0.01,
                         p["wall"] + 2.0 + min(p["ant_chan_l"], in_w - 4),
                         out_h - p["wall"] + p["ant_chan_d"] - 0.01)
        # Nische = flacher CUT in die Wand (nicht durchgehend!)
        ex = extrude_sk(sk, p["floor"] + z_bat + p["ant_chan_h"], CUT, base)

        # ================= DECKEL =================
        z_lid0 = p["floor"] + in_depth_base
        off = planes.createInput()
        off.setByOffset(xy, adsk.core.ValueInput.createByReal(z_lid0 / 10.0))
        pl_lid = planes.add(off)
        sk = rect_sketch(pl_lid, 0, 0, out_w, out_h)
        lid = extrude_sk(sk, lid_cavity + p["lid"], NB).bodies.item(0)
        lid.name = "Deckel"
        # Deckel aushoehlen
        sk = rect_sketch(pl_lid, p["wall"], p["wall"],
                         p["wall"] + in_w, p["wall"] + in_h)
        extrude_sk(sk, lid_cavity, CUT, lid)

        # Lautsprecher: Sitz + Gitter im Deckel (Position: ueber dem
        # Akku-/Audio-Bereich, Mitte unten)
        spk_cx = (p["wall"] + in_w / 2) / 10.0
        spk_cy = (out_h - p["wall"] - p["spk_d"] / 2 - 4.0) / 10.0
        z_top = z_lid0 + lid_cavity + p["lid"]
        off = planes.createInput()
        off.setByOffset(xy, adsk.core.ValueInput.createByReal(z_lid0 / 10.0))
        pl_spk = planes.add(off)
        sk = sketches.add(pl_spk)
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(spk_cx, spk_cy, 0), p["spk_d"] / 20.0)
        extrude_sk(sk, p["spk_depth"], CUT, lid)  # Einbausitz von innen
        # Gitter: 7 Schlitze
        for i in range(-3, 4):
            sk = sketches.add(pl_spk)
            yy = spk_cy + i * 0.25
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                adsk.core.Point3D.create(spk_cx - p["spk_grill_d"] / 20.0, yy - 0.06, 0),
                adsk.core.Point3D.create(spk_cx + p["spk_grill_d"] / 20.0, yy + 0.06, 0))
            extrude_sk(sk, lid_cavity + p["lid"] + 0.1, CUT, lid)

        # RESET-Nadelloch im Deckel
        sk = sketches.add(pl_spk)
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(
                (p["wall"] + p["pcb_clear"] + p["rst_x"]) / 10.0,
                (p["wall"] + p["pcb_clear"] + p["rst_y"]) / 10.0, 0),
            p["rst_d"] / 20.0)
        extrude_sk(sk, lid_cavity + p["lid"] + 0.1, CUT, lid)

        if VARIANT == "vision":
            # Display-Fenster mittig-oben (ueber ESP32/IMU-Bereich,
            # Kabel laeuft zu J4 rechts)
            wcx = (p["wall"] + in_w / 2) / 10.0
            wcy = (p["wall"] + 16.0) / 10.0
            sk = sketches.add(pl_spk)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                adsk.core.Point3D.create(wcx - p["disp_win_w"] / 20.0,
                                         wcy - p["disp_win_h"] / 20.0, 0),
                adsk.core.Point3D.create(wcx + p["disp_win_w"] / 20.0,
                                         wcy + p["disp_win_h"] / 20.0, 0))
            extrude_sk(sk, lid_cavity + p["lid"] + 0.1, CUT, lid)
            # Modul-Auflagetasche von innen (0.5 tiefer als Deckelinnenseite)
            sk = sketches.add(pl_spk)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                adsk.core.Point3D.create(wcx - (p["disp_mod_w"] + 0.6) / 20.0,
                                         wcy - (p["disp_mod_h"] + 0.6) / 20.0, 0),
                adsk.core.Point3D.create(wcx + (p["disp_mod_w"] + 0.6) / 20.0,
                                         wcy + (p["disp_mod_h"] + 0.6) / 20.0, 0))
            extrude_sk(sk, lid_cavity - 0.5, CUT, lid)

        # Kanten brechen (aussen)
        try:
            edges = adsk.core.ObjectCollection.create()
            for b in (base, lid):
                for e in b.edges:
                    if abs(e.length - 0) > 0:
                        pass
            # Aussenkanten-Fillets sind optional — von Hand in Fusion
            # eleganter; hier bewusst weggelassen.
        except Exception:
            pass

        ui.messageBox(
            f"AuraBip-Gehaeuse ({VARIANT}) erstellt.\n"
            f"Aussenmasse: {out_w:.1f} x {out_h:.1f} x "
            f"{(z_lid0 + lid_cavity + p['lid']):.1f} mm\n\n"
            "Merkzettel:\n"
            "- Akku 504050 liegt im Schacht unter der Platine\n"
            "- Flexantenne in die Nische an der unteren Innenwand kleben\n"
            "  (max. Abstand zum GNSS oben!)\n"
            "- Lautsprecher von innen in den Deckelsitz kleben\n"
            "- Platine liegt auf dem Steg, Deckel klemmt sie\n"
            "- Fuer die Passform: KiCad-STEP der Platine importieren\n"
            "  (hardware/production/aurabip.step) und einschwimmen lassen")
    except Exception:
        if ui:
            ui.messageBox("Fehler:\n{}".format(traceback.format_exc()))
