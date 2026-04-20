from flask import Flask, render_template_string, jsonify, request
import json, os, threading, redis, time, socket

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SERVERS_FILE = os.path.join(PROJECT_ROOT, 'servers.json')
file_lock = threading.Lock()

cached_servers = []
known_hosts = set()
active_workers = {} # ID: timestamp
needs_save = False

def load_data():
    global cached_servers, known_hosts
    if os.path.exists(SERVERS_FILE):
        try:
            with open(SERVERS_FILE, 'r') as f:
                data = json.load(f)
                cached_servers = data
                known_hosts = {f"{s['ip']}:{s['port']}" for s in data}
        except: pass

def background_saver():
    global needs_save
    while True:
        if needs_save:
            with file_lock:
                try:
                    with open(SERVERS_FILE, 'w') as f:
                        json.dump(cached_servers, f, indent=4)
                    needs_save = False
                    print("[DISK] Dados sincronizados com sucesso.")
                except Exception as e:
                    print(f"[DISK] Erro ao salvar: {e}")
        time.sleep(10)

load_data()
threading.Thread(target=background_saver, daemon=True).start()

API_KEY = "MC-SCAN-2026"

def get_redis_conn():
    try:
        return redis.Redis(host='localhost', port=6379, decode_responses=True, socket_timeout=5)
    except:
        return None

@app.route('/api/stats')
def get_stats():
    r = get_redis_conn()
    try:
        tasks = r.llen('mc_scan_tasks') if r else 0
    except: tasks = 0
    
    # Limpar workers inativos (30s sem sinal)
    now = time.time()
    dead = [w for w, t in active_workers.items() if now - t > 30]
    for w in dead: del active_workers[w]

    return jsonify({
        "tasks_remaining": tasks, 
        "total_found": len(cached_servers),
        "workers_online": len(active_workers)
    })

@app.route('/api/register', methods=['POST'])
def register_worker():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    worker_id = data.get('worker_id', 'Desconhecido')
    ip = request.remote_addr
    active_workers[worker_id] = time.time()
    print(f"[WORKER] Sinal recebido: {worker_id} (IP: {ip})")
    return jsonify({"status": "ok"})

@app.route('/api/report', methods=['POST'])
def report_server():
    global needs_save
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    res = request.json
    if not res: return jsonify({"error": "No data"}), 400
    
    host_key = f"{res['ip']}:{res['port']}"
    if host_key not in known_hosts:
        with file_lock:
            known_hosts.add(host_key)
            res['notified'] = res.get('notified', False)
            cached_servers.append(res)
            needs_save = True 
        print(f"[API] Novo servidor encontrado: {host_key} ({res.get('motd', 'N/A')})")
        return jsonify({"status": "added"})
    return jsonify({"status": "exists"})

@app.route('/api/servers')
def get_servers():
    return jsonify(cached_servers[-50:])

TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MC-SCAN | Comando Central</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg: #0a0b0d;
            --card-bg: rgba(20, 22, 26, 0.8);
            --accent: #00f2ff;
            --accent-glow: rgba(0, 242, 255, 0.3);
            --success: #00ff88;
        }

        body { 
            background: var(--bg); 
            color: #e1e1e1; 
            font-family: 'Inter', sans-serif;
            background-image: radial-gradient(circle at 50% 50%, #1a1c22 0%, #0a0b0d 100%);
            min-height: 100vh;
        }

        .navbar {
            background: rgba(0,0,0,0.5);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 1rem 2rem;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .stat-card:hover {
            border-color: var(--accent);
            box-shadow: 0 0 20px var(--accent-glow);
            transform: translateY(-5px);
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--accent);
            text-shadow: 0 0 10px var(--accent-glow);
        }

        .stat-label {
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 0.8rem;
            color: #888;
        }

        .main-table-container {
            background: var(--card-bg);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.05);
            padding: 25px;
            margin-top: 30px;
            backdrop-filter: blur(10px);
        }

        .table { color: #ddd; vertical-align: middle; }
        .table thead th { border-bottom: 1px solid rgba(255,255,255,0.1); color: #888; font-weight: 500; }
        .table tbody td { border-bottom: 1px solid rgba(255,255,255,0.02); padding: 15px 10px; }

        .badge-ip { background: rgba(0, 242, 255, 0.1); color: var(--accent); border: 1px solid var(--accent); padding: 5px 12px; border-radius: 8px; font-family: monospace; }
        .badge-players { background: rgba(0, 255, 136, 0.1); color: var(--success); border: 1px solid var(--success); padding: 5px 12px; border-radius: 8px; }

        .pulse {
            width: 10px; height: 10px; background: var(--success); border-radius: 50%;
            display: inline-block; margin-right: 10px;
            box-shadow: 0 0 10px var(--success);
            animation: pulse-animation 2s infinite;
        }

        @keyframes pulse-animation {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
        }
    </style>
</head>
<body>
    <nav class="navbar mb-5">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1" style="color: var(--accent); font-weight: 800; letter-spacing: 2px;">
                <i class="fa-solid fa-radar fa-spin-slow me-2"></i> MC-SCAN <span style="color: #fff; font-weight: 300;">V5.3</span>
            </span>
            <div class="d-flex align-items-center">
                <span class="pulse"></span>
                <span style="font-size: 0.9rem; color: #888;">SISTEMA OPERACIONAL</span>
            </div>
        </div>
    </nav>

    <div class="container">
        <div class="row g-4">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Servidores</div>
                    <div class="stat-value" id="found">0</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Fila Redis</div>
                    <div class="stat-value" id="tasks" style="color: #ff4d4d;">0</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Workers Online</div>
                    <div class="stat-value" id="workers" style="color: #ffaa00;">0</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Status Rede</div>
                    <div class="stat-value" style="color: #00ff88;">ATIVO</div>
                </div>
            </div>
        </div>

        <div class="main-table-container">
            <table class="table table-dark">
                <thead><tr><th>ENDEREÇO</th><th>MOTD</th><th>JOGADORES</th><th>HORA</th></tr></thead>
                <tbody id="body"></tbody>
            </table>
        </div>
    </div>

    <script>
        async function update() {
            try {
                const s = await (await fetch('/api/stats')).json();
                document.getElementById('found').innerText = s.total_found;
                document.getElementById('tasks').innerText = s.tasks_remaining.toLocaleString();
                document.getElementById('workers').innerText = s.workers_online;
                
                const svs = await (await fetch('/api/servers')).json();
                document.getElementById('body').innerHTML = svs.reverse().map(x => `
                    <tr>
                        <td><span class="badge-ip">${x.ip}:${x.port}</span></td>
                        <td>${x.motd}</td>
                        <td><span class="badge-players">${x.players}/${x.max_players}</span></td>
                        <td class="text-muted small">${x.time}</td>
                    </tr>
                `).join('');
            } catch(e) {}
        }
        setInterval(update, 2000); update();
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
