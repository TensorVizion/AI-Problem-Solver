import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
PROVIDERS = {
    "openai": {"name": "OpenAI", "base_url": None, "env_key": "OPENAI_API_KEY", "default_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")},
    "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "env_key": "OPENROUTER_API_KEY", "default_model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")},
    "nvidia": {"name": "NVIDIA NIM", "base_url": "https://integrate.api.nvidia.com/v1", "env_key": "NVIDIA_NIM_API_KEY", "default_model": os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.1-8b-instruct")},
}
MODEL_CATALOG = {
    "openai": ["gpt-4o-mini"],
    "openrouter": ["openai/gpt-4o-mini", "openrouter/free"],
    "nvidia": ["meta/llama-3.1-8b-instruct", "qwen/qwen3-32b", "qwen/qwen3-coder-next", "zai-org/glm-5", "minimax-ai/minimax-m25"],
}
for provider_name, provider in PROVIDERS.items():
    env_name = provider["env_key"].replace("_API_KEY", "_MODELS")
    configured = [m.strip() for m in os.getenv(env_name, "").split(",") if m.strip()]
    MODEL_CATALOG[provider_name] = list(dict.fromkeys([provider["default_model"]] + configured + MODEL_CATALOG.get(provider_name, [])))

MODES = {
    "general": "Solve the problem practically and clearly.",
    "coding": "Act as a senior software engineer. Diagnose the issue, identify the root cause, propose an implementation-ready fix, and include code and verification steps when useful.",
    "business": "Act as a pragmatic business strategist. Focus on ROI, feasibility, risks, and concrete next steps.",
    "marketing": "Act as a performance marketing expert. Focus on audience, positioning, conversion, testing, and measurable actions.",
    "math": "Act as a meticulous mathematician. Show necessary reasoning and verify calculations.",
    "research": "Act as a research analyst. Build conclusions from supplied sources, distinguish facts from inference, and identify uncertainty.",
    "writing": "Act as an expert editor and writing coach. Diagnose the writing problem and give a strong, usable solution.",
    "troubleshooting": "Act as a technical troubleshooter. Prioritize likely root causes, diagnostic checks, and fixes from safest to most invasive.",
}
BASE_PROMPT = """You are AI Problem Solver, a practical assistant that helps users solve real-world problems.
Analyze the user's problem, identify the key issue, give a clear recommended solution, and provide actionable steps.
When useful, include assumptions, alternatives, tradeoffs, examples, and a concise checklist.
Do not pretend to have performed actions you cannot perform. Be accurate and practical."""
CODING_PROMPT = """For coding mode, structure the response with these sections when applicable:
1. Diagnosis — what is happening.
2. Root Cause — why it is happening.
3. Fix — the recommended implementation.
4. Code — complete, copy-paste-ready code or the smallest relevant patch.
5. Verification — commands/tests to confirm the fix.
6. Notes — edge cases, security concerns, or tradeoffs.
Respect the user's language/framework and existing architecture. Do not invent files, APIs, test results, or environment details."""


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
    if mode == "coding":
        prompt += "\n\n" + CODING_PROMPT
    if context:
        prompt += "\n\nResearch sources/context. Treat these as source material and cite source numbers where relevant:\n" + context
    response = client_for(provider_name, key).chat.completions.create(
        model=model or provider["default_model"],
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": problem}],
        temperature=0.4,
    )
    return response.choices[0].message.content or "No solution was returned."


