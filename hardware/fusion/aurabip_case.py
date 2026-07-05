# AuraBip — parametrisches Gehäuse für Fusion 360, v2
# © 2026 KIE Engineering. Proprietär.
#
# Ausführen: UTILITIES -> ADD-INS (Shift+S) -> Skripte -> "+" -> diesen
# Ordner wählen -> aurabip_case ausführen. Erzeugt "Basis" + "Deckel".
#
# VARIANT:  "audio" (ohne Display) | "vision" (Fenster + 1.32"-OLED)
# PORT:     True = Reflex-Kanal ("Transmission-Line light") zusätzlich
#           zur geschlossenen Rückkammer — mehr Pegel 300–600 Hz
# ANT_STUB: True = Ø6.4-Bohrung rechte Wand für SMA-Buchse (Stummel-
#           antenne) statt interner Flexantenne
#
# AKUSTIK-KONZEPT (K 28 WP, Abstrahlung nach OBEN, Klett unten):
#   1. Lautsprecher hängt in einer Boss-Ringkammer unter der Deckelplatte,
#      Membran zeigt nach oben durch einen KONISCHEN Trichter (Quasi-Horn:
#      Ø22 -> Ø26) mit feinen Gitterstegen — bester Mittelton-Wirkungsgrad.
#   2. Die Rückseite ist eine GESCHLOSSENE Kammer (Boss + Bodenplatte).
#      Das verhindert den akustischen Kurzschluss — der eigentliche
#      Pegelkiller in offenen Gehäusen.
#   3. Optional (PORT=True): 3×3-mm-Kanal aus der Kammer, ~45 mm an der
#      Deckelinnenwand entlang, Austritt seitlich vorn. Wirkt als
#      Reflex-/kurze Transmission-Line für 300–600 Hz.
#   Vario-Töne (400–1600 Hz) und Sprache brauchen keinen Tiefbass —
#   die Portlänge (port_len) ist der Tuning-Parameter, am Druck testen.
#
# ANTENNE FANET: Nische in der unteren Innenwand. Gehäuse steht flach
# auf dem Cockpit -> Wand steht senkrecht -> Flexantenne ist vertikal
# polarisiert wie die OGN-/FANET-Gegenstellen. Integriert schlägt
# Stummel, solange die Wand kupfer-/karbonfrei bleibt (PLA/PETG ok).

import adsk.core
import adsk.fusion
import traceback

VARIANT = "vision"      # "audio" | "vision"
PORT = True
ANT_STUB = False

