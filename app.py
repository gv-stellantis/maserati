import pandas as pd
import streamlit as st
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
import unicodedata
from datetime import datetime

# ========= LIMITS (da guida) =========
LIMITS = {
    "sf_campaign_id": 15,
    "wtl_source": 15,
    "utm_medium": 12,
    "utm_source": 10,
    "campaign_name": 50,
    "utm_content": 20,
}

# ========= MODALITÀ (CRM / Media / Social / Dealer) =========
# Decide quali parametri includere (e quali campi mostrare).
CHANNELS = {
    "CRM": {
        "include": ["campaignName", "wtl_source"],  # tipico CRM tracking
        "allow_utm": False,
    },
    "Media": {
        "include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"],
        "allow_utm": True,
    },
    "Social": {
        "include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"],
        "allow_utm": True,
    },
    "Dealer": {
        "include": ["campaignName", "wtl_source", "utm_source", "utm_medium", "utm_campaign", "utm_content"],
        "allow_utm": True,
    },
}

# ========= DROPDOWNS =========
UTM_MEDIUM = ["paid-search", "display", "email", "paid-social", "social-owned", "qr-code"]
UTM_SOURCE = ["newsletter", "facebook", "google", "instagram", "pinterest", "linkedin", "tiktok", "youtube"]

PHASE = {"Awareness": "aw", "Consideration": "cns", "Conversion": "cnv"}
TARGETING = {"Prospecting": "prs", "Retargeting": "rtg", "Geolocal": "geo"}

