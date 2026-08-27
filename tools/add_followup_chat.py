from pathlib import Path

APP = Path("app.py")
HTML = Path("templates/index.html")
JS = Path("static/chat.js")

CHAT_ENDPOINT = r'''

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    provider_name = (data.get("provider") or "openai").lower()
    history = data.get("history") or []
    if provider_name not in PROVIDERS or not message or len(message) > 12000:
        return jsonify({"error": "Choose a valid provider and enter a message between 1 and 12,000 characters."}), 400
    if not isinstance(history, list): history = []
    key = (data.get("api_key") or "").strip() or os.getenv(PROVIDERS[provider_name]["env_key"], "").strip()
    if not key:
        return jsonify({"error": f"No API key configured for {PROVIDERS[provider_name]['name']}."}), 400
    messages = [{"role": "system", "content": BASE_PROMPT + "\nContinue the existing conversation. Answer the user's follow-up directly and preserve useful context from earlier messages."}]
    for item in history[-10:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
            content = str(item.get("content") or "").strip()
            if content: messages.append({"role": item["role"], "content": content[:12000]})
    messages.append({"role": "user", "content": message})
    try:
        provider = PROVIDERS[provider_name]
        kwargs = {"api_key": key}
        if provider["base_url"]: kwargs["base_url"] = provider["base_url"]
        response = OpenAI(**kwargs).chat.completions.create(model=(data.get("model") or provider["default_model"]).strip(), messages=messages, temperature=0.4)
        return jsonify({"answer": response.choices[0].message.content or "No response returned."})
    except Exception:
        app.logger.exception("Follow-up chat failed")
        return jsonify({"error": "The follow-up request failed. Check your provider settings and try again."}), 502
'''

CHAT_JS = r'''(() => {
"use strict";
const $=id=>document.getElementById(id);
const key=p=>p?localStorage.getItem("aps_"+p+"_key")||"":"";
const esc=v=>String(v||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c]));
const style=document.createElement("style");style.textContent=`.chat-card{margin-top:22px}.chat-log{max-height:460px;overflow:auto;display:flex;flex-direction:column;gap:10px;margin-bottom:14px}.chat-msg{padding:12px 14px;border:1px solid #27272a;border-radius:14px;line-height:1.6;white-space:pre-wrap}.chat-msg.user{background:#18181b}.chat-msg.assistant{background:#0d0d0f}.chat-compose{display:flex;gap:10px}.chat-compose textarea{min-height:90px;flex:1}.chat-compose button{align-self:flex-end;white-space:nowrap}@media(max-width:600px){.chat-compose{flex-direction:column}.chat-compose button{width:100%}}`;document.head.appendChild(style);
const result=$("result");if(!result)return;
const card=document.createElement("section");card.className="card chat-card hidden";card.id="followupChat";card.innerHTML=`<div class="result-head"><h2>💬 Continue the conversation</h2><button id="clearChat" class="secondary" type="button">New conversation</button></div><div id="chatLog" class="chat-log"></div><div class="chat-compose"><textarea id="chatInput" maxlength="12000" placeholder="Ask a follow-up about this solution…"></textarea><button id="chatSend" type="button">Send ↗</button></div><div id="chatStatus" class="status"></div>`;result.parentNode.insertBefore(card,result.nextSibling);
let history=[];
function add(role,content){history.push({role,content});const row=document.createElement("div");row.className=`chat-msg ${role}`;row.innerHTML=`<strong>${role==="user"?"You":"AI"}</strong><br>${esc(content)}`;$("chatLog").appendChild(row);$("chatLog").scrollTop=$("chatLog").scrollHeight;}
function start(){const problem=$("problem")?.value.trim(),answer=$("answer")?.innerText.trim();if(!answer)return;history=[];add("user",problem||"Original problem");add("assistant",answer);card.classList.remove("hidden");}
const observer=new MutationObserver(()=>{if(!result.classList.contains("hidden")&&$("answer")?.innerText.trim()&&card.classList.contains("hidden"))start();});observer.observe(result,{attributes:true,subtree:true,childList:true});
$("chatSend").addEventListener("click",async()=>{const input=$("chatInput"),message=input.value.trim();if(!message)return;const provider=$("provider")?.value||"openai",model=$("model")?.value.trim()||"";add("user",message);input.value="";const send=$("chatSend");send.disabled=true;send.textContent="Thinking…";$("chatStatus").textContent="";try{const res=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message,history,provider,model,api_key:key(provider)})});const data=await res.json();if(!res.ok)throw new Error(data.error||"Follow-up failed.");add("assistant",data.answer);}catch(e){$("chatStatus").textContent=e.message;}finally{send.disabled=false;send.textContent="Send ↗";}});
$("chatInput").addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key==="Enter")$("chatSend").click();});$("clearChat").addEventListener("click",()=>{history=[];$("chatLog").innerHTML="";card.classList.add("hidden");});
})();
'''

def patch():
    app = APP.read_text(encoding="utf-8")
    if '@app.post("/api/chat")' not in app:
        marker='\nif __name__ == "__main__":'
        if marker not in app: raise SystemExit("Could not find app.py insertion point")
        APP.write_text(app.replace(marker, CHAT_ENDPOINT + marker, 1), encoding="utf-8")
    html=HTML.read_text(encoding="utf-8");tag='<script src="/static/chat.js"></script>'
    if tag not in html:
        if '</body>' not in html: raise SystemExit("Could not find HTML body end")
        HTML.write_text(html.replace('</body>',tag+'</body>',1),encoding="utf-8")
    JS.write_text(CHAT_JS,encoding="utf-8")

if __name__ == "__main__":
    patch()
    print("Follow-up chat feature installed")
