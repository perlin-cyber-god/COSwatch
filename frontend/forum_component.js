// forum_component.js
// -------------------------------------------------------
// DROP-IN REDDIT CLONE COMPONENT
// Usage: Just add <script src="forum_component.js"></script>
// -------------------------------------------------------

c// Use the global variable if it exists, otherwise default to localhost
const API_BASE = window.API_BASE || "http://127.0.0.1:8000"; // Ensure this matches your backend

// 1. INJECT HTML & STYLES
const forumTemplate = `
<style>
    .forum-glass { background: rgba(11, 15, 25, 0.95); backdrop-filter: blur(10px); }
    .forum-scroll::-webkit-scrollbar { width: 6px; }
    .forum-scroll::-webkit-scrollbar-track { background: #05080f; }
    .forum-scroll::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    .forum-scroll::-webkit-scrollbar-thumb:hover { background: #00f3ff; }
    .loader { width: 16px; height: 16px; border: 2px solid #FFF; border-bottom-color: transparent; border-radius: 50%; display: inline-block; box-sizing: border-box; animation: rotation 1s linear infinite; }
    @keyframes rotation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>

<div id="forum-modal" class="hidden fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-4">
    <div class="w-full max-w-5xl h-[85vh] forum-glass border border-white/10 rounded-lg shadow-2xl flex overflow-hidden flex-col md:flex-row font-sans">
        
        <div class="w-full md:w-1/3 bg-[#05080f] border-r border-white/10 flex flex-col">
            <div class="p-4 border-b border-white/10 bg-white/5 flex justify-between items-center">
                <h2 class="text-cyan-400 font-mono text-xs font-bold tracking-widest">/// TRANSMISSIONS</h2>
                <button onclick="Forum.refresh()" class="text-[10px] text-slate-400 hover:text-white uppercase hover:underline">↻ SYNC</button>
            </div>
            <div id="forum-thread-list" class="flex-1 overflow-y-auto p-2 space-y-1 forum-scroll">
                <div class="text-slate-600 text-xs text-center mt-10">INITIALIZING UPLINK...</div>
            </div>
        </div>

        <div class="w-full md:w-2/3 flex flex-col relative bg-[#0b0f19]">
            <div class="h-14 border-b border-white/10 flex justify-between items-center px-6 bg-[#0f1420]">
                <div id="forum-active-title" class="text-slate-300 font-mono text-sm">SELECT TARGET</div>
                <div class="flex gap-4">
                    <button id="btn-delete-thread" onclick="Forum.deleteThread()" class="hidden text-red-500 hover:text-red-400 text-[10px] uppercase font-bold tracking-wider flex items-center gap-1">
                        DELETE SIGNAL
                    </button>
                    <button onclick="Forum.close()" class="text-slate-500 hover:text-white transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
            </div>

            <div id="forum-messages" class="flex-1 overflow-y-auto p-6 space-y-6 forum-scroll bg-[url('https://www.transparenttextures.com/patterns/stardust.png')]">
                <div class="flex h-full items-center justify-center flex-col text-slate-700 gap-3">
                    <div class="w-12 h-12 border border-slate-800 rounded-full flex items-center justify-center">
                        <div class="w-2 h-2 bg-slate-600 rounded-full animate-ping"></div>
                    </div>
                    <span class="text-xs font-mono tracking-widest">WAITING FOR SELECTION</span>
                </div>
            </div>

            <div class="p-4 border-t border-white/10 bg-[#05080f] z-10">
                <div class="flex items-center gap-3 bg-white/5 rounded px-4 py-3 border border-white/5">
                    <div class="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></div>
                    <span class="text-[10px] text-slate-400 font-mono">
                        ⚠️ <strong>READ ONLY:</strong> REPLY VIA ENCRYPTED TELEGRAM CHANNEL.
                    </span>
                </div>
            </div>
        </div>
    </div>
</div>
`;

// Inject into DOM immediately
document.body.insertAdjacentHTML('beforeend', forumTemplate);


