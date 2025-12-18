import pandas as pd
import streamlit as st
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
import unicodedata
from datetime import datetime

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

MODES = {
    "CRM": {"include": ["campaignName", "wtl_source"], "allow_media_builder": False},
    "Media": {"include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"], "allow_media_builder": True},
    "Social": {"include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"], "allow_media_builder": True},
    "Dealer": {"include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"], "allow_media_builder": True},
}

# UTM-only (kept separate)
UTM_MEDIUM = ["paid-search", "display", "email", "paid-social", "social-owned", "qr-code"]
UTM_SOURCE = [
    "edm",
    "nl",
    "adalliance",
    "adbalancer",
    "amobee",
    "apex",
    "askaprice",
    "axelspring",
    "autovia",
    "baidu",
    "bing",
    "caraffinit",
    "carkeys",
    "clearchann",
    "condenast",
    "criteo",
    "tiktok",
    "drivek",
    "dupontregi",
    "esquire",
    "facebook",
    "forbes",
    "gentleman",
    "google",
    "goop",
    "gq",
    "handelsbla",
    "hearstauto",
    "howtospend",
    "iflytek",
    "il",
    "impactradi",
    "innovid",
    "instagram",
    "internazio",
    "iodonna",
    "iqmedia",
    "jiemian",
    "kargo",
    "kerv",
    "leadscale",
    "lefigaro",
    "linkedin",
    "livesystem",
    "manzoni",
    "meta",
    "newyorktim",
    "northwarre",
    "ogury",
    "precision",
    "quattroruo",
    "red",
    "regit",
    "sabato",
    "strive",
    "taboola",
    "teads",
    "thegoodlif",
    "thetradede",
    "topgear",
    "twitter",
    "uim",
    "vanityfair",
    "various",
    "vogue",
    "wallstreet",
    "wangshangc",
    "wechat",
    "weibo",
    "whatcar",
    "wirtschaft",
    "yahoo",
    "yhouse",
    "youtube",
    "zeitmagazi",
    "screenondemand",
    "amazon",
    "outbrain",
    "sms",
    "snapchat",
    "elle",
    "offline-platform",
    "xing",
    "tradedoubler",
    "whatsapp",
    "meetdeal",
    "hbz",
    "sz",
    "seedtag"
]


# Media details (not UTM)
TYPE_MEDIUM = ["Display", "Video", "Paid Search", "Paid Social"]

PHASE = {"Awareness": "aw", "Consideration": "cns", "Conversion": "cnv"}

# Model label -> token (exact output)
# First entry "" to make the first option empty
MODEL_OPTIONS = [
    ("", ""),  # empty first option
    ("Multi Model", "multim"),
    ("Grecale", "grecale"),
    ("GranTurismo", "granturismo"),
    ("Ghibli", "ghibli"),
    ("Levante", "levante"),
    ("MC20", "mc20"),
    ("MC Pura", "mcpura"),
    ("MC Pura Cielo", "mcpura-cielo"),
]

# Engine label -> token (ONLY ICE / BEV) with empty first option
ENGINE_OPTIONS = [
    ("", ""),  # empty first option
    ("ICE", "ice"),
    ("BEV", "bev"),
]


FORMAT_BY_MEDIUM = {
    "Display": ["Standard", "Native", "Skin", "Interstitial"],
    "Video": ["Non-Skippable", "Skippable", "Bumper", "Short", "In-feed", "Masthead"],
    "Paid Search": ["Demand Gen", "Search Ad", "Pmax"],
    "Paid Social": ["Static Feed Ad", "Video Feed Ad", "Sponsered Content Ad", "Stories", "Reels", "Inmail"],
}

AUDIENCE_BY_MEDIUM = {
    "Display": ["Prospecting", "Retargeting", "Look a Like"],
    "Video": ["Prospecting", "Retargeting", "Look a Like"],
    "Paid Search": ["Prospecting", "Retargeting", "Look a Like", "Mix"],
    "Paid Social": ["Prospecting", "Retargeting", "Look a Like", "Advantage plus audience"],
}

_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))

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

def merge_query_params_ordered(url: str, ordered_params: list[tuple[str, str]]) -> str:
    """
    Keeps query param order:
    - preserves any existing params not overwritten
    - appends our params in the exact order given by ordered_params
    """
    p = urlparse(url.strip())
    if not p.scheme or not p.netloc:
        raise ValueError("Invalid URL (use https://...)")

    existing = parse_qsl(p.query, keep_blank_values=True)
    keys_to_set = {k for (k, v) in ordered_params if v}

    # keep existing params except the ones we will set (to avoid duplicates)
    kept = [(k, v) for (k, v) in existing if k not in keys_to_set]

    # append new params in the requested order (only if value is not empty)
    appended = [(k, v) for (k, v) in ordered_params if v]

    new_query = urlencode(kept + appended, doseq=True)
    return urlunparse(p._replace(query=new_query))


st.set_page_config(page_title="UTM Builder (Updated: Dic-2025)", layout="wide")
st.title("UTM Builder (Updated: Dic-2025)")

with st.sidebar:
    st.header("Settings")
    sep = st.selectbox("Word separator", ["_", "-"], index=0)
    mode = st.selectbox("Mode", list(MODES.keys()), index=1)

allow_media_builder = MODES[mode]["allow_media_builder"]
st.info(f"Current mode: **{mode}**")

st.subheader("Salesforce ID")
sf_campaign_id_raw = st.text_input("Salesforce Campaign ID* (15 chars)", placeholder="e.g. 701D0000000v4Gf")
wtl_source_value = sf_campaign_id_raw.strip()
st.text_input("WTL Source (auto = SF Campaign ID)", value=wtl_source_value, disabled=True)

