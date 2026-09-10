import json
import os
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, ElementTree

import firebase_admin
from firebase_admin import credentials, firestore

SITE = "https://pak-point.github.io/pak-point/"

service_account = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
if not service_account:
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT GitHub Secret is missing.")

try:
    service_account_info = json.loads(service_account)
except json.JSONDecodeError as exc:
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT is not valid JSON.") from exc

if not firebase_admin._apps:
    firebase_admin.initialize_app(
        credentials.Certificate(service_account_info)
    )

db = firestore.client()

root = Element(
    "urlset",
    {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
)

def add_url(loc, lastmod=None):
    url = SubElement(root, "url")
    SubElement(url, "loc").text = loc
    if lastmod:
        SubElement(url, "lastmod").text = lastmod

# Homepage
add_url(SITE)

# Published Firebase articles
docs = db.collection("articles").where("status", "==", "published").stream()

articles = []

for doc in docs:
    data = doc.to_dict() or {}

    updated = data.get("updatedAt") or data.get("createdAt")
    lastmod = None

    if updated and hasattr(updated, "timestamp"):
        lastmod = datetime.fromtimestamp(
            updated.timestamp(), tz=timezone.utc
        ).date().isoformat()

    article_url = (
        SITE
        + "article.html?id="
        + doc.id
    )

    articles.append((article_url, lastmod))

# Stable ordering makes GitHub commits clean.
for article_url, lastmod in sorted(articles):
    add_url(article_url, lastmod)

tree = ElementTree(root)

try:
    import xml.etree.ElementTree as ET
    ET.indent(tree, space="  ")
except AttributeError:
    pass

tree.write("sitemap.xml", encoding="utf-8", xml_declaration=True)

# robots.txt points Google to the sitemap.
with open("robots.txt", "w", encoding="utf-8") as f:
    f.write(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE}sitemap.xml\n"
    )

print(f"Sitemap generated with {len(articles)} published articles.")
