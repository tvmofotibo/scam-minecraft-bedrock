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
    
    # Em vez de deletar, vamos ver o que já tem
    print("[*] Verificando estado da fila no Redis...")
    # Usar um set temporário para verificar duplicatas na fila atual (operação pesada se fila for enorme)
    # Para simplificar e ser rápido: só adicionamos se a fila estiver vazia ou se o usuário forçar.
    
    current_size = r.llen(REDIS_QUEUE)
    if current_size > 0:
        print(f"[!] A fila já contém {current_size} tarefas. Deseja adicionar mais blocos? (s/n)")
        # Em scripts automatizados, podemos assumir 'n' ou usar flags. 
        # Vou mudar para: Adicionar apenas o que não está lá.
    
    count = 0
    print(f"[*] Lendo blocos de {IPS_FILE}...")
    
    with open(IPS_FILE, "r") as f:
        cidrs = [line.strip() for line in f if line.strip()]

    # Para evitar testar a mesma coisa, poderíamos usar um SET no Redis para "blocos_concluidos"
    # Mas o BRPOP já garante que 2 workers não peguem o mesmo bloco.
    
    for cidr in cidrs:
        try:
            net = IPNetwork(cidr)
            if net.prefixlen < 24:
                for sub in net.subnet(24):
                    r.lpush(REDIS_QUEUE, str(sub))
                    count += 1
            else:
                r.lpush(REDIS_QUEUE, cidr)
                count += 1
        except: continue
    
    print(f"[✔] Produtor finalizado. {count} novas tarefas adicionadas.")

if __name__ == "__main__":
    populate()
