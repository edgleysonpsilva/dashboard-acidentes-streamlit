"""Dashboard - Acidentes nas Rodovias Federais (PRF, jan-ago/2026).

Atividade - Análise e Visualização de Dados (CESAR School)
Aluno: Edgleyson Pereira da Silva

Para rodar localmente:  streamlit run app.py
"""

from datetime import date
from pathlib import Path

import streamlit as st

from dados import (AMOSTRA_MINIMA, DIA_FOLGA, DIA_UTIL, FERIADOS, MESES, TIPOS_PISTA, carregar_dados,
                   contagem_semana_hora, filtrar, letalidade, mortes_por_dia, participacao_por,
                   pico_semana_hora, resumo_por)
from graficos import (METRICAS, barras_mortes_dia, barras_participacao, barras_ranking, fmt_dec, fmt_int,
                      fmt_pct, heatmap_semana_hora, linha_letalidade_hora, mapa_densidade)

BANNER_IMG = Path(__file__).parent / "assets" / "banner.png"
CONFIG_PLOTLY = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}
FONTE_URL = "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf"

# rótulo mostrado no widget -> coluna usada no agrupamento
AGRUPAMENTOS = {"Estado": "uf", "Rodovia": "rodovia", "Município": "municipio_uf"}
CONDICOES = {"Área e pista": "area_pista", "Fase do dia": "fase_dia", "Clima": "clima",
             "Nº de veículos": "n_veiculos"}
NOTAS_CONDICOES = {
    "Área e pista": "Área urbana ou rural segundo o campo uso_solo da PRF.",
    "Fase do dia": "Fase do dia anotada no boletim pela luz natural, não pelo horário.",
    "Clima": "“Ignorado ou outros” junta Ignorado, Vento, Granizo e Neve.",
    "Nº de veículos": "Acidentes com mais veículos envolvem mais pessoas, o que por si só aumenta as mortes.",
}

st.set_page_config(
    page_title="Acidentes nas Rodovias Federais | PRF 2026",
    page_icon="🚧",
    layout="wide",
)


def juntar(nomes):
    """['A', 'B', 'C'] -> 'A, B e C'"""
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def mostrar_insights(frases):
    """Uma caixa de insight por aba: uma frase ou uma lista com várias."""
    if len(frases) == 1:
        st.info(f"**Insight:** {frases[0]}")
    elif frases:
        st.info("**Insights**\n\n" + "\n".join(f"- {frase}" for frase in frases))


def limpar_filtros():
    """Troca as chaves dos widgets da barra lateral, que então voltam aos valores padrão."""
    st.session_state.versao_filtros += 1


# --------- LEITURA DO DATASET --------------------
df = carregar_dados()
LETALIDADE_BRASIL = letalidade(df)

# --------- WIDGETS DE FILTRO -------------------
st.session_state.setdefault("versao_filtros", 0)
versao = st.session_state.versao_filtros

with st.sidebar:
    st.header("Filtros")

    meses = sorted(int(m) for m in df["mes"].unique())
    periodo = st.select_slider(
        "Período",
        options=meses,
        value=(meses[0], meses[-1]),
        format_func=MESES.get,  # mostra "Jan", "Fev"... no lugar de 1, 2...
        key=f"periodo_{versao}",
    )
    ufs = st.multiselect(
        "Estados (UF)",
        options=sorted(df["uf"].unique()),
        placeholder="Todos os estados",
        key=f"ufs_{versao}",
    )
    pistas = st.pills(
        "Tipo de pista",
        options=TIPOS_PISTA,
        selection_mode="multi",
        default=TIPOS_PISTA,
        key=f"pistas_{versao}",
    )
    if not pistas:
        st.caption("Nenhum tipo de pista marcado: mostrando todos.")

    sem_filtros = periodo == (meses[0], meses[-1]) and not ufs and set(pistas) == set(TIPOS_PISTA)
    st.button("Limpar filtros", icon=":material/filter_alt_off:", type="tertiary", on_click=limpar_filtros,
              disabled=sem_filtros)

    st.divider()
    st.caption(f"**Fonte:** [PRF – Dados Abertos]({FONTE_URL}), acidentes de 01/01 a 31/08/2026.")
    st.caption("**Aluno:** Edgleyson Pereira da Silva  \nAnálise e Visualização de Dados – CESAR School")

dff = filtrar(df, periodo, ufs, pistas)

# --------- CABEÇALHO --------------------
st.image(str(BANNER_IMG))  # figura fixa que ilustra o dashboard

