import asyncio, socket, struct, time, json, os, redis, aiohttp
from netaddr import IPNetwork

RAKNET_MAGIC = b'\0\xff\xff\0\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx'
CONFIG = {"redis_host": "", "redis_port": 6379, "api_url": "", "api_key": ""}

async def check_server(ip, port):
    packet = b'\x01' + struct.pack('>q', int(time.time() * 1000)) + RAKNET_MAGIC + struct.pack('>q', 0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    try:
        await loop.sock_sendto(sock, packet, (ip, port))
        data = await asyncio.wait_for(loop.sock_recv(sock, 1024), timeout=1.0)
        if data.startswith(b'\x1c'):
            stats = data[35:].decode('utf-8', errors='ignore').split(';')
            return {
                "ip": str(ip), "port": int(port),
                "motd": str(stats[1]) if len(stats) > 1 else "N/A",
                "version": str(stats[3]) if len(stats) > 3 else "N/A",
                "players": str(stats[4]) if len(stats) > 4 else "0",
                "max_players": str(stats[5]) if len(stats) > 5 else "0",
                "time": time.strftime("%H:%M:%S")
            }
    except: return None
    finally: sock.close()

async def fetch_tasks(r, session):
    headers = {"X-API-Key": CONFIG["api_key"]}
    print(f"[*] Worker pronto. Escaneando...")
    
    while True:
        task = r.brpop("mc_scan_tasks", timeout=5)
        if not task: continue
        
        cidr = task[1]
        queue = asyncio.Queue(maxsize=1000)
        
        # Workers internos para o bloco atual
        async def scan_worker():
            while True:
                item = await queue.get()
                if item is None: break
                res = await check_server(item[0], item[1])
                if res:
                    try:
                        async with session.post(CONFIG["api_url"], json=res, headers=headers, timeout=5) as resp:
                            await resp.release()
                    except: pass
                queue.task_done()

        workers = [asyncio.create_task(scan_worker()) for _ in range(250)]
        
        for ip in IPNetwork(cidr):
            for port in [19132, 19133, 25565]:
                await queue.put((str(ip), port))

        await queue.join()
        for _ in range(len(workers)): await queue.put(None)
        await asyncio.gather(*workers)
        print(f"[✔] Bloco {cidr} concluído.")

async def main_async():
    r = redis.Redis(host=CONFIG["redis_host"], port=CONFIG["redis_port"], decode_responses=True)
    connector = aiohttp.TCPConnector(limit=None)
    async with aiohttp.ClientSession(connector=connector) as session:
        await fetch_tasks(r, session)

def main():
    print("=== WORKER MC-SCAN v5.3 (High Performance) ===")
    CONFIG["redis_host"] = input("IP Redis: ") or "localhost"
    master_ip = input("IP Central: ") or "localhost"
    CONFIG["api_url"] = f"http://{master_ip}:5000/api/report"
    CONFIG["api_key"] = input("Chave API: ") or "MC-SCAN-2026"
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt: pass
    except Exception as e: print(f"Erro: {e}")

if __name__ == "__main__":
    main()
