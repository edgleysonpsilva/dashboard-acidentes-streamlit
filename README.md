# Acidentes nas Rodovias Federais: Dashboard com Streamlit

![Banner do dashboard](assets/banner.png)

Dashboard interativo sobre os acidentes registrados pela Polícia Rodoviária Federal (PRF) de
01/01 a 31/08/2026. Ele foi construído a partir dos insights de atividades anteriores.

**Análise e Visualização de Dados (CESAR School)**
Aluno: Edgleyson Pereira da Silva

🔗 **App publicado:** acidentes-prf-2026.streamlit.app/
---

## 💡 Insights

1. **Quando?** O volume se concentra no rush (7h e 17h–19h), com pico no domingo às 19h.
   A letalidade, porém, é maior na madrugada: às 4h, 13,5% dos acidentes têm morte, quase o
   dobro da média nacional (7,2%).
2. **Como?** A colisão traseira é o tipo mais frequente (9.847 acidentes), mas só 4,4% terminam
   em morte. Colisão frontal e atropelamento de pedestre somam 10,5% dos acidentes e **46,3% das mortes**.
3. **Onde?** MG, SC e PR lideram em volume, enquanto AM, MA e PA têm letalidade acima de 2× a
   média nacional.

Os textos de insight do app são recalculados a cada filtro.

## 📁 Estrutura

```
atividade-3-dashboard-streamlit/
├── app.py                  # layout do dashboard: filtros, indicadores e abas
├── dados.py                # leitura, limpeza e agregações (pandas)
├── graficos.py             # paleta BTG e funções que montam as figuras Plotly
├── requirements.txt        # dependências (usado também no deploy)
├── .streamlit/config.toml  # tema com a paleta BTG
├── assets/banner.png       # figura fixa do dashboard
├── data/datatran2026.csv   # dataset da PRF (jan–ago/2026)
└── scripts/gerar_banner.py # gera o banner com matplotlib
```

## ▶️ Como rodar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O app abre em http://localhost:8501.

## 📊 Dados

- **Fonte:** [PRF – Dados Abertos](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf),
  arquivo `datatran2026.csv` (acidentes agrupados por ocorrência).
- **Leitura:** separador `;`, vírgula decimal, codificação latin-1 e `NA` para ausentes.
- **Limpeza:** remoção das 27 linhas com algum campo nulo (48.712 → 48.685 acidentes).
- **Letalidade:** % dos acidentes com pelo menos uma morte (`mortos > 0`).

## 🛠️ Tecnologias

Python · pandas · Plotly (Express e Graph Objects) · Streamlit · matplotlib (só para o banner)
