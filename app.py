from flask import Flask, request, jsonify
from openai import OpenAI  # versioni i ri i librarisë
import numpy as np
import cirq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
import os
from flask_cors import CORS

# Vendos API key në mënyrë të sigurt (mos e lë publikisht në kod)
client = OpenAI(api_key="[SECRETKEY]")

app = Flask(__name__)
CORS(app)

# Analiza e tekstit dhe kthimi në amplituda
def text_to_amplitudes(text):
    vec = TfidfVectorizer(max_features=2).fit_transform([text]).toarray()
    if vec.shape[1] < 2:
        vec = np.pad(vec, ((0, 0), (0, 2 - vec.shape[1])), 'constant')
    return normalize(vec)[0]

# Simulimi në Cirq
def simulate_quantum(amplitudes):
    qubit = cirq.NamedQubit("q0")
    circuit = cirq.Circuit()
    circuit.append(cirq.StatePreparationChannel(amplitudes)(qubit))
    sim = cirq.Simulator()
    result = sim.simulate(circuit)
    return [float(x.real) for x in result.final_state_vector]
    # return result.final_state_vector.tolist()

# Endpoint për testim
@app.route('/api/test', methods=['GET'])
def readFile():
    return jsonify({
        'openai_response': 1,
        'quantum_result': 2
    })

# Endpoint kryesor që përpunon tekstin
@app.route('/api/process', methods=['POST'])
def process_text():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Nuk u dërgua fusha "text" në JSON.'}), 400

        user_input = data['text']
        print("Teksti i marrë:", user_input)

        # Thirrje OpenAI me SDK të ri
        openai_resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_input}]
        )
        response_text = openai_resp.choices[0].message.content
        print("OpenAI response:", response_text)

        # Përkthe tekstin në amplituda dhe ekzekuto në Cirq
        amplitudes = text_to_amplitudes(response_text)
        print("Amplitudat:", amplitudes)

        quantum_output = simulate_quantum(amplitudes)
        print("Quantum output:", quantum_output)

        return jsonify({
            'openai_response': response_text,
            'quantum_result': quantum_output
        })

    except Exception as e:
        print("Gabim gjatë përpunimit:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
