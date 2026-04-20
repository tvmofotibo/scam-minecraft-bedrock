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

async def fetch_tasks(session):
    headers = {"X-API-Key": CONFIG["api_key"]}
    queue = asyncio.Queue(maxsize=5000)
    print(f"[*] Worker {CONFIG['worker_id']} pronto. Escaneando...")
    
    # Processador de resultados e limpeza de MOTD
    def clean_motd(m):
        return "".join(c for c in m if c.isprintable()).replace("§", "")

    async def scan_worker():
        while True:
            item = await queue.get()
            if item is None: break
            res = await check_server(item[0], item[1])
            if res:
                res["motd"] = clean_motd(res["motd"])
                try:
                    async with session.post(CONFIG["api_url"], json=res, headers=headers, timeout=5) as resp:
                        await resp.release()
                except: pass
            queue.task_done()

    # Cria os workers uma única vez (Pool)
    worker_count = 250
    workers = [asyncio.create_task(scan_worker()) for _ in range(worker_count)]
    
    # Sistema de Heartbeat
    async def heartbeat():
        url = CONFIG["api_url"].replace("/report", "/register")
        while True:
            try:
                async with session.post(url, json={"worker_id": CONFIG["worker_id"]}, headers=headers, timeout=10) as resp:
                    await resp.release()
            except: pass
            await asyncio.sleep(20)

    asyncio.create_task(heartbeat())
    
    task_url = CONFIG["api_url"].replace("/report", "/get_task")
    
    while True:
        try:
            async with session.get(task_url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    await asyncio.sleep(5); continue
                
                data = await resp.json()
                cidr = data.get("cidr")
                if not cidr:
                    await asyncio.sleep(10); continue
                    
                print(f"[*] Escaneando bloco: {cidr}")
                for ip in IPNetwork(cidr):
                    # Foca na porta padrão Bedrock para máxima velocidade
                    await queue.put((str(ip), 19132))
                
                # Aguarda o bloco atual ser processado antes de pedir outro
                await queue.join()
                print(f"[✔] Bloco {cidr} finalizado.")
                
        except Exception as e:
            print(f"[X] Erro no loop principal: {e}")
            await asyncio.sleep(10)

async def main_async():
    connector = aiohttp.TCPConnector(limit=None)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Validar conexão inicial
        stats_url = CONFIG["api_url"].replace("/report", "/stats")
        try:
            async with session.get(stats_url, timeout=10) as resp:
                if resp.status == 200:
                    print(f"[✔] Conexão com Master estabelecida.")
                else:
                    print(f"[!] Master respondeu com erro {resp.status}")
                    return
        except Exception as e:
            print(f"[X] Falha crítica ao conectar no Master em {stats_url}")
            print(f"    Verifique se o Master está rodando e se o IP está correto.")
            return

        await fetch_tasks(session)

def main():
    parser = argparse.ArgumentParser(description="Worker MC-SCAN v5.3")
    parser.add_argument("--master", help="IP do Master", default=None)
    parser.add_argument("--key", help="Chave API", default="MC-SCAN-2026")
    args = parser.parse_args()

    # Gerar ID único para este worker
    h = socket.gethostname()
    CONFIG["worker_id"] = f"{h}-{random.randint(100, 999)}"

    print(f"=== WORKER MC-SCAN v5.3 | ID: {CONFIG['worker_id']} ===")
    
    master_ip = args.master or input("IP Central (Ex: 192.168.1.10): ") or "localhost"
    CONFIG["api_key"] = args.key
    CONFIG["api_url"] = f"http://{master_ip}:5000/api/report"
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt: pass
    except Exception as e: print(f"Erro: {e}")


if __name__ == "__main__":
    main()