# ---- Vehicle (first option empty) ----
st.subheader("Vehicle")
colA, colB = st.columns(2)

model_map = dict(MODEL_OPTIONS)
engine_map = dict(ENGINE_OPTIONS)

with colA:
    model_label = st.selectbox("Model", [x[0] for x in MODEL_OPTIONS], index=0)
    model_token = model_map.get(model_label, "")

with colB:
    engine_label = st.selectbox(
        "Engine",
        [lbl for (lbl, _) in ENGINE_OPTIONS],
        index=0
    )
    engine_token = engine_map.get(engine_label, "")


# ---- UTM params (separate) ----
if allow_media_builder:
    st.subheader("UTM parameters")
    u1, u2 = st.columns(2)
    with u1:
        utm_source = st.selectbox("utm_source", UTM_SOURCE)
    with u2:
        utm_medium = st.selectbox("utm_medium*", UTM_MEDIUM)
else:
    utm_source = ""
    utm_medium = ""

# ---- Media details (optional, first option empty) ----
if allow_media_builder:
    st.subheader("Media details (optional)")
    m1, m2, m3 = st.columns(3)
    with m1:
        type_medium = st.selectbox("Type-medium", TYPE_MEDIUM)

    format_options = [""] + FORMAT_BY_MEDIUM.get(type_medium, [])
    audience_options = [""] + AUDIENCE_BY_MEDIUM.get(type_medium, [])

    with m2:
        format_val = st.selectbox("Format (optional)", format_options, index=0)
    with m3:
        audience_val = st.selectbox("Audience (optional)", audience_options, index=0)
else:
    type_medium = ""
    format_val = ""
    audience_val = ""

st.subheader("Campaign Name *")
st.caption("Required – used to generate utm_campaign")
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

st.subheader("URLs (one per line)")
urls_text = st.text_area("Paste URLs here", height=160)

if st.button("Generate"):
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    rows = []

    # REQUIRED:
    if not sf_campaign_id_raw.strip():
        st.error("Salesforce Campaign ID * is required (used for campaignName and wtl_source).")
        st.stop()

    if allow_media_builder and not utm_medium:
        st.error("utm_medium * is required in this mode.")
        st.stop()

    if not urls:
        st.error("Please paste at least one URL.")
        st.stop()

    for u in urls:
        try:
            sf_campaign_id = sf_campaign_id_raw.strip()
            enforce_max_len("Salesforce Campaign ID", sf_campaign_id, LIMITS["sf_campaign_id"])

            # ---- FIX 1: campaignName is Salesforce ID ----
            campaignName_param = sf_campaign_id

            # ---- FIX 2: wtl_source is Salesforce ID ----
            wtl_source_param = sf_campaign_id

            # ---- Build utm_campaign from concatenated fields ----
            # (this is what you previously called campaign_name)
            if campaign_manual.strip():
                utm_campaign_val = slugify(campaign_manual, sep=sep)
            else:
                parts = [
                    slugify(region_dept, sep=sep),
                    slugify(camp_short, sep=sep),
                    slugify(activity, sep=sep),
                    slugify(country, sep=sep),
                    slugify(yyyymm, sep=sep),
                    slugify(language, sep=sep),
                ]

                # Vehicle tokens (optional, only if selected)
                if model_token:
                    parts.append(model_token)      # exact token (multim, mcpura, mcpura-cielo)
                if engine_token:
                    parts.append(engine_token)     # ice / bev (or empty)

                # Media details (optional)
                if allow_media_builder:
                    if format_val:
                        fmt = slugify(format_val, sep=sep)
                        enforce_max_len("Format", fmt, LIMITS["format"])
                        parts.append(fmt)
                    if audience_val:
                        aud = slugify(audience_val, sep=sep)
                        enforce_max_len("Audience", aud, LIMITS["audience"])
                        parts.append(aud)

                parts = [p for p in parts if p and p != "n_a"]
                utm_campaign_val = sep.join(parts)

            # utm_campaign REQUIRED in media modes
            if allow_media_builder and not utm_campaign_val.strip():
                raise ValueError("utm_campaign * is required (fill campaign fields or use Override campaign name).")

            enforce_max_len("utm_campaign", utm_campaign_val, LIMITS["campaign_name"])

            # utm_content only if available
            utm_content_val = slugify(PHASE[phase], sep=sep) if phase else ""
            if utm_content_val:
                enforce_max_len("utm_content", utm_content_val, LIMITS["utm_content"])

            # ---- UTM params ----
            utm_medium_clean = slugify(utm_medium, sep=sep) if allow_media_builder else ""
            if utm_medium_clean:
                enforce_max_len("utm_medium", utm_medium_clean, LIMITS["utm_medium"])

            utm_source_clean = slugify(utm_source, sep=sep) if (allow_media_builder and utm_source) else ""
            if utm_source_clean:
                enforce_max_len("utm_source", utm_source_clean, LIMITS["utm_source"])

            # ---- Build ordered param list (EXACT ORDER REQUIRED) ----
            ordered_params = [
                ("campaignName", campaignName_param),
                ("wtl_source", wtl_source_param),
                ("utm_medium", utm_medium_clean if allow_media_builder else ""),
                ("utm_source", utm_source_clean if allow_media_builder else ""),
                ("utm_campaign", utm_campaign_val if allow_media_builder else ""),
                ("utm_content", utm_content_val if (allow_media_builder and utm_content_val) else ""),
            ]

            # filter by mode include list
            include_keys = set(MODES[mode]["include"])
            ordered_params = [(k, v) for (k, v) in ordered_params if k in include_keys]

            out = merge_query_params_ordered(u, ordered_params)

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
