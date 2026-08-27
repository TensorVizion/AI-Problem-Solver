# AI Problem Solver 🚀

A lightweight multi-provider AI app that turns messy problems into practical solution plans.

## Features

- OpenAI, OpenRouter, and NVIDIA NIM providers
- API keys entered from the in-app Settings panel
- Browser-local API-key storage (never committed to the repo)
- Server environment-variable fallback for hosted deployments
- Problem modes: General, Coding, Business, Marketing, Math, Research, Writing, Troubleshooting
- Single-model solving
- Multi-model comparison across up to 3 providers
- Optional final AI judge that synthesizes the strongest answer
- Local problem history (up to 20 items)
- Copy solutions
- Responsive dark UI
- `Ctrl/Cmd + Enter` shortcut
- Custom model names

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` and enter your provider API key under **Settings**.

## Provider configuration

The app uses OpenAI-compatible chat completions for all three providers.

| Provider | Browser key | Optional server variable | Default model |
|---|---|---|---|
| OpenAI | Settings | `OPENAI_API_KEY` | `gpt-4o-mini` |
| OpenRouter | Settings | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` |
| NVIDIA NIM | Settings | `NVIDIA_NIM_API_KEY` | `meta/llama-3.1-8b-instruct` |

Optional model environment variables: `OPENAI_MODEL`, `OPENROUTER_MODEL`, `NVIDIA_NIM_MODEL`. `PORT` defaults to `5000`.

## Security note

For a personal/local deployment, browser-local keys are convenient. For a public SaaS deployment, do not collect users' API keys without a proper security architecture. Add authentication, HTTPS, rate limiting, server-side secret handling, and a clear privacy policy before production use.

## Roadmap ideas

- Streaming responses
- Markdown rendering
- PDF/Markdown export
- Shareable solution links
- Token/cost estimates
- User accounts and cloud history
- Model discovery APIs
- Solution quality scoring
- File/image attachments
- Web research mode
