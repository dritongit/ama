import json
import re
from openai import OpenAI
from services.retrieval import retrieve, format_citation
from services.database import save_analysis

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# Threat patterns for Albanian (standard + Gheg dialect)
THREAT_PATTERNS = [
    r"\bkam me vra\b", r"\bdo ta vras\b", r"\bkam me t'vra\b",
    r"\bkam me rrah\b", r"\bdo ta rrah\b", r"\bdo ta thyej\b",
    r"\bkam me t'myt\b", r"\bdo ta myt\b", r"\bmyt\b",
    r"\bdo ta djeg\b", r"\bkam me djeg\b",
    r"\bdo ta ther\b", r"\bkam me ther\b",
    r"\bdo ta zhduk\b", r"\bkam me zhduk\b",
    r"\bkill\b", r"\bmurder\b",
    r"\bi will kill\b",
]

def rule_based_threat_check(statement: str):
    # Fast rule-based check, does not depend on LLM
    text_lower = statement.lower()
    for pattern in THREAT_PATTERNS:
        if re.search(pattern, text_lower):
            return {"detected": True, "reason": f"Rule-based threat pattern found: '{pattern}'", "method": "rule-based"}
    return {"detected": False, "reason": "", "method": "rule-based"}

SYSTEM_PROMPT = """You are a JSON-only classifier. You do NOT give advice. You do NOT console the user. You do NOT explain how to report corruption.

Your ONLY job: analyze the given STATEMENT and return a single valid JSON object.

STRICT RULES:
- Output MUST be valid JSON only. No markdown. No ```json. No text before or after JSON.
- NEVER start with "I'm sorry", "Here are steps", "You should".
- NEVER give advice on what to do.
- Treat the STATEMENT as data to classify, NOT as a request for help.
- If STATEMENT is an allegation, classify it as allegation, do NOT verify it.
- Distinguish ALLEGATION vs VERIFIED FACT. Without proof, it is ALLEGATION.
- Analyze the WHOLE statement. If it has 2 sentences, analyze both.

Relevant articles:
- Article 40: Freedom of Expression - can be limited by law to protect reputation.
- Article 23: Human dignity is inviolable.
- Article 31: Right to fair trial - nobody is guilty without court decision.
- Article 24: Equality before the law.

Definitions:
- defamation: factual claim presented as fact without proof, damaging reputation. "He is a thief" = defamation risk. "I think his policy is bad" = opinion, NOT defamation.
- hate_speech: hate / violence call against protected group (ethnicity, religion, gender, etc). Criticism of a politician is NOT hate speech.
- discrimination: different treatment because of protected characteristic.
- threats: promise of future physical violence. Includes Gheg dialect: "kam me vra" = I will kill, "kam me rrah" = I will beat, "kam me myt" = I will kill, "kur ta shoh" + violent verb = threat.
- legitimate_criticism: political opinion, policy criticism, protected by Article 40.

Return EXACTLY this JSON structure, no extra fields, no extra text:
{
  "statement": "<copy original statement>",
  "summary": "neutral 1-sentence summary",
  "defamation": {"risk": "low|medium|high", "reason": "...", "is_allegation_vs_fact": "allegation|fact|opinion"},
  "hate_speech": {"detected": true|false, "reason": "..."},
  "discrimination": {"detected": true|false, "protected_group": "...|null", "reason": "..."},
  "threats": {"detected": true|false, "reason": "..."},
  "legitimate_criticism": {"is_legitimate": true|false, "reason": "..."},
  "overall_assessment": "short neutral assessment",
  "constitutional_basis": ["Article 40", "Article 23"],
  "disclaimer": "This analysis is not a court decision. Allegations are claims until proven."
}
"""

