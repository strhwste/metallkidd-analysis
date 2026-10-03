"""Korrekturen, Sensitivität, Monte Carlo, funktionale Einheit, Abbildungen.
Gibt Markdown-Tabellen auf stdout aus (Grundlage für rechnung-neu.md)."""
import math
import random
import numpy as np
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
from metallkidd_modell import *

P = Parameter()
V0, NEU = KORREKTUR_V0, KORREKTUR_NEU


def pct(a, b):
    return (b / a - 1) * 100 if a else float("nan")


def kennzahlen(p, k, ern=None, eff=None):
    e = rechne(p, k, erneuerung=ern, effizienz=eff)
    e0 = rechne(p, k, erneuerung=0.2, effizienz=0.0)
    kr = kritikalitaet(e0, k)
    return {
        "GPU RW1 2023 (ohne Überkap.)": e.rw["ohne"]["RW1"],
        "GPU Mittel 2023 (mit Überkap.)": e.gpu_auswahl_oh,
        "Federated-Anteil 2023": e.federated,
        "GPUs Startjahr (MAIN!S21)": e.gpu_start,
        "Server Startjahr": e.server_start,
        "Metall Server+GPU 2023 (t)": e.metall_server_2023,
        "Metall kum. 2023–2050, Ern20/Eff5 (t)": e.metall_server_kum,
        "Metall kum. 2023–2050, Ern20/Eff0 (t)": e0.metall_server_kum,
        "Metall kum. Ern20/Eff40 (t)": rechne(p, k, erneuerung=0.2, effizienz=0.4).metall_server_kum,
        "Metall kum. Ern0/Eff40 (t)": rechne(p, k, erneuerung=0.0, effizienz=0.4).metall_server_kum,
        "Kobalt Endgeräte 2023 (t)": e.endgeraet_2023["Kobalt"],
        "Kobalt Endgeräte, O_Krit-Spalte G (t)": (e0.endgeraet_zeile_ende if k.krit_mischgroesse else e0.endgeraet_kauf_kum)["Kobalt"],
        "Palladium sekundär kum., Ern20/Eff0 (t)": recycling_palladium(e0, k),
        "Krit. H Kobalt (% EU-Bedarf/a)": kr["Kobalt"]["H"] * 100,
        "Krit. M Kobalt mit Faktor (%)": kr["Kobalt"]["M"] * 100,
        "Krit. M Tantal mit Faktor (%)": kr["Tantal"]["M"] * 100,
        "Energie RW-Mittel 2023 (GWh/a)": sum(e.energie_2023.values()) / 4,
    }


# --- C) Korrekturen einzeln und gesamt -------------------------------------
einzeln = [
    ("2 Effizienz-MATCH", dict(eff_match=False)),
    ("3 Endgeräte-Versatz", dict(endgeraet_versatz=0)),
    ("4 feste Werte", dict(feste_werte=False)),
    ("5 Peripherie (Option)", dict(peripherie_aus=False)),
    ("6 Palladium-Quote", dict(pd_neodym=False)),
    ("7 Faktor Endgerät", dict(krit_faktor_gw=False)),
    ("8 Mischgröße", dict(krit_mischgroesse=False)),
    ("9 RW1 ×350/80 (setzt 4 voraus)", dict(feste_werte=False, rw1_teilt=False)),
    ("10 Federated-Vorlauf (setzt 4 voraus)", dict(feste_werte=False, federated_vorlauf=False)),
    ("11 RW4 verknüpft (Option, setzt 4 voraus)", dict(feste_werte=False, rw4_unverknuepft=False)),
    ("12 Nutzer-Deckel", dict(ohne_deckel=False)),
    ("13 Abgang Generationen exakt FIFO", dict(grau_fifo_v0=False)),
]
basis = kennzahlen(P, V0)
neu = kennzahlen(P, NEU)
neu_p = kennzahlen(P, replace(NEU, peripherie_aus=False))
neu_11 = kennzahlen(P, replace(NEU, rw4_unverknuepft=False))

