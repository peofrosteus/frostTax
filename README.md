# frostTax

SIE → Årsredovisning & Deklaration för svenska aktiebolag.

Webbapp som tar en SIE4-fil (exporterad från t.ex. Fortnox, Visma, Björn Lundén) och genererar:

- **Årsredovisning** (HTML + PDF) enligt K2 eller K3
- **Deklarationsunderlag** (INK2) med SRU-fältmappning
- **SRU-fil** för digital inlämning till Skatteverket

## Kom igång

```bash
pip install flask weasyprint pytest
cd c:\repos\frostTax
python -m src.app
```

Öppna http://127.0.0.1:5000 i webbläsaren.

> WeasyPrint krävs bara för PDF-generering. Appen fungerar utan det (HTML-vy + SRU-filer).

## Användning

1. Ladda upp en SIE4-fil (.se / .si / .sie) via webbformuläret, eller klicka på en lokal fil i `sieFiles/`
2. Granska årsredovisningen (förvaltningsberättelse, resultaträkning, balansräkning, noter)
3. Byt mellan K2/K3 med knappen i övre högra hörnet
4. Ladda ner PDF för inlämning till Bolagsverket
5. Gå till deklarationsunderlaget för att se INK2-fält och ladda ner SRU-filen

## Projektstruktur

```
frostTax/
├── sieFiles/               # SIE-filer att bearbeta
├── src/
│   ├── app.py              # Flask-webbapp
│   ├── sie_parser/
│   │   ├── parser.py       # SIE4-parser (hanterar PC8/CP437)
│   │   └── models.py       # Datamodeller
│   ├── financial/
│   │   ├── income_statement.py  # Resultaträkning
│   │   ├── balance_sheet.py     # Balansräkning
│   │   ├── management_report.py # Förvaltningsberättelse
│   │   └── notes.py             # Noter
│   ├── tax/
│   │   ├── sru_mapping.py  # SRU-kod → INK2-fältmappning
│   │   └── sru_generator.py # SRU-filgenerering
│   ├── templates/           # Jinja2 HTML-templates
│   └── static/              # CSS
├── tests/                   # pytest-tester
└── requirements.txt
```

## Tester

```bash
python -m pytest tests/ -v
```

## Avgränsningar

- Stöder enbart **aktiebolag** (INK2). Enskild firma (NE) och handelsbolag (INK4) ingår inte.
- Kassaflödesanalys genereras inte (ej obligatorisk K2).
- Digital signering och automatisk inlämning till Bolagsverket/Skatteverket ingår inte.
- Förvaltningsberättelsens verksamhetsbeskrivning och resultatdisposition kräver manuell redigering.
