import asyncio, socket, struct, time, json, os
from netaddr import IPNetwork

RAKNET_MAGIC = b'\0\xff\xff\0\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVERS_FILE = os.path.join(BASE_DIR, '../servers.json')
STOP_FLAG = os.path.join(BASE_DIR, '../stop_scan.flag')

file_lock = asyncio.Lock()

async def check_server(ip, port):
    packet = b'\x01' + struct.pack('>q', int(time.time() * 1000)) + RAKNET_MAGIC + struct.pack('>q', 0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    loop = asyncio.get_event_loop()
    try:
        await loop.sock_sendto(sock, packet, (ip, port))
        data = await asyncio.wait_for(loop.sock_recv(sock, 1024), timeout=1.0)
        if data.startswith(b'\x1c'):
            stats = data[35:].decode('utf-8', errors='ignore').split(';')
            return {
                "ip": str(ip),
                "port": int(port),
                "motd": str(stats[1]) if len(stats) > 1 else "N/A",
                "version": str(stats[3]) if len(stats) > 3 else "N/A",
                "players": str(stats[4]) if len(stats) > 4 else "0",
                "max_players": str(stats[5]) if len(stats) > 5 else "0",
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    except: return None
    finally: sock.close()

async def save_result(res):
    async with file_lock:
        results = []
        if os.path.exists(SERVERS_FILE):
            try:
                with open(SERVERS_FILE, 'r') as f: results = json.load(f)
            except: results = []
        
        if not any(s['ip'] == res['ip'] and s['port'] == res['port'] for s in results):
            results.append(res)
            with open(SERVERS_FILE, 'w') as f:
                json.dump(results, f, indent=4)

async def worker(queue):
    while True:
        item = await queue.get()
        if item is None or os.path.exists(STOP_FLAG):
            queue.task_done(); break
        res = await check_server(item[0], item[1])
        if res: await save_result(res)
        queue.task_done()

async def main():
    if os.path.exists(STOP_FLAG): os.remove(STOP_FLAG)
    
    # LISTA MASSIVA DE IPS BRASILEIROS (Expandida para 32 blocos estratégicos)
    cidrs = [
        "177.54.144.0/20", "187.108.192.0/19", "45.160.124.0/22", "191.252.192.0/18",
        "131.255.102.0/23", "177.154.0.0/15", "189.126.104.0/21", "201.150.0.0/16",
        "170.81.0.0/16", "45.164.0.0/16", "177.20.0.0/16", "200.25.0.0/16",
        "177.36.0.0/16", "189.1.0.0/16", "187.1.0.0/16", "179.127.0.0/16",
        "177.135.0.0/16", "187.10.0.0/16", "189.40.0.0/16", "191.185.0.0/16",
        "200.150.0.0/16", "177.100.0.0/16", "186.200.0.0/16", "189.50.0.0/16",
        "131.255.0.0/16", "177.80.0.0/16", "45.160.0.0/15", "170.230.0.0/15",
        "201.0.0.0/16", "187.50.0.0/16", "189.100.0.0/16", "177.0.0.0/16"
    ]
    
    ports = [19132, 19133, 19134, 19135, 25565]
    
    print(f"[*] INICIANDO BUSCA GIGANTE EM {len(cidrs)} BLOCOS BRASILEIROS...")
    queue = asyncio.Queue(maxsize=30000)
    workers = [asyncio.create_task(worker(queue)) for _ in range(2500)]

    for cidr in cidrs:
        if os.path.exists(STOP_FLAG): break
        try:
            network = IPNetwork(cidr)
            print(f"[*] Varrendo agora: {cidr} ({len(network)} IPs)")
            for ip in network:
                if os.path.exists(STOP_FLAG): break
                for port in ports:
                    await queue.put((str(ip), port))
        except: continue

    await queue.join()
    for _ in range(len(workers)): await queue.put(None)
    await asyncio.gather(*workers)

if __name__ == "__main__": asyncio.run(main())
