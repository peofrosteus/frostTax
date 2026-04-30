# frostTax

SIE → Årsredovisning & Deklaration för svenska aktiebolag enligt **K2 (BFNAR 2016:10)**.

Webbapp som tar en SIE4-fil (exporterad från t.ex. Fortnox, Visma, Björn Lundén) och genererar:

- **Årsredovisning** (HTML + PDF) enligt K2
- **Faststallelseintyg** för stämmans fastställelse av räkenskaperna
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
2. Arbeta i den uppdelade redigeringsvyn (editor till vänster, förhandsgranskning till höger)
3. Fyll i sektionerna i tur och ordning via flikarna:
   - **Grunduppgifter** – företagsnamn, org.nr, säte, räkenskapsår, redovisningsvaluta, vem som avger årsredovisningen
   - **Förvaltningsberättelse** – verksamhetsbeskrivning, väsentliga händelser, framtidsutsikter, fri text för resultatdisposition + strukturerade fält (utdelning, avsättning till reservfond, i ny räkning)
   - **Noter** – redigera/komplettera nottexter (innehållet rendereras direkt i förhandsgranskningen)
   - **Underskrifter** – ort, färdigställandedatum, dynamiskt antal underskrifter (minst 1; lägg till/ta bort vid behov)
   - **Faststallelseintyg** – datum för årsstämma, beslut om resultatdisposition, intygets undertecknare
4. Kontrollistan under editorn visar formkrav och varnar om något saknas (se *Formkrav* nedan)
5. Ladda ner PDF för inlämning till Bolagsverket
6. Gå till deklarationsunderlaget för att se hela INK2/INK2R/INK2S och ladda ner SRU-filerna (zip)

## Årsredovisning – K2 (BFNAR 2016:10)

Genereras enligt ÅRL (1995:1554) och BFNAR 2016:10 (K2) – "Årsredovisning i mindre företag":

- **Förvaltningsberättelse** med bolagets säte, verksamhetsbeskrivning, väsentliga händelser, framtidsutsikter, flerårsöversikt och strukturerad resultatdisposition
- **Resultaträkning** (kostnadsslagsindelad)
- **Balansräkning**
- **Förändringar i eget kapital** (K2 punkt 4.7) – aktiekapital, balanserat resultat, årets resultat med ingående/utgående saldon
- **Noter** (auto-genereras från SIE per K2-taxonomi):
  - Redovisnings- och värderingsprinciper
  - Medelantal anställda
  - Immateriella anläggningstillgångar – separat avskrivningstabell per kategori när saldon finns:
    - Balanserade utgifter för utvecklingsarbeten (1010–1019, 7811)
    - Koncessioner, patent, licenser, varumärken och liknande rättigheter (1020–1039, 7812–7815/7818–7819)
    - Hyresrätter och liknande rättigheter (1040–1049/1060–1069, 7816)
    - Goodwill (1050–1059, 7817)
    - Förskott avseende immateriella anläggningstillgångar (1080–1099)
  - Materiella anläggningstillgångar – separat avskrivningstabell per kategori när saldon finns:
    - Byggnader och mark (1110–1119/1130–1199, 7820–7821/7824–7829)
    - Förbättringsutgifter på annans fastighet (1120–1129, 7822–7823)
    - Maskiner och andra tekniska anläggningar (1210–1219, 7830–7831)
    - Inventarier, verktyg och installationer (1220–1269, 7832–7839)
    - Övriga materiella anläggningstillgångar (1290–1299)
  - Checkräkningskredit (om konto 2330 är använt)
  - Långfristiga skulder – förfaller senare än 5 år (om konton 2300–2399 har saldo)
  - Upplupna kostnader och förutbetalda intäkter (om konton 2900–2999 har saldo)
  - Ställda säkerheter och ansvarsförbindelser (alltid)

  Varje avskrivningstabell visar 7 rader: ingående/förändring/utgående anskaffningsvärde, ingående/årets/utgående ackumulerade avskrivningar och bokfört värde. Konton som slutar på 9 i anläggnings-intervallet identifieras som ackumulerade avskrivningar (BAS-konvention).
- **Underskrifter** med valfritt antal styrelsepersoner
- **Faststallelseintyg** på egen sida

