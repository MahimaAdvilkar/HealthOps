from __future__ import annotations
from typing import Any, Dict

def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst

def apply_agent_result(context: Dict[str, Any], result_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies agent outputs back into the shared context WITHOUT changing AgentManager behavior.
    Convention:
      - result_data["state"] updates context["state"]
      - result_data["decisions"] merges into context["decisions"]
      - result_data["normalized_patch"] deep-merges into context["normalized"]
      - result_data["actions_add"] extends context["actions"]
    """
    context.setdefault("decisions", {})
    context.setdefault("actions", [])
    context.setdefault("normalized", {})

    if not result_data:
        return context

    # decisions
    decisions = result_data.get("decisions") or {}
    if isinstance(decisions, dict):
        context["decisions"].update(decisions)

    # normalized patch
    patch = result_data.get("normalized_patch") or {}
    if isinstance(patch, dict) and patch:
        _deep_merge(context["normalized"], patch)

    # direct normalized payload
    normalized = result_data.get("normalized") or {}
    if isinstance(normalized, dict) and normalized:
        _deep_merge(context["normalized"], normalized)

    # actions
    actions_add = result_data.get("actions_add") or []
    if isinstance(actions_add, list) and actions_add:
        context["actions"].extend(actions_add)

    # state
    if result_data.get("state"):
        context["state"] = result_data["state"]

    # Compatibility bridge: map extracted text into context for downstream agents
    # Prefer explicit fields from the result payload, then fall back to heuristics.
    if "extracted_text" not in context:
        # Direct field
        v = result_data.get("extracted_text")
        if isinstance(v, str) and v.strip():
            context["extracted_text"] = v
        else:
            # From extracted_data blob
            ed = result_data.get("extracted_data")
            if isinstance(ed, dict):
                t = ed.get("text")
                if isinstance(t, str) and t.strip():
                    context["extracted_text"] = t
            # Fallback to common keys in result_data
            if "extracted_text" not in context:
                for candidate_key in ("text", "raw_text", "content"):
                    v2 = result_data.get(candidate_key)
                    if isinstance(v2, str) and v2.strip():
                        context["extracted_text"] = v2
                        break
            # Fallback to common keys already in context
            if "extracted_text" not in context:
                for candidate_key in ("text", "extracted", "raw_text", "content"):
                    v3 = context.get(candidate_key)
                    if isinstance(v3, str) and v3.strip():
                        context["extracted_text"] = v3
                        break

    # Compatibility bridge: ensure legacy extraction fields exist for agents expecting them
    # Shape: context["extraction"]["extraction"]["fields"]
    context.setdefault("extraction", {})
    context["extraction"].setdefault("extraction", {})
    context["extraction"]["extraction"].setdefault("fields", {})

    fields = context["extraction"]["extraction"]["fields"]
    # Populate from normalized keys if available
    norm = context.get("normalized") or {}
    # Some normalized agents may put nested structures (e.g., patient.name)
    patient = norm.get("patient") or {}
    payer = norm.get("payer") or {}
    if isinstance(patient, dict):
        if patient.get("name"):
            fields.setdefault("patient_name", patient["name"]) 
        if patient.get("dob"):
            fields.setdefault("date_of_birth", patient["dob"]) 
    # Flat normalized keys
    if norm.get("patient_name"):
        fields.setdefault("patient_name", norm["patient_name"]) 
    if norm.get("date_of_birth"):
        fields.setdefault("date_of_birth", norm["date_of_birth"]) 
    if norm.get("member_id"):
        fields.setdefault("member_id", norm["member_id"]) 
    if isinstance(payer, dict) and payer.get("member_id"):
        fields.setdefault("member_id", payer["member_id"]) 

    # Derive nested normalized entries for intake agent
    # Create patient, payer, referral nested structures if flat keys exist
    # Ensure nested dicts exist (coerce non-dicts into dicts)
    existing_patient = context["normalized"].get("patient")
    if not isinstance(existing_patient, dict):
        context["normalized"]["patient"] = {} if existing_patient is None else {"name": str(existing_patient)}
    patient_norm = context["normalized"]["patient"]

    existing_payer = context["normalized"].get("payer")
    if not isinstance(existing_payer, dict):
        context["normalized"]["payer"] = {} if existing_payer is None else {"name": str(existing_payer)}
    payer_norm = context["normalized"]["payer"]

    existing_referral = context["normalized"].get("referral")
    if not isinstance(existing_referral, dict):
        context["normalized"]["referral"] = {}
    referral_norm = context["normalized"]["referral"]

    # Map flat keys -> nested
    if norm.get("patient_name") and not patient_norm.get("name"):
        patient_norm["name"] = norm["patient_name"]
    if norm.get("date_of_birth") and not patient_norm.get("dob"):
        patient_norm["dob"] = norm["date_of_birth"]
    # Patient contact/address from flat keys
    addr = norm.get("patient_address") or norm.get("address")
    city = norm.get("patient_city") or norm.get("city")
    zipc = norm.get("patient_zip") or norm.get("zip")
    phone = norm.get("patient_phone") or norm.get("phone")
    if addr and not patient_norm.get("address"):
        patient_norm["address"] = addr if not city else f"{addr}, {city}{' ' + str(zipc) if zipc else ''}"
    if city and not patient_norm.get("city"):
        patient_norm["city"] = city
    if zipc and not patient_norm.get("zip"):
        patient_norm["zip"] = zipc
    if phone and not patient_norm.get("phone"):
        patient_norm["phone"] = phone
    payer_val = norm.get("payer")
    if isinstance(payer_val, dict):
        # If already dict, prefer its name
        if payer_val.get("name") and not payer_norm.get("name"):
            payer_norm["name"] = payer_val.get("name")
        if payer_val.get("member_id") and not payer_norm.get("member_id"):
            payer_norm["member_id"] = payer_val.get("member_id")
    else:
        if payer_val and not payer_norm.get("name"):
            payer_norm["name"] = payer_val
    if norm.get("member_id") and not payer_norm.get("member_id"):
        payer_norm["member_id"] = norm["member_id"]

    # Demo fallback: if member_id still missing, derive from other identifiers
    if not payer_norm.get("member_id"):
        # Prefer authorization number if present
        auth_num = norm.get("authorization_number")
        if isinstance(auth_num, str) and auth_num.strip():
            payer_norm["member_id"] = auth_num.strip()
        else:
            # fallback to referral_id if available
            ref_id = norm.get("referral_id")
            if isinstance(ref_id, str) and ref_id.strip():
                payer_norm["member_id"] = ref_id.strip()

    # Keep legacy fields in sync after fallbacks
    if payer_norm.get("member_id") and not fields.get("member_id"):
        fields["member_id"] = payer_norm["member_id"]

    # Assessment: derive nested normalized entries
    existing_assessment = context["normalized"].get("assessment")
    if not isinstance(existing_assessment, dict):
        context["normalized"]["assessment"] = {}
    assessment_norm = context["normalized"]["assessment"]

    # Map flat -> nested
    if norm.get("assessment_date") and not assessment_norm.get("date"):
        assessment_norm["date"] = norm["assessment_date"]
    if norm.get("assessment_status") and not assessment_norm.get("status"):
        assessment_norm["status"] = norm["assessment_status"].lower()
    # Inference from completed flag
    completed_val = (norm.get("assessment_completed") or "").strip().lower()
    if completed_val and not assessment_norm.get("status"):
        if completed_val in ("yes", "true", "completed", "complete", "done"):
            assessment_norm["status"] = "complete"
    # Pragmatic fallbacks: use document dates to imply assessment completion
    if not assessment_norm.get("date"):
        for fallback_key in ("signed_date", "date_of_service", "issued_date"):
            fv = norm.get(fallback_key)
            if isinstance(fv, str) and fv.strip():
                assessment_norm["date"] = fv.strip()
                break
    if not assessment_norm.get("status") and assessment_norm.get("date"):
        # If we have an assessment date via fallback, mark status complete
        assessment_norm["status"] = "complete"

    # requested_service from procedure or service_category+procedure
    proc = norm.get("procedure")
    svc_cat = norm.get("service_category")
    if not referral_norm.get("requested_service"):
        if proc and svc_cat:
            referral_norm["requested_service"] = f"{svc_cat} - {proc}"
        elif proc:
            referral_norm["requested_service"] = proc

    return context
