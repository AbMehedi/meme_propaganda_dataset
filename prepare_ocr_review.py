#!/usr/bin/env python3
"""Draft OCR for the 20-image pilot and make a local human-review page.

Run with the Python in .ocr-venv. The machine draft can be imported with an
author-verification-pending status; the downloaded CSV supports later review.
"""

import csv
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "pilot_20_audit.csv"
DRAFT = ROOT / "ocr_draft_20.csv"
RAW = ROOT / "ocr_raw_20.json"
REVIEW = ROOT / "ocr_review_20.html"


def read_pilot():
    with PILOT.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Pilot list is empty")
    return rows


def run_ocr(rows):
    import easyocr

    reader = easyocr.Reader(["bn", "en"], gpu=False, verbose=False)
    draft, raw = [], []
    for row in rows:
        image_path = ROOT / row["relative_path"]
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        regions = reader.readtext(str(image_path), detail=1, paragraph=False)
        parts = [str(text).strip() for _, text, _ in regions if str(text).strip()]
        draft.append({"image_id": row["image_id"], "ocr_draft": "\n".join(parts)})
        raw.append({
            "image_id": row["image_id"],
            "relative_path": row["relative_path"],
            "regions": [
                {"polygon": [[float(coordinate) for coordinate in point] for point in box],
                 "text": text, "confidence": float(confidence)}
                for box, text, confidence in regions
            ],
        })
        print(f"{row['pilot_order']}/{len(rows)} {row['image_id']}: {len(regions)} OCR regions", flush=True)

    with DRAFT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["image_id", "ocr_draft"])
        writer.writeheader()
        writer.writerows(draft)
    RAW.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {row["image_id"]: row["ocr_draft"] for row in draft}


def make_review_page(rows, drafts):
    cards = []
    for row in rows:
        image_id = html.escape(row["image_id"], quote=True)
        image_path = html.escape(row["relative_path"].replace("\\", "/"), quote=True)
        text = html.escape(drafts.get(row["image_id"], ""))
        cards.append(f"""
        <section class="card" data-id="{image_id}">
          <h2>Image {html.escape(row['pilot_order'])} <small>{image_id}</small></h2>
          <a href="{image_path}" target="_blank" title="Open full-size image"><img src="{image_path}" alt="Pilot image {html.escape(row['pilot_order'])}"></a>
          <div class="editor">
            <label for="ocr-{image_id}">Exact text visible in image</label>
            <textarea id="ocr-{image_id}" rows="9" spellcheck="false">{text}</textarea>
            <label class="check"><input type="checkbox" class="reviewed"> I inspected this image and corrected the text. An empty field means I confirmed no readable embedded text.</label>
          </div>
        </section>""")
    page = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CampNet OCR review — 20 images</title>
<style>
body{font:16px system-ui,sans-serif;max-width:1400px;margin:auto;padding:1.5rem;color:#1c2430;background:#f5f7fa}
header{position:sticky;top:0;background:#fff;padding:1rem;box-shadow:0 2px 8px #0002;z-index:2}
h1{font-size:1.4rem;margin:0 0 .4rem}p{margin:.3rem 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(540px,1fr));gap:1rem;margin-top:1rem}
.card{background:white;border:2px solid #d8dfe7;border-radius:8px;padding:1rem}.card.done{border-color:#248352}
h2{font-size:1rem;margin:0 0 .7rem}small{font-weight:400;color:#5b6470}.card img{display:block;max-width:100%;max-height:500px;margin:auto;object-fit:contain}
.editor{margin-top:.8rem}textarea{display:block;width:100%;box-sizing:border-box;resize:vertical;font:16px/1.5 sans-serif;margin:.4rem 0}.check{display:block;line-height:1.5}
button{padding:.65rem 1rem;font-weight:600;cursor:pointer}button:disabled{cursor:not-allowed}code{font-size:.9rem}
</style>
<header><h1>CampNet pilot OCR review</h1>
<p>Machine OCR is a draft. Compare every word with the original image, including Bengali spelling, numbers, logos, and small text. Click an image for full size.</p>
<p><strong id="progress">0 of 20 reviewed</strong> · <button id="download" disabled>Download ocr_corrected_20.csv</button></p>
<p>After downloading, place the CSV beside this HTML file and run the <code>audit-ocr</code> command in the README. Recheck annotations for images whose OCR changed.</p></header>
<main class="cards">__CARDS__</main>
<script>
const cards=[...document.querySelectorAll('.card')], button=document.getElementById('download');
const storageKey='campnet-ocr-review-v1';
try { const saved=JSON.parse(localStorage.getItem(storageKey)||'{}'); for(const card of cards){const item=saved[card.dataset.id];if(item){card.querySelector('textarea').value=item.text;card.querySelector('.reviewed').checked=!!item.reviewed;}} } catch(_) {}
function refresh(){
  const count=cards.filter(card=>card.querySelector('.reviewed').checked).length;
  for(const card of cards) card.classList.toggle('done',card.querySelector('.reviewed').checked);
  document.getElementById('progress').textContent=`${count} of ${cards.length} reviewed`;
  button.disabled=count!==cards.length;
  try{const data={};for(const card of cards)data[card.dataset.id]={text:card.querySelector('textarea').value,reviewed:card.querySelector('.reviewed').checked};localStorage.setItem(storageKey,JSON.stringify(data));}catch(_){}
}
for(const card of cards)for(const input of card.querySelectorAll('textarea,input'))input.addEventListener('input',refresh);
function quoteCsv(value){return '"'+String(value).replaceAll('"','""')+'"';}
button.addEventListener('click',()=>{
  if(button.disabled)return;
  const lines=['image_id,ocr_corrected',...cards.map(card=>quoteCsv(card.dataset.id)+','+quoteCsv(card.querySelector('textarea').value.trim()))];
  const blob=new Blob(['\\uFEFF'+lines.join('\\r\\n')+'\\r\\n'],{type:'text/csv;charset=utf-8'});
  const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='ocr_corrected_20.csv';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),30000);
});
refresh();
</script></html>""".replace("__CARDS__", "\n".join(cards))
    REVIEW.write_text(page, encoding="utf-8")


def main():
    rows = read_pilot()
    drafts = run_ocr(rows)
    make_review_page(rows, drafts)
    print(f"Saved draft: {DRAFT}")
    print(f"Saved OCR regions: {RAW}")
    print(f"Open and complete review: {REVIEW}")


if __name__ == "__main__":
    main()
