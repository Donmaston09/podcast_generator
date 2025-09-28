

# json_prompt_expert_app_enhanced.py
import streamlit as st
import json
import textwrap
import re
from slugify import slugify
from datetime import datetime
from typing import Dict, Any, List, Optional

# Optional imports (OpenAI + jsonschema)
try:
    import openai
except Exception:
    openai = None

try:
    from jsonschema import validate, Draft7Validator, exceptions as jsonschema_exceptions
except Exception:
    validate = None
    Draft7Validator = None
    jsonschema_exceptions = None

st.set_page_config(page_title="JSON Prompt Expert (Enhanced)", layout="wide")

st.title("🧩 Natural Language to JSON Prompt Builder")
st.markdown(
    "<h4 style='color: grey;'>From plain text to perfect JSON — faster prompts, better AI results</h4>",
    unsafe_allow_html=True
)

st.markdown(
    "**by Anthony Onoja, Ph.D. | Email: [donmaston09@gmail.com](mailto:donmaston09@gmail.com), YouTube: [@tonyonoja7880](https://www.youtube.com/@tonyonoja7880)**",
    unsafe_allow_html=False # HTML is not needed here
)
# -------------------------------
# JSON Schemas for validation
# -------------------------------
SCHEMAS = {
    "veo3_video": {
        "type": "object",
        "required": ["scene_description", "duration", "aspect_ratio", "style"],
        "properties": {
            "scene_description": {"type": "string"},
            "camera_movement": {"type": "string"},
            "lighting": {"type": "string"},
            "style": {"type": "string"},
            "duration": {"type": "number", "minimum": 0},
            "aspect_ratio": {"type": "string"},
            "audio": {
                "type": "object",
                "properties": {
                    "music": {"type": "boolean"},
                    "narration": {"type": "boolean"}
                },
                "additionalProperties": False
            },
            "meta": {"type": "object"}
        },
        "additionalProperties": True
    },
    "image": {
        "type": "object",
        "required": ["prompt", "size", "quality"],
        "properties": {
            "prompt": {"type": "string"},
            "style": {"type": "string"},
            "quality": {"type": "string"},
            "size": {"type": "string", "pattern": r"^\d{2,4}x\d{2,4}$"},
            "negative_prompt": {"type": "string"},
            "composition": {"type": "string"},
            "meta": {"type": "object"}
        },
        "additionalProperties": True
    },
    "code": {
        "type": "object",
        "required": ["task", "language", "requirements"],
        "properties": {
            "task": {"type": "string"},
            "language": {"type": "string"},
            "requirements": {"type": "array", "items": {"type": "string"}},
            "constraints": {"type": "object"},
            "output_format": {"type": "string"},
            "meta": {"type": "object"}
        },
        "additionalProperties": True
    },
    "other": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "style": {"type": "string"},
            "constraints": {"type": ["array", "string"]},
            "meta": {"type": "object"}
        },
        "additionalProperties": True
    }
}

# -------------------------------
# Helper functions
# -------------------------------
def pretty_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)

def validate_schema(tool: str, data: Dict[str, Any]) -> List[str]:
    """Return list of validation errors (strings). Empty if OK."""
    errors = []
    if validate is None or Draft7Validator is None:
        errors.append("jsonschema package not available in runtime. Install 'jsonschema' to enable validation.")
        return errors
    schema = SCHEMAS.get(tool, SCHEMAS["other"])
    validator = Draft7Validator(schema)
    for err in sorted(validator.iter_errors(data), key=str):
        path = ".".join([str(p) for p in err.path]) or "(root)"
        errors.append(f"{path}: {err.message}")
    return errors

