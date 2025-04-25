# AMA – Awakened Mind Alliance (ProtoHybrid v0.1)

> A proof-of-concept “hybrid” playground where human prompts, an LLM response and a
> toy quantum simulation interact through a lightweight Flask + HTML/JS stack.

---

## ✨ What Is It?

AMA is an experimental sandbox that explores  
1. **Conversational AI** – calls OpenAI’s chat completions API.  
2. **Quantum-inspired post-processing** – turns the model’s text into a pair of
   amplitudes with TF-IDF, feeds them to a *Cirq* simulator and returns the
   final state vector.  
3. **Browser chat UI** – a minimal front-end (`index.html` + `main.js`) that
   streams both the LLM reply and the quantum result to the user.  

Current code base (Python ≈ 50 %, HTML ≈ 29 %, JS ≈ 21 %) lives in three files:  
`app.py`, `index.html`, `main.js` :contentReference[oaicite:0]{index=0}  

---

## 📦 Quick start

```bash
# clone & enter
git clone https://github.com/dritongit/ama.git
cd ama

# create virtual-env (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# install backend deps
pip install flask flask-cors openai cirq numpy scikit-learn

# set your OpenAI key
export OPENAI_API_KEY="sk-..."

# run the Flask API
python app.py        # default: http://127.0.0.1:5000
