import os
import glob
import json
from pathlib import Path

# Ensure repo root is on path
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CONVERTED_DIR = os.path.join(REPO_ROOT, "data", "documents", "converted")
OUT_DIR = os.path.join(REPO_ROOT, "data", "documents", "extracted", "agents_demo")
os.makedirs(OUT_DIR, exist_ok=True)

from backend.src.services import (
    AgentManager,
    DocumentExtractionAgent,
    NormalizedSummaryAgent,
)


def main():
    pdfs = sorted(glob.glob(os.path.join(CONVERTED_DIR, "*.pdf")))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {CONVERTED_DIR}")

    mgr = AgentManager([
        DocumentExtractionAgent(),
        NormalizedSummaryAgent(),
    ])

    for pdf_path in pdfs:
        ref_id = "UNKNOWN"
        base = os.path.basename(pdf_path)
        if "_REF-" in base:
            ref_id = "REF-" + base.split("_REF-")[-1].split(".")[0]

        # First run extraction
        results = mgr.run_all({
            "file_path": pdf_path,
            "document_type": "auto",
            # normalized agent needs text; fill after extraction
        })

        # Extract text for normalized agent
        extracted_text = ""
        for r in results:
            if r.name == "DocumentExtractionAgent" and r.success:
                extracted_text = (r.data.get("extracted_data") or {}).get("text", "")
                break

        # Re-run only normalized agent with text context
        norm_result = NormalizedSummaryAgent().run({
            "extracted_text": extracted_text,
            "referral_id": ref_id,
        })
        results.append(norm_result)

        out = {
            "pdf": pdf_path,
            "referral_id": ref_id,
            "results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "data": r.data,
                    "issues": r.issues,
                } for r in results
            ],
        }
        out_path = os.path.join(OUT_DIR, f"agents_{os.path.basename(pdf_path).rsplit('.',1)[0]}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"[OK] Agents run: {out_path}")

    print("\n✅ Done running agents across PDFs.")


if __name__ == "__main__":
    main()
