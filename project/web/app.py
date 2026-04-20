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
    tasks = 0
    if r:
        try: tasks = r.llen('mc_scan_tasks')
        except: pass
    
    # Limpar workers inativos (45s sem sinal)
    now = time.time()
    for w in list(active_workers.keys()):
        if now - active_workers[w] > 45:
            del active_workers[w]

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
    worker_id = data.get('worker_id', 'Unknown')
    active_workers[worker_id] = time.time()
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
        print(f"[API] Novo: {host_key} ({res.get('motd', 'N/A')[:30]}...)")
        return jsonify({"status": "added"})
    return jsonify({"status": "exists"})

@app.route('/api/get_task', methods=['GET'])
def get_task():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    r = get_redis_conn()
    if not r: return jsonify({"error": "Redis offline"}), 503

    try:
        # lpop retira o item mais antigo (FIFO)
        task = r.lpop('mc_scan_tasks')
        return jsonify({"cidr": task})
    except:
        return jsonify({"error": "Redis Error"}), 500

@app.route('/api/servers')
def get_servers():
    return jsonify(cached_servers[-50:])

TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MC-SCAN | COMMAND CENTER</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg: #050608;
            --card-bg: rgba(13, 16, 23, 0.9);
            --accent: #00f2ff;
            --accent-glow: rgba(0, 242, 255, 0.4);
            --danger: #ff0055;
            --success: #00ff88;
            --warning: #ffaa00;
        }

        body { 
            background: var(--bg); 
            color: #e1e1e1; 
            font-family: 'JetBrains Mono', monospace;
            background-image: 
                linear-gradient(rgba(0, 242, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 242, 255, 0.03) 1px, transparent 1px);
            background-size: 30px 30px;
            margin: 0;
            overflow-x: hidden;
        }

        .scanline {
            width: 100%; height: 2px;
            background: rgba(0, 242, 255, 0.1);
            position: fixed; top: 0; z-index: 1000;
            pointer-events: none;
            animation: scan 8s linear infinite;
        }

        @keyframes scan { 0% { top: -100px; } 100% { top: 100%; } }

        .navbar {
            background: rgba(5, 6, 8, 0.8);
            backdrop-filter: blur(15px);
            border-bottom: 2px solid var(--accent);
            box-shadow: 0 0 20px var(--accent-glow);
            padding: 0.8rem 2rem;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid rgba(0, 242, 255, 0.1);
            border-radius: 4px;
            padding: 1.5rem;
            position: relative;
            transition: 0.3s;
            clip-path: polygon(0 0, 100% 0, 100% 85%, 90% 100%, 0 100%);
        }

        .stat-card:hover {
            border-color: var(--accent);
            box-shadow: 0 0 30px rgba(0, 242, 255, 0.2);
            transform: translateY(-2px);
        }

        .stat-value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 2.8rem;
            font-weight: 700;
            color: var(--accent);
            text-shadow: 0 0 15px var(--accent-glow);
        }

        .stat-label {
            text-transform: uppercase;
            letter-spacing: 3px;
            font-size: 0.7rem;
            color: #666;
            font-weight: 700;
        }

        .main-container {
            padding: 40px 20px;
            max-width: 1400px;
            margin: auto;
        }

        .console-box {
            background: var(--card-bg);
            border-radius: 4px;
            border-left: 4px solid var(--accent);
            padding: 20px;
            margin-top: 30px;
        }

        .search-input {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(0, 242, 255, 0.2);
            color: #fff;
            padding: 12px 20px;
            width: 100%;
            border-radius: 4px;
            margin-bottom: 20px;
            outline: none;
        }

        .search-input:focus { border-color: var(--accent); box-shadow: 0 0 10px var(--accent-glow); }

        .table { color: #aaa; font-size: 0.9rem; }
        .table thead th { border: none; color: #555; text-transform: uppercase; font-size: 0.75rem; }
        .table tbody tr { transition: 0.2s; border-bottom: 1px solid rgba(255,255,255,0.02); }
        .table tbody tr:hover { background: rgba(0, 242, 255, 0.05); color: #fff; }

        .badge-ip { 
            color: var(--accent); 
            cursor: pointer;
            padding: 4px 8px;
            border: 1px solid transparent;
        }
        .badge-ip:hover { border-color: var(--accent); background: var(--accent-glow); color: #fff; }

        .player-bar {
            height: 4px; background: rgba(255,255,255,0.05);
            width: 100px; border-radius: 2px; overflow: hidden;
            display: inline-block; vertical-align: middle;
            margin-right: 10px;
        }
        .player-progress { height: 100%; background: var(--success); box-shadow: 0 0 10px var(--success); }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: var(--accent); }
    </style>
</head>
<body>
    <div class="scanline"></div>
    
    <nav class="navbar mb-5">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1" style="color: var(--accent); font-weight: 700; letter-spacing: 4px;">
                <i class="fa-solid fa-microchip me-2"></i>MC-SCAN <span style="font-weight: 300; opacity: 0.5;">DISTRIBUTED_OS</span>
            </span>
            <div id="connection-status" class="small text-success">
                <i class="fa-solid fa-circle-nodes me-2"></i>SISTEMA_SINCRO_ATIVO
            </div>
        </div>
    </nav>

    <div class="main-container">
        <div class="row g-4 mb-5">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Discovery_Count</div>
                    <div class="stat-value" id="found">0</div>
                    <div class="progress mt-2" style="height: 2px; background: transparent;"><div class="progress-bar bg-info" style="width: 100%"></div></div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Queue_Backlog</div>
                    <div class="stat-value text-danger" id="tasks">0</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Active_Units</div>
                    <div class="stat-value text-warning" id="workers">0</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-label">Network_Load</div>
                    <div class="stat-value text-success">98.2%</div>
                </div>
            </div>
        </div>

        <div class="row g-4">
            <div class="col-lg-8">
                <div class="console-box">
                    <input type="text" id="search" class="search-input" placeholder="FILTRAR POR IP, MOTD OU VERSÃO...">
                    <div class="table-responsive">
                        <table class="table table-dark">
                            <thead>
                                <tr>
                                    <th>SOCKET_ADDRESS</th>
                                    <th>IDENTIFIER (MOTD)</th>
                                    <th>PLAYERS_LOAD</th>
                                    <th>TIME_STAMP</th>
                                </tr>
                            </thead>
                            <tbody id="body"></tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="console-box" style="height: 100%;">
                    <div class="stat-label mb-4">Discovery_Flow_Rate</div>
                    <canvas id="discoveryChart"></canvas>
                    
                    <div class="mt-5">
                        <div class="stat-label mb-3">System_Logs</div>
                        <div id="logs" style="font-size: 0.7rem; color: #555; height: 200px; overflow-y: hidden;">
                            <div>> INICIALIZANDO NÚCLEO...</div>
                            <div>> CONECTADO AO REDIS...</div>
                            <div>> AGUARDANDO WORKERS...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let lastCount = 0;
        const ctx = document.getElementById('discoveryChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['', '', '', '', '', '', '', '', '', ''],
                datasets: [{
                    data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    borderColor: '#00f2ff',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    backgroundColor: 'rgba(0, 242, 255, 0.1)'
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { display: false }, x: { display: false } }
            }
        });

        function copyIP(ip) {
            navigator.clipboard.writeText(ip);
            const log = document.getElementById('logs');
            const div = document.createElement('div');
            div.innerText = `> IP COPIADO: ${ip}`;
            div.style.color = '#00f2ff';
            log.prepend(div);
        }

        async function update() {
            try {
                const s = await (await fetch('/api/stats')).json();
                document.getElementById('found').innerText = s.total_found;
                document.getElementById('tasks').innerText = s.tasks_remaining.toLocaleString();
                document.getElementById('workers').innerText = s.workers_online;
                
                // Update Chart
                if (lastCount > 0) {
                    chart.data.datasets[0].data.shift();
                    chart.data.datasets[0].data.push(s.total_found - lastCount);
                    chart.update();
                }
                lastCount = s.total_found;

                const svs = await (await fetch('/api/servers')).json();
                const filter = document.getElementById('search').value.toLowerCase();
                
                document.getElementById('body').innerHTML = svs.reverse()
                    .filter(x => x.ip.includes(filter) || x.motd.toLowerCase().includes(filter))
                    .map(x => {
                        const p = (parseInt(x.players) / (parseInt(x.max_players) || 1)) * 100;
                        return `
                        <tr>
                            <td><span class="badge-ip" onclick="copyIP('${x.ip}:${x.port}')">${x.ip}:${x.port}</span></td>
                            <td class="small">${x.motd}</td>
                            <td>
                                <div class="player-bar"><div class="player-progress" style="width: ${p}%"></div></div>
                                <span style="font-size: 0.7rem">${x.players}/${x.max_players}</span>
                            </td>
                            <td class="text-muted small">${x.time}</td>
                        </tr>
                    `}).join('');
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
