"""Tests for notes generation."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.financial.notes import generate_notes
from src.sie_parser.models import Account, Balance, ResultRow, SieFile
from src.sie_parser.parser import parse_sie_file

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def _make_sie(
    *,
    accounts: dict[str, str] | None = None,
    ib: dict[str, Decimal] | None = None,
    ub: dict[str, Decimal] | None = None,
    res: dict[str, Decimal] | None = None,
) -> SieFile:
    """Bygg ett minimalt SieFile för noter-tester."""
    sie = SieFile()
    accounts = accounts or {}
    for num, name in accounts.items():
        sie.accounts[num] = Account(number=num, name=name)
    for acct, amt in (ib or {}).items():
        sie.ib.append(Balance(year_offset=0, account=acct, amount=amt))
    for acct, amt in (ub or {}).items():
        sie.ub.append(Balance(year_offset=0, account=acct, amount=amt))
    for acct, amt in (res or {}).items():
        sie.res.append(ResultRow(year_offset=0, account=acct, amount=amt))
    return sie


# ── Bas-noter ──

def test_standard_notes_always_present():
    sie = parse_sie_file(SIE_FILE)
    notes = generate_notes(sie)
    titles = [n.title for n in notes.items]
    assert "Redovisnings- och värderingsprinciper" in titles
    assert "Medelantal anställda" in titles
    assert "Ställda säkerheter och ansvarsförbindelser" in titles


_ANLAGGNING_KATEGORIER = {
    "Balanserade utgifter för utvecklingsarbeten",
    "Koncessioner, patent, licenser, varumärken och liknande rättigheter",
    "Hyresrätter och liknande rättigheter",
    "Goodwill",
    "Förskott avseende immateriella anläggningstillgångar",
    "Byggnader och mark",
    "Förbättringsutgifter på annans fastighet",
    "Maskiner och andra tekniska anläggningar",
    "Inventarier, verktyg och installationer",
    "Övriga materiella anläggningstillgångar",
}


def test_no_anlaggning_notes_for_minimal_company():
    sie = parse_sie_file(SIE_FILE)
    notes = generate_notes(sie)
    titles = {n.title for n in notes.items}
    assert not (titles & _ANLAGGNING_KATEGORIER)


# ── Per-kategori avskrivningstabeller ──

def test_inventarier_kategori_genereras_med_avskrivningstabell():
    """Konton 1220/1229 + 7832 ska ge noten 'Inventarier, verktyg och installationer'."""
    sie = _make_sie(
        accounts={
            "1220": "Inventarier",
            "1229": "Ackumulerade avskrivningar inventarier",
            "7832": "Avskrivningar inventarier",
        },
        ib={"1220": Decimal("100000"), "1229": Decimal("-30000")},
        ub={"1220": Decimal("120000"), "1229": Decimal("-45000")},
        res={"7832": Decimal("15000")},
    )
    notes = generate_notes(sie)
    inventarier = [n for n in notes.items if n.title == "Inventarier, verktyg och installationer"]
    assert len(inventarier) == 1
    table = dict(inventarier[0].table)
    assert table["Ingående anskaffningsvärde"] == "100 000"
    assert table["Förändring under året"] == "20 000"
    assert table["Utgående anskaffningsvärde"] == "120 000"
    assert table["Ingående ackumulerade avskrivningar"] == "-30 000"
    assert table["Årets avskrivningar"] == "-15 000"
    assert table["Utgående ackumulerade avskrivningar"] == "-45 000"
    assert table["Bokfört värde vid årets slut"] == "75 000"


def test_goodwill_kategori_skils_fran_andra_immateriella():
    """Goodwill (1050/1059, 7817) ska få egen not separat från övriga immateriella."""
    sie = _make_sie(
        accounts={
            "1050": "Goodwill",
            "1059": "Ackumulerade avskrivningar goodwill",
            "1020": "Patent",
            "1029": "Ackumulerade avskrivningar patent",
            "7817": "Avskrivningar goodwill",
            "7813": "Avskrivningar patent",
        },
        ib={"1050": Decimal("200000"), "1059": Decimal("-40000"),
            "1020": Decimal("80000"), "1029": Decimal("-10000")},
        ub={"1050": Decimal("200000"), "1059": Decimal("-80000"),
            "1020": Decimal("80000"), "1029": Decimal("-20000")},
        res={"7817": Decimal("40000"), "7813": Decimal("10000")},
    )
    notes = generate_notes(sie)
    titles = [n.title for n in notes.items]
    assert "Goodwill" in titles
    assert "Koncessioner, patent, licenser, varumärken och liknande rättigheter" in titles
    goodwill = next(n for n in notes.items if n.title == "Goodwill")
    patent = next(
        n for n in notes.items
        if n.title == "Koncessioner, patent, licenser, varumärken och liknande rättigheter"
    )
    assert dict(goodwill.table)["Utgående anskaffningsvärde"] == "200 000"
    assert dict(goodwill.table)["Årets avskrivningar"] == "-40 000"
    assert dict(patent.table)["Utgående anskaffningsvärde"] == "80 000"
    assert dict(patent.table)["Årets avskrivningar"] == "-10 000"


def test_byggnader_och_forbattringsutgifter_separeras():
    """Byggnader (1110-1119) ska skiljas från Förbättringsutgifter (1120-1129)."""
    sie = _make_sie(
        accounts={
            "1110": "Byggnader",
            "1119": "Ackumulerade avskrivningar byggnader",
            "1120": "Förbättringsutgifter på annans fastighet",
            "1129": "Ack avskr förbättringsutgifter",
        },
        ub={
            "1110": Decimal("500000"), "1119": Decimal("-100000"),
            "1120": Decimal("60000"), "1129": Decimal("-20000"),
        },
    )
    notes = generate_notes(sie)
    titles = [n.title for n in notes.items]
    assert "Byggnader och mark" in titles
    assert "Förbättringsutgifter på annans fastighet" in titles
    byggnader = next(n for n in notes.items if n.title == "Byggnader och mark")
    forbattring = next(n for n in notes.items if n.title == "Förbättringsutgifter på annans fastighet")
    assert dict(byggnader.table)["Utgående anskaffningsvärde"] == "500 000"
    assert dict(forbattring.table)["Utgående anskaffningsvärde"] == "60 000"


def test_kategori_utan_saldon_genererar_ingen_not():
    """En kategori utan saldon (t.ex. bolag utan goodwill) ska inte ge en not."""
    sie = _make_sie(
        accounts={"1220": "Inventarier"},
        ub={"1220": Decimal("50000")},
    )
    notes = generate_notes(sie)
    titles = {n.title for n in notes.items}
    assert "Inventarier, verktyg och installationer" in titles
    assert "Goodwill" not in titles
    assert "Byggnader och mark" not in titles


# ── Checkräkningskredit ──

def test_checkrakningskredit_med_utnyttjat_belopp():
    sie = _make_sie(
        accounts={"2330": "Checkräkningskredit"},
        ub={"2330": Decimal("-25000")},  # kreditbalans = utnyttjat 25 000
    )
    notes = generate_notes(sie)
    check = [n for n in notes.items if n.title == "Checkräkningskredit"]
    assert len(check) == 1
    assert "25 000" in check[0].content
    assert "kompletteras manuellt" in check[0].content


def test_no_checkrakningskredit_when_account_missing():
    sie = parse_sie_file(SIE_FILE)
    notes = generate_notes(sie)
    titles = [n.title for n in notes.items]
    assert "Checkräkningskredit" not in titles


# ── Långfristiga skulder ──

def test_langfristiga_skulder_not_med_default_text():
    sie = _make_sie(
        accounts={"2350": "Andra långfristiga skulder"},
        ub={"2350": Decimal("-150000")},  # kreditbalans
    )
    notes = generate_notes(sie)
    lang = [n for n in notes.items if n.title == "Långfristiga skulder"]
    assert len(lang) == 1
    assert "fem år" in lang[0].content


def test_no_langfristiga_skulder_when_no_debt():
    sie = parse_sie_file(SIE_FILE)
    notes = generate_notes(sie)
    titles = [n.title for n in notes.items]
    assert "Långfristiga skulder" not in titles


# ── Numreringsordning ──

def test_notes_are_numbered_sequentially():
    sie = parse_sie_file(SIE_FILE)
    notes = generate_notes(sie)
    numbers = [n.number for n in notes.items]
    assert numbers == list(range(1, len(numbers) + 1))
