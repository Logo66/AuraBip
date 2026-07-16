# AuraPIP — parametrisches Gehäuse für Fusion 360, v4 (Neuaufbau)
# © 2026 KIE Engineering. Proprietär.
#
# Ausführen: UTILITIES -> ADD-INS (Shift+S) -> Skripte -> "+" -> diesen
# Ordner wählen -> aurapip_case. Erzeugt 4 Körper:
#   Basis, Deckel, Kammerdeckel, Displayrahmen
#
# v4 (Ivo, 2026-07-16) — Neuaufbau wegen Display-Einbau:
#   - DISPLAY GANZ NACH OBEN: Fenster + Modul-Tasche sitzen direkt unter
#     der Gehäuse-Oberkante. Echter Einbau statt 0.6-mm-Mulde:
#     Modul liegt in einer Tasche (Glas nach vorn, Moosgummi-Band),
#     ein gedruckter DISPLAYRAHMEN klemmt es von hinten gegen den Deckel
#     (2x M2.2-Schrauben in seitliche Bosse) — unabhängig von den
#     Modul-Bohrlöchern, kein Kleben.
#   - LAUTSPRECHER VOLL SICHTBAR: kein 22-mm-Trichter mehr; volle
#     Öffnung (spk_d - 2x Lippe), optional 2 dünne Schutzstege.
#   - RUNDUNG UNTEN RAUSGEZOGEN: halbrunde Ausbuchtung an der Unterkante
#     (beide Halbschalen). Der Lautsprecher wandert ~12 mm nach unten in
#     die Rundung -> die Deckelfläche darüber wird fürs Display frei.
#   - WICHTIG: PLATINE UM 180° GEDREHT einbauen! USB liegt jetzt an der
#     OBERKANTE (sonst Kollision mit der Rundung), Schalter rechts,
#     Sensor-Schlitze links. Alle Durchbrüche sind entsprechend gespiegelt.
#   - Dichtsitz (Nut/Feder) läuft wie v3 um — mit bewusster LÜCKE über
#     der Lautsprecher-Zone (die ist akustisch eh offen; K28 ist WP).
#
# VARIANT: "audio" | "vision";  PORT: Reflexöffnung;  GRILL_BARS: 0 = ganz
# offen, 2 = zwei dünne Schutzstege.

import adsk.core
import adsk.fusion
import traceback

VARIANT = "vision"
PORT = True
ANT_STUB = False
GRILL_BARS = 2

