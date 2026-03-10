import os
from datetime import datetime
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from scrapers.gartner import get_rating, should_include_gartner

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def count_advantages(data):
    lw = cw = t = 0
    for cat in data.get("feature_comparison", []):
        for f in cat.get("features", []):
            l, c = f["log360"]["supported"], f["competitor"]["supported"]
            if l and not c: lw += 1
            elif c and not l: cw += 1
            else: t += 1
    return {"log360": lw, "competitor": cw, "ties": t}

def generate_comparison_doc(competitor_key, output_dir="output", template_dir="templates"):
    tokens = load_yaml("config/design_tokens.yaml")
    data = load_yaml(f"data/comparisons/{competitor_key}.yaml")
    products = load_yaml("config/products.yaml")
    comp_cfg = products["competitors"][competitor_key]
    l360_cfg = products["log360"]
    include_gartner = should_include_gartner("log360", competitor_key)
    g_l360 = g_comp = None
    if include_gartner:
        g_l360 = get_rating("log360", l360_cfg.get("gartner_product_url"))
        g_comp = get_rating(competitor_key, comp_cfg.get("gartner_product_url"))
    ctx = {"tokens": tokens, "data": data, "log360": l360_cfg, "competitor": comp_cfg,
           "advantages": count_advantages(data), "include_gartner": include_gartner,
           "gartner_log360": g_l360, "gartner_competitor": g_comp,
           "generated_date": datetime.now().strftime("%B %Y")}
    env = Environment(loader=FileSystemLoader(template_dir))
    html = env.get_template("comparison.html").render(**ctx)
    os.makedirs(output_dir, exist_ok=True)
    name = comp_cfg.get("short_name", competitor_key).replace(" ", "_")
    fname = f"ManageEngine_Log360_vs_{name}_{datetime.now().strftime('%b_%Y')}.pdf"
    out = os.path.join(output_dir, fname)
    HTML(string=html, base_url=str(Path(template_dir).resolve())).write_pdf(out)
    return out
