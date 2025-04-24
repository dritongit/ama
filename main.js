async function sendMessage() {
  const userInput = document.getElementById('userInput').value;
  if (!userInput.trim()) return;

  appendMessage(userInput, 'user');
  document.getElementById('userInput').value = '';

  try {
    const res = await fetch('http://127.0.0.1:5000/api/process', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ text: userInput })
    });

    const data = await res.json();
    const openAIResponse = data.openai_response;
    const quantumResult = data.quantum_result;

    appendMessage(openAIResponse, 'bot');
    appendMessage(`Q Result: ${JSON.stringify(quantumResult)}`, 'bot');

  } catch (err) {
    console.error('Gabim:', err);
    appendMessage("Gabim në server...", 'bot');
  }
}

function appendMessage(content, sender) {
  const chat = document.getElementById('chat');
  const message = document.createElement('div');
  message.className = `message ${sender}`;
  message.innerText = content;
  chat.appendChild(message);
  chat.scrollTop = chat.scrollHeight;
}
