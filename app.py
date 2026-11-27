from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
import cirq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
import os
from flask_cors import CORS
from services.database import init_db
init_db()  # Create DB tables once on startup

from services.rag import ask_ama
from services.content_analysis import analyze_statement

load_dotenv()

# Ollama lokalisht - pa kredite, pa API key
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

app = Flask(__name__)
CORS(app)

# --- Serve frontend nga root ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/main.js')
def serve_main_js():
    return send_from_directory('.', 'main.js')

# --- Quantum helpers (të vjetrat, i ruajmë) ---
def text_to_amplitudes(text):
    vec = TfidfVectorizer(max_features=2).fit_transform([text]).toarray()
    if vec.shape[1] < 2:
        vec = np.pad(vec, ((0, 0), (0, 2 - vec.shape[1])), 'constant')
    return normalize(vec)[0]

def simulate_quantum(amplitudes):
    qubit = cirq.NamedQubit("q0")
    circuit = cirq.Circuit()
    circuit.append(cirq.StatePreparationChannel(amplitudes)(qubit))
    sim = cirq.Simulator()
    result = sim.simulate(circuit)
    return [float(x.real) for x in result.final_state_vector]

# --- Endpoints ---
@app.route('/api/test', methods=['GET'])
def readFile():
    return jsonify({
        'openai_response': 1,
        'quantum_result': 2
    })

@app.route('/api/process', methods=['POST'])
def process_text():
    """Chat i lirë + Quantum - tash me Ollama."""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Nuk u dërgua fusha "text" në JSON.'}), 400

        user_input = data['text']
        print("Teksti i marrë:", user_input)

        openai_resp = client.chat.completions.create(
            model="qwen2.5:7b",
            messages=[{"role": "user", "content": user_input}]
        )
        response_text = openai_resp.choices[0].message.content
        print("Ollama response:", response_text)

        amplitudes = text_to_amplitudes(response_text)
        quantum_output = simulate_quantum(amplitudes)

        return jsonify({
            'openai_response': response_text,
            'quantum_result': quantum_output
        })
    except Exception as e:
        print("Gabim gjatë përpunimit:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def ask_constitution():
    """RAG - Pyet Kushtetutën."""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Nuk u dërgua fusha "text" në JSON.'}), 400

        question = data['text']
        print("Pyetja RAG:", question)

        result = ask_ama(question)

        return jsonify({
            'question': result["question"],
            'answer': result["answer"],
            'sources': result["sources"],
        })
    except Exception as e:
        print("Gabim RAG:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analizo deklaratën - shpifje / urrejtje / kërcënim."""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Nuk u dërgua fusha "text" në JSON.'}), 400

        result = analyze_statement(data['text'])
        return jsonify(result)
    except Exception as e:
        print("Gabim Analyze:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)