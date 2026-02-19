import os
import json
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import streamlit.components.v1 as components
import matplotlib as mpl


from sqlalchemy import create_engine, text




# -----------------------------
# MATPLOTLIB GLOBAL STYLE
# -----------------------------
mpl.rcParams["font.family"] = "sans-serif"
mpl.rcParams["font.sans-serif"] = ["Segoe UI", "Roboto", "Arial", "DejaVu Sans"]
mpl.rcParams["text.color"] = "white"
mpl.rcParams["axes.labelcolor"] = "white"
mpl.rcParams["xtick.color"] = "white"
mpl.rcParams["ytick.color"] = "white"
mpl.rcParams["axes.edgecolor"] = "white"


# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Match Centre", layout="wide")


MATCHES_TABLE = "eredivisie_matches"
MONTE_TABLE = "monte carlo"  # als er spaties in je tabelnaam zitten: laat quotes in SQL staan


EXPECTED_COLOR = "#7B68EE"
ACTUAL_COLOR = "#E32636"


# -----------------------------
# APP STYLING
# -----------------------------
st.markdown(
    """
    <style>
      .stApp { background: #0B1220 !important; }
      [data-testid="stAppViewContainer"] { background: #0B1220 !important; }
      [data-testid="stHeader"] { background: rgba(11, 18, 32, 0.65) !important; }


      h2, h3 {
        color: white !important;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
        font-weight: 700;
        margin-bottom: 10px;
      }


      div[data-testid="stMarkdownContainer"] h3 {
        margin-top: 0px;
        padding-top: 0px;
      }


      .hero {
        padding: 18px 22px;
        border-radius: 18px;
        background: linear-gradient(90deg, #0B1220 0%, #121B2F 55%, #0B1220 100%);
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 14px;
      }
      .hero h1 { color: white; margin: 0; font-size: 28px; }
      .hero p  { color: rgba(255,255,255,0.7); margin: 6px 0 0 0; }


      .chip {
        display: inline-block;
        padding: 6px 10px;
        margin-right: 8px;
        border-radius: 999px;
        background: rgba(123,104,238,0.16);
        border: 1px solid rgba(123,104,238,0.35);
        color: white;
        font-size: 12px;
      }


      .card {
        padding: 14px 14px;
        border-radius: 16px;
        background: #0F172A;
        border: 1px solid rgba(255,255,255,0.08);
        color: white;
        min-height: 92px;
      }
      .muted { color: rgba(255,255,255,0.65); font-size: 12px; }
      .big   { font-size: 18px; font-weight: 700; margin-top: 6px; }


      div[data-testid="stTextInput"] label,
      div[data-testid="stCheckbox"] label {
        color: rgba(255,255,255,0.80) !important;
      }
      div[data-testid="stTextInput"] input {
        background: #0F172A !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        color: rgba(255,255,255,0.90) !important;
        border-radius: 12px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# DB CONNECTION
# -----------------------------
# Pas dit aan naar jouw situatie (env var / secrets)
# Voorbeeld:
# DATABASE_URL = st.secrets["DATABASE_URL"]
DATABASE_URL = st.secrets["DB_URL"]
if not DATABASE_URL:
    st.error("DATABASE_URL ontbreekt. Zet env var DATABASE_URL of gebruik st.secrets.")
    st.stop()


engine = create_engine(DATABASE_URL)


# -----------------------------
# HELPERS (plaats jouw bestaande functies hier)
# -----------------------------
def parse_score(s):
    try:
        if not isinstance(s, str) or "-" not in s:
            return (None, None)
        a, b = s.split("-", 1)
        return (int(a.strip()), int(b.strip()))
    except Exception:
        return (None, None)


def points_from_goals(hg, ag):
    if hg is None or ag is None:
        return (0, 0)
    if hg > ag:
        return (3, 0)
    if hg < ag:
        return (0, 3)
    return (1, 1)


def monte_label(row):
    hg = row.get("home_goals_sim")
    ag = row.get("away_goals_sim")


    if pd.isna(hg) or pd.isna(ag):
        return None


    try:
        hg = int(round(hg))
        ag = int(round(ag))
    except Exception:
        return None


    return f"{hg} : {ag}"   # gebruik – (en-dash), of "-" als je dat liever hebt


def monte_prob_label(row):
    ph = row.get("p_home_win")
    pd_ = row.get("p_draw")
    pa = row.get("p_away_win")


    if pd.isna(ph) or pd.isna(pd_) or pd.isna(pa):
        return None


    return f"H {ph*100:.1f}% – D {pd_*100:.1f}% – A {pa*100:.1f}%"


import re
import pandas as pd


def parse_score(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return (None, None)


    s = str(s).strip()
    # normalize dashes
    s = s.replace("–", "-").replace("—", "-")
    # allow "0 - 0" / "0-0" / "0:0"
    m = re.search(r"(\d+)\s*[-:]\s*(\d+)", s)
    if not m:
        return (None, None)
    return (int(m.group(1)), int(m.group(2)))






# -----------------------------
# LOADERS (DB ONLY)  ✅ join via match_id
# -----------------------------
PLAYER = "player_stats"  # jouw view


@st.cache_data(show_spinner=False)
def load_players_view() -> pd.DataFrame:
    q = text(f'SELECT * FROM "{PLAYER}"')
    return pd.read_sql(q, engine)


players = load_players_view()


@st.cache_data(show_spinner=False)
def load_matches_db() -> pd.DataFrame:
    q = text(f"""
        SELECT
            "matchId" AS match_id,
            "startDate",
            "startTime",
            "venueName",
            "attendance",
            "score",
            "home_team",
            "away_team",
            (("home"::jsonb -> 0 ->> 'teamId')::int) AS home_teamId,
            (("away"::jsonb -> 0 ->> 'teamId')::int) AS away_teamId
        FROM "{MATCHES_TABLE}"
    """)
    return pd.read_sql(q, engine)


@st.cache_data(show_spinner=False)
def load_monte_db() -> pd.DataFrame:
    # BELANGRIJK: zorg dat jouw monte-table ook matchId heeft!
    # Als kolom anders heet, pas hier aan en alias altijd naar match_id.
    q = text(f"""
        SELECT
            "matchId" AS match_id,
             "home_teamId",
             "away_teamId",
            "home_goals_sim",
            "away_goals_sim",
            "p_home_win",
            "p_draw",
            "p_away_win",
            "exp_home_points",
            "exp_away_points"
        FROM "{MONTE_TABLE}"
    """)
    return pd.read_sql(q, engine)


# -----------------------------
# MAIN DATA PIPELINE (DB ONLY) ✅
# -----------------------------
matches = load_matches_db()
monte = load_monte_db()


# types
matches["match_id"] = pd.to_numeric(matches["match_id"], errors="coerce")
monte["match_id"] = pd.to_numeric(monte["match_id"], errors="coerce")


for col in ["home_teamId", "away_teamId"]:
    if col in matches.columns:
        matches[col] = pd.to_numeric(matches[col], errors="coerce")
    if col in monte.columns:
        monte[col] = pd.to_numeric(monte[col], errors="coerce")


if "startDate" in matches.columns:
    matches["startDate"] = pd.to_datetime(matches["startDate"], errors="coerce").dt.date.astype(str)
if "startDate" in monte.columns:
    monte["startDate"] = pd.to_datetime(monte["startDate"], errors="coerce").dt.date.astype(str)


# ✅ join only on match_id
df = matches.merge(monte, on="match_id", how="left", suffixes=("", "_monte"))


# derived columns
df["monte_outcome"] = df.apply(monte_label, axis=1)
df["monte_prob"] = df.apply(monte_prob_label, axis=1)
df[["hg", "ag"]] = df["score"].apply(lambda s: pd.Series(parse_score(s)))
df[["home_pts", "away_pts"]] = df.apply(lambda r: pd.Series(points_from_goals(r["hg"], r["ag"])), axis=1)




# -----------------------------
# HEADER
# -----------------------------
total_matches = len(df)


st.markdown(
    f"""
    <div class="hero">
      <h1>Eredivisie Match Centre</h1>
      <p>Wedstrijden + Monte Carlo voorspellingen    
      <div style="margin-top:10px;">
        <span class="chip">Matches: {total_matches}</span>
        <span class="chip">Mode: DB</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)