// 2. LOGIC CONTROLLER
const Forum = {
    currentThread: null,
    interval: null,

    open: function() {
        document.getElementById('forum-modal').classList.remove('hidden');
        this.refresh();
        // Auto-refresh every 5s while open
        if (this.interval) clearInterval(this.interval);
        this.interval = setInterval(() => this.refresh(), 5000);
    },

    close: function() {
        document.getElementById('forum-modal').classList.add('hidden');
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    },

    refresh: async function() {
        const listEl = document.getElementById('forum-thread-list');
        try {
            const res = await fetch(`${API_BASE}/threads`);
            const data = await res.json();
            
            // If empty
            if (!data.threads || data.threads.length === 0) {
                listEl.innerHTML = '<div class="text-slate-600 text-xs p-4 text-center">NO ACTIVE SIGNALS</div>';
                return;
            }

            // Sort & Render
            const sorted = data.threads.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            
            listEl.innerHTML = sorted.map(t => `
                <div onclick="Forum.loadThread('${t.asteroid_name}')" 
                     class="p-3 border-b border-white/5 hover:bg-white/5 cursor-pointer transition-all group ${this.currentThread === t.asteroid_name ? 'bg-cyan-900/20 border-l-2 border-l-cyan-400' : 'border-l-2 border-l-transparent'}">
                    <div class="flex items-center justify-between mb-1">
                        <span class="font-bold text-xs text-slate-200 group-hover:text-cyan-300 font-mono">#${t.asteroid_name}</span>
                        <span class="text-[9px] text-slate-600">${new Date(t.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                    </div>
                    <div class="text-[10px] text-slate-500 truncate group-hover:text-slate-400">
                        // Secure Thread Active
                    </div>
                </div>
            `).join('');

            // Also refresh messages if a thread is open
            if (this.currentThread) this.loadThread(this.currentThread, false);

        } catch (e) {
            console.error("Forum Error", e);
        }
    },

    loadThread: async function(asteroidName, showLoading = true) {
        this.currentThread = asteroidName;
        const container = document.getElementById('forum-messages');
        const title = document.getElementById('forum-active-title');
        const delBtn = document.getElementById('btn-delete-thread');

        title.innerHTML = `<span class="text-slate-500">TARGET:</span> <span class="text-cyan-400 font-bold ml-2 tracking-wider">${asteroidName}</span>`;
        delBtn.classList.remove('hidden');

        if(showLoading) container.innerHTML = '<div class="flex h-full items-center justify-center text-cyan-500 text-xs font-mono animate-pulse">DECRYPTING...</div>';

        try {
            const res = await fetch(`${API_BASE}/debug/thread-messages/${asteroidName}`);
            const data = await res.json();
            
            if (!data.messages || data.messages.length === 0) {
                container.innerHTML = '<div class="text-slate-600 text-xs text-center mt-10 font-mono">NO CHATTER DETECTED</div>';
                return;
            }

            // Render Messages (Preserve scroll position if refreshing)
            const wasAtBottom = container.scrollHeight - container.scrollTop === container.clientHeight;
            
            container.innerHTML = data.messages.map(msg => {
                const isBot = msg.username === 'CosmicWatchBot' || msg.username === 'unknown';
                const color = isBot ? 'text-cyan-400' : 'text-purple-400';
                const name = isBot ? 'SYSTEM' : msg.username;
                
                return `
                <div class="flex flex-col gap-1 pl-3 border-l ${isBot ? 'border-cyan-500/20' : 'border-purple-500/20'} py-1">
                    <div class="flex items-baseline gap-2">
                        <span class="text-xs font-bold font-mono ${color}">${isBot ? '🤖' : '👤'} ${name}</span>
                        <span class="text-[9px] text-slate-600">${new Date(msg.created_at).toLocaleTimeString()}</span>
                    </div>
                    <div class="text-xs text-slate-300 font-sans leading-relaxed opacity-90">
                        ${msg.message}
                    </div>
                </div>`;
            }).join('');

            if(showLoading || wasAtBottom) container.scrollTop = container.scrollHeight;

        } catch (e) {
            console.error(e);
        }
    },

    createThread: async function(asteroidName) {
        try {
            const res = await fetch(`${API_BASE}/debug/create-thread/${asteroidName}`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'thread created') {
                alert(`✅ Secure Channel Opened: ${asteroidName}`);
                this.open(); // Open the forum immediately
            } else {
                alert(data.status);
            }
        } catch (e) {
            alert("Connection Failed");
        }
    },

    deleteThread: async function() {
        if (!this.currentThread) return;
        if (!confirm(`⚠ CONFIRM DELETION\n\nPurge all records for ${this.currentThread}?`)) return;

        try {
            await fetch(`${API_BASE}/thread/${this.currentThread}`, { method: 'DELETE' });
            this.currentThread = null;
            document.getElementById('forum-messages').innerHTML = '';
            document.getElementById('forum-active-title').innerText = "SELECT TARGET";
            document.getElementById('btn-delete-thread').classList.add('hidden');
            this.refresh();
        } catch (e) {
            alert("Delete failed");
        }
    }
};