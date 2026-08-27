import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

PROVIDERS = {
    "openai": {"name": "OpenAI", "base_url": None, "env_key": "OPENAI_API_KEY", "default_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")},
    "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "env_key": "OPENROUTER_API_KEY", "default_model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")},
    "nvidia": {"name": "NVIDIA NIM", "base_url": "https://integrate.api.nvidia.com/v1", "env_key": "NVIDIA_NIM_API_KEY", "default_model": os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.1-8b-instruct")},
}

MODES = {
    "general": "Solve the problem practically and clearly.",
    "coding": "Act as a senior software engineer. Diagnose bugs, explain root causes, and provide implementation-ready fixes.",
    "business": "Act as a pragmatic business strategist. Focus on ROI, feasibility, risks, and concrete next steps.",
    "marketing": "Act as a performance marketing expert. Focus on audience, positioning, conversion, testing, and measurable actions.",
    "math": "Act as a meticulous mathematician. Show necessary reasoning and verify calculations.",
    "research": "Act as a research analyst. Produce a structured research brief, clearly separate established facts from assumptions, identify uncertainty, and recommend what evidence should be checked.",
    "writing": "Act as an expert editor and writing coach. Diagnose the writing problem and give a strong, usable solution.",
    "troubleshooting": "Act as a technical troubleshooter. Prioritize likely root causes, diagnostic checks, and fixes from safest to most invasive.",
}

BASE_PROMPT = """You are AI Problem Solver, a practical assistant that helps users solve real-world problems.
Analyze the user's problem, identify the key issue, give a clear recommended solution, and provide actionable steps.
When useful, include assumptions, alternatives, tradeoffs, examples, and a concise checklist.
Do not pretend to have performed actions you cannot perform. Be accurate and practical."""


def client_for(provider_name, api_key):
    provider = PROVIDERS[provider_name]
    kwargs = {"api_key": api_key}
    if provider["base_url"]:
        kwargs["base_url"] = provider["base_url"]
    return OpenAI(**kwargs)


def solve_one(problem, provider_name, api_key, model, mode="general", context=""):
    provider = PROVIDERS[provider_name]
    key = (api_key or "").strip() or os.getenv(provider["env_key"], "").strip()
    if not key:
        raise ValueError(f"No API key configured for {provider['name']}.")
    prompt = f"{BASE_PROMPT}\n\nMode: {MODES.get(mode, MODES['general'])}"
    if context:
        prompt += "\n\nResearch context provided by the application. Use it as evidence, do not invent citations:\n" + context
    response = client_for(provider_name, key).chat.completions.create(
        model=model or provider["default_model"],
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": problem}],
        temperature=0.4,
    )
    return response.choices[0].message.content or "No solution was returned."


@app.get("/")
def index():
    return render_template("index.html", providers=PROVIDERS, modes=MODES)


@app.get("/api/providers")
def providers():
    return jsonify({k: {"name": v["name"], "default_model": v["default_model"]} for k, v in PROVIDERS.items()})


@app.post("/api/solve")
def solve():
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()
    provider_name = (data.get("provider") or "openai").lower()
    provider = PROVIDERS.get(provider_name)
    if not provider:
        return jsonify({"error": "Unsupported provider."}), 400
    if not problem or len(problem) > 12000:
        return jsonify({"error": "Enter a problem between 1 and 12,000 characters."}), 400
    model = (data.get("model") or provider["default_model"]).strip()
    try:
        answer = solve_one(problem, provider_name, data.get("api_key"), model, data.get("mode", "general"), data.get("research_context", ""))
        return jsonify({"answer": answer, "provider": provider_name, "model": model})
    except Exception as exc:
        app.logger.exception("AI request failed")
        return jsonify({"error": f"AI request failed: {exc}"}), 502


@app.post("/api/research")
def research():
    """Research mode uses a user-configured OpenAI-compatible provider to synthesize a research brief.
    The server does not scrape arbitrary sites; the UI can provide retrieved source text/URLs from a search integration later.
    """
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()
    provider_name = (data.get("provider") or "openai").lower()
    provider = PROVIDERS.get(provider_name)
    if not provider or not problem or len(problem) > 12000:
        return jsonify({"error": "Choose a valid provider and enter a problem between 1 and 12,000 characters."}), 400
    model = (data.get("model") or provider["default_model"]).strip()
    try:
        answer = solve_one(problem, provider_name, data.get("api_key"), model, "research", data.get("research_context", ""))
        return jsonify({"answer": answer, "provider": provider_name, "model": model, "sources": data.get("sources", [])})
    except Exception as exc:
        app.logger.exception("Research request failed")
        return jsonify({"error": f"Research request failed: {exc}"}), 502


@app.post("/api/compare")
def compare():
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()
    if not problem or len(problem) > 12000:
        return jsonify({"error": "Enter a problem between 1 and 12,000 characters."}), 400
    mode = data.get("mode", "general")
    requested = data.get("providers") or []
    if not isinstance(requested, list) or not requested:
        return jsonify({"error": "Select at least one provider."}), 400
    jobs = []
    for item in requested[:3]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("provider", "")).lower()
        if name not in PROVIDERS:
            continue
        jobs.append((name, item.get("api_key", ""), (item.get("model") or PROVIDERS[name]["default_model"]).strip()))
    if not jobs:
        return jsonify({"error": "No valid providers selected."}), 400
    results = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        futures = {executor.submit(solve_one, problem, p, k, m, mode, data.get("research_context", "")): (p, m) for p, k, m in jobs}
        for future in as_completed(futures):
            p, m = futures[future]
            try:
                results.append({"provider": p, "model": m, "answer": future.result()})
            except Exception as exc:
                results.append({"provider": p, "model": m, "error": str(exc)})
    successful = [r for r in results if "answer" in r]
    if not successful:
        return jsonify({"error": "All selected providers failed.", "results": results}), 502
    judge = None
    judge_provider = data.get("judge_provider", "")
    judge_key = data.get("judge_api_key", "")
    judge_model = data.get("judge_model", "")
    if judge_provider in PROVIDERS and (judge_key or os.getenv(PROVIDERS[judge_provider]["env_key"])):
        combined = "\n\n".join(f"--- {r['provider']} / {r['model']} ---\n{r['answer']}" for r in successful)
        judge_prompt = f"""You are the final AI judge for AI Problem Solver. Compare the candidate solutions below for the user's problem.
Choose the most accurate and actionable ideas, correct weak points, and produce one superior final solution. Do not mention internal judging.

PROBLEM:\n{problem}\n\nCANDIDATES:\n{combined}"""
        try:
            response = client_for(judge_provider, judge_key).chat.completions.create(model=judge_model or PROVIDERS[judge_provider]["default_model"], messages=[{"role": "system", "content": "Be a rigorous solution evaluator and synthesizer."}, {"role": "user", "content": judge_prompt}], temperature=0.2)
            judge = {"provider": judge_provider, "model": judge_model or PROVIDERS[judge_provider]["default_model"], "answer": response.choices[0].message.content}
        except Exception as exc:
            judge = {"error": str(exc)}
    return jsonify({"results": results, "judge": judge})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
