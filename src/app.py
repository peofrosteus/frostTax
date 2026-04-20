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
from src.financial.management_report import generate_management_report
from src.financial.notes import generate_notes
from src.tax.sru_mapping import aggregate_sru
from src.tax.sru_generator import generate_sru_file

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

# In-memory store for parsed SIE files (session-based)
_parsed_files: dict[str, SieFile] = {}
_file_names: dict[str, str] = {}

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


@app.route("/report/<file_id>")
def report(file_id: str):
    sie = _parsed_files.get(file_id)
    if not sie:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    framework = request.args.get("framework", "K2")
    income_stmt = generate_income_statement(sie, framework=framework)
    balance = generate_balance_sheet(sie, framework=framework)
    mgmt_report = generate_management_report(sie)
    notes = generate_notes(sie, framework=framework)

    return render_template(
        "report.html",
        sie=sie,
        income_stmt=income_stmt,
        balance=balance,
        mgmt_report=mgmt_report,
        notes=notes,
        framework=framework,
        file_id=file_id,
        filename=_file_names.get(file_id, ""),
    )


@app.route("/report/<file_id>/pdf")
def report_pdf(file_id: str):
    sie = _parsed_files.get(file_id)
    if not sie:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    framework = request.args.get("framework", "K2")
    income_stmt = generate_income_statement(sie, framework=framework)
    balance = generate_balance_sheet(sie, framework=framework)
    mgmt_report = generate_management_report(sie)
    notes = generate_notes(sie, framework=framework)

    html = render_template(
        "report_print.html",
        sie=sie,
        income_stmt=income_stmt,
        balance=balance,
        mgmt_report=mgmt_report,
        notes=notes,
        framework=framework,
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
    return render_template(
        "tax_summary.html",
        sie=sie,
        sru_fields=sru_fields,
        file_id=file_id,
    )


@app.route("/tax/<file_id>/sru")
def download_sru(file_id: str):
    sie = _parsed_files.get(file_id)
    if not sie:
        flash("Filen har gått ut. Ladda upp igen.", "error")
        return redirect(url_for("index"))

    sru_content = generate_sru_file(sie)
    from io import BytesIO
    sru_io = BytesIO(sru_content.encode("iso-8859-1", errors="replace"))
    sru_io.seek(0)
    org_nr = sie.company.org_number.replace("-", "")
    return send_file(
        sru_io,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"INK2_{org_nr}.sru",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