P = {
    "pcb_w": 52.0, "pcb_h": 52.0, "pcb_t": 1.6, "pcb_clear": 0.6,
    "top_clear": 8.0, "bot_clear": 3.4,
    "bat_t": 5.0, "bat_clear": 0.4,
    "wall": 5.0, "floor": 2.0, "lid_plate": 2.0,
    "lid_cavity": 9.2, "ledge": 2.0,
    # Nut/Feder (Nut in Basis-Stirnflaeche, Mittellinie 1.2 von aussen)
    "groove_w": 1.5, "groove_d": 1.5, "groove_off": 1.2,
    "tongue_clear": 0.15,
    # Schrauben M2 Inbus (Gehaeuse-Ecken)
    "scr_pos": 3.6,
    "scr_thru": 2.15, "scr_head_d": 3.95, "scr_head_h": 1.9,
    "ins_d": 3.2, "ins_depth": 4.5,
    # Lautsprecher K 28 WP
    "spk_d": 28.6, "spk_flange_t": 1.6, "spk_depth": 5.6,
    "boss_wall": 1.6, "chamber_h": 1.8,
    "spk_drop": 12.0,          # so weit rutscht der Lautsprecher nach unten
    "bulge_wall": 3.0,         # Wandstaerke der Rundung um die Kammer
    "spk_open_lip": 1.5,       # Rand um die volle Oeffnung
    "grill_bar": 1.1,
    # Reflexoeffnung (direkt durch die Rundungswand nach unten)
    "port_w": 3.0, "port_h": 3.0,
    # Display Waveshare 1.32" (Masse verifiziert, v3)
    "disp_mod_w": 34.30, "disp_mod_h": 30.50,
    "disp_win_w": 27.26, "disp_win_h": 20.54,
    "disp_off_x": 0.0, "disp_off_y": -0.98,
    "disp_top_gap": 1.5,       # Abstand Modul-Oberkante zur Innenwand oben
    "disp_pock_d": 1.0,        # Taschen-Tiefe im Deckel (Glas + Moosgummi)
    "disp_stack": 4.2,         # Modulhoehe Glas+PCB unter der Deckeldecke
    "disp_boss_d": 6.0, "disp_boss_pilot": 1.8,   # M2.2 selbstschneidend
    "frame_t": 2.0, "frame_ear": 8.0, "frame_hole": 2.4,
    # Durchbrueche (Platinen-Koordinaten wie v3; Einbau um 180° GEDREHT)
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
            root.name = f"AuraPIP_{VARIANT}_v4"
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

        def all_profiles(sk):
            coll = adsk.core.ObjectCollection.create()
            for i in range(sk.profiles.count):
                coll.add(sk.profiles.item(i))
            return coll

        def ext(sk_or_prof, dist, op, body=None, everything=False):
            if everything:
                prof = all_profiles(sk_or_prof)
            else:
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
        z_ceil = z_part + P["lid_cavity"]

        cx = out_w / 2.0
        # Lautsprecher-Zentrum: v3-Lage minus spk_drop weiter unten
        y_ch = out_h - P["wall"] - P["spk_d"] / 2.0 + P["spk_drop"]
        boss_od = P["spk_d"] + 2 * P["boss_wall"]
        r_bulge = boss_od / 2.0 + P["bulge_wall"]
        boss_h = P["spk_depth"] + P["spk_flange_t"] + P["chamber_h"] + 1.2

        def bx(px):
            return P["wall"] + P["pcb_clear"] + px

        def by(py):
            return P["wall"] + P["pcb_clear"] + py

        # Platine liegt um 180° gedreht im Gehaeuse:
        def rx(px):          # gespiegelte x-Koordinate
            return out_w - bx(px)

        def ry(py):          # gespiegelte y-Koordinate
            return out_h - by(py)

        scr_xy = [(P["scr_pos"], P["scr_pos"]),
                  (out_w - P["scr_pos"], P["scr_pos"]),
                  (P["scr_pos"], out_h - P["scr_pos"]),
                  (out_w - P["scr_pos"], out_h - P["scr_pos"])]

        def outline_sketch(plane):
            """Quadrat + Halbrund-Ausbuchtung unten (ueberlappend)."""
            sk = sketches.add(plane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                adsk.core.Point3D.create(0, 0, 0),
                adsk.core.Point3D.create(mm(out_w), mm(out_h), 0))
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(mm(cx), mm(y_ch), 0), mm(r_bulge))
            return sk

        # ================= BASIS =================
        base = ext(outline_sketch(xy), z_part, NB,
                   everything=True).bodies.item(0)
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

        # Nut in der Basis-Stirnflaeche (voller Ring; im Rundungs-Bereich
        # liegt sie in der Ausbuchtung — dort hat die Feder eine Luecke)
        g0 = P["groove_off"]
        prof = ring(plane_at(z_part - P["groove_d"]), g0, g0,
                    out_w - g0, out_h - g0, P["groove_w"])
        i = extrudes.createInput(prof, CUT)
        i.setDistanceExtent(False,
                            adsk.core.ValueInput.createByReal(mm(P["groove_d"] + 0.1)))
        i.participantBodies = [base]
        extrudes.add(i)

        # Freistellung in der Basis-Stirn unter dem Kammer-Boss (der ragt
        # 1 mm unter die Trennebene; im Rundungs-Bereich ist die Basis voll)
        ext(circ(plane_at(z_part - 1.8), cx, y_ch, boss_od + 0.8),
            1.9, CUT, base)

        # Insert-Bohrungen (3.2 x 4.5) von der Stirnflaeche nach unten
        for (sx, sy) in scr_xy:
            ext(circ(plane_at(z_part - P["ins_depth"]), sx, sy, P["ins_d"]),
                P["ins_depth"] + 0.1, CUT, base)

        # USB-C: jetzt an der OBERKANTE (y=0), gespiegelt + Steckertasche
        z_usb = z_pcb_top + 1.6
        ux = rx(P["usb_x"])
        ext(rect(plane_at(z_usb - P["usb_h"] / 2),
                 ux - P["usb_w"] / 2, -0.1,
                 ux + P["usb_w"] / 2, P["wall"] + 0.1),
            P["usb_h"], CUT, base)
        ext(rect(plane_at(z_usb - P["usb_pock_h"] / 2),
                 ux - P["usb_pock_w"] / 2, -0.1,
                 ux + P["usb_pock_w"] / 2, P["usb_pock_d"]),
            P["usb_pock_h"], CUT, base)

        # Schiebeschalter: jetzt RECHTE Wand (x=out_w), gespiegelt
        z_sw = z_pcb_top + 0.5
        sy1 = ry(P["sw1_y"])
        ext(rect(plane_at(z_sw),
                 out_w - P["wall"] - 0.1, sy1 - P["sw1_w"] / 2,
                 out_w + 0.1, sy1 + P["sw1_w"] / 2),
            P["sw1_h"], CUT, base)
        ext(rect(plane_at(z_sw - (P["sw1_pock_h"] - P["sw1_h"]) / 2),
                 out_w - P["sw1_pock_d"], sy1 - P["sw1_pock_w"] / 2,
                 out_w + 0.1, sy1 + P["sw1_pock_w"] / 2),
            P["sw1_pock_h"], CUT, base)

        # Sensor-Schlitze: jetzt LINKE Wand
        for k in range(3):
            yy = ry(P["vent_y1"] + 1.2 + k * 2.6) - 1.4
            ext(rect(plane_at(z_pcb_top),
                     -0.1, yy, P["wall"] + 0.1, yy + 1.4),
                2.0, CUT, base)

        # Antennen-Nische: jetzt innen an der OBERWAND
        if not ANT_STUB:
            ext(rect(plane_at(P["floor"] + 1.0),
                     P["wall"] + 3.0, P["wall"] - P["ant_d"] + 0.01,
                     P["wall"] + 3.0 + P["ant_l"], P["wall"] + 0.01),
                P["ant_h"], CUT, base)

        # ================= DECKEL =================
        pl_part = plane_at(z_part)
        lid = ext(outline_sketch(pl_part),
                  P["lid_cavity"] + P["lid_plate"], NB,
                  everything=True).bodies.item(0)
        lid.name = "Deckel"
        ext(rect(pl_part, P["wall"], P["wall"],
                 P["wall"] + in_w, P["wall"] + in_h),
            P["lid_cavity"], CUT, lid)

        # Feder (Gegenstueck zur Nut)
        tc = P["tongue_clear"]
        prof = ring(plane_at(z_part - P["groove_d"] + tc),
                    g0 + tc, g0 + tc, out_w - g0 - tc, out_h - g0 - tc,
                    P["groove_w"] - 2 * tc)
        i = extrudes.createInput(prof, JOIN)
        i.setDistanceExtent(False, adsk.core.ValueInput.createByReal(
            mm(P["groove_d"] - tc)))
        i.participantBodies = [lid]
        extrudes.add(i)

        # Feder-LUECKE ueber der Lautsprecher-Zone (sonst versperrt der
        # Feder-Steg die Kammer-Oeffnung; Zone ist akustisch eh offen)
        ext(rect(plane_at(z_part - P["groove_d"] - 0.1),
                 cx - 17.5, out_h - g0 - P["groove_w"] - 0.4,
                 cx + 17.5, out_h + 0.2),
            P["groove_d"] + 0.3, CUT, lid)

        # Schrauben: Durchgang + Kopfsenkung von oben
        for (sx, sy) in scr_xy:
            ext(circ(plane_at(z_part - P["groove_d"] - 0.1), sx, sy, P["scr_thru"]),
                P["lid_cavity"] + P["lid_plate"] + P["groove_d"] + 0.2, CUT, lid)
            ext(circ(plane_at(z_top - P["scr_head_h"]), sx, sy, P["scr_head_d"]),
                P["scr_head_h"] + 0.1, CUT, lid)

        # ---- Lautsprecher in der Rundung ----
        # 1) Kammer-Hohlraum ausschneiden (funktioniert in Luft UND im
        #    soliden Rundungs-Bereich gleichermassen)
        ext(circ(plane_at(z_ceil - boss_h), cx, y_ch, P["spk_d"]),
            boss_h - 0.01, CUT, lid)
        # 2) Boss-Ring auffuellen (dort wo Kammer in der Deckel-Kavitaet liegt)
        sk = sketches.add(plane_at(z_ceil - boss_h))
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(mm(cx), mm(y_ch), 0), mm(boss_od / 2))
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(mm(cx), mm(y_ch), 0), mm(P["spk_d"] / 2))
        prof = None
        for k in range(sk.profiles.count):
            if sk.profiles.item(k).profileLoops.count == 2:
                prof = sk.profiles.item(k)
        i = extrudes.createInput(prof, JOIN)
        i.setDistanceExtent(False, adsk.core.ValueInput.createByReal(mm(boss_h)))
        i.participantBodies = [lid]
        extrudes.add(i)

        # 3) Volle Front-Oeffnung (Lautsprecher sichtbar), nur schmale Lippe
        open_d = P["spk_d"] - 2 * P["spk_open_lip"]
        ext(circ(plane_at(z_ceil), cx, y_ch, open_d),
            P["lid_plate"] + 0.1, CUT, lid)
        # optionale Schutzstege
        for k in range(GRILL_BARS):
            off = (k - (GRILL_BARS - 1) / 2.0) * 9.0
            ext(rect(plane_at(z_ceil),
                     cx - open_d / 2, y_ch + off - P["grill_bar"] / 2,
                     cx + open_d / 2, y_ch + off + P["grill_bar"] / 2),
                P["lid_plate"], JOIN, lid)

        # 4) Kabelschlitz nach oben in den Innenraum (Litzen zu J3)
        ext(rect(plane_at(z_ceil - boss_h + 1.2),
                 cx - 1.5, y_ch - boss_od / 2 - 0.5,
                 cx + 1.5, y_ch - P["spk_d"] / 2 + 0.5),
            2.6, CUT, lid)

        # 5) Reflexoeffnung direkt durch die Rundungswand nach unten
        if PORT:
            ext(rect(plane_at(z_ceil - boss_h + 1.2),
                     cx - P["port_w"] / 2, y_ch,
                     cx + P["port_w"] / 2, y_ch + r_bulge + 0.1),
                P["port_h"], CUT, lid)

        # RESET-Nadelloch (gespiegelt)
        ext(circ(plane_at(z_part), rx(P["rst_x"]), ry(P["rst_y"]), P["rst_d"]),
            P["lid_cavity"] + P["lid_plate"] + 0.1, CUT, lid)

        # ---- Display GANZ OBEN (vision) ----
        frame = None
        if VARIANT == "vision":
            mcx = P["wall"] + in_w / 2.0
            mcy = P["wall"] + P["disp_top_gap"] + P["disp_mod_h"] / 2.0
            wcx = mcx + P["disp_off_x"]
            wcy = mcy + P["disp_off_y"]
            # Sichtfenster
            ext(rect(plane_at(z_ceil),
                     wcx - P["disp_win_w"] / 2, wcy - P["disp_win_h"] / 2,
                     wcx + P["disp_win_w"] / 2, wcy + P["disp_win_h"] / 2),
                P["lid_plate"] + 0.1, CUT, lid)
            # Modul-Tasche (Glas + Moosgummi-Band liegen darin)
            ext(rect(plane_at(z_ceil - P["disp_pock_d"]),
                     mcx - (P["disp_mod_w"] + 0.6) / 2,
                     mcy - (P["disp_mod_h"] + 0.6) / 2,
                     mcx + (P["disp_mod_w"] + 0.6) / 2,
                     mcy + (P["disp_mod_h"] + 0.6) / 2),
                P["disp_pock_d"], CUT, lid)
            # 2 Klemm-Bosse links/rechts des Moduls
            boss_hh = P["disp_stack"] - P["disp_pock_d"]
            bx1 = mcx - (P["disp_mod_w"] / 2 + 4.0)
            bx2 = mcx + (P["disp_mod_w"] / 2 + 4.0)
            for bxx in (bx1, bx2):
                ext(circ(plane_at(z_ceil - boss_hh), bxx, mcy, P["disp_boss_d"]),
                    boss_hh, JOIN, lid)
                ext(circ(plane_at(z_ceil - boss_hh), bxx, mcy,
                         P["disp_boss_pilot"]),
                    boss_hh - 0.01 + 1.0, CUT, lid)
            # Displayrahmen (separates Teil): klemmt das Modul gegen den Deckel
            z_fr = z_ceil - P["disp_stack"] - P["frame_t"]
            frame = ext(rect(plane_at(z_fr),
                             bx1 - P["frame_ear"] / 2, mcy - P["disp_mod_h"] / 2,
                             bx2 + P["frame_ear"] / 2, mcy + P["disp_mod_h"] / 2),
                        P["frame_t"], NB).bodies.item(0)
            frame.name = "Displayrahmen"
            # grosse Aussparung fuer Bauteile/Stecker auf der Modul-Rueckseite
            ext(rect(plane_at(z_fr),
                     mcx - (P["disp_mod_w"] - 6.0) / 2,
                     mcy - (P["disp_mod_h"] - 6.0) / 2,
                     mcx + (P["disp_mod_w"] - 6.0) / 2,
                     mcy + (P["disp_mod_h"] - 6.0) / 2),
                P["frame_t"] + 0.1, CUT, frame)
            # Schraubenloecher (fluchten mit den Bossen)
            for bxx in (bx1, bx2):
                ext(circ(plane_at(z_fr), bxx, mcy, P["frame_hole"]),
                    P["frame_t"] + 0.1, CUT, frame)

        # ---- Kammerdeckel (separates Teil) ----
        cap = ext(circ(plane_at(z_ceil - boss_h - 1.4), cx, y_ch, boss_od),
                  1.2, NB).bodies.item(0)
        cap.name = "Kammerdeckel"
        ext(circ(plane_at(z_ceil - boss_h - 0.2), cx, y_ch, P["spk_d"] - 0.5),
            1.0, JOIN, cap)

        bulge_out = y_ch + r_bulge - out_h
        ui.messageBox(
            f"AuraPIP-Gehaeuse v4 ({VARIANT}) — 4 Koerper.\n"
            f"Aussen: {out_w:.1f} x {out_h:.1f} (+{bulge_out:.1f} Rundung) "
            f"x {z_top:.1f} mm\n\n"
            "NEU v4:\n"
            "- Display ganz oben; Einbau: Modul in die Tasche (Glas nach vorn,\n"
            "  rundum 2-mm-Moosgummi-Band als Auflage), Displayrahmen dahinter\n"
            "  mit 2x M2.2 in die Bosse schrauben -> klemmt, kein Kleben.\n"
            "- Lautsprecher voll sichtbar in der unteren Rundung\n"
            f"  (Oeffnung {P['spk_d'] - 2 * P['spk_open_lip']:.1f} mm, "
            f"{GRILL_BARS} Schutzstege).\n"
            "- PLATINE UM 180 GRAD GEDREHT einbauen: USB oben, Schalter\n"
            "  rechts, Sensorik links!\n"
            "- Dichtring hat bewusst eine Luecke ueber der Lautsprecher-Zone\n"
            "  (dort akustisch offen; K28 ist wasserfest).\n\n"
            "Einbau Lautsprecher: von innen in den Boss, Litzen durch den\n"
            "Schlitz nach oben, Kammerdeckel dicht einkleben.\n"
            "Passform: hardware/production/aurabip.step importieren\n"
            "(um 180 Grad gedreht platzieren).")
    except Exception:
        if ui:
            ui.messageBox("Fehler:\n{}".format(traceback.format_exc()))
