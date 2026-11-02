"""Paleta BTG e funções que montam as figuras Plotly do dashboard.

Cada função recebe dados já filtrados/agregados (ver dados.py) e devolve uma
figura pronta para o st.plotly_chart. Também dá para testar no Colab com fig.show().
"""

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from dados import AMOSTRA_MINIMA, DIA_FOLGA, DIA_UTIL, MESES, pico_semana_hora

# --------- PALETA BTG --------------------
AZUL_1 = "#05132A"
AZUL_2 = "#0B2859"
AZUL_3 = "#10408D"
AZUL_4 = "#195AB4"
AZUL_5 = "#307AE0"
AZUL_6 = "#549CFF"
AZUL_7 = "#6BAAFF"
AZUL_8 = "#87BAFF"
AZUL_9 = "#B1D2FF"
AZUL_10 = "#D2E5FF"
BRANCO = "#FFFFFF"

DESTAQUE = "#E63946"  # marcadores de destaque
CINZA = "#5B6577"     # textos secundários
GRADE = "#E3EAF5"     # linhas de grade bem claras

ESCALA_AZUL = [BRANCO, AZUL_9, AZUL_5, AZUL_2, AZUL_1]

# para o mapa
ESCALA_MAPA = [[0, AZUL_9], [0.04, AZUL_8], [0.15, AZUL_5], [0.45, AZUL_3], [1, AZUL_1]]

DIAS_CURTOS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
HORAS_PARES = list(range(0, 24, 2))

# coluna da tabela de resumo
METRICAS = {"Acidentes": "acidentes", "Mortos": "mortos", "Letalidade (%)": "letalidade"}

GRUPO_CRITICO = "Letalidade acima de 2× a média"
GRUPO_DEMAIS = "Demais"


# --------- FORMATAÇÃO--------------------
def fmt_int(valor):
    """48685 -> '48.685'"""
    return f"{valor:,.0f}".replace(",", ".")


def fmt_pct(valor):
    """7.17 -> '7,2%'"""
    return f"{valor:.1f}%".replace(".", ",")


def fmt_dec(valor):
    """14.68 -> '14,7'"""
    return f"{valor:.1f}".replace(".", ",")


def _estilo_base(fig, altura, margem_baixo=10):
    """Ajustes comuns a todas as figuras."""
    fig.update_layout(
        height=altura,
        margin=dict(l=10, r=10, t=30, b=margem_baixo),
        separators=",.",  # vírgula decimal e ponto no milhar dentro do Plotly
        font=dict(color=AZUL_1),
        hoverlabel=dict(bgcolor=BRANCO, bordercolor=AZUL_8, font=dict(color=AZUL_1)),
    )
    # com margens pequenas, os eixos precisam abrir espaço
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def _encurtar(nomes, limite=42):
    """Encurta nomes longos (ex.: causas) para caber no eixo"""
    curtos = nomes.where(nomes.str.len() <= limite, nomes.str[: limite - 1].str.rstrip() + "…")
    return curtos if curtos.is_unique else nomes


