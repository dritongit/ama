import os
from dotenv import load_dotenv
from openai import OpenAI
from services.retrieval import retrieve, format_citation

load_dotenv()
#client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

SYSTEM_PROMPT = """Ti je AMA - asistent ligjor për Kushtetutën e Republikës së Kosovës.

RREGULLA STRIKTE:
1. Përgjigju VETËM nga KONTEKSTI që ta jap më poshtë. Mos përdor njohuri të jashtme.
2. Nëse konteksti nuk e përmban përgjigjen, thuaj saktë: "Nuk e gjej këtë dispozitë në kontekstin e dhënë."
3. Çdo pohim faktik duhet me pas citim në fund, në formatin: [Neni X] ose [Amendamenti Y]
4. Mos hallucino numra nenesh. Nëse nuk je i sigurt për numrin, mos e përmend.
5. Përgjigju në gjuhën e pyetjes (shqip nëse pyetja osht shqip).
6. Përgjigju shkurt, qartë, me pika nëse ka nevojë.
"""

def build_context(results):
    parts = []
    for i, r in enumerate(results, 1):
        citation = format_citation(r)
        parts.append(f"--- BURIMI {i}: {citation} ---\n{r['text']}")
    return "\n\n".join(parts)

def ask_ama(question: str, n_results: int = 4):
    results = retrieve(question, n_results=n_results)
    context = build_context(results)

    response = client.chat.completions.create(
        #model="gpt-4.1-mini",
        model="qwen2.5:7b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"KONTEKSTI:\n{context}\n\nPYETJA: {question}"}
        ],
        temperature=0.0,
    )

    answer = response.choices[0].message.content

    sources = []
    for r in results:
        sources.append({
            "citation": format_citation(r),
            "method": r["method"],
            "text_preview": r["text"][:200]
        })

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }

if __name__ == "__main__":
    tests = [
        "Qka thotë Neni 162?",
        "Kush e zgjedh Presidentin e Kosovës?",
        "A ka të drejtë çdokush për gjykim të drejtë?",
        "Qka thotë Neni 999?",
        "Qka thotë Neni 52?",
    ]
    for q in tests:
        print(f"\n{'='*70}")
        print(f"PYETJA: {q}")
        print(f"{'='*70}")
        result = ask_ama(q)
        print(f"\nPËRGJIGJA:\n{result['answer']}")
        print(f"\nBURIMET: {[s['citation'] for s in result['sources']]}")