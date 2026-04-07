"""Wraps a local Ollama instance running gpt-oss:120b."""
import json
import re
import httpx
from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL


class AIServiceError(Exception):
    pass


async def _chat(prompt: str, system: str, json_mode: bool = False) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.4},
    }
    if json_mode:
        payload["format"] = "json"
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            r = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("message", {}).get("content", "")
    except httpx.HTTPError as e:
        raise AIServiceError(f"Ollama request failed: {e}") from e


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
        "STRICT RULES for every problem you generate:\n"
        "1. Single self-contained Python 3.11 file. It MUST run as-is with `python file.py` "
        "   (even before the learner writes anything) — no syntax errors.\n"
        "2. ONLY the Python standard library. NEVER import third-party packages "
        "   (no numpy, pandas, requests, sqlmodel, sqlalchemy, pytest, flask, etc). "
        "   If the material references such a library, translate the concept to pure stdlib "
        "   (e.g. use `sqlite3` instead of SQLModel, or plain lists/dicts instead of pandas).\n"
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
        "5. The `pass` stub must return a sensible default (e.g. None, 0, '', []) so the file "
        "   runs without NameError.\n"
        "6. NO markdown fences, NO prose outside the file, NO comments like 'here is problem 1'. "
        "   Only the raw Python source.\n"
        "7. Keep each problem focused on ONE concept and solvable in ~5-15 lines of real code."
    )
    prompt = (
        f"Generate exactly {n} DISTINCT Python coding challenges from this material. "
        f"Each challenge must follow the structure rules exactly.\n\n"
        f"---MATERIAL---\n{content}\n---END---\n\n"
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
        "Grade the learner's submission against the problem. Respond in markdown with three "
        "sections: **Verdict** (Correct / Partially correct / Incorrect with one-line reason), "
        "**Strengths** (bullets of what they did well), **Improvements** (bullets of what to fix "
        "or add). Be concrete and concise."
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