# --------- QUANDO? --------------------
def heatmap_semana_hora(contagem):
    """Volume de acidentes por dia da semana e hora (Insight #1 das Atividades 1 e 2)."""
    fig = go.Figure(go.Heatmap(
        z=contagem.values,
        x=list(contagem.columns),
        y=DIAS_CURTOS,
        colorscale=ESCALA_AZUL,
        zmin=0,
        xgap=2,  # espaço branco entre as células
        ygap=2,
        colorbar=dict(title=dict(text="Acidentes"), thickness=12, outlinewidth=0),
        hovertemplate="%{y}, %{x}h<br><b>%{z:,} acidentes</b><extra></extra>",
    ))

    # contorno na célula de pico
    linha, coluna = pico_semana_hora(contagem)
    fig.add_shape(type="rect", x0=coluna - 0.5, x1=coluna + 0.5, y0=linha - 0.5, y1=linha + 0.5,
                  line=dict(color=DESTAQUE, width=2.5))

    fig.update_xaxes(title="Hora do dia", tickmode="array", tickvals=HORAS_PARES,
                     ticktext=[f"{h}h" for h in HORAS_PARES], showgrid=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return _estilo_base(fig, 360)


def linha_letalidade_hora(por_hora, media):
    """% dos acidentes com morte em cada hora do dia, com a média do recorte."""
    por_hora = por_hora.reindex(range(24))  # mantém as 24 horas no eixo, mesmo sem acidentes

    fig = go.Figure()

    # faixa da madrugada, onde a Atividade 2 encontrou a maior letalidade
    fig.add_vrect(x0=-0.5, x1=5.5, fillcolor=AZUL_10, opacity=0.45, line_width=0, layer="below",
                  annotation_text="madrugada", annotation_position="top left",
                  annotation_font=dict(color=CINZA, size=12))
    fig.add_hline(y=media, line=dict(color=DESTAQUE, width=1.5, dash="dash"), layer="above",
                  annotation_text=f"média do recorte: {fmt_pct(media)}",
                  annotation_position="top right", annotation_font=dict(color=DESTAQUE, size=12))

    fig.add_trace(go.Scatter(
        x=por_hora.index,
        y=por_hora["letalidade"],
        mode="lines+markers",
        line=dict(color=AZUL_5, width=2),
        marker=dict(size=8, color=AZUL_5, line=dict(color=BRANCO, width=2)),
        customdata=por_hora["acidentes"],
        hovertemplate="<b>%{x}h</b><br>%{y:.1f}% com morte<br>%{customdata:,} acidentes<extra></extra>",
    ))

    # destaque no maior e no menor valor
    # considerando só as horas com amostra suficiente
    confiaveis = por_hora[por_hora["acidentes"] >= AMOSTRA_MINIMA]["letalidade"]
    destaques = []
    if not confiaveis.empty:
        destaques.append((confiaveis.idxmax(), "maior", -38))
        if confiaveis.idxmin() != confiaveis.idxmax():
            destaques.append((confiaveis.idxmin(), "menor", 38))
    for hora, texto, deslocamento_y in destaques:
        valor = por_hora.loc[hora, "letalidade"]
        fig.add_trace(go.Scatter(x=[hora], y=[valor], mode="markers", hoverinfo="skip",
                                 marker=dict(size=12, color=DESTAQUE, line=dict(color=BRANCO, width=2))))
        fig.add_annotation(x=hora, y=valor, text=f"<b>{texto}: {hora}h · {fmt_pct(valor)}</b>",
                           ax=45 if hora < 18 else -45, ay=deslocamento_y,
                           arrowhead=0, arrowwidth=1.5, arrowcolor=DESTAQUE,
                           font=dict(color=AZUL_1, size=12), bgcolor="rgba(255,255,255,0.85)")

    fig.update_xaxes(title="Hora do dia", tickmode="array", tickvals=HORAS_PARES,
                     ticktext=[f"{h}h" for h in HORAS_PARES], range=[-0.6, 23.6],
                     showgrid=False, zeroline=False)
    fig.update_yaxes(title="% com morte", ticksuffix="%", gridcolor=GRADE, zerolinecolor=GRADE,
                     range=[0, max(por_hora["letalidade"].max() * 1.3, 1)])  # max(..., 1): recorte sem mortes
    fig.update_layout(showlegend=False)
    return _estilo_base(fig, 380)


def barras_mortes_dia(dias):
    """Mortes em cada dia do período, separando dias úteis de fins de semana e feriados."""
    dados = dias.reset_index()
    dia_semana = dados["data"].dt.day_of_week.map(dict(enumerate(DIAS_CURTOS)))
    dados["dia"] = dados["data"].dt.strftime("%d/%m") + ", " + dia_semana
    dados["feriado"] = (" · " + dados["feriado"]).where(dados["feriado"] != "", "")

    fig = px.bar(
        dados,
        x="data",
        y="mortos",
        color="tipo_dia",
        color_discrete_map={DIA_UTIL: AZUL_8, DIA_FOLGA: AZUL_3},
        category_orders={"tipo_dia": [DIA_UTIL, DIA_FOLGA]},
        custom_data=["dia", "acidentes", "feriado"],
    )
    fig.update_traces(hovertemplate="<b>%{customdata[0]}</b>%{customdata[2]}<br>%{y} mortos"
                                    "<br>%{customdata[1]:,} acidentes<extra></extra>")

    # média de mortes por dia de cada grupo: linha tracejada vermelha por cima das barras
    medias = dias.groupby("tipo_dia")["mortos"].mean()
    for media in medias:
        fig.add_hline(y=media, line=dict(color=DESTAQUE, width=1.5, dash="dash"), layer="above")
        fig.add_annotation(x=1, y=media, xref="paper", yref="y", xanchor="left", showarrow=False,
                           text=f"<b>média {fmt_dec(media)}</b>", font=dict(color=DESTAQUE, size=12))
    fig.for_each_trace(lambda barras: barras.update(
        name=f"{barras.name} · média de {fmt_dec(medias[barras.name])} mortes"))

    # destaque no dia com mais mortes, se ele for único (em recortes pequenos o "pior dia" seria só ruído)
    maximo = int(dias["mortos"].max())
    if dias["mortos"].sum() >= AMOSTRA_MINIMA and (dias["mortos"] == maximo).sum() == 1:
        pior = dias["mortos"].idxmax()
        fig.add_annotation(x=pior, y=maximo, text=f"<b>{pior:%d/%m}: {maximo} mortes</b>",
                           ax=-50 if pior > dias.index[len(dias) * 2 // 3] else 50, ay=-22,
                           arrowhead=0, arrowwidth=1.5, arrowcolor=DESTAQUE,
                           font=dict(color=AZUL_1, size=12), bgcolor="rgba(255,255,255,0.85)")

    meio_do_mes = dias.index[dias.index.day == 15]  # nome do mês no meio de cada mês
    fig.update_xaxes(title=None, tickvals=meio_do_mes, ticktext=[MESES[d.month] for d in meio_do_mes], showgrid=False)
    fig.update_yaxes(title="Mortes por dia", gridcolor=GRADE, zerolinecolor=GRADE, range=[0, max(maximo * 1.3, 1)])
    fig.update_layout(bargap=0.15, legend=dict(title=None, orientation="h", x=0, y=1.02, yanchor="bottom"))
    fig = _estilo_base(fig, 280)
    fig.update_layout(margin=dict(r=90))
    return fig


# --------- COMO? E ONDE? --------------------
def barras_ranking(tabela, metrica, media, top=None):
    """Ranking em barras horizontais pela métrica escolhida no widget.

    Categorias com letalidade acima de 2× a média ficam em azul-escuro e o
    restante em azul-claro (foco de atenção, como na Atividade 2).
    """
    dados = tabela.sort_values(metrica, ascending=False)
    if top:
        dados = dados.head(top)
    dados = dados.reset_index()
    categoria = dados.columns[0]

    dados["rotulo"] = _encurtar(dados[categoria])
    dados["grupo"] = np.where(dados["letalidade"] > 2 * media, GRUPO_CRITICO, GRUPO_DEMAIS)
    dados["texto"] = dados[metrica].map(fmt_pct if metrica == "letalidade" else fmt_int)

    fig = px.bar(
        dados,
        x=metrica,
        y="rotulo",
        orientation="h",
        color="grupo",
        color_discrete_map={GRUPO_CRITICO: AZUL_1, GRUPO_DEMAIS: AZUL_8},
        category_orders={"rotulo": list(dados["rotulo"]), "grupo": [GRUPO_CRITICO, GRUPO_DEMAIS]},
        custom_data=[categoria, "acidentes", "mortos", "letalidade"],
    )
    fig.update_traces(
        marker_cornerradius=4,
        hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]:,} acidentes"
                       "<br>%{customdata[2]:,} mortos<br>%{customdata[3]:.1f}% com morte<extra></extra>"),
    )

    limite_x = max(dados[metrica].max() * 1.22, 1)

    # valores numa coluna fixa à direita (longe da linha da média)
    for _, linha in dados.iterrows():
        fig.add_annotation(x=limite_x, y=linha["rotulo"], text=linha["texto"],
                           xref="x", yref="y", xanchor="right", showarrow=False,
                           font=dict(color=AZUL_1, size=12))

    if metrica == "letalidade":
        fig.add_vline(x=media, line=dict(color=DESTAQUE, width=1.5, dash="dash"), layer="above")
        # rótulo acima do gráfico, fora da área das barras
        fig.add_annotation(x=media, y=1, xref="x", yref="paper", yanchor="bottom",
                           text=f"<b>média {fmt_pct(media)}</b>", showarrow=False,
                           font=dict(color=DESTAQUE, size=12))
                           s
    fig.update_xaxes(visible=False, range=[0, limite_x])
    fig.update_yaxes(title=None)
    fig.update_layout(
        bargap=0.35,
        showlegend=bool((dados["grupo"] == GRUPO_CRITICO).any()),  # a legenda só explica algo se houver barra escura
        legend=dict(title=None, orientation="h", x=0, y=1.1, yanchor="bottom"),
    )
    fig = _estilo_base(fig, 100 + 28 * len(dados), margem_baixo=30)
    fig.update_layout(margin=dict(t=70))  # espaço para legenda + rótulo da média
    return fig