top_goals = (
    players[["playername", "goals"]]
    .dropna()
    .sort_values("goals", ascending=False)
    .head(3)
)


top_assists = (
    players[["playername", "assists"]]
    .dropna()
    .sort_values("assists", ascending=False)
    .head(3)
)


top_dribbles = (
    players[["playername", "dribbles_attempted"]]
    .dropna()
    .sort_values("dribbles_attempted", ascending=False)
    .head(3)
)


def top3_card(title, df, value_col, unit, height=220):
    if df.empty:
        return f"""
        <div class="card" style="height:{height}px;">
          <div class="muted">{title}</div>
          <div class="big">—</div>
          <div class="muted">Geen data</div>
        </div>
        """


    p1 = df.iloc[0]
    p2 = df.iloc[1] if len(df) > 1 else None
    p3 = df.iloc[2] if len(df) > 2 else None


    return f"""
    <div class="card" style="display:flex; flex-direction:column; height:{height}px;">
      <div class="muted">{title}</div>


      <!-- 1/2 -->
      <div style="flex:2; display:flex; flex-direction:column; justify-content:center; margin-top:8px;">
        <div class="big">{p1["playername"]}</div>
        <div class="muted">{int(p1[value_col])} {unit}</div>
      </div>


      <!-- 1/4 -->
      <div style="flex:1; border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;">
        <div style="font-weight:600;">{p2["playername"] if p2 is not None else "—"}</div>
        <div class="muted">{int(p2[value_col]) if p2 is not None else "—"} {unit}</div>
      </div>


      <!-- 1/4 -->
      <div style="flex:1; border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;">
        <div style="font-weight:600;">{p3["playername"] if p3 is not None else "—"}</div>
        <div class="muted">{int(p3[value_col]) if p3 is not None else "—"} {unit}</div>
      </div>
    </div>
    """


