from flask import Flask, render_template, jsonify
import requests
import pandas as pd
import io
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────────
#  CONFIGURATION  ← paste your OneDrive link here
# ─────────────────────────────────────────────
ONEDRIVE_SHARE_URL = "https://rclwiring-my.sharepoint.com/:x:/g/personal/chatfield_rclburco_com/IQB_WrwUX7A-QaY7s8dUnic5ASNb0jDw1p6Sra3rs67oQiI?e=Q87yn3"


def resolve_onedrive_url(share_url: str) -> str:
    """Convert a OneDrive share URL into a direct download URL."""
    if "download=1" in share_url or "download=true" in share_url.lower():
        return share_url
    sep = "&" if "?" in share_url else "?"
    return share_url + sep + "download=1"


def fetch_inventory():
    download_url = resolve_onedrive_url(ONEDRIVE_SHARE_URL)
    resp = requests.get(download_url, timeout=20)
    resp.raise_for_status()

    df = pd.read_excel(io.BytesIO(resp.content), engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]

    # Normalise column names
    rename = {}
    for col in df.columns:
        low = col.lower().replace(" ", "").replace("_", "")
        if low in ("burco#", "burco"):
            rename[col] = "Burco #"
        elif low == "scn":
            rename[col] = "SCN"
        elif low in ("description", "desc"):
            rename[col] = "Description"
        elif low in ("qtyonhand", "qty", "quantity", "onhand"):
            rename[col] = "Qty On Hand"
    df.rename(columns=rename, inplace=True)

    for c in ["Burco #", "SCN", "Description", "Qty On Hand"]:
        if c not in df.columns:
            df[c] = ""

    df = df[["Burco #", "SCN", "Description", "Qty On Hand"]].copy()
    df = df.fillna("")
    df["Description"] = df["Description"].astype(str)
    df.sort_values("Description", key=lambda s: s.str.lower(), inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df.astype(str).to_dict(orient="records")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/inventory")
def inventory():
    try:
        data = fetch_inventory()
        return jsonify({
            "success": True,
            "data": data,
            "count": len(data),
            "refreshed": datetime.now().strftime("%b %d, %Y at %I:%M %p")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False)
