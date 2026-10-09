import os
import pandas as pd
from sqlalchemy import create_engine, text, URL
from dotenv import load_dotenv

load_dotenv()

# ── MAPEAMENTO DE CONTAS ────────────────────────────────────────────────
CONTAS = {
    "contraprestacoes_efetivas": ["31"],   # Receitas com operações de assistência à saúde
    "despesas_assistenciais":    ["41"],   # Eventos indenizáveis líquidos / sinistros retidos
    "resultado_liquido":         ["6"],    # Contas de destinação/apuração de resultado
    "ativo_total":               ["1"],    # Ativo
    "passivo_total":             ["2"],    # Passivo (sem PL)
    "patrimonio_liquido":        ["25"],   # Patrimônio líquido
}

# ── PERÍODOS DO ESTUDO ──────────────────────────────────────────────────
PERIODOS = [
    (20231, 2023, 1, "1T2023", "2023-03-31"),
    (20232, 2023, 2, "2T2023", "2023-06-30"),
    (20233, 2023, 3, "3T2023", "2023-09-30"),
    (20234, 2023, 4, "4T2023", "2023-12-31"),
    (20241, 2024, 1, "1T2024", "2024-03-31"),
    (20242, 2024, 2, "2T2024", "2024-06-30"),
    (20243, 2024, 3, "3T2024", "2024-09-30"),
    (20244, 2024, 4, "4T2024", "2024-12-31"),
    (20251, 2025, 1, "1T2025", "2025-03-31"),
    (20252, 2025, 2, "2T2025", "2025-06-30"),
    (20253, 2025, 3, "3T2025", "2025-09-30"),
    (20254, 2025, 4, "4T2025", "2025-12-31"),
    (20261, 2026, 1, "1T2026", "2026-03-31"),
]

def conectar():
    url = URL.create(
        drivername="mysql+mysqlconnector",
        username=os.getenv("DB_USUARIO", "root"),
        password=os.getenv("DB_SENHA") or None,
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NOME", "saude_suplementar")
    )
    return create_engine(url)

def popular_dim_periodo(engine):
    df = pd.DataFrame(
        PERIODOS,
        columns=["id_periodo", "ano", "trimestre", "rotulo", "data_fim"]
    )
    df["data_fim"] = pd.to_datetime(df["data_fim"]).dt.date

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
        conn.execute(text("TRUNCATE TABLE dim_periodo;"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

    df.to_sql("dim_periodo", engine, if_exists="append", index=False)
    print(f"OK: {len(df)} períodos na dim_periodo")

def soma_contas(df_op: pd.DataFrame, codigos: list) -> float:
    sub = df_op[df_op["cd_conta_contabil"].isin(codigos)]
    return sub["vl_saldo_final"].sum() if not sub.empty else None

def consolidar(engine):
    print("Lendo staging...")
    df_stg = pd.read_sql("SELECT * FROM stg_demonstracao_contabil", engine)
    if df_stg.empty:
        print("AVISO: staging vazia. Rode primeiro: python pipeline/carregar_staging.py")
        return

    # Forçar a coluna código contábil a ser string
    df_stg["cd_conta_contabil"] = df_stg["cd_conta_contabil"].astype(str)

    linhas = []
    for (id_p, ano, trim, rotulo, data_fim) in PERIODOS:
        # Estratégia blindada: Cruzar diretamente pelo nome do arquivo do qual o dado foi extraído
        nome_arq = f"{rotulo}.zip"
        df_p = df_stg[df_stg["arquivo_origem"] == nome_arq]

        if df_p.empty:
            print(f"  Sem dados para {rotulo} (arquivo esperado: {nome_arq})")
            continue

        for reg in df_p["registro_ans"].unique():
            df_op = df_p[df_p["registro_ans"] == reg]
            linhas.append({
                "registro_ans": reg,
                "id_periodo": id_p,
                "contraprestacoes_efetivas": soma_contas(df_op, CONTAS["contraprestacoes_efetivas"]),
                "despesas_assistenciais": soma_contas(df_op, CONTAS["despesas_assistenciais"]),
                "resultado_liquido": soma_contas(df_op, CONTAS["resultado_liquido"]),
                "ativo_total": soma_contas(df_op, CONTAS["ativo_total"]),
                "passivo_total": soma_contas(df_op, CONTAS["passivo_total"]),
                "patrimonio_liquido": soma_contas(df_op, CONTAS["patrimonio_liquido"]),
            })

    if not linhas:
        print("AVISO: nenhum dado consolidado. Verifique os códigos em CONTAS.")
        return

    df_fato = pd.DataFrame(linhas)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fato_financeiro;"))

    df_fato.to_sql("fato_financeiro", engine, if_exists="append", index=False)
    print(f"OK: {len(df_fato)} linhas na fato_financeiro")

def executar():
    engine = conectar()
    popular_dim_periodo(engine)
    consolidar(engine)
    print("\nConsolidação concluída.")

if __name__ == "__main__":
    executar()