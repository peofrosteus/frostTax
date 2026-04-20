"""SRU code to INK2 field mapping.

Maps SRU codes (from Skatteverket) found in SIE files to the corresponding
field numbers in the INK2 declaration form (Inkomstdeklaration 2 for aktiebolag).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.sie_parser.models import SieFile


@dataclass
class SruField:
    """A field in the INK2 declaration form."""
    sru_code: str
    ink2_field: str
    label: str
    amount: Decimal = Decimal(0)
    section: str = ""


# Mapping from SRU code to INK2 field number and label
# Based on Skatteverkets specifikation for INK2 (blankett 2)
SRU_TO_INK2: dict[str, tuple[str, str, str]] = {
    # Balansräkning - Tillgångar
    "7201": ("2.1", "Immateriella anläggningstillgångar", "Tillgångar"),
    "7214": ("2.2", "Byggnader och mark", "Tillgångar"),
    "7215": ("2.3", "Maskiner och andra tekniska anläggningar, inventarier, verktyg", "Tillgångar"),
    "7233": ("2.4", "Andelar i intresseföretag och gemensamt styrda företag", "Tillgångar"),
    "7235": ("2.5", "Andra långfristiga fordringar", "Tillgångar"),
    "7241": ("2.6", "Råvaror och förnödenheter", "Tillgångar"),
    "7242": ("2.7", "Varor under tillverkning", "Tillgångar"),
    "7243": ("2.8", "Färdiga varor och handelsvaror", "Tillgångar"),
    "7244": ("2.9", "Övriga lagertillgångar", "Tillgångar"),
    "7245": ("2.10", "Pågående arbeten för annans räkning", "Tillgångar"),
    "7246": ("2.11", "Förskott till leverantörer", "Tillgångar"),
    "7251": ("2.12", "Kundfordringar", "Tillgångar"),
    "7261": ("2.13", "Övriga kortfristiga fordringar", "Tillgångar"),
    "7263": ("2.14", "Förutbetalda kostnader och upplupna intäkter", "Tillgångar"),
    "7271": ("2.15", "Kortfristiga placeringar", "Tillgångar"),
    "7281": ("2.16", "Kassa och bank", "Tillgångar"),

    # Balansräkning - Eget kapital och skulder
    "7301": ("2.17", "Bundet eget kapital", "Eget kapital"),
    "7302": ("2.18", "Fritt eget kapital", "Eget kapital"),
    "7310": ("2.17a", "Eget kapital delägare (EF/HB)", "Eget kapital"),
    "7311": ("2.17b", "Egna insättningar/uttag", "Eget kapital"),
    "7312": ("2.17c", "Årets resultat delägare", "Eget kapital"),
    "7321": ("2.19", "Periodiseringsfonder", "Obeskattade reserver"),
    "7322": ("2.20", "Ackumulerade överavskrivningar", "Obeskattade reserver"),
    "7331": ("2.21", "Avsättningar för pensioner", "Avsättningar"),
    "7333": ("2.22", "Övriga avsättningar", "Avsättningar"),
    "7351": ("2.23", "Checkräkningskredit", "Långfristiga skulder"),
    "7352": ("2.24", "Övriga skulder till kreditinstitut", "Långfristiga skulder"),
    "7354": ("2.25", "Övriga långfristiga skulder", "Långfristiga skulder"),
    "7360": ("2.26", "Checkräkningskredit kortfristig", "Kortfristiga skulder"),
    "7361": ("2.27", "Kortfristiga skulder till kreditinstitut", "Kortfristiga skulder"),
    "7362": ("2.28", "Förskott från kunder", "Kortfristiga skulder"),
    "7365": ("2.29", "Leverantörsskulder", "Kortfristiga skulder"),
    "7368": ("2.30", "Skatteskulder", "Kortfristiga skulder"),
    "7369": ("2.31", "Övriga kortfristiga skulder", "Kortfristiga skulder"),
    "7370": ("2.32", "Upplupna kostnader och förutbetalda intäkter", "Kortfristiga skulder"),

    # Resultaträkning
    "7410": ("2.33", "Nettoomsättning", "Resultaträkning"),
    "7411": ("2.34", "Förändring av lager", "Resultaträkning"),
    "7412": ("2.35", "Aktiverat arbete för egen räkning", "Resultaträkning"),
    "7413": ("2.36", "Övriga rörelseintäkter", "Resultaträkning"),
    "7511": ("2.37", "Förändring av varulager", "Resultaträkning"),
    "7512": ("2.38", "Råvaror och förnödenheter", "Resultaträkning"),
    "7513": ("2.39", "Övriga externa kostnader", "Resultaträkning"),
    "7514": ("2.40", "Personalkostnader", "Resultaträkning"),
    "7515": ("2.41", "Av- och nedskrivningar", "Resultaträkning"),
    "7517": ("2.42", "Övriga rörelsekostnader", "Resultaträkning"),
    "7416": ("2.43", "Resultat från andelar i koncern-/intresseföretag", "Resultaträkning"),
    "7417": ("2.44", "Övriga ränteintäkter och liknande", "Resultaträkning"),
    "7521": ("2.45", "Nedskrivningar finansiella anläggningstillgångar", "Resultaträkning"),
    "7522": ("2.46", "Räntekostnader och liknande", "Resultaträkning"),
    "7420": ("2.47", "Återföring periodiseringsfonder", "Bokslutsdispositioner"),
    "7525": ("2.48", "Avsättning periodiseringsfonder", "Bokslutsdispositioner"),
    "7526": ("2.49", "Förändring av överavskrivningar", "Bokslutsdispositioner"),
    "7528": ("2.50", "Skatt på årets resultat", "Skatt"),
    "7450": ("2.51", "Årets resultat", "Resultat"),

    # INK2S (skattemässiga justeringar)
    "8735": ("INK2S.1", "Eget kapital ideella föreningar", "Ideell"),
}


def aggregate_sru(sie: SieFile) -> list[SruField]:
    """Aggregate account balances by SRU code and map to INK2 fields."""
    sru_totals: dict[str, Decimal] = {}

    # For balance sheet accounts (1000-2999): use UB
    # For income statement accounts (3000-8999): use RES
    for account_num, account in sie.accounts.items():
        if not account.sru_code:
            continue

        try:
            num = int(account_num)
        except ValueError:
            continue

        if 1000 <= num <= 2999:
            amount = sie.get_ub(account_num, 0)
        else:
            amount = sie.get_result(account_num, 0)

        if amount == 0:
            continue

        sru_code = account.sru_code
        sru_totals[sru_code] = sru_totals.get(sru_code, Decimal(0)) + amount

    # Map to INK2 fields
    fields: list[SruField] = []
    for sru_code, amount in sorted(sru_totals.items()):
        if sru_code in SRU_TO_INK2:
            ink2_field, label, section = SRU_TO_INK2[sru_code]
            fields.append(SruField(
                sru_code=sru_code,
                ink2_field=ink2_field,
                label=label,
                amount=amount,
                section=section,
            ))
        else:
            fields.append(SruField(
                sru_code=sru_code,
                ink2_field=f"SRU_{sru_code}",
                label=f"Okänd SRU-kod {sru_code}",
                amount=amount,
                section="Övrigt",
            ))

    return fields
