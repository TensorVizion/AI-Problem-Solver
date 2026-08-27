import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

PROVIDERS = {
    "openai": {"name": "OpenAI", "base_url": None, "env_key": "OPENAI_API_KEY", "default_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")},
    "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "env_key": "OPENROUTER_API_KEY", "default_model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")},
    "nvidia": {"name": "NVIDIA NIM", "base_url": "https://integrate.api.nvidia.com/v1", "env_key": "NVIDIA_NIM_API_KEY", "default_model": os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.1-8b-instruct")},
}

SYSTEM_PROMPT = """You are AI Problem Solver, a practical assistant that helps users solve real-world problems.
Analyze the user's problem, identify the key issue, give a clear solution, and provide actionable steps.
If useful, include assumptions, alternatives, examples, or a short checklist. Be concise but useful.
Do not pretend to have performed actions you cannot perform."""

@app.get("/")
def index():
    return render_template("index.html", providers=PROVIDERS)

@app.get("/api/providers")
def providers():
    return jsonify({k: {"name": v["name"], "default_model": v["default_model"]} for k, v in PROVIDERS.items()})

@app.post("/api/solve")
def solve():
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()
    provider_name = (data.get("provider") or "openai").lower()
    provider = PROVIDERS.get(provider_name)
    api_key = (data.get("api_key") or "").strip()
    model = (data.get("model") or "").strip()

    if not provider:
        return jsonify({"error": "Unsupported provider. Choose OpenAI, OpenRouter, or NVIDIA NIM."}), 400
    if not problem:
        return jsonify({"error": "Please describe a problem first."}), 400
    if len(problem) > 12000:
        return jsonify({"error": "Problem description is too long (12,000 character limit)."}), 400

    # Server environment variables remain available for hosted deployments.
    api_key = api_key or os.getenv(provider["env_key"], "").strip()
    if not api_key:
        return jsonify({"error": f"Add your {provider['name']} API key in Settings."}), 503

    model = model or provider["default_model"]
    try:
        kwargs = {"api_key": api_key}
        if provider["base_url"]:
            kwargs["base_url"] = provider["base_url"]
        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": problem}],
            temperature=0.4,
        )
        answer = response.choices[0].message.content or "No solution was returned."
        return jsonify({"answer": answer, "provider": provider_name, "model": model})
    except Exception as exc:
        app.logger.exception("AI request failed")
        return jsonify({"error": f"AI request failed: {exc}"}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
