import os
import glob
from pathlib import Path

# Ensure repo root is on path
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

RAW_DIR = os.path.join(REPO_ROOT, "data", "documents", "raw")
OUT_DIR = os.path.join(REPO_ROOT, "data", "documents", "converted")
os.makedirs(OUT_DIR, exist_ok=True)


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def sanitize(s: str) -> str:
    return (
        s.replace("\u2013", "-")
         .replace("\u2014", "-")
         .replace("\u2019", "'")
         .replace("\u2018", "'")
         .replace("\u201c", '"')
         .replace("\u201d", '"')
    )


def txt_to_pdf(txt_path: str, pdf_path: str):
    from fpdf import FPDF
    text = read_file(txt_path)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, sanitize(text))
    pdf.output(pdf_path)


def main():
    if not os.path.isdir(RAW_DIR):
        raise FileNotFoundError(f"RAW_DIR not found: {RAW_DIR}")

    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.txt")))
    if not files:
        print("No .txt files found to convert.")
        return

    for fp in files:
        base = os.path.basename(fp)
        out_pdf = os.path.join(OUT_DIR, base.rsplit(".", 1)[0] + ".pdf")
        txt_to_pdf(fp, out_pdf)
        print(f"[OK] Converted: {fp} -> {out_pdf}")

    print(f"\n✅ Done. PDFs in: {OUT_DIR}")


if __name__ == "__main__":
    main()