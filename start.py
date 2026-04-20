import os, sys, subprocess, time, socket

# Cores
G = "\033[1;32m"
R = "\033[1;31m"
Y = "\033[1;33m"
C = "\033[1;36m"
W = "\033[0m"

def clear(): os.system('clear')

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]
    except: ip = '127.0.0.1'
    finally: s.close()
    return ip

def check_deps():
    print(f"{C}[*] Verificando dependências...{W}")
    
    # Verificar Redis
    try:
        subprocess.run(["redis-cli", "--version"], check=True, capture_output=True)
    except:
        print(f"{Y}[!] Redis-cli não encontrado. Tentando instalar...{W}")
        # Detectar se o sudo está disponível
        has_sudo = os.system("command -v sudo > /dev/null 2>&1") == 0
        sudo_cmd = "sudo " if has_sudo else ""
        
        if os.system("apt --version > /dev/null 2>&1") == 0:
            os.system(f"{sudo_cmd}apt update && {sudo_cmd}apt install -y redis-server python3-pip")
        else:
            print(f"{R}[X] Gerenciador de pacotes 'apt' não encontrado. Instale o Redis manualmente.{W}")

    deps = ["redis", "aiohttp", "netaddr", "flask", "requests"]
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            print(f"[*] Instalando {dep}...")
            # Usa --user se não tiver permissão de root/sudo
            os.system(f"pip3 install {dep} --break-system-packages || pip3 install {dep} --user")

def start_redis():
    if os.system("redis-cli ping > /dev/null 2>&1") != 0:
        print(f"{Y}[!] Redis não está rodando. Iniciando manualmente...{W}")
        os.system("redis-server --daemonize yes > /dev/null 2>&1")
        time.sleep(2)
        if os.system("redis-cli ping > /dev/null 2>&1") != 0:
            print(f"{R}[X] Falha ao iniciar o Redis.{W}")
            return False
    return True

def start_master():
    my_ip = get_ip()
    clear()
    print(f"{G}=== CENTRAL MASTER v5.3 ==={W}")
    print(f"IP: {my_ip} | API: 5000 | Redis: 6379")
    
    if not start_redis(): return
    
    # Iniciar Master API
    print("[*] Iniciando API Master...")
    subprocess.Popen([sys.executable, "project/web/app.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Atualizar IPs e Popular Redis
    print("[*] Baixando lista de IPs brasileiros...")
    subprocess.run([sys.executable, "project/scanner/update_ips.py"])
    print("[*] Populando Redis...")
    subprocess.run([sys.executable, "project/scanner/producer.py"])
    
    print(f"{G}[✔] Painel Online: http://{my_ip}:5000{W}")
    time.sleep(2)
    
    # Iniciar Worker Local
    print("[*] Iniciando scanner local...")
    cmd = [sys.executable, "project/scanner/worker.py", "--master", "localhost"]
    subprocess.run(cmd)

def start_worker():
    clear()
    print(f"{C}=== MODO WORKER ==={W}")
    
    master_ip = input("IP do Servidor Master: ")
    key = input("Chave de API (Enter para padrão): ") or "MC-SCAN-2026"
    
    print("[*] Iniciando worker...")
    
    cmd = [
        sys.executable,
        "project/scanner/worker.py",
        "--master", master_ip,
        "--key", key
    ]
    
    subprocess.run(cmd)
    
def main():
    clear()
    print(f"{G}MC-SCAN DISTRIBUÍDO v5.3{W}")
    print("1. MODO MASTER (Servidor)")
    print("2. MODO WORKER (Escravo)")
    choice = input("\nEscolha: ")
    
    check_deps()
    if choice == '1': start_master()
    elif choice == '2': start_worker()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nSaindo...")
