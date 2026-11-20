import json
from openai import OpenAI
from services.retrieval import retrieve, format_citation

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

SYSTEM_PROMPT = """Ti je AMA - analizues ligjor neutral.

RREGULLA STRIKTE:
1. Mos supozo që akuzat janë të vërteta. Dalloi AKUZËN nga FAKTI I VERIFIKUAR.
2. Nëse deklarata nuk ka provë, trajtoje si PRETENDIM, jo si fakt.
3. Analizo VETËM nga KONTEKSTI kushtetues i dhënë dhe nga teksti i deklaratës.
4. Mos merr anë politike. Mos mbro, mos akuzo.
5. Kthe VETËM JSON valid, pa tekst jashtë JSON-it.

Nenet relevante për këtë analizë:
- Neni 40: Liria e Shprehjes - kushdo ka të drejtë me shpreh mendimin, por liria mundet me u kufizu me ligj për me mbrojt reputacionin e të tjerëve.
- Neni 23: Dinjiteti i Njeriut osht i pacenueshëm.
- Neni 31: Çdokush ka të drejtë për gjykim të drejtë - askush nuk osht fajtor pa vendim gjykate.
- Neni 24: Barazia para ligjit.

DEFINICIONE:
- defamation (shpifje): Pohim faktik i pavërtetuar si fakt, që e dëmton reputacionin. "Mendoj që osht i korruptum" = opinion. "Ka vjedh 1 milion" pa provë = shpifje potenciale.
- hate_speech: Thirrje për urrejtje / dhunë ndaj grupit të mbrojtur (etni, fe, gjini, etj). Kritika ndaj politikanit NUK osht hate speech.
- discrimination: Trajtim i ndryshëm për shkak të karakteristikës së mbrojtur.
- threats: Premtim për dhunë / dëm në të ardhmen.
- legitimate_criticism: Kritikë politike, opinion, kërkesë për llogari - e mbrojtur nga Neni 40.
"""

def analyze_statement(statement: str):
    # Merr kontekstin kushtetues relevant
    queries = [
        "Liria e shprehjes Neni 40",
        "Dinjiteti i njeriut Neni 23",
        "Gjykim i drejtë, prezumimi i pafajësisë"
    ]
    context_parts = []
    used_sources = []
    for q in queries:
        results = retrieve(q, n_results=1)
        for r in results:
            context_parts.append(f"{format_citation(r)}:\n{r['text'][:1500]}")
            used_sources.append(format_citation(r))

    context = "\n\n".join(context_parts)

    user_prompt = f"""KONTEKSTI KUSHTETUES:
{context}

DEKLARATA PËR ANALIZË:
"{statement}"

Analizoje dhe kthe VETËM këtë JSON:

{{
  "statement": "{statement}",
  "summary": "përmbledhje 1-2 fjali, neutrale",
  "defamation": {{
    "risk": "low | medium | high",
    "reason": "pse, me citim",
    "is_allegation_vs_fact": "a osht akuzë apo fakt i verifikum?"
  }},
  "hate_speech": {{
    "detected": true | false,
    "reason": "pse"
  }},
  "discrimination": {{
    "detected": true | false,
    "protected_group": "cili grup, ose null",
    "reason": "pse"
  }},
  "threats": {{
    "detected": true | false,
    "reason": "pse"
  }},
  "legitimate_criticism": {{
    "is_legitimate": true | false,
    "reason": "pse osht / nuk osht kritikë e mbrojtur nga Neni 40"
  }},
  "overall_assessment": "rekomandim neutral: a duhet me u moderu, me u leju, me u shënu si pretendim?",
  "constitutional_basis": ["Neni 40", "Neni 23", ...],
  "disclaimer": "Kjo analizë nuk osht vendim gjykate. Akuzat janë pretendime derisa të vërtetohen."
}}
"""

    response = client.chat.completions.create(
        model="qwen2.5:7b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()
    # Hiq ```json ... ``` nëse modeli i shton
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except:
        # Nëse modeli nuk ktheu JSON të pastër, kthe raw-in që me debug-u
        parsed = {"error": "Modeli nuk ktheu JSON valid", "raw_output": raw}

    parsed["sources_used"] = list(set(used_sources))
    return parsed

if __name__ == "__main__":
    test = "Politikani X është hajdut dhe ka vjedhur paratë e qytetarëve."
    result = analyze_statement(test)
    print(json.dumps(result, indent=2, ensure_ascii=False))