print("## C1 Gesamt\n| Kennzahl | Version 0 | korrigiert | Änderung % | korr. + Peripherie 30 % | Änderung % |\n|---|---|---|---|---|---|")
for n in basis:
    print(f"| {n} | {basis[n]:,.6g} | {neu[n]:,.6g} | {pct(basis[n], neu[n]):+.1f} | {neu_p[n]:,.6g} | {pct(basis[n], neu_p[n]):+.1f} |")

print("\n## C2 Einzelwirkung (gegen Version 0, nur betroffene Kennzahlen)\n| Korrektur | Kennzahl | Version 0 | nur diese Korrektur | Änderung % |\n|---|---|---|---|---|")
for name, kw in einzeln:
    w = kennzahlen(P, replace(V0, **kw))
    if name.startswith("9") or name.startswith("10") or name.startswith("11"):
        ref = kennzahlen(P, replace(V0, feste_werte=False)); refn = "V0 mit Formeln"
    else:
        ref = basis; refn = None
    for n in w:
        if abs(pct(ref[n], w[n])) > 1e-6 and not (isinstance(ref[n], float) and math.isnan(ref[n])):
            print(f"| {name} | {n} | {ref[n]:,.6g}{' ('+refn+')' if refn else ''} | {w[n]:,.6g} | {pct(ref[n], w[n]):+.2f} |")

print("\nRW4 verknüpft (Option 11) auf korrigiert:", {n: round(neu_11[n], 4) for n in ["GPU Mittel 2023 (mit Überkap.)", "Metall kum. 2023–2050, Ern20/Eff5 (t)"]})

# Fehler 4: Wirkung auf die Empfindlichkeit (V0 reagiert nicht)
for wh in (0.24, 6.8):
    pv = replace(P, wh_pro_anfrage=wh)
    a, b = rechne(pv, V0), rechne(pv, NEU)
    print(f"Wh={wh}: V0 GPU Start {a.gpu_start:,.0f} Metall kum {a.metall_server_kum:.2f} | korr GPU Start {b.gpu_start:,.0f} Metall kum {b.metall_server_kum:.2f}")
for anteil in (0.32, 0.67):
    pv = replace(P, nutzeranteil=anteil)
    a, b = rechne(pv, V0), rechne(pv, replace(NEU))
    print(f"Anteil={anteil}: V0 GPU Start {a.gpu_start:,.0f} KI-Nutzer 2050 {a.ki_nutzer[2050]:,.0f} (Smartphone {a.smartphone_nutzer[2050]:,.0f}) Metall {a.metall_server_kum:.2f} | korr GPU {b.gpu_start:,.0f} KI 2050 {b.ki_nutzer[2050]:,.0f} Metall {b.metall_server_kum:.2f}")

# Rechenwege korrigiert
ek = rechne(P, NEU)
print("\nRechenwege korrigiert (ohne/mit Überkap.):", {n: (round(ek.rw['ohne'][n], 1), round(ek.rw['mit'][n], 1)) for n in ek.rw['ohne']})
print("Energie korrigiert GWh/a:", {n: round(v, 3) for n, v in ek.energie_2023.items()})
print("RW1 Varianten: ganzzahlig 5 GPU/Instanz:", ek.rw["q"] * ek.t_rw1 * 5 if False else ek.rw["q"] * (P.tflop_inferenz / P.gpu_tflops / 4.375) * 5,
      " B13 multipliziert:", ek.rw["q"] * P.tflop_inferenz / P.gpu_tflops * 4.375)

# Fehler 1: #REF!-Spalte O_Metallbedarf_Server!L (Ern = MAIN 20 %, Eff 2,5 %)
print("Fehler 1: Ern20/Eff2,5 kum. =", round(rechne(P, V0, 0.2, 0.025).metall_server_kum, 3), "t; Jahreswert 2050 =", round(rechne(P, V0, 0.2, 0.025).metall_server_jahr[-1], 4))

