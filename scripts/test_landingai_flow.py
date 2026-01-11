import os
import json
import glob
import re
from datetime import datetime
from pathlib import Path

# Ensure repo root is on path
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

RAW_DIR = os.path.join(REPO_ROOT, "data", "documents", "raw")
OUT_DIR = os.path.join(REPO_ROOT, "data", "documents", "extracted")
CONVERTED_DIR = os.path.join(REPO_ROOT, "data", "documents", "converted")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def build_pdf_for_packet(ref_id: str, files: list[str]) -> str:
    """Build a simple PDF from text files to enable LandingAI parsing."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    def sanitize(s: str) -> str:
        # Replace common unicode punctuation with ASCII equivalents for core fonts
        return (
            s.replace("\u2013", "-")
             .replace("\u2014", "-")
             .replace("\u2019", "'")
             .replace("\u2018", "'")
             .replace("\u201c", '"')
             .replace("\u201d", '"')
        )

    for fp in files:
        text = read_file(fp)
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        safe_text = sanitize(text)
        pdf.multi_cell(0, 10, f"FILE: {os.path.basename(fp)}\n\n{safe_text}")

    out_path = os.path.join(CONVERTED_DIR, f"packet_{ref_id}.pdf")
    pdf.output(out_path)
    return out_path


def main():
    if not os.path.isdir(RAW_DIR):
        raise FileNotFoundError(f"RAW_DIR not found: {RAW_DIR}")

    files = sorted(glob.glob(os.path.join(RAW_DIR, "*")))
    if not files:
        raise FileNotFoundError(f"No files found in {RAW_DIR}")

    # Group by REF id based on filename suffix like *_REF-1001.txt
    packets: dict[str, list[str]] = {}
    for fp in files:
        base = os.path.basename(fp)
        ref_id = "UNKNOWN"
        if "_REF-" in base:
            ref_id = "REF-" + base.split("_REF-")[-1].split(".")[0]
        packets.setdefault(ref_id, []).append(fp)

    from backend.src.services.landingai_service import LandingAIService
    import asyncio

    svc = LandingAIService()

    results = []
    for ref_id, fps in packets.items():
        # Build a PDF from the packet text files
        pdf_path = build_pdf_for_packet(ref_id, fps)

        # Process via LandingAI
        result = asyncio.run(
            svc.process_document(
                file_path=pdf_path,
                document_type="referral_packet",
            )
        )

        out = {
            "referral_id": ref_id,
            "packet_files": [os.path.basename(x) for x in fps],
            "raw_dir": RAW_DIR,
            "converted_pdf": pdf_path,
            "extraction": result,
        }
        results.append(out)

        out_path = os.path.join(OUT_DIR, f"extraction_{ref_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"[OK] Wrote: {out_path}")

        # Per-table CSV export when tables are present
        tables = None
        if isinstance(result, dict) and result.get("extracted_data"):
            tables = result["extracted_data"].get("tables")
        if isinstance(tables, list) and tables:
            tables_dir = os.path.join(OUT_DIR, "tables")
            os.makedirs(tables_dir, exist_ok=True)

            def parse_markdown_table(md: str):
                lines = [l.strip() for l in md.splitlines() if "|" in l]
                if len(lines) < 2:
                    return [], []
                # Find header and separator indices
                header_idx = 0
                sep_idx = 1 if len(lines) > 1 else -1
                header = [c.strip() for c in lines[header_idx].split("|")]
                if header and header[0] == "":
                    header = header[1:]
                if header and header[-1] == "":
                    header = header[:-1]
                rows = []
                for l in lines[sep_idx+1:]:
                    cells = [c.strip() for c in l.split("|")]
                    if cells and cells[0] == "":
                        cells = cells[1:]
                    if cells and cells[-1] == "":
                        cells = cells[:-1]
                    if any(cell for cell in cells):
                        rows.append(cells)
                return header, rows

            import csv
            for idx, chunk in enumerate(tables):
                md = chunk.get("markdown") or ""
                header, rows = parse_markdown_table(md)
                csv_path = os.path.join(tables_dir, f"{ref_id}_table_{idx+1}.csv")
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if header:
                        writer.writerow(header)
                    for r in rows:
                        writer.writerow(r)
                print(f"[OK] Table CSV: {csv_path}")

    index_path = os.path.join(OUT_DIR, "extraction_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Done. Index: {index_path}")

    # Tables summary
    summary_rows = []
    kv_rows = []
    for item in results:
        ref_id = item.get("referral_id")
        extraction = item.get("extraction", {})
        success = extraction.get("success")
        tables = None
        if isinstance(extraction, dict) and extraction.get("extracted_data"):
            tables = extraction["extracted_data"].get("tables")
            text = extraction["extracted_data"].get("text", "")
            # Simple KV parsing: lines like "Key: Value"
            for line in text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if key and val and len(key) < 80:
                        kv_rows.append({
                            "referral_id": ref_id,
                            "key": key,
                            "value": val,
                        })
        table_count = len(tables) if isinstance(tables, list) else 0
        summary_rows.append({
            "referral_id": ref_id,
            "success": success,
            "table_count": table_count,
        })

    summary_path = os.path.join(OUT_DIR, "tables_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_rows, f, indent=2)
    print(f"📊 Tables summary: {summary_path}")

    # Write KV summary CSV for a tabular view when no tables are present
    kv_csv_path = os.path.join(OUT_DIR, "kv_summary.csv")
    try:
        import csv
        with open(kv_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["referral_id", "key", "value"])
            writer.writeheader()
            for row in kv_rows:
                writer.writerow(row)
        print(f"📑 KV summary CSV: {kv_csv_path}")
    except Exception as e:
        print(f"⚠️ Failed to write KV summary CSV: {e}")

    # Build a normalized table CSV for downstream systems
    normalized_csv_path = os.path.join(OUT_DIR, "normalized_summary.csv")
    try:
        import csv
        # Aggregate per referral
        by_ref: dict[str, dict[str, str]] = {}

        def norm_key(k: str) -> str | None:
            kl = k.strip().lower()
            mapping = {
                "referral id": "referral_id",
                "patient name": "patient_name",
                "date of birth": "date_of_birth",
                "payer": "payer",
                "payer name": "payer",
                "plan type": "plan_type",
                "authorization status": "authorization_status",
                "authorization number": "authorization_number",
                "authorization required": "authorization_required",
                "authorization start date": "authorization_start_date",
                "authorization end date": "authorization_end_date",
                "authorized units": "authorized_units",
                "units used": "units_used",
                "units delivered": "units_delivered",
                "unit type": "unit_type",
                "service category": "service_category",
                "procedure": "procedure",
                "date of service": "date_of_service",
                "ready to bill": "ready_to_bill",
                "billing hold reason": "billing_hold_reason",
                "facility": "facility",
                "city": "city",
                "technician name": "technician_name",
                "signed date": "signed_date",
                "issued date": "issued_date",
                "issued by": "issued_by",
            }
            return mapping.get(kl)

        for row in kv_rows:
            rid = row["referral_id"]
            k = row["key"]
            v = row["value"]
            nk = norm_key(k)
            if nk:
                by_ref.setdefault(rid, {})
                # do not overwrite referral_id key if exists
                if nk == "referral_id":
                    by_ref[rid][nk] = rid
                else:
                    by_ref[rid][nk] = v

        # Columns order for consistency
        cols = [
            "referral_id",
            "patient_name",
            "date_of_birth",
            "payer",
            "plan_type",
            "authorization_required",
            "authorization_status",
            "authorization_number",
            "authorization_start_date",
            "authorization_end_date",
            "authorized_units",
            "units_used",
            "units_delivered",
            "unit_type",
            "service_category",
            "procedure",
            "date_of_service",
            "ready_to_bill",
            "billing_hold_reason",
            "facility",
            "city",
            "technician_name",
            "signed_date",
            "issued_date",
            "issued_by",
        ]

        with open(normalized_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols)
            writer.writeheader()
            for rid, data in by_ref.items():
                row = {c: data.get(c, "") for c in cols}
                # ensure referral_id populated
                row["referral_id"] = rid
                writer.writerow(row)
        print(f"📎 Normalized CSV: {normalized_csv_path}")
    except Exception as e:
        print(f"⚠️ Failed to write normalized CSV: {e}")


if __name__ == "__main__":
    main()