Stöder bara K2 — K3 (BFNAR 2012:1) och kassaflödesanalys ingår inte. Alla tjänsteuppdrag förutsätts vara mindre företag som inte är skyldiga att tillämpa K3.

### Jämförelsetal

Om SIE-filen innehåller föregående räkenskapsår (`#RAR -1`) visas jämförelsekolumner automatiskt i alla rapporter samt flerårsöversikten.

### PDF-layout

PDF-export bryter sidor mellan varje huvudsektion: försättsblad → förvaltningsberättelse → resultaträkning → balansräkning → noter → underskrifter → faststallelseintyg. Underskriftslinje rendereras med ~56 px höjd för fysisk signatur ovanför namnförtydligandet.

## Formkrav (compliance)

Editorn visar en levande kontrollista som flaggar saknade formkrav. Kontrollerna baseras på K2-kraven samt Gredors checklista och täcker bl.a.:

- Grunduppgifter (företagsnamn, org.nr, räkenskapsår)
- Bolagets säte
- Verksamhetsbeskrivning
- Att noter har innehåll eller tabell
- **Balanskontroll** – tillgångar = eget kapital + skulder
- **Resultatdisposition balanserar** – utdelning + reservfond + ny räkning summerar till fritt eget kapital
- **Förändringar i eget kapital** – sektion finns
- Underskrifter (minst en med namn och datum)
- Datering ≤ tidigaste underskrift
- Faststallelseintyg (årsstämmodatum, intygare, datumordning AGM ≥ färdigställdes)

## SRU-filer & deklarationsunderlag

SRU-filerna genereras i enlighet med Skatteverkets krav och har verifierats mot Skatteverkets officiella filöverföringstjänst:

- **INFO.SRU** – identitet, organisationsnummer, kontaktuppgifter
- **BLANKETTER.SRU** – INK2M (sida 1), INK2R (räkenskapsschema), INK2S (skattemässiga justeringar)

Alla SRU-koder verifierade mot SKV 294, srufiler.se och BAS 2026.

I webbgränssnittet visas **alla** INK2R- (2.1–2.50, 3.1–3.27) och INK2S-fält (4.1–4.22) i deklarationsunderlaget — även rader med belopp 0 listas (dämpade) så strukturen speglar den officiella blanketten. SRU-filerna i sig innehåller endast nollskilda fält enligt Skatteverkets format.

## Projektstruktur

```
frostTax/
├── sieFiles/                       # SIE-filer att bearbeta
├── src/
│   ├── app.py                      # Flask-webbapp
│   ├── sie_parser/
│   │   ├── parser.py               # SIE4-parser (hanterar PC8/CP437)
│   │   └── models.py               # Datamodeller
│   ├── financial/
│   │   ├── income_statement.py     # Resultaträkning (K2 kostnadsslagsindelad)
│   │   ├── balance_sheet.py        # Balansräkning
│   │   ├── management_report.py    # Förvaltningsberättelse + strukturerad resultatdisposition
│   │   ├── notes.py                # Noter
│   │   ├── equity_changes.py       # Förändringar i eget kapital (K2 4.7)
│   │   └── reporting_workspace.py  # ReportState + compliance-checklista
│   ├── tax/
│   │   ├── sru_mapping.py          # BAS-konto → SRU-kod → INK2R-fält + komplett INK2R-tabell
│   │   ├── sru_generator.py        # SRU-filgenerering (INFO + BLANKETTER)
│   │   ├── ink2_tax_calc.py        # INK2 sida 1 (fält 1.1–1.16)
│   │   └── ink2s_calc.py           # INK2S skattemässiga justeringar (4.1–4.22)
│   ├── templates/                  # Jinja2 HTML-mallar (workspace + print)
│   └── static/                     # CSS (Gredor-inspirerad palett)
├── tests/                          # pytest-tester (60 st)
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

- Stöder enbart **aktiebolag enligt K2** (INK2). Enskild firma (NE), handelsbolag (INK4) och K3 (BFNAR 2012:1) ingår inte.
- Kassaflödesanalys ingår inte (krävs inte enligt K2).
- Digital signering och automatisk inlämning till Bolagsverket/Skatteverket ingår inte (signering sker manuellt på utskriven PDF).
- Anställningsuppgifter i noterna kräver manuell komplettering vid fler än 0 anställda.
- Förhandsgranskningen i webbgränssnittet uppdateras vid spara, inte live medan användaren skriver.