def natural_to_template(tool: str, text: str) -> Dict[str, Any]:
    t = text.strip()
    lower = t.lower()
    now = datetime.utcnow().isoformat() + "Z"
    template = {"meta": {"created_at": now, "source_text": text}}

    if tool == "veo3_video":
        template.update({
            "scene_description": textwrap.shorten(t, width=600, placeholder="..."),
            "camera_movement": "static",
            "lighting": "natural",
            "style": "cinematic",
            "duration": 8,
            "aspect_ratio": "16:9",
            "audio": {"music": False, "narration": False}
        })
        m = re.search(r"(\d+)\s*(s|sec|secs|seconds|second|m|min|minutes)", lower)
        if m:
            val = int(m.group(1))
            if m.group(2).startswith("m"):
                template["duration"] = val * 60
            else:
                template["duration"] = val
        if "vertical" in lower or "tiktok" in lower or "9:16" in lower:
            template["aspect_ratio"] = "9:16"
        if any(w in lower for w in ["pan", "tilt", "dolly", "zoom", "tracking", "follow"]):
            template["camera_movement"] = "cinematic_tracking"
        if any(w in lower for w in ["golden hour", "sunset", "soft light", "studio light", "dramatic"]):
            template["lighting"] = "dramatic"
        if any(w in lower for w in ["cinematic", "film", "8k", "ultra realistic", "photorealistic"]):
            template["style"] = "cinematic_photorealistic"
        if any(w in lower for w in ["cartoon", "2d", "anime", "cel-shaded"]):
            template["style"] = "cartoon"

    elif tool == "image":
        template.update({
            "prompt": textwrap.shorten(t, width=1000, placeholder="..."),
            "style": "photorealistic",
            "quality": "high",
            "size": "1024x1024",
            "negative_prompt": "low-quality, blurry, deformed, text, watermark",
            "composition": "centered_subject"
        })
        m = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", text)
        if m:
            template["size"] = f"{m.group(1)}x{m.group(2)}"
        if "cinematic" in lower:
            template["style"] = "cinematic"
            template["composition"] = "wide"
        if "illustration" in lower or "vector" in lower:
            template["style"] = "illustration"

    elif tool == "code":
        lang = None
        if "python" in lower or "py " in lower:
            lang = "python"
        elif "javascript" in lower or "js " in lower:
            lang = "javascript"
        elif "r " in lower or "rstudio" in lower:
            lang = "r"
        template.update({
            "task": textwrap.shorten(t, width=1000, placeholder="..."),
            "language": lang or "python",
            "requirements": [],
            "constraints": {"no_external_network": False, "security": "avoid-shell-execution", "time_complexity": None},
            "output_format": "file"
        })
        if "scrape" in lower or "scraping" in lower:
            template["requirements"].extend(["requests", "beautifulsoup4"])
        if "pandas" in lower or "dataframe" in lower:
            template["requirements"].append("pandas")
        if "notebook" in lower or "jupyter" in lower:
            template["output_format"] = "notebook"
    else:
        template.update({"prompt": t, "style": "neutral", "quality": "standard", "constraints": []})

    return template

def merge_manual_fields(base: Dict[str, Any], manual: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for k, v in manual.items():
        if v is None or (isinstance(v, str) and v.strip() == ""):
            continue
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = merge_manual_fields(merged.get(k, {}), v)
        else:
            merged[k] = v
    return merged

def openai_enrich(prompt_text: str, tool: str, openai_key: str, model: str = "gpt-4"):
    """Call OpenAI to extract structured fields from a natural language description."""
    if openai is None:
        return {"error": "OpenAI SDK not installed in environment."}
    if not openai_key:
        return {"error": "No OpenAI API key provided."}
    openai.api_key = openai_key
    system = (
        "You are a JSON Prompt Expert. Extract and return a JSON object with keys appropriate for "
        "the requested tool. Only return valid JSON. Keys should match expected schema for the tool. "
        "If a field cannot be inferred, omit it."
    )
    tool_hint = f"tool: {tool}"
    user = f"{tool_hint}\n\nDescription:\n{prompt_text}\n\nReturn only JSON."
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0.0,
            max_tokens=600
        )
        text = resp["choices"][0]["message"]["content"]
        j = None
        try:
            j = json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                try:
                    j = json.loads(m.group(0))
                except Exception as e:
                    return {"error": f"Failed to parse JSON: {e}. Raw response: {text}"}
            else:
                return {"error": "No JSON found in model response.", "raw": text}
        return {"ok": j}
    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# UI - Sidebar & inputs