st.markdown(
    "Painel construído a partir de análises exploratórias e explanatórias: **o horário com mais acidentes "
    "não é o mais letal**, **os tipos de acidente mais frequentes não são os que mais matam** e **as pistas "
    "simples em área rural concentram mais da metade das mortes**. "
    "Use os filtros da barra lateral para explorar os dados."
)

texto_periodo = MESES[periodo[0]] if periodo[0] == periodo[1] else f"{MESES[periodo[0]]}–{MESES[periodo[1]]}"
texto_ufs = ", ".join(ufs) if ufs else "todos os estados"
texto_pistas = ", ".join(pistas).lower() if pistas and len(pistas) < len(TIPOS_PISTA) else "todas"
st.caption(f"Recorte atual: {texto_periodo}/2026 · {texto_ufs} · pistas: {texto_pistas}")

if dff.empty:
    st.warning("Nenhum acidente encontrado para os filtros escolhidos. Ajuste a barra lateral.")
    st.stop()

# --------- INDICADORES --------------------
media = letalidade(dff)
diferenca = media - LETALIDADE_BRASIL
total_mortos = dff["mortos"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Acidentes", fmt_int(len(dff)), border=True)
col2.metric("Mortos", fmt_int(total_mortos), border=True)
col3.metric("Feridos", fmt_int(dff["feridos"].sum()), border=True, help="Feridos leves + graves.")
col4.metric(
    "Letalidade",
    fmt_pct(media),
    # sem filtros o recorte é o próprio Brasil, então não há diferença para mostrar
    delta=f"{diferenca:+.1f}".replace(".", ",") + " p.p. vs. média nacional" if abs(diferenca) >= 0.05 else None,
    delta_color="inverse",
    help=f"% dos acidentes com pelo menos uma morte. Média nacional no período todo: {fmt_pct(LETALIDADE_BRASIL)}.",
    border=True,
)

if len(dff) < 500:
    st.info("Poucos acidentes neste recorte: as taxas por hora, tipo e estado podem oscilar bastante.")

aba_quando, aba_como, aba_onde, aba_condicoes, aba_dados = st.tabs(
    ["🕒 Quando?", "🚗 Como?", "📍 Onde?", "🛣️ Em que condições?", "📋 Dados"]
)

# --------- ABA 1: QUANDO? --------------------
with aba_quando:
    contagem = contagem_semana_hora(dff)
    por_hora = resumo_por(dff, "hora")
    dias = mortes_por_dia(dff, periodo)

    st.subheader("Volume de acidentes por dia da semana e hora")
    st.caption("Cada célula é o nº de acidentes naquele dia e hora. O contorno vermelho marca o pico.")
    st.plotly_chart(heatmap_semana_hora(contagem), config=CONFIG_PLOTLY)

    st.subheader("% dos acidentes que terminam em morte, por hora")
    st.caption("A faixa azul marca a madrugada (0h–5h). Passe o mouse para ver o nº de acidentes de cada hora.")
    st.plotly_chart(linha_letalidade_hora(por_hora, media), config=CONFIG_PLOTLY)

    st.subheader("Mortes por dia ao longo do período")
    if total_mortos == 0:
        st.caption("Nenhuma morte neste recorte.")
    else:
        st.caption("Barras escuras: sábados, domingos e feriados prolongados. "
                   "As linhas tracejadas marcam a média de cada grupo.")
        st.plotly_chart(barras_mortes_dia(dias), config=CONFIG_PLOTLY)

    insights = []
    linha, coluna = pico_semana_hora(contagem)
    texto = (
        f"O pico de volume é **{contagem.index[linha]} às {coluna}h** "
        f"({fmt_int(contagem.iat[linha, coluna])} acidentes)"
    )
    # só compara a letalidade entre horas com amostra suficiente
    horas_confiaveis = por_hora[por_hora["acidentes"] >= AMOSTRA_MINIMA]
    if total_mortos == 0:
        texto += ". Nenhum acidente deste recorte teve morte."
    elif horas_confiaveis.empty:
        texto += ". O recorte é pequeno demais para comparar a letalidade entre as horas."
    else:
        hora_letal = horas_confiaveis["letalidade"].idxmax()
        comparacao = (f"{fmt_pct(por_hora.loc[hora_letal, 'letalidade'])} dos acidentes têm morte, "
                      f"contra {fmt_pct(media)} na média do recorte.")
        if hora_letal == coluna:
            texto += f", e {hora_letal}h também é a hora mais letal: {comparacao}"
        else:
            texto += f", mas a hora mais letal é **{hora_letal}h**: {comparacao}"
    insights.append(texto)

    # dias de folga x dias úteis, só com mortes suficientes para comparar
    medias = dias.groupby("tipo_dia")["mortos"].mean()
    if total_mortos >= AMOSTRA_MINIMA and medias.get(DIA_UTIL, 0) > 0 and DIA_FOLGA in medias:
        variacao = medias[DIA_FOLGA] / medias[DIA_UTIL] - 1
        folgas = "fins de semana e feriados prolongados" if (dias["feriado"] != "").any() else "fins de semana"
        if round(variacao, 2):
            diferenca_dias = f"{abs(variacao):.0%} {'a mais' if variacao > 0 else 'a menos'} que"
        else:
            diferenca_dias = "o mesmo que"
        insights.append(
            f"Nos {folgas} morrem em média **{fmt_dec(medias[DIA_FOLGA])} pessoas por dia**, "
            f"{diferenca_dias} nos dias úteis ({fmt_dec(medias[DIA_UTIL])})."
        )
    mostrar_insights(insights)

# --------- ABA 2: COMO? --------------------
with aba_como:
    col_metrica, col_minimo = st.columns([3, 2])
    metrica = METRICAS[col_metrica.radio("Ordenar por", list(METRICAS), horizontal=True, key="metrica_como")]
    minimo = col_minimo.slider(
        "Esconder categorias com menos de N acidentes",
        min_value=0, max_value=200, value=10, step=5,
        help="Categorias raras distorcem a letalidade (ex.: 9 casos e 6 mortes = 66,7%).",
    )

    tipos = resumo_por(dff, "tipo_acidente")
    tipos = tipos[tipos["acidentes"] >= minimo]
    todas_causas = resumo_por(dff, "causa_acidente")
    causas = todas_causas[todas_causas["acidentes"] >= minimo]

    col_tipos, col_causas = st.columns(2, gap="large")
    with col_tipos:
        st.subheader("Tipos de acidente")
        if tipos.empty:
            st.info("Nenhum tipo com acidentes suficientes. Diminua o mínimo.")
        else:
            st.plotly_chart(barras_ranking(tipos, metrica, media), config=CONFIG_PLOTLY)
    with col_causas:
        st.subheader("10 principais causas")
        if causas.empty:
            st.info("Nenhuma causa com acidentes suficientes. Diminua o mínimo.")
        else:
            st.plotly_chart(barras_ranking(causas, metrica, media, top=10), config=CONFIG_PLOTLY)

    insights = []
    if not tipos.empty:
        mais_comum = tipos["acidentes"].idxmax()
        let_comum = tipos.loc[mais_comum, "letalidade"]
        texto = (
            f"**{mais_comum}** é o tipo mais frequente "
            f"({fmt_int(tipos.loc[mais_comum, 'acidentes'])} acidentes) e {fmt_pct(let_comum)} deles têm morte"
        )
        if media > 0:  # sem mortes no recorte, não há média para comparar
            if abs(let_comum - media) < 0.05:
                texto += ", igual à média do recorte"
            else:
                texto += f" ({'abaixo' if let_comum < media else 'acima'} da média de {fmt_pct(media)})"
        texto += "."
        criticos = tipos[tipos["letalidade"] > 2 * media].sort_values("mortos", ascending=False)
        if not criticos.empty and total_mortos > 0:
            pct_acidentes = criticos["acidentes"].sum() / len(dff) * 100
            pct_mortes = criticos["mortos"].sum() / total_mortos * 100
            texto += (
                f" Já **{juntar(list(criticos.index))}** {'soma' if len(criticos) == 1 else 'somam'} "
                f"{fmt_pct(pct_acidentes)} dos acidentes, mas **{fmt_pct(pct_mortes)} das mortes**."
            )
        insights.append(texto)

    # causa mais frequente x causa com mais mortes (todas as causas, independente do mínimo do gráfico)
    causa_comum = todas_causas["acidentes"].idxmax()
    pct_causa_acidentes = todas_causas["acidentes"] / len(dff) * 100
    if total_mortos == 0:
        insights.append(f"A causa mais frequente é **{causa_comum}** ({fmt_pct(pct_causa_acidentes[causa_comum])} "
                        "dos acidentes).")
    else:
        causa_letal = todas_causas["mortos"].idxmax()
        pct_causa_mortes = todas_causas["mortos"] / total_mortos * 100
        if causa_comum == causa_letal:
            insights.append(
                f"**{causa_comum}** é ao mesmo tempo a causa mais frequente "
                f"({fmt_pct(pct_causa_acidentes[causa_comum])} "
                f"dos acidentes) e a que mais mata ({fmt_pct(pct_causa_mortes[causa_comum])} das mortes)."
            )
        else:
            insights.append(
                f"A causa mais frequente é **{causa_comum}** ({fmt_pct(pct_causa_acidentes[causa_comum])} "
                f"dos acidentes), mas a que mais mata é **{causa_letal}**: "
                f"{fmt_pct(pct_causa_acidentes[causa_letal])} dos acidentes e "
                f"**{fmt_pct(pct_causa_mortes[causa_letal])} das mortes**."
            )
    mostrar_insights(insights)

# --------- ABA 3: ONDE? --------------------
with aba_onde:
    col_mapa, col_ranking = st.columns([3, 2], gap="large")
    with col_mapa:
        st.subheader("Onde os acidentes se concentram")
        so_com_morte = st.toggle("Mostrar apenas acidentes com morte")
        if so_com_morte and dff["com_morte"].sum() == 0:
            st.info("Não há acidentes com morte neste recorte.")
        else:
            st.plotly_chart(mapa_densidade(dff, so_com_morte), config=CONFIG_PLOTLY)
        st.caption("Quanto mais escuro, maior a concentração. Use o scroll para dar zoom e arraste para mover.")
    with col_ranking:
        st.subheader("Ranking")
        agrupamento = st.radio("Agrupar por", list(AGRUPAMENTOS), horizontal=True, key="agrupar_onde")
        metrica_onde = METRICAS[st.radio(
            "Ordenar por", list(METRICAS), horizontal=True, key="metrica_onde",
            help=f"Na letalidade, rodovias e municípios só entram com {AMOSTRA_MINIMA} acidentes ou mais.",
        )]

        resumo = resumo_por(dff, AGRUPAMENTOS[agrupamento])
        comparaveis = resumo[resumo["acidentes"] >= AMOSTRA_MINIMA]  # amostra suficiente para comparar taxas
        top = None if agrupamento == "Estado" else 15
        ranking = comparaveis if top and metrica_onde == "letalidade" else resumo
        if ranking.empty:
            st.info(f"Nenhum grupo com {AMOSTRA_MINIMA} acidentes ou mais neste recorte.")
        else:
            st.plotly_chart(barras_ranking(ranking, metrica_onde, media, top=top), config=CONFIG_PLOTLY)

    # o texto acompanha o agrupamento escolhido (estados, rodovias ou municípios)
    if len(comparaveis) >= 2:
        maior_volume = comparaveis["acidentes"].idxmax()
        mais_letal = comparaveis["letalidade"].idxmax()
        let_max = comparaveis.loc[mais_letal, "letalidade"]
        texto = (
            f"**{maior_volume}** concentra o maior volume "
            f"({fmt_int(comparaveis.loc[maior_volume, 'acidentes'])} acidentes, letalidade de "
            f"{fmt_pct(comparaveis.loc[maior_volume, 'letalidade'])})"
        )
        if let_max > media:
            letal = f"{fmt_pct(let_max)}, {fmt_dec(let_max / media)}× a média do recorte"
            if mais_letal == maior_volume:
                texto += f" e também tem a maior letalidade: {letal}."
            else:
                texto += f", enquanto **{mais_letal}** tem a maior letalidade: {letal}."
        else:
            texto += "."
        mostrar_insights([texto])

# --------- ABA 4: EM QUE CONDIÇÕES? --------------------
with aba_condicoes:
    st.subheader("% dos acidentes × % das mortes")
    condicao = st.radio("Comparar por", list(CONDICOES), horizontal=True, key="condicao")

    if total_mortos == 0:
        st.info("Não há mortes neste recorte para comparar.")
    else:
        participacao = participacao_por(dff, CONDICOES[condicao])
        st.caption(f"Barra escura maior que a clara: a condição pesa mais nas mortes do que nos acidentes. "
                   f"{NOTAS_CONDICOES[condicao]}")
        st.plotly_chart(barras_participacao(participacao), config=CONFIG_PLOTLY)

        if total_mortos < AMOSTRA_MINIMA:
            mostrar_insights([f"Só {total_mortos} mortes neste recorte: poucas para comparar as participações."])
        else:
            # categoria que mais pesa nas mortes além do volume (2 p.p. ou mais) e a mais letal (amostra suficiente)
            excesso = participacao["pct_mortos"] - participacao["pct_acidentes"]
            lider = excesso.idxmax() if excesso.max() >= 2 else None
            confiaveis = participacao[participacao["acidentes"] >= AMOSTRA_MINIMA]
            mais_letal = confiaveis["letalidade"].idxmax() if not confiaveis.empty else None
            if mais_letal is not None and confiaveis.loc[mais_letal, "letalidade"] <= media:
                mais_letal = None
            letal = (f"{fmt_pct(confiaveis.loc[mais_letal, 'letalidade'])} dos acidentes têm morte, "
                     f"contra {fmt_pct(media)} na média do recorte") if mais_letal is not None else ""

            insights = []
            if lider is None:
                insights.append("As mortes se dividem quase na mesma proporção dos acidentes: "
                                "nenhuma categoria passa de 2 p.p. de diferença.")
            else:
                texto = (f"**{lider}** reúne {fmt_pct(participacao.loc[lider, 'pct_acidentes'])} dos acidentes, "
                         f"mas **{fmt_pct(participacao.loc[lider, 'pct_mortos'])} das mortes**")
                if mais_letal == lider:
                    texto += f", e é também a categoria mais letal: {letal}"
                    mais_letal = None
                insights.append(texto + ".")
            if mais_letal is not None:
                insights.append(f"A maior letalidade fica com **{mais_letal}**: {letal}.")
            mostrar_insights(insights)

# --------- ABA 5: DADOS --------------------
with aba_dados:
    colunas = {
        "data": "Data", "horario": "Horário", "uf": "UF", "br": "BR", "km": "Km",
        "municipio": "Município", "tipo_acidente": "Tipo", "causa_acidente": "Causa",
        "classificacao_acidente": "Classificação", "tipo_pista": "Pista",
        "condicao_metereologica": "Clima", "mortos": "Mortos", "feridos": "Feridos", "veiculos": "Veículos",
    }
    tabela = dff[list(colunas)].rename(columns=colunas)
    tabela["Horário"] = tabela["Horário"].str[:5]  # 06:40:00 -> 06:40

    st.subheader(f"{fmt_int(len(tabela))} acidentes no recorte")
    st.dataframe(
        tabela,
        hide_index=True,
        height=420,
        column_config={
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Km": st.column_config.NumberColumn(format="localized"),  # vírgula decimal no navegador em português
        },
    )
    st.download_button(
        "Baixar CSV do recorte",
        data=tabela.to_csv(index=False, sep=";", decimal=",", date_format="%d/%m/%Y").encode("utf-8-sig"),
        file_name="acidentes_prf_2026_recorte.csv",
        mime="text/csv",
    )

    feriados = ", ".join(
        f"{nome} ({date.fromisoformat(primeiro):%d/%m}–{date.fromisoformat(ultimo):%d/%m})"
        for nome, (primeiro, ultimo) in FERIADOS.items()
    )
    with st.expander("Sobre os dados e a metodologia"):
        st.markdown(
            f"""
- **Base:** `datatran2026.csv` da [PRF]({FONTE_URL}), um registro por acidente, de 01/01 a 31/08/2026.
- **Limpeza:** remoção das 27 linhas com algum campo nulo (48.712 → 48.685 acidentes), igual às Atividades 1 e 2.
- **Letalidade:** % dos acidentes com pelo menos uma morte (`mortos > 0`). Média nacional: {fmt_pct(LETALIDADE_BRASIL)}.
- **Azul-escuro nos rankings:** categorias com letalidade acima de 2× a média do recorte.
- **Mapa:** densidade das coordenadas (latitude/longitude) de cada acidente.
- **% das mortes:** mortos da categoria ÷ total de mortos do recorte (conta pessoas, não acidentes).
- **Amostra mínima:** os textos e o ranking de rodovias e municípios por letalidade só comparam grupos com {AMOSTRA_MINIMA} acidentes ou mais.
- **Área:** urbana ou rural pelo campo `uso_solo` da PRF ("Sim" = urbana).
- **Clima:** Ignorado, Vento, Granizo e Neve somados em "Ignorado ou outros".
- **Fins de semana e feriados:** sábados, domingos e os feriados prolongados de 2026, contando pontes e a Quarta de Cinzas: {feriados}.
- **Rodovias e municípios:** "BR não informada" reúne os registros com BR 0; os nomes de município vêm sem acento na base.
"""
        )
