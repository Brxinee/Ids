"""
Run this after username_hunter.py finds new usernames.
It reads available_usernames.csv and available_dotted.csv
then injects the data into index.html automatically.

Usage:
  python site/update_data.py
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITE = Path(__file__).parent

plain  = []
dotted = []

plain_csv = ROOT / "available_usernames.csv"
if plain_csv.exists():
    with open(plain_csv, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("username"):
                plain.append({"u": row["username"], "t": "plain"})

dotted_csv = ROOT / "available_dotted.csv"
if dotted_csv.exists():
    with open(dotted_csv, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("username"):
                dotted.append({"u": row["username"], "t": "dotted"})

all_data = dotted + plain  # dotted first
js_data  = json.dumps(all_data, separators=(",", ":"))

html_path = SITE / "index.html"
html = html_path.read_text()
html = re.sub(r'const DATA = \[.*?\];', f'const DATA = {js_data};', html, flags=re.DOTALL)
html_path.write_text(html)

print(f"Updated index.html — {len(plain)} plain, {len(dotted)} dotted ({len(all_data)} total)")