def web_research(query, max_sources=5):
    headers = {"User-Agent": "AI-Problem-Solver/1.0"}
    search_url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    r = requests.get(search_url, headers=headers, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    candidates = []
    for result in soup.select(".result"):
        a = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        if href.startswith("//"):
            href = "https:" + href
        candidates.append({"title": a.get_text(" ", strip=True), "url": href, "snippet": snippet.get_text(" ", strip=True) if snippet else ""})
        if len(candidates) >= max_sources:
            break
    sources = []
    for item in candidates:
        try:
            page = requests.get(item["url"], headers=headers, timeout=8, allow_redirects=True)
            if "text/html" not in page.headers.get("content-type", ""):
                text = item["snippet"]
            else:
                psoup = BeautifulSoup(page.text, "html.parser")
                for tag in psoup(["script", "style", "noscript", "svg", "nav", "footer"]):
                    tag.decompose()
                text = re.sub(r"\s+", " ", " ".join(psoup.stripped_strings))[:5000]
            sources.append({"title": item["title"], "url": page.url, "snippet": item["snippet"], "content": text})
        except Exception:
            sources.append({**item, "content": item["snippet"]})
    return sources


def format_sources(sources):
    return "\n\n".join(f"[Source {i}] {s['title']}\nURL: {s['url']}\nExcerpt: {s['content']}" for i, s in enumerate(sources, 1))


@app.get("/")
def index():
    return render_template("index.html", providers=PROVIDERS, modes=MODES)

@app.get("/api/providers")
def providers():
    return jsonify({k: {"name": v["name"], "default_model": v["default_model"]} for k, v in PROVIDERS.items()})

@app.get("/api/models")
def models():
    provider_name = (request.args.get("provider") or "openai").lower()
    if provider_name not in PROVIDERS:
        return jsonify({"error": "Unknown provider."}), 400
    return jsonify({
        "provider": provider_name,
        "default_model": PROVIDERS[provider_name]["default_model"],
        "models": [{"id": model, "label": model} for model in MODEL_CATALOG[provider_name]],
    })

@app.post("/api/solve")
def solve():
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()
    provider_name = (data.get("provider") or "openai").lower()
    if provider_name not in PROVIDERS or not problem or len(problem) > 12000:
        return jsonify({"error": "Choose a valid provider and enter a problem between 1 and 12,000 characters."}), 400
    model = (data.get("model") or PROVIDERS[provider_name]["default_model"]).strip()
    try:
        answer = solve_one(problem, provider_name, data.get("api_key"), model, data.get("mode", "general"), data.get("research_context", ""))
        return jsonify({"answer": answer, "provider": provider_name, "model": model})
    except Exception as exc:
        app.logger.exception("AI request failed")
        return jsonify({"error": f"AI request failed: {exc}"}), 502

@app.post("/api/research")
def research():
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()
    provider_name = (data.get("provider") or "openai").lower()
    if provider_name not in PROVIDERS or not problem or len(problem) > 12000:
        return jsonify({"error": "Choose a valid provider and enter a problem between 1 and 12,000 characters."}), 400
    model = (data.get("model") or PROVIDERS[provider_name]["default_model"]).strip()
    try:
        sources = web_research(problem, max_sources=5)
        context = format_sources(sources)
        extra = (data.get("research_context") or "").strip()
        if extra:
            context += "\n\n[User-provided research context]\n" + extra[:20000]
        answer = solve_one(problem, provider_name, data.get("api_key"), model, "research", context)
        return jsonify({"answer": answer, "provider": provider_name, "model": model, "sources": [{"title": s["title"], "url": s["url"], "snippet": s.get("snippet", "")} for s in sources]})
    except Exception as exc:
        app.logger.exception("Research request failed")
        return jsonify({"error": "Research request failed. Check your API key and research query, then try again."}), 502

@app.post("/api/compare")
def compare():
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()
    if not problem or len(problem) > 12000:
        return jsonify({"error": "Enter a problem between 1 and 12,000 characters."}), 400
    requested = data.get("providers") or []
    if not isinstance(requested, list) or not requested:
        return jsonify({"error": "Select at least one provider."}), 400
    jobs = []
    for item in requested[:3]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("provider", "")).lower()
        if name in PROVIDERS:
            jobs.append((name, item.get("api_key", ""), (item.get("model") or PROVIDERS[name]["default_model"]).strip()))
    if not jobs:
        return jsonify({"error": "No valid providers selected."}), 400
    results = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        futures = {executor.submit(solve_one, problem, p, k, m, data.get("mode", "general"), data.get("research_context", "")): (p, m) for p, k, m in jobs}
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
    jp = data.get("judge_provider", "")
    jk = data.get("judge_api_key", "")
    jm = data.get("judge_model", "")
    if jp in PROVIDERS and (jk or os.getenv(PROVIDERS[jp]["env_key"])):
        combined = "\n\n".join(f"--- {r['provider']} / {r['model']} ---\n{r['answer']}" for r in successful)
        try:
            response = client_for(jp, jk).chat.completions.create(model=jm or PROVIDERS[jp]["default_model"], messages=[{"role": "system", "content": "Be a rigorous solution evaluator and synthesizer."}, {"role": "user", "content": f"Compare these candidate solutions and produce one superior final solution.\n\nPROBLEM:\n{problem}\n\nCANDIDATES:\n{combined}"}], temperature=0.2)
            judge = {"provider": jp, "model": jm or PROVIDERS[jp]["default_model"], "answer": response.choices[0].message.content}
        except Exception as exc:
            judge = {"error": str(exc)}
    return jsonify({"results": results, "judge": judge})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    provider_name = (data.get("provider") or "openai").lower()
    history = data.get("history") or []
    if provider_name not in PROVIDERS or not message or len(message) > 12000:
        return jsonify({"error": "Choose a valid provider and enter a message between 1 and 12,000 characters."}), 400
    if not isinstance(history, list): history = []
    key = (data.get("api_key") or "").strip() or os.getenv(PROVIDERS[provider_name]["env_key"], "").strip()
    if not key:
        return jsonify({"error": f"No API key configured for {PROVIDERS[provider_name]['name']}."}), 400
    messages = [{"role": "system", "content": BASE_PROMPT + "\nContinue the existing conversation. Answer the user's follow-up directly and preserve useful context from earlier messages."}]
    for item in history[-10:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
            content = str(item.get("content") or "").strip()
            if content: messages.append({"role": item["role"], "content": content[:12000]})
    messages.append({"role": "user", "content": message})
    try:
        provider = PROVIDERS[provider_name]
        kwargs = {"api_key": key}
        if provider["base_url"]: kwargs["base_url"] = provider["base_url"]
        response = OpenAI(**kwargs).chat.completions.create(model=(data.get("model") or provider["default_model"]).strip(), messages=messages, temperature=0.4)
        return jsonify({"answer": response.choices[0].message.content or "No response returned."})
    except Exception:
        app.logger.exception("Follow-up chat failed")
        return jsonify({"error": "The follow-up request failed. Check your provider settings and try again."}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
