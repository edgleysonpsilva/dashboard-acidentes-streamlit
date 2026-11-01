"""Leitura, limpeza e agregações do dataset de acidentes da PRF"""

from pathlib import Path

import pandas as pd
import streamlit as st

CAMINHO_CSV = Path(__file__).parent / "data" / "datatran2026.csv"
ANO = 2026

DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]
MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
         7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
TIPOS_PISTA = ["Simples", "Dupla", "Múltipla"]

# feriados prolongados de 2026 (Páscoa em 05/04), do primeiro ao último dia de folga
FERIADOS = {
    "Ano-Novo": ("2026-01-01", "2026-01-04"),
    "Carnaval": ("2026-02-13", "2026-02-18"),
    "Semana Santa": ("2026-04-02", "2026-04-05"),
    "Tiradentes": ("2026-04-18", "2026-04-21"),
    "Dia do Trabalho": ("2026-04-30", "2026-05-03"),
    "Corpus Christi": ("2026-06-04", "2026-06-07"),
}
DIA_UTIL = "Dia útil"
DIA_FOLGA = "Fim de semana ou feriado"

# condições climáticas com nome próprio; as demais (Ignorado, Vento, Granizo, Neve) viram uma só
CLIMAS = ["Céu Claro", "Nublado", "Chuva", "Sol", "Garoa/Chuvisco", "Nevoeiro/Neblina"]
OUTROS_CLIMA = "Ignorado ou outros"

# ordem das categorias no gráfico da aba "Em que condições?"
ORDEM_CATEGORIAS = {
    "area_pista": [f"{area} · pista {pista.lower()}" for area in ["Rural", "Urbana"] for pista in TIPOS_PISTA],
    "fase_dia": ["Amanhecer", "Pleno dia", "Anoitecer", "Plena Noite"],
    "clima": CLIMAS + [OUTROS_CLIMA],
    "n_veiculos": ["1 veículo", "2 veículos", "3 ou mais veículos"],
}

# mínimo de acidentes para destacar uma taxa nos textos/anotações (evita ruído de amostras pequenas)
AMOSTRA_MINIMA = 30


def _nome_proprio(nomes):
    """'SAO JOSE DOS CAMPOS' -> 'Sao Jose dos Campos' (a base não tem acentos)"""
    return nomes.str.title().str.replace(r"(?<=\s)(D[aeo]s?|E)\b", lambda m: m.group(0).lower(), regex=True)


# --------- LEITURA E LIMPEZA --------------------
@st.cache_data(show_spinner="Carregando os dados da PRF...")
def carregar_dados():
    """Lê o CSV e faz a limpeza dos dados"""
    # o CSV separa com ;, usa vírgula decimal, codificação latin-1 e NA para ausentes
    df = pd.read_csv(CAMINHO_CSV, sep=";", encoding="latin-1", decimal=",", na_values=["NA"])

    # remover linhas que tenham qualquer nulo
    df = df.dropna().copy()

    # colunas derivadas usadas nos filtros e gráficos
    df["data"] = pd.to_datetime(df["data_inversa"])
    df["mes"] = df["data"].dt.month
    df["hora"] = pd.to_datetime(df["horario"], format="%H:%M:%S").dt.hour
    df["com_morte"] = (df["mortos"] > 0).astype(int)

    # agrupamentos das abas "Onde?" e "Em que condições?"
    df["rodovia"] = ("BR-" + df["br"].astype(str).str.zfill(3)).where(df["br"] > 0, "BR não informada")
    df["municipio_uf"] = _nome_proprio(df["municipio"]) + " (" + df["uf"] + ")"  # há nomes repetidos entre estados
    area = df["uso_solo"].map({"Sim": "Urbana", "Não": "Rural"})
    df["area_pista"] = area + " · pista " + df["tipo_pista"].str.lower()
    df["clima"] = df["condicao_metereologica"].where(df["condicao_metereologica"].isin(CLIMAS), OUTROS_CLIMA)
    df["n_veiculos"] = df["veiculos"].clip(upper=3).map({1: "1 veículo", 2: "2 veículos", 3: "3 ou mais veículos"})
    return df


# --------- FILTROS --------------------
def filtrar(df, meses, ufs, pistas):
    """Aplica os filtros da barra lateral. Lista vazia = sem filtro."""
    filtro = df["mes"].between(meses[0], meses[1])
    if ufs:
        filtro &= df["uf"].isin(ufs)
    if pistas:
        filtro &= df["tipo_pista"].isin(pistas)
    return df[filtro]


# --------- AGREGAÇÕES --------------------
def letalidade(df):
    """% dos acidentes com pelo menos uma morte."""
    return df["com_morte"].mean() * 100


def resumo_por(df, coluna):
    """Nº de acidentes, nº de mortos e letalidade (%) de cada categoria da coluna."""
    tabela = df.groupby(coluna).agg(
        acidentes=("com_morte", "size"),
        mortos=("mortos", "sum"),
        letalidade=("com_morte", "mean"),
    )
    tabela["letalidade"] *= 100
    return tabela


def contagem_semana_hora(df):
    """Matriz dia da semana (linhas) x hora do dia (colunas) com o nº de acidentes."""
    return (
        pd.crosstab(df["dia_semana"], df["hora"])
        .reindex(index=DIAS_SEMANA, columns=range(24), fill_value=0)
    )


def pico_semana_hora(contagem):
    """Posição (linha, coluna) da célula com mais acidentes na matriz dia x hora."""
    return divmod(int(contagem.values.argmax()), contagem.shape[1])


def mortes_por_dia(df, meses):
    """Acidentes e mortos em cada dia dos meses escolhidos, com o tipo de dia (útil ou de folga)."""
    inicio = pd.Timestamp(ANO, meses[0], 1)
    fim = pd.Timestamp(ANO, meses[1], 1) + pd.offsets.MonthEnd(0)
    dias = (
        df.groupby("data").agg(acidentes=("com_morte", "size"), mortos=("mortos", "sum"))
        .reindex(pd.date_range(inicio, fim, name="data"), fill_value=0)  # dia sem acidente conta como zero
    )
    dias["feriado"] = ""
    for nome, (primeiro, ultimo) in FERIADOS.items():
        dias.loc[primeiro:ultimo, "feriado"] = nome
    folga = (dias.index.day_of_week >= 5) | (dias["feriado"] != "")
    dias["tipo_dia"] = pd.Series(folga, index=dias.index).map({True: DIA_FOLGA, False: DIA_UTIL})
    return dias


def participacao_por(df, coluna):
    """Resumo da coluna com a % dos acidentes e a % das mortes de cada categoria, na ordem do gráfico."""
    tabela = resumo_por(df, coluna)
    tabela["pct_acidentes"] = tabela["acidentes"] / len(df) * 100
    tabela["pct_mortos"] = tabela["mortos"] / max(df["mortos"].sum(), 1) * 100  # max(..., 1): recorte sem mortes
    ordem = ORDEM_CATEGORIAS.get(coluna, [])
    return tabela.reindex([c for c in ordem if c in tabela.index] + [c for c in tabela.index if c not in ordem])
