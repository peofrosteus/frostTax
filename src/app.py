"""Flask web application for frostTax."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from src.sie_parser.parser import parse_sie_bytes, parse_sie_file
from src.sie_parser.models import SieFile
from src.financial.income_statement import generate_income_statement
from src.financial.balance_sheet import generate_balance_sheet
from src.financial.management_report import generate_management_report, ManagementReport
from src.financial.notes import generate_notes
from src.financial.cash_flow import generate_cash_flow
from src.financial.equity_changes import generate_equity_changes
from src.tax.sru_mapping import aggregate_sru
from src.tax.sru_generator import generate_sru_file, generate_sru_files
from src.tax.ink2_tax_calc import calculate_ink2_tax
from src.tax.ink2s_calc import calculate_ink2s

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

# In-memory store for parsed SIE files (session-based)
_parsed_files: dict[str, SieFile] = {}
_file_names: dict[str, str] = {}
_mgmt_edits: dict[str, dict[str, str]] = {}  # file_id -> management report overrides
_signature_edits: dict[str, list[dict[str, str]]] = {}  # file_id -> [{name, role}]
_notes_edits: dict[str, dict[int, str]] = {}  # file_id -> {note_number: content}

UPLOAD_DIR = Path(__file__).parent.parent / "sieFiles"


@app.route("/")
def index():
    local_files = []
    if UPLOAD_DIR.exists():
        local_files = [f.name for f in UPLOAD_DIR.iterdir()
                       if f.suffix.lower() in (".se", ".si", ".sie")]
    return render_template("upload.html", local_files=local_files)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("Ingen fil vald.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if not file.filename:
        flash("Ingen fil vald.", "error")
        return redirect(url_for("index"))

    try:
        data = file.read()
        sie = parse_sie_bytes(data)
        file_id = uuid.uuid4().hex[:12]
        _parsed_files[file_id] = sie
        _file_names[file_id] = file.filename
        return redirect(url_for("report", file_id=file_id))
    except Exception as e:
        flash(f"Kunde inte parsa SIE-filen: {e}", "error")
        return redirect(url_for("index"))


@app.route("/load/<path:filename>")
def load_local(filename: str):
    """Load a SIE file from the sieFiles directory."""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        flash("Filen hittades inte.", "error")
        return redirect(url_for("index"))

    try:
        sie = parse_sie_file(filepath)
        file_id = uuid.uuid4().hex[:12]
        _parsed_files[file_id] = sie
        _file_names[file_id] = filename
        return redirect(url_for("report", file_id=file_id))
    except Exception as e:
        flash(f"Kunde inte parsa SIE-filen: {e}", "error")
        return redirect(url_for("index"))


def _get_signatures(sie: SieFile, file_id: str) -> list[dict[str, str]]:
    """Get signature list, defaulting to SIE contact as styrelseledamot."""
    if file_id in _signature_edits:
        return _signature_edits[file_id]
    name = sie.company.address_contact or ""
    return [{"name": name, "role": "Styrelseledamot"}] if name else []


def _get_mgmt_report(sie: SieFile, file_id: str) -> ManagementReport:
    """Generate management report with any user edits applied."""
    edits = _mgmt_edits.get(file_id, {})
    return generate_management_report(
        sie,
        company_location=edits.get("company_location", ""),
        business_description=edits.get("business_description", ""),
        significant_events=edits.get("significant_events", ""),
        expected_future_development=edits.get("expected_future_development", ""),
        profit_disposition_text=edits.get("profit_disposition_text", ""),
    )


@app.route("/report/<file_id>")
def report(file_id: str):
    sie = _parsed_files.get(file_id)
    if not sie:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    framework = request.args.get("framework", "K2")
    income_stmt = generate_income_statement(sie, framework=framework)
    balance = generate_balance_sheet(sie, framework=framework)
    mgmt_report = _get_mgmt_report(sie, file_id)
    notes = generate_notes(sie, framework=framework)

    # Apply user overrides to note content
    note_edits = _notes_edits.get(file_id, {})
    for note in notes.items:
        if note.number in note_edits:
            note.content = note_edits[note.number]

    # K3 requires additional reports
    cash_flow = generate_cash_flow(sie) if framework == "K3" else None
    equity_chg = generate_equity_changes(sie) if framework == "K3" else None

    return render_template(
        "report.html",
        sie=sie,
        income_stmt=income_stmt,
        balance=balance,
        mgmt_report=mgmt_report,
        notes=notes,
        cash_flow=cash_flow,
        equity_changes=equity_chg,
        framework=framework,
        file_id=file_id,
        filename=_file_names.get(file_id, ""),
        edits=_mgmt_edits.get(file_id, {}),
        signatures=_get_signatures(sie, file_id),
    )


@app.route("/report/<file_id>/edit", methods=["POST"])
def edit_mgmt_report(file_id: str):
    """Save management report edits and redirect back to report."""
    if file_id not in _parsed_files:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    _mgmt_edits[file_id] = {
        "company_location": request.form.get("company_location", "").strip(),
        "business_description": request.form.get("business_description", "").strip(),
        "significant_events": request.form.get("significant_events", "").strip(),
        "expected_future_development": request.form.get("expected_future_development", "").strip(),
        "profit_disposition_text": request.form.get("profit_disposition_text", "").strip(),
    }
    flash("Förvaltningsberättelsen har uppdaterats.", "success")
    return redirect(url_for("report", file_id=file_id))


@app.route("/report/<file_id>/edit-signatures", methods=["POST"])
def edit_signatures(file_id: str):
    """Save signature list edits."""
    if file_id not in _parsed_files:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    names = request.form.getlist("sig_name")
    roles = request.form.getlist("sig_role")
    sigs = []
    for name, role in zip(names, roles):
        name = name.strip()
        role = role.strip()
        if name:
            sigs.append({"name": name, "role": role or "Styrelseledamot"})
    _signature_edits[file_id] = sigs
    flash("Underskrifterna har uppdaterats.", "success")
    return redirect(url_for("report", file_id=file_id))


@app.route("/report/<file_id>/edit-note/<int:note_number>", methods=["POST"])
def edit_note(file_id: str, note_number: int):
    """Save a note content override."""
    if file_id not in _parsed_files:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    content = request.form.get("note_content", "").strip()
    if file_id not in _notes_edits:
        _notes_edits[file_id] = {}
    if content:
        _notes_edits[file_id][note_number] = content
    else:
        _notes_edits[file_id].pop(note_number, None)
    flash(f"Not {note_number} har uppdaterats.", "success")
    return redirect(url_for("report", file_id=file_id))


@app.route("/report/<file_id>/pdf")
def report_pdf(file_id: str):
    sie = _parsed_files.get(file_id)
    if not sie:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    framework = request.args.get("framework", "K2")
    income_stmt = generate_income_statement(sie, framework=framework)
    balance = generate_balance_sheet(sie, framework=framework)
    mgmt_report = _get_mgmt_report(sie, file_id)
    notes = generate_notes(sie, framework=framework)

    note_edits = _notes_edits.get(file_id, {})
    for note in notes.items:
        if note.number in note_edits:
            note.content = note_edits[note.number]

    cash_flow = generate_cash_flow(sie) if framework == "K3" else None
    equity_chg = generate_equity_changes(sie) if framework == "K3" else None

    html = render_template(
        "report_print.html",
        sie=sie,
        income_stmt=income_stmt,
        balance=balance,
        mgmt_report=mgmt_report,
        notes=notes,
        cash_flow=cash_flow,
        equity_changes=equity_chg,
        framework=framework,
        signatures=_get_signatures(sie, file_id),
    )

    from io import BytesIO
    from xhtml2pdf import pisa

    pdf_io = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_io)

    if pisa_status.err:
        flash("Kunde inte generera PDF.", "error")
        return redirect(url_for("report", file_id=file_id))

    pdf_io.seek(0)
    company_name = sie.company.name.replace(" ", "_")
    return send_file(
        pdf_io,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"arsredovisning_{company_name}.pdf",
    )


@app.route("/tax/<file_id>")
def tax_summary(file_id: str):
    sie = _parsed_files.get(file_id)
    if not sie:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    sru_fields = aggregate_sru(sie)
    tax_calc = calculate_ink2_tax(sie)
    ink2s = calculate_ink2s(sie)
    return render_template(
        "tax_summary.html",
        sie=sie,
        sru_fields=sru_fields,
        tax_calc=tax_calc,
        ink2s=ink2s,
        file_id=file_id,
    )


@app.route("/tax/<file_id>/sru")
def download_sru(file_id: str):
    sie = _parsed_files.get(file_id)
    if not sie:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    sru_files = generate_sru_files(sie)

    # Skatteverket requires two separate files: INFO.SRU and BLANKETTER.SRU
    # We package them in a zip for download.
    import zipfile
    from io import BytesIO
    zip_io = BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("INFO.SRU", sru_files.info_sru.encode("iso-8859-1", errors="replace"))
        zf.writestr("BLANKETTER.SRU", sru_files.blanketter_sru.encode("iso-8859-1", errors="replace"))
    zip_io.seek(0)
    org_nr = sie.company.org_number.replace("-", "")
    return send_file(
        zip_io,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"SRU_{org_nr}.zip",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
