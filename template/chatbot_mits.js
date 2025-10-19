// ----------------------
// CONFIG
// ----------------------
const WEBHOOK_URL = "http://localhost:5678/webhook/762830e1-8bfa-4adb-b690-e22b687210da";

// ----------------------
// Simple UI helpers
// ----------------------
const messagesEl = document.getElementById('messages');
const historyList = document.getElementById('historyList');
const inputEl = document.getElementById('input');
const fileInput = document.getElementById('fileInput');
const attachedFileEl = document.getElementById('attachedFile');

let conversation = loadConversation();

function loadConversation(){
  try{
    const raw = localStorage.getItem('college_chat_history_v1');
    return raw ? JSON.parse(raw) : [{role:'assistant',text:'Hi — I can help with lecture summaries, study plans, quizzes, code explanations, and referencing. Try: "Summarize these notes" or "Create a 4-week study plan for Data Structures."'}];
  }catch(e){
    return [{role:'assistant',text:'Hi — I can help with lecture summaries, study plans, quizzes, code explanations, and referencing.'}];
  }
}

function saveConversation(){
  localStorage.setItem('college_chat_history_v1', JSON.stringify(conversation));
  renderHistory();
}

function addMessage(role,text,meta){
  conversation.push({id:Date.now()+Math.random(),role,text,meta});
  saveConversation();
  renderMessages();
}

function renderMessages(){
  messagesEl.innerHTML = '';
  for(const msg of conversation){
    const wrapper = document.createElement('div');
    wrapper.className = 'msg';
    const avatar = document.createElement('div');
    avatar.className = 'avatar ' + (msg.role === 'user' ? 'user' : 'assistant');
    avatar.textContent = msg.role === 'user' ? 'YOU' : 'CB';
    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (msg.role === 'user' ? 'user' : 'assistant');
    bubble.innerHTML = sanitize(msg.text).replace(/\n/g,'<br>');
    const meta = document.createElement('div');
    meta.className = 'meta';
    const time = new Date(msg.id).toLocaleString();
    meta.textContent = `${msg.role === 'user' ? 'You' : 'Assistant'} • ${time}`;
    const col = document.createElement('div');
    col.style.display='flex';col.style.flexDirection='column';
    col.appendChild(bubble); col.appendChild(meta);
    if(msg.role === 'assistant'){
      wrapper.appendChild(avatar); wrapper.appendChild(col);
    } else {
      wrapper.style.justifyContent='flex-end';
      wrapper.appendChild(col); wrapper.appendChild(avatar);
    }
    messagesEl.appendChild(wrapper);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
  renderHistory();
}

function renderHistory(){
  historyList.innerHTML = '';
  for(const item of conversation.slice().reverse().slice(0,30)){
    const el = document.createElement('div');
    el.className = 'item';
    el.textContent = truncate(item.text,120);
    el.onclick = ()=>{ inputEl.value = item.text; inputEl.focus(); };
    historyList.appendChild(el);
  }
}

function truncate(s,n){ return s.length>n ? s.slice(0,n-1)+'…' : s; }
function sanitize(s){ const div = document.createElement('div'); div.textContent = s; return div.innerHTML; }

// ----------------------
// Start UI
// ----------------------
renderMessages();

// Quick action buttons (sidebar)
document.querySelectorAll('[data-action]').forEach(btn=>{
  btn.addEventListener('click', ()=> {
    const action = btn.getAttribute('data-action');
    if(action==='summarize'){ inputEl.value = 'Please summarize the following notes:'; inputEl.focus(); }
    if(action==='study-plan'){ inputEl.value = 'Create a 4-week study plan for: [Subject/Topics], with study hours per day and priorities.'; inputEl.focus(); }
    if(action==='quiz'){ inputEl.value = 'Generate a 10-question multiple choice quiz on: [Topic], include answers and short explanations.'; inputEl.focus(); }
    if(action==='explain-code'){ inputEl.value = 'Explain this code line-by-line and suggest improvements: ```paste code here```'; inputEl.focus(); }
  });
});

// file attach
let attachedFile = null;
fileInput.addEventListener('change', ()=>{
  const f = fileInput.files[0];
  attachedFile = f || null;
  attachedFileEl.textContent = f ? f.name : '';
});

// composer: send message
document.getElementById('composer').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const text = inputEl.value.trim();
  if(!text && !attachedFile) return;
  addMessage('user', text || ('[file] ' + (attachedFile ? attachedFile.name : '')));
  inputEl.value = ''; attachedFileEl.textContent = ''; fileInput.value = ''; // clear
  const payload = makePayload('message', text, attachedFile);
  await postToWebhook(payload, attachedFile);
});