# Modelli e motorizzazioni BLOCCATI (esempi: sostituisci con le tue liste ufficiali)
MODELS_ENGINES = {
    "grecale": ["mhev", "bev", "phev"],
    "granturismo": ["bev", "ice"],
    "ghibli": ["ice", "mhev"],
    "levante": ["ice", "mhev"],
    "mc20": ["ice"],
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
        raise ValueError(f"{label} supera il limite ({len(value)}/{max_len}).")
    return value

def yyyymm_now() -> str:
    return datetime.now().strftime("%Y%m")

def merge_query_params(url: str, new_params: dict) -> str:
    p = urlparse(url.strip())
    if not p.scheme or not p.netloc:
        raise ValueError("URL non valido (usa https://...)")
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q.update({k: v for k, v in new_params.items() if v})
    return urlunparse(p._replace(query=urlencode(q, doseq=True)))

# ========= UI =========
st.set_page_config(page_title="UTM Builder (Compliant)", layout="wide")
st.title("UTM Builder (Compliant)")

with st.sidebar:
    st.header("Impostazioni")
    sep = st.selectbox("Separatore", ["_", "-"], index=0)
    channel = st.selectbox("Tipo attività", list(CHANNELS.keys()), index=1)  # default Media

st.info(
    f"Modalità selezionata: **{channel}**. "
    "Il tool includerà automaticamente solo i parametri previsti per questo caso."
)

# ---- Salesforce block ----
st.subheader("Salesforce (tracking base)")
sf_campaign_id_raw = st.text_input("Salesforce Campaign ID (15 caratteri)", placeholder="Es. 701D0000000v4Gf")
wtl_source_value = sf_campaign_id_raw.strip()
st.text_input("WTL Source (auto = SF Campaign ID)", value=wtl_source_value, disabled=True)

# ---- Modello / Motorizzazione (dropdown bloccati) ----
st.subheader("Veicolo")
m1, m2 = st.columns(2)
with m1:
    model = st.selectbox("Modello", sorted(MODELS_ENGINES.keys()))
with m2:
    engine = st.selectbox("Motorizzazione", MODELS_ENGINES.get(model, []))

# ---- Adobe/UTM (solo se la modalità lo permette) ----
allow_utm = CHANNELS[channel]["allow_utm"]

if allow_utm:
    st.subheader("Adobe / UTM")
    c1, c2, c3 = st.columns(3)
    with c1:
        utm_medium = st.selectbox("utm_medium", UTM_MEDIUM)
    with c2:
        utm_source = st.selectbox("utm_source", UTM_SOURCE)
    with c3:
        yyyymm = st.text_input("Year_Month (YYYYMM)", value=yyyymm_now())
else:
    # valori placeholder (non usati)
    utm_medium, utm_source, yyyymm = "", "", yyyymm_now()

# ---- Campaign Name (unico) ----
st.subheader("Campaign Name (unico cross-platform)")
st.caption("Verrà usato sia come campaignName (SF) sia come utm_campaign (Adobe), quando previsto.")

# componenti “guidati” ma con campi controllati dove serve
a1, a2, a3, a4 = st.columns(4)
with a1: dept_region = st.text_input("Dept/Region", placeholder="es. hq_crm")
with a2: camp_short = st.text_input("Campaign short name", placeholder="es. dstck")
with a3: activity = st.text_input("Activity type", placeholder="es. td")
with a4: country = st.text_input("Country", placeholder="es. it")

b1, b2 = st.columns(2)
with b1: language = st.text_input("Language", placeholder="it / multil")
with b2: comm_type = st.text_input("Communication type", placeholder="edm / nl / push")

campaign_manual = st.text_input("Override campaign name (opzionale)")

# ---- UTM_CONTENT (solo se UTM) ----
if allow_utm:
    st.subheader("UTM_CONTENT (phase + targeting + opzionale asset)")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        phase = st.selectbox("Campaign phase", list(PHASE.keys()))
    with cc2:
        targeting = st.selectbox("Targeting type", list(TARGETING.keys()))
    with cc3:
        asset_ref = st.text_input("Asset ref (opzionale)", placeholder="es. crea1a / 300x250 / v2")
else:
    phase, targeting, asset_ref = "Awareness", "Prospecting", ""

# ---- URL input ----
st.subheader("URL (uno per riga)")
urls_text = st.text_area("Incolla qui gli URL", height=160)

# ========= GENERATION =========
if st.button("Genera"):
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    rows = []

    for u in urls:
        try:
            # Salesforce ID + WTL source
            sf_campaign_id = sf_campaign_id_raw.strip()
            enforce_max_len("Salesforce Campaign ID", sf_campaign_id, LIMITS["sf_campaign_id"])
            wtl_source = sf_campaign_id
            enforce_max_len("WTL Source", wtl_source, LIMITS["wtl_source"])

            # Campaign name (unico)
            if campaign_manual.strip():
                campaign_name = slugify(campaign_manual, sep=sep)
            else:
                parts = [
                    slugify(dept_region, sep=sep),
                    slugify(camp_short, sep=sep),
                    slugify(activity, sep=sep),
                    slugify(country, sep=sep),
                    slugify(yyyymm, sep=sep),
                    slugify(language, sep=sep),
                    slugify(model, sep=sep),
                    slugify(engine, sep=sep),
                    slugify(comm_type, sep=sep),
                ]
                parts = [p for p in parts if p]
                campaign_name = sep.join(parts)

            enforce_max_len("Campaign name", campaign_name, LIMITS["campaign_name"])

            # Base params (sempre)
            params_all = {
                "campaignName": campaign_name,
                "wtl_source": wtl_source,
            }

            # UTM params (solo se previsto per la modalità)
            if allow_utm:
                utm_source_clean = slugify(utm_source, sep=sep)
                utm_medium_clean = slugify(utm_medium, sep=sep)
                enforce_max_len("utm_source", utm_source_clean, LIMITS["utm_source"])
                enforce_max_len("utm_medium", utm_medium_clean, LIMITS["utm_medium"])

                content_parts = [PHASE[phase], TARGETING[targeting]]
                if asset_ref.strip():
                    content_parts.append(slugify(asset_ref, sep=sep))
                utm_content = sep.join(content_parts)
                enforce_max_len("utm_content", utm_content, LIMITS["utm_content"])

                params_all.update({
                    "utm_source": utm_source_clean,
                    "utm_medium": utm_medium_clean,
                    "utm_campaign": campaign_name,   # stesso valore di campaignName
                    "utm_content": utm_content,
                })

            # Filtra SOLO i parametri previsti per la modalità
            include_keys = set(CHANNELS[channel]["include"])
            params = {k: v for k, v in params_all.items() if k in include_keys}

            out = merge_query_params(u, params)
            rows.append({"Tipo": channel, "URL originale": u, "URL con tracking": out})

        except Exception as e:
            rows.append({"Tipo": channel, "URL originale": u, "URL con tracking": f"ERRORE: {e}"})

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Scarica CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="utm_output.csv",
        mime="text/csv",
    )
