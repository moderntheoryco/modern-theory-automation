import os
import json
import anthropic
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

app = Flask(__name__)

# ── helpers ──────────────────────────────────────────────────────────────────

def get_drive_service():
    creds_json = os.environ["GOOGLE_CREDENTIALS"]
    creds_info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def call_claude(master_brief: str, monthly_input: str, client_name: str, tier: str) -> str:
    """Call Claude API and return the full content kit text."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    is_growth = "growth" in tier.lower()

    caption_instructions = (
        "30 Instagram captions total:\n"
        "- 10 educational captions\n"
        "- 10 engagement captions\n"
        "- 10 promotional captions"
        if is_growth else
        "20 Instagram captions total:\n"
        "- 10 educational captions\n"
        "- 10 engagement captions\n"
        "- NO promotional captions"
    )

    extra_deliverables = (
        "\n- 8 video scripts (short-form, 30–60 seconds each)\n"
        "- 1 long-form blog post or email newsletter (600–900 words)"
        if is_growth else ""
    )

    prompt = f"""You are writing a monthly content kit for a medical spa client. You are a registered nurse and clinical content strategist. All content must be FTC-compliant, clinically accurate, and written for an aesthetic wellness audience.

CLIENT MASTER BRIEF:
{master_brief}

MONTHLY INPUT FROM CLIENT:
{monthly_input}

DELIVERABLES FOR THIS KIT:

{caption_instructions}

- 1 email marketing campaign (subject line + full email body)
- 1 monthly content calendar (map each caption to a day of the month){extra_deliverables}

FORMAT INSTRUCTIONS:
- Use clear section headers in ALL CAPS (e.g. EDUCATIONAL CAPTIONS, ENGAGEMENT CAPTIONS, etc.)
- Number each caption
- For captions, include: the caption text, 5 relevant hashtags, and a content type label
- For the email, include the subject line on its own line labeled SUBJECT:
- For the content calendar, list Day 1 through Day 30 with the caption number assigned to each posting day (post 4–5x per week)
- Write in a warm, professional, clinical tone that reflects the practice's voice from the Master Brief
- Never make specific medical claims or guarantees
- All promotional content must include appropriate disclaimers

Begin the kit now."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def create_google_doc(drive_service, title: str, content: str, folder_id: str) -> str:
    """Create a plain-text Google Doc in the specified Drive folder."""
    # Upload as plain text; Drive will store it as a Google Doc
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
        "parents": [folder_id]
    }
    media = MediaInMemoryUpload(
        content.encode("utf-8"),
        mimetype="text/plain",
        resumable=False
    )
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()
    return file.get("webViewLink", "")


# ── route ─────────────────────────────────────────────────────────────────────

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)

    client_name   = data.get("client_name", "Client")
    tier          = data.get("tier", "Essential")
    master_brief  = data.get("master_brief", "")
    monthly_input = data.get("monthly_input", "")
    folder_id     = data.get("folder_id", os.environ.get("DRIVE_FOLDER_ID", ""))
    month_label   = data.get("month_label", "Monthly")

    if not master_brief:
        return jsonify({"error": "master_brief is required"}), 400

    # 1. Generate content with Claude
    kit_text = call_claude(master_brief, monthly_input, client_name, tier)

    # 2. Upload to Google Drive as a Google Doc
    drive_service = get_drive_service()
    doc_title = f"{client_name} — Content Kit {month_label}"
    doc_link = create_google_doc(drive_service, doc_title, kit_text, folder_id)

    return jsonify({
        "status": "success",
        "doc_title": doc_title,
        "doc_link": doc_link
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
