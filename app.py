import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(
    page_title="Brasileirao - Dashboard BI",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Tema / CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Fundo geral */
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }

/* Cabeçalho */
.main-header {
    background: linear-gradient(135deg, #1a6b2e 0%, #0d4a1f 60%, #0a3318 100%);
    padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
    border: 1px solid #2ea44f; box-shadow: 0 4px 20px rgba(46,164,79,0.3);
}
.main-header h1 { color: #f0e130; font-size: 2rem; margin: 0; letter-spacing: 1px; }
.main-header p  { color: #8ac990; margin: 0.2rem 0 0; font-size: 0.9rem; }

/* Cards KPI */
.kpi-grid { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 1rem; }
.kpi-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 1rem 1.4rem; flex: 1; min-width: 140px;
    transition: transform .15s, border-color .15s;
}
.kpi-card:hover { transform: translateY(-3px); border-color: #2ea44f; }
.kpi-label { color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: .8px; }
.kpi-value { color: #f0e130; font-size: 1.6rem; font-weight: 700; line-height: 1.2; }
.kpi-sub   { color: #2ea44f; font-size: 0.8rem; margin-top: 2px; }
.kpi-card.gold   { border-color: #f0e130; }
.kpi-card.green  { border-color: #2ea44f; }
.kpi-card.red    { border-color: #e74c3c; }
.kpi-card.blue   { border-color: #58a6ff; }
.kpi-card.purple { border-color: #a371f7; }

/* Tabs */
[data-baseweb="tab-list"] { background: #161b22 !important; border-radius: 8px; gap: 4px; }
[data-baseweb="tab"] { color: #8b949e !important; border-radius: 6px !important; }
[aria-selected="true"] { background: #1a6b2e !important; color: #f0e130 !important; }

/* Tabelas */
[data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; }

/* Sidebar */
.sidebar-badge {
    background: #1a6b2e; color: #f0e130; padding: 2px 10px;
    border-radius: 20px; font-size: 0.75rem; font-weight: 600;
}

/* Plotly fundo */
.js-plotly-plot .plotly { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Paleta de cores padrão dos gráficos
COR_VERDE   = "#2ea44f"
COR_AMARELO = "#f0e130"
COR_VERMELHO= "#e74c3c"
COR_AZUL    = "#58a6ff"
COR_ROXO    = "#a371f7"
TEMPLATE    = "plotly_dark"

def kpi(label, value, sub="", cor=""):
    return f"""<div class="kpi-card {cor}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

# ── Conexão ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "camp-brasileiro.mysql.uhserver.com"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "biuser"),
        password=os.getenv("DB_PASSWORD", "@passUFU2026"),
        database=os.getenv("DB_NAME", "camp_brasileiro"),
        connection_timeout=10
    )

@st.cache_data(ttl=300)
def q(sql):
    conn = get_conn()
    if not conn.is_connected():
        conn.reconnect()
    return pd.read_sql(sql, conn)

try:
    get_conn()
    ok = True
except Exception as e:
    ok = False
    err = str(e)

# ── Cabeçalho ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>⚽ Brasileirão Série A — Dashboard BI</h1>
  <p>Análise completa de desempenho, gols, cartões e estatísticas</p>
</div>
""", unsafe_allow_html=True)

if not ok:
    st.error(f"Não foi possível conectar ao banco.\n\n{err}")
    st.stop()

# ── Dimensões base ───────────────────────────────────────────────────────────
anos_df   = q("SELECT sk_campeonato, ano, nome FROM dim_campeonato ORDER BY ano")
clubes_df = q("SELECT sk_clube, nome_clube, estado FROM dim_clube ORDER BY nome_clube")

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🎯 Filtros")
ano_opcoes = {"🏆 Todos os Brasileirões": None}
ano_opcoes.update({row["nome"]: row["sk_campeonato"] for _, row in anos_df.iterrows()})
ano_sel_nome = st.sidebar.selectbox("Campeonato:", list(ano_opcoes.keys()), index=0)
sk_camp = ano_opcoes[ano_sel_nome]

todos = sk_camp is None
titulo_camp = ano_sel_nome.replace("🏆 ", "")
camp_where_p = "WHERE 1=1"  if todos else f"WHERE p.sk_campeonato = {sk_camp}"
camp_subq    = ""            if todos else f"WHERE sk_campeonato = {sk_camp}"
camp_where_e = "WHERE 1=1"  if todos else f"WHERE e.sk_campeonato = {sk_camp}"

clube_opcoes = ["Todos"] + clubes_df["nome_clube"].tolist()
clube_sel = st.sidebar.selectbox("Clube:", clube_opcoes)

st.sidebar.markdown("---")
n_edicoes = len(anos_df)
n_clubes  = len(clubes_df)
st.sidebar.markdown(f"""
<div style='text-align:center'>
  <span class='sidebar-badge'>⚽ {n_edicoes} edições</span>&nbsp;
  <span class='sidebar-badge'>🏟️ {n_clubes} clubes</span>
</div>
""", unsafe_allow_html=True)
st.sidebar.caption("Fonte: Brasileirão Série A")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Classificação",
    "⚽ Artilheiros",
    "🟨 Cartões",
    "📊 Estatísticas",
    "📋 Partidas"
])

# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — CLASSIFICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    df_part = q(f"""
        SELECT p.vencedor, p.placar_mandante, p.placar_visitante,
               m.nome_clube AS mandante, v.nome_clube AS visitante
        FROM fato_partidas p
        JOIN dim_clube m ON p.sk_mandante = m.sk_clube
        JOIN dim_clube v ON p.sk_visitante = v.sk_clube
        {camp_where_p}
    """)

    clubes_list = pd.concat([df_part["mandante"], df_part["visitante"]]).unique()
    rows = []
    for clube in clubes_list:
        mand  = df_part[df_part["mandante"] == clube]
        visit = df_part[df_part["visitante"] == clube]
        jogos = len(mand) + len(visit)
        vit   = int((df_part["vencedor"] == clube).sum())
        emp   = int(((df_part["mandante"] == clube) & (df_part["vencedor"] == "Empate")).sum()
                  + ((df_part["visitante"] == clube) & (df_part["vencedor"] == "Empate")).sum())
        der   = jogos - vit - emp
        gm    = int(mand["placar_mandante"].sum() + visit["placar_visitante"].sum())
        gs    = int(mand["placar_visitante"].sum() + visit["placar_mandante"].sum())
        pts   = vit * 3 + emp
        aprov = round(pts / (jogos * 3) * 100, 1) if jogos else 0
        vit_m = int(((df_part["mandante"] == clube) & (df_part["vencedor"] == clube)).sum())
        vit_v = int(((df_part["visitante"] == clube) & (df_part["vencedor"] == clube)).sum())
        rows.append({"Clube": clube, "PJ": jogos, "V": vit, "E": emp, "D": der,
                     "GM": gm, "GS": gs, "SG": gm - gs, "Pts": pts,
                     "Aprov%": aprov, "V.Casa": vit_m, "V.Fora": vit_v})

    tabela = pd.DataFrame(rows).sort_values("Pts", ascending=False).reset_index(drop=True)
    tabela.index += 1
    tabela.index.name = "Pos"

    lider       = tabela.iloc[0]
    lanterna    = tabela.iloc[-1]
    mais_gols   = tabela.sort_values("GM", ascending=False).iloc[0]
    melhor_def  = tabela.sort_values("GS").iloc[0]
    mais_vit    = tabela.sort_values("V", ascending=False).iloc[0]
    mais_der    = tabela.sort_values("D", ascending=False).iloc[0]
    total_gols_tab = int(tabela["GM"].sum() / 2)  # cada gol conta 2x (mand+visit)
    media_gols_jogo = round(total_gols_tab / len(df_part), 2) if len(df_part) else 0

    st.markdown(f"### 🏆 Classificação — {titulo_camp}")
    st.markdown(f"""<div class="kpi-grid">
        {kpi("🥇 Líder", lider['Clube'], f"{lider['Pts']} pts · {lider['Aprov%']}% aprov.", "gold")}
        {kpi("📈 Mais Vitórias", mais_vit['Clube'], f"{mais_vit['V']} vitórias", "green")}
        {kpi("⚽ Mais Gols (time)", mais_gols['Clube'], f"{mais_gols['GM']} gols marcados", "green")}
        {kpi("🛡️ Melhor Defesa", melhor_def['Clube'], f"{melhor_def['GS']} gols sofridos", "blue")}
        {kpi("📉 Lanterna", lanterna['Clube'], f"{lanterna['Pts']} pts", "red")}
        {kpi("😓 Mais Derrotas", mais_der['Clube'], f"{mais_der['D']} derrotas", "red")}
        {kpi("🎯 Total Partidas", len(df_part), "", "blue")}
        {kpi("⚡ Média Gols/Jogo", media_gols_jogo, "gols por partida", "purple")}
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Colorir posições da tabela
    def colorir_pos(row):
        pos = row.name
        if pos <= 4:   return ["background-color:#0d2b12; color:#2ea44f"] * len(row)
        if pos <= 6:   return ["background-color:#0d1f2b; color:#58a6ff"] * len(row)
        if pos >= len(tabela) - 2: return ["background-color:#2b0d0d; color:#e74c3c"] * len(row)
        return [""] * len(row)

    st.dataframe(
        tabela.style.apply(colorir_pos, axis=1).format({"Aprov%": "{:.1f}%"}),
        use_container_width=True, height=560
    )
    st.caption("🟢 Libertadores   🔵 Sul-Americana   🔴 Rebaixamento")

    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        fig = px.bar(tabela.head(10), x="Clube", y="Pts",
                     color="Pts", color_continuous_scale=[[0,"#1a6b2e"],[1,"#f0e130"]],
                     title="Top 10 — Pontos", text="Pts", template=TEMPLATE)
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig2 = px.bar(tabela.head(10), x="Clube", y=["GM","GS"],
                      title="Top 10 — Gols Marcados vs Sofridos", barmode="group",
                      color_discrete_map={"GM": COR_VERDE, "GS": COR_VERMELHO},
                      template=TEMPLATE)
        st.plotly_chart(fig2, use_container_width=True)
    with col_c:
        fig3 = px.bar(tabela.head(10).sort_values("Aprov%", ascending=False),
                      x="Clube", y="Aprov%", color="Aprov%",
                      color_continuous_scale=[[0,"#e74c3c"],[0.5,"#f0e130"],[1,"#2ea44f"]],
                      title="Top 10 — Aproveitamento %", text_auto=".1f", template=TEMPLATE)
        fig3.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)

    col_d, col_e = st.columns(2)
    with col_d:
        fig4 = px.bar(tabela.head(10), x="Clube", y=["V.Casa","V.Fora"],
                      title="Vitórias em Casa vs Fora (Top 10)", barmode="stack",
                      color_discrete_map={"V.Casa": COR_AZUL, "V.Fora": COR_ROXO},
                      template=TEMPLATE)
        st.plotly_chart(fig4, use_container_width=True)
    with col_e:
        fig5 = px.scatter(tabela, x="GM", y="Pts", size="PJ", color="Clube",
                          title="Gols Marcados × Pontos", template=TEMPLATE,
                          hover_data=["SG","Aprov%"])
        st.plotly_chart(fig5, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — ARTILHEIROS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    where_clube = f"AND clube = '{clube_sel}'" if clube_sel != "Todos" else ""
    df_gols = q(f"""
        SELECT atleta, clube, COUNT(*) AS gols, tipo_de_gol
        FROM trusted_campeonato_brasileiro_gols
        WHERE partida_ID IN (
            SELECT id_partida_original FROM fato_partidas {camp_subq}
        )
        {where_clube}
        GROUP BY atleta, clube, tipo_de_gol
        ORDER BY gols DESC
    """)

    st.markdown(f"### ⚽ Artilheiros — {titulo_camp}")

    if df_gols.empty:
        st.info("Sem dados de gols para este filtro.")
    else:
        top_art  = df_gols.groupby(["atleta","clube"])["gols"].sum().reset_index()
        top_art  = top_art.sort_values("gols", ascending=False).head(20)
        total_g  = int(df_gols["gols"].sum())
        n_artil  = df_gols["atleta"].nunique()
        n_clubes_g = df_gols["clube"].nunique()
        media_g  = round(total_g / n_artil, 2) if n_artil else 0
        top1     = top_art.iloc[0]
        gols_penalti = int(df_gols[df_gols["tipo_de_gol"].str.lower().str.contains("penalt|pênalt", na=False)]["gols"].sum())
        gols_proprios= int(df_gols[df_gols["tipo_de_gol"].str.lower().str.contains("contra|próprio|proprio", na=False)]["gols"].sum())

        st.markdown(f"""<div class="kpi-grid">
            {kpi("🥇 Artilheiro", top1['atleta'], f"{top1['gols']} gols — {top1['clube']}", "gold")}
            {kpi("⚽ Total de Gols", total_g, "todos os marcadores", "green")}
            {kpi("👥 Jogadores que Marcaram", n_artil, f"em {n_clubes_g} clubes", "blue")}
            {kpi("📊 Média por Atleta", media_g, "gols/marcador", "blue")}
            {kpi("🎯 Gols de Pênalti", gols_penalti, f"{round(gols_penalti/total_g*100,1) if total_g else 0}% do total", "purple")}
            {kpi("😬 Gols Contra", gols_proprios, "gols contra", "red")}
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            fig = px.bar(top_art, x="gols", y="atleta", color="clube",
                         orientation="h", title="Top 20 Artilheiros", text="gols",
                         height=560, template=TEMPLATE)
            fig.update_layout(yaxis={"categoryorder":"total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            tipos = df_gols.groupby("tipo_de_gol")["gols"].sum().reset_index()
            tipos = tipos[tipos["tipo_de_gol"].notna() & (tipos["tipo_de_gol"] != "")]
            if not tipos.empty:
                fig2 = px.pie(tipos, names="tipo_de_gol", values="gols",
                              title="Tipos de Gol", hole=0.4, template=TEMPLATE,
                              color_discrete_sequence=px.colors.sequential.Greens_r)
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        gols_clube = df_gols.groupby("clube")["gols"].sum().reset_index().sort_values("gols", ascending=False)
        fig3 = px.bar(gols_clube, x="clube", y="gols",
                      color="gols", color_continuous_scale=[[0,"#1a6b2e"],[1,"#f0e130"]],
                      title="Total de Gols por Clube", text="gols", template=TEMPLATE)
        fig3.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)

        # Top marcadores com distribuição de tipos
        st.markdown("---")
        top10_nomes = top_art.head(10)["atleta"].tolist()
        df_top10_tipos = df_gols[df_gols["atleta"].isin(top10_nomes)]
        fig4 = px.bar(df_top10_tipos, x="atleta", y="gols", color="tipo_de_gol",
                      title="Top 10 Artilheiros — Distribuição por Tipo de Gol",
                      template=TEMPLATE, text_auto=True)
        fig4.update_xaxes(tickangle=30)
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — CARTÕES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    where_clube_c = f"AND clube = '{clube_sel}'" if clube_sel != "Todos" else ""
    df_cart = q(f"""
        SELECT clube, cartao, atleta, posicao, minuto
        FROM trusted_campeonato_brasileiro_cartoes
        WHERE partida_ID IN (
            SELECT id_partida_original FROM fato_partidas {camp_subq}
        )
        {where_clube_c}
    """)

    st.markdown(f"### 🟨 Cartões — {titulo_camp}")

    if df_cart.empty:
        st.info("Sem dados de cartões para este filtro.")
    else:
        amarelos  = df_cart[df_cart["cartao"].str.lower().str.contains("amarelo", na=False)]
        vermelhos = df_cart[df_cart["cartao"].str.lower().str.contains("vermelho", na=False)]
        mais_cart_cl = df_cart.groupby("clube").size().idxmax()
        mais_cart_at = df_cart.groupby("atleta").size().idxmax()
        pos_mais = df_cart[df_cart["posicao"].notna() & (df_cart["posicao"] != "")]
        pos_top  = pos_mais.groupby("posicao").size().idxmax() if not pos_mais.empty else "—"
        ratio_vm = round(len(vermelhos) / len(amarelos) * 100, 1) if len(amarelos) else 0

        st.markdown(f"""<div class="kpi-grid">
            {kpi("🟨 Amarelos", len(amarelos), f"{round(len(amarelos)/len(df_cart)*100,1)}% dos cartões", "gold")}
            {kpi("🟥 Vermelhos", len(vermelhos), f"1 vermelho a cada {round(len(amarelos)/len(vermelhos),1) if len(vermelhos) else '∞'} amarelos", "red")}
            {kpi("📋 Total de Cartões", len(df_cart), "", "blue")}
            {kpi("🏟️ Clube Mais Cartões", mais_cart_cl, f"{df_cart.groupby('clube').size().max()} cartões", "red")}
            {kpi("😤 Atleta Mais Cartões", mais_cart_at, f"{df_cart.groupby('atleta').size().max()} cartões", "red")}
            {kpi("🦵 Posição Mais Punida", pos_top, "", "purple")}
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            cart_clube = df_cart.groupby(["clube","cartao"]).size().reset_index(name="qtd")
            fig = px.bar(cart_clube, x="clube", y="qtd", color="cartao",
                         title="Cartões por Clube",
                         color_discrete_map={"Amarelo": COR_AMARELO, "Vermelho": COR_VERMELHO,
                                             "amarelo": COR_AMARELO, "vermelho": COR_VERMELHO},
                         template=TEMPLATE)
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            top_cart = df_cart.groupby("atleta").size().reset_index(name="cartoes")
            top_cart = top_cart.sort_values("cartoes", ascending=False).head(15)
            fig2 = px.bar(top_cart, x="cartoes", y="atleta", orientation="h",
                          title="Top 15 — Atletas com Mais Cartões", text="cartoes",
                          color="cartoes", color_continuous_scale=[[0,"#8b0000"],[1,COR_VERMELHO]],
                          template=TEMPLATE)
            fig2.update_layout(yaxis={"categoryorder":"total ascending"}, coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        col_c, col_d = st.columns(2)
        with col_c:
            df_cart["minuto_num"] = pd.to_numeric(df_cart["minuto"], errors="coerce")
            fig3 = px.histogram(df_cart.dropna(subset=["minuto_num"]), x="minuto_num",
                                nbins=18, color="cartao",
                                color_discrete_map={"Amarelo": COR_AMARELO, "Vermelho": COR_VERMELHO,
                                                    "amarelo": COR_AMARELO, "vermelho": COR_VERMELHO},
                                title="Distribuição de Cartões por Minuto", template=TEMPLATE,
                                labels={"minuto_num": "Minuto"})
            st.plotly_chart(fig3, use_container_width=True)
        with col_d:
            if not pos_mais.empty:
                pos_dist = pos_mais.groupby(["posicao","cartao"]).size().reset_index(name="qtd")
                fig4 = px.bar(pos_dist, x="posicao", y="qtd", color="cartao",
                              title="Cartões por Posição",
                              color_discrete_map={"Amarelo": COR_AMARELO, "Vermelho": COR_VERMELHO,
                                                  "amarelo": COR_AMARELO, "vermelho": COR_VERMELHO},
                              template=TEMPLATE)
                st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 4 — ESTATÍSTICAS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    where_clube_e = f"AND c.nome_clube = '{clube_sel}'" if clube_sel != "Todos" else ""
    df_est = q(f"""
        SELECT c.nome_clube AS clube,
               AVG(e.chutes)           AS chutes,
               AVG(e.chutes_a_gol)     AS chutes_a_gol,
               AVG(e.posse_bola)       AS posse_bola,
               AVG(e.passes)           AS passes,
               AVG(e.precisao_passes)  AS precisao_passes,
               AVG(e.faltas)           AS faltas,
               AVG(e.impedimentos)     AS impedimentos,
               AVG(e.escanteios)       AS escanteios,
               COUNT(*) AS partidas
        FROM fato_estatisticas e
        JOIN dim_clube c ON e.sk_clube = c.sk_clube
        {camp_where_e}
        {where_clube_e}
        GROUP BY c.nome_clube
        ORDER BY posse_bola DESC
    """)

    st.markdown(f"### 📊 Estatísticas — {titulo_camp}")

    if df_est.empty:
        st.info("Sem dados de estatísticas para este filtro.")
    else:
        top_posse   = df_est.sort_values("posse_bola", ascending=False).iloc[0]
        top_chutes  = df_est.sort_values("chutes_a_gol", ascending=False).iloc[0]
        top_passes  = df_est.sort_values("precisao_passes", ascending=False).iloc[0]
        top_faltas  = df_est.sort_values("faltas", ascending=False).iloc[0]
        media_posse = round(df_est["posse_bola"].mean(), 1)
        media_passes= round(df_est["precisao_passes"].mean(), 1)

        st.markdown(f"""<div class="kpi-grid">
            {kpi("🏃 Maior Posse (média)", top_posse['clube'], f"{top_posse['posse_bola']:.1f}%", "green")}
            {kpi("🎯 Mais Preciso nos Passes", top_passes['clube'], f"{top_passes['precisao_passes']:.1f}%", "green")}
            {kpi("💥 Mais Chutes a Gol", top_chutes['clube'], f"{top_chutes['chutes_a_gol']:.1f} por jogo", "blue")}
            {kpi("😤 Mais Faltoso", top_faltas['clube'], f"{top_faltas['faltas']:.1f} faltas/jogo", "red")}
            {kpi("📈 Média de Posse (geral)", f"{media_posse}%", "todos os clubes", "purple")}
            {kpi("📬 Média Precisão Passes", f"{media_passes}%", "todos os clubes", "purple")}
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        metrica_sel = st.selectbox("Métrica para comparação:", [
            "posse_bola","chutes","chutes_a_gol","passes",
            "precisao_passes","faltas","impedimentos","escanteios"
        ], format_func=lambda x: x.replace("_"," ").title())

        col_a, col_b = st.columns(2)
        with col_a:
            df_plot = df_est.sort_values(metrica_sel, ascending=False)
            fig = px.bar(df_plot, x="clube", y=metrica_sel,
                         title=f"{metrica_sel.replace('_',' ').title()} por Clube (média)",
                         color=metrica_sel, color_continuous_scale=[[0,"#1a6b2e"],[1,"#f0e130"]],
                         text_auto=".1f", template=TEMPLATE)
            fig.update_xaxes(tickangle=45)
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            ref = df_est[df_est["clube"] == clube_sel] if clube_sel != "Todos" else df_est.head(1)
            if not ref.empty:
                categorias = ["chutes_a_gol","posse_bola","precisao_passes","escanteios","impedimentos"]
                row_r  = ref.iloc[0]
                media  = df_est[categorias].mean()
                fig_r  = go.Figure()
                fig_r.add_trace(go.Scatterpolar(
                    r=[row_r[c] for c in categorias] + [row_r[categorias[0]]],
                    theta=categorias + [categorias[0]], fill="toself",
                    name=row_r["clube"], line_color=COR_AMARELO
                ))
                fig_r.add_trace(go.Scatterpolar(
                    r=[media[c] for c in categorias] + [media[categorias[0]]],
                    theta=categorias + [categorias[0]], fill="toself",
                    name="Média geral", opacity=0.35, line_color=COR_VERDE
                ))
                fig_r.update_layout(title=f"Radar — {row_r['clube']} vs Média", template=TEMPLATE)
                st.plotly_chart(fig_r, use_container_width=True)

        st.markdown("---")

        # Heatmap correlação
        col_c, col_d = st.columns(2)
        with col_c:
            metricas_num = ["chutes","chutes_a_gol","posse_bola","passes","precisao_passes","faltas","escanteios"]
            corr = df_est[metricas_num].corr().round(2)
            fig_h = px.imshow(corr, text_auto=True, color_continuous_scale="RdYlGn",
                              title="Correlação entre Métricas", template=TEMPLATE)
            st.plotly_chart(fig_h, use_container_width=True)
        with col_d:
            fig_s = px.scatter(df_est, x="posse_bola", y="chutes_a_gol",
                               size="passes", color="clube", text="clube",
                               title="Posse × Chutes a Gol", template=TEMPLATE)
            fig_s.update_traces(textposition="top center")
            st.plotly_chart(fig_s, use_container_width=True)

        st.markdown("---")
        st.dataframe(df_est.round(2), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 5 — PARTIDAS
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    where_clube_p = ""
    if clube_sel != "Todos":
        where_clube_p = f"AND (m.nome_clube = '{clube_sel}' OR v.nome_clube = '{clube_sel}')"

    df_res = q(f"""
        SELECT t.data_completa AS data,
               m.nome_clube AS mandante, p.placar_mandante, p.placar_visitante,
               v.nome_clube AS visitante, p.vencedor, a.nome_arena AS arena
        FROM fato_partidas p
        JOIN dim_clube m ON p.sk_mandante = m.sk_clube
        JOIN dim_clube v ON p.sk_visitante = v.sk_clube
        JOIN dim_tempo t ON p.sk_tempo = t.sk_tempo
        JOIN dim_arena a ON p.sk_arena = a.sk_arena
        {camp_where_p}
        {where_clube_p}
        ORDER BY t.data_completa
    """)

    st.markdown(f"### 📋 Partidas — {titulo_camp}")

    if df_res.empty:
        st.info("Sem partidas para este filtro.")
    else:
        df_res["total_gols"] = df_res["placar_mandante"] + df_res["placar_visitante"]
        total_gols = int(df_res["total_gols"].sum())
        media_gpp  = round(total_gols / len(df_res), 2) if len(df_res) else 0
        jogo_mais_gols = df_res.loc[df_res["total_gols"].idxmax()]
        clean_sheets   = int(((df_res["placar_mandante"] == 0) | (df_res["placar_visitante"] == 0)).sum())
        empates_total  = int((df_res["vencedor"] == "Empate").sum())
        goleadas       = int((df_res["total_gols"] >= 5).sum())

        if clube_sel != "Todos":
            vit = int((df_res["vencedor"] == clube_sel).sum())
            emp = int((((df_res["mandante"] == clube_sel) | (df_res["visitante"] == clube_sel)) &
                       (df_res["vencedor"] == "Empate")).sum())
            der = len(df_res) - vit - emp
            aprov_c = round(vit*3 / (len(df_res)*3) * 100, 1)
            st.markdown(f"""<div class="kpi-grid">
                {kpi("✅ Vitórias", vit, f"{round(vit/len(df_res)*100,1)}% dos jogos", "green")}
                {kpi("🤝 Empates", emp, f"{round(emp/len(df_res)*100,1)}% dos jogos", "blue")}
                {kpi("❌ Derrotas", der, f"{round(der/len(df_res)*100,1)}% dos jogos", "red")}
                {kpi("📈 Aproveitamento", f"{aprov_c}%", f"{len(df_res)} jogos", "gold")}
                {kpi("⚽ Gols no período", total_gols, f"média {media_gpp}/jogo", "green")}
                {kpi("🧤 Clean Sheets", clean_sheets, "jogos sem sofrer gol", "purple")}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="kpi-grid">
                {kpi("🎮 Total de Partidas", len(df_res), "", "blue")}
                {kpi("⚽ Total de Gols", total_gols, "", "green")}
                {kpi("📊 Média Gols/Jogo", media_gpp, "", "green")}
                {kpi("🤝 Empates", empates_total, f"{round(empates_total/len(df_res)*100,1)}% das partidas", "blue")}
                {kpi("🧤 Clean Sheets", clean_sheets, "placar sem gol de um lado", "purple")}
                {kpi("💥 Goleadas (5+ gols)", goleadas, "partidas com 5+ gols", "gold")}
                {kpi("🔥 Maior Placar", f"{jogo_mais_gols['mandante']} {int(jogo_mais_gols['placar_mandante'])}x{int(jogo_mais_gols['placar_visitante'])} {jogo_mais_gols['visitante']}", f"{jogo_mais_gols['total_gols']} gols", "red")}
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            df_res["data"] = pd.to_datetime(df_res["data"])
            gols_data = df_res.groupby("data")["total_gols"].sum().reset_index()
            fig = px.line(gols_data, x="data", y="total_gols",
                          title="Gols ao Longo do Campeonato", markers=True,
                          template=TEMPLATE, color_discrete_sequence=[COR_VERDE])
            fig.update_traces(fill="tozeroy", fillcolor="rgba(46,164,79,0.15)")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            arena_res = df_res.groupby("arena").agg(
                partidas=("vencedor","count"), gols=("total_gols","sum")
            ).reset_index().sort_values("gols", ascending=False).head(15)
            fig2 = px.bar(arena_res, x="arena", y="gols", text="gols",
                          title="Gols por Arena (Top 15)", color="partidas",
                          color_continuous_scale=[[0,"#1a1a6b"],[1,COR_ROXO]],
                          template=TEMPLATE)
            fig2.update_xaxes(tickangle=45)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        col_c, col_d = st.columns(2)
        with col_c:
            res_dist = df_res["vencedor"].value_counts().reset_index()
            res_dist.columns = ["resultado","qtd"]
            fig3 = px.pie(res_dist, names="resultado", values="qtd", hole=0.4,
                          title="Distribuição de Resultados", template=TEMPLATE,
                          color_discrete_sequence=[COR_VERDE, COR_AMARELO, COR_VERMELHO])
            st.plotly_chart(fig3, use_container_width=True)
        with col_d:
            fig4 = px.histogram(df_res, x="total_gols", nbins=12,
                                title="Distribuição de Gols por Partida",
                                color_discrete_sequence=[COR_AZUL], template=TEMPLATE,
                                labels={"total_gols":"Total de Gols na Partida"})
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown("---")
        busca = st.text_input("🔍 Buscar clube:")
        df_exib = df_res[["data","mandante","placar_mandante","placar_visitante",
                           "visitante","vencedor","arena"]].copy()
        df_exib["data"] = df_exib["data"].dt.strftime("%d/%m/%Y")
        df_exib.columns = ["Data","Mandante","GM","GV","Visitante","Vencedor","Arena"]
        if busca:
            mask = (df_exib["Mandante"].str.contains(busca, case=False, na=False) |
                    df_exib["Visitante"].str.contains(busca, case=False, na=False))
            df_exib = df_exib[mask]
        st.dataframe(df_exib, use_container_width=True, height=400)