c1, c2, c3 = st.columns(3, gap="medium")


with c1:
    st.markdown(
        top3_card(
            title="Top 3 goalscorers",
            df=top_goals,
            value_col="goals",
            unit="goals",
            height=220,
        ),
        unsafe_allow_html=True,
    )


with c2:
    st.markdown(
        top3_card(
            title="Top 3 assist providers",
            df=top_assists,
            value_col="assists",
            unit="assists",
            height=220,
        ),
        unsafe_allow_html=True,
    )


with c3:
    st.markdown(
        top3_card(
            title="Top 3 dribble merchants",
            df=top_dribbles,
            value_col="dribbles_attempted",
            unit="dribbles",
            height=220,
        ),
        unsafe_allow_html=True,
    )










# -----------------------------
# MAIN ROW: table (2/3) + ranking plot (1/3)
# -----------------------------
import os, base64
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

team_filter = st.text_input("Filter op team (home/away bevat):", "")

# ============================================================
# 2 kolommen: tabel 2x zo breed als chart
# ============================================================
left, right = st.columns([2, 1], gap="large")




# =========================
# LEFT: Matches table
# =========================
with left:
    st.subheader("Matches")

    view = df.copy()
    if team_filter.strip():
        t = team_filter.strip().lower()
        view = view[
            view["home_team"].astype(str).str.lower().str.contains(t)
            | view["away_team"].astype(str).str.lower().str.contains(t)
        ]


    cols = []
    for c in ["match_id","startTime", "home_team", "away_team", "score", "monte_outcome", "monte_prob"]:
        if c in view.columns:
            cols.append(c)


    table = view[cols].copy()


    # percentage formatting (als aanwezig)
    for col in ["p_home_win", "p_draw", "p_away_win"]:
        if col in table.columns:
            table[col] = (pd.to_numeric(table[col], errors="coerce") * 100).round(1)


    # --- voeg "Open" button toe (matchId nodig, maar niet tonen) ---
    if "matchId" in view.columns:
        table = view[cols].copy()


        def _open_btn(mid):
            return f'<a class="open-btn" href="?matchId={int(mid)}">Open</a>'


        table["Open"] = view["matchId"].apply(_open_btn)
    else:
        table = view[cols].copy()


    # --- HTML tabel (in iframe) ---
    table_html = table.to_html(index=False, escape=False)


    components.html(
        f"""
        <style>
        body {{
            margin: 0;
            background: transparent;
            font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
        }}


        .open-btn {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 10px;
            background: rgba(123,104,238,0.18);
            border: 1px solid rgba(123,104,238,0.45);
            color: rgba(255,255,255,0.92);
            text-decoration: none;
            font-weight: 700;
            font-size: 12px;
        }}
        .open-btn:hover {{
            background: rgba(123,104,238,0.30);
        }}


        .table-card {{
            background: #0F172A;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 10px;
            height: 520px;
            overflow: hidden;
            box-sizing: border-box;
        }}


        .table-wrap {{
            height: 100%;
            overflow: auto;
            border-radius: 12px;
        }}


        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}


        thead th {{
            position: sticky;
            top: 0;
            z-index: 5;
            background: rgba(255,255,255,0.04);
            color: rgba(255,255,255,0.95);
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
            white-space: nowrap;
        }}


        tbody td {{
            background: #0F172A;
            color: rgba(255,255,255,0.88);
            padding: 9px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            white-space: nowrap;
        }}


        tbody tr:nth-child(even) td {{
            background: rgba(255,255,255,0.02);
        }}


        tbody tr:hover td {{
            background: rgba(123,104,238,0.10);
        }}


        .table-wrap::-webkit-scrollbar {{ height: 10px; width: 10px; }}
        .table-wrap::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.16); border-radius: 999px; }}
        .table-wrap::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.06); }}
        </style>


        <div class="table-card">
          <div class="table-wrap">
            {table_html}
          </div>
        </div>
        """,
        height=560,          # 👈 zelfde hoogte als chart
        scrolling=False,
    )




