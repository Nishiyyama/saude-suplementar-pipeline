import os
import requests
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def conectar():
    senha = os.getenv('DB_SENHA', '')
    if senha:
        url = f"mysql+mysqlconnector://{os.getenv('DB_USUARIO')}:{senha}@{os.getenv('DB_HOST')}/{os.getenv('DB_NOME')}"
    else:
        url = f"mysql+mysqlconnector://{os.getenv('DB_USUARIO')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NOME')}"
    return create_engine(url)

def baixar_cadop():
    URL = (
        "https://dadosabertos.ans.gov.br/FTP/PDA/"
        "operadoras_de_plano_de_saude_ativas/Relatorio_cadop.csv"
    )
    print("Baixando CADOP...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()

    df = pd.read_csv(
        pd.io.common.BytesIO(r.content),
        sep=";", encoding="latin-1", dtype=str
    )
    df.columns = [
        c.strip().lower().replace(" ",