import pandas as pd
import streamlit as st
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
import unicodedata
from datetime import datetime

# ========= COMPLIANCE / LIMITS =========
# (I limiti numerici sono mostrati nella tabella "After" della guida; qui li applichiamo come validazione.)
LIMITS = {
    "sf_campaign_id": 15,   # Salesforce Campaign ID
    "wtl_source": 15,       # WTL Source (auto = SF Campaign ID)
    "utm_medium": 12,       # Medium (dropdown)
    "utm_source": 10,       # Source (dropdown)
    "campaign_name": 50,    # CampaignName / utm_campaign
    "utm_content": 20,      # Content
    "utm_term": 0,          # non consigliato in guida (lasciamo opzionale)
}

# ========= DROPDOWNS (Guide-aligned) =========
# utm_medium: evitare spazi (es. paid-search) :contentReference[oaicite:7]{index=7}
UTM_MEDIUM = [
    "paid-search",
    "display",
    "email",
    "paid-social",
    "social-owned",
    "qr-code",
]

# utm_source: esempi nella guida (newsletter, facebook, google, instagram, pinterest, linkedin, tiktok, youtube...) – dinamico :contentReference[oaicite:8]{index=8}
UTM_SOURCE = [
    "newsletter",
    "facebook",
    "google",
    "instagram",
    "pinterest",
    "linkedin",
    "tiktok",
    "youtube",
]

# UTM_CONTENT recommendation: phase + targeting type :contentReference[oaicite:9]{index=9}
PHASE = {"Awareness": "aw", "Consideration": "cns", "Conversion": "cnv"}
TARGETING = {"Prospecting": "prs", "Retargeting": "rtg", "Geolocal": "geo"}

# ========= HELPERS =========
_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def strip_accents(s: str) -> str:
    # "Don’t use accent marks" :contentReference[oaicite:10]{index=10}
    return "".join(
        c for c in unicodedata.normalize("NFKD", s or "")
        if not unicodedata.combining(c)
    )

def slugify(value: str, sep: str = "_") -> str:
    """
    Compliant cleaning:
    - trim
    - lowercase (no capitals) :contentReference[oaicite:11]{index=11}
    - no accents :contentReference[oaicite:12]{index=12}
    - replace spaces with sep, remove special chars :contentReference[oaicite:13]{index=13}
    """
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
    """
    Mantiene anche l'anchor #fragment (che resta alla fine) – in linea col tip :contentReference[oaicite:14]{index=14}
    """
    p = urlparse(url.strip())
    if not p.scheme or not p.netloc:
        raise ValueError("URL non valido (manca schema tipo https:// o dominio).")

    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q.update({k: v for k, v in new_params.items() if v})

    return urlunparse(p._replace(query=urlencode(q, doseq=True)))

# ========= UI =========
st.set_page_config(page_title="UTM Builder (Compliant 2024/25)", layout="wide")
st.title("UTM Builder (Compliant 2024/25)")

st.caption("Note: campaign name unico su SFDC/Adobe/Eloqua e wtl_source = Salesforce campaign code. "
           "No spazi, lowercase, no accenti, no special chars.")

with st.sidebar:
    st.header("Impostazioni")
    sep = st.selectbox("Separatore parole (consigliato _ o -)", ["_", "-"], index=0)

# ---- Salesforce block (new) ----
st.subheader("Salesforce (obbligatorio per tracking)")
sf_col1, sf_col2 = st.columns(2)
with sf_col1:
    sf_campaign_id_raw = st.text_input("Salesforce Campaign ID (15 caratteri)", placeholder="Es. 701D0000000v4Gf")
with sf_col2:
    st.text_input("WTL Source (auto = SF Campaign ID)", value=sf_campaign_id_raw.strip(), disabled=True)

# ---- Adobe / UTM ----
st.subheader("Adobe / UTM")
col1, col2, col3 = st.columns(3)
with col1:
    utm_medium = st.selectbox("utm_medium (valori ammessi)", UTM_MEDIUM)
with col2:
    utm_source = st.selectbox("utm_source", UTM_SOURCE)
with col3:
    yyyymm = st.text_input("Year_Month (YYYYMM)", value=yyyymm_now())

st.subheader("Campaign Name (unico per tutte le piattaforme)")
st.caption("La guida richiede: Salesforce campaign name = Adobe campaign name = Eloqua campaign name. "
           "Questo tool imposta anche campaignName = utm_campaign. ")

