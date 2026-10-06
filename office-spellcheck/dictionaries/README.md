# Dictionaries

`python fetch_dictionaries.py` puts these files here:

| File | Language | Source and licence |
|---|---|---|
| `mn_MN.aff`, `mn_MN.dic`, `README_mn_MN.txt` | Mongolian | Batmunkh Dorjgotov, <https://bataak.github.io/dict-mn/>, LaTeX Project Public License 1.3. Redistributed unmodified, with its README. |
| `en_US.aff`, `en_US.dic`, `README_en_US.txt` | English (US) | SCOWL, Kevin Atkinson and others, permissive licence (see the README). |

Any other Hunspell dictionary (`xx_YY.aff` + `xx_YY.dic`, as used by
LibreOffice) placed here is loaded too. Dictionaries for Cyrillic-script
languages (mn, ru, kk, …) check Cyrillic words, all others check Latin words.

Plain `.txt` files here are word lists: one accepted word per line (UTF-8,
or UTF-16 like Microsoft Office's `CUSTOM.DIC`). Use them for legal terms,
names of courts, company names and so on.
