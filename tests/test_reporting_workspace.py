"""Tests for annual report workspace state and compliance checks."""

import sys
from pathlib import Path

from werkzeug.datastructures import ImmutableMultiDict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.financial.balance_sheet import generate_balance_sheet
from src.financial.notes import generate_notes
from src.financial.reporting_workspace import (
    build_compliance_items,
    build_default_report_state,
    update_report_state,
)
from src.app import app, _file_names, _parsed_files
from src.sie_parser.parser import parse_sie_file

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_default_report_state_uses_sie_values():
    sie = parse_sie_file(SIE_FILE)

    state = build_default_report_state(sie)

    assert state.company_name == sie.company.name
    assert state.org_number == sie.company.org_number
    assert state.fiscal_year_start == "2025-01-01"
    assert state.fiscal_year_end == "2025-12-31"


def test_update_report_state_collects_signature_rows():
    sie = parse_sie_file(SIE_FILE)
    state = build_default_report_state(sie)
    notes = generate_notes(sie)

    update_report_state(
        state,
        "underskrifter",
        ImmutableMultiDict(
            [
                ("signing_location", "Stockholm"),
                ("prepared_date", "2026-03-10"),
                ("signature_name", "Ada Lovelace"),
                ("signature_role", "Styrelseledamot"),
                ("signature_date", "2026-03-12"),
                ("signature_name", ""),
                ("signature_role", "Styrelsesuppleant"),
                ("signature_date", ""),
            ]
        ),
        notes,
    )

    assert state.signing_location == "Stockholm"
    assert state.prepared_date == "2026-03-10"
    assert len(state.signatures) == 2
    assert state.signatures[0].name == "Ada Lovelace"
    assert state.signatures[1].role == "Styrelsesuppleant"


def test_compliance_marks_missing_signature_data_as_error():
    sie = parse_sie_file(SIE_FILE)
    state = build_default_report_state(sie)
    notes = generate_notes(sie)
    balance = generate_balance_sheet(sie)

    items = build_compliance_items(state, balance, notes, sie.has_previous_year)
    by_key = {item.key: item for item in items}

    assert by_key["balance"].status == "complete"
    assert by_key["signatures"].status == "error"
    assert by_key["signing-metadata"].status == "error"


def test_compliance_accepts_valid_prepared_date_order():
    sie = parse_sie_file(SIE_FILE)
    state = build_default_report_state(sie)
    notes = generate_notes(sie)
    balance = generate_balance_sheet(sie)

    update_report_state(
        state,
        "underskrifter",
        ImmutableMultiDict(
            [
                ("signing_location", "Sundbyberg"),
                ("prepared_date", "2026-03-10"),
                ("signature_name", "Ada Lovelace"),
                ("signature_role", "Styrelseledamot"),
                ("signature_date", "2026-03-12"),
            ]
        ),
        notes,
    )

    items = build_compliance_items(state, balance, notes, sie.has_previous_year)
    by_key = {item.key: item for item in items}

    assert by_key["signatures"].status == "complete"
    assert by_key["signing-order"].status == "complete"


def test_signature_action_add_appends_empty_row():
    sie = parse_sie_file(SIE_FILE)
    state = build_default_report_state(sie)
    notes = generate_notes(sie)

    initial_count = len(state.signatures)
    update_report_state(
        state,
        "underskrifter",
        ImmutableMultiDict(
            [("signing_location", ""), ("prepared_date", ""), ("action", "add")]
            + [("signature_name", s.name) for s in state.signatures]
            + [("signature_role", s.role) for s in state.signatures]
            + [("signature_date", s.signed_date) for s in state.signatures]
        ),
        notes,
    )

    assert len(state.signatures) == initial_count + 1
    assert state.signatures[-1].name == ""


def test_signature_action_remove_drops_indexed_row():
    sie = parse_sie_file(SIE_FILE)
    state = build_default_report_state(sie)
    notes = generate_notes(sie)

    update_report_state(
        state,
        "underskrifter",
        ImmutableMultiDict(
            [
                ("signing_location", "Sthlm"),
                ("prepared_date", "2026-03-10"),
                ("signature_name", "A"),
                ("signature_role", "Styrelseledamot"),
                ("signature_date", "2026-03-11"),
                ("signature_name", "B"),
                ("signature_role", "Styrelseordförande"),
                ("signature_date", "2026-03-12"),
                ("action", "remove_0"),
            ]
        ),
        notes,
    )

    assert len(state.signatures) == 1
    assert state.signatures[0].name == "B"
    assert state.signatures[0].role == "Styrelseordförande"


def test_signature_remove_enforces_minimum_one():
    sie = parse_sie_file(SIE_FILE)
    state = build_default_report_state(sie)
    notes = generate_notes(sie)

    update_report_state(
        state,
        "underskrifter",
        ImmutableMultiDict(
            [
                ("signing_location", ""),
                ("prepared_date", ""),
                ("signature_name", "Sole"),
                ("signature_role", "Styrelseledamot"),
                ("signature_date", "2026-03-11"),
                ("action", "remove_0"),
            ]
        ),
        notes,
    )

    # Min 1 ska gälla, även när användaren försöker ta bort sista raden.
    assert len(state.signatures) == 1


def test_default_report_state_always_has_one_signature():
    sie = parse_sie_file(SIE_FILE)
    state = build_default_report_state(sie)
    assert len(state.signatures) >= 1


def test_report_route_renders_workspace_template():
    sie = parse_sie_file(SIE_FILE)
    file_id = "render-test-file"
    _parsed_files[file_id] = sie
    _file_names[file_id] = SIE_FILE.name

    try:
        with app.test_client() as client:
            response = client.get(f"/report/{file_id}")
            body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Årsredovisningsverktyg" in body
        assert "Redovisningsvaluta" in body
    finally:
        _parsed_files.pop(file_id, None)
        _file_names.pop(file_id, None)