# Kritikalität vollständig (V0 vs korrigiert)
e0v = rechne(P, V0, 0.2, 0.0); e0n = rechne(P, NEU, 0.2, 0.0)
kv, kn = kritikalitaet(e0v, V0), kritikalitaet(e0n, NEU)
kn_y28 = kritikalitaet(e0n, NEU, faktor_endgeraet_neu=2292.0)
print("\n## C3 Kritikalität (Ern20/Eff0 wie O_Kritikalitäten)\n| Metall | H V0 % | H korr % | M V0 % | M korr (Faktor X40) % | M korr (Faktor Y28) % |\n|---|---|---|---|---|---|")
for m in METALLE:
    print(f"| {m} | {kv[m]['H']*100:.3g} | {kn[m]['H']*100:.3g} | {kv[m]['M']*100:.3g} | {kn[m]['M']*100:.3g} | {kn_y28[m]['M']*100:.3g} |")


# --- D) Sensitivität -------------------------------------------------------
def ziel(p, k=NEU, peri=0.0):
    kk = replace(k, peripherie_aus=(peri == 0.0))
    pp = replace(p, peripherie=peri)
    e = rechne(pp, kk)
    return e.metall_server_kum, e.gpu_start

basis_m, basis_g = ziel(P)
print(f"\n## D Basis korrigiert: Metall kum {basis_m:.3f} t, GPUs 2023 {basis_g:,.1f}")

rw_opt = ["RW1", "RW2", "RW3", "RW4", "Durchschnitt", "Median"]
tornado = [
    # Name, Feld, Werte (niedrig, hoch), Beleg
    ("Energy per query 0.24–6.8 Wh", "wh_pro_anfrage", (0.24, 6.8)),
    ("Calculation path (4 paths, mean, median)", "rechenweg", None),
    ("Server renewal 0–30 %/a", "erneuerung_server", (0.0, 0.30)),
    ("Efficiency gain 0–30 %/a", "effizienz", (0.0, 0.30)),
    ("AI user share 20–67 %", "nutzeranteil", (0.20, 0.67)),
    ("Queries per day 7.5–22.5*", "anfragen_pro_tag", (7.5, 22.5)),
    ("Spare capacity 0–100 %*", "ueberkapazitaet", (0.0, 1.0)),
    ("GPU power 700–1000 W", "gpu_watt", (700.0, 1000.0)),
    ("Device load for federated 10–20 %", "auslastung_federated", (0.10, 0.20)),
    ("Server periphery 0–30 %", "peripherie", (0.0, 0.30)),
    ("Server PCB weight 265–4,000 g", "pcb2_g", (264.9728, 4000.0)),
]
res = []
for name, feld, wr in tornado:
    if feld == "rechenweg":
        vals = [ziel(replace(P, rechenweg=r)) for r in rw_opt]
        mm = [v[0] for v in vals]; gg = [v[1] for v in vals]
        res.append((name, min(mm), max(mm), min(gg), max(gg), dict(zip(rw_opt, vals))))
    elif feld == "peripherie":
        a, b = ziel(P, peri=0.0), ziel(P, peri=0.30)
        res.append((name, min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]), {0: a, 0.3: b}))
    else:
        a, b = ziel(replace(P, **{feld: wr[0]})), ziel(replace(P, **{feld: wr[1]}))
        res.append((name, min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]), {wr[0]: a, wr[1]: b}))
# Zwischenwert 32 % Nutzeranteil
m32 = ziel(replace(P, nutzeranteil=0.32))
res.sort(key=lambda r: -(math.log(r[2]) - math.log(r[1])))
print("| Eingabe | Metall kum. min (t) | max (t) | Spanne max/min | GPUs 2023 min | max |\n|---|---|---|---|---|---|")
for r in res:
    print(f"| {r[0]} | {r[1]:.2f} | {r[2]:.2f} | {r[2]/r[1]:.2f} | {r[3]:,.0f} | {r[4]:,.0f} |")
