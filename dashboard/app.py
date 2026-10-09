import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, URL
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Saude Suplementar",
    layout="wide"
)


@st.cache_resource
def conectar():
    url = URL.create(
        drivername="mysql+mysqlconnector",
        username=os.getenv("DB_USUARIO", "root"),
        password=os.getenv("DB_SENHA") or None,
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NOME", "saude_suplementar")
    )
    return create_engine(url)


@st.cache_data(ttl=60)
def carregar_dados():
    engine = conectar()
    df = pd.read_sql(
        "SELECT * FROM vw_indicadores ORDER BY razao_social, ano, num_trimestre",
        engine
    )

    # ── SOLUÇÃO DO PROBLEMA 3 (ENCODING - ABORDAGEM DEFINITIVA) ───────────
    # Em vez de procurar o erro, buscamos a palavra-chave e padronizamos o nome.
    df.loc[df["razao_social"].str.contains("BRADESCO", case=False, na=False), "razao_social"] = "Bradesco Saúde S.A."
    df.loc[df["razao_social"].str.contains("PORTO SEGURO", case=False,
                                           na=False), "razao_social"] = "Porto Seguro Saúde S/A"

    # ── SOLUÇÃO DO PROBLEMA 2 (ORDEM CRONOLÓGICA) ─────────────────────────
    df["periodo_grafico"] = df["ano"].astype(str) + " - " + df["num_trimestre"].astype(str) + "T"

    return df


@st.fragment(run_every="60s")
def painel():
    df = carregar_dados()

    # sidebar com filtros
    st.sidebar.title("Filtros")
    operadoras = st.sidebar.multiselect(
        "Operadora",
        options=df["razao_social"].unique(),
        default=list(df["razao_social"].unique())
    )
    anos = st.sidebar.multiselect(
        "Ano",
        options=sorted(df["ano"].unique()),
        default=sorted(df["ano"].unique())
    )

    df_f = df[df["razao_social"].isin(operadoras) & df["ano"].isin(anos)]

    if df_f.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    # título
    st.title("🏥 Saude Suplementar — Análise Econômico-Financeira")
    st.caption("Bradesco Saúde x Porto Seguro Saúde · 1T2023 a 1T2026 · Fonte: ANS/DIOPS")

    # métricas rápidas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sinistralidade média", f"{df_f['sinistralidade_pct'].mean():.1f}%")
    c2.metric("Margem líquida média", f"{df_f['margem_liquida_pct'].mean():.1f}%")
    c3.metric("Endividamento médio", f"{df_f['endividamento_pct'].mean():.1f}%")
    c4.metric("Passivo/PL médio", f"{df_f['passivo_sobre_pl'].mean():.2f}x")

    st.divider()

    # abas com gráficos
    t1, t2, t3, t4 = st.tabs([
        "Sinistralidade", "Margem Liquida",
        "Endividamento", "Dados Completos"
    ])

    def grafico(tab, coluna, titulo, subtitulo):
        with tab:
            st.subheader(titulo)
            st.caption(subtitulo)
            pivot = df_f.pivot_table(
                index="periodo_grafico", columns="razao_social",
                values=coluna, aggfunc="mean"
            )
            st.line_chart(pivot)

    grafico(t1, "sinistralidade_pct", "Sinistralidade (%)",
            "Despesas assistenciais / Receita x 100")
    grafico(t2, "margem_liquida_pct", "Margem Liquida (%)",
            "Resultado liquido / Receita x 100")
    grafico(t3, "endividamento_pct", "Endividamento (%)",
            "Passivo total / Ativo total x 100")

    with t4:
        st.subheader("Tabela completa")
        cols = ["razao_social", "periodo_grafico", "sinistralidade_pct",
                "margem_liquida_pct", "endividamento_pct", "passivo_sobre_pl"]

        st.dataframe(
            df_f[cols].rename(columns={
                "razao_social": "Operadora",
                "periodo_grafico": "Trimestre",
                "sinistralidade_pct": "Sinistralidade (%)",
                "margem_liquida_pct": "Margem Liquida (%)",
                "endividamento_pct": "Endividamento (%)",
                "passivo_sobre_pl": "Passivo/PL (x)",
            }),
            width="stretch",
            hide_index=True
        )


painel()