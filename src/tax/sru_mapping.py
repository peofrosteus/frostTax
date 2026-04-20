"""SRU code to INK2 field mapping.

Maps SRU codes (from Skatteverket) found in SIE files to the corresponding
field numbers in the INK2 declaration form (Inkomstdeklaration 2 for aktiebolag).

Field numbering follows the official INK2R blankett:
- 2.1–2.26: Tillgångar (balansräkning)
- 2.27–2.50: Eget kapital, reserver och skulder (balansräkning)
- 3.1–3.27: Resultaträkning
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


# Mapping from SRU code to (INK2R field, label, section)
# Based on srufiler.se and Skatteverkets blankett INK2R (SKV 2002)
SRU_TO_INK2: dict[str, tuple[str, str, str]] = {
    # ── Tillgångar / Anläggningstillgångar ──
    # Immateriella anläggningstillgångar
    "7201": ("2.1", "Koncessioner, patent, licenser, varumärken, hyresrätter, goodwill", "Tillgångar"),
    "7202": ("2.2", "Förskott avseende immateriella anläggningstillgångar", "Tillgångar"),
    # Materiella anläggningstillgångar
    "7214": ("2.3", "Byggnader och mark", "Tillgångar"),
    "7215": ("2.4", "Maskiner, inventarier och övriga materiella anläggningstillgångar", "Tillgångar"),
    "7216": ("2.5", "Förbättringsutgifter på annans fastighet", "Tillgångar"),
    "7217": ("2.6", "Pågående nyanläggningar och förskott avseende materiella anläggningstillgångar", "Tillgångar"),
    # Finansiella anläggningstillgångar
    "7230": ("2.7", "Andelar i koncernföretag", "Tillgångar"),
    "7231": ("2.8", "Andelar i intresseföretag och gemensamt styrda företag", "Tillgångar"),
    "7233": ("2.9", "Ägarintressen i övriga företag och andra långfristiga värdepappersinnehav", "Tillgångar"),
    "7232": ("2.10", "Fordringar hos koncern-, intresse- och gemensamt styrda företag", "Tillgångar"),
    "7234": ("2.11", "Lån till delägare eller närstående", "Tillgångar"),
    "7235": ("2.12", "Fordringar hos övriga företag och andra långfristiga fordringar", "Tillgångar"),

    # ── Omsättningstillgångar ──
    # Varulager m.m.
    "7241": ("2.13", "Råvaror och förnödenheter", "Omsättningstillgångar"),
    "7242": ("2.14", "Varor under tillverkning", "Omsättningstillgångar"),
    "7243": ("2.15", "Färdiga varor och handelsvaror", "Omsättningstillgångar"),
    "7244": ("2.16", "Övriga lagertillgångar", "Omsättningstillgångar"),
    "7245": ("2.17", "Pågående arbeten för annans räkning", "Omsättningstillgångar"),
    "7246": ("2.18", "Förskott till leverantörer", "Omsättningstillgångar"),
    # Kortfristiga fordringar
    "7251": ("2.19", "Kundfordringar", "Omsättningstillgångar"),
    "7252": ("2.20", "Fordringar hos koncern-, intresse- och gemensamt styrda företag", "Omsättningstillgångar"),
    "7261": ("2.21", "Övriga fordringar", "Omsättningstillgångar"),
    "7262": ("2.22", "Upparbetad men ej fakturerad intäkt", "Omsättningstillgångar"),
    "7263": ("2.23", "Förutbetalda kostnader och upplupna intäkter", "Omsättningstillgångar"),
    # Kortfristiga placeringar
    "7270": ("2.24", "Andelar i koncernföretag", "Omsättningstillgångar"),
    "7271": ("2.25", "Övriga kortfristiga placeringar", "Omsättningstillgångar"),
    # Kassa och bank
    "7281": ("2.26", "Kassa, bank och redovisningsmedel", "Omsättningstillgångar"),

    # ── Eget kapital ──
    "7301": ("2.27", "Bundet eget kapital", "Eget kapital"),
    "7302": ("2.28", "Fritt eget kapital", "Eget kapital"),
    # EF/HB-specifika (ej AB, men kan finnas i SIE)
    "7310": ("2.27", "Eget kapital vid räkenskapsårets början", "Eget kapital"),
    "7311": ("2.27", "Insättningar/uttag under året", "Eget kapital"),
    "7312": ("2.28", "Årets resultat (EF/HB)", "Eget kapital"),

    # ── Obeskattade reserver ──
    "7321": ("2.29", "Periodiseringsfonder", "Obeskattade reserver"),
    "7322": ("2.30", "Ackumulerade överavskrivningar", "Obeskattade reserver"),
    "7323": ("2.31", "Övriga obeskattade reserver", "Obeskattade reserver"),

    # ── Avsättningar ──
    "7331": ("2.32", "Avsättningar för pensioner enl. tryggandelagen", "Avsättningar"),
    "7332": ("2.33", "Övriga avsättningar för pensioner", "Avsättningar"),
    "7333": ("2.34", "Övriga avsättningar", "Avsättningar"),

    # ── Långfristiga skulder ──
    "7350": ("2.35", "Obligationslån", "Långfristiga skulder"),
    "7351": ("2.36", "Checkräkningskredit", "Långfristiga skulder"),
    "7352": ("2.37", "Övriga skulder till kreditinstitut", "Långfristiga skulder"),
    "7353": ("2.38", "Skulder till koncern-, intresse- och gemensamt styrda företag", "Långfristiga skulder"),
    "7354": ("2.39", "Övriga skulder", "Långfristiga skulder"),

    # ── Kortfristiga skulder ──
    "7360": ("2.40", "Checkräkningskredit", "Kortfristiga skulder"),
    "7361": ("2.41", "Övriga skulder till kreditinstitut", "Kortfristiga skulder"),
    "7362": ("2.42", "Förskott från kunder", "Kortfristiga skulder"),
    "7363": ("2.43", "Pågående arbeten för annans räkning", "Kortfristiga skulder"),
    "7364": ("2.44", "Fakturerad men ej upparbetad intäkt", "Kortfristiga skulder"),
    "7365": ("2.45", "Leverantörsskulder", "Kortfristiga skulder"),
    "7366": ("2.46", "Växelskulder", "Kortfristiga skulder"),
    "7367": ("2.47", "Skulder till koncern-, intresse- och gemensamt styrda företag", "Kortfristiga skulder"),
    "7369": ("2.48", "Övriga skulder", "Kortfristiga skulder"),
    "7368": ("2.49", "Skatteskulder", "Kortfristiga skulder"),
    "7370": ("2.50", "Upplupna kostnader och förutbetalda intäkter", "Kortfristiga skulder"),

    # ── Resultaträkning (INK2R sid 2, fält 3.1–3.27) ──
    # Rörelseintäkter
    "7410": ("3.1", "Nettoomsättning", "Resultaträkning – Rörelseintäkter"),
    "7411": ("3.2", "Förändring av lager av produkter i arbete, färdiga varor och pågående arbete", "Resultaträkning – Rörelseintäkter"),
    "7412": ("3.3", "Aktiverat arbete för egen räkning", "Resultaträkning – Rörelseintäkter"),
    "7413": ("3.4", "Övriga rörelseintäkter", "Resultaträkning – Rörelseintäkter"),
    # Rörelsekostnader
    "7511": ("3.5", "Råvaror och förnödenheter", "Resultaträkning – Rörelsekostnader"),
    "7512": ("3.6", "Handelsvaror", "Resultaträkning – Rörelsekostnader"),
    "7513": ("3.7", "Övriga externa kostnader", "Resultaträkning – Rörelsekostnader"),
    "7514": ("3.8", "Personalkostnader", "Resultaträkning – Rörelsekostnader"),
    "7515": ("3.9", "Av- och nedskrivningar av materiella och immateriella anläggningstillgångar", "Resultaträkning – Rörelsekostnader"),
    "7516": ("3.10", "Nedskrivningar av omsättningstillgångar utöver normala nedskrivningar", "Resultaträkning – Rörelsekostnader"),
    "7517": ("3.11", "Övriga rörelsekostnader", "Resultaträkning – Rörelsekostnader"),
    # Finansiella poster
    "7414": ("3.12", "Resultat från andelar i koncernföretag", "Resultaträkning – Finansiella poster"),
    "7415": ("3.13", "Resultat från andelar i intresseföretag och gemensamt styrda företag", "Resultaträkning – Finansiella poster"),
    "7423": ("3.14", "Resultat från övriga företag som det finns ett ägarintresse i", "Resultaträkning – Finansiella poster"),
    "7416": ("3.15", "Resultat från övriga finansiella anläggningstillgångar", "Resultaträkning – Finansiella poster"),
    "7417": ("3.16", "Övriga ränteintäkter och liknande resultatposter", "Resultaträkning – Finansiella poster"),
    "7521": ("3.17", "Nedskrivningar av finansiella anläggningstillgångar och kortfristiga placeringar", "Resultaträkning – Finansiella poster"),
    "7522": ("3.18", "Räntekostnader och liknande resultatposter", "Resultaträkning – Finansiella poster"),
    # Bokslutsdispositioner
    "7524": ("3.19", "Lämnade koncernbidrag", "Resultaträkning – Bokslutsdispositioner"),
    "7419": ("3.20", "Mottagna koncernbidrag", "Resultaträkning – Bokslutsdispositioner"),
    "7420": ("3.21", "Återföring av periodiseringsfond", "Resultaträkning – Bokslutsdispositioner"),
    "7525": ("3.22", "Avsättning till periodiseringsfond", "Resultaträkning – Bokslutsdispositioner"),
    "7421": ("3.23", "Förändring av överavskrivningar", "Resultaträkning – Bokslutsdispositioner"),
    "7526": ("3.23", "Förändring av överavskrivningar", "Resultaträkning – Bokslutsdispositioner"),  # Fortnox alt. code
    "7422": ("3.24", "Övriga bokslutsdispositioner", "Resultaträkning – Bokslutsdispositioner"),
    # Skatt och resultat
    "7528": ("3.25", "Skatt på årets resultat", "Resultaträkning – Skatt och resultat"),
    "7450": ("3.26", "Årets resultat, vinst", "Resultaträkning – Skatt och resultat"),
    "7550": ("3.27", "Årets resultat, förlust", "Resultaträkning – Skatt och resultat"),

    # Ideella föreningar (ej AB)
    "8735": ("EK", "Eget kapital ideella föreningar", "Övrigt"),
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
            # Income statement fields (3.x): use absolute values
            # Balance sheet fields (2.x): keep raw SIE sign
            if ink2_field.startswith("3."):
                amount = abs(amount)
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
