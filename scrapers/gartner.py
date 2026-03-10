import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
GARTNER_BASE = "https://www.gartner.com/reviews"


@dataclass
class GartnerRating:
    product_name: str
    overall_rating: float
    total_reviews: int
    willingness_to_recommend: Optional[float] = None
    subcategories: Optional[dict] = field(default_factory=dict)
    source: str = "manual"


MANUAL_RATINGS: dict[str, GartnerRating] = {
    "log360": GartnerRating(
        product_name="ManageEngine Log360", overall_rating=4.4, total_reviews=310,
        willingness_to_recommend=88.0,
        subcategories={"Evaluation & Contracting": 4.5, "Integration & Deployment": 4.3, "Service & Support": 4.4, "Product Capabilities": 4.4},
        source="manual_2025Q4",
    ),
    "micro_focus_sentinel": GartnerRating(
        product_name="Micro Focus Sentinel", overall_rating=4.0, total_reviews=120,
        willingness_to_recommend=76.0,
        subcategories={"Evaluation & Contracting": 4.0, "Integration & Deployment": 3.8, "Service & Support": 3.9, "Product Capabilities": 4.1},
        source="manual_2025Q4",
    ),
    "splunk": GartnerRating(
        product_name="Splunk Enterprise Security", overall_rating=4.3, total_reviews=780,
        willingness_to_recommend=84.0,
        subcategories={"Evaluation & Contracting": 4.1, "Integration & Deployment": 4.0, "Service & Support": 4.2, "Product Capabilities": 4.5},
        source="manual_2025Q4",
    ),
    "ibm_qradar": GartnerRating(
        product_name="IBM QRadar", overall_rating=4.2, total_reviews=560,
        willingness_to_recommend=80.0,
        subcategories={"Evaluation & Contracting": 4.1, "Integration & Deployment": 3.9, "Service & Support": 4.1, "Product Capabilities": 4.3},
        source="manual_2025Q4",
    ),
    "microsoft_sentinel": GartnerRating(
        product_name="Microsoft Sentinel", overall_rating=4.4, total_reviews=430,
        willingness_to_recommend=86.0,
        subcategories={"Evaluation & Contracting": 4.3, "Integration & Deployment": 4.2, "Service & Support": 4.3, "Product Capabilities": 4.5},
        source="manual_2025Q4",
    ),
}


def fetch_gartner_rating(product_url_path: str) -> Optional[GartnerRating]:
    url = f"{GARTNER_BASE}{product_url_path}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", "Accept": "text/html"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        el = soup.select_one('[data-testid="overall-rating"], .overall-rating, .star-rating-score')
        if not el:
            return None
        m = re.search(r"(\d+\.?\d*)", el.get_text(strip=True))
        if not m:
            return None
        overall = float(m.group(1))
        reviews = 0
        rev_el = soup.select_one('[data-testid="total-reviews"], .review-count')
        if rev_el:
            rm = re.search(r"(\d+)", rev_el.get_text(strip=True).replace(",", ""))
            if rm:
                reviews = int(rm.group(1))
        return GartnerRating(product_name=product_url_path.split("/product/")[-1], overall_rating=overall, total_reviews=reviews, source="scraped")
    except Exception as e:
        logger.warning("Gartner scrape failed for %s: %s", product_url_path, e)
        return None


def get_rating(product_key: str, product_url_path: Optional[str] = None) -> GartnerRating:
    if product_url_path:
        live = fetch_gartner_rating(product_url_path)
        if live:
            return live
    if product_key in MANUAL_RATINGS:
        return MANUAL_RATINGS[product_key]
    raise ValueError(f"No Gartner rating data for: {product_key}")


def should_include_gartner(log360_key: str = "log360", competitor_key: str = "") -> bool:
    try:
        log360 = get_rating(log360_key)
        comp = get_rating(competitor_key)
        return log360.overall_rating >= comp.overall_rating
    except ValueError:
        return False
