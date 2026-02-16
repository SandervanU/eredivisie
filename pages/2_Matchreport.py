# ============================================================
# STREAMLIT MATCH SELECT + EVENTS LOAD
# ============================================================

# -------------------------
# IMPORTS
# -------------------------
import os
import json
import base64

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
from mplsoccer import VerticalPitch

import plotly.graph_objects as go


# -------------------------
# THEME
# -------------------------
HOME_COLOR = "#7B68EE"   # paars
AWAY_COLOR = "#E32636"   # rood

THEME_BG = "#0B1220"
THEME_PANEL = "#0F172A"
THEME_TEXT = "rgba(255,255,255,0.90)"
THEME_MUTED = "rgba(255,255,255,0.65)"

PITCH_COLOR = "#101827"      # iets rijker dan #171717, past bij bg
PITCH_LINE_COLOR = "#2B3650" # subtiel blauwgrijs
PITCH_TEXT = "white"


# -------------------------
# CONFIG
# -------------------------
DATABASE_URL = st.secrets["DB_URL"]
MATCHES_TABLE = "eredivisie_matches"
EVENTS_TABLE = "eredivisie_events"

engine = create_engine(DATABASE_URL)


# -------------------------
# PAGE
# -------------------------
st.set_page_config(layout="wide")
st.markdown(
    f"""
    <style>
      .stApp {{ background: {THEME_BG} !important; }}
      [data-testid="stAppViewContainer"] {{ background: {THEME_BG} !important; }}
      [data-testid="stHeader"] {{ background: rgba(11, 18, 32, 0.65) !important; }}

      h2, h3 {{
        color: white !important;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
        font-weight: 700;
        margin-bottom: 10px;
      }}

      div[data-testid="stMarkdownContainer"] h3 {{
        margin-top: 0px;
        padding-top: 0px;
      }}

      .hero {{
        padding: 18px 22px;
        border-radius: 18px;
        background: linear-gradient(90deg, {THEME_BG} 0%, #121B2F 55%, {THEME_BG} 100%);
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 14px;
      }}
      .hero h1 {{ color: white; margin: 0; font-size: 28px; }}
      .hero p  {{ color: rgba(255,255,255,0.7); margin: 6px 0 0 0; }}

      .chip {{
        display: inline-block;
        padding: 6px 10px;
        margin-right: 8px;
        border-radius: 999px;
        background: rgba(123,104,238,0.16);
        border: 1px solid rgba(123,104,238,0.35);
        color: white;
        font-size: 12px;
      }}

      .card {{
        padding: 14px 14px;
        border-radius: 16px;
        background: {THEME_PANEL};
        border: 1px solid rgba(255,255,255,0.08);
        color: white;
        min-height: 92px;
      }}
      .muted {{ color: {THEME_MUTED}; font-size: 12px; }}
      .big   {{ font-size: 18px; font-weight: 700; margin-top: 6px; }}

      div[data-testid="stTextInput"] label,
      div[data-testid="stCheckbox"] label {{
        color: rgba(255,255,255,0.80) !important;
      }}
      div[data-testid="stTextInput"] input {{
        background: {THEME_PANEL} !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        color: {THEME_TEXT} !important;
        border-radius: 12px !important;
      }}

      div[data-testid="stSelectbox"] label {{
        color: rgba(255,255,255,0.80) !important;
      }}
      div[data-testid="stSelectbox"] div[role="combobox"] {{
        background: {THEME_PANEL} !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        color: {THEME_TEXT} !important;
        border-radius: 12px !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================
def parse_team_json(val):
    if val is None:
        return None
    if isinstance(val, (list, dict)):
        parsed = val
    else:
        s = str(val).strip()
        if '""' in s:
            s = s.replace('""', '"')
        parsed = json.loads(s)
    if isinstance(parsed, list):
        return parsed[0] if len(parsed) else None
    return parsed


def img_to_data_uri(path: str) -> str | None:
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# ============================================================
# DB LOADERS
# ============================================================
@st.cache_data(show_spinner=False)
def load_matches_db() -> pd.DataFrame:
    q = text(f"""
        SELECT
            "matchId" AS match_id,
            "score",
            "home_team",
            "away_team",
            "home" AS home_json,
            "away" AS away_json,
            (("home"::jsonb -> 0 ->> 'teamId')::int) AS "home_teamId",
            (("away"::jsonb -> 0 ->> 'teamId')::int) AS "away_teamId"
        FROM "{MATCHES_TABLE}"
    """)
    df = pd.read_sql(q, engine)

    if "home_teamId" not in df.columns and "home_teamid" in df.columns:
        df = df.rename(columns={"home_teamid": "home_teamId"})
    if "away_teamId" not in df.columns and "away_teamid" in df.columns:
        df = df.rename(columns={"away_teamid": "away_teamId"})
    return df


@st.cache_data(show_spinner=False)
def load_events(match_id: int) -> pd.DataFrame:
    q = text(f"""
        SELECT *
        FROM "{EVENTS_TABLE}"
        WHERE "matchId" = :match_id
        ORDER BY "id"
    """)
    return pd.read_sql(q, engine, params={"match_id": match_id})


# ============================================================
# FORMATION HELPERS
# ============================================================
def get_start_formation(team_data: dict) -> dict | None:
    formations = team_data.get("formations", []) if team_data else []
    if not formations:
        return None
    start_forms = [f for f in formations if f.get("startMinuteExpanded") == 0]
    return start_forms[0] if start_forms else sorted(formations, key=lambda f: f.get("startMinuteExpanded", 9999))[0]


def get_starting_xi_and_kitmap(team_data: dict):
    f0 = get_start_formation(team_data)
    if not f0:
        return set(), {}
    player_ids = f0.get("playerIds", [])
    jersey_nums = f0.get("jerseyNumbers", [])
    slots = f0.get("formationSlots", [])

    xi_ids = [
        int(pid) for pid, slot in zip(player_ids, slots)
        if isinstance(slot, (int, float)) and 1 <= int(slot) <= 11
    ]
    kit_map = {
        int(pid): int(jn)
        for pid, jn, slot in zip(player_ids, jersey_nums, slots)
        if isinstance(slot, (int, float)) and 1 <= int(slot) <= 11
    }
    return set(xi_ids), kit_map


# ============================================================
# EPV OVER TIME (PLOTLY)
# ============================================================
def plot_epv_over_time_plotly(
    events_df: pd.DataFrame,
    home_teamId: int, away_teamId: int,
    home_team: str, away_team: str,
    epv_col: str = "EPV",
    home_color: str = "#7B68EE",
    away_color: str = "#E32636",
    smooth_window: int = 3
):
    df = events_df.copy()

    if epv_col not in df.columns:
        for c in ["epv", "Epv", "xEPV", "epv_value"]:
            if c in df.columns:
                epv_col = c
                break
    if epv_col not in df.columns:
        return None, "Geen EPV kolom gevonden."

    # time
    if "second" in df.columns:
        df["t"] = df["minute"] + df["second"].fillna(0) / 60
    else:
        df["t"] = df["minute"]

    df = df.dropna(subset=["t", "teamId", epv_col])
    df[epv_col] = pd.to_numeric(df[epv_col], errors="coerce").fillna(0.0)
    df["t_min"] = df["t"].astype(int)

    home = df[df["teamId"] == home_teamId].groupby("t_min")[epv_col].sum()
    away = df[df["teamId"] == away_teamId].groupby("t_min")[epv_col].sum()

    t = np.arange(0, max(df["t_min"].max(), 90) + 1)
    home_vals = home.reindex(t, fill_value=0).values
    away_vals = away.reindex(t, fill_value=0).values

    if smooth_window and smooth_window > 1:
        kernel = np.ones(smooth_window) / smooth_window
        home_vals = np.convolve(home_vals, kernel, mode="same")
        away_vals = np.convolve(away_vals, kernel, mode="same")

    fig = go.Figure()

    # Home (boven)
    fig.add_trace(go.Scatter(
        x=t,
        y=home_vals,
        mode="lines",
        line=dict(color=home_color, width=2.5),
        fill="tozeroy",
        fillcolor=f"rgba{tuple(int(home_color[i:i+2],16) for i in (1,3,5)) + (0.15,)}",
        name=home_team
    ))

    # Away (onder)
    fig.add_trace(go.Scatter(
        x=t,
        y=-away_vals,
        mode="lines",
        line=dict(color=away_color, width=2.5),
        fill="tozeroy",
        fillcolor=f"rgba{tuple(int(away_color[i:i+2],16) for i in (1,3,5)) + (0.15,)}",
        name=away_team
    ))

    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.25)")

    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0B1220",
        plot_bgcolor="#0F172A",
        showlegend=False,
        font=dict(color="white", size=11),
        xaxis=dict(
            title="",
            tickmode="array",
            tickvals=list(range(0, 91, 15)),
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            title="",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
            showticklabels=False
        ),
    )

    # team labels
    fig.add_annotation(
        x=0, y=0.95, xref="paper", yref="paper",
        text=f"<b>{home_team}</b>",
        showarrow=False,
        font=dict(size=11)
    )
    fig.add_annotation(
        x=0, y=0.05, xref="paper", yref="paper",
        text=f"<b>{away_team}</b>",
        showarrow=False,
        font=dict(size=11)
    )

    return fig, None


# ============================================================
# PASS NETWORK (same logic, only colors themed)
# ============================================================
def pass_network_same_logic_as_old(
    events_df: pd.DataFrame,
    team_id: int,
    team_name: str,
    team_data: dict,
    *,
    team_color: str,
    max_line_width=6,
    marker_size=1500,
    edgewidth=3,
    marker_edge_color="w",
    kit_no_size=25,
):
    xi_ids, kit_map = get_starting_xi_and_kitmap(team_data)
    if not xi_ids:
        return None, f"Geen basis-11 (startformatie) gevonden voor {team_name}"

    df = events_df.copy()

    # minute of first substitution (same as old)
    sub_rows = df[(df["type"] == "SubstitutionOn") & (df["teamId"] == team_id)]
    if len(sub_rows) > 0:
        sub_minute = int(sub_rows["minute"].min())
        df = df[df["minute"] < sub_minute]
    else:
        sub_minute = int(df["minute"].max()) if len(df) else 90

    passes_df = df[df["teamId"] == team_id].reset_index(drop=True).copy()
    passes_df = passes_df.dropna(subset=["playerId"])
    passes_df["playerId"] = passes_df["playerId"].astype(float).astype("Int64")

    # recipient via shift(-1) EXACTLY like your code
    passes_df["passRecipientId"] = passes_df["playerId"].shift(-1)
    passes_df = passes_df.dropna(subset=["passRecipientId"])

    # filters
    passes_df = passes_df.loc[passes_df["type"] == "Pass", :].reset_index(drop=True)
    passes_df = passes_df.loc[passes_df["outcomeType"] == "Successful", :].reset_index(drop=True)

    passes_df = passes_df[passes_df["playerId"] != passes_df["passRecipientId"]]

    # no subs: keep only starting XI
    passes_df["playerId"] = passes_df["playerId"].astype(int)
    passes_df["passRecipientId"] = passes_df["passRecipientId"].astype(int)
    passes_df = passes_df[passes_df["playerId"].isin(xi_ids) & passes_df["passRecipientId"].isin(xi_ids)]

    if passes_df.empty:
        return None, f"Geen passes over na filters voor {team_name}"

    # map to kit numbers
    passes_df["playerKitNumber"] = passes_df["playerId"].map(lambda pid: kit_map.get(pid, pid))
    passes_df["playerKitNumberReceipt"] = passes_df["passRecipientId"].map(lambda pid: kit_map.get(pid, pid))

    average_locs_and_count = (
        passes_df.groupby("playerKitNumber")
        .agg(x=("x", "mean"), y=("y", "mean"), count=("y", "size"))
    )

    passes_between = (
        passes_df.groupby(["playerKitNumber", "playerKitNumberReceipt"])
        .size()
        .reset_index(name="pass_count")
    )

    passes_between = passes_between.merge(average_locs_and_count, left_on="playerKitNumber", right_index=True)
    passes_between = passes_between.merge(
        average_locs_and_count, left_on="playerKitNumberReceipt", right_index=True, suffixes=["", "_end"]
    )

    pass_filter = int(passes_between["pass_count"].mean())
    passes_between = passes_between.loc[passes_between["pass_count"] > pass_filter].reset_index(drop=True)

    if passes_between.empty:
        return None, f"Alles weggefilterd (mean threshold) voor {team_name}"

    passes_between["width"] = passes_between["pass_count"] / passes_between["pass_count"].max() * max_line_width

    min_transparency = 0.3
    c_transparency = passes_between["pass_count"] / passes_between["pass_count"].max()
    c_transparency = (c_transparency * (1 - min_transparency)) + min_transparency
    passes_between["alpha"] = c_transparency

    # plot (same size)
    fig, ax = plt.subplots(figsize=(16, 11))

    pitch = VerticalPitch(
        pitch_type="opta",
        pitch_color=PITCH_COLOR,
        line_color=PITCH_LINE_COLOR,
        goal_type="box"
    )
    pitch.draw(ax=ax)
    fig.patch.set_facecolor(THEME_BG)
    ax.set_facecolor(THEME_BG)

    # edges (ONLY color changed)
    for _, r in passes_between.iterrows():
        pitch.lines(
            r["x"], r["y"], r["x_end"], r["y_end"],
            lw=float(r["width"]),
            color=team_color,
            alpha=float(r["alpha"]),
            ax=ax,
            zorder=2
        )

    # nodes (ONLY color changed)
    for kit in average_locs_and_count.index:
        pitch.scatter(
            average_locs_and_count.loc[kit, "x"],
            average_locs_and_count.loc[kit, "y"],
            s=marker_size,
            color=team_color,
            edgecolors=marker_edge_color,
            linewidth=edgewidth,
            ax=ax,
            zorder=3
        )

    # labels (same)
    for kit in average_locs_and_count.index:
        pitch.annotate(
            int(kit),
            xy=(average_locs_and_count.loc[kit, "x"], average_locs_and_count.loc[kit, "y"]),
            c="white",
            va="center",
            ha="center",
            size=kit_no_size,
            weight="bold",
            ax=ax,
            zorder=4
        )

    ax.text(
        50, 104, f"{team_name} (Mins 1-{sub_minute})".upper(),
        size=10, fontweight="bold", ha="center", va="center", c=PITCH_TEXT
    )

    return fig, None


# ============================================================
# UI: HEADER + MATCH SELECT
# ============================================================
matches = load_matches_db()

with st.container():
    hc1, hc2 = st.columns([3, 1], gap="small")

    with hc1:
        st.markdown(
            """
            <div class="hero">
              <h1>Match Dashboard</h1>
              <p>Kies een match in de header.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with hc2:
        st.markdown(
            """
            <div class="hero" style="padding: 14px 16px;">
              <div style="color: rgba(255,255,255,0.80); font-weight: 700; margin-bottom: 8px;">
                Select match_id
              </div>
            """,
            unsafe_allow_html=True,
        )

        match_ids = matches["match_id"].sort_values().tolist()
        selected_match_id = st.selectbox(
            label="",
            options=match_ids,
            key="match_select_header",
            label_visibility="collapsed"
        )

        st.markdown("</div>", unsafe_allow_html=True)

with st.spinner("Loading events…"):
    events = load_events(selected_match_id)

row = matches.loc[matches["match_id"] == selected_match_id].iloc[0]
home_team = row["home_team"]
away_team = row["away_team"]
score = row["score"]
home_teamId = int(row["home_teamId"])
away_teamId = int(row["away_teamId"])

home_data = parse_team_json(row["home_json"])
away_data = parse_team_json(row["away_json"])

st.markdown(
    f"""
    <span class="chip">Match ID: {selected_match_id}</span>
    <span class="chip">Home: {home_team} ({home_teamId})</span>
    <span class="chip">Away: {away_team} ({away_teamId})</span>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MATCH STRIP (single, clean)
# ============================================================
home_logo_uri = img_to_data_uri(f"logo/{home_teamId}.png")
away_logo_uri = img_to_data_uri(f"logo/{away_teamId}.png")

score_text = f"{score}"
meta_text = f"Match ID {selected_match_id}"

components.html(
    f"""
    <style>
      .match-strip {{
        padding: 14px 16px;
        border-radius: 18px;
        background: {THEME_PANEL};
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 10px 30px rgba(0,0,0,0.22);
        color: white;
        font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      }}
      .ms-row {{
        display: grid;
        grid-template-columns: 1fr 220px 1fr;
        align-items: center;
        gap: 10px;
      }}
      .ms-team {{
        display:flex;
        align-items:center;
        gap:12px;
        min-width: 0;
      }}
      .ms-team.right {{ justify-content:flex-end; }}

      .ms-badge {{
        width:46px; height:46px;
        border:3px solid rgba(255,255,255,0.12);
        border-radius:999px;
        display:flex;
        align-items:center;
        justify-content:center;
        background: rgba(255,255,255,0.06);
        flex: 0 0 46px;
      }}
      .ms-badge img {{
        width:34px;
        height:34px;
        object-fit:contain;
        padding:3px;
        background:{THEME_BG};
        border-radius:999px;
      }}
      .dot {{ width:22px; height:22px; border-radius:999px; background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.12); }}

      .ms-name-wrap {{ min-width:0; }}
      .ms-name {{
        font-weight: 900;
        font-size: 20px;
        line-height: 1.05;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .ms-bar {{
        margin-top: 8px;
        height: 3px;
        width: 120px;
        border-radius: 999px;
      }}
      .ms-bar.right {{ margin-left: auto; }}

      .ms-center {{ text-align:center; }}
      .ms-score {{
        font-weight: 950;
        font-size: 28px;
        letter-spacing: 1px;
        line-height: 1.0;
      }}
      .ms-meta {{
        margin-top: 6px;
        color: rgba(255,255,255,0.55);
        font-size: 12px;
      }}
    </style>

    <div class="match-strip">
      <div class="ms-row">

        <div class="ms-team">
          <div class="ms-badge" style="border-color:{HOME_COLOR};">
            {f'<img src="{home_logo_uri}" />' if home_logo_uri else '<div class="dot"></div>'}
          </div>

          <div class="ms-name-wrap">
            <div class="ms-name">{home_team}</div>
            <div class="ms-bar" style="background:{HOME_COLOR};"></div>
          </div>
        </div>

        <div class="ms-center">
          <div class="ms-score">{score_text}</div>
          <div class="ms-meta">{meta_text}</div>
        </div>

        <div class="ms-team right">
          <div class="ms-name-wrap">
            <div class="ms-name" style="text-align:right;">{away_team}</div>
            <div class="ms-bar right" style="background:{AWAY_COLOR};"></div>
          </div>

          <div class="ms-badge" style="border-color:{AWAY_COLOR};">
            {f'<img src="{away_logo_uri}" />' if away_logo_uri else '<div class="dot"></div>'}
          </div>
        </div>

      </div>
    </div>
    """,
    height=120,
    scrolling=False
)


# ============================================================
# LAYOUT: LEFT | MIDDLE | RIGHT
# ============================================================
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

left_col, mid_col, right_col = st.columns([1.5, 4, 1.5], gap="small")

with left_col:
    with st.spinner("Building L1 (home pass network)…"):
        fig, err = pass_network_same_logic_as_old(
            events, home_teamId, home_team, home_data,
            team_color=HOME_COLOR,
            max_line_width=6, marker_size=1500, edgewidth=3,
            marker_edge_color="w",
            kit_no_size=25
        )
    if err:
        st.error(err)
    else:
        st.pyplot(fig, use_container_width=True)

    st.markdown(
        "<div class='card'><div class='muted'>L2</div><div class='big'>Placeholder (smalle visual)</div></div>",
        unsafe_allow_html=True
    )


# ============================================================
# LINEUP / PLAYER HELPERS
# ============================================================
def build_team_player_lookup(team_data: dict) -> dict:
    """
    team_data fallback: {playerId: name}
    Probeert meerdere velden want sources verschillen.
    """
    out = {}
    if not team_data:
        return out

    for p in team_data.get("players", []):
        pid = p.get("id") or p.get("playerId")
        if not pid:
            continue
        name = (
            p.get("name")
            or p.get("playerName")
            or p.get("shortName")
            or p.get("knownName")
            or p.get("lastName")
            or None
        )
        if name:
            out[int(pid)] = str(name)
    return out


def build_pid_to_shirt_map(team_data: dict) -> dict:
    """
    {playerId: shirtNo} voor basis + bank.
    """
    out = {}
    if not team_data:
        return out

    # uit players list
    for p in team_data.get("players", []):
        pid = p.get("id") or p.get("playerId")
        if not pid:
            continue
        shirt = p.get("shirt") or p.get("jerseyNumber")
        if shirt is not None and str(shirt).strip() != "":
            out[int(pid)] = int(shirt)

    # uit start formation (betrouwbaar voor basis)
    f0 = get_start_formation(team_data)
    if f0:
        for pid, jn in zip(f0.get("playerIds", []), f0.get("jerseyNumbers", [])):
            if pid is None or jn is None:
                continue
            out[int(pid)] = int(jn)

    return out


def build_player_name_lookup(events: pd.DataFrame) -> dict:
    """
    Events fallback: {playerId: name}, probeert veel voorkomende kolomnamen.
    """
    if events is None or events.empty or "playerId" not in events.columns:
        return {}

    name_cols = [c for c in ["playerName", "player_name", "name", "player", "shortName", "short_name"] if c in events.columns]
    if not name_cols:
        return {}

    tmp = events.dropna(subset=["playerId"]).copy()
    tmp["__name__"] = None
    for c in name_cols:
        vals = tmp[c].astype(str)
        vals = vals.where(~vals.isin(["None", "nan", "NaN", ""]), None)
        tmp["__name__"] = tmp["__name__"].fillna(vals)

    tmp = tmp.dropna(subset=["__name__"])
    if tmp.empty:
        return {}

    return tmp.groupby("playerId")["__name__"].first().to_dict()


def get_starting_players_simple(team_data: dict):
    """
    Returns list of tuples: [(shirt_no, player_id), ...] for starting XI
    """
    f0 = get_start_formation(team_data)
    if not f0:
        return []

    players = []
    for pid, jn, slot in zip(
        f0.get("playerIds", []),
        f0.get("jerseyNumbers", []),
        f0.get("formationSlots", [])
    ):
        if not isinstance(slot, (int, float)) or not (1 <= int(slot) <= 11):
            continue
        players.append((int(jn), int(pid)))

    return sorted(players, key=lambda x: x[0])


def get_bench_players(team_data: dict, starting_ids: set, pid_to_shirt: dict):
    """
    Bench als [(shirt_no, player_id)] gesorteerd op shirt_no.
    """
    bench = []
    if not team_data:
        return bench

    for p in team_data.get("players", []):
        pid = p.get("id") or p.get("playerId")
        if not pid:
            continue
        pid = int(pid)
        if pid in starting_ids:
            continue
        shirt = pid_to_shirt.get(pid)
        bench.append((shirt, pid))

    bench.sort(key=lambda x: (x[0] is None, x[0] if x[0] is not None else 9999))
    return bench


def pair_substitutions(events: pd.DataFrame, team_id: int):
    """
    Pair SubstitutionOff + SubstitutionOn per team & minute (op volgorde).
    Output (bewust simpel gehouden):
      off_map[off_pid] = minute
      on_map[on_pid]   = minute
    """
    if events is None or events.empty:
        return {}, {}

    df = events[events["teamId"] == team_id].copy()
    if df.empty or "type" not in df.columns or "minute" not in df.columns:
        return {}, {}

    on_df  = df[df["type"] == "SubstitutionOn"].dropna(subset=["playerId", "minute"]).copy()
    off_df = df[df["type"] == "SubstitutionOff"].dropna(subset=["playerId", "minute"]).copy()

    if on_df.empty and off_df.empty:
        return {}, {}

    if "id" in df.columns:
        on_df  = on_df.sort_values(["minute", "id"])
        off_df = off_df.sort_values(["minute", "id"])
    else:
        on_df  = on_df.sort_values(["minute"])
        off_df = off_df.sort_values(["minute"])

    off_map = {}
    on_map = {}

    for m in sorted(set(on_df["minute"].astype(int)) | set(off_df["minute"].astype(int))):
        ons  = on_df[on_df["minute"].astype(int) == m]["playerId"].astype(int).tolist()
        offs = off_df[off_df["minute"].astype(int) == m]["playerId"].astype(int).tolist()

        for off_pid in offs:
            off_map[int(off_pid)] = int(m)
        for on_pid in ons:
            on_map[int(on_pid)] = int(m)

    return off_map, on_map


def resolve_name(pid: int, name_lookup_events: dict, name_lookup_team: dict) -> str:
    return (
        name_lookup_events.get(pid)
        or name_lookup_team.get(pid)
        or f"ID {pid}"
    )


def sub_badge(direction: str, minute: int) -> str:
    """
    direction: "on" or "off"
    """
    if direction == "on":
        return f"<span style='color:#16A34A;font-weight:900'>↑</span><span style='font-size:12px;opacity:.75'>{minute}'</span>"
    return f"<span style='color:#E32636;font-weight:900'>↓</span><span style='font-size:12px;opacity:.75'>{minute}'</span>"

def _parse_qualifiers(val):
    """Return list of qualifier dicts (best effort)."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return [val]
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none"):
        return []
    # soms double quotes issues
    if '""' in s:
        s = s.replace('""', '"')
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
        return []
    except Exception:
        return []


def _parse_qualifiers(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return [val]
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none"):
        return []
    if '""' in s:
        s = s.replace('""', '"')
    try:
        out = json.loads(s)
        if isinstance(out, list):
            return out
        if isinstance(out, dict):
            return [out]
    except Exception:
        return []
    return []


def _is_keypass(qual_list) -> bool:
    for q in qual_list or []:
        if not isinstance(q, dict):
            continue

        candidates = []
        t = q.get("type")
        if isinstance(t, str):
            candidates.append(t)
        elif isinstance(t, dict):
            candidates += [t.get("value"), t.get("displayName"), t.get("name"), t.get("label")]

        candidates += [
            q.get("value"),
            q.get("displayName"),
            q.get("name"),
            q.get("qualifier"),
            q.get("qualifierType"),
        ]

        for c in candidates:
            if not c:
                continue
            txt = str(c).replace(" ", "").lower()
            if "keypass" in txt:
                return True
    return False


def _find_end_cols(df: pd.DataFrame):
    endx_col = next((c for c in ["endX", "x_end", "toX", "end_x", "passEndX"] if c in df.columns), None)
    endy_col = next((c for c in ["endY", "y_end", "toY", "end_y", "passEndY"] if c in df.columns), None)
    return endx_col, endy_col
from mplsoccer import Pitch

def plot_key_pass_zones_with_arrows(
    events: pd.DataFrame,
    team_id: int,
    team_name: str,
    team_color: str,
    *,
    direction: str,      # "LEFT" of "RIGHT"
    n_x: int = 6,
    n_y: int = 4,
):
    df = events.copy()
    if df is None or df.empty:
        return None, "Geen events."

    endx_col, endy_col = _find_end_cols(df)
    if endx_col is None or endy_col is None:
        return None, "Geen endX/endY kolommen gevonden."

    # filter key passes
    if "qualifiers" not in df.columns:
        return None, "Kolom qualifiers ontbreekt."

    df["__qual__"] = df["qualifiers"].apply(_parse_qualifiers)
    df["__is_keypass__"] = df["__qual__"].apply(_is_keypass)

    kp = df[(df["type"] == "Pass") & (df["teamId"] == team_id) & (df["__is_keypass__"] == True)].copy()
    if kp.empty:
        return None, "Geen key passes."

    # numeric coords
    for c in ["x", "y", endx_col, endy_col]:
        kp[c] = pd.to_numeric(kp[c], errors="coerce")
    kp = kp.dropna(subset=["x", "y", endx_col, endy_col])

    # flip coords if direction is LEFT (attack towards left goal)
    # (opta coords assumed 0..100)
    if direction.upper() == "LEFT":
        kp["x1"] = 100 - kp["x"]
        kp["y1"] = kp["y"]
        kp["x2"] = 100 - kp[endx_col]
        kp["y2"] = kp[endy_col]
    else:
        kp["x1"] = kp["x"]
        kp["y1"] = kp["y"]
        kp["x2"] = kp[endx_col]
        kp["y2"] = kp[endy_col]

    # zone counts based on END location (x2,y2)
    bins_x = np.linspace(0, 100, n_x + 1)
    bins_y = np.linspace(0, 100, n_y + 1)

    kp["x_bin"] = np.clip(np.digitize(kp["x1"], bins_x) - 1, 0, n_x - 1)
    kp["y_bin"] = np.clip(np.digitize(kp["y1"], bins_y) - 1, 0, n_y - 1)

    counts = kp.groupby(["x_bin", "y_bin"]).size().reset_index(name="count")

    # plot
    fig, ax = plt.subplots(figsize=(8, 4.6))
    pitch = Pitch(
        pitch_type="opta",
        pitch_color=PITCH_COLOR,
        line_color=PITCH_LINE_COLOR,
        goal_type="box"
    )
    pitch.draw(ax=ax)
    fig.patch.set_facecolor(THEME_BG)
    ax.set_facecolor(THEME_BG)

    # grid
    for x in bins_x:
        ax.plot([x, x], [0, 100], color=(1, 1, 1, 0.12), lw=1)
    for y in bins_y:
        ax.plot([0, 100], [y, y], color=(1, 1, 1, 0.12), lw=1)

    # arrows
    pitch.arrows(
        kp["x1"], kp["y1"], kp["x2"], kp["y2"],
        ax=ax,
        color=team_color,
        width=2.2,
        headwidth=4.2,
        headlength=4.2,
        alpha=0.9,
        zorder=3
    )

    # numbers in zones
    for _, r in counts.iterrows():
        cx = (bins_x[int(r["x_bin"])] + bins_x[int(r["x_bin"]) + 1]) / 2
        cy = (bins_y[int(r["y_bin"])] + bins_y[int(r["y_bin"]) + 1]) / 2
        ax.text(
            cx, cy, str(int(r["count"])),
            ha="center", va="center",
            fontsize=14,
            fontweight="bold",
            color="white",
            zorder=4
        )

    # title + direction of play
    dir_txt = direction.upper()
    arrow_char = "←" if dir_txt == "LEFT" else "→"
    ax.set_title(
        f"{team_name}\nKey Passes by zone  |  Direction of play {arrow_char} {dir_txt}",
        color="white",
        fontsize=12,
        fontweight="bold",
        pad=10
    )

    return fig, None


with mid_col:

    # Lookups
    name_lookup_events = build_player_name_lookup(events)
    home_name_team = build_team_player_lookup(home_data)
    away_name_team = build_team_player_lookup(away_data)

    home_pid_to_shirt = build_pid_to_shirt_map(home_data)
    away_pid_to_shirt = build_pid_to_shirt_map(away_data)

    home_players = get_starting_players_simple(home_data)
    away_players = get_starting_players_simple(away_data)

    home_ids = {pid for _, pid in home_players}
    away_ids = {pid for _, pid in away_players}

    home_bench = get_bench_players(home_data, home_ids, home_pid_to_shirt)
    away_bench = get_bench_players(away_data, away_ids, away_pid_to_shirt)

    home_off_map, home_on_map = pair_substitutions(events, home_teamId)
    away_off_map, away_on_map = pair_substitutions(events, away_teamId)

    # =========================================================
    # 3-KOLOMS: HOME | EPV | AWAY  (HORIZONTAAL)
    # =========================================================
    lu_home_col, epv_col, lu_away_col = st.columns([1.5, 4, 1.5], gap="small")

    # -------------------------
    # HOME LINE-UP (LINKS)
    # -------------------------
    with lu_home_col:
        st.markdown(
            f"<div style='font-weight:800;color:{HOME_COLOR};margin-bottom:6px'>{home_team}</div>",
            unsafe_allow_html=True
        )

        # basis
        for nr, pid in home_players:
            name = resolve_name(pid, name_lookup_events, home_name_team)

            badge = ""
            if pid in home_off_map:
                badge = sub_badge("off", home_off_map[pid])
            elif pid in home_on_map:
                badge = sub_badge("on", home_on_map[pid])

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;padding:3px 0;color:white;font-size:13px">
                  <div style="
                      width:26px;height:26px;border-radius:999px;
                      background:{HOME_COLOR};
                      border:2px solid white;
                      display:flex;align-items:center;justify-content:center;
                      font-weight:800;font-size:12px;
                      flex:0 0 26px;
                  ">{nr}</div>

                  <div style="
                      opacity:.95;
                      white-space:nowrap;
                      overflow:hidden;
                      text-overflow:ellipsis;
                      max-width:220px;
                  ">{name}</div>

                  <div style="display:flex;gap:6px;white-space:nowrap">{badge}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # bench
        st.markdown("<div style='opacity:.5;font-size:12px;color:white;margin:8px 0'> Bench </div>", unsafe_allow_html=True)

        for nr, pid in home_bench:
            name = resolve_name(pid, name_lookup_events, home_name_team)

            badge = ""
            if pid in home_on_map:
                badge = sub_badge("on", home_on_map[pid])
            elif pid in home_off_map:
                badge = sub_badge("off", home_off_map[pid])

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;padding:2px 0;color:white;font-size:12px;opacity:.9">
                  <div style="
                      width:22px;height:22px;border-radius:999px;
                      background:#374151;border:1px solid rgba(255,255,255,.4);
                      display:flex;align-items:center;justify-content:center
                  ">{nr if nr is not None else ''}</div>

                  <div style="
                      white-space:nowrap;
                      overflow:hidden;
                      text-overflow:ellipsis;
                      max-width:220px;
                  ">{name}</div>

                  <div style="display:flex;gap:6px;white-space:nowrap">{badge}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # -------------------------
    # EPV (MIDDEN)
    with epv_col:

        st.markdown(
            "<div style='font-weight:800;font-size:14px;color:white;margin-bottom:4px'>"
            "Expected Possession Value (EPV)"
            "</div>",
            unsafe_allow_html=True
        )

        fig, err = plot_epv_over_time_plotly(
            events,
            home_teamId,
            away_teamId,
            home_team,
            away_team,
            epv_col="EPV",
            home_color=HOME_COLOR,
            away_color=AWAY_COLOR
        )

        if err:
            st.error(err)
        else:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            "<div style='font-weight:800;font-size:14px;color:white;margin-bottom:4px'>"
            "Key Passes (Passes leading up to a shot)"
            "</div>",
            unsafe_allow_html=True
        )
        kp_left, kp_right = st.columns(2, gap="small")
        with kp_left:
            fig, err = plot_key_pass_zones_with_arrows(
                events,
                team_id=home_teamId,
                team_name=home_team,
                team_color=HOME_COLOR,
                direction="LEFT",     # HOME attack direction
                n_x=6, n_y=4
            )
            if err:
                st.error(err)
            else:
                st.pyplot(fig, use_container_width=True)

        with kp_right:
            fig, err = plot_key_pass_zones_with_arrows(
                events,
                team_id=away_teamId,
                team_name=away_team,
                team_color=AWAY_COLOR,
                direction="RIGHT",    # AWAY attack direction
                n_x=6, n_y=4
            )
            if err:
                st.error(err)
            else:
                st.pyplot(fig, use_container_width=True)


    # -------------------------
    # AWAY LINE-UP (RECHTS)
    # -------------------------
    with lu_away_col:
        st.markdown(
            f"<div style='font-weight:800;color:{AWAY_COLOR};margin-bottom:6px;text-align:right'>{away_team}</div>",
            unsafe_allow_html=True
        )

        # basis
        for nr, pid in away_players:
            name = resolve_name(pid, name_lookup_events, away_name_team)

            badge = ""
            if pid in away_off_map:
                badge = sub_badge("off", away_off_map[pid])
            elif pid in away_on_map:
                badge = sub_badge("on", away_on_map[pid])

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;justify-content:flex-end;gap:10px;padding:3px 0;color:white;font-size:13px">
                  <div style="display:flex;gap:6px;white-space:nowrap">{badge}</div>

                  <div style="
                      opacity:.95;
                      white-space:nowrap;
                      overflow:hidden;
                      text-overflow:ellipsis;
                      max-width:220px;
                      text-align:right
                  ">{name}</div>

                  <div style="
                      width:26px;height:26px;border-radius:999px;
                      background:{AWAY_COLOR};
                      border:2px solid white;
                      display:flex;align-items:center;justify-content:center;
                      font-weight:800;font-size:12px;
                      flex:0 0 26px;
                  ">{nr}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # bench
        st.markdown("<div style='opacity:.5;font-size:12px;color:white;margin:8px 0;text-align:right'> Bench </div>", unsafe_allow_html=True)

        for nr, pid in away_bench:
            name = resolve_name(pid, name_lookup_events, away_name_team)

            badge = ""
            if pid in away_on_map:
                badge = sub_badge("on", away_on_map[pid])
            elif pid in away_off_map:
                badge = sub_badge("off", away_off_map[pid])

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;justify-content:flex-end;gap:10px;padding:2px 0;color:white;font-size:12px;opacity:.9">
                  <div style="display:flex;gap:6px;white-space:nowrap">{badge}</div>

                  <div style="
                      white-space:nowrap;
                      overflow:hidden;
                      text-overflow:ellipsis;
                      max-width:220px;
                      text-align:right
                  ">{name}</div>

                  <div style="
                      width:22px;height:22px;border-radius:999px;
                      background:#374151;border:1px solid rgba(255,255,255,.4);
                      display:flex;align-items:center;justify-content:center
                  ">{nr if nr is not None else ''}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# RIGHT COL
# ============================================================
with right_col:

    with st.spinner("Building R1 (away pass network)…"):
        fig, err = pass_network_same_logic_as_old(
            events, away_teamId, away_team, away_data,
            team_color=AWAY_COLOR,
            max_line_width=6, marker_size=1500, edgewidth=3,
            marker_edge_color="w",
            kit_no_size=25
        )
    if err:
        st.error(err)
    else:
        st.pyplot(fig, use_container_width=True)

    st.markdown(
        "<div class='card'><div class='muted'>R2</div><div class='big'>Placeholder (smalle visual)</div></div>",
        unsafe_allow_html=True
    )
