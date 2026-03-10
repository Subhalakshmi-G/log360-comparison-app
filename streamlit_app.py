import os, sys, base64
from datetime import datetime
from pathlib import Path
import streamlit as st
import yaml
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, os.path.dirname(__file__))
from scrapers.gartner import get_rating, should_include_gartner

st.set_page_config(page_title="Log360 Comparison Generator", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
.stApp{background-color:#FAFBFC}
.main-header{background:linear-gradient(135deg,#1A1A2E,#C8102E);padding:2rem 2.5rem;border-radius:12px;margin-bottom:2rem;color:white}
.main-header h1{color:white!important;margin:0;font-size:2rem}.main-header p{color:rgba(255,255,255,.85);margin:.5rem 0 0}
.metric-card{background:white;border-radius:10px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,.08);border-left:4px solid #C8102E;text-align:center}
.metric-card .value{font-size:2rem;font-weight:700;color:#C8102E}.metric-card .label{font-size:.85rem;color:#555}
.gartner-box{background:#FFFBEB;border:1px solid #FFB400;border-radius:10px;padding:1.2rem;margin:.5rem 0}
.download-btn{display:inline-block;background:#C8102E;color:white!important;padding:.75rem 2rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:1rem;margin:.5rem .5rem .5rem 0}
.download-btn:hover{background:#A00D24;color:white!important}
</style>""", unsafe_allow_html=True)

def load_yaml(path):
    with open(path) as f: return yaml.safe_load(f)

def get_competitor_keys():
    return list(load_yaml("config/products.yaml").get("competitors",{}).keys())

def get_competitor_display_name(key):
    return load_yaml("config/products.yaml")["competitors"].get(key,{}).get("name",key)

def count_advantages(data):
    lw=cw=t=0
    for cat in data.get("feature_comparison",[]):
        for f in cat.get("features",[]):
            l,c=f["log360"]["supported"],f["competitor"]["supported"]
            if l and not c: lw+=1
            elif c and not l: cw+=1
            else: t+=1
    return {"log360":lw,"competitor":cw,"ties":t}

def render_stars(rating):
    full=int(rating); half=1 if rating-full>=0.25 else 0; empty=5-full-half
    return "★"*full+("★" if half else "")+"☆"*empty

def generate_pdf(template_name, competitor_key):
    from weasyprint import HTML as WHTML
    tokens=load_yaml("config/design_tokens.yaml"); data=load_yaml(f"data/comparisons/{competitor_key}.yaml")
    products=load_yaml("config/products.yaml"); comp_cfg=products["competitors"][competitor_key]; l360_cfg=products["log360"]
    ig=should_include_gartner("log360",competitor_key); g_l360=g_comp=None
    if ig:
        g_l360=get_rating("log360",l360_cfg.get("gartner_product_url"))
        g_comp=get_rating(competitor_key,comp_cfg.get("gartner_product_url"))
    total=sum(len(c["features"]) for c in data.get("feature_comparison",[])); l360_sup=sum(1 for c in data["feature_comparison"] for f in c["features"] if f["log360"]["supported"]); comp_sup=sum(1 for c in data["feature_comparison"] for f in c["features"] if f["competitor"]["supported"])
    ctx={"tokens":tokens,"data":data,"log360":l360_cfg,"competitor":comp_cfg,"advantages":count_advantages(data),"include_gartner":ig,"gartner_log360":g_l360,"gartner_competitor":g_comp,"generated_date":datetime.now().strftime("%B %Y"),"total_features":total,"log360_supported":l360_sup,"comp_supported":comp_sup}
    env=Environment(loader=FileSystemLoader("templates")); html_str=env.get_template(template_name).render(**ctx)
    return WHTML(string=html_str,base_url=str(Path("templates").resolve())).write_pdf()

def create_download_link(pdf_bytes, filename):
    b64=base64.b64encode(pdf_bytes).decode()
    return f'<a class="download-btn" href="data:application/pdf;base64,{b64}" download="{filename}">📥 Download {filename}</a>'

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    available_keys=[k for k in get_competitor_keys() if os.path.exists(f"data/comparisons/{k}.yaml")]
    if not available_keys: st.error("No comparison data files found"); st.stop()
    selected=st.selectbox("Select Competitor",available_keys,format_func=get_competitor_display_name)
    st.markdown("---"); st.markdown("### 📊 Gartner Settings")
    include_g=should_include_gartner("log360",selected)
    st.metric("Include Gartner?","✅ Yes" if include_g else "❌ No")
    st.markdown("---"); st.caption(f"Generated: {datetime.now().strftime('%B %d, %Y')}")

st.markdown('<div class="main-header"><h1>🛡️ Log360 Competitive Intelligence Generator</h1><p>Generate branded comparison documents and battlecards with Gartner Peer Insights data</p></div>',unsafe_allow_html=True)

data=load_yaml(f"data/comparisons/{selected}.yaml"); products=load_yaml("config/products.yaml")
comp_cfg=products["competitors"][selected]; l360_cfg=products["log360"]; advantages=count_advantages(data)
g_l360=g_comp=None
if include_g:
    g_l360=get_rating("log360",l360_cfg.get("gartner_product_url"))
    g_comp=get_rating(selected,comp_cfg.get("gartner_product_url"))

c1,c2,c3,c4=st.columns(4)
with c1: st.markdown(f'<div class="metric-card"><div class="value">{advantages["log360"]}</div><div class="label">Log360 Advantages</div></div>',unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="value">{advantages["competitor"]}</div><div class="label">{comp_cfg["short_name"]} Advantages</div></div>',unsafe_allow_html=True)
with c3:
    total_f=sum(len(c["features"]) for c in data["feature_comparison"]); l360_f=sum(1 for c in data["feature_comparison"] for f in c["features"] if f["log360"]["supported"])
    st.markdown(f'<div class="metric-card"><div class="value">{l360_f}/{total_f}</div><div class="label">Log360 Feature Coverage</div></div>',unsafe_allow_html=True)
with c4:
    if include_g and g_l360: st.markdown(f'<div class="metric-card"><div class="value" style="color:#FFB400">{g_l360.overall_rating}★</div><div class="label">Gartner Peer Rating</div></div>',unsafe_allow_html=True)
    else: st.markdown('<div class="metric-card"><div class="value">—</div><div class="label">Gartner (N/A)</div></div>',unsafe_allow_html=True)

tab1,tab2,tab3,tab4,tab5=st.tabs(["📋 Overview","🔍 Features","💰 Pricing","⭐ Gartner","📥 Generate PDFs"])

with tab1:
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"### {l360_cfg['name']}"); st.write(data["overview"]["log360"]); st.markdown("**Key Strengths:**")
        for s in data["strengths"]["log360"]: st.markdown(f"- ✅ {s}")
    with c2:
        st.markdown(f"### {comp_cfg['name']}"); st.write(data["overview"]["competitor"]); st.markdown("**Known Weaknesses:**")
        for w in data["weaknesses"]["competitor"]: st.markdown(f"- ⚠️ {w}")

with tab2:
    for cat in data["feature_comparison"]:
        st.markdown(f"#### {cat['category']}")
        rows=[{"Feature":f["name"],l360_cfg["short_name"]:"✅ "+f["log360"]["detail"] if f["log360"]["supported"] else "❌ "+f["log360"]["detail"],comp_cfg["short_name"]:"✅ "+f["competitor"]["detail"] if f["competitor"]["supported"] else "❌ "+f["competitor"]["detail"]} for f in cat["features"]]
        st.table(rows)

with tab3:
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"### {l360_cfg['name']}"); st.caption(f"Model: {data['pricing']['log360']['model']}")
        for tier in data["pricing"]["log360"]["tiers"]:
            st.markdown(f"**{tier['name']}** — `{tier['annual_cost']}`"); st.caption(tier["eps"])
            for feat in tier["features"]: st.markdown(f"  - {feat}")
        st.markdown("---")
        for n in data["pricing"]["log360"]["notes"]: st.markdown(f"📌 {n}")
    with c2:
        st.markdown(f"### {comp_cfg['name']}"); st.caption(f"Model: {data['pricing']['competitor']['model']}")
        for tier in data["pricing"]["competitor"]["tiers"]:
            st.markdown(f"**{tier['name']}** — `{tier['annual_cost']}`"); st.caption(tier["eps"])
            for feat in tier["features"]: st.markdown(f"  - {feat}")
        st.markdown("---")
        for n in data["pricing"]["competitor"]["notes"]: st.markdown(f"⚠️ {n}")
    st.success(f"**Pricing Advantage:** {data['pricing_comparison_summary']['log360_advantage']}")

with tab4:
    if include_g and g_l360 and g_comp:
        c1,_,c2=st.columns([5,1,5])
        with c1:
            st.markdown(f'<div class="gartner-box" style="text-align:center"><div style="font-size:3rem;font-weight:700;color:#C8102E">{g_l360.overall_rating}</div><div style="color:#FFB400;font-size:1.5rem">{render_stars(g_l360.overall_rating)}</div><div><strong>{l360_cfg["name"]}</strong></div><div style="color:#555">{g_l360.total_reviews} reviews</div><div style="color:#555">{g_l360.willingness_to_recommend}% willing to recommend</div></div>',unsafe_allow_html=True)
            if g_l360.subcategories:
                for cat,score in g_l360.subcategories.items(): st.progress(score/5.0,text=f"{cat}: {score}/5")
        with c2:
            st.markdown(f'<div class="gartner-box" style="text-align:center;border-color:#6C757D"><div style="font-size:3rem;font-weight:700;color:#6C757D">{g_comp.overall_rating}</div><div style="color:#FFB400;font-size:1.5rem">{render_stars(g_comp.overall_rating)}</div><div><strong>{comp_cfg["name"]}</strong></div><div style="color:#555">{g_comp.total_reviews} reviews</div><div style="color:#555">{g_comp.willingness_to_recommend}% willing to recommend</div></div>',unsafe_allow_html=True)
            if g_comp.subcategories:
                for cat,score in g_comp.subcategories.items(): st.progress(score/5.0,text=f"{cat}: {score}/5")
        st.caption("Source: Gartner Peer Insights — Ratings updated quarterly")
    else: st.warning(f"Gartner section will not be included — {comp_cfg['name']} has a higher or equal rating.")

with tab5:
    st.markdown("### Generate & Download PDFs")
    st.markdown(f"**Competitor:** {comp_cfg['name']}  |  **Gartner Included:** {'✅ Yes' if include_g else '❌ No'}")
    gc1,gc2=st.columns(2)
    with gc1:
        if st.button("📄 Generate Comparison Document",type="primary",use_container_width=True):
            with st.spinner("Generating comparison PDF..."):
                try:
                    pdf=generate_pdf("comparison.html",selected); fname=f"Log360_vs_{comp_cfg['short_name'].replace(' ','_')}_{datetime.now().strftime('%b_%Y')}.pdf"
                    st.markdown(create_download_link(pdf,fname),unsafe_allow_html=True); st.success("Comparison document generated!")
                except Exception as e: st.error(f"PDF generation failed: {e}"); st.info("Ensure WeasyPrint system deps are installed.")
    with gc2:
        if st.button("⚔️ Generate Battlecard",type="primary",use_container_width=True):
            with st.spinner("Generating battlecard PDF..."):
                try:
                    pdf=generate_pdf("battlecard.html",selected); fname=f"Battlecard_Log360_vs_{comp_cfg['short_name'].replace(' ','_')}_{datetime.now().strftime('%b_%Y')}.pdf"
                    st.markdown(create_download_link(pdf,fname),unsafe_allow_html=True); st.success("Battlecard generated!")
                except Exception as e: st.error(f"PDF generation failed: {e}"); st.info("Ensure WeasyPrint system deps are installed.")

st.markdown("---"); st.caption(f"ManageEngine Log360 Competitive Intelligence Tool | {datetime.now().year}")
