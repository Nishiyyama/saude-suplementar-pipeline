import os
import requests
import pandas as pd
from sqlalchemy import create_engine, text
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

    # Padronizar nomes de colunas
    df.columns = [
        c.strip().lower().replace(" ", "_").replace("/", "_")
        for c in df.columns
    ]

    # 1. Recuperado o filtro do projeto para analisar apenas operadoras médico-hospitalares
    df = df[df["segmentacao_cadastral"].str.contains(
        "MEDICO-HOSPITALAR", case=False, na=False
    )].copy()

    # 2. Renomeando as colunas corretamente para evitar KeyError
    colunas_para_renomear = {
        "registro_operadora": "registro_ans",
        "modalidade_assistencia_medica": "modalidade",
    }
    df = df.rename(columns={k: v for k, v in colunas_para_renomear.items() if k in df.columns})

    # Manter só as colunas que o banco espera
    colunas_finais = ["registro_ans", "cnpj", "razao_social",
                      "nome_fantasia", "modalidade", "uf", "data_registro_ans"]
    df = df[[c for c in colunas_finais if c in df.columns]].copy()

    # 3. Correção do UserWarning da data mudando para format="mixed"
    df["data_registro_ans"] = pd.to_datetime(
        df["data_registro_ans"], format="mixed", errors="coerce"
    ).dt.date

    engine = conectar()

    # 4. Correção do Erro 1451: Desativa a verificação de chaves temporariamente,
    # limpa a tabela mantendo sua estrutura primária e reativa a verificação
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
        conn.execute(text("TRUNCATE TABLE dim_operadora;"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

    # 5. Alterado if_exists de "replace" para "append"
    df.to_sql("dim_operadora", engine, if_exists="append", index=False)
    print(f"OK: {len(df)} operadoras carregadas na dim_operadora")


if __name__ == "__main__":
    baixar_cadop()