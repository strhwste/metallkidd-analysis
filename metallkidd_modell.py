"""
MetallKIDD – Nachbau der Kernrechnung (Wuppertal Institut, 2024, Version 0).

Jede Eingabe stammt aus einer Zelle von metallkidd.xlsx; der Zellbezug steht im
Kommentar. Defaults = Werte des Tools im Default-Szenario (BingGPT auf dem
Smartphone, Start 2023, Ende 2050).

Die Funktion `rechne(p, k)` rechnet das ganze Modell. `p` sind die Eingaben
(PARAMETER), `k` sind Schalter für die Korrekturen (KORREKTUR_V0 = Tool wie
ausgeliefert, KORREKTUR_NEU = korrigierte Fassung). So lässt sich jede
Korrektur einzeln an- und abschalten und ihre Wirkung beziffern.

Einheiten: Metall in Tonnen (t) der 15 bilanzierten Metalle, Energie in GWh/a
bzw. Wh, Rechenleistung in TFLOP und TFLOP/s.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from statistics import median

# ---------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------

METALLE = ["Antimon", "Beryllium", "Bor", "Gallium", "Indium", "Kobalt",
           "Magnesium", "Mangan", "Neodym", "Palladium", "Silizium",
           "Strontium", "Tantal", "Titan", "Wolfram"]

# g Metall pro Server ohne GPU (I_Modellierung_Server!N2:N16 in der Reihenfolge
# Antimon..Wolfram, Summe N17 = 632,64 g; Indium N6 und Wolfram N16 sind 0)
G_PRO_SERVER = [12.786676240332149, 0.42570275775739963, 44.869999573960214,
                0.8529648662758152, 0.0, 0.42570275775739963, 17.40112919159701,
                31.966690600830372, 3.9000000000000004, 0.8529648662758152,
                481.15408245708784, 1.7043703817906144, 36.08584546362563,
                0.21759792137131884, 0.0]

# davon aus PCB_2 (4.000 g Leiterplatte, I_Modellierung_Server!H2:H16, Summe H17 = 465,71 g)
G_PRO_SERVER_PCB2 = [12.378629051736635, 0.412117772088305, 38.44487388894257, 0.8257451330853582, 0.0, 0.412117772088305, 8.709187358098644, 30.94657262934158, 0.0, 0.8257451330853582, 347.1764437708324, 1.6499806772619683, 23.933022559296656, 0.0, 0.0]

# g Metall pro GPU-Karte (I_Modellierung_Server!F2:F16, Summe F17 = 17,31 g)
G_PRO_GPU = [0.5225418856811777, 0.009304690686497091, 0.8718698581284469,
             0.01864346448906194, 3.4083116067754917e-22, 0.009326640213244726,
             0.19663382650844508, 0.6987038793889757, 0.0, 0.01864346448906194,
             14.386483336507402, 0.03725284586205613, 0.5406795090114317,
             3.32651212821288e-05, 0.003816378530519901]

# g Metall pro Smartphone (DATEN_Endgerät_Smartphone!B2:B16)
G_PRO_SMARTPHONE = [0.07819185, 5.65e-06, 0.00336686, 0.00035174, 4.5e-06,
                    12.6675696, 4.52072024, 0.07039166, 0.086885, 0.00017865,
                    0.10572785, 0.00163777, 2.51e-05, 0.07793807, 0.74109501]

# Smartphone-Nutzer Deutschland 2009–2021, Datenwerte
# (B_Endgeräte_Nutzung_Smartphone!B4:B16); ab 2022 fortgeschrieben.
SMARTPHONE_NUTZER_DATEN = {2009: 6.31e6, 2010: 14.03e6, 2011: 21.3e6, 2012: 31e6,
                           2013: 37.4e6, 2014: 41.1e6, 2015: 46e6, 2016: 51e6,
                           2017: 54e6, 2018: 57e6, 2019: 57.7e6, 2020: 60.74e6,
                           2021: 62.61e6}

# EU-Bedarf 2016–2020 (Summe 5 Jahre, t) und Weltproduktion Ø 2016–2020 (t)
# aus O_Kritikalitäten!C5:C21 und N5:N21 (Mangan: Zeile 12 = Extraktion).
EU_BEDARF_5J = {"Antimon": 16667, "Beryllium": 5.5, "Bor": 51450, "Gallium": 30,
                "Indium": 6.5, "Kobalt": 10946, "Magnesium": 76766,
                "Mangan": 270394, "Neodym": 119, "Palladium": 20,
                "Silizium": 440968, "Strontium": 50000, "Tantal": 395,
                "Titan": 457050, "Wolfram": 17273}

# Recyclingquote min EOL-RIR in % (B_Recycling!D2:D16); Silizium leer = 0
EOL_RIR_MIN = {"Antimon": 27, "Beryllium": 7, "Bor": 0.6, "Gallium": 25,
               "Indium": 0.0011, "Kobalt": 34, "Magnesium": 33, "Mangan": 9,
               "Neodym": 1, "Palladium": 50, "Silizium": 0, "Strontium": 25,
               "Tantal": 25, "Titan": 91, "Wolfram": 42}


# ---------------------------------------------------------------------------
# Eingaben (Defaults = Tool)
# ---------------------------------------------------------------------------

@dataclass
class Parameter:
    # Block 1 – Endgeräte und Nutzer
    startjahr: int = 2023                 # MAIN!E17
    endjahr: int = 2050                   # Background_Parameter!B3
    wachstum_endgeraet: float = 0.005     # MAIN!E9
    daempfung_endgeraet: float = 0.10     # MAIN!E10
    erneuerung_endgeraet: float = 0.33    # MAIN!E11
    nutzeranteil: float = 0.20            # MAIN!E18 (KI_Nutzer_Anteil)
    geraete_pro_nutzer: float = 1.0       # MAIN!E19
    adoptionsrate: float = 0.55           # MAIN!E20 (wirkt in V0 nicht, s. u.)
    daempfung_ki: float = 0.30            # I_Endgerät!B6
    # Block 2 – KI-Modell
    anfragen_pro_tag: float = 15.0        # MAIN!K9
    rechenzeit_rw2_s: float = 30.0        # MAIN!K7
    tflop_inferenz: float = 3956.0        # MAIN!K15 = I_KI!E48 = 1 s × 989 × 4 GPU
    vram_modell_gb: float = 350.0         # MAIN!K16
    tflops_endgeraet_rw2: float = 2.29    # MAIN!K18
    wh_pro_anfrage: float = 3.71          # MAIN!K21 = Mittel I_KI!L62:L66
    wh_zusatz: float = 0.0                # MAIN!K22
    ueberkapazitaet: float = 0.50         # MAIN!K38
    rechenweg: str = "Durchschnitt"       # MAIN!K39: RW1..RW4, Durchschnitt, Median
    # GPU (B_KI!B33:B36, H100 SXM)
    gpu_tflops: float = 989.0             # B_KI!B34 (TF32)
    gpu_vram_gb: float = 80.0             # B_KI!B35
    gpu_watt: float = 700.0               # B_KI!B36
    # Rechenweg 4 (B_KI!N5:N10)
    rw4_ptotal: float = 800000.0          # B_KI!N5 = 1000 × N8 (Wh/s)
    rw4_ttpu: float = 10.0                # B_KI!N7
    rw4_pbusy: float = 800.0              # B_KI!N8
    rw4_pidle: float = 72.5               # B_KI!N9
    rw4_pue: float = 1.1                  # B_KI!N10
    # Block 3 – Server und Federated
    peripherie: float = 0.30              # MAIN!S11
    pcb2_g: float = 4000.0                # I_Modellierung_Server!B5; Doku D_Übersicht!D8: 264,9728 g
    erneuerung_server: float = 0.20       # MAIN!S12
    gpu_pro_server: float = 8.0           # MAIN!S13
    tflops_federated: float = 1.0         # MAIN!S14
    effizienz: float = 0.05               # MAIN!S15
    auslastung_federated: float = 0.10    # MAIN!S20
    mehraufwand_federated: float = 0.50   # MAIN!S23
    # Fest eingetragene Werte der Version 0 (nur wirksam, wenn k.feste_werte)
    v0_server_start: float = 2160.0       # Background_Parameter!B6
    v0_gpu_rw1: float = 2008.0            # B_KI!B16
    v0_gpu_rw1_oh: float = 3012.0         # B_KI!B17
    v0_gpu_rw2: float = 153.0             # B_KI!F16
    v0_gpu_rw2_oh: float = 230.0          # B_KI!F17
    v0_gpu_rw3: float = 41895.0           # B_KI!J19
    v0_gpu_rw3_oh: float = 62843.0        # B_KI!J20
    v0_gpu_l40: float = 19456.759051457804  # MAIN!L40
    v0_ki_nutzer_b7: float = 12647533.049999997  # B_KI!B7


@dataclass
class Korrektur:
    """Schalter: True = so wie in Version 0 (fehlerhaft), False = korrigiert."""
    feste_werte: bool = True        # Fehler 4: fest eingetragene Zwischenwerte
    eff_match: bool = True          # Fehler 2: 25 %/40 % fallen auf 20 %/30 % zurück
    endgeraet_versatz: int = 2      # Fehler 3: O_KI!BK4 = 20 → +2 Jahre
    peripherie_aus: bool = True     # Fehler 5: Peripherie wirkt nicht (Option)
    pd_neodym: bool = True          # Fehler 6: Palladium mit Neodym-Quote
    krit_faktor_gw: bool = True     # Fehler 7: Endgeräte-Faktor = MAIN!Z40 (GW)
    krit_mischgroesse: bool = True  # Fehler 8: kumuliert + Bestand gemischt
    rw1_teilt: bool = True          # Fehler 9: RW1 teilt durch 350/80
    # weitere gefundene Fehler:
    federated_vorlauf: bool = True  # B_Federated!G wächst schon ab 2021 (+3 Jahre)
    rw4_unverknuepft: bool = True   # B_KI!N5,N7,N8 nicht mit I_KI!E65:E67 verknüpft
    ohne_deckel: bool = True        # KI-Nutzer nicht auf Smartphone-Nutzer gedeckelt
    grau_fifo_v0: bool = True       # Generationenblatt: Abgang bei 2 leeren Jahrgängen
    energie_rw4: str = "v0"         # B_KI!N25: "v0" ×60, "wh_s" ×3600 (N5 als Wh/s), "watt" ×1 (N5 als W)


KORREKTUR_V0 = Korrektur()
# Hauptkorrektur: Fehler 2, 3, 4, 6, 7, 8, 9, dazu Federated-Vorlauf (Fund 10)
# und Nutzer-Deckel (Fund 12). Peripherie (5) und RW4-Verknüpfung (Fund 11)
# bleiben aus und werden als Option gerechnet.
KORREKTUR_NEU = Korrektur(feste_werte=False, eff_match=False, endgeraet_versatz=0,
                          peripherie_aus=True, pd_neodym=False, krit_faktor_gw=False,
                          krit_mischgroesse=False, rw1_teilt=False,
                          federated_vorlauf=False, rw4_unverknuepft=True,
                          ohne_deckel=False, grau_fifo_v0=True)


# ---------------------------------------------------------------------------
# 1. Nutzerzeitreihe (B_Endgeräte_Nutzung_Smartphone)
# ---------------------------------------------------------------------------

def nutzerzeitreihe(p: Parameter, k: Korrektur, bis: int | None = None):
    """Smartphone-Nutzer B(t) und KI-Nutzer C(t), dynamisches Modell.

    B(t) = B(t-1) · (1 + F(t-2))   (Spalte B nutzt die Rate zwei Zeilen höher)
    F(t) = E9 für t ≤ Start, sonst F(t-1) · (1 - E10)
    C(Start) = B(Start) · E18 · E19;  C(t) = C(t-1) · (1 + G(t-1))
    G(t) = 0,55 · 0,7^(t-Start) – in V0 als feste Zahlen (Spalte G), nicht
    mit MAIN!E20 verknüpft. Korrigiert: G(Start) = MAIN!E20.
    """
    bis = bis or p.endjahr + 4
    B = dict(SMARTPHONE_NUTZER_DATEN)
    F = {}
    for t in range(2009, bis + 1):
        F[t] = p.wachstum_endgeraet if t <= p.startjahr else F[t - 1] * (1 - p.daempfung_endgeraet)
    for t in range(2022, bis + 1):
        B[t] = B[t - 1] * (1 + F[t - 2])
    g0 = 0.55 if k.feste_werte else p.adoptionsrate
    C = {}
    for t in range(p.startjahr, bis + 1):
        if t == p.startjahr:
            c = B[t] * p.nutzeranteil * p.geraete_pro_nutzer
        else:
            c = C[t - 1] * (1 + g0 * (1 - p.daempfung_ki) ** (t - 1 - p.startjahr))
        if not k.ohne_deckel:
            # Deckel: nicht mehr KI-Nutzer als Smartphone-Nutzer (eigene Korrektur)
            c = min(c, B[t] * p.geraete_pro_nutzer)
        C[t] = c
    return B, C


# ---------------------------------------------------------------------------
# 2. GPU-Bedarf im Startjahr: vier Rechenwege (B_KI)
# ---------------------------------------------------------------------------

def gpu_rechenwege(p: Parameter, k: Korrektur, ki_nutzer: float) -> dict:
    """GPUs ohne Überkapazität je Rechenweg, dazu Mittel und Median.

    Anfragen/s  q = N · a / 86 400                       (B_KI!B15)
    RW1  t_I = TFLOP / P_GPU / (VRAM_M / VRAM_GPU)       (B_KI!B13)
         V0:   GPU = q · t_I                             (B16 fest: 2008)
         korr: GPU = q · t_I · (VRAM_M / VRAM_GPU) = q · TFLOP / P_GPU
    RW2  GPU = q / (P_GPU / (t_dev · P_dev))             (B_KI!F13, F14, F16)
    RW3  GPU = q · (Wh + Wh_zus) · 3600 / W_GPU          (B_KI!J13..J19)
    RW4  GPU = Ptot/(Pidle·PUE) − q·(Pbusy−Pidle)/(TTPU·Pidle)  (B_KI!N13)
    """
    nutzer = p.v0_ki_nutzer_b7 if k.feste_werte else ki_nutzer
    q = nutzer * p.anfragen_pro_tag / 86400.0
    instanz = p.vram_modell_gb / p.gpu_vram_gb             # 350/80 = 4,375 GPU
    t_i = p.tflop_inferenz / p.gpu_tflops / instanz        # 0,914 s
    rw1 = q * t_i if k.rw1_teilt else q * t_i * instanz
    rw2 = q / (p.gpu_tflops / (p.rechenzeit_rw2_s * p.tflops_endgeraet_rw2))
    rw3 = q * (p.wh_pro_anfrage + p.wh_zusatz) * 3600.0 / p.gpu_watt
    if k.rw4_unverknuepft:
        ptot, ttpu, pbusy = p.rw4_ptotal, p.rw4_ttpu, p.rw4_pbusy
    else:  # I_KI!E65:E67 (BingGPT-Spalte)
        ptot, ttpu, pbusy = 660000.0, 175.0, 96.0
    rw4_roh = ptot / (p.rw4_pidle * p.rw4_pue) - q * (pbusy - p.rw4_pidle) / (ttpu * p.rw4_pidle)
    # Fund 14: Bei festem Ptotal sinkt RW4 mit steigender Nachfrage und wird ab
    # q > 9 997 Anfragen/s negativ. Negative GPU-Zahlen werden auf 0 gesetzt.
    rw4 = max(rw4_roh, 0.0)
    ohne = {"RW1": rw1, "RW2": rw2, "RW3": rw3, "RW4": rw4}
    oh = 1 + p.ueberkapazitaet
    mit = {n: v * oh for n, v in ohne.items()}
    if k.feste_werte:
        # Version 0: RW1–RW3 sind feste Zahlen; nur RW4 (N13/N15) rechnet
        ohne.update(RW1=p.v0_gpu_rw1, RW2=p.v0_gpu_rw2, RW3=p.v0_gpu_rw3)
        mit.update(RW1=p.v0_gpu_rw1_oh, RW2=p.v0_gpu_rw2_oh, RW3=p.v0_gpu_rw3_oh)
    for d in (ohne, mit):
        werte = [d["RW1"], d["RW2"], d["RW3"], d["RW4"]]
        d["Durchschnitt"] = sum(werte) / 4
        d["Median"] = median(werte)
    return {"q": q, "ohne": ohne, "mit": mit, "t_rw1": t_i, "rw4_roh": rw4_roh}


# ---------------------------------------------------------------------------
# 3. Federated-Anteil (B_Federated, Background_Parameter)
# ---------------------------------------------------------------------------

def federated_anteil(p: Parameter, k: Korrektur, jahr_offset: int = 0) -> float:
    """Anteil der Rechenlast, den die KI-Smartphones übernehmen (MAIN!S22).

    verfügbar  H = N · G / (1 + S23),  G = S14 · S20 · (1 + S15)^n
    benötigt   I = N · a / 86 400 · TFLOP
    Anteil     J = H / I   (N kürzt sich heraus)
    V0: G wächst schon ab 2021 (B_Federated!G14), im Startjahr also n = 3.
    """
    n = (3 if k.federated_vorlauf else 0) + jahr_offset
    g = p.tflops_federated * p.auslastung_federated * (1 + p.effizienz) ** n
    verf = g / (1 + p.mehraufwand_federated)
    bedarf = p.anfragen_pro_tag / 86400.0 * p.tflop_inferenz
    return verf / bedarf


# ---------------------------------------------------------------------------
# 4. Generationenmodell (B_GPU_Generationen / B_Server_Generationen)
# ---------------------------------------------------------------------------

def generationen(start: float, zuwachs_neu: list[float], erneuerung: float,
                 effizienz: float, fifo_v0: bool = True):
    """Bestand je Jahrgang mit Erneuerung und Effizienz.

    Jahr i ≥ 1:
      AT_i  = Erneuerung · Bestand_{i-1}                 (gelb, Spalte AT)
      r_ig  = Abgang aus Jahrgang g, älteste zuerst      (grün, AW46:CH82)
      n_ig  = r_ig · (1 − e)^(i−g)  neue Einheiten als Ersatz (blau, AW6:CH42)
      neu_i = Σ_g n_ig + zuwachs_neu_i                   (Spalte CI + CM)
    Bestand des Jahrgangs g (grau, B5:AM42) – wie im Tool: ist der ältere
    Jahrgang leer, wird vom Jahrgang g (AT − Vorjahresbestand g−1) abgezogen.
    Bei fifo_v0=False wird stattdessen exakt r_ig abgezogen.
    Rückgabe: Liste neue Einheiten je Jahr (AO), Liste Bestand je Jahr (AN).
    """
    T = len(zuwachs_neu)
    S = [[0.0] * T for _ in range(T)]
    S[0][0] = start
    neu = [start]
    bestand = [start]
    for i in range(1, T):
        prev = S[i - 1]
        at = erneuerung * sum(prev)
        r = [0.0] * T
        for g in range(i):
            if prev[g] == 0:
                continue
            rest = at - sum(r[:g])
            r[g] = prev[g] if prev[g] < rest else rest
        ersatz = sum(r[g] * (1 - effizienz) ** (i - g) for g in range(i) if r[g] > 0)
        row = S[i]
        for g in range(i):
            if not fifo_v0:
                row[g] = max(prev[g] - r[g], 0.0)
            elif g == 0:
                row[0] = max(prev[0] - r[0], 0.0)
            else:
                row[g] = prev[g] if row[g - 1] > 0 else max(prev[g] - at + prev[g - 1], 0.0)
        row[i] = ersatz + zuwachs_neu[i]
        neu.append(row[i])
        bestand.append(sum(row))
    return neu, bestand


# ---------------------------------------------------------------------------
# 5. Gesamtrechnung
# ---------------------------------------------------------------------------

@dataclass
class Ergebnis:
    jahre: list
    ki_nutzer: dict
    smartphone_nutzer: dict
    rw: dict
    gpu_auswahl_oh: float
    federated: float
    gpu_start: float
    server_start: float
    gpu_neu: list
    server_neu: list
    gpu_bestand: list
    server_bestand: list
    metall_server_jahr: list        # t/a, Summe 15 Metalle (Server + GPU)
    metall_server_je_metall: dict   # t kumuliert 2023–Ende je Metall
    metall_server_kum: float
    metall_server_2023: float
    endgeraet_2023: dict            # t je Metall, O_KI Spalte „Endgeräte"
    endgeraet_zeile_ende: dict      # t je Metall, O_KI Zeile Endjahr
    endgeraet_kauf_kum: dict        # t je Metall, Jahreskäufe kumuliert (korr.)
    energie_2023: dict              # GWh/a je Rechenweg
    anfragen_2023: float


def wachstum_neu(nutzer: list[float], start: float, eff: float) -> list[float]:
    """B_Hyperscale_Anzahl!N/O: (Bedarf_t − Bedarf_{t−1}) · (1 − e)^(t−t0),
    Bedarf_t = Nutzer_t · (Einheiten_Start / Nutzer_Start)."""
    pro_nutzer = start / nutzer[0]
    bedarf = [n * pro_nutzer for n in nutzer]
    return [0.0] + [(bedarf[i] - bedarf[i - 1]) * (1 - eff) ** i for i in range(1, len(nutzer))]


def eff_fuer_zuwachs(eff: float, k: Korrektur) -> float:
    """V0: Zuwachs holt die Werte per ungefährem MATCH aus B_Hyperscale_Anzahl
    U:Y (nur 2,5/5/10/20/30 %): 25 % → 20 %, 40 % → 30 %."""
    if not k.eff_match or eff == 0:
        return eff
    stufen = [0.025, 0.05, 0.1, 0.2, 0.3]
    kandidaten = [s for s in stufen if s <= eff + 1e-12]
    return kandidaten[-1] if kandidaten else eff


def rechne(p: Parameter = Parameter(), k: Korrektur = KORREKTUR_V0,
           erneuerung: float | None = None, effizienz: float | None = None) -> Ergebnis:
    ern = p.erneuerung_server if erneuerung is None else erneuerung
    eff = p.effizienz if effizienz is None else effizienz
    jahre = list(range(p.startjahr, p.endjahr + 1))
    B, C = nutzerzeitreihe(p, k)
    nutzer = [C[t] for t in jahre]

    # Startjahr: GPUs nach Rechenweg, Überkapazität, Federated-Abzug
    rw = gpu_rechenwege(p, k, C[p.startjahr])
    if k.feste_werte:
        gpu_oh = p.v0_gpu_l40          # MAIN!L40 fest = B_KI!B45 (Durchschnitt)
    else:
        gpu_oh = rw["mit"][p.rechenweg]
    f = federated_anteil(p, k)
    gpu0 = gpu_oh * (1 - f)            # MAIN!S21
    server0 = p.v0_server_start if k.feste_werte else gpu0 / p.gpu_pro_server

    # Zeitreihen mit Erneuerung und Effizienz (Generationenmodell)
    e_z = eff_fuer_zuwachs(eff, k)
    gpu_neu, gpu_best = generationen(gpu0, wachstum_neu(nutzer, gpu0, e_z), ern, eff, k.grau_fifo_v0)
    srv_neu, srv_best = generationen(server0, wachstum_neu(nutzer, server0, e_z), ern, eff, k.grau_fifo_v0)

    # Metall Server + GPU (O_KI / O_Metallbedarf_Server)
    fp = 1.0 if k.peripherie_aus else 1.0 + p.peripherie
    # PCB_2-Anteil skaliert linear mit dem Leiterplattengewicht (Variante „PCB laut Doku“)
    w_srv = [G_PRO_SERVER[m] - G_PRO_SERVER_PCB2[m] * (1 - p.pcb2_g / 4000.0) for m in range(15)]
    je_metall_jahr = [[(w_srv[m] * fp * s + G_PRO_GPU[m] * g) / 1e6
                       for m in range(15)] for s, g in zip(srv_neu, gpu_neu)]
    jahr = [sum(x) for x in je_metall_jahr]
    je_metall_kum = {METALLE[m]: sum(x[m] for x in je_metall_jahr) for m in range(15)}

    # Endgeräte-Allokation (O_KI Spalte „Endgeräte", Endgerät_Allokation = S22)
    v = k.endgeraet_versatz
    end23 = {METALLE[m]: C[p.startjahr + v] * G_PRO_SMARTPHONE[m] * f / 1e6 for m in range(15)}
    endE = {METALLE[m]: C[p.endjahr + v] * G_PRO_SMARTPHONE[m] * f / 1e6 for m in range(15)}
    # Jahreskäufe der zugerechneten Geräte, Logik wie B_Endgeräte_Nutzung!E
    # (Absatz = Zuwachs + Erneuerungsrate · Vorjahresbestand), Startjahr = Bestand
    kaeufe = [nutzer[0]] + [max(nutzer[i] - nutzer[i - 1], 0) + p.erneuerung_endgeraet * nutzer[i - 1]
                            for i in range(1, len(nutzer))]
    kauf_kum = {METALLE[m]: sum(kaeufe) * p.geraete_pro_nutzer * G_PRO_SMARTPHONE[m] * f / 1e6
                for m in range(15)}

    # Energie 2023 (B_KI!B25, F25, J25, N25), GWh/a
    h = 8760.0
    anfr = (p.v0_ki_nutzer_b7 if k.feste_werte else C[p.startjahr]) * p.anfragen_pro_tag * 365
    ptot = p.rw4_ptotal if k.rw4_unverknuepft else 660000.0
    energie = {"RW1": rw["mit"]["RW1"] * h * p.gpu_watt / 1e9,
               "RW2": rw["mit"]["RW2"] * h * p.gpu_watt / 1e9,
               "RW3": anfr * (p.wh_pro_anfrage + p.wh_zusatz) / 1e9,
               "RW4": ptot * {"v0": 60, "wh_s": 3600, "watt": 1}[k.energie_rw4] * 24 * 365 / 1e9}

    return Ergebnis(jahre, C, B, rw, gpu_oh, f, gpu0, server0, gpu_neu, srv_neu,
                    gpu_best, srv_best, jahr, je_metall_kum, sum(jahr), jahr[0],
                    end23, endE, kauf_kum, energie, anfr)


# ---------------------------------------------------------------------------
# 6. Auswertungen
# ---------------------------------------------------------------------------

def recycling_palladium(e: Ergebnis, k: Korrektur) -> float:
    """Sekundär-Palladium kumuliert (B_Recycling!AJ4:AJ31, ohne ES, Ern. MAIN,
    Eff. 0): Jahresbedarf · EOL-RIR. V0 nimmt ab 2024 die Neodym-Quote 1 %."""
    m = METALLE.index("Palladium")
    q0 = EOL_RIR_MIN["Palladium"] / 100
    q1 = EOL_RIR_MIN["Neodym"] / 100 if k.pd_neodym else q0
    jahr = [(G_PRO_SERVER[m] * s + G_PRO_GPU[m] * g) / 1e6 for s, g in zip(e.server_neu, e.gpu_neu)]
    return jahr[0] * q0 + sum(jahr[1:]) * q1


def kritikalitaet(e_oki: Ergebnis, k: Korrektur, faktor_server: float = 51.149696,
                  faktor_endgeraet_v0: float = 0.6802009115790197,
                  faktor_endgeraet_neu: float = 51.149696) -> dict:
    """O_Kritikalitäten: Anteil des KI-Bedarfs pro Jahr am EU-Jahresbedarf.

    V0:  H = (Server_kum + Endgerät_Zeile2050)/28 / D,  L = J · MAIN!Z40
    korr: Endgerät = Jahreskäufe kumuliert (Fehler 8), L = J · Faktor (Fehler 7).
    faktor_server = MAIN!X40; faktor_endgeraet_neu = MAIN!X40 (Annahme, s. Text).
    """
    jahre = len(e_oki.jahre)
    out = {}
    for m in METALLE:
        d = EU_BEDARF_5J[m] / 5
        srv = e_oki.metall_server_je_metall[m]
        end = e_oki.endgeraet_zeile_ende[m] if k.krit_mischgroesse else e_oki.endgeraet_kauf_kum[m]
        fe = faktor_endgeraet_v0 if k.krit_faktor_gw else faktor_endgeraet_neu
        H = (srv + end) / jahre / d
        I = srv / jahre / d
        J = end / jahre / d
        out[m] = {"H": H, "I": I, "J": J, "M": I * faktor_server + J * fe}
    return out


if __name__ == "__main__":
    for name, k in (("Version 0", KORREKTUR_V0), ("korrigiert", KORREKTUR_NEU)):
        e = rechne(Parameter(), k)
        print(f"{name}: GPU Start {e.gpu_start:,.1f}, Server {e.server_start:,.1f}, "
              f"Metall 2023 {e.metall_server_2023:.4f} t, kum. {e.metall_server_kum:.2f} t")
