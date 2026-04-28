"""Workspace state and compliance checks for the annual report editor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from werkzeug.datastructures import ImmutableMultiDict

from src.financial.management_report import generate_management_report, ManagementReport
from src.financial.notes import Notes
from src.financial.balance_sheet import BalanceSheet
from src.financial.equity_changes import EquityChanges
from src.sie_parser.models import SieFile


@dataclass
class SignatureEntry:
    name: str = ""
    role: str = "Styrelseledamot"
    signed_date: str = ""


@dataclass
class ReportState:
    company_name: str = ""
    org_number: str = ""
    company_location: str = ""
    accounting_currency: str = "SEK"
    report_issuer: str = "Styrelsen"
    fiscal_year_start: str = ""
    fiscal_year_end: str = ""
    previous_year_start: str = ""
    previous_year_end: str = ""
    business_description: str = ""
    significant_events: str = ""
    expected_future_development: str = ""
    profit_disposition_text: str = ""
    # Strukturerad resultatdisposition (B). Tomma strängar = ej angivet (faller tillbaka till beräknat förslag).
    disposition_dividend: str = ""
    disposition_to_reserve_fund: str = ""
    disposition_to_new_account: str = ""
    signing_location: str = ""
    prepared_date: str = ""
    signatures: list[SignatureEntry] = field(default_factory=list)
    note_overrides: dict[int, str] = field(default_factory=dict)
    # Faststallelseintyg (A)
    agm_date: str = ""
    faststallelse_disposition_choice: str = "enligt_forslag"
    faststallelse_disposition_text: str = ""
    certifier_name: str = ""
    certifier_role: str = "Ordförande vid stämman"
    certifier_date: str = ""


@dataclass
class ComplianceItem:
    key: str
    title: str
    description: str
    status: str


def build_default_report_state(sie: SieFile) -> ReportState:
    """Build a default workspace state from parsed SIE data."""
    mgmt_report = generate_management_report(sie)
    contact_name = (sie.company.address_contact or "").strip()
    # Minst en underskrift krävs alltid; använd SIE-kontakt om tillgänglig.
    signatures = [SignatureEntry(name=contact_name)]

    return ReportState(
        company_name=sie.company.name,
        org_number=sie.company.org_number,
        company_location=mgmt_report.company_location,
        accounting_currency="SEK",
        report_issuer="Styrelsen",
        fiscal_year_start=_format_date(sie.company.fiscal_year_start),
        fiscal_year_end=_format_date(sie.company.fiscal_year_end),
        previous_year_start=_format_date(sie.company.prev_fiscal_year_start),
        previous_year_end=_format_date(sie.company.prev_fiscal_year_end),
        business_description=mgmt_report.business_description,
        significant_events=mgmt_report.significant_events,
        expected_future_development=mgmt_report.expected_future_development,
        profit_disposition_text=mgmt_report.profit_disposition_text,
        signing_location=mgmt_report.company_location,
        prepared_date="",
        signatures=signatures,
    )


def update_report_state(
    state: ReportState,
    section: str,
    form: ImmutableMultiDict[str, str],
    notes: Notes,
) -> None:
    """Mutate report state based on a submitted editor section."""
    if section == "grunduppgifter":
        state.company_name = form.get("company_name", "").strip()
        state.org_number = form.get("org_number", "").strip()
        state.company_location = form.get("company_location", "").strip()
        state.accounting_currency = form.get("accounting_currency", "SEK").strip() or "SEK"
        state.report_issuer = form.get("report_issuer", "Styrelsen").strip() or "Styrelsen"
        state.fiscal_year_start = form.get("fiscal_year_start", "").strip()
        state.fiscal_year_end = form.get("fiscal_year_end", "").strip()
        state.previous_year_start = form.get("previous_year_start", "").strip()
        state.previous_year_end = form.get("previous_year_end", "").strip()
        return

    if section == "forvaltningsberattelse":
        state.business_description = form.get("business_description", "").strip()
        state.significant_events = form.get("significant_events", "").strip()
        state.expected_future_development = form.get("expected_future_development", "").strip()
        state.profit_disposition_text = form.get("profit_disposition_text", "").strip()
        state.disposition_dividend = form.get("disposition_dividend", "").strip()
        state.disposition_to_reserve_fund = form.get("disposition_to_reserve_fund", "").strip()
        state.disposition_to_new_account = form.get("disposition_to_new_account", "").strip()
        return

    if section == "faststallelseintyg":
        state.agm_date = form.get("agm_date", "").strip()
        choice = form.get("faststallelse_disposition_choice", "enligt_forslag").strip()
        state.faststallelse_disposition_choice = choice or "enligt_forslag"
        state.faststallelse_disposition_text = form.get("faststallelse_disposition_text", "").strip()
        state.certifier_name = form.get("certifier_name", "").strip()
        state.certifier_role = form.get("certifier_role", "Ordförande vid stämman").strip() or "Ordförande vid stämman"
        state.certifier_date = form.get("certifier_date", "").strip()
        return

    if section == "noter":
        overrides: dict[int, str] = {}
        for note in notes.items:
            content = form.get(f"note_{note.number}", "").strip()
            if content:
                overrides[note.number] = content
        state.note_overrides = overrides
        return

    if section == "underskrifter":
        state.signing_location = form.get("signing_location", "").strip()
        state.prepared_date = form.get("prepared_date", "").strip()
        names = form.getlist("signature_name")
        roles = form.getlist("signature_role")
        signed_dates = form.getlist("signature_date")
        signatures: list[SignatureEntry] = []
        # Bevara alla insända rader (även tomma) så att add/remove-flödet behåller användarinmatning.
        for name, role, signed_date in zip(names, roles, signed_dates):
            signatures.append(
                SignatureEntry(
                    name=name.strip(),
                    role=role.strip() or "Styrelseledamot",
                    signed_date=signed_date.strip(),
                )
            )

        action = form.get("action", "").strip()
        if action == "add":
            signatures.append(SignatureEntry())
        elif action.startswith("remove_"):
            try:
                idx = int(action.split("_", 1)[1])
                if 0 <= idx < len(signatures):
                    signatures.pop(idx)
            except ValueError:
                pass

        # Minst en underskrift krävs alltid.
        if not signatures:
            signatures = [SignatureEntry()]
        state.signatures = signatures


def apply_report_state_to_notes(notes: Notes, state: ReportState) -> None:
    """Apply note overrides from the editor workspace to generated notes."""
    for note in notes.items:
        if note.number in state.note_overrides:
            note.content = state.note_overrides[note.number]


def build_compliance_items(
    state: ReportState,
    balance: BalanceSheet,
    notes: Notes,
    has_previous_year: bool,
    mgmt_report: ManagementReport | None = None,
    equity_changes: EquityChanges | None = None,
) -> list[ComplianceItem]:
    """Build a simple checklist aligned with the K2 editor scope."""
    items = [
        ComplianceItem(
            key="company",
            title="Grunduppgifter",
            description="Företagsnamn och organisationsnummer behöver vara ifyllda.",
            status="complete" if state.company_name and state.org_number else "error",
        ),
        ComplianceItem(
            key="current-year",
            title="Aktuellt räkenskapsår",
            description="Start- och slutdatum för aktuellt räkenskapsår måste finnas.",
            status="complete" if state.fiscal_year_start and state.fiscal_year_end else "error",
        ),
        ComplianceItem(
            key="previous-year",
            title="Jämförelseår",
            description="K2-årsredovisning bör ha jämförelseår för visning i tabeller och noter.",
            status=(
                "complete"
                if state.previous_year_start and state.previous_year_end
                else "warning" if has_previous_year else "warning"
            ),
        ),
        ComplianceItem(
            key="company-location",
            title="Bolagets säte",
            description="Säte bör anges i förvaltningsberättelsen.",
            status="complete" if state.company_location else "warning",
        ),
        ComplianceItem(
            key="management-report",
            title="Förvaltningsberättelse",
            description="Verksamhetsbeskrivning behöver vara ifylld och granskningsbar.",
            status="complete" if state.business_description else "error",
        ),
        ComplianceItem(
            key="notes",
            title="Noter",
            description="Samtliga genererade noter ska ha innehåll eller tabell.",
            status="complete" if all(_note_has_content(note) for note in notes.items) else "warning",
        ),
        ComplianceItem(
            key="balance",
            title="Balanskontroll",
            description="Tillgångar måste vara lika med eget kapital och skulder.",
            status="complete" if balance.is_balanced else "error",
        ),
        ComplianceItem(
            key="profit-disposition",
            title="Resultatdisposition balanserar",
            description="Utdelning + reservfond + ny räkning ska summera till fritt eget kapital.",
            status=(
                "complete"
                if mgmt_report is None or mgmt_report.profit_disposition.is_balanced
                else "error"
            ),
        ),
        ComplianceItem(
            key="equity-changes",
            title="Förändringar i eget kapital",
            description="Specifikation av förändringar i eget kapital krävs (K2 4.7 / K3 kap 6).",
            status=(
                "complete"
                if equity_changes is not None and equity_changes.columns
                else "warning"
            ),
        ),
        ComplianceItem(
            key="signing-metadata",
            title="Ort och datering",
            description="Ort och datum för färdigställd årsredovisning ska vara ifyllda.",
            status="complete" if state.signing_location and state.prepared_date else "error",
        ),
        ComplianceItem(
            key="signatures",
            title="Underskrifter",
            description="Minst en underskrift med namn och datum bör finnas innan export.",
            status="complete" if _signatures_complete(state.signatures) else "error",
        ),
        ComplianceItem(
            key="signing-order",
            title="Dateringslogik",
            description="Datum då årsredovisningen färdigställdes får inte ligga efter första underskrift.",
            status="complete" if _prepared_date_is_valid(state) else "warning",
        ),
        ComplianceItem(
            key="faststallelse-agm",
            title="Faststallelseintyg – årsstämma",
            description="Datum för årsstämma där resultat- och balansräkning fastställts behöver anges.",
            status="complete" if state.agm_date else "warning",
        ),
        ComplianceItem(
            key="faststallelse-certifier",
            title="Faststallelseintyg – intygare",
            description="Intygets undertecknare (oftast stämmoordförande) med namn och datum krävs.",
            status=(
                "complete"
                if state.certifier_name and state.certifier_date
                else "warning"
            ),
        ),
        ComplianceItem(
            key="faststallelse-order",
            title="Faststallelseintyg – datumordning",
            description="Årsstämman kan inte ha hållits före årsredovisningen färdigställdes.",
            status="complete" if _agm_date_is_after_prepared(state) else "warning",
        ),
    ]
    return items


def _agm_date_is_after_prepared(state: ReportState) -> bool:
    """AGM-datum måste ligga efter eller på samma dag som färdigställd årsredovisning."""
    if not state.agm_date:
        return True  # Ingen varning innan användaren fyllt i
    agm = _parse_iso_date(state.agm_date)
    prepared = _parse_iso_date(state.prepared_date) if state.prepared_date else None
    if agm is None:
        return False
    if prepared is None:
        return True
    return agm >= prepared


def _prepared_date_is_valid(state: ReportState) -> bool:
    if not state.prepared_date:
        return False
    signature_dates = [_parse_iso_date(item.signed_date) for item in state.signatures if item.signed_date]
    signature_dates = [item for item in signature_dates if item is not None]
    prepared_date = _parse_iso_date(state.prepared_date)
    if prepared_date is None:
        return False
    if not signature_dates:
        return True
    return prepared_date <= min(signature_dates)


def _signatures_complete(signatures: list[SignatureEntry]) -> bool:
    if not signatures:
        return False
    return all(item.name and item.signed_date for item in signatures)


def _note_has_content(note) -> bool:
    return bool(note.content.strip() if note.content else False) or bool(note.table)


def _format_date(value: date | None) -> str:
    return value.isoformat() if value else ""


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None