from flask import Flask, render_template_string, jsonify, request
import json, os, threading, time, socket, struct
from collections import Counter

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SERVERS_FILE = os.path.join(PROJECT_ROOT, 'servers.json')
file_lock = threading.Lock()

cached_servers = []
# Estatísticas baseadas no espaço de IP brasileiro (MC-SCAN BR V5.3)
STATS_GLOBAL = {
    "total_ips_scanned": 85450240,
    "blocks_analyzed": 333790,
}

RAKNET_MAGIC = b'\0\xff\xff\0\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx'

def check_server(ip, port):
    packet = b'\x01' + struct.pack('>q', int(time.time() * 1000)) + RAKNET_MAGIC + struct.pack('>q', 0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.5)
    try:
        sock.sendto(packet, (ip, port))
        data, addr = sock.recvfrom(1024)
        if data.startswith(b'\x1c'):
            stats = data[35:].decode('utf-8', errors='ignore').split(';')
            if len(stats) < 6: return None
            return {
                "players": str(stats[4]),
                "max_players": str(stats[5]),
                "motd": str(stats[1])
            }
    except: return None
    finally: sock.close()

def load_data():
    global cached_servers
    if os.path.exists(SERVERS_FILE):
        try:
            with open(SERVERS_FILE, 'r') as f:
                cached_servers = json.load(f)
                for s in cached_servers:
                    if 'port' not in s: s['port'] = 19132
        except: pass

def update_loop():
    global cached_servers
    while True:
        for server in cached_servers:
            res = check_server(server['ip'], server.get('port', 19132))
            if res:
                server['players'], server['max_players'], server['motd'] = res['players'], res['max_players'], res['motd']
                server['online'] = True
            else:
                server['online'] = False
            time.sleep(0.05)
        
        with file_lock:
            try:
                with open(SERVERS_FILE, 'w') as f:
                    json.dump(cached_servers, f, indent=4)
            except: pass
        time.sleep(30)

load_data()
threading.Thread(target=update_loop, daemon=True).start()

@app.route('/api/stats')
def get_stats():
    total_players = sum(int(s.get('players', 0)) for s in cached_servers if s.get('online'))
    online_servers = sum(1 for s in cached_servers if s.get('online'))
    offline_servers = len(cached_servers) - online_servers
    
    # Contagem de portas
    ports = [s.get('port', 19132) for s in cached_servers]
    port_counts = dict(Counter(ports))
    
    return jsonify({
        "total_servers": len(cached_servers),
        "online_servers": online_servers,
        "offline_servers": offline_servers,
        "total_players": total_players,
        "ips_scanned": STATS_GLOBAL["total_ips_scanned"],
        "port_distribution": port_counts
    })

@app.route('/api/servers')
def get_servers():
    return jsonify(cached_servers)

TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MC-SCAN BR V5.3 | MONITOR MASSIVO</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&family=Orbitron:wght@400;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --matrix-green: #00ff41;
            --portal-purple: #a800ff;
            --rm-blue: #00d2ff;
            --bg-black: #050505;
            --warning-red: #ff0033;
        }

        body {
            margin: 0;
            background-color: var(--bg-black);
            color: var(--matrix-green);
            font-family: 'Fira Code', monospace;
            overflow-x: hidden;
        }

        #matrix-bg {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: -1;
            opacity: 0.15;
            pointer-events: none;
        }

        .container {
            padding: 15px;
            max-width: 1200px;
            margin: auto;
        }

        header {
            text-align: center;
            padding: 20px 10px;
            border: 2px solid var(--rm-blue);
            background: rgba(0, 210, 255, 0.05);
            box-shadow: 0 0 20px rgba(0, 210, 255, 0.2);
            margin-bottom: 20px;
            position: relative;
            clip-path: polygon(2% 0, 100% 0, 100% 80%, 98% 100%, 0 100%, 0 20%);
        }

        h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.2rem;
            margin: 0;
            color: var(--rm-blue);
            text-shadow: 0 0 10px var(--rm-blue);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: rgba(0,0,0,0.8);
            border: 1px solid var(--matrix-green);
            padding: 10px;
            text-align: center;
        }

        .stat-label { font-size: 0.55rem; color: var(--rm-blue); text-transform: uppercase; }
        .stat-value { font-size: 1rem; font-weight: bold; }

        .charts-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }

        @media (min-width: 768px) {
            .charts-container { grid-template-columns: 1fr 1fr; }
            h1 { font-size: 2rem; }
        }

        .chart-box {
            background: rgba(10, 10, 10, 0.8);
            border: 1px solid #333;
            padding: 15px;
            height: 300px;
        }

        .port-tag {
            background: rgba(168, 0, 255, 0.2);
            border: 1px solid var(--portal-purple);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.6rem;
            margin-right: 5px;
        }

        .server-card {
            background: rgba(10, 10, 10, 0.9);
            border: 1px solid #222;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 4px solid var(--portal-purple);
            text-decoration: none;
            display: block;
            cursor: pointer;
        }

        .server-card:hover {
            border-color: var(--rm-blue);
            background: rgba(0, 210, 255, 0.05);
        }

        .ip-text { color: var(--rm-blue); font-size: 0.85rem; font-weight: bold; display: flex; align-items: center; }
        .motd-text { color: #888; font-size: 0.7rem; margin: 4px 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

        .players-load {
            height: 4px; background: #111; width: 100%; margin-top: 5px;
        }
        .players-progress { height: 100%; background: var(--matrix-green); }
        
        #port-list {
            display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 15px;
        }

        .join-badge {
            background: var(--matrix-green);
            color: black;
            font-size: 0.5rem;
            padding: 2px 5px;
            margin-left: 10px;
            font-weight: 900;
        }
    </style>