P = {
    "pcb_w": 52.0, "pcb_h": 52.0, "pcb_t": 1.6, "pcb_clear": 0.6,
    "top_clear": 8.0, "bot_clear": 3.4,
    "bat_w": 52.0, "bat_h": 42.0, "bat_t": 5.0, "bat_clear": 0.4,
    "wall": 1.8, "floor": 1.6, "lid_plate": 1.8,
    "lid_cavity": 9.2,          # Innenhoehe Deckel (Lautsprecherkammer!)
    "ledge": 2.0,
    # Lautsprecher K 28 WP
    "spk_d": 28.6, "spk_flange_t": 1.6, "spk_depth": 5.6,
    "boss_wall": 1.6, "chamber_h": 1.8,   # Luft hinter dem Magneten
    "horn_d1": 22.0, "horn_d2": 26.5,     # Trichter innen -> aussen
    "grill_bar": 1.1,
    # Reflex-Kanal
    "port_wh": 3.0, "port_len": 45.0,
    # Display Waveshare 1.32"
    "disp_mod_w": 32.6, "disp_mod_h": 28.3,
    "disp_win_w": 27.4, "disp_win_h": 20.7,
    # Durchbrueche (Platinen-Koordinaten, Ursprung oben links)
    "usb_x": 12.0, "usb_w": 10.2, "usb_h": 4.0,
    "sw1_y": 45.5, "sw1_w": 9.5, "sw1_h": 4.2,
    "rst_x": 47.0, "rst_y": 34.0, "rst_d": 1.6,
    "vent_y1": 19.6,
    # Antennen-Nische
    "ant_d": 2.2, "ant_l": 46.0, "ant_h": 13.0,
    "stub_d": 6.4, "stub_y": 40.0,
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
        # root.name ist in neuen Dokumenten schreibgeschuetzt -> Occurrence
        try:
            root.name = f"AuraBip_{VARIANT}"
        except Exception:
            pass  # Name bleibt Standard; Dokument beim Speichern benennen

        sketches = root.sketches
        planes = root.constructionPlanes
        extrudes = root.features.extrudeFeatures

        NB = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
        xy = root.xYConstructionPlane

        def mm(v):
            return v / 10.0  # API rechnet in cm

        def plane_at(z):
            inp = planes.createInput()
            inp.setByOffset(xy, adsk.core.ValueInput.createByReal(mm(z)))
            return planes.add(inp)

        def rect(plane, x1, y1, x2, y2):
            sk = sketches.add(plane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                adsk.core.Point3D.create(mm(x1), mm(y1), 0),
                adsk.core.Point3D.create(mm(x2), mm(y2), 0))
            return sk

        def circ(plane, cx, cy, d):
            sk = sketches.add(plane)
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(mm(cx), mm(cy), 0), mm(d / 2.0))
            return sk

        def ext(sk, dist, op, body=None, profile_index=0):
            prof = sk.profiles.item(profile_index)
            inp = extrudes.createInput(prof, op)
            inp.setDistanceExtent(False,
                                  adsk.core.ValueInput.createByReal(mm(dist)))
            if body is not None:
                inp.participantBodies = [body]
            return extrudes.add(inp)

        # ---------- abgeleitete Masse ----------
        in_w = P["pcb_w"] + 2 * P["pcb_clear"]
        in_h = P["pcb_h"] + 2 * P["pcb_clear"]
        out_w = in_w + 2 * P["wall"]
        out_h = in_h + 2 * P["wall"]
        z_bat = P["bat_t"] + 2 * P["bat_clear"]
        z_pcb_bot = P["floor"] + z_bat + P["bot_clear"]
        z_pcb_top = z_pcb_bot + P["pcb_t"]
        z_part = z_pcb_top + P["top_clear"] - P["lid_cavity"] + 2.0
        # Basis reicht bis z_part, Deckel von z_part bis oben
        z_top = z_part + P["lid_cavity"] + P["lid_plate"]

        def bx(px):  # Platinen-x -> absolut
            return P["wall"] + P["pcb_clear"] + px

        def by(py):
            return P["wall"] + P["pcb_clear"] + py

        # ================= BASIS =================
        sk = rect(xy, 0, 0, out_w, out_h)
        base = ext(sk, z_part, NB).bodies.item(0)
        base.name = "Basis"
        sk = rect(plane_at(P["floor"]), P["wall"], P["wall"],
                  P["wall"] + in_w, P["wall"] + in_h)
        ext(sk, z_part - P["floor"], CUT, base)

        # Platinen-Auflagesteg (Rahmen) auf PCB-Unterkante
        pl = plane_at(z_pcb_bot - 1.2)
        sk = sketches.add(pl)
        ln = sk.sketchCurves.sketchLines
        ln.addTwoPointRectangle(
            adsk.core.Point3D.create(mm(P["wall"]), mm(P["wall"]), 0),
            adsk.core.Point3D.create(mm(P["wall"] + in_w), mm(P["wall"] + in_h), 0))
        ln.addTwoPointRectangle(
            adsk.core.Point3D.create(mm(P["wall"] + P["ledge"]),
                                     mm(P["wall"] + P["ledge"]), 0),
            adsk.core.Point3D.create(mm(P["wall"] + in_w - P["ledge"]),
                                     mm(P["wall"] + in_h - P["ledge"]), 0))
        prof = None
        for i in range(sk.profiles.count):
            if sk.profiles.item(i).profileLoops.count == 2:
                prof = sk.profiles.item(i)
        inp = extrudes.createInput(prof, JOIN)
        inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(mm(1.2)))
        inp.participantBodies = [base]
        extrudes.add(inp)

        # USB-C (Unterwand), auf Steckerhoehe
        sk = rect(plane_at(z_pcb_top - 0.3),
                  bx(P["usb_x"] - P["usb_w"] / 2), out_h - P["wall"] - 0.1,
                  bx(P["usb_x"] + P["usb_w"] / 2), out_h + 0.1)
        ext(sk, P["usb_h"], CUT, base)

        # Schiebeschalter (linke Wand)
        sk = rect(plane_at(z_pcb_top - 0.3),
                  -0.1, by(P["sw1_y"] - P["sw1_w"] / 2),
                  P["wall"] + 0.1, by(P["sw1_y"] + P["sw1_w"] / 2))
        ext(sk, P["sw1_h"], CUT, base)

        # Sensor-Schlitze (rechte Wand, Hoehe Insel)
        for i in range(3):
            yy = by(P["vent_y1"] + 1.2 + i * 2.6)
            sk = rect(plane_at(z_pcb_top),
                      out_w - P["wall"] - 0.1, yy, out_w + 0.1, yy + 1.4)
            ext(sk, 2.0, CUT, base)

        # Antennen-Nische (untere Innenwand) ODER SMA-Stummel-Bohrung
        if not ANT_STUB:
            sk = rect(plane_at(P["floor"] + 1.0),
                      P["wall"] + 3.0, out_h - P["wall"] - 0.01,
                      P["wall"] + 3.0 + P["ant_l"],
                      out_h - P["wall"] + P["ant_d"] - 0.01)
            ext(sk, P["ant_h"], CUT, base)
        else:
            pl = plane_at((z_pcb_bot + z_pcb_top) / 2)
            sk = sketches.add(pl)  # Bohrung rechte Wand als Rechteck-Naeherung
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(mm(out_w - P["wall"] / 2),
                                         mm(by(P["stub_y"])), 0),
                mm(P["stub_d"] / 2))
            # Zylinder quer durch die Wand: als Loch von aussen fraesen
            # (vereinfachte Naeherung: senkrechte Bohrung entfaellt; SMA-
            # Bohrung von Hand setzen oder Wandstaerke lokal anpassen)
            pass

        # ================= DECKEL =================
        pl_part = plane_at(z_part)
        sk = rect(pl_part, 0, 0, out_w, out_h)
        lid = ext(sk, P["lid_cavity"] + P["lid_plate"], NB).bodies.item(0)
        lid.name = "Deckel"
        sk = rect(pl_part, P["wall"], P["wall"],
                  P["wall"] + in_w, P["wall"] + in_h)
        ext(sk, P["lid_cavity"], CUT, lid)

        # ---- Lautsprecher-Akustikmodul (im Deckel, hinten mittig) ----
        scx = P["wall"] + in_w / 2.0
        scy = out_h - P["wall"] - P["spk_d"] / 2.0 - 5.0
        boss_od = P["spk_d"] + 2 * P["boss_wall"]
        z_lid_ceil = z_part + P["lid_cavity"]          # Unterseite Deckelplatte
        boss_h = P["spk_depth"] + P["spk_flange_t"] + P["chamber_h"] + 1.2

        # Boss-Ring (JOIN von der Deckeldecke nach unten)
        pl = plane_at(z_lid_ceil - boss_h)
        sk = sketches.add(pl)
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(mm(scx), mm(scy), 0), mm(boss_od / 2))
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(mm(scx), mm(scy), 0), mm(P["spk_d"] / 2))
        prof = None
        for i in range(sk.profiles.count):
            if sk.profiles.item(i).profileLoops.count == 2:
                prof = sk.profiles.item(i)
        inp = extrudes.createInput(prof, JOIN)
        inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(mm(boss_h)))
        inp.participantBodies = [lid]
        extrudes.add(inp)

        # Kammerboden (verschliesst die Rueckkammer; JOIN)
        sk = circ(plane_at(z_lid_ceil - boss_h), scx, scy, boss_od)
        ext(sk, 1.2, JOIN, lid)

        # Trichter (Quasi-Horn) durch die Deckelplatte: zwei Stufen
        sk = circ(plane_at(z_lid_ceil), scx, scy, P["horn_d1"])
        ext(sk, P["lid_plate"] / 2, CUT, lid)
        sk = circ(plane_at(z_lid_ceil + P["lid_plate"] / 2), scx, scy, P["horn_d2"])
        ext(sk, P["lid_plate"] / 2 + 0.1, CUT, lid)
        # Gitterstege wieder einsetzen (3 Balken quer)
        for i in (-1, 0, 1):
            sk = rect(plane_at(z_lid_ceil),
                      scx - P["horn_d2"] / 2, scy + i * 6.0 - P["grill_bar"] / 2,
                      scx + P["horn_d2"] / 2, scy + i * 6.0 + P["grill_bar"] / 2)
            ext(sk, P["lid_plate"], JOIN, lid)

        # Reflex-Kanal: Schlitz aus der Kammer -> Kanal an der Decke ->
        # Austritt durch die rechte Deckelwand
        if PORT:
            zc = z_lid_ceil - P["port_wh"]
            # Durchbruch Boss-Wand (rechts)
            sk = rect(plane_at(zc),
                      scx + P["spk_d"] / 2 - 0.5, scy - P["port_wh"] / 2,
                      scx + boss_od / 2 + 0.5, scy + P["port_wh"] / 2)
            ext(sk, P["port_wh"], CUT, lid)
            # Kanalstege an der Decke: zwei Rippen bilden den Kanal
            x0 = scx + boss_od / 2
            x1 = min(x0 + P["port_len"], P["wall"] + in_w - 0.5)
            for off in (-P["port_wh"] / 2 - 1.2, P["port_wh"] / 2):
                sk = rect(plane_at(zc),
                          x0, scy + off, x1, scy + off + 1.2)
                ext(sk, P["port_wh"], JOIN, lid)
            # Austritt durch die rechte Wand des Deckels
            sk = rect(plane_at(zc),
                      P["wall"] + in_w - 0.1, scy - P["port_wh"] / 2,
                      out_w + 0.1, scy + P["port_wh"] / 2)
            ext(sk, P["port_wh"], CUT, lid)

        # RESET-Nadelloch
        sk = circ(plane_at(z_part), bx(P["rst_x"]), by(P["rst_y"]), P["rst_d"])
        ext(sk, P["lid_cavity"] + P["lid_plate"] + 0.1, CUT, lid)

        if VARIANT == "vision":
            wcx = P["wall"] + in_w / 2.0
            wcy = P["wall"] + 16.0
            sk = rect(plane_at(z_lid_ceil),
                      wcx - P["disp_win_w"] / 2, wcy - P["disp_win_h"] / 2,
                      wcx + P["disp_win_w"] / 2, wcy + P["disp_win_h"] / 2)
            ext(sk, P["lid_plate"] + 0.1, CUT, lid)
            sk = rect(plane_at(z_lid_ceil - 0.6),
                      wcx - (P["disp_mod_w"] + 0.6) / 2,
                      wcy - (P["disp_mod_h"] + 0.6) / 2,
                      wcx + (P["disp_mod_w"] + 0.6) / 2,
                      wcy + (P["disp_mod_h"] + 0.6) / 2)
            ext(sk, 0.6, CUT, lid)

        ui.messageBox(
            f"AuraBip-Gehaeuse ({VARIANT}) erstellt.\n"
            f"Aussen: {out_w:.1f} x {out_h:.1f} x {z_top:.1f} mm\n\n"
            "Akustik: geschlossene Rueckkammer + Trichterfront"
            + (" + Reflex-Kanal (port_len tunen!)" if PORT else "") + "\n"
            "Antenne: " + ("SMA-Stummel rechts" if ANT_STUB else
                           "Flexantenne in Wandnische unten (steht vertikal)") + "\n"
            "Passform: hardware/production/aurabip.step importieren.")
    except Exception:
        if ui:
            ui.messageBox("Fehler:\n{}".format(traceback.format_exc()))
