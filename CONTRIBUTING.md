# Contributing to AI Problem Solver

Thanks for helping improve AI Problem Solver! 🚀

This project is intentionally lightweight. Contributions should keep the app simple, reliable, understandable, and easy to deploy.

## Development setup

### Requirements

- Python 3.11+
- Git
- A provider API key for live AI requests (OpenAI, OpenRouter, or NVIDIA NIM)

### Run locally

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
python app.py
```

Then open `http://localhost:5000`.

API keys can be entered through the Settings panel for local development. Never commit real API keys to GitHub.

## How the project is structured

```text
app.py                 Flask application and provider integrations
templates/index.html   Main application UI
static/style.css       UI styling and responsive layout
static/models.js       Provider/model selector and model discovery
static/chat.js         Follow-up conversation UI
requirements.txt       Python dependencies
render.yaml             Render deployment configuration
Procfile                Production Gunicorn startup
README.md               Project documentation
CONTRIBUTING.md         Contribution guidelines
```

## Making changes

Before changing code:

1. Read the existing implementation related to your change.
2. Reuse the current architecture and provider abstractions.
3. Keep the change focused on the requested feature or bug.
4. Avoid adding dependencies unless they are genuinely needed.
5. Do not modify unrelated functionality.

### Frontend changes

When modifying the UI:

- Preserve responsive behavior.
- Keep accessibility in mind.
- Do not introduce duplicate ownership of DOM elements or state.
- Use existing styling conventions where practical.
- Test both desktop and narrow/mobile layouts.

The model selector has a single owner: `static/models.js`. Other frontend code should read the selected `#model` value rather than replacing or repopulating it.

### Backend/provider changes

When modifying AI providers:

- Keep provider-specific configuration inside `PROVIDERS`.
- Preserve OpenAI-compatible API behavior where possible.
- Use environment variables for server-side credentials.
- Never log API keys or other secrets.
- Handle provider failures with useful user-facing errors.
- Keep model fallback behavior intact when live discovery is unavailable.

### New models

Prefer adding models through provider configuration or environment variables rather than scattering model IDs throughout the UI.

The application supports provider-specific model catalogs and can discover models from configured OpenAI-compatible providers.

## Testing checklist

Before opening a pull request, test the affected paths locally.

At minimum, verify:

- `/` loads successfully.
- The Settings popup opens and closes.
- Provider selection works.
- The model dropdown populates and changes with providers.
- A valid API key can solve a problem.
- Coding mode works.
- Research mode works.
- Model comparison works when multiple providers are configured.
- Follow-up chat works after a solution.
- Markdown and TXT export work.
- Invalid/empty input produces a useful error.
- The app still starts with `python app.py`.

For provider changes, also test the relevant provider's model IDs and API endpoint.

## Commit messages

Use clear, focused commit messages. Examples:

```text
Add coding-mode response structure
Fix provider model selector race
Improve OpenRouter error handling
Update Render deployment configuration
```

Avoid vague messages such as `stuff`, `changes`, or `fixes`.

## Pull requests

A good pull request should include:

- A clear title.
- A concise description of the problem and solution.
- The files or areas changed.
- Testing performed.
- Any provider/API/deployment requirements.

Keep pull requests focused. A feature pull request should not also contain unrelated formatting or refactoring unless necessary.

## Security

Never commit:

- API keys
- Access tokens
- Passwords
- Private credentials
- `.env` files containing secrets

If you accidentally expose a secret, revoke/rotate it immediately and then remove it from the repository history as appropriate.

Public deployments should use server-side environment secrets, HTTPS, authentication where appropriate, and rate limiting.

## Feature ideas

Useful contributions include:

- Better coding-agent workflows
- Additional provider integrations
- More reliable model discovery
- Better research/source handling
- Automated tests and CI
- Accessibility improvements
- Deployment improvements
- Performance and error-handling improvements

## Code of conduct

Be respectful, constructive, and professional. Focus discussions on the code, implementation, and user experience.

## License

See the repository license, if present, for the terms governing contributions and distribution.
