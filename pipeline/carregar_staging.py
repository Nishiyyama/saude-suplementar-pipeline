import os
import zipfile
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

PASTA_DOWNLOADS = Path("downloads")

# ANS 005711 = Bradesco Saúde  |  ANS 000582 = Porto Seguro Saúde
OPERADORAS = ["005711", "000582"]

def conectar():
    senha = os.getenv('DB_SENHA', '')
    if senha:
        url = f"mysql+mysqlconnector://{os.getenv('DB_USUARIO')}:{senha}@{os.getenv('DB_HOST')}/{os.getenv('DB_NOME')}"
    else:
        url = f"mysql+mysqlconnector://{os.getenv('DB_USUARIO')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NOME')}"
    return create_engine(url)

def ja_carregado(engine, nome_arquivo: str) -> bool:
    """Verifica se o arquivo já foi carregado na staging."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM stg_demonstracao_contabil"
                 " WHERE arquivo_origem = :nome"),
            {"nome": nome_arquivo}
        )
        return result.scalar() > 0

def ler_zip(caminho: Path) -> pd.DataFrame:
    """Abre o ZIP e lê todos os CSV dentro dele."""
    with zipfile.ZipFile(caminho) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            raise ValueError(f"Nenhum CSV em {caminho.name}")
        frames = []
        for nome_csv in csvs:
            with z.open(nome_csv) as f:
                df = pd.read_csv(
                    f, sep=";", encoding="latin-1",
                    dtype=str, on_bad_lines="skip"
                )
                frames.append(df)
        return pd.concat(frames, ignore_index=True)

def padronizar(df: pd.DataFrame, nome_arquivo: str) -> pd.DataFrame:
    """Limpa, filtra e formata os dados antes de carregar."""
    df.columns = [c.strip().upper() for c in df.columns]

    # Ampliado o mapeamento para cobrir possíveis variações do nome na base da ANS
    mapa = {
        "DATA":              "data_ref",
        "REG_ANS":           "registro_ans",
        "CD_CONTA_CONTABIL": "cd_conta_contabil",
        "DESCRICAO_CONTA":   "descricao",
        "DESCRIÇÃO_CONTA":   "descricao",
        "DESCRICAO":         "descricao",
        "DESCRIÇÃO":         "descricao",
        "VL_SALDO_INICIAL":  "vl_saldo_inicial",
        "VL_SALDO_FINAL":    "vl_saldo_final",
    }
    df = df.rename(columns={k: v for k, v in mapa.items() if k in df.columns})

    # CRÍTICO: Garantir que a coluna 'descricao' também seja criada (como nula) caso a ANS não a envie
    for col in ["data_ref", "registro_ans", "cd_conta_contabil",
                "descricao", "vl_saldo_inicial", "vl_saldo_final"]:
        if col not in df.columns:
            df[col] = None

    # filtrar somente as duas operadoras do estudo
    df["registro_ans"] = df["registro_ans"].astype(str).str.strip().str.zfill(6)
    df = df[df["registro_ans"].isin(OPERADORAS)].copy()

    # converter tipos
    df["data_ref"] = pd.to_datetime(
        df["data_ref"], format="%Y%m%d", errors="coerce"
    ).dt.date

    for col in ["vl_saldo_inicial", "vl_saldo_final"]:
        df[col] = (
            df[col].astype(str)
                   .str.replace(".", "", regex=False)
                   .str.replace(",", ".", regex=False)
                   .pipe(pd.to_numeric, errors="coerce")
        )

    df["arquivo_origem"] = nome_arquivo
    return df[["data_ref", "registro_ans", "cd_conta_contabil",
               "descricao", "vl_saldo_inicial", "vl_saldo_final",
               "arquivo_origem"]]

def executar():
    engine = conectar()
    zips = sorted(PASTA_DOWNLOADS.glob("*.zip"))
    if not zips:
        print("AVISO: Nenhum ZIP em downloads/")
        print("Execute primeiro: python coleta/scraper_trimestres.py")
        return
    for caminho in zips:
        nome = caminho.name
        if ja_carregado(engine, nome):
            print(f"Pulando {nome} (ja no banco)")
            continue
        print(f"Processando {nome}...")
        try:
            df = ler_zip(caminho)
            df = padronizar(df, nome)
            if df.empty:
                print(f"  Sem registros das operadoras em {nome}")
                continue
            df.to_sql("stg_demonstracao_contabil", engine,
                      if_exists="append", index=False, chunksize=1000)
            print(f"  OK: {len(df)} registros carregados")
        except Exception as e:
            print(f"  ERRO em {nome}: {e}")
    print("\nStaging concluida.")

if __name__ == "__main__":
    executar()