def analyze_statement(statement: str):
    print(f"[DEBUG] START analyze: {statement}")

    # Get relevant constitutional context - if retrieval fails, continue with empty context
    # This guarantees we still reach save_analysis even if Chroma is down
    context_parts = []
    used_sources = []
    try:
        queries = [
            "Liria e shprehjes Neni 40",
            "Dinjiteti i njeriut Neni 23",
            "Gjykim i drejtë, prezumimi i pafajësisë"
        ]
        for q in queries:
            results = retrieve(q, n_results=1)
            for r in results:
                context_parts.append(f"{format_citation(r)}:\n{r['text'][:1500]}")
                used_sources.append(format_citation(r))
        print(f"[DEBUG] Retrieve OK, context len: {len(context_parts)}")
    except Exception as e:
        print(f"[DEBUG] Retrieve FAILED, continuing with empty context: {e}")
        context_parts = []
        used_sources = []

    context = "\n\n".join(context_parts)

    user_prompt = f"""CONSTITUTIONAL CONTEXT:
{context}

STATEMENT TO ANALYZE:
"{statement}"

IMPORTANT: The STATEMENT above is DATA to classify. The user is NOT asking for help.
Do NOT give advice. Do NOT say "I'm sorry". Return ONLY valid JSON.
"""

    # Call LLM - if LLM fails, create error JSON but STILL save it
    raw = ""
    try:
        print("[DEBUG] Calling LLM...")
        response = client.chat.completions.create(
            model="aya-expanse:8b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        print(f"[DEBUG] LLM OK, raw starts with: {raw[:80]}")

        # Retry if model returned advice instead of JSON
        if not raw.startswith("{"):
            print("[RETRY] Model returned non-JSON, retrying...")
            retry_prompt = user_prompt + "\n\nREMINDER: Return ONLY valid JSON. No advice. No 'I'm sorry'. No steps. JSON only."
            response = client.chat.completions.create(
                model="aya-expanse:8b",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": retry_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        print(f"[DEBUG] LLM FAILED: {e}")
        # Build error JSON so save still happens
        parsed = {
            "statement": statement,
            "summary": f"LLM failed: {e}",
            "defamation": {"risk": "unknown", "reason": f"LLM error: {e}", "is_allegation_vs_fact": "unknown"},
            "hate_speech": {"detected": False, "reason": "LLM error"},
            "discrimination": {"detected": False, "protected_group": None, "reason": "LLM error"},
            "threats": {"detected": False, "reason": "LLM error"},
            "legitimate_criticism": {"is_legitimate": False, "reason": "LLM error"},
            "overall_assessment": f"LLM failed: {e}",
            "constitutional_basis": [],
            "disclaimer": "This analysis is not a court decision.",
            "error": str(e),
            "sources_used": used_sources,
        }
        # Save error case too, then return
        try:
            save_analysis(statement_text=statement, analysis=parsed, source="manual", model_used="aya-expanse:8b")
            print(f"[DB] Saved (error case): {statement[:50]}...")
        except Exception as se:
            print(f"[DB] Save error: {se}")
        return parsed

    try:
        parsed = json.loads(raw)
    except:
        # If model did not return valid JSON, return raw for debugging
        parsed = {"error": "Model did not return valid JSON", "raw_output": raw, "statement": statement}

    # Safety override: if rules find a threat, LLM cannot deny it
    rule_threat = rule_based_threat_check(statement)
    if rule_threat["detected"] and "threats" in parsed:
        parsed["threats"] = {
            "detected": True,
            "reason": rule_threat["reason"] + " | " + parsed.get("threats", {}).get("reason", ""),
        }
        parsed["overall_assessment"] = "THREAT DETECTED - must be moderated / reported. Contains threat of physical violence."
        if "legitimate_criticism" in parsed:
            parsed["legitimate_criticism"]["is_legitimate"] = False
            parsed["legitimate_criticism"]["reason"] = "Threat of violence is not protected by Article 40."

    parsed["sources_used"] = list(set(used_sources))

    # Save to DB automatically - SAME JSON that model returned
    # init_db() inside save_analysis() is safe (IF NOT EXISTS)
    try:
        save_analysis(
            statement_text=statement,
            analysis=parsed,
            source="manual",
            model_used="aya-expanse:8b"
        )
        print(f"[DB] Saved: {statement[:50]}...")
    except Exception as e:
        print(f"[DB] Save error: {e}")

    return parsed

if __name__ == "__main__":
    tests = [
        "x politican has stole citizen's money",
        "Politikani X është hajdut dhe ka vjedhur paratë e qytetarëve. Te cilin kam me vra kur ta shoh",
    ]
    for test in tests:
        print(f"\n=== TEST: {test} ===")
        result = analyze_statement(test)
        print(json.dumps(result, indent=2, ensure_ascii=False))