def mapa_densidade(df, so_com_morte=False):
    """Mapa de calor com a localização dos acidentes (px.density_map, visto na Aula 04)."""
    pontos = df[df["com_morte"] == 1] if so_com_morte else df
    pontos = pontos[["latitude", "longitude", "mortos"]].round(3)  # ~100 m de precisão e menos dados no navegador
    pontos["peso"] = pontos["mortos"] if so_com_morte else 1

    # centraliza e ajusta o zoom na região filtrada
    lat_min, lat_max = pontos["latitude"].min(), pontos["latitude"].max()
    lon_min, lon_max = pontos["longitude"].min(), pontos["longitude"].max()
    extensao = max(lat_max - lat_min, lon_max - lon_min, 1.0)
    zoom = float(np.clip(np.log2(420 / extensao) - 0.2, 2.5, 10))

    # teto da escala de cor: sem ele, qualquer trecho com alguns acidentes já fica saturado.
    # Usa o percentil 99 de uma grade do tamanho do raio, então só os 1% trechos mais carregados
    # chegam ao azul mais escuro, em qualquer recorte.
    raio = 8 if so_com_morte else 5
    lado = 360 / (512 * 2 ** zoom) * raio  # graus cobertos pelo raio nesse zoom
    grade = pontos.groupby([pontos["latitude"] // lado, pontos["longitude"] // lado])["peso"].sum()
    teto = max(float(grade.quantile(0.99)), 1.0)

    fig = px.density_map(
        pontos,
        lat="latitude",
        lon="longitude",
        z="peso",
        radius=raio,
        range_color=(0, teto),
        center=dict(lat=(lat_min + lat_max) / 2, lon=(lon_min + lon_max) / 2),
        zoom=zoom,
        map_style="carto-positron",
        color_continuous_scale=ESCALA_MAPA,
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hoverinfo="skip")
    _estilo_base(fig, 600)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


# --------- EM QUE CONDIÇÕES? --------------------
def barras_participacao(tabela):
    """% dos acidentes x % das mortes de cada categoria, na ordem da tabela (ver dados.participacao_por)."""
    detalhes = tabela[["acidentes", "mortos", "letalidade"]].to_numpy()

    fig = go.Figure()
    for coluna, nome, cor in [("pct_acidentes", "% dos acidentes", AZUL_8), ("pct_mortos", "% das mortes", AZUL_1)]:
        fig.add_trace(go.Bar(
            x=tabela[coluna],
            y=tabela.index,
            name=nome,
            orientation="h",
            marker=dict(color=cor, cornerradius=4),
            text=tabela[coluna].map(fmt_pct),
            textposition="outside",
            constraintext="none",  # sem isso o Plotly encolhe o texto até a espessura da barra
            cliponaxis=False,
            textfont=dict(color=AZUL_1, size=12),
            customdata=detalhes,
            hovertemplate=(f"<b>%{{y}}</b><br>{nome}: %{{x:.1f}}%<br>%{{customdata[0]:,}} acidentes · "
                           "%{customdata[1]:,} mortos<br>%{customdata[2]:.1f}% com morte<extra></extra>"),
        ))

    fig.update_xaxes(visible=False, range=[0, tabela[["pct_acidentes", "pct_mortos"]].to_numpy().max() * 1.2])
    # eixo invertido: 1ª categoria no topo e, em cada par, acidentes acima de mortes (como na legenda)
    fig.update_yaxes(title=None, autorange="reversed", categoryorder="array", categoryarray=list(tabela.index))
    fig.update_layout(
        barmode="group",
        bargap=0.28,
        bargroupgap=0.06,
        legend=dict(title=None, orientation="h", x=0, y=1.0, yanchor="bottom"),
    )
    return _estilo_base(fig, 90 + 64 * len(tabela))
