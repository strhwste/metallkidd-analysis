"""Abgleich Skript gegen die im Excel gespeicherten Werte (wb.pkl = Formeln und
Cache-Werte aus metallkidd.xlsx, erzeugt mit fd.py)."""
import pickle
from metallkidd_modell import *

wf, wv = pickle.load(open("wb.pkl", "rb"))
V = lambda s, c: wv[s][c]
P = Parameter()
e = rechne(P, KORREKTUR_V0)
e0 = rechne(P, KORREKTUR_V0, erneuerung=0.2, effizienz=0.0)

zeilen = []
def z(name, zelle, tool, skript):
    abw = (skript / tool - 1) * 100 if tool else float("nan")
    zeilen.append((name, zelle, tool, skript, abw))

# GPUs 2023 je Rechenweg (ohne / mit Überkapazität) – Skript mit Formeln gerechnet
kf = replace(KORREKTUR_V0, feste_werte=False)     # Formeln statt fester Zahlen, sonst V0
rwf = gpu_rechenwege(P, kf, e.ki_nutzer[2023])
for n, c1, c2 in [("RW1", "B16", "B17"), ("RW2", "F16", "F17"), ("RW3", "J19", "J20"), ("RW4", "N13", "N15")]:
    z(f"GPU {n} ohne Überkapazität", f"B_KI!{c1}", V("B_KI", c1), rwf["ohne"][n])
    z(f"GPU {n} mit 50 % Überkapazität", f"B_KI!{c2}", V("B_KI", c2), rwf["mit"][n])
z("GPU Durchschnitt ohne", "MAIN!K35", V("MAIN", "K35"), e.rw["ohne"]["Durchschnitt"])
z("GPU Durchschnitt mit Überkap.", "B_KI!B45", V("B_KI", "B45"), e.rw["mit"]["Durchschnitt"])
z("GPU Median mit Überkap.", "B_KI!B46", V("B_KI", "B46"), e.rw["mit"]["Median"])
z("Anfragen pro Sekunde", "B_KI!B15", V("B_KI", "B15"), e.rw["q"])
z("Federated-Anteil 2023", "MAIN!S22", V("MAIN", "S22"), e.federated)
z("GPUs Startjahr", "MAIN!S21", V("MAIN", "S21"), e.gpu_start)
z("Server Startjahr", "Background_Parameter!B6", V("Background_Parameter", "B6"), e.server_start)
z("Smartphone-Nutzer 2050", "B_Endgeräte_Nutzung_Smartphone!B45", V("B_Endgeräte_Nutzung_Smartphone", "B45"), e.smartphone_nutzer[2050])
z("KI-Nutzer 2050", "B_Endgeräte_Nutzung_Smartphone!P45", V("B_Endgeräte_Nutzung_Smartphone", "P45"), e.ki_nutzer[2050])
z("Metall Server+GPU 2023 (t)", "O_KI!AH113", V("O_KI", "AH113"), e.metall_server_2023)
z("Metall kum. 2050 Ern20/Eff0 (t)", "O_KI!AH140", V("O_KI", "AH140"), e0.metall_server_kum)
z("Metall kum. 2050 Ern20/Eff5 (t)", "O_KI_plus_ES!AH85", V("O_KI_plus_ES", "AH85"), e.metall_server_kum)
z("GPU kum. 2050 Ern20/Eff5", "B_Hyperscale_Anzahl!AD30", V("B_Hyperscale_Anzahl", "AD30"), sum(e.gpu_neu))
z("Server kum. 2050 Ern20/Eff5", "B_Hyperscale_Anzahl!AC30", V("B_Hyperscale_Anzahl", "AC30"), sum(e.server_neu))
z("GPU kum. 2050 Ern20/Eff0", "B_Hyperscale_Anzahl!H30", V("B_Hyperscale_Anzahl", "H30"), sum(e0.gpu_neu))
z("Metallbedarf 2050 Ern20/Eff5 (t/a)", "O_Metallbedarf_Server!F32", V("O_Metallbedarf_Server", "F32"), e.metall_server_jahr[-1])
z("Metallbestand 2050 Ern20/Eff5 (t)", "O_Metallbestand_Server!F32", V("O_Metallbestand_Server", "F32"),
  (e.server_bestand[-1] * sum(G_PRO_SERVER) + e.gpu_bestand[-1] * sum(G_PRO_GPU)) / 1e6)
z("Kobalt Endgeräte 2023 (t)", "O_KI!W4", V("O_KI", "W4"), e.endgeraet_2023["Kobalt"])
z("Silizium Server kum. Ern20/Eff0 (t)", "O_KI!AP31", V("O_KI", "AP31"), e0.metall_server_je_metall["Silizium"])
for n, c in [("RW1", "B25"), ("RW2", "F25"), ("RW3", "J25"), ("RW4", "N25")]:
    z(f"Energie {n} 2023 (GWh/a)", f"B_KI!{c}", V("B_KI", c), e.energie_2023[n])
z("Palladium sekundär kum. (t)", "Σ B_Recycling!AJ4:AJ31", sum(V("B_Recycling", f"AJ{r}") for r in range(4, 32)),
  recycling_palladium(e0, KORREKTUR_V0))
kr = kritikalitaet(e0, KORREKTUR_V0)
z("Krit. H Kobalt", "O_Kritikalitäten!H10", V("O_Kritikalitäten", "H10"), kr["Kobalt"]["H"])
z("Krit. M Tantal", "O_Kritikalitäten!M19", V("O_Kritikalitäten", "M19"), kr["Tantal"]["M"])

# Szenario-Matrix: alle Generationenblätter (Parameter aus den Kopfzellen)
gpu_s, srv_s = {}, {}
for s in wv:
    if s.startswith("GPU_Generationen_Ern"):
        gpu_s[(V(s, "D1"), V(s, "H1"))] = sum(V(s, f"AO{r}") for r in range(6, 34))
    if s.startswith("Server_Generationen_Ern") or s.startswith("Tabellenblatt"):
        srv_s[(V(s, "E1"), V(s, "I1"))] = sum(V(s, f"AO{r}") for r in range(6, 34))
matrix = []
for key in sorted(gpu_s):
    if key not in srv_s:
        continue
    ern, eff = key
    tool = (gpu_s[key] * sum(G_PRO_GPU) + srv_s[key] * sum(G_PRO_SERVER)) / 1e6
    s = rechne(P, KORREKTUR_V0, erneuerung=ern, effizienz=eff)
    s_fifo = rechne(P, replace(KORREKTUR_V0, grau_fifo_v0=False), erneuerung=ern, effizienz=eff)
    matrix.append((ern, eff, tool, s.metall_server_kum, s_fifo.metall_server_kum))

if __name__ == "__main__":
    print("| Kennzahl | Zelle | Tool | Skript | Abw. % |\n|---|---|---|---|---|")
    for n, c, t, s, a in zeilen:
        print(f"| {n} | {c} | {t:,.6g} | {s:,.6g} | {a:+.4f} |")
    mx = max(abs(r[3] / r[2] - 1) for r in matrix)
    print(f"\nMatrix: {len(matrix)} Zellen, max. Abweichung {mx*100:.2e} %")
    for r in matrix:
        print(f"Ern {r[0]:.3f} Eff {r[1]:.3f}: Tool {r[2]:.4f} Skript {r[3]:.4f} FIFO-exakt {r[4]:.4f}")