print("Nutzeranteil 32 %:", m32)
print("Rechenwege einzeln:", {k: (round(v[0], 2), round(v[1])) for k, v in res[[r[0] for r in res].index('Calculation path (4 paths, mean, median)')][5].items()})

# Monte Carlo
rng = random.Random(20261003)
N = 10000
mc_m, mc_g, X, neg4 = [], [], [], []
for _ in range(N):
    wh = math.exp(rng.uniform(math.log(0.24), math.log(6.8)))
    rwy = rng.choice(rw_opt)
    ern = rng.uniform(0, 0.30); eff = rng.uniform(0, 0.30)
    ant = rng.uniform(0.20, 0.67); anf = rng.uniform(7.5, 22.5)
    ovk = rng.uniform(0, 1.0); w = rng.uniform(700, 1000)
    fed = rng.uniform(0.10, 0.20); peri = rng.uniform(0, 0.30)
    pcb = rng.uniform(264.9728, 4000.0)
    pp = replace(P, pcb2_g=pcb, wh_pro_anfrage=wh, rechenweg=rwy, erneuerung_server=ern, effizienz=eff,
                 nutzeranteil=ant, anfragen_pro_tag=anf, ueberkapazitaet=ovk, gpu_watt=w,
                 auslastung_federated=fed)
    m, g = ziel(pp, peri=peri)
    neg4.append(rechne(pp, NEU).rw["rw4_roh"] < 0)
    mc_m.append(m); mc_g.append(g)
    X.append([wh, rw_opt.index(rwy), ern, eff, ant, anf, ovk, w, fed, peri, pcb])
mc_m, mc_g, X = np.array(mc_m), np.array(mc_g), np.array(X)
q = lambda a: np.percentile(a, [5, 50, 95])
print("\nMC Metall kum. t: P5/P50/P95", q(mc_m), "Mittel", mc_m.mean(), "Anteil > Basis", (mc_m > basis_m).mean())
print("MC Läufe mit RW4 < 0 (auf 0 gesetzt):", np.mean(neg4), "; Läufe mit Metall = 0:", (mc_m <= 0).mean())
print("MC GPUs 2023: P5/P50/P95", q(mc_g), "Mittel", mc_g.mean())
print("MC Metall in V0-Werten: Anteil unter 23.64 t", (mc_m < 23.642).mean())

def rang(a):
    return np.argsort(np.argsort(a)).astype(float)
namen = ["Wh/Anfrage", "Rechenweg (Index, nicht ordinal)", "Erneuerung", "Effizienz", "Nutzeranteil", "Anfragen/Tag", "Überkapazität", "GPU-Leistung", "Federated-Auslastung", "Peripherie", "PCB-Gewicht"]
print("| Eingabe | Spearman ρ Metall | Spearman ρ GPUs |\n|---|---|---|")
for i, n in enumerate(namen):
    if i == 1:
        continue
    rm = np.corrcoef(rang(X[:, i]), rang(mc_m))[0, 1]; rg = np.corrcoef(rang(X[:, i]), rang(mc_g))[0, 1]
    print(f"| {n} | {rm:+.2f} | {rg:+.2f} |")
# Rechenweg: Median der Zielgröße je Auswahl
for j, r in enumerate(rw_opt):
    sel = X[:, 1] == j
    print(f"MC Rechenweg {r}: Median Metall {np.median(mc_m[sel]):.2f} t, GPUs {np.median(mc_g[sel]):,.0f}")


