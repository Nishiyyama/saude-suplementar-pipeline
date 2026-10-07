import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
PASTA_DOWNLOADS = Path("downloads")
PASTA_DOWNLOADS.mkdir(exist_ok=True)

# padrão dos arquivos: 1T2023.zip, 2T2024.zip, etc.
PADRAO = re.compile(r"^[1-4]T20\d{2}\.zip$", re.IGNORECASE)


def listar_arquivos_ano(ano: int) -> list:
    """Lê o índice HTML do ano e retorna a lista de arquivos ZIP disponíveis."""
    url = f"{BASE_URL}{ano}/"
    print(f"  Verificando {url}...")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    arquivos = []
    for link in soup.find_all("a", href=True):
        nome = link["href"]
        if PADRAO.match(nome):
            arquivos.append({"nome": nome, "url": f"{url}{nome}"})
    return arquivos


def baixar_arquivo(info: dict) -> bool:
    """Baixa um arquivo ZIP. Pula se já existir na pasta downloads/."""
    destino = PASTA_DOWNLOADS / info["nome"]
    if destino.exists():
        print(f"  Pulando {info['nome']} (já existe)")
        return False
    print(f"  Baixando {info['nome']}...")
    r = requests.get(info["url"], timeout=300, stream=True)
    r.raise_for_status()
    with open(destino, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    mb = destino.stat().st_size / 1024 / 1024
    print(f"  OK: {info['nome']} — {mb:.1f} MB")
    return True


def executar():
    anos = range(2023, 2027)  # 2023, 2024, 2025, 2026
    total_novos = 0
    for ano in anos:
        print(f"\nAno {ano}:")
        try:
            arquivos = listar_arquivos_ano(ano)
            print(f"  {len(arquivos)} arquivo(s) encontrado(s)")
            for arq in arquivos:
                if baixar_arquivo(arq):
                    total_novos += 1
        except Exception as e:
            print(f"  ERRO em {ano}: {e}")
    print(f"\nConcluido. {total_novos} arquivo(s) novo(s) baixado(s).")


if __name__ == "__main__":
    executar()
