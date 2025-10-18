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
            "{{FULL_NAME}}": fullname,
            "{{TICKET_PRICE}}": price,
            "{{EVENT_PLACE}}": place,
            "{{EVENT_DATE}}": date,
            "{{TICKET_NO}}": ticket_no
        }

        for placeholder, value in replacements.items():
            for inst in page.search_for(placeholder):
                # Remove old placeholder text
                page.add_redact_annot(inst)
                page.apply_redactions()
                # Write the new text in its place
                page.insert_text(
                    (inst.x0, inst.y0),
                    value,
                    fontsize=12,
                    fontname="helv",
                    fill=(0, 0, 0)
                )

        # --- Add QR code image ---
        qr_rect = fitz.Rect(420, 620, 500, 700)
        page.insert_image(qr_rect, stream=qr_bytes)

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
