import requests
import os

URL = "https://www.ipdeny.com/ipblocks/data/countries/br.zone"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "brazil_ips.txt")

def download_ips():
    print(f"[*] Baixando lista massiva de IPs brasileiros...")
    try:
        response = requests.get(URL, timeout=15)
        if response.status_code == 200:
            cidrs = response.text.strip().split('\n')
            # Limpeza básica
            cidrs = [c.strip() for c in cidrs if "/" in c]
            
            with open(OUTPUT_FILE, "w") as f:
                f.write("\n".join(cidrs))
            
            print(f"[✔] Sucesso! {len(cidrs)} blocos de IP salvos em {OUTPUT_FILE}")
            return True
        else:
            print(f"[X] Erro ao baixar lista: Status {response.status_code}")
    except Exception as e:
        print(f"[X] Erro na conexão: {e}")
    return False

if __name__ == "__main__":
    download_ips()
