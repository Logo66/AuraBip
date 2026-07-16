# AuraBip — parametrisches Gehäuse für Fusion 360, v3
# © 2026 KIE Engineering. Proprietär.
#
# Ausführen: UTILITIES -> ADD-INS (Shift+S) -> Skripte -> "+" -> diesen
# Ordner wählen -> aurabip_case. Erzeugt 3 Körper: Basis, Deckel,
# Kammerdeckel.
#
# v3 (Ivo, 2026-07-05):
#   - Wandstärke 5 mm  (Aussenmass dadurch ~63.4 x 63.4 — Hinweis!)
#   - Nut im Basis-Rand (1.5 x 1.5), Feder am Deckel (Dichtsitz)
#   - 4x Inbus M2: Deckel Durchgang 2.15 + Kopfsenkung 3.95 x 1.9;
#     Basis 3.2 x 4.5 tief für Gewinde-Inserts
#   - Reflexkanal als GESCHLOSSENER Kanal (Decke+2 Rippen+Boden) von
#     der Lautsprecherkammer bis DURCH die Aussenwand
#   - USB-C: Durchbruch + aussen 3 mm tiefe Steckertasche (sonst
#     erreicht der Stecker die Buchse durch 5 mm Wand nicht);
#     dito Schiebeschalter-Tasche
#
# VARIANT: "audio" | "vision";  PORT: Reflexkanal;  ANT_STUB: SMA statt
# Flexantennen-Nische.

import adsk.core
import adsk.fusion
import traceback

VARIANT = "vision"
PORT = True
ANT_STUB = False

