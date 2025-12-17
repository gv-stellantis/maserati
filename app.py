import pandas as pd
import streamlit as st
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
from datetime import datetime

# ---------------- CONFIG ----------------
UTM_SOURCE = ["google", "facebook", "instagram", "linkedin", "newsletter", "crm", "partner"]
UTM_MEDIUM = ["cpc", "paid_social", "organic_social", "email", "referral", "display", "affiliate"]

TEMPLATES = {
    "brand_country_offer_yyyymm": "{brand}_{country}_{offer}_{yyyymm}",
}

# ---------------- HELPERS ----------------
_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def slugify(value: str, lower=True, sep="_") -> str:
    v = (value or "").strip()
    if lower:
        v = v.lower()
    v = _slug_re.sub(sep, v)
    v = v.strip(sep)
    v = re.sub(rf"{re.escape(sep)}+", sep, v)
    return v

def yyyymm_now():
    return datetime.now().strftime("%Y%m")

def merge_query_params(url: str, new_params: dict) -> str:
    p = urlparse(url.strip())
    if not p.scheme or not p.netloc:
        raise ValueError("URL non valido")
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q.update({k: v for k, v in new_params.items() if v})
    return urlunparse(p._replace(query=urlencode(q, doseq=True)))

# ---------------- UI ----------------
st.set_page_config(page_title="UTM Builder", layout="wide")
st.title("UTM Builder")

with st.sidebar:
    st.header("Impostazioni")
    lower = st.toggle("Forza lowercase", value=True)
    sep = st.selectbox("Separatore", ["_", "-"], index=0)

col1, col2, col3 = st.columns(3)
with col1:
    source = st.selectbox("utm_source", UTM_SOURCE)
with col2:
    medium = st.selectbox("utm_medium", UTM_MEDIUM)
with col3:
    template_key = st.selectbox("Template campaign", list(TEMPLATES.keys()))

st.subheader("Campi per template")
c1, c2, c3 = st.columns(3)
with c1: brand = st.text_input("brand")
with c2: country = st.text_input("country")
with c3: offer = st.text_input("offer")

st.subheader("Campi liberi")
c4, c5, c6 = st.columns(3)
with c4: campaign_manual = st.text_input("utm_campaign (opzionale)")
with c5: content = st.text_input("utm_content (opzionale)")
with c6: term = st.text_input("utm_term (opzionale)")

st.subheader("URL (uno per riga)")
urls_text = st.text_area("Incolla qui gli URL", height=160)

if st.button("Genera"):
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    rows = []

    for u in urls:
        try:
            if campaign_manual.strip():
                campaign = slugify(campaign_manual, lower=lower, sep=sep)
            else:
                fields = {
                    "brand": slugify(brand, lower=lower, sep=sep),
                    "country": slugify(country, lower=lower, sep=sep),
                    "offer": slugify(offer, lower=lower, sep=sep),
                    "yyyymm": yyyymm_now(),
                }
                campaign = slugify(TEMPLATES[template_key].format(**fields), lower=lower, sep=sep)

            params = {
                "utm_source": source,
                "utm_medium": medium,
                "utm_campaign": campaign,
                "utm_content": slugify(content, lower=lower, sep=sep) if content else "",
                "utm_term": slugify(term, lower=lower, sep=sep) if term else "",
            }

            out = merge_query_params(u, params)
            rows.append({"URL originale": u, "URL con UTM": out})

        except Exception as e:
            rows.append({"URL originale": u, "URL con UTM": f"ERRORE: {e}"})

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Scarica CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="utm_output.csv",
        mime="text/csv",
    )
