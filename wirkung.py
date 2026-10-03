"""Tabelle: Korrektur | Wirkung auf Server-Metall kum. 2050 | Wirkung auf GPUs 2023,
einzeln (gegen Version 0) und kombiniert."""
from metallkidd_modell import *
P = Parameter(); V0 = KORREKTUR_V0; NEU = KORREKTUR_NEU
PCB_DOKU = 264.9728   # D_Übersicht!D8

def ziel(p, k):
    return (rechne(p, k).metall_server_kum, rechne(p, k, 0.2, 0.0).metall_server_kum, rechne(p, k).gpu_start)

b = ziel(P, V0)
VF = replace(V0, feste_werte=False)
faelle = [
    ("Fehler 4: feste Werte → Formeln", P, VF),
    ("Fehler 9: RW1 Instanz-GPUs mitzählen (mit 4)", P, replace(VF, rw1_teilt=False)),
    ("Fund 10: Federated-Vorlauf (mit 4)", P, replace(VF, federated_vorlauf=False)),
    ("Fund 11: RW4 mit I_KI verknüpft (Option, mit 4)", P, replace(VF, rw4_unverknuepft=False)),
    ("Fehler 5: Peripherie 30 % im Hauptpfad (Option)", P, replace(V0, peripherie_aus=False)),
    ("Variante PCB laut Dokumentation 264,97 g", replace(P, pcb2_g=PCB_DOKU), V0),
    ("Fehler 2: Effizienz-MATCH (wirkt nur bei 25/40 %)", P, replace(V0, eff_match=False)),
    ("Fehler 3, 6, 7, 8, Fund 12, 13, N25", P, replace(V0, endgeraet_versatz=0, pd_neodym=False, krit_faktor_gw=False, krit_mischgroesse=False, ohne_deckel=False, grau_fifo_v0=False, energie_rw4="wh_s")),
    ("**Kombiniert: Hauptkorrektur (2,3,4,6–10,12)**", P, NEU),
    ("Hauptkorrektur + Peripherie", P, replace(NEU, peripherie_aus=False)),
    ("Hauptkorrektur + PCB laut Doku", replace(P, pcb2_g=PCB_DOKU), NEU),
    ("Hauptkorrektur + Peripherie + PCB laut Doku", replace(P, pcb2_g=PCB_DOKU), replace(NEU, peripherie_aus=False)),
    ("Hauptkorrektur + alle Optionen (Periph., PCB, RW4)", replace(P, pcb2_g=PCB_DOKU), replace(NEU, peripherie_aus=False, rw4_unverknuepft=False)),
]
print(f"| Korrektur | Server-Metall kum. 2050, Ern20/Eff5 (V0 {b[0]:.2f} t) | Ern20/Eff0 (V0 {b[1]:.2f} t) | GPUs 2023 (V0 {b[2]:,.0f}) |")
print("|---|---|---|---|")
for n, p, k in faelle:
    z = ziel(p, k)
    f = lambda i, d: f"{z[i]:,.{d}f} ({(z[i]/b[i]-1)*100:+.1f} %)"
    print(f"| {n} | {f(0,2)} t | {f(1,2)} t | {f(2,0)} |")