P = {
    "pcb_w": 52.0, "pcb_h": 52.0, "pcb_t": 1.6, "pcb_clear": 0.6,
    "top_clear": 8.0, "bot_clear": 3.4,
    "bat_t": 5.0, "bat_clear": 0.4,
    "wall": 5.0, "floor": 2.0, "lid_plate": 2.0,
    "lid_cavity": 9.2, "ledge": 2.0,
    # Nut/Feder (Nut in Basis-Stirnflaeche, Mittellinie 1.2 von aussen)
    "groove_w": 1.5, "groove_d": 1.5, "groove_off": 1.2,
    "tongue_clear": 0.15,        # Feder allseits schmaler/kuerzer
    # Schrauben M2 Inbus
    "scr_pos": 3.6,              # Achsabstand von jeder Aussenecke
    "scr_thru": 2.15, "scr_head_d": 3.95, "scr_head_h": 1.9,
    "ins_d": 3.2, "ins_depth": 4.5,
    # Lautsprecher K 28 WP
    "spk_d": 28.6, "spk_flange_t": 1.6, "spk_depth": 5.6,
    "boss_wall": 1.6, "chamber_h": 1.8,
    "horn_d1": 22.0, "horn_d2": 26.5, "grill_bar": 1.1,
    # Reflexkanal (Innenquerschnitt)
    "port_w": 3.0, "port_h": 3.0,
    # Display Waveshare 1.32" (verifiziert)
    "disp_mod_w": 34.30, "disp_mod_h": 30.50,
    "disp_win_w": 27.26, "disp_win_h": 20.54,
    "disp_off_x": 0.0, "disp_off_y": -0.98,
    # Durchbrueche (Platinen-Koordinaten)
    "usb_x": 12.0, "usb_w": 10.2, "usb_h": 4.0,
    "usb_pock_w": 15.0, "usb_pock_h": 8.5, "usb_pock_d": 3.0,
    "sw1_y": 45.5, "sw1_w": 9.5, "sw1_h": 4.2,
    "sw1_pock_w": 14.0, "sw1_pock_h": 8.0, "sw1_pock_d": 3.0,
    "rst_x": 47.0, "rst_y": 34.0, "rst_d": 1.6,
    "vent_y1": 19.6,
    "ant_d": 2.2, "ant_l": 46.0, "ant_h": 13.0,
    "stub_d": 6.4, "stub_y": 40.0,
}


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        try:
            root.name = f"AuraBip_{VARIANT}_v3"
        except Exception:
            pass

        sketches = root.sketches
        planes = root.constructionPlanes
        extrudes = root.features.extrudeFeatures
        NB = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
        xy = root.xYConstructionPlane

        def mm(v):
            return v / 10.0

        def plane_at(z):
            i = planes.createInput()
            i.setByOffset(xy, adsk.core.ValueInput.createByReal(mm(z)))
            return planes.add(i)

        def rect(plane, x1, y1, x2, y2):
            sk = sketches.add(plane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                adsk.core.Point3D.create(mm(x1), mm(y1), 0),
                adsk.core.Point3D.create(mm(x2), mm(y2), 0))
            return sk

        def ring(plane, x1, y1, x2, y2, inset):
            """Skizze mit 2 Rechtecken -> Ringprofil."""
            sk = sketches.add(plane)
            ln = sk.sketchCurves.sketchLines
            ln.addTwoPointRectangle(
                adsk.core.Point3D.create(mm(x1), mm(y1), 0),
                adsk.core.Point3D.create(mm(x2), mm(y2), 0))
            ln.addTwoPointRectangle(
                adsk.core.Point3D.create(mm(x1 + inset), mm(y1 + inset), 0),
                adsk.core.Point3D.create(mm(x2 - inset), mm(y2 - inset), 0))
            prof = None
            for i in range(sk.profiles.count):
                if sk.profiles.item(i).profileLoops.count == 2:
                    prof = sk.profiles.item(i)
            return prof

        def circ(plane, cx, cy, d):
            sk = sketches.add(plane)
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(mm(cx), mm(cy), 0), mm(d / 2.0))
            return sk

        def ext(sk_or_prof, dist, op, body=None):
            prof = (sk_or_prof.profiles.item(0)
                    if hasattr(sk_or_prof, "profiles") else sk_or_prof)
            i = extrudes.createInput(prof, op)
            i.setDistanceExtent(False,
                                adsk.core.ValueInput.createByReal(mm(dist)))
            if body is not None:
                i.participantBodies = [body]
            return extrudes.add(i)

        # ---------- Masse ----------
        in_w = P["pcb_w"] + 2 * P["pcb_clear"]
        in_h = P["pcb_h"] + 2 * P["pcb_clear"]
        out_w = in_w + 2 * P["wall"]
        out_h = in_h + 2 * P["wall"]
        z_bat = P["bat_t"] + 2 * P["bat_clear"]
        z_pcb_bot = P["floor"] + z_bat + P["bot_clear"]
        z_pcb_top = z_pcb_bot + P["pcb_t"]
        z_part = z_pcb_top + P["top_clear"] - P["lid_cavity"] + 2.0
        z_top = z_part + P["lid_cavity"] + P["lid_plate"]

        def bx(px):
            return P["wall"] + P["pcb_clear"] + px

        def by(py):
            return P["wall"] + P["pcb_clear"] + py

        scr_xy = [(P["scr_pos"], P["scr_pos"]),
                  (out_w - P["scr_pos"], P["scr_pos"]),
                  (P["scr_pos"], out_h - P["scr_pos"]),
                  (out_w - P["scr_pos"], out_h - P["scr_pos"])]

        # ================= BASIS =================
        base = ext(rect(xy, 0, 0, out_w, out_h), z_part, NB).bodies.item(0)
        base.name = "Basis"
        ext(rect(plane_at(P["floor"]), P["wall"], P["wall"],
                 P["wall"] + in_w, P["wall"] + in_h),
            z_part - P["floor"], CUT, base)

        # Platinen-Auflagesteg
        pl = plane_at(z_pcb_bot - 1.2)
        prof = ring(pl, P["wall"], P["wall"], P["wall"] + in_w,
                    P["wall"] + in_h, P["ledge"])
        i = extrudes.createInput(prof, JOIN)
        i.setDistanceExtent(False, adsk.core.ValueInput.createByReal(mm(1.2)))
        i.participantBodies = [base]
        extrudes.add(i)

        # Nut in der Basis-Stirnflaeche (Mittellinie groove_off+groove_w/2
        # von aussen; laeuft als Rechteckring komplett um)
        g0 = P["groove_off"]
        prof = ring(plane_at(z_part - P["groove_d"]), g0, g0,
                    out_w - g0, out_h - g0, P["groove_w"])
        i = extrudes.createInput(prof, CUT)
        i.setDistanceExtent(False,
                            adsk.core.ValueInput.createByReal(mm(P["groove_d"] + 0.1)))
        i.participantBodies = [base]
        extrudes.add(i)

        # Insert-Bohrungen (3.2 x 4.5) von der Stirnflaeche nach unten
        for (sx, sy) in scr_xy:
            ext(circ(plane_at(z_part - P["ins_depth"]), sx, sy, P["ins_d"]),
                P["ins_depth"] + 0.1, CUT, base)

        # USB-C: Durchbruch + Steckertasche aussen (Unterwand y=out_h)
        z_usb = z_pcb_top + 1.6
        ext(rect(plane_at(z_usb - P["usb_h"] / 2),
                 bx(P["usb_x"] - P["usb_w"] / 2), P["wall"] + in_h - 0.1,
                 bx(P["usb_x"] + P["usb_w"] / 2), out_h + 0.1),
            P["usb_h"], CUT, base)
        ext(rect(plane_at(z_usb - P["usb_pock_h"] / 2),
                 bx(P["usb_x"] - P["usb_pock_w"] / 2),
                 out_h - P["usb_pock_d"],
                 bx(P["usb_x"] + P["usb_pock_w"] / 2), out_h + 0.1),
            P["usb_pock_h"], CUT, base)

        # Schiebeschalter: Durchbruch + Fingertasche (linke Wand x=0)
        z_sw = z_pcb_top + 0.5
        ext(rect(plane_at(z_sw),
                 -0.1, by(P["sw1_y"] - P["sw1_w"] / 2),
                 P["wall"] + 0.1, by(P["sw1_y"] + P["sw1_w"] / 2)),
            P["sw1_h"], CUT, base)
        ext(rect(plane_at(z_sw - (P["sw1_pock_h"] - P["sw1_h"]) / 2),
                 -0.1, by(P["sw1_y"] - P["sw1_pock_w"] / 2),
                 P["sw1_pock_d"], by(P["sw1_y"] + P["sw1_pock_w"] / 2)),
            P["sw1_pock_h"], CUT, base)

        # Sensor-Schlitze rechte Wand
        for k in range(3):
            yy = by(P["vent_y1"] + 1.2 + k * 2.6)
            ext(rect(plane_at(z_pcb_top),
                     out_w - P["wall"] - 0.1, yy, out_w + 0.1, yy + 1.4),
                2.0, CUT, base)

        # Antennen-Nische innen an der Unterwand
        if not ANT_STUB:
            ext(rect(plane_at(P["floor"] + 1.0),
                     P["wall"] + 3.0, P["wall"] + in_h - 0.01,
                     P["wall"] + 3.0 + P["ant_l"],
                     P["wall"] + in_h + P["ant_d"] - 0.01),
                P["ant_h"], CUT, base)

        # ================= DECKEL =================
        pl_part = plane_at(z_part)
        lid = ext(rect(pl_part, 0, 0, out_w, out_h),
                  P["lid_cavity"] + P["lid_plate"], NB).bodies.item(0)
        lid.name = "Deckel"
        ext(rect(pl_part, P["wall"], P["wall"],
                 P["wall"] + in_w, P["wall"] + in_h),
            P["lid_cavity"], CUT, lid)

        # Feder (Gegenstueck zur Nut), nach unten aus der Deckel-Stirn
        tc = P["tongue_clear"]
        prof = ring(plane_at(z_part - P["groove_d"] + tc),
                    g0 + tc, g0 + tc, out_w - g0 - tc, out_h - g0 - tc,
                    P["groove_w"] - 2 * tc)
        i = extrudes.createInput(prof, JOIN)
        i.setDistanceExtent(False, adsk.core.ValueInput.createByReal(
            mm(P["groove_d"] - tc)))
        i.participantBodies = [lid]
        extrudes.add(i)

        # Schrauben: Durchgang + Kopfsenkung von oben
        for (sx, sy) in scr_xy:
            ext(circ(plane_at(z_part - P["groove_d"] - 0.1), sx, sy, P["scr_thru"]),
                P["lid_cavity"] + P["lid_plate"] + P["groove_d"] + 0.2, CUT, lid)
            ext(circ(plane_at(z_top - P["scr_head_h"]), sx, sy, P["scr_head_d"]),
                P["scr_head_h"] + 0.1, CUT, lid)

        # ---- Lautsprecher-Akustikmodul ----
        scx = P["wall"] + in_w / 2.0
        scy = out_h - P["wall"] - P["spk_d"] / 2.0 - 5.0
        boss_od = P["spk_d"] + 2 * P["boss_wall"]
        z_ceil = z_part + P["lid_cavity"]
        boss_h = P["spk_depth"] + P["spk_flange_t"] + P["chamber_h"] + 1.2

        sk = sketches.add(plane_at(z_ceil - boss_h))
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(mm(scx), mm(scy), 0), mm(boss_od / 2))
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(mm(scx), mm(scy), 0), mm(P["spk_d"] / 2))
        prof = None
        for k in range(sk.profiles.count):
            if sk.profiles.item(k).profileLoops.count == 2:
                prof = sk.profiles.item(k)
        i = extrudes.createInput(prof, JOIN)
        i.setDistanceExtent(False, adsk.core.ValueInput.createByReal(mm(boss_h)))
        i.participantBodies = [lid]
        extrudes.add(i)

        # Kabelschlitz unten in der Boss-Wand (Litzen zu J3)
        ext(rect(plane_at(z_ceil - boss_h + 1.2),
                 scx - 1.5, scy - boss_od / 2 - 0.5,
                 scx + 1.5, scy - P["spk_d"] / 2 + 0.5),
            2.6, CUT, lid)

        # Trichter + Gitter
        ext(circ(plane_at(z_ceil), scx, scy, P["horn_d1"]),
            P["lid_plate"] / 2, CUT, lid)
        ext(circ(plane_at(z_ceil + P["lid_plate"] / 2), scx, scy, P["horn_d2"]),
            P["lid_plate"] / 2 + 0.1, CUT, lid)
        for k in (-1, 0, 1):
            ext(rect(plane_at(z_ceil),
                     scx - P["horn_d2"] / 2, scy + k * 6.0 - P["grill_bar"] / 2,
                     scx + P["horn_d2"] / 2, scy + k * 6.0 + P["grill_bar"] / 2),
                P["lid_plate"], JOIN, lid)

        # ---- Reflexkanal: GESCHLOSSENER Kanal Kammer -> Aussenwand ----
        if PORT:
            zc_top = z_ceil                     # Kanaldecke = Deckeldecke
            zc_bot = z_ceil - P["port_h"]       # Kanalboden-Oberkante
            x0 = scx + P["spk_d"] / 2 - 0.5     # ab Kammer-Innenwand
            x1 = out_w - P["wall"] + 0.01       # bis Innenflaeche Aussenwand
            # 1) Durchbruch Boss-Wand
            ext(rect(plane_at(zc_bot),
                     x0, scy - P["port_w"] / 2,
                     scx + boss_od / 2 + 0.5, scy + P["port_w"] / 2),
                P["port_h"], CUT, lid)
            # 2) zwei Rippen (Kanalwaende) bis zur Aussenwand
            for off in (-P["port_w"] / 2 - 1.2, P["port_w"] / 2):
                ext(rect(plane_at(zc_bot),
                         scx + boss_od / 2 - 0.3, scy + off,
                         x1, scy + off + 1.2),
                    P["port_h"], JOIN, lid)
            # 3) Kanal-BODEN (schliesst den Kanal nach unten)
            ext(rect(plane_at(zc_bot - 1.2),
                     scx + boss_od / 2 - 0.3, scy - P["port_w"] / 2 - 1.2,
                     x1, scy + P["port_w"] / 2 + 1.2),
                1.2, JOIN, lid)
            # 4) Austritts-Tunnel durch die 5-mm-Aussenwand
            ext(rect(plane_at(zc_bot),
                     out_w - P["wall"] - 0.1, scy - P["port_w"] / 2,
                     out_w + 0.1, scy + P["port_w"] / 2),
                P["port_h"], CUT, lid)

        # RESET-Nadelloch
        ext(circ(plane_at(z_part), bx(P["rst_x"]), by(P["rst_y"]), P["rst_d"]),
            P["lid_cavity"] + P["lid_plate"] + 0.1, CUT, lid)

        if VARIANT == "vision":
            mcx = P["wall"] + in_w / 2.0
            mcy = P["wall"] + 16.0
            wcx = mcx + P["disp_off_x"]
            wcy = mcy + P["disp_off_y"]
            ext(rect(plane_at(z_ceil),
                     wcx - P["disp_win_w"] / 2, wcy - P["disp_win_h"] / 2,
                     wcx + P["disp_win_w"] / 2, wcy + P["disp_win_h"] / 2),
                P["lid_plate"] + 0.1, CUT, lid)
            ext(rect(plane_at(z_ceil - 0.6),
                     mcx - (P["disp_mod_w"] + 0.6) / 2,
                     mcy - (P["disp_mod_h"] + 0.6) / 2,
                     mcx + (P["disp_mod_w"] + 0.6) / 2,
                     mcy + (P["disp_mod_h"] + 0.6) / 2),
                0.6, CUT, lid)

        # ---- Kammerdeckel (separates Teil) ----
        cap = ext(circ(plane_at(z_ceil - boss_h - 1.4), scx, scy, boss_od),
                  1.2, NB).bodies.item(0)
        cap.name = "Kammerdeckel"
        ext(circ(plane_at(z_ceil - boss_h - 0.2), scx, scy, P["spk_d"] - 0.5),
            1.0, JOIN, cap)

        ui.messageBox(
            f"AuraBip-Gehaeuse v3 ({VARIANT}) — 3 Koerper.\n"
            f"Aussen: {out_w:.1f} x {out_h:.1f} x {z_top:.1f} mm"
            f"  (5-mm-Wand -> >60 mm!)\n\n"
            "Neu in v3: Nut/Feder-Dichtsitz, 4x M2-Inbus (Inserts 3.2x4.5),\n"
            "geschlossener Reflexkanal bis durch die Aussenwand,\n"
            "USB-C- und Schalter-Taschen (5-mm-Wand!).\n\n"
            "Einbau Lautsprecher: von innen in den Boss, Litzen durch\n"
            "den Schlitz, Kammerdeckel dicht einkleben.\n"
            "Passform: hardware/production/aurabip.step importieren.")
    except Exception:
        if ui:
            ui.messageBox("Fehler:\n{}".format(traceback.format_exc()))
