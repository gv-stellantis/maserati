import pandas as pd
import streamlit as st
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
import unicodedata
from datetime import datetime

# ========= LIMITS (from guide) =========
LIMITS = {
    "sf_campaign_id": 15,
    "wtl_source": 15,
    "utm_medium": 12,
    "utm_source": 10,
    "campaign_name": 50,
    "utm_content": 20,
    "format": 25,
    "audience": 25,
}

# ========= MODES (CRM / Media / Social / Dealer) =========
MODES = {
    "CRM": {
        "include": ["campaignName", "wtl_source"],
        "allow_media_builder": False,
    },
    "Media": {
        "include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"],
        "allow_media_builder": True,
    },
    "Social": {
        "include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"],
        "allow_media_builder": True,
    },
    "Dealer": {
        "include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"],
        "allow_media_builder": True,
    },
}

# ========= DROPDOWNS =========
# utm_medium (no spaces)
UTM_MEDIUM = ["paid-search", "display", "email", "paid-social", "social-owned", "qr-code"]

# Type-medium (media channel for format/audience)
TYPE_MEDIUM = ["Display", "Video", "Paid Search", "Paid Social"]

# Type-source (also used as utm_source)
UTM_SOURCE = ["newsletter", "facebook", "google", "instagram", "pinterest", "linkedin", "tiktok", "youtube"]

# Minimal utm_content
PHASE = {"Awareness": "aw", "Consideration": "cns", "Conversion": "cnv"}

# ========= MODELS / ENGINES (locked tokens) =========
# Display label -> token (exact output)
MODEL_OPTIONS = [
    ("Grecale", "grecale"),
    ("GranTurismo", "granturismo"),
    ("Ghibli", "ghibli"),
    ("Levante", "levante"),
    ("MC20", "mc20"),
    ("MC Pura", "mcpura"),
    ("MC Pura Cielo", "mcpura-cielo"),
]

# Model token -> list of engine tokens
# NOTE: replaced MHEV with BEV as requested
MODEL_ENGINES = {
    "grecale": ["bev", "phev"],
    "granturismo": ["bev", "ice"],
    "ghibli": ["ice", "bev"],   # was mhev -> bev
    "levante": ["ice", "bev"],  # was mhev -> bev
    "mc20": ["ice"],
    "mcpura": ["ice"],
    "mcpura-cielo": ["ice"],
}

# ========= FORMAT (Format Reviewed) =========
FORMAT_BY_MEDIUM = {
    "Display": ["Standard", "Native", "Skin", "Interstitial"],
    "Video": ["Non-Skippable", "Skippable", "Bumper", "Short", "In-feed", "Masthead"],
    "Paid Search": ["Demand Gen", "Search Ad", "Pmax"],
    "Paid Social": ["Static Feed Ad", "Video Feed Ad", "Sponsered Content Ad", "Stories", "Reels", "Inmail"],
}

# ========= AUDIENCE (Targeting) =========
AUDIENCE_BY_MEDIUM = {
    "Display": ["Prospecting", "Retargeting", "Look a Like"],
    "Video": ["Prospecting", "Retargeting", "Look a Like"],
    "Paid Search": ["Prospecting", "Retargeting", "Look a Like", "Mix"],
    "Paid Social": ["Prospecting", "Retargeting", "Look a Like", "Advantage plus audience"],
}

# ========= HELPERS =========
_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s or "")
        if not unicodedata.combining(c)
    )

def slugify(value: str, sep: str = "_") -> str:
    v = (value or "").strip()
    v = strip_accents(v).lower()
    v = _slug_re.sub(sep, v)
    v = v.strip(sep)
    v = re.sub(rf"{re.escape(sep)}+", sep, v)
    return v

def enforce_max_len(label: str, value: str, max_len: int) -> str:
    if max_len and len(value) > max_len:
        raise ValueError(f"{label} exceeds the limit ({len(value)}/{max_len}).")
    return value

def yyyymm_now() -> str:
    return datetime.now().strftime("%Y%m")

def merge_query_params(url: str, new_params: dict) -> str:
    p = urlparse(url.strip())
    if not p.scheme or not p.netloc:
        raise ValueError("Invalid URL (use https://...)")
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q.update({k: v for k, v in new_params.items() if v})
    return urlunparse(p._replace(query=urlencode(q, doseq=True)))

# ========= UI =========
st.set_page_config(page_title="UTM Builder (Compliant + Format/Audience)", layout="wide")
st.title("UTM Builder (Compliant + Format/Audience)")

with st.sidebar:
    st.header("Settings")
    sep = st.selectbox("Word separator", ["_", "-"], index=0)
    mode = st.selectbox("Mode", list(MODES.keys()), index=1)  # Media default

allow_media_builder = MODES[mode]["allow_media_builder"]
st.info(f"Current mode: **{mode}**")

# ---- Salesforce block ----
st.subheader("Salesforce (base tracking)")
sf_campaign_id_raw = st.text_input("Salesforce Campaign ID (15 chars)", placeholder="e.g. 701D0000000v4Gf")
wtl_source_value = sf_campaign_id_raw.strip()
st.text_input("WTL Source (auto = SF Campaign ID)", value=wtl_source_value, disabled=True)