# Template semplice (manteniamo il tuo approccio) ma “campaign name” unico e con limiti.
c1, c2, c3, c4 = st.columns(4)
with c1: dept_region = st.text_input("Dept/Region (es. hq_crm)")
with c2: name = st.text_input("Campaign name (short)", placeholder="es. dstck")
with c3: activity = st.text_input("Activity type", placeholder="es. td")
with c4: country = st.text_input("Country (ISO 3166 o Multic)", placeholder="es. it")

c5, c6, c7 = st.columns(3)
with c5: language = st.text_input("Language (o Multil)", placeholder="es. it / multil")
with c6: model_engine = st.text_input("Model_Engine", placeholder="es. gr_ice / gh_bev")
with c7: comm_type = st.text_input("Type", placeholder="es. edm / nl / push")

campaign_manual = st.text_input("Override campaign name (opzionale)")

st.subheader("UTM_CONTENT (consigliato: phase + targeting + optional asset)")
cc1, cc2, cc3 = st.columns(3)
with cc1:
    phase = st.selectbox("Campaign phase", list(PHASE.keys()))
with cc2:
    targeting = st.selectbox("Targeting type", list(TARGETING.keys()))
with cc3:
    asset_ref = st.text_input("Asset ref (opzionale)", placeholder="es. crea1a / 300x250 / v2")

st.subheader("URL (uno per riga)")
urls_text = st.text_area("Incolla qui gli URL", height=160)

if st.button("Genera"):
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    rows = []

    for u in urls:
        try:
            # Salesforce ID + WTL source rules :contentReference[oaicite:15]{index=15}
            sf_campaign_id = sf_campaign_id_raw.strip()
            enforce_max_len("Salesforce Campaign ID", sf_campaign_id, LIMITS["sf_campaign_id"])
            wtl_source = sf_campaign_id
            enforce_max_len("WTL Source", wtl_source, LIMITS["wtl_source"])

            # source / medium limits + compliance cleaning
            utm_source_clean = slugify(utm_source, sep=sep)
            utm_medium_clean = slugify(utm_medium, sep=sep)  # già “safe”
            enforce_max_len("utm_source", utm_source_clean, LIMITS["utm_source"])
            enforce_max_len("utm_medium", utm_medium_clean, LIMITS["utm_medium"])

            # campaign name: unico su tutte le piattaforme :contentReference[oaicite:16]{index=16}
            if campaign_manual.strip():
                campaign_name = slugify(campaign_manual, sep=sep)
            else:
                parts = [
                    slugify(dept_region, sep=sep),
                    slugify(name, sep=sep),
                    slugify(activity, sep=sep),
                    slugify(country, sep=sep),
                    slugify(yyyymm, sep=sep),
                    slugify(language, sep=sep),
                    slugify(model_engine, sep=sep),
                    slugify(comm_type, sep=sep),
                ]
                parts = [p for p in parts if p]  # drop vuoti
                campaign_name = sep.join(parts)

            enforce_max_len("Campaign name", campaign_name, LIMITS["campaign_name"])

            # utm_content: phase + targeting recommended :contentReference[oaicite:17]{index=17}
            content_parts = [PHASE[phase], TARGETING[targeting]]
            if asset_ref.strip():
                content_parts.append(slugify(asset_ref, sep=sep))
            utm_content = sep.join(content_parts)
            enforce_max_len("utm_content", utm_content, LIMITS["utm_content"])

            # Build params:
            # - Adobe: utm_source/medium/campaign/content
            # - Salesforce: campaignName + wtl_source
            params = {
                "campaignName": campaign_name,   # Salesforce
                "wtl_source": wtl_source,        # Salesforce (persist session)
                "utm_source": utm_source_clean,  # Adobe
                "utm_medium": utm_medium_clean,  # Adobe
                "utm_campaign": campaign_name,   # Adobe (same as SFDC)
                "utm_content": utm_content,      # Adobe
                # utm_term è sconsigliato (resta fuori di default)
            }

            out = merge_query_params(u, params)
            rows.append({"URL originale": u, "URL con tracking": out})

        except Exception as e:
            rows.append({"URL originale": u, "URL con tracking": f"ERRORE: {e}"})

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Scarica CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="utm_output.csv",
        mime="text/csv",
    )

