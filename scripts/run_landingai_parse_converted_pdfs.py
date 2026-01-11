import os
import json
import glob
from datetime import datetime

# Ensure repo root is on path
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CONVERTED_DIR = os.path.join(REPO_ROOT, "data", "documents", "converted")
OUT_DIR = os.path.join(REPO_ROOT, "data", "documents", "extracted", "individual")
os.makedirs(OUT_DIR, exist_ok=True)
TABLES_DIR = os.path.join(OUT_DIR, "tables")
os.makedirs(TABLES_DIR, exist_ok=True)


def parse_doc_type(filename: str) -> str:
    base = os.path.basename(filename).lower()
    if base.startswith("auth_approval_"):
        return "auth_approval"
    if base.startswith("billing_readiness_"):
        return "billing_readiness"
    if base.startswith("referral_intake_"):
        return "referral_intake"
    if base.startswith("visit_note_"):
        return "visit_note"
    return "unknown"


def parse_ref_id(filename: str) -> str:
    base = os.path.basename(filename)
    if "_REF-" in base:
        return "REF-" + base.split("_REF-")[-1].split(".")[0]
    return "UNKNOWN"


def export_tables(ref_id: str, base_pdf: str, extracted_data: dict):
    tables = extracted_data.get("tables")
    if not isinstance(tables, list) or not tables:
        return []
    import csv
    written = []
    for idx, chunk in enumerate(tables):
        md = chunk.get("markdown") or ""
        # Simple markdown table parse: split by '|' keeping header and rows
        lines = [l.strip() for l in md.splitlines() if "|" in l]
        if len(lines) < 2:
            continue
        header = [c.strip() for c in lines[0].split("|")]
        if header and header[0] == "":
            header = header[1:]
        if header and header[-1] == "":
            header = header[:-1]
        rows = []
        for l in lines[2:]:  # skip header and separator
            cells = [c.strip() for c in l.split("|")]
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]
            if any(cell for cell in cells):
                rows.append(cells)
        csv_path = os.path.join(TABLES_DIR, f"{os.path.basename(base_pdf).rsplit('.',1)[0]}_table_{idx+1}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if header:
                writer.writerow(header)
            for r in rows:
                writer.writerow(r)
        written.append(csv_path)
    return written


def export_kv_csv(ref_id: str, base_pdf: str, extracted_data: dict):
    import csv
    text = extracted_data.get("text", "")
    kv_rows = []
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if key and val and len(key) < 80:
                kv_rows.append({"referral_id": ref_id, "key": key, "value": val})
    out_csv = os.path.join(OUT_DIR, f"kv_{os.path.basename(base_pdf).rsplit('.',1)[0]}.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["referral_id", "key", "value"])
        writer.writeheader()
        for r in kv_rows:
            writer.writerow(r)
    return out_csv


def add_to_summary(summary_rows: list, ref_id: str, doc_type: str, result: dict):
    ed = result.get("extracted_data") or {}
    tables = ed.get("tables")
    table_count = len(tables) if isinstance(tables, list) else 0
    summary_rows.append({
        "referral_id": ref_id,
        "doc_type": doc_type,
        "success": result.get("success"),
        "table_count": table_count,
        "processing_time": result.get("processing_time"),
    })


def main():
    files = sorted(glob.glob(os.path.join(CONVERTED_DIR, "*.pdf")))
    if not files:
        raise FileNotFoundError(f"No PDFs found in {CONVERTED_DIR}")

    from backend.src.services.landingai_service import LandingAIService
    import asyncio
    svc = LandingAIService()

    summary = []
    for pdf_path in files:
        doc_type = parse_doc_type(pdf_path)
        ref_id = parse_ref_id(pdf_path)
        result = asyncio.run(
            svc.process_document(
                file_path=pdf_path,
                document_type=doc_type,
            )
        )

        out = {
            "referral_id": ref_id,
            "doc_type": doc_type,
            "pdf": pdf_path,
            "extraction": result,
        }
        out_path = os.path.join(OUT_DIR, f"extraction_{os.path.basename(pdf_path).rsplit('.',1)[0]}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"[OK] Wrote: {out_path}")

        # Exports
        if isinstance(result, dict) and result.get("extracted_data"):
            export_tables(ref_id, pdf_path, result["extracted_data"])
            export_kv_csv(ref_id, pdf_path, result["extracted_data"])
        add_to_summary(summary, ref_id, doc_type, result)

    # Write summary CSV
    import csv
    summary_csv = os.path.join(OUT_DIR, "summary_individual.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["referral_id", "doc_type", "success", "table_count", "processing_time"])
        writer.writeheader()
        for r in summary:
            writer.writerow(r)
    print(f"\n✅ Summary: {summary_csv}")


if __name__ == "__main__":
    main()
