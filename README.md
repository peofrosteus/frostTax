# frostTax

SIE → Årsredovisning & Deklaration för svenska aktiebolag.

Webbapp som tar en SIE4-fil (exporterad från t.ex. Fortnox, Visma, Björn Lundén) och genererar:

- **Årsredovisning** (HTML + PDF) enligt K2 eller K3
- **Deklarationsunderlag** (INK2) med SRU-fältmappning
- **SRU-filer** (INFO.SRU + BLANKETTER.SRU) för digital inlämning till Skatteverket

## Kom igång

```bash
pip install -r requirements.txt
cd c:\repos\frostTax
python -m src.app
```

Öppna http://127.0.0.1:5000 i webbläsaren.

## Användning

1. Ladda upp en SIE4-fil (.se / .si / .sie) via webbformuläret, eller klicka på en lokal fil i `sieFiles/`
2. Granska årsredovisningen (förvaltningsberättelse, resultaträkning, balansräkning, noter)
3. Redigera förvaltningsberättelsen (verksamhetsbeskrivning, väsentliga händelser, resultatdisposition) via "Redigera"-knappen
4. Byt mellan K2/K3 med knappen i rapporthuvudet
5. Ladda ner PDF för inlämning till Bolagsverket
6. Gå till deklarationsunderlaget för att se INK2-fält och ladda ner SRU-filerna (zip)

## Årsredovisning

Genereras enligt ÅRL (1995:1554) och valbart regelverk:

### K2 (BFNAR 2016:10)

- Förvaltningsberättelse med bolagets säte, verksamhetsbeskrivning, flerårsöversikt och strukturerad resultatdisposition
- Resultaträkning (kostnadsslagsindelad)
- Balansräkning
- Noter (redovisningsprinciper, anställda, ställda säkerheter m.m.)

### K3 (BFNAR 2012:1)

Allt ovan plus:

- **Kassaflödesanalys** (indirekt metod)
- **Förändringar i eget kapital**
- Utökade redovisningsprinciper i noterna (intäktsredovisning, fordringar, anläggningstillgångar, kassaflödesmetod)

### Jämförelsetal

Om SIE-filen innehåller föregående räkenskapsår (`#RAR -1`) visas jämförelsekolumner automatiskt i alla rapporter samt flerårsöversikten.

## SRU-filer

SRU-filerna genereras i enlighet med Skatteverkets krav och har verifierats mot Skatteverkets officiella filöverföringstjänst:

- **INFO.SRU** – identitet, organisationsnummer, kontaktuppgifter
- **BLANKETTER.SRU** – INK2M (sida 1), INK2R (räkenskapsschema), INK2S (skattemässiga justeringar)

Alla SRU-koder verifierade mot SKV 294, srufiler.se och BAS 2026.

## Projektstruktur

```
frostTax/
├── sieFiles/                    # SIE-filer att bearbeta
├── src/
│   ├── app.py                   # Flask-webbapp
│   ├── sie_parser/
│   │   ├── parser.py            # SIE4-parser (hanterar PC8/CP437)
│   │   └── models.py            # Datamodeller
│   ├── financial/
│   │   ├── income_statement.py  # Resultaträkning
│   │   ├── balance_sheet.py     # Balansräkning
│   │   ├── management_report.py # Förvaltningsberättelse
│   │   ├── notes.py             # Noter
│   │   ├── cash_flow.py         # Kassaflödesanalys (K3)
│   │   └── equity_changes.py    # Förändringar i eget kapital (K3)
│   ├── tax/
│   │   ├── sru_mapping.py       # BAS-konto → SRU-kod → INK2R-fält
│   │   ├── sru_generator.py     # SRU-filgenerering (INFO + BLANKETTER)
│   │   ├── ink2_tax_calc.py     # INK2 sida 1 (fält 1.1–1.16)
│   │   └── ink2s_calc.py        # INK2S skattemässiga justeringar (4.1–4.22)
│   ├── templates/               # Jinja2 HTML-templates
│   └── static/                  # CSS
├── tests/                       # pytest-tester (40 st)
└── requirements.txt
```

## Tester

```bash
python -m pytest tests/ -v
```

## Beroenden

- Python 3.13+
- Flask ≥ 3.0
- xhtml2pdf ≥ 0.2.16 (PDF-generering)
- Jinja2 ≥ 3.1
- pytest ≥ 8.0

## Avgränsningar

- Stöder enbart **aktiebolag** (INK2). Enskild firma (NE) och handelsbolag (INK4) ingår inte.
- Digital signering och automatisk inlämning till Bolagsverket/Skatteverket ingår inte.
- Anställningsuppgifter i noterna kräver manuell komplettering vid fler än 0 anställda.
