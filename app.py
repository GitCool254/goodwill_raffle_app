from flask import Flask, render_template_string, request, send_file
import fitz  # PyMuPDF
import io
import qrcode
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# Google Sheets setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

import json, os
from google.oauth2.service_account import Credentials

service_account_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open("Goodwill Raffle Logs").sheet1

# HTML form
form_html = """
<!DOCTYPE html>
<html>
<head><title>Goodwillstores Raffle Ticket Generator</title></head>
<body>
  <h2>Goodwillstores Raffle Ticket Generator</h2>
  <form method="POST">
    Full Name: <input name="fullname" required><br>
    Ticket Price: <input name="price" required><br>
    Event Place: <input name="place" required><br>
    Event Date: <input name="date" required><br>
    <button type="submit">Generate Ticket</button>
  </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        fullname = request.form["fullname"]
        price = request.form["price"]
        place = request.form["place"]
        date = request.form["date"]

        # Generate unique ticket number and QR data
        ticket_no = f"GWS-{int(__import__('time').time())}"
        qr_data = f"Goodwillstores@{fullname} - {ticket_no}"

        # --- Generate QR code ---
        qr_img = qrcode.make(qr_data)
        qr_bytes = io.BytesIO()
        qr_img.save(qr_bytes, format="PNG")
        qr_bytes.seek(0)

        # --- Open PDF template ---
        template_path = "templates/goodwill_raffle_template.pdf"
        doc = fitz.open(template_path)
        page = doc[0]

        # --- Replace placeholders with actual form data ---
        replacements = {
            "Full Name:": f"Full Name: {fullname}",
            "Ticket Price:": f"Ticket Price: {price}",
            "Event Place:": f"Event Place: {place}",
            "Event Date:": f"Event Date: {date}",
            "Ticket No:": f"Ticket No: {ticket_no}"
        }

        # smarter placement: wrap & auto-shrink to fit the area to the right of each label
from math import floor

page_rect = page.rect  # full page rect
right_margin = 20  # points from the right edge; tune if needed

for label, value in label_mapping.items():
    matches = page.search_for(label)
    for inst in matches:
        # define box starting a few points right of the label up to the page right margin
        x0 = inst.x1 + 4            # start just after label
        y0 = inst.y0 - 1            # small vertical tweak (top)
        x1 = page_rect.width - right_margin
        y1 = inst.y1 + 1            # small vertical tweak (bottom)
        box = fitz.Rect(x0, y0, x1, y1)

        # initial font size: use box height * 0.8 (heuristic), cap at 14
        initial_fs = max(6, min(14, int(box.height * 0.8)))
        fs = initial_fs

        # try insert_textbox and shrink until it fits within box height (max lines)
        # We'll allow up to 2 lines by default (increase as needed)
        max_lines_allowed = 2
        while fs >= 6:
            # draw into a temporary page copy so we can test whether text fits
            # simpler: try insert_textbox; if it obviously overflows visually you'll see; but we try to avoid too many iterations
            page.insert_textbox(box, value, fontsize=fs, fontname="helv", align=0)  # left align
            # To check fit: measure height taken roughly by lines = ceil(text_width/box.width) * line_height
            # We can approximate: line_height ≈ fs * 1.2
            # Use page.get_text_length if available for exact width, else approximate
            try:
                text_width = page.get_text_length(value, fontsize=fs, fontname="helv")
            except Exception:
                # fallback estimation using average char width
                avg_char_width = fs * 0.5
                text_width = len(value) * avg_char_width

            lines_needed = max(1, int((text_width / box.width) + 0.999))
            est_height = lines_needed * (fs * 1.2)
            if lines_needed <= max_lines_allowed and est_height <= box.height:
                # fits — done
                break
            # else: it doesn't fit — remove the previously drawn text and shrink font, then retry
            # remove by redaction of the box area (clean) then apply
            page.add_redact_annot(box)
            page.apply_redactions()
            fs -= 1

        # final pass: draw with the last fs (if fs<6, will still draw with 6)
        if fs < 6:
            fs = 6
        page.insert_textbox(box, value, fontsize=fs, fontname="helv", align=0)

        # --- Save final ticket to memory and return download ---
        output_pdf = io.BytesIO()
        doc.save(output_pdf)
        output_pdf.seek(0)
        doc.close()

        return send_file(output_pdf, as_attachment=True, download_name=f"raffle_{fullname}.pdf")

    return render_template_string(form_html)

if __name__ == "__main__":

    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
