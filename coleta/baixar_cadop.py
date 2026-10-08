import os
import requests
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def conectar():
    from urllib.parse import quote_plus
    usuario = os.getenv('DB_USUARIO', 'root')
    senha = quote_plus(os.getenv('DB_SENHA', ''))
    host = os.getenv('DB_HOST', 'localhost')
    nome = os.getenv('DB_NOME', 'saude_suplementar')

    if senha:
        url = f"mysql+mysqlconnector://{usuario}:{senha}@{host}/{nome}"
    else:
        url = f"mysql+mysqlconnector://{usuario}@{host}/{nome}"

    return create_engine(url)


def baixar_cadop():
    URL = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/Relatorio_cadop.csv"

    print("Baixando CADOP...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()

    df = pd.read_csv(pd.io.common.BytesIO(r.content), sep=";", encoding="latin-1", dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]

    df = df.rename(columns={"registro_operadora": "registro_ans"})

    colunas = ["registro_ans", "cnpj", "razao_social", "nome_fantasia", "modalidade", "uf", "data_registro_ans"]
    df = df[colunas].copy()

    df["data_registro_ans"] = pd.to_datetime(df["data_registro_ans"], dayfirst=True, errors="coerce").dt.date

    engine = conectar()
    with engine.begin() as conn:
        conn.execute(__import__("sqlalchemy").text("SET FOREIGN_KEY_CHECKS=0"))
        conn.execute(__import__("sqlalchemy").text("TRUNCATE TABLE dim_operadora"))
        conn.execute(__import__("sqlalchemy").text("SET FOREIGN_KEY_CHECKS=1"))
    df.to_sql("dim_operadora", engine, if_exists="append", index=False)
    print(f"OK: {len(df)} operadoras carregadas na dim_operadora")


if __name__ == "__main__":
    baixar_cadop()