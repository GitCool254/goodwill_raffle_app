import os
import io
from datetime import datetime
from flask import Flask, render_template, request, send_file
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
TEMPLATE_PATH = "templates/goodwill_raffle_template.pdf"
OUTPUT_DIR = "output"
SERVICE_ACCOUNT_FILE = "creds/service_account.json"
SHEET_NAME = "Goodwill Raffle Logs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------- GOOGLE SHEETS -------------
def get_sheets_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    return gspread.authorize(creds)

def log_to_sheets(ticket_no, full_name, ticket_price, event_place, event_date):
    try:
        client = get_sheets_client()
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row([
            datetime.utcnow().isoformat(),
            ticket_no, full_name, ticket_price, event_place, event_date
        ])
    except Exception as e:
        print("Google Sheets logging failed:", e)

# --------------- HELPERS ----------------
def replace_placeholders(template_path, replacements, output_path):
    reader = PdfReader(template_path)
    writer = PdfWriter()
    page = reader.pages[0]

    # Create overlay PDF for replacements
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)

    # Coordinates tuned for your layout
    # Adjusted coordinates for perfect fit
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(105*mm, 100*mm, replacements["TICKET_NO"])  # Move up slightly

    c.setFont("Helvetica", 10)
    c.drawString(60*mm, 73*mm, replacements["FULL_NAME"])     # Full Name
    c.drawString(60*mm, 67*mm, replacements["TICKET_PRICE"])  # Ticket Price
    c.drawString(60*mm, 61*mm, replacements["EVENT_PLACE"])   # Event Place
    c.drawString(60*mm, 55*mm, replacements["EVENT_DATE"])    # Event Date

    # QR bottom-right aligned
    qr = qrcode.make(replacements["QR_TEXT"])
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    c.drawImage(ImageReader(qr_buffer), 165*mm, 38*mm, width=20*mm, height=20*mm)

    c.save()
    packet.seek(0)

    overlay = PdfReader(packet)
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

# --------------- FLASK APP ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    full_name = request.form["full_name"]
    ticket_price = request.form["ticket_price"]
    event_place = request.form["event_place"]
    event_date = request.form["event_date"]

    ticket_no = f"GWS-{int(datetime.utcnow().timestamp())}"
    qr_text = f"Goodwillstores@{full_name}-{ticket_no}"

    replacements = {
        "TICKET_NO": ticket_no,
        "FULL_NAME": full_name,
        "TICKET_PRICE": ticket_price,
        "EVENT_PLACE": event_place,
        "EVENT_DATE": event_date,
        "QR_TEXT": qr_text
    }

    output_path = os.path.join(OUTPUT_DIR, f"{ticket_no}.pdf")
    replace_placeholders(TEMPLATE_PATH, replacements, output_path)
    log_to_sheets(ticket_no, full_name, ticket_price, event_place, event_date)

    return send_file(output_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
