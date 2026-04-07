"""Wraps Google Gemini API."""
import json
import re
import httpx
from ..config import GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL


class AIServiceError(Exception):
    pass


async def _chat(prompt: str, system: str, json_mode: bool = False) -> str:
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4},
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            r = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": GEMINI_API_KEY,
                },
            )
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts)
    except httpx.HTTPError as e:
        raise AIServiceError(f"Gemini request failed: {e}") from e


def _extract_json(text: str):
    text = text.strip()
    # try direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # strip code fences
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # find first {...} or [...]
    m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    raise AIServiceError(f"Could not parse JSON from model output: {text[:200]}")


async def generate_problems(content: str, n: int) -> list[str]:
    system = (
        "You are an expert Python coding-challenge author for the Gateway learning app. "
        "You write small, beautifully-formatted, runnable Python 3.11 exercises that "
        "teach a concept through implementation.\n\n"
        "CORE PRINCIPLE — TEACH THE CONCEPT, NOT THE EXAMPLE:\n"
        "The material contains a MAIN CONCEPT (e.g. dependency injection, decorators, context managers, "
        "generators, protocols, etc.) and INCIDENTAL EXAMPLES used to illustrate that concept "
        "(e.g. a rock-paper-scissors game, a todo list, a calculator). Your problems MUST exercise the "
        "MAIN CONCEPT. Do NOT generate problems that merely re-implement the incidental example's "
        "domain logic (e.g. 'write the rock-paper-scissors winner function') — that teaches nothing about "
        "the actual topic. Instead, build small problems where the learner must APPLY the concept itself "
        "(e.g. 'refactor this hardcoded dependency into an injected parameter', 'write a function that "
        "accepts a service via a parameter and uses it', 'implement a simple Depends-style resolver').\n"
        "Before writing, ask yourself: 'If the learner solves this, will they have practiced <main concept>, "
        "or just re-typed an example from the reading?' If the latter, pick a different problem.\n\n"
        "STRICT RULES for every problem you generate:\n"
        "1. Single self-contained Python 3.11 file. It MUST run as-is with `python file.py` "
        "   (even before the learner writes anything) — no syntax errors.\n"
        "2. ONLY the Python standard library. NEVER import third-party packages "
        "   (no numpy, pandas, requests, sqlmodel, sqlalchemy, pytest, flask, fastapi, etc). "
        "   If the material references such a library, translate the concept to pure stdlib "
        "   (e.g. simulate `Depends` with a plain higher-order function or a tiny resolver dict; "
        "   use `sqlite3` instead of SQLModel; use plain lists/dicts instead of pandas).\n"
        "3. Structure EXACTLY like this:\n"
        '   """\n'
        "   TASK:\n"
        "     <one short sentence describing the goal>\n\n"
        "   INSTRUCTIONS:\n"
        "     1. <step>\n"
        "     2. <step>\n\n"
        "   EXAMPLE:\n"
        "     >>> function_name(args)\n"
        "     expected_output\n"
        '   """\n\n'
        "   def function_name(params):\n"
        "       # TODO: implement\n"
        "       pass\n\n\n"
        '   if __name__ == "__main__":\n'
        "       # quick sanity check the learner can run\n"
        "       print(function_name(sample_input))\n"
        "4. Give the function a meaningful snake_case name. Add type hints to parameters and "
        "   return type.\n"
        "5. CRITICAL — STUB MUST BE EMPTY: The target function body must contain ONLY "
        "   `# TODO: implement` followed by a trivial placeholder return of a sensible default "
        "   (None, 0, '', [], False, {}). NEVER write the real solution, a partial solution, "
        "   the winning set/dict, an if/loop, or ANY domain logic inside the target function. "
        "   The learner must write all real logic themselves. If you catch yourself putting the "
        "   answer in the stub — delete it and leave only `return <default>`. Helper functions, "
        "   constants, and sample inputs OUTSIDE the target function are fine for scaffolding.\n"
        "6. NO markdown fences, NO prose outside the file, NO comments like 'here is problem 1'. "
        "   Only the raw Python source.\n"
        "7. Keep each problem focused on ONE concept and solvable in ~5-15 lines of real code."
    )
    prompt = (
        f"Read the material below and identify the MAIN CONCEPT it is teaching "
        f"(not the incidental example domain). Then generate exactly {n} DISTINCT Python coding "
        f"challenges that make the learner PRACTICE that main concept directly. Each challenge must "
        f"target a different facet or angle of the concept. Do NOT ask the learner to re-implement "
        f"the example domain's business logic from the reading — that does not teach the concept.\n\n"
        f"---MATERIAL---\n{content}\n---END---\n\n"
        f"First, internally identify the main concept in one sentence. Then design {n} problems that "
        f"exercise that concept in pure-stdlib Python (translate any framework-specific ideas into "
        f"plain Python equivalents). Each challenge must follow the structure rules exactly.\n\n"
        f'Return STRICT JSON in this exact shape: {{"problems": ["<full python source 1>", "<full python source 2>", ...]}}. '
        f"Each array element is the complete .py file contents as a single string. No markdown, no commentary."
    )
    raw = await _chat(prompt, system, json_mode=True)
    try:
        parsed = _extract_json(raw)
    except Exception as e:
        raise AIServiceError(f"Could not parse JSON. Raw: {raw[:800]}") from e
    problems = None
    if isinstance(parsed, list):
        problems = parsed
    elif isinstance(parsed, dict):
        # prefer "problems", else first list value
        problems = parsed.get("problems")
        if problems is None:
            for v in parsed.values():
                if isinstance(v, list):
                    problems = v
                    break
    if not isinstance(problems, list) or not problems:
        raise AIServiceError(f"Model did not return a problems list. Raw: {raw[:800]}")
    # each item may be a string or a dict with a code/source/problem field
    out: list[str] = []
    for p in problems:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            for k in ("code", "source", "problem", "text", "content"):
                if k in p and isinstance(p[k], str):
                    out.append(p[k])
                    break
            else:
                out.append(json.dumps(p, indent=2))
    if not out:
        raise AIServiceError(f"Empty problems list. Raw: {raw[:800]}")
    return out[:n]


