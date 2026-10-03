# MetallKIDD tool, version 0: reimplementation and analysis

Code for the working paper *How much metal does AI inference bind? Verification,
uncertainty and a 2026 update of the MetallKIDD estimation tool* (Severin
Hackspiel, October 2026), [paper/metallkidd-working-paper.pdf](paper/metallkidd-working-paper.pdf).

The MetallKIDD tool (Austrup, Hackspiel, Bickel 2024) estimates how much metal
the inference hardware of an AI service binds. This repository rebuilds its
calculation in Python, checks it against the published workbook, corrects the
errors found and runs a sensitivity and Monte Carlo analysis.

## Results in brief

- The reimplementation reproduces the workbook's core values and all 49 cells of
  its renewal × efficiency matrix.
- Corrected, cumulative server and GPU metal 2023–2050 (default case) rises by
  15 %, from 23.6 to 27.2 t. An undocumented circuit-board mass (4,000 g vs. 265 g
  in the documentation) could halve it.
- The choice between the tool's four calculation methods spans a factor of 275.
  Over 10,000 runs, the median is 3.1 t (90 % interval 0.07–23.6 t).

## Running it

1. Download the tool from https://doi.org/10.5281/zenodo.11506192 and save it
   in this folder as `metallkidd.xlsx`.
2. `pip install openpyxl numpy matplotlib`
3. `python cache_erzeugen.py`  reads the workbook once (`wb.pkl`)
4. `python verifikation.py`    compares the reimplementation with the workbook
5. `python wirkung.py`         effect of each correction
6. `python analyse.py`         one-at-a-time sensitivity and Monte Carlo
                               (seed 20261003), figures in `paper/fig/`

`metallkidd_modell.py` contains the model. `rechne(p, k)` takes the inputs `p`
and correction switches `k`: `KORREKTUR_V0` is the tool as published,
`KORREKTUR_NEU` the corrected version. Comments in the code are in German and
give the cell of the workbook each value comes from.

## Sources

- Tool: Austrup, V. H., Hackspiel, S., Bickel, M. (2024): MetallKIDD-Tool,
  version 0. Zenodo. https://doi.org/10.5281/zenodo.11506192
- Project page: https://hackspiel.studio/arbeit/metallkidd/

This repository is not a publication of the Wuppertal Institute.

## License

CC BY 4.0, like the tool. See LICENSE.