# ---- Vehicle (locked) ----
st.subheader("Vehicle")
colA, colB = st.columns(2)
with colA:
    model_label = st.selectbox("Model", [x[0] for x in MODEL_OPTIONS])
    model_token = dict(MODEL_OPTIONS)[model_label]  # exact output token
with colB:
    engine_token = st.selectbox("Engine", MODEL_ENGINES.get(model_token, []))

# ---- Media Builder fields (only if enabled) ----
if allow_media_builder:
    st.subheader("Media fields (guided)")

    c1, c2, c3 = st.columns(3)
    with c1:
        type_medium = st.selectbox("Type-medium", TYPE_MEDIUM)
    with c2:
        type_source = st.selectbox("Type-source", UTM_SOURCE)  # also utm_source
    with c3:
        utm_medium = st.selectbox("utm_medium", UTM_MEDIUM)

    f1, f2 = st.columns(2)
    with f1:
        format_val = st.selectbox("Format", FORMAT_BY_MEDIUM.get(type_medium, ["N/A"]))
    with f2:
        audience_val = st.selectbox("Audience", AUDIENCE_BY_MEDIUM.get(type_medium, ["N/A"]))
else:
    type_medium = ""
    type_source = ""
    utm_medium = ""
    format_val = ""
    audience_val = ""

# ---- Campaign name inputs ----
st.subheader("Campaign Name (unique cross-platform)")

a1, a2, a3, a4 = st.columns(4)
with a1: region_dept = st.text_input("Region/Dept", placeholder="e.g. hq")
with a2: camp_short = st.text_input("Name", placeholder="e.g. dstck")
with a3: activity = st.text_input("Activity type (objective)", placeholder="e.g. td")
with a4: country = st.text_input("Country", placeholder="e.g. it")

b1, b2 = st.columns(2)
with b1: language = st.text_input("Language", placeholder="it / multil")
with b2: yyyymm = st.text_input("Year_Month (YYYYMM)", value=yyyymm_now())

if allow_media_builder:
    st.subheader("UTM_CONTENT (minimal)")
    phase = st.selectbox("Campaign phase", list(PHASE.keys()))
else:
    phase = "Awareness"

campaign_manual = st.text_input("Override campaign name (optional)")

# ---- URLs ----
st.subheader("URLs (one per line)")
urls_text = st.text_area("Paste URLs here", height=160)

# ========= GENERATION =========
if st.button("Generate"):
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    rows = []

    for u in urls:
        try:
            # Salesforce ID + WTL source
            sf_campaign_id = sf_campaign_id_raw.strip()
            enforce_max_len("Salesforce Campaign ID", sf_campaign_id, LIMITS["sf_campaign_id"])
            wtl_source = sf_campaign_id
            enforce_max_len("WTL Source", wtl_source, LIMITS["wtl_source"])

            # Build campaign name
            if campaign_manual.strip():
                campaign_name = slugify(campaign_manual, sep=sep)
            else:
                parts = [
                    slugify(region_dept, sep=sep),
                    slugify(camp_short, sep=sep),
                    slugify(activity, sep=sep),
                    slugify(country, sep=sep),
                    slugify(yyyymm, sep=sep),
                    slugify(language, sep=sep),

                    # IMPORTANT: model token must be exact (mcpura / mcpura-cielo), so we do not slugify it
                    model_token,
                    # engine token is already controlled, keep as-is
                    engine_token,
                ]

                # ---- Media enrichment: AFTER type-source add format + audience ----
                if allow_media_builder:
                    fmt = slugify(format_val, sep=sep)
                    aud = slugify(audience_val, sep=sep)
                    enforce_max_len("Format", fmt, LIMITS["format"])
                    enforce_max_len("Audience", aud, LIMITS["audience"])

                    parts.extend([
                        slugify(type_medium, sep=sep),
                        slugify(type_source, sep=sep),  # Type-source
                        fmt,                             # Format (after type-source)
                        aud,                             # Audience (after type-source)
                    ])

                parts = [p for p in parts if p and p != "n_a"]
                campaign_name = sep.join(parts)

            enforce_max_len("Campaign name", campaign_name, LIMITS["campaign_name"])

            # Minimal utm_content
            utm_content = slugify(PHASE[phase], sep=sep)
            enforce_max_len("utm_content", utm_content, LIMITS["utm_content"])

            # Params base (always)
            params_all = {
                "campaignName": campaign_name,
                "wtl_source": wtl_source,
            }

            # UTM params only if media modes
            if allow_media_builder:
                utm_source_clean = slugify(type_source, sep=sep)  # type-source = utm_source
                utm_medium_clean = slugify(utm_medium, sep=sep)

                enforce_max_len("utm_source", utm_source_clean, LIMITS["utm_source"])
                enforce_max_len("utm_medium", utm_medium_clean, LIMITS["utm_medium"])

                params_all.update({
                    "utm_source": utm_source_clean,
                    "utm_medium": utm_medium_clean,
                    "utm_campaign": campaign_name,
                    "utm_content": utm_content,
                })

            # Filter by mode
            include_keys = set(MODES[mode]["include"])
            params = {k: v for k, v in params_all.items() if k in include_keys}

            out = merge_query_params(u, params)
            rows.append({"Mode": mode, "Original URL": u, "Tagged URL": out})

        except Exception as e:
            rows.append({"Mode": mode, "Original URL": u, "Tagged URL": f"ERROR: {e}"})

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="utm_output.csv",
        mime="text/csv",
    )