</head>
<body>
    <canvas id="matrix-bg"></canvas>

    <div class="container">
        <header>
            <h1>MC-SCAN BR V5.3</h1>
            <div style="font-size: 0.6rem; opacity: 0.7;">TOTAL BR SCAN: 85.4M IPs</div>
        </header>

        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Portais</div><div class="stat-value" id="s-servers">0</div></div>
            <div class="stat-card"><div class="stat-label">Online</div><div class="stat-value" id="s-online" style="color:var(--matrix-green)">0</div></div>
            <div class="stat-card"><div class="stat-label">Offline</div><div class="stat-value" id="s-offline" style="color:var(--warning-red)">0</div></div>
            <div class="stat-card"><div class="stat-label">Viajantes</div><div class="stat-value" id="s-players">0</div></div>
        </div>

        <div id="port-list"></div>

        <div class="charts-container">
            <div class="chart-box">
                <canvas id="mainChart"></canvas>
            </div>
            <div class="chart-box">
                <canvas id="statusChart"></canvas>
            </div>
        </div>

        <div id="server-list"></div>
    </div>

    <script>
        // Matrix BG
        const canvas = document.getElementById('matrix-bg');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const letters = "010101"; const fontSize = 16; const columns = canvas.width / fontSize;
        const drops = Array(Math.floor(columns)).fill(1);
        function drawMatrix() {
            ctx.fillStyle = "rgba(0, 0, 0, 0.05)"; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = "#0F0"; ctx.font = fontSize + "px monospace";
            for (let i = 0; i < drops.length; i++) {
                const text = letters[Math.floor(Math.random() * letters.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(drawMatrix, 50);

        // Charts
        const ctx1 = document.getElementById('mainChart').getContext('2d');
        const mainChart = new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: ['IPs Analisados (M)', 'Servidores Encontrados', 'Portas Únicas'],
                datasets: [{
                    label: 'Proporção Global',
                    data: [85.4, 0, 0],
                    backgroundColor: ['rgba(0, 210, 255, 0.5)', 'rgba(0, 255, 65, 0.5)', 'rgba(168, 0, 255, 0.5)'],
                    borderColor: ['#00d2ff', '#00ff41', '#a800ff'],
                    borderWidth: 1
                }]
            },
            options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#222' } } } }
        });

        const ctx2 = document.getElementById('statusChart').getContext('2d');
        const statusChart = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['#00ff41', '#ff0033'],
                    borderColor: '#000',
                    borderWidth: 2
                }]
            },
            options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#fff' } } } }
        });

        async function update() {
            try {
                const stats = await (await fetch('/api/stats')).json();
                document.getElementById('s-servers').innerText = stats.total_servers;
                document.getElementById('s-online').innerText = stats.online_servers;
                document.getElementById('s-offline').innerText = stats.offline_servers;
                document.getElementById('s-players').innerText = stats.total_players;

                // Update Ports
                const portList = document.getElementById('port-list');
                portList.innerHTML = Object.entries(stats.port_distribution)
                    .sort((a,b) => b[1] - a[1])
                    .map(([port, count]) => `<span class="port-tag">PORT: ${port} (${count})</span>`).join('');

                // Update Charts
                mainChart.data.datasets[0].data[1] = stats.total_servers;
                mainChart.data.datasets[0].data[2] = Object.keys(stats.port_distribution).length;
                mainChart.update();

                statusChart.data.datasets[0].data = [stats.online_servers, stats.offline_servers];
                statusChart.update();

                const servers = await (await fetch('/api/servers')).json();
                const list = document.getElementById('server-list');
                list.innerHTML = servers.reverse().map(s => {
                    const p = parseInt(s.players) || 0; const m = parseInt(s.max_players) || 1;
                    const online = s.online !== false;
                    const cleanMotd = (s.motd || 'MC-SCAN-SIGNAL').replace(/§[0-9a-fklmnor]/g, '');
                    const mcLink = `minecraft://?addExternalServer=${encodeURIComponent(cleanMotd)}|${s.ip}:${s.port}`;
                    
                    return `
                        <a href="${mcLink}" class="server-card" style="border-left-color: ${online ? 'var(--portal-purple)' : 'var(--warning-red)'}">
                            <div class="ip-text">
                                ${s.ip}:${s.port} 
                                ${online ? '<span class="join-badge">CLICK TO JOIN</span>' : ''}
                            </div>
                            <div class="motd-text">${s.motd || '---'}</div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.55rem;">
                                <span>VIAJANTES: ${p}/${m}</span>
                                <span style="color: ${online ? 'var(--matrix-green)' : 'var(--warning-red)'}">${online ? 'ATIVO' : 'DESLIGADO'}</span>
                            </div>
                            <div class="players-load">
                                <div class="players-progress" style="width: ${(p/m)*100}%; background: ${online ? 'var(--matrix-green)' : '#444'}"></div>
                            </div>
                        </a>
                    `;
                }).join('');
            } catch(e){}
        }
        setInterval(update, 10000); update();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
