import os
import json
import glob
from datetime import datetime

# Make sure repo root is on PYTHONPATH even if you forget PYTHONPATH=.
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

RAW_DIR = os.path.join(REPO_ROOT, "data", "documents", "raw")
OUT_DIR = os.path.join(REPO_ROOT, "data", "documents", "extracted")
os.makedirs(OUT_DIR, exist_ok=True)

# We’ll try to use your existing LandingAI service if it exists.
# If not, we’ll fall back to a simple local “stub extraction” so the demo still works.
def try_landingai_extract(text: str) -> dict:
    """Attempt to run LandingAIService against provided text as file bytes.

    Falls back to a stub extraction if the service isn't available or fails.
    """
    try:
        import asyncio
        from backend.src.services.landingai_service import LandingAIService  # type: ignore

        svc = LandingAIService()
        # Use the async API with file_bytes to send the packet as a single document.
        result = asyncio.run(
            svc.process_document(
                file_bytes=text.encode("utf-8"),
                document_type="referral_packet",
            )
        )
        return result
    except Exception as e:
        # Stub extraction (demo-safe) – keeps project moving even without LandingAI credentials.
        return {
            "_mode": "stub",
            "_note": f"LandingAI not used ({type(e).__name__}: {e})",
            "extracted_at": datetime.utcnow().isoformat() + "Z",
            "fields": {}
        }

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def main():
    if not os.path.isdir(RAW_DIR):
        raise FileNotFoundError(f"RAW_DIR not found: {RAW_DIR}")

    files = sorted(glob.glob(os.path.join(RAW_DIR, "*")))
    if not files:
        raise FileNotFoundError(f"No files found in {RAW_DIR}")

    # Group by REF id based on filename suffix like *_REF-1001.txt
    packets = {}
    for fp in files:
        base = os.path.basename(fp)
        ref_id = "UNKNOWN"
        if "_REF-" in base:
            ref_id = "REF-" + base.split("_REF-")[-1].split(".")[0]
        packets.setdefault(ref_id, []).append(fp)

    results = []
    for ref_id, fps in packets.items():
        combined_text = ""
        for fp in fps:
            combined_text += f"\n\n===== FILE: {os.path.basename(fp)} =====\n"
            combined_text += read_file(fp)

        extracted = try_landingai_extract(combined_text)

        out = {
            "referral_id": ref_id,
            "packet_files": [os.path.basename(x) for x in fps],
            "raw_dir": RAW_DIR,
            "extraction": extracted,
        }
        results.append(out)

        out_path = os.path.join(OUT_DIR, f"extraction_{ref_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

        print(f"[OK] Wrote: {out_path}")

    index_path = os.path.join(OUT_DIR, "extraction_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Done. Index: {index_path}")

    # Optional: Quick summary of tables presence across packets for easy tabular review
    summary_rows = []
    for item in results:
        ref_id = item.get("referral_id")
        extraction = item.get("extraction", {})
        success = extraction.get("success")
        tables = None
        if isinstance(extraction, dict) and extraction.get("extracted_data"):
            tables = extraction["extracted_data"].get("tables")
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

if __name__ == "__main__":
    main()