// Smart quick button (tries to infer helpful action)
document.getElementById('quickActionBtn').addEventListener('click', ()=>{
  const t = inputEl.value.toLowerCase();
  if(t.includes('summar') || t.includes('summary')) inputEl.value = 'Please summarize the following: ' + inputEl.value;
  else if(t.includes('plan') || t.includes('study plan')) inputEl.value = 'Create a study plan: ' + inputEl.value;
  else inputEl.value = 'Make a clear answer for: ' + inputEl.value;
  inputEl.focus();
});

// clear / export
document.getElementById('clearBtn').addEventListener('click', ()=>{
  if(!confirm('Clear local conversation?')) return;
  conversation = [];
  saveConversation();
  renderMessages();
});
document.getElementById('exportBtn').addEventListener('click', ()=>{
  const blob = new Blob([JSON.stringify(conversation, null, 2)], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download='college_chat_export.json'; a.click();
  URL.revokeObjectURL(url);
});

// ----------------------
// Webhook + network
// ----------------------
function makePayload(kind, text, file){
  return {
    kind: kind,
    message: text || '',
    attachedFileName: file ? file.name : null,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    source: 'college_chat_frontend'
  };
}

async function postToWebhook(jsonPayload, file){
  showAssistantTyping();
  try{
    // If there's a file, send as FormData; else send JSON
    let resp;
    if(file){
      const fd = new FormData();
      fd.append('payload', JSON.stringify(jsonPayload));
      fd.append('file', file);
      resp = await fetch(WEBHOOK_URL, { method:'POST', body: fd });
    } else {
      resp = await fetch(WEBHOOK_URL, {
        method:'POST',
        headers:{ 'Content-Type': 'application/json' },
        body: JSON.stringify(jsonPayload)
      });
    }

    if(!resp.ok){
      const txt = await resp.text().catch(()=>null);
      addMessage('assistant', `⚠️ Webhook returned HTTP ${resp.status}. ${txt ? 'Response: '+txt : ''}`);
      return;
    }

    // Try parse JSON, fallback to text
    let data;
    const ct = resp.headers.get('content-type') || '';
    if(ct.includes('application/json')){
      data = await resp.json();
      // If webhook returns a field 'reply' or 'message' show it
      const reply = data.reply || data.message || JSON.stringify(data);
      addMessage('assistant', String(reply));
    } else {
      const text = await resp.text();
      const reply = text || 'Webhook received your message — no reply body returned.';
      addMessage('assistant', String(reply));
    }
  } catch (err){
    console.error(err);
    addMessage('assistant', `❌ Network error: ${err.message || err}`);
    addMessage('assistant', 'Possible causes: the webhook server is not running, CORS blocked the request, or the URL is incorrect.');
  } finally {
    hideAssistantTyping();
  }
}

// ----------------------
// Typing indicator
// ----------------------
let typingId = null;
function showAssistantTyping(){
  if(typingId) return;
  typingId = Date.now();
  addMessage('assistant','⏳ Thinking...');
}
function hideAssistantTyping(){
  if(!typingId) return;
  // remove last auto typing message if it's the placeholder
  const last = conversation[conversation.length-1];
  if(last && last.text === '⏳ Thinking...'){
    conversation.splice(conversation.length-1,1);
  }
  typingId = null;
  saveConversation();
  renderMessages();
}

// ----------------------
// Helpful: initial checks on load
// ----------------------
(function initialNote(){
  // show a short note about webhook reachability
  const note = `Note: This page will POST messages to your webhook at ${WEBHOOK_URL}. If you're running n8n locally, ensure it allows CORS or serve this page from the same machine origin.`;
  addMessage('assistant', note);
})();

// Accessibility & keyboard shortcuts
window.addEventListener('keydown', (e)=>{
  if((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==='k'){ e.preventDefault(); inputEl.focus(); }
  if((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==='enter'){ e.preventDefault(); document.getElementById('composer').dispatchEvent(new Event('submit')); }
});
