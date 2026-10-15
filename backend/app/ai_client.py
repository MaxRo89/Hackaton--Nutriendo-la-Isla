import json
import os
import re
from concurrent.futures import ThreadPoolExecutor


def _candidate_models():
    return ["gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]


def _configured_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    try:
        genai.configure(api_key=api_key)
        return genai
    except Exception:
        return None


def _safe_call(prompt, timeout_seconds=5):
    genai = _configured_client()
    if genai is None:
        return ""

    last_error = None
    for model_name in _candidate_models():
        try:
            model = genai.GenerativeModel(model_name)
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(model.generate_content, prompt)
                return future.result(timeout=timeout_seconds)
        except Exception as exc:
            last_error = exc
    return ""


def _text_from_response(response):
    if response is None:
        return ""
    text = getattr(response, "text", "")
    if isinstance(text, str) and text.strip():
        return text.strip()
    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list):
        text_chunks = []
        for candidate in candidates:
            for part in getattr(candidate, "content", getattr(candidate, "parts", [])):
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    text_chunks.append(part_text)
        if text_chunks:
            return "".join(text_chunks).strip()
    raw = str(response).strip()
    return raw


def _clean_structured_text(text):
    value = (text or "").strip()
    if value.startswith("```"):
        segments = value.split("```")
        if len(segments) >= 3:
            value = segments[1].strip()
            if value.lower() in {"json", "javascript"}:
                value = segments[2].strip()
    return value


def _normalize_list(values, max_items=3, max_length=120):
    items = []
    for value in values:
        text = re.sub(r"\s+", " ", str(value)).strip()
        if not text:
            continue
        if len(text) > max_length:
            trimmed = text[: max_length - 3].rstrip()
            text = f"{trimmed}..."
        if text not in items:
            items.append(text)
    return items[:max_items]


def generate_donation_hints(payload):
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return []
    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    allergens = str(payload.get("allergens") or "").strip()
    storage_notes = str(payload.get("storage_notes") or "").strip()
    handling_notes = str(payload.get("handling_notes") or "").strip()
    food_category = str(payload.get("food_category") or "").strip()
    prompt = (
        "Eres un asistente de revisión para donaciones solidarias. "
        "Tu tarea es detectar información crítica que falte, pero no decides la seguridad ni el valor del alimento. "
        "Responde solo en JSON con una lista de 0 a 3 sugerencias en español. "
        "Cada sugerencia debe ser breve, útil y no superar 120 caracteres. "
        "No incluyas explicaciones ni texto extra.\n\n"
        f"title: {title}\n"
        f"description: {description}\n"
        f"allergens: {allergens}\n"
        f"storage_notes: {storage_notes}\n"
        f"handling_notes: {handling_notes}\n"
        f"food_category: {food_category}\n"
    )
    response = _safe_call(prompt, timeout_seconds=5)
    text = _clean_structured_text(_text_from_response(response))
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for key in ("suggestions", "hints", "items"):
                if isinstance(parsed.get(key), list):
                    return _normalize_list(parsed[key])
        if isinstance(parsed, list):
            return _normalize_list(parsed)
    except json.JSONDecodeError:
        pass
    raw_candidates = re.split(r"\n|;|\.|\*|\-|\[|\]", text)
    return _normalize_list(raw_candidates)


def generate_application_summary(answers):
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return ""
    compact = json.dumps(answers or {}, ensure_ascii=False, sort_keys=True)
    prompt = (
        "Resume de forma neutra sin recomendar aprobación ni rechazo. "
        "Genera un párrafo breve en español de máximo 200 caracteres que describa la solicitud sin emitir juicios ni decisiones. "
        "No incluya recomendaciones ni evaluaciones automáticas.\n\n"
        f"Respuestas: {compact}"
    )
    response = _safe_call(prompt, timeout_seconds=5)
    summary = _text_from_response(response)
    if not summary:
        return ""
    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > 200:
        summary = summary[:197].rstrip() + "..."
    return summary
