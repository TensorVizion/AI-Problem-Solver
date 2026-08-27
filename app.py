import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BASE_URL = os.getenv("OPENAI_BASE_URL")

client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL or None)

SYSTEM_PROMPT = """You are AI Problem Solver, a practical assistant that helps users solve real-world problems.
Analyze the user's problem, identify the key issue, give a clear solution, and provide actionable steps.
If useful, include assumptions, alternatives, examples, or a short checklist. Be concise but useful.
Do not pretend to have performed actions you cannot perform."""


@app.get("/")
def index():
    return render_template("index.html", configured=client is not None, model=MODEL)


@app.post("/api/solve")
def solve():
    if client is None:
        return jsonify({"error": "AI is not configured. Add OPENAI_API_KEY to your environment."}), 503

    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or "").strip()

    if not problem:
        return jsonify({"error": "Please describe the problem you want to solve."}), 400
    if len(problem) > 12000:
        return jsonify({"error": "Problem description is too long (12,000 character limit)."}), 400

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": problem},
            ],
            temperature=0.4,
        )
        answer = response.choices[0].message.content or "No solution was returned."
        return jsonify({"answer": answer})
    except Exception as exc:
        app.logger.exception("AI request failed")
        return jsonify({"error": f"AI request failed: {exc}"}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