async def grade_submission(problem_text: str, submitted_code: str) -> str:
    system = (
        "You are a friendly but rigorous Python code reviewer for the Gateway learning app. "
        "Grade the learner's submission against the problem. Respond in markdown with four "
        "sections, in this order:\n"
        "**Grade**: a single line of the form `NN / 100` where NN is an integer score. "
        "Use the full range: 90-100 fully correct and clean, 70-89 mostly correct with minor "
        "issues, 40-69 partial/buggy, 1-39 barely attempted or wrong approach, 0 empty/no "
        "attempt.\n"
        "**Verdict**: Correct / Partially correct / Incorrect with a one-line reason.\n"
        "**Strengths**: bullets of what they did well.\n"
        "**Improvements**: bullets of what to fix or add.\n"
        "Be concrete and concise."
    )
    prompt = (
        f"PROBLEM:\n{problem_text}\n\nLEARNER SUBMISSION:\n```python\n{submitted_code}\n```"
    )
    return (await _chat(prompt, system)).strip()


async def generate_hint(problem_text: str, current_code: str) -> str:
    system = (
        "You are a Socratic tutor. Give ONE short, targeted hint that nudges the learner "
        "without revealing the full answer. 2-3 sentences max."
    )
    prompt = f"PROBLEM:\n{problem_text}\n\nCURRENT CODE:\n```python\n{current_code}\n```"
    return (await _chat(prompt, system)).strip()


async def generate_report(problems_and_feedback: list[dict]) -> str:
    system = (
        "You are an educational coach. Given a learner's full session of problems and "
        "per-problem feedback, write a comprehensive markdown report with sections: "
        "**Overview**, **Score** (X/Y with one-line reasoning), **Strengths** (bullets), "
        "**Weaknesses** (bullets), **Recommended Next Steps** (bullets)."
    )
    body = "\n\n".join(
        f"### Problem {i+1}\n{item['problem']}\n\n**Submission:**\n```\n{item['code']}\n```\n\n**Feedback:**\n{item['feedback'] or '(none)'}"
        for i, item in enumerate(problems_and_feedback)
    )
    return (await _chat(body, system)).strip()