# --- E) Funktionale Einheit ------------------------------------------------
def fe(name, p, k, quelle):
    e = rechne(p, k)
    anfr = e.anfragen_2023                    # Anfragen im Startjahr
    t_tsd = anfr / 1000
    stock = e.metall_server_2023 * 1e9        # mg (Startjahr = Bestand)
    lebens = 1 / p.erneuerung_server          # Jahre (Annahme: Nutzungsdauer = 1/Erneuerung)
    anfr_kum = sum(e.ki_nutzer[t] for t in e.jahre) * p.anfragen_pro_tag * 365
    kum = e.metall_server_kum * 1e9
    dev_stock = sum(e.ki_nutzer[p.startjahr] * g * e.federated for g in G_PRO_SMARTPHONE) * 1e3  # mg
    dev_leb = 1 / p.erneuerung_endgeraet
    flotte_wh = e.gpu_start * p.gpu_watt * 8760  # Wh/a bei Volllast
    print(f"| {name} | {quelle} | {anfr:,.4g} | {e.gpu_start:,.0f} | {e.server_start:,.0f} | {stock/t_tsd:.2f} | {stock/lebens/t_tsd:.2f} | {kum/(anfr_kum/1000):.2f} | {dev_stock/dev_leb/t_tsd:.1f} | {(p.wh_pro_anfrage+p.wh_zusatz)*1000:,.0f} | {flotte_wh/t_tsd:,.0f} |")

print("\n## E\n| Fall | Grundlage | Anfragen/a | GPUs | Server | Metall Server+GPU, Bestand (mg/1000) | dto. je Nutzungsjahr, 1/Ern. (mg/1000) | kum. 2023–2050 / kum. Anfragen (mg/1000) | Endgerät anteilig je Nutzungsjahr (mg/1000) | Energie RW3 (Wh/1000) | GPU-Flotte Volllast (Wh/1000) |\n|---|---|---|---|---|---|---|---|---|---|---|")
fe("2023 Tool (V0)", P, V0, "Tool")
fe("2023 korrigiert", P, NEU, "korr., Mittel 4 RW")
fe("2023 Tool, nur RW3", replace(P, rechenweg="RW3"), replace(V0, feste_werte=False), "V0-Formeln, RW3")
n26 = 34468311.0
for wh in (0.31, 3.91):
    # 2026: Nutzer 2026 aus Tool-Prognose (B_Endgeräte_Nutzung_Smartphone!P21), RW3,
    # 1 000 W, Überkapazität 50 % und Federated 11,24 % wie im Tool
    anfr = n26 * 15 * 365
    gpu = (n26 * 15 / 86400) * wh * 3600 / 1000 * 1.5 * (1 - 0.11236804853387261)
    srv = gpu / 8
    stock = (srv * sum(G_PRO_SERVER) + gpu * sum(G_PRO_GPU)) * 1e3  # mg
    t_tsd = anfr / 1000
    print(f"| 2026, {wh} Wh, 1 000 W | RW3, Federated 11,24 %, Überkap. 50 % | {anfr:,.4g} | {gpu:,.0f} | {srv:,.0f} | {stock/t_tsd:.2f} | {stock/5/t_tsd:.2f} | – | – | {wh*1000:,.0f} | {gpu*1000*8760/t_tsd:,.0f} |")


# --- Abbildungen -----------------------------------------------------------
GOLD, BLAU, GRAU, TINTE = "#b8862e", "#3f7fae", "#9a9a9a", "#222222"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Charter", "Georgia", "Times New Roman"],
    "font.size": 8, "axes.edgecolor": "#888", "axes.linewidth": .6, "axes.labelcolor": TINTE,
    "xtick.color": "#555", "ytick.color": "#555", "xtick.major.width": .5, "ytick.major.width": .5,
    "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none",
    "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": .5, "axes.axisbelow": True,
})
W = 3.3
from matplotlib.ticker import FuncFormatter
GANZ = FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}")

# Tornado: Metall kumuliert, Reihenfolge nach Spanne
fig, ax = plt.subplots(figsize=(W, 2.6))
for i, r in enumerate(res):
    lo, hi = r[1], r[2]
    ax.barh(i, basis_m - lo, left=lo, color=BLAU, height=.6)
    ax.barh(i, hi - basis_m, left=basis_m, color=GOLD, height=.6)