# -------------------------------
st.subheader("JSON Prompt Expert — Enhanced (LLM enrichment + Schema validation)")
st.markdown("Enter a natural language description and optionally use an LLM to auto-extract structured fields. Validate JSON against schemas before downloading.")

with st.sidebar:
    st.header("Settings & Integrations")
    tool_key = st.selectbox("Target tool", options=["veo3_video","image","code","other"])
    st.subheader("OpenAI (optional)")
    openai_key = st.text_input("OpenAI API key (sk-...)", type="password")
    openai_model = st.text_input("OpenAI model", value="gpt-4")
    st.caption("If you provide an API key, the app can call OpenAI to enrich/parse your description into JSON fields.")

    st.markdown("---")
    st.header("Output")
    filename_prefix = st.text_input("Filename prefix", value="prompt")
    pretty = st.checkbox("Pretty-print JSON", value=True)
    include_meta = st.checkbox("Include metadata", value=True)
    use_llm = st.checkbox("Use LLM for auto-parsing/enrichment", value=False)

# Main input
st.subheader("Natural language request")
user_text = st.text_area("Describe what you want:", height=250)
if not user_text:
    st.info("Tip: include objective, style, format, constraints, examples, and desired output size/duration.")

# Manual overrides area
st.markdown("### Manual overrides (optional)")
manual = {}
if tool_key == "veo3_video":
    manual["scene_description"] = st.text_input("Scene description override", value="")
    manual["camera_movement"] = st.selectbox("Camera movement", options=["", "static","pan","dolly","tracking","cinematic_tracking"])
    manual["lighting"] = st.selectbox("Lighting", options=["", "natural","studio","dramatic","golden_hour","low_key"])
    manual["style"] = st.selectbox("Style", options=["", "cinematic","cinematic_photorealistic","cartoon","documentary","vintage"])
    manual["duration"] = st.number_input("Duration (seconds)", min_value=1, max_value=3600, value=8)
    manual["aspect_ratio"] = st.selectbox("Aspect ratio", options=["","16:9","9:16","1:1","4:5"])
    audio_music = st.checkbox("Include background music", value=False)
    audio_narration = st.checkbox("Include narration", value=False)
    manual["audio"] = {"music": audio_music, "narration": audio_narration}
elif tool_key == "image":
    manual["prompt"] = st.text_input("Prompt override", value="")
    manual["style"] = st.selectbox("Style", options=["","photorealistic","illustration","vector","cinematic","graphic"])
    manual["quality"] = st.selectbox("Quality", options=["","low","medium","high","ultra"], index=3)
    manual["size"] = st.text_input("Size (e.g. 1024x1024)", value="1024x1024")
    manual["negative_prompt"] = st.text_input("Negative prompt (avoid)", value="low-quality, blurry, watermark")
    manual["composition"] = st.text_input("Composition", value="centered_subject")
elif tool_key == "code":
    manual["task"] = st.text_input("Task summary / prompt", value="")
    manual["language"] = st.selectbox("Language", options=["","python","javascript","r","bash","go","java"])
    manual["requirements"] = st.text_input("Requirements (comma-separated)", value="")
    c1 = st.checkbox("Avoid external network calls", value=True)
    c2 = st.checkbox("Prefer standard library only", value=False)
    manual["constraints"] = {"no_external_network": c1, "stdlib_only": c2}
    manual["output_format"] = st.selectbox("Output format", options=["","code_block","file","notebook"], index=1)
