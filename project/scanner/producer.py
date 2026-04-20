import redis
import os
from netaddr import IPNetwork

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_QUEUE = 'mc_scan_tasks'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IPS_FILE = os.path.join(BASE_DIR, "brazil_ips.txt")

def populate():
    if not os.path.exists(IPS_FILE):
        print(f"[X] Arquivo {IPS_FILE} não encontrado! Rode o update_ips.py primeiro.")
        return

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    print("[*] Limpando fila anterior...")
    r.delete(REDIS_QUEUE)
    
    count = 0
    print(f"[*] Lendo blocos de {IPS_FILE} e distribuindo no Redis...")
    
    with open(IPS_FILE, "r") as f:
        cidrs = [line.strip() for line in f if line.strip()]

    for cidr in cidrs:
        try:
            net = IPNetwork(cidr)
            # Quebrar blocos grandes para melhor distribuição entre workers
            if net.prefixlen < 24:
                # Limitamos a quebra para não gerar milhões de subnets de uma vez se for muito grande
                # Mas para o Brasil, /24 é um tamanho excelente para workers
                for sub in net.subnet(24):
                    r.lpush(REDIS_QUEUE, str(sub))
                    count += 1
            else:
                r.lpush(REDIS_QUEUE, cidr)
                count += 1
        except: continue
    
    print(f"[✔] Fila pronta! {count} tarefas (/24) adicionadas ao Redis.")

if __name__ == "__main__":
    populate()
