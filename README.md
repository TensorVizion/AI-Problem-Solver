# AI Problem Solver

A lightweight AI-powered web app for turning a problem description into a practical solution plan.

## Features

- Clean responsive interface
- AI solution generation through the OpenAI-compatible API
- 12,000-character input limit
- Copy solution button
- `Ctrl/Cmd + Enter` shortcut
- Supports custom OpenAI-compatible endpoints via `OPENAI_BASE_URL`

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Windows PowerShell
$env:OPENAI_API_KEY="your-key"
# macOS/Linux
export OPENAI_API_KEY="your-key"

python app.py
```

Open `http://localhost:5000`.

### Configuration

- `OPENAI_API_KEY` — required API key
- `OPENAI_MODEL` — optional model name; defaults to `gpt-4o-mini`
- `OPENAI_BASE_URL` — optional OpenAI-compatible API endpoint
- `PORT` — optional port; defaults to `5000`

Never commit API keys to the repository. For production, use your host's secret/environment-variable manager.
