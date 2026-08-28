(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const result = $('result');
  if (!result || $('followupChat')) return;
  const key = provider => provider ? (localStorage.getItem('aps_' + provider + '_key') || '') : '';
  let history = [];

  const style = document.createElement('style');
  style.textContent = `.chat-card{margin-top:22px}.chat-log{max-height:460px;overflow:auto;display:flex;flex-direction:column;gap:10px;margin-bottom:14px}.chat-msg{padding:13px 15px;border:1px solid #27272a;border-radius:14px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere}.chat-msg.user{background:#18181b}.chat-msg.assistant{background:#0d0d0f}.chat-role{display:block;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#a1a1aa;margin-bottom:5px}.chat-compose{display:flex;gap:10px;align-items:flex-end}.chat-compose textarea{min-height:90px;flex:1}.chat-compose button{white-space:nowrap}.chat-status{min-height:20px;margin-top:8px;color:#f87171;font-size:12px}@media(max-width:600px){.chat-compose{flex-direction:column;align-items:stretch}.chat-compose button{width:100%}}`;
  document.head.appendChild(style);

  const card = document.createElement('section');
  card.className = 'card chat-card hidden';
  card.id = 'followupChat';
  card.innerHTML = `<div class="result-head"><h2>💬 Continue the conversation</h2><button id="clearChat" class="secondary" type="button">New conversation</button></div><div id="chatLog" class="chat-log" aria-live="polite"></div><div class="chat-compose"><textarea id="chatInput" maxlength="12000" placeholder="Ask a follow-up about this solution…"></textarea><button id="chatSend" type="button">Send ↗</button></div><div id="chatStatus" class="chat-status" role="status"></div>`;
  result.parentNode.insertBefore(card, result.nextSibling);

  function addMessage(role, content) {
    const clean = String(content || '').trim();
    if (!clean) return;
    history.push({ role, content: clean });
    const row = document.createElement('div');
    row.className = 'chat-msg ' + role;
    const label = document.createElement('span');
    label.className = 'chat-role';
    label.textContent = role === 'user' ? 'You' : 'AI';
    const body = document.createElement('div');
    body.textContent = clean;
    row.append(label, body);
    $('chatLog').appendChild(row);
    $('chatLog').scrollTop = $('chatLog').scrollHeight;
  }

  function startConversation() {
    const answer = $('answer')?.innerText.trim();
    if (!answer) return;
    history = [];
    $('chatLog').innerHTML = '';
    addMessage('user', $('problem')?.value.trim() || 'Original problem');
    addMessage('assistant', answer);
    card.classList.remove('hidden');
  }

  const observer = new MutationObserver(() => {
    if (!result.classList.contains('hidden') && $('answer')?.innerText.trim() && card.classList.contains('hidden')) startConversation();
  });
  observer.observe(result, { attributes: true, subtree: true, childList: true });

  $('chatSend').addEventListener('click', async () => {
    const input = $('chatInput');
    const message = input.value.trim();
    if (!message) return;
    const provider = $('provider')?.value || 'openai';
    const model = $('model')?.value.trim() || '';
    const send = $('chatSend');
    addMessage('user', message);
    input.value = '';
    send.disabled = true;
    send.textContent = 'Thinking…';
    $('chatStatus').textContent = '';
    try {
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, history, provider, model, api_key: key(provider) }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Follow-up request failed.');
      addMessage('assistant', data.answer || 'No response returned.');
    } catch (error) {
      history.pop();
      $('chatStatus').textContent = error.message || 'Follow-up request failed.';
    } finally {
      send.disabled = false;
      send.textContent = 'Send ↗';
      input.focus();
    }
  });

  $('chatInput').addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      $('chatSend').click();
    }
  });
  $('clearChat').addEventListener('click', () => { history = []; $('chatLog').innerHTML = ''; $('chatStatus').textContent = ''; card.classList.add('hidden'); });
})();
