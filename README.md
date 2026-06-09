# Modern Theory Automation

Flask app hosted on Render. Receives a POST request from Make.com containing client brief and monthly input, calls the Claude API to generate a content kit, and uploads the result as a Google Doc to the client's Drive folder.

## Environment Variables Required

- `ANTHROPIC_API_KEY` — Anthropic API key
- `GOOGLE_CREDENTIALS` — Full JSON content of Google service account key
- `DRIVE_FOLDER_ID` — Default Google Drive folder ID for uploads