# =========================
# RIGHT: Ranking plot (Plotly + logos buiten de plot)
# =========================
with right:
    st.subheader("Ranking: Actual vs Expected")


    import os, base64
    import numpy as np
    import plotly.graph_objects as go


    ACTUAL_COLOR = "#E32636"    # rood
    EXPECTED_COLOR = "#7B68EE"  # paars


    # -----------------------------
    # helpers: logo -> data uri
    # -----------------------------
    def img_to_data_uri(path: str) -> str | None:
        if not path or not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"


    def team_logo_uri(team_id: int) -> str | None:
        p1 = f"logo/{team_id}.png"
        p2 = f"logos/{team_id}.png"
        if os.path.exists(p1):
            return img_to_data_uri(p1)
        if os.path.exists(p2):
            return img_to_data_uri(p2)
        return None


    # 1) Alleen wedstrijden met Monte Carlo simulatie
    # -----------------------------
    sim = df.copy()
    sim["home_goals_sim"] = pd.to_numeric(sim.get("home_goals_sim"), errors="coerce")
    sim["away_goals_sim"] = pd.to_numeric(sim.get("away_goals_sim"), errors="coerce")
    sim = sim.dropna(subset=["home_goals_sim", "away_goals_sim"])

    if sim.empty:
        st.warning("Geen Monte Carlo simulaties gevonden.")
    else:
        # -----------------------------
        # 2) Actual goals / points
        # -----------------------------
        sim[["hg", "ag"]] = sim["score"].apply(lambda s: pd.Series(parse_score(s)))
        sim = sim.dropna(subset=["hg", "ag"]).copy()

        sim[["home_pts", "away_pts"]] = sim.apply(
            lambda r: pd.Series(points_from_goals(int(r["hg"]), int(r["ag"]))),
            axis=1
        )

        # -----------------------------
        # 3) Expected points (DIRECT: gebruik exp_home_points / exp_away_points)
        # -----------------------------
        sim["exp_home_points"] = pd.to_numeric(sim.get("exp_home_points"), errors="coerce")
        sim["exp_away_points"] = pd.to_numeric(sim.get("exp_away_points"), errors="coerce")
        sim = sim.dropna(subset=["exp_home_points", "exp_away_points"])

        # -----------------------------
        # 4) Aggregatie per team
        # -----------------------------
        home_actual = (
            sim.groupby(["home_teamId", "home_team"], as_index=False)["home_pts"]
            .sum()
            .rename(columns={"home_teamId": "teamId", "home_team": "Team", "home_pts": "ActualPts"})
        )
        away_actual = (
            sim.groupby(["away_teamId", "away_team"], as_index=False)["away_pts"]
            .sum()
            .rename(columns={"away_teamId": "teamId", "away_team": "Team", "away_pts": "ActualPts"})
        )
        actual_pts = (
            pd.concat([home_actual, away_actual], ignore_index=True)
            .groupby(["teamId", "Team"], as_index=False)["ActualPts"]
            .sum()
        )

        home_exp = (
            sim.groupby(["home_teamId", "home_team"], as_index=False)["exp_home_points"]
            .sum()
            .rename(columns={"home_teamId": "teamId", "home_team": "Team", "exp_home_points": "ExpectedPts"})
        )
        away_exp = (
            sim.groupby(["away_teamId", "away_team"], as_index=False)["exp_away_points"]
            .sum()
            .rename(columns={"away_teamId": "teamId", "away_team": "Team", "exp_away_points": "ExpectedPts"})
        )
        expected_pts = (
            pd.concat([home_exp, away_exp], ignore_index=True)
            .groupby(["teamId", "Team"], as_index=False)["ExpectedPts"]
            .sum()
        )

        table_pts = (
            actual_pts.merge(expected_pts, on=["teamId", "Team"], how="outer")
            .fillna(0)
        )

        # -----------------------------
        # 5) Unieke posities (geen ties)
        # -----------------------------
        table_pts = table_pts.sort_values(["ActualPts", "Team"], ascending=[False, True]).reset_index(drop=True)
        table_pts["ActualPos"] = range(1, len(table_pts) + 1)

        tmp = table_pts.sort_values(["ExpectedPts", "Team"], ascending=[False, True]).reset_index(drop=True)
        tmp["ExpectedPos"] = range(1, len(tmp) + 1)

        table_pts = table_pts.merge(tmp[["teamId", "ExpectedPos"]], on="teamId", how="left")
        table_pts = table_pts.sort_values("ActualPos").reset_index(drop=True)



        # -----------------------------
        # 6) Plot (Plotly)
        # -----------------------------
        n = len(table_pts)
        fig = go.Figure()


        # verbindingslijnen Expected -> Actual
        for _, r in table_pts.iterrows():
            y = int(r["ActualPos"])
            fig.add_trace(
                go.Scatter(
                    x=[int(r["ExpectedPos"]), int(r["ActualPos"])],
                    y=[y, y],
                    mode="lines",
                    line=dict(width=2, color="rgba(255,255,255,0.22)"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


        # Expected markers
        fig.add_trace(
            go.Scatter(
                x=table_pts["ExpectedPos"],
                y=table_pts["ActualPos"],
                mode="markers+text",
                text=table_pts["ExpectedPos"].astype(int).astype(str),
                textposition="middle center",
                textfont=dict(size=11, color="white"),
                marker=dict(
                    size=22,
                    color=EXPECTED_COLOR,
                    line=dict(width=1, color="rgba(255,255,255,0.35)")
                ),
                name="Expected",
                hovertemplate="<b>%{customdata[0]}</b><br>Expected pos: %{x}<br>Actual pos: %{y}<extra></extra>",
                customdata=np.stack([table_pts["Team"]], axis=-1),
            )
        )


        # Actual markers
        fig.add_trace(
            go.Scatter(
                x=table_pts["ActualPos"],
                y=table_pts["ActualPos"],
                mode="markers+text",
                text=table_pts["ActualPos"].astype(int).astype(str),
                textposition="middle center",
                textfont=dict(size=11, color="white"),
                marker=dict(
                    size=22,
                    color=ACTUAL_COLOR,
                    line=dict(width=1, color="rgba(255,255,255,0.35)")
                ),
                name="Actual",
                hovertemplate="<b>%{customdata[0]}</b><br>Actual pos: %{x}<br>Expected pos: %{customdata[1]}<extra></extra>",
                customdata=np.stack([table_pts["Team"], table_pts["ExpectedPos"]], axis=-1),
            )
        )


        # logo’s links BUITEN de plot
        layout_images = []
        for _, r in table_pts.iterrows():
            uri = team_logo_uri(int(r["teamId"]))
            if not uri:
                continue
            y = int(r["ActualPos"])
            layout_images.append(
                dict(
                    source=uri,
                    xref="paper", yref="y",
                    x=-0.12, y=y,          # 👈 buiten de plot
                    sizex=0.07, sizey=0.90, # 👈 logo size
                    xanchor="left", yanchor="middle",
                    layer="above",
                    opacity=1.0
                )
            )


        fig.update_layout(
            height=560,  # match met tabel
            # 🚫 geen width hier (use_container_width=True regelt het)
            margin=dict(l=80, r=24, t=50, b=40),  # 👈 ruimte voor logo’s links
            paper_bgcolor="#0B1220",
            plot_bgcolor="#0F172A",
            title=dict(
                text="Ranking: Actual vs Expected",
                x=0.0,
                xanchor="left",
                font=dict(size=18, color="white")
            ),
            font=dict(color="white"),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1,
                bgcolor="rgba(0,0,0,0)",
                font=dict(color="white", size=12)
            ),
            images=layout_images,
        )


        fig.update_xaxes(
            title_text="Position",
            range=[0.5, n + 0.5],
            tickmode="linear",
            dtick=1,
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
            linecolor="rgba(255,255,255,0.20)",
        )


        fig.update_yaxes(
            title_text="",
            range=[n + 0.5, 0.5],      # invert: 1 bovenaan
            tickmode="array",
            tickvals=list(range(1, n + 1)),
            ticktext=[""] * n,         # 👈 geen teamnamen (alleen logo’s)
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False,
            linecolor="rgba(255,255,255,0.20)",
        )


        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
