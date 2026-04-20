import asyncio, socket, struct, time, json, os, redis, aiohttp, argparse, random
from netaddr import IPNetwork

RAKNET_MAGIC = b'\0\xff\xff\0\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx'
CONFIG = {"redis_host": "", "redis_port": 6379, "api_url": "", "api_key": "", "worker_id": ""}

async def check_server(ip, port):
    packet = b'\x01' + struct.pack('>q', int(time.time() * 1000)) + RAKNET_MAGIC + struct.pack('>q', 0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    try:
        await loop.sock_sendto(sock, packet, (ip, port))
        # Reduzido para 0.8s para aumentar a velocidade, servidores BR respondem rápido
        data = await asyncio.wait_for(loop.sock_recv(sock, 1024), timeout=0.8)
        if data.startswith(b'\x1c'):
            stats = data[35:].decode('utf-8', errors='ignore').split(';')
            if len(stats) < 6: return None # Pacote inválido
            return {
                "ip": str(ip), "port": int(port),
                "motd": str(stats[1]) if len(stats) > 1 else "N/A",
                "version": str(stats[3]) if len(stats) > 3 else "N/A",
                "players": str(stats[4]) if len(stats) > 4 else "0",
                "max_players": str(stats[5]) if len(stats) > 5 else "0",
                "time": time.strftime("%H:%M:%S")
            }
    except (asyncio.TimeoutError, ConnectionRefusedError):
        return None
    except Exception:
        return None
    finally:
        try: sock.close()
        except: pass

async def fetch_tasks(r, session):
    headers = {"X-API-Key": CONFIG["api_key"]}
    print(f"[*] Worker {CONFIG['worker_id']} pronto. Escaneando...")
    
    # Sistema de Check-in (Heartbeat)
    async def heartbeat():
        url = CONFIG["api_url"].replace("/report", "/register")
        print(f"[*] Heartbeat iniciado para: {url}")
        while True:
            try:
                async with session.post(url, json={"worker_id": CONFIG["worker_id"]}, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        print(f"[!] Erro no Heartbeat: Status {resp.status}")
                    await resp.release()
            except Exception as e:
                print(f"[!] Erro de conexão no Heartbeat: {e}")
            await asyncio.sleep(20)

    asyncio.create_task(heartbeat())
    
    loop = asyncio.get_running_loop()
    while True:
        # Executa brpop em thread para não travar o loop
        try:
            task = await loop.run_in_executor(None, r.brpop, "mc_scan_tasks", 5)
        except:
            await asyncio.sleep(5)
            continue

        if not task: continue
        
        cidr = task[1]
        queue = asyncio.Queue(maxsize=1000)
        
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
        
        try:
            for ip in IPNetwork(cidr):
                for port in [19132, 19133, 25565]:
                    await queue.put((str(ip), port))
        except Exception as e:
            print(f"Erro no bloco {cidr}: {e}")

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
    parser = argparse.ArgumentParser(description="Worker MC-SCAN v5.3")
    parser.add_argument("--redis", help="IP do Redis", default=None)
    parser.add_argument("--master", help="IP do Master", default=None)
    parser.add_argument("--key", help="Chave API", default="MC-SCAN-2026")
    args = parser.parse_args()

    # Gerar ID único para este worker
    h = socket.gethostname()
    CONFIG["worker_id"] = f"{h}-{random.randint(100, 999)}"

    print(f"=== WORKER MC-SCAN v5.3 | ID: {CONFIG['worker_id']} ===")
    
    CONFIG["redis_host"] = args.redis or input("IP Redis (localhost): ") or "localhost"
    master_ip = args.master or input("IP Central (localhost): ") or "localhost"
    
    # Se estiver vindo do start.py, haverá uma terceira linha para a chave
    if not args.redis and not args.master:
        try:
            # Tenta ler a chave se houver algo no buffer (como o echo do start.py faz)
            import select, sys
            if select.select([sys.stdin,],[],[],0.1)[0]:
                CONFIG["api_key"] = input() or args.key
            else:
                CONFIG["api_key"] = args.key
        except:
            CONFIG["api_key"] = args.key
    else:
        CONFIG["api_key"] = args.key

    CONFIG["api_url"] = f"http://{master_ip}:5000/api/report"
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt: pass
    except Exception as e: print(f"Erro: {e}")

if __name__ == "__main__":
    main()