else:
    manual["prompt"] = st.text_input("Prompt override", value="")
    manual["style"] = st.text_input("Style", value="neutral")
    manual["constraints"] = st.text_input("Constraints (comma-separated)", value="")

# Generate base or LLM-enriched JSON
st.markdown("---")
if st.button("Generate JSON Prompt"):
    if not user_text or user_text.strip() == "":
        st.error("Please enter a natural language request.")
    else:
        base = natural_to_template(tool_key, user_text)
        enriched = {}
        if use_llm:
            if openai is None:
                st.error("OpenAI SDK not available. Install 'openai' to use LLM enrichment.")
            elif not openai_key:
                st.error("Please provide your OpenAI API key to use LLM enrichment.")
            else:
                with st.spinner("Calling OpenAI to extract structured fields..."):
                    result = openai_enrich(user_text, tool_key, openai_key, model=openai_model)
                    if "error" in result:
                        st.error(f"LLM error: {result.get('error')}")
                        if result.get("raw"):
                            st.code(result.get("raw"))
                    else:
                        enriched = result.get("ok", {})
                        st.success("LLM returned structured JSON. Merging with base template.")
        merged = merge_manual_fields(base, enriched)
        merged = merge_manual_fields(merged, manual)
        if include_meta:
            merged.setdefault("meta", {})
            merged["meta"]["tool_target"] = tool_key
            merged["meta"]["generated_at"] = datetime.utcnow().isoformat() + "Z"
        errors = validate_schema(tool_key, merged)
        if errors:
            st.warning("Schema validation issues detected:")
            for e in errors:
                st.write("- " + e)
            st.info("You can still download the JSON, but consider correcting the missing/invalid fields.")
        else:
            st.success("JSON validated against schema ✅")
        st.session_state["latest_json"] = merged

# Output area
st.markdown("### Generated JSON Prompt")
json_out = st.session_state.get("latest_json", None)
if json_out is None:
    st.info("No prompt generated yet — enter a request and click Generate JSON Prompt.")
else:
    rendered = pretty_json(json_out)
    st.code(rendered, language="json", line_numbers=True)
    filename = f"{slugify('prompt')}_{tool_key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    st.download_button("Download JSON", data=rendered, file_name=filename, mime="application/json")
    st.markdown("---")
    st.markdown("#### Validation Summary")
    v_errs = validate_schema(tool_key, json_out)
    if v_errs:
        st.error("Validation errors (see details above).")
    else:
        st.success("No validation errors. JSON conforms to schema.")

st.markdown("---")

# ---------------------- About Section ----------------------
st.markdown("---")
st.markdown("### 📌 About This App")
st.write("""
This app helps you convert **natural language requests** into perfectly structured JSON prompts
for AI tools such as Veo 3 (video), image generators, and code generation systems.
It works with or without an OpenAI API key:
- 🔹 Without API key: rule-based parser + manual overrides
- 🔹 With API key: enriched JSON generation powered by LLMs

#### 🚀 Why We Built This
Working with AI tools can be frustrating when:
- ❌ Prompts are too vague and give poor results
- ❌ Each tool needs a different JSON format
- ❌ Users waste time tweaking instead of creating
- ❌ Not everyone has access to LLM APIs

This app tackles those issues by giving you:
- ✅ A clear, consistent JSON structure for multiple AI tools
- ✅ Smart defaults + manual overrides for full control
- ✅ LLM-enhanced parsing when API keys are available
- ✅ A smooth entry point for both beginners and power users
""")



st.markdown("### Notes & Tips")
st.markdown("""
- To use OpenAI enrichment, supply your API key and enable 'Use LLM' on the sidebar. The app sends your description to OpenAI and tries to parse a JSON object back.
- If LLM output fails to be valid JSON, the app will show raw response for debugging.
- JSON Schema validation requires the `jsonschema` package. Install it with `pip install jsonschema`.
- This app is modular: update `SCHEMAS` to change validation rules or add new tool types.
""")
