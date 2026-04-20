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
    try:
        subprocess.run(["redis-cli", "--version"], check=True, capture_output=True)
    except:
        print(f"{Y}[!] Instalando Redis Server...{W}")
        os.system("sudo apt update && sudo apt install -y redis-server python3-pip")
        os.system("sudo systemctl enable redis-server && sudo systemctl start redis-server")

    deps = ["redis", "aiohttp", "netaddr", "flask", "requests"]
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            os.system(f"pip3 install {dep} --break-system-packages")

def start_master():
    my_ip = get_ip()
    clear()
    print(f"{G}=== CENTRAL MASTER v5.3 ==={W}")
    print(f"IP: {my_ip} | API: 5000 | Redis: 6379")
    
    # Iniciar Redis
    os.system("sudo systemctl start redis-server")
    
    # Iniciar Master API
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
    cmd = f"echo 'localhost\nlocalhost\nMC-SCAN-2026' | {sys.executable} project/scanner/worker.py"
    os.system(cmd)

def start_worker():
    clear()
    print(f"{C}=== MODO WORKER ==={W}")
    master_ip = input("IP do Servidor Master: ")
    key = input("Chave de API (Enter para padrão): ") or "MC-SCAN-2026"
    cmd = f"echo '{master_ip}\n{master_ip}\n{key}' | {sys.executable} project/scanner/worker.py"
    os.system(cmd)

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