ax.axvline(basis_m, color=TINTE, lw=.8)
ax.set_xscale("log"); ax.xaxis.set_major_formatter(GANZ)
ax.set_yticks(range(len(res))); ax.set_yticklabels([r[0] for r in res], fontsize=7)
ax.invert_yaxis(); ax.grid(axis="y", visible=False)
ax.set_xlabel(f"Server metal bought 2023–2050 (t, log scale); base {basis_m:.1f} t")
ax.text(0, -.30, "* own assumption, no source", transform=ax.transAxes, ha="left", va="top", fontsize=6.5, color="#555")
fig.savefig("paper/fig/abb-tornado.svg", bbox_inches="tight", pad_inches=.02); plt.close(fig)

# Monte Carlo
fig, ax = plt.subplots(figsize=(W, 1.9))
bins = np.logspace(np.log10(mc_m[mc_m > 0].min()), np.log10(mc_m.max()), 50)
ax.hist(mc_m, bins=bins, color=BLAU, alpha=.85, label="calculation path drawn at random")
# zweiter Lauf: Rechenweg fest = Durchschnitt (wie MAIN!K39)
rng2 = random.Random(20261003); mc_mittel = []
for _ in range(N):
    wh = math.exp(rng2.uniform(math.log(0.24), math.log(6.8)))
    pp = replace(P, wh_pro_anfrage=wh, erneuerung_server=rng2.uniform(0, .3), effizienz=rng2.uniform(0, .3),
                 nutzeranteil=rng2.uniform(.2, .67), anfragen_pro_tag=rng2.uniform(7.5, 22.5),
                 ueberkapazitaet=rng2.uniform(0, 1), gpu_watt=rng2.uniform(700, 1000),
                 auslastung_federated=rng2.uniform(.1, .2), peripherie=rng2.uniform(0, .3),
                 pcb2_g=rng2.uniform(264.9728, 4000.0))
    mc_mittel.append(rechne(pp, replace(NEU, peripherie_aus=False)).metall_server_kum)
mc_mittel = np.array(mc_mittel)
print("MC Rechenweg fest Durchschnitt: P5/P50/P95", q(mc_mittel))
ax.hist(mc_mittel, bins=bins, histtype="step", color=GOLD, lw=1.1, label="path fixed to mean of four")
p5, p50, p95 = q(mc_m)
for v, ls in ((p5, ":"), (p50, "-"), (p95, ":")):
    ax.axvline(v, color=TINTE, lw=.8, ls=ls)
ymax = ax.get_ylim()[1]
ax.text(p50 * 0.85, ymax * .97, f"median {p50:.1f} t", color=TINTE, fontsize=6.5, ha="right", va="top")
ax.text(p5 * 0.92, ymax * .97, f"5 %: {p5:.1f}", color=TINTE, fontsize=6.5, ha="right", va="top")
ax.text(p95 * 1.08, ymax * .97, f"95 %: {p95:.0f}", color=TINTE, fontsize=6.5, va="top")
ax.axvline(basis_m, color=TINTE, lw=.8, ls="--")
ax.text(p95 * 1.08, ymax * .84, f"base {basis_m:.1f}", color=TINTE, fontsize=6.5, va="top")
ax.legend(frameon=False, fontsize=6.5, loc="upper left", bbox_to_anchor=(0, -.32), ncol=1)
ax.set_xscale("log"); ax.xaxis.set_major_formatter(GANZ)
ax.set_xlabel("Server metal bought 2023–2050 (t, log scale), 10,000 runs")
ax.set_ylabel("runs"); ax.grid(axis="x", visible=False)
fig.savefig("paper/fig/abb-montecarlo.svg", bbox_inches="tight", pad_inches=.02); plt.close(fig)
print("Abbildungen geschrieben")
