# ============================================================
# STREAMLIT PLAYER DASHBOARD (CLEANER + MORE VISIBLE)
# - TOP: Header (left) + Select Player + Compare Player (right)
# - UNDER: TM profile strip (1 row)
# - MAIN: LEFT radar (do not change chart logic) + stat groups multiselect
#         RIGHT 2 collapsible sections (Transfers + Injuries)
#           -> tables rendered with your original HTML method (stylable)
# ============================================================
import re
from datetime import datetime
import json
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MaxNLocator

import plotly.graph_objects as go


# -------------------------
# THEME (keep your colors)
# -------------------------
HOME_COLOR = "#7B68EE"   # paars
AWAY_COLOR = "#E32636"   # rood

THEME_BG = "#0B1220"
THEME_PANEL = "#0F172A"
THEME_TEXT = "rgba(255,255,255,0.92)"
THEME_MUTED = "rgba(255,255,255,0.72)"  # a bit more visible

PITCH_LINE_COLOR = "#2B3650"


# -------------------------
# CONFIG
# -------------------------
DATABASE_URL = st.secrets["DB_URL"]
engine = create_engine(DATABASE_URL)

PLAYER = "player_stats"                 # jouw view
TM_VIEW = "transfermarkt_players_clean" # jouw transfermarkt view

MIN_MINUTES = 450
PCTL_SUFFIX = "_pctl"  # of "_score"


# -------------------------
# PAGE + CSS (more visible)
# -------------------------
st.set_page_config(layout="wide")

st.markdown(
    f"""
    <style>

    /* ================= BASE APP ================= */
    .stApp {{
      background: {THEME_BG} !important;
      color: {THEME_TEXT} !important;
    }}
    [data-testid="stAppViewContainer"] {{
      background: {THEME_BG} !important;
    }}
    [data-testid="stHeader"] {{
      background: rgba(11,18,32,0.70) !important;
      border-bottom: 1px solid rgba(255,255,255,0.06) !important;
    }}

        /* Expander: header stays same color open/closed */
    div[data-testid="stExpander"] summary {{
      background: rgba(255,255,255,0.03) !important;
      border-bottom: 1px solid rgba(255,255,255,0.10) !important;
    }}

    /* Sometimes Streamlit adds background to the clickable header wrapper */
    div[data-testid="stExpander"] div[role="button"] {{
      background: rgba(255,255,255,0.03) !important;
    }}

    /* Expander body background */
    div[data-testid="stExpander"] > div {{
      background: rgba(255,255,255,0.03) !important;
    }}
    /* ================= TYPO ================= */
    h1, h2, h3 {{
      color: white !important;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      font-weight: 850;
      margin-bottom: 10px;
    }}

    /* ================= HERO ================= */
    .hero {{
      padding: 18px 22px;
      border-radius: 18px;
      background: linear-gradient(90deg, {THEME_BG} 0%, #121B2F 55%, {THEME_BG} 100%);
      border: 1px solid rgba(255,255,255,0.10);
      box-shadow: 0 10px 30px rgba(0,0,0,0.35);
      margin-bottom: 14px;
    }}
    .hero h1 {{
      margin: 0;
      font-size: 28px;
    }}
    .hero p {{
      color: rgba(255,255,255,0.75);
      margin: 6px 0 0 0;
      font-weight: 700;
    }}

    /* ================= CARDS ================= */
    .card {{
      padding: 16px;
      border-radius: 16px;
      background: {THEME_PANEL};
      border: 1px solid rgba(255,255,255,0.10);
      color: white;
      box-shadow: 0 10px 28px rgba(0,0,0,0.35);
    }}

    .section-title {{
      color: {THEME_MUTED};
      font-size: 12px;
      font-weight: 900;
      margin-bottom: 10px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}

    .muted {{
      color: {THEME_MUTED};
      font-size: 12px;
      font-weight: 750;
    }}

    /* ================= STRIP CARDS ================= */
    .strip-card {{
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255,255,255,0.04); /* slightly more visible */
      border: 1px solid rgba(255,255,255,0.12);
      box-shadow: inset 0 0 0 1px rgba(0,0,0,0.18);
    }}
    .strip-card .label {{
      color: rgba(255,255,255,0.70);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .strip-card .value {{
      color: rgba(255,255,255,0.96);
      font-size: 14px;
      font-weight: 950;
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    /* ==============================
    MULTISELECT – ULTRA DARK
    ================================ */
    
    /* Label */
    label[data-testid="stWidgetLabel"] > div {{
    color: rgba(255,255,255,0.75) !important;
    font-weight: 900;
    }}
    label[data-testid="stWidgetLabel"] > div {{
  color: #FFFFFF !important;
  font-weight: 900;
  letter-spacing: 0.04em;
}}


    /* Outer container */
    div[data-testid="stMultiSelect"] {{
    background: transparent !important;
    }}

    /* Actual input bar */
    div[data-testid="stMultiSelect"] div[role="combobox"] {{
    background: #0B1220 !important;               /* THEME_BG */
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 14px !important;
    min-height: 46px;
    padding: 6px 10px;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,0.40);
    }}

    /* Prevent Streamlit inner white layer */
    div[data-testid="stMultiSelect"] div[role="combobox"] > div {{
    background: transparent !important;
    }}

    /* Selected chips */
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background: #0F172A !important;                /* THEME_PANEL */
    color: rgba(255,255,255,0.92) !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 900;
    padding: 4px 9px;
    }}

    /* Chip remove (x) */
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg {{
    color: rgba(255,255,255,0.55) !important;
    }}

    /* Dropdown menu */
    div[data-baseweb="menu"] {{
    background: #0F172A !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 12px;
    }}

    /* Dropdown option */
    div[data-baseweb="option"] {{
    background: #0F172A !important;
    color: rgba(255,255,255,0.88) !important;
    font-weight: 800;
    }}

    /* Hover option */
    div[data-baseweb="option"]:hover {{
    background: rgba(255,255,255,0.08) !important;
    }}



    /* ================= SELECTBOX (player/compare) ================= */
    div[data-testid="stSelectbox"] div[role="combobox"] {{
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02)) !important;
      border: 1px solid rgba(255,255,255,0.14) !important;
      color: rgba(255,255,255,0.92) !important;
      border-radius: 14px !important;
      min-height: 44px;
    }}

    /* ================= EXPANDERS (dark) ================= */
    div[data-testid="stExpander"] {{
      border: 1px solid rgba(255,255,255,0.12) !important;
      border-radius: 16px !important;
      background: rgba(255,255,255,0.03) !important;
      box-shadow: 0 10px 26px rgba(0,0,0,0.30);
      overflow: hidden;
    }}
    div[data-testid="stExpander"] summary {{
      color: rgba(255,255,255,0.92) !important;
      font-weight: 950 !important;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# LOADERS
# -------------------------
@st.cache_data(show_spinner=False)
def load_players_view() -> pd.DataFrame:
    q = text(f'SELECT * FROM "{PLAYER}"')
    return pd.read_sql(q, engine)

@st.cache_data(show_spinner=False)
def load_tm_view() -> pd.DataFrame:
    q = text(f'SELECT * FROM "{TM_VIEW}"')
    return pd.read_sql(q, engine)

players = load_players_view()
tm = load_tm_view()


# -------------------------
# SETTINGS / COLUMN NAMES
# -------------------------
name_col = "playername"


# -------------------------
# HELPERS
# -------------------------
def _norm_name(x: str) -> str:
    s = str(x) if x is not None else ""
    return "".join(ch.lower() for ch in s.strip() if ch.isalnum())

def _safe_json(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (dict, list)):
        return val
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    if '""' in s:
        s = s.replace('""', '"')
    try:
        return json.loads(s)
    except Exception:
        return None

def _eur_short(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    try:
        x = float(v)
        if x >= 1_000_000:
            return f"€{x/1_000_000:.2f}m".replace(".00m", "m").replace(".0m", "m")
        if x >= 1_000:
            return f"€{x/1_000:.0f}k"
        return f"€{x:.0f}"
    except Exception:
        return str(v)

def _fmt_date_any(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    s = str(x).strip()
    if s in ("", "None", "nan", "-"):
        return "-"
    for dayfirst in (True, False):
        try:
            dt = pd.to_datetime(s, dayfirst=dayfirst, errors="raise")
            return dt.strftime("%d-%m-%Y")
        except Exception:
            pass
    return s

def _days_to_int(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    if s in ("-", "", "None", "nan"):
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits) if digits else None

def strip_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="strip-card">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_html_table_card(df: pd.DataFrame, title: str, height: int = 240):
    html = df.to_html(index=False, escape=False)

    components.html(
        f"""
        <style>
        body {{
            margin: 0;
            background: transparent;
            font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
            color: white;
        }}
        .title {{
            font-size: 12px;
            font-weight: 950;
            color: rgba(255,255,255,0.78);
            margin: 0 0 10px 0;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .table-wrap {{
            height: {height}px;
            overflow: auto;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.04);
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.18);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
        }}
        thead th {{
            position: sticky;
            top: 0;
            z-index: 5;
            background: rgba(255,255,255,0.06);
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.16);
            text-align: left;
            white-space: nowrap;
        }}
        tbody td {{
            padding: 9px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            white-space: nowrap;
        }}
        tbody tr:hover td {{
            background: rgba(123,104,238,0.14);
        }}
        .table-wrap::-webkit-scrollbar {{ height: 10px; width: 10px; }}
        .table-wrap::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.20); border-radius: 999px; }}
        .table-wrap::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.06); }}
        </style>

        <div class="title">{title}</div>
        <div class="table-wrap">{html}</div>
        """,
        height=height + 60,
        scrolling=False,
    )


# -------------------------
# FILTER MINUTES
# -------------------------
players_f = players.copy()
players_f["minutes_played_90"] = pd.to_numeric(players_f["minutes_played_90"], errors="coerce")
players_f = players_f[players_f["minutes_played_90"] > MIN_MINUTES].copy()

if players_f.empty:
    st.warning(f"Geen spelers met > {MIN_MINUTES} minuten gevonden.")
    st.stop()

playernames = players_f[name_col].astype(str).sort_values().unique().tolist()


# -------------------------
# HEADER + TOP RIGHT SELECTS
# -------------------------
with st.container():
    hc1, hc2 = st.columns([3, 1], gap="small")

    with hc1:
        st.markdown(
            f"""
            <div class="hero">
              <h1>Player Dashboard</h1>
              <p>Selecteer een speler (min. {MIN_MINUTES} minuten).</p>
              <p style="margin-bottom: 28px;"></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with hc2:
        st.markdown(
            """
              <div style="color: rgba(255,255,255,0.85); font-weight: 900; margin: 0px 0 8px 0;">
                Select player
              </div>
            """,
            unsafe_allow_html=True,
        )
        selected_name = st.selectbox(
            label="",
            options=playernames,
            key="player_select_header",
            label_visibility="collapsed"
        )

        st.markdown(
            """
              <div style="color: rgba(255,255,255,0.85); font-weight: 900; margin: 0px 0 8px 0;">
                Compare Player
              </div>
            """,
            unsafe_allow_html=True,
        )

        compare_options = ["None"] + [n for n in playernames if n != selected_name]

        compare_name = st.selectbox(
            label="",
            options=compare_options,
            index=0,  # standaard None
            key="compare_player_select_header",
            label_visibility="collapsed"
        )


        st.markdown("</div>", unsafe_allow_html=True)

sel_row = players_f.loc[players_f[name_col].astype(str) == str(selected_name)].iloc[0]
if compare_name == "None":
    compare_row = None
else:
    compare_row = players_f.loc[
        players_f[name_col].astype(str) == str(compare_name)
    ].iloc[0]



# ============================================================
# TRANSFERMARKT LOOKUP
# ============================================================
tm_row = None
if tm is not None and not tm.empty and "player_name_raw" in tm.columns:
    tm_tmp = tm.copy()
    tm_tmp["__k__"] = tm_tmp["player_name_raw"].astype(str).apply(_norm_name)
    key = _norm_name(selected_name)

    if "scrape_date" in tm_tmp.columns:
        tm_hit = tm_tmp[tm_tmp["__k__"] == key].sort_values("scrape_date")
        tm_row = tm_hit.iloc[-1] if len(tm_hit) else None
    else:
        tm_hit = tm_tmp[tm_tmp["__k__"] == key]
        tm_row = tm_hit.iloc[0] if len(tm_hit) else None

_NL_MONTHS = {
    "jan": 1, "feb": 2, "mrt": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12
}

def _parse_injury_date_nl(s):
    """Parses strings like '6 mrt. 2025' / '15 aug. 2025' to datetime, else NaT."""
    if s is None:
        return pd.NaT
    txt = str(s).strip().lower()
    if txt in ("-", "", "none", "nan"):
        return pd.NaT

    # remove dots and extra commas
    txt = txt.replace(".", "").replace(",", " ").strip()

    # match: day month year  (e.g., 6 mrt 2025)
    m = re.match(r"^(\d{1,2})\s+([a-z]{3})\s+(\d{4})$", txt)
    if not m:
        # fallback: try pandas for already-ISO-like strings
        return pd.to_datetime(s, dayfirst=True, errors="coerce")

    day = int(m.group(1))
    mon_txt = m.group(2)
    year = int(m.group(3))
    mon = _NL_MONTHS.get(mon_txt)

    if mon is None:
        return pd.NaT

    try:
        return pd.Timestamp(datetime(year, mon, day))
    except Exception:
        return pd.NaT
# ============================================================
# STAT GROUPS
# ============================================================
STAT_GROUPS = {
    "SHOOTING": [
        ("Shots", "shots_per90", f"shots_per90{PCTL_SUFFIX}"),
        ("Goals", "goals_per90", f"goals_per90{PCTL_SUFFIX}"),
        ("xG", "xg_per90", f"xg_per90{PCTL_SUFFIX}"),
        ("Shot accuracy", "shot_accuracy_pct", f"shot_accuracy_pct{PCTL_SUFFIX}"),
        ("xG/shot", "xg_per_shot", f"xg_per_shot{PCTL_SUFFIX}"),
    ],
    "PASSING": [
        ("Passes", "passes_per90", f"passes_per90{PCTL_SUFFIX}"),
        ("Pass accuracy", "pass_accuracy_pct", f"pass_accuracy_pct{PCTL_SUFFIX}"),
        ("Key passes", "key_passes_per90", f"key_passes_per90{PCTL_SUFFIX}"),
        ("Crosses", "crosses_per90", f"crosses_per90{PCTL_SUFFIX}"),
        ("Prog passes", "progressive_passes_per90", f"progressive_passes_per90{PCTL_SUFFIX}"),
        ("Into box", "passes_into_box_per90", f"passes_into_box_per90{PCTL_SUFFIX}"),
    ],
    "DRIBBLING": [
        ("Take-ons", "dribbles_attempted_per90", f"dribbles_attempted_per90{PCTL_SUFFIX}"),
        ("Completed", "dribbles_completed_per90", f"dribbles_completed_per90{PCTL_SUFFIX}"),
        ("Success %", "dribble_success_pct", f"dribble_success_pct{PCTL_SUFFIX}"),
        ("Dispossessed", "dispossessions_per90", f"dispossessions_per90{PCTL_SUFFIX}"),
    ],
    "DEFENDING": [
        ("Tackles", "tackles_per90", f"tackles_per90{PCTL_SUFFIX}"),
        ("Tackles won", "tackles_won_per90", f"tackles_won_per90{PCTL_SUFFIX}"),
        ("Interceptions", "interceptions_per90", f"interceptions_per90{PCTL_SUFFIX}"),
        ("Recoveries", "recoveries_per90", f"recoveries_per90{PCTL_SUFFIX}"),
        ("Aerials won", "aerials_won_per90", f"aerials_won_per90{PCTL_SUFFIX}"),
    ],
    "PHYSICALITY": [
        ("Fouls", "fouls_committed_per90", f"fouls_committed_per90{PCTL_SUFFIX}"),
        ("Cards", "cards_per90", f"cards_per90{PCTL_SUFFIX}"),
        ("Events/90", "total_events_per90", f"total_events_per90{PCTL_SUFFIX}"),
    ],
}


# ============================================================
# TM DATA PREP (strip)
# ============================================================
profile = {}
injuries = None
transfers = None
mv_dev = None

if tm_row is not None:
    profile = {
        "name": tm_row.get("player_name_raw", selected_name),
        "birth_date": tm_row.get("birth_date", None),
        "age_years": tm_row.get("age_years", None),
        "nationality": tm_row.get("nationality", None),
        "position_tm": tm_row.get("position_tm", None),
        "height_m": tm_row.get("height_m", None),
        "contract_signed_date": tm_row.get("contract_signed_date", None),
        "market_value_eur": tm_row.get("market_value_eur", None),
        "market_value_last_update": tm_row.get("market_value_last_update", None),
    }
    injuries = _safe_json(tm_row.get("injury_history_json", None))
    transfers = _safe_json(tm_row.get("transfer_history_json", None))
    mv_dev = _safe_json(tm_row.get("market_value_development_json", None))

mv_current = None
mv_highest = None
mv_last_change = None
if isinstance(mv_dev, dict):
    mv_current = mv_dev.get("current", None)
    mv_highest = mv_dev.get("highest", None)
    mv_last_change = mv_dev.get("last_change", None)


# ============================================================
# PROFILE STRIP (1 row)
# ============================================================
if tm_row is None:
    st.markdown("<div class='muted'>Geen Transfermarkt match gevonden voor deze speler.</div>", unsafe_allow_html=True)
else:
    nm = str(profile.get("name", selected_name))
    pos = str(profile.get("position_tm", "-"))
    nat = str(profile.get("nationality", "-"))

    height_m = profile.get("height_m", None)
    height_txt = f"{float(height_m):.2f}m" if height_m not in (None, "-", "") and not (isinstance(height_m, float) and np.isnan(height_m)) else "-"

    bday = _fmt_date_any(profile.get("birth_date"))
    contract = _fmt_date_any(profile.get("contract_signed_date"))
    mv_txt = _eur_short(profile.get("market_value_eur"))
    mv_upd = _fmt_date_any(profile.get("market_value_last_update"))

    inj_cnt = str(len(injuries)) if isinstance(injuries, list) else "0"
    tr_cnt = str(len(transfers.get("transfers", []))) if isinstance(transfers, dict) else "0"

    cols = st.columns([1.4,1.2,1.0,0.8,1.0,1.2,0.9,0.9,0.7,0.7], gap="small")
    with cols[0]: strip_card("Name", nm)
    with cols[1]: strip_card("Position", pos)
    with cols[2]: strip_card("Nationality", nat)
    with cols[3]: strip_card("Height", height_txt)
    with cols[4]: strip_card("Birth date", bday)
    with cols[5]: strip_card("Contract (signed)", contract)
    with cols[6]: strip_card("Current MV", mv_current or mv_txt)
    with cols[7]: strip_card("Highest MV", mv_highest or "-")
    with cols[8]: strip_card("Injuries", inj_cnt)
    with cols[9]: strip_card("Transfers", tr_cnt)

    st.markdown(
        f"<div class='muted' style='margin-top:8px;'>Market value last update: <b style='color:white'>{mv_upd}</b> · MV last change: <b style='color:white'>{mv_last_change or '-'}</b></div>",
        unsafe_allow_html=True
    )

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


# ============================================================
# PIZZA RADAR FUNCTION (your logic kept)
# ============================================================
def build_pizza_percentile_chart(
    sel_row: pd.Series,
    compare_row: pd.Series | None,
    players_df: pd.DataFrame,
    stat_groups: dict,
    selected_groups: list,
    pctl_suffix: str = "_pctl",
    title: str = None,
    subtitle: str = None,
    theme_bg: str = "#0B1220",
    theme_panel: str = "#0F172A",
    home_color: str = "#7B68EE",
    pitch_line_color: str = "rgba(255,255,255,0.14)",
    theme_muted: str = "rgba(255,255,255,0.70)",
    theme_bg_text: str = "#0B1220",
    ring_fill: str = "rgba(123,104,238,0.18)",
    you_fill: str = "rgba(227,38,54,0.62)",
):
    def wrap_label(s: str, max_len: int = 12) -> str:
        parts = str(s).split(" ")
        out, line = [], ""
        for w in parts:
            trial = (line + " " + w).strip()
            if len(trial) <= max_len:
                line = trial
            else:
                if line:
                    out.append(line)
                line = w
        if line:
            out.append(line)
        return "<br>".join(out)

    items = []
    for g in selected_groups:
        for label, val_col, pctl_col in stat_groups.get(g, []):
            if pctl_col in players_df.columns:
                items.append((label, pctl_col))

    if not items:
        return None

    labels, pctls, pctls_cmp = [], [], []
    for label, pctl_col in items:
        v1 = sel_row.get(pctl_col, None)
        if v1 is None or (isinstance(v1, float) and np.isnan(v1)):
            continue
        try:
            pv1 = float(v1)
        except Exception:
            continue
        pv1 = max(0.0, min(99.0, pv1))

        labels.append(label)
        pctls.append(pv1)

        if compare_row is not None:
            v2 = compare_row.get(pctl_col, None)
            try:
                pv2 = float(v2) if v2 is not None and not (isinstance(v2, float) and np.isnan(v2)) else np.nan
            except Exception:
                pv2 = np.nan
            if np.isnan(pv2):
                pv2 = 0.0
            pv2 = max(0.0, min(99.0, pv2))
            pctls_cmp.append(pv2)

    if not pctls:
        return None

    n = len(pctls)
    theta = np.linspace(0, 360, n, endpoint=False)
    labels_wrapped = [wrap_label(l, max_len=12) for l in labels]

    player_1_name = str(sel_row.get("player", sel_row.get("name", "Player 1")))
    player_2_name = str(compare_row.get("player", compare_row.get("name", "Player 2"))) if compare_row is not None else None

    fig = go.Figure()

    if compare_row is not None and pctls_cmp:
        cd_you = [[lab, p2] for lab, p2 in zip(labels, pctls_cmp)]
        hover_you = (
            "<b>%{customdata[0]}</b><br>"
            + player_1_name + ": %{r:.0f}/99<br>"
            + player_2_name + ": %{customdata[1]:.0f}/99"
            + "<extra></extra>"
        )
    else:
        cd_you = [[lab] for lab in labels]
        hover_you = (
            "<b>%{customdata[0]}</b><br>"
            + player_1_name + ": %{r:.0f}/99<br>"
            + "<extra></extra>"
        )

    fig.add_trace(
        go.Barpolar(
            r=pctls,
            theta=theta,
            width=[360 / n] * n,
            marker=dict(
                color=you_fill,
                line=dict(color="rgba(255,255,255,0.40)", width=1),
            ),
            customdata=cd_you,
            hovertemplate=hover_you,
            name="Player 1",
        )
    )

    if compare_row is not None and pctls_cmp:
        step = 360 / n
        half = step / 2

        theta_wide, r_wide, cd_wide = [], [], []
        for lab, ang, r2, r1 in zip(labels, theta, pctls_cmp, pctls):
            left = (ang - half) % 360
            right = (ang + half) % 360
            theta_wide += [left, right]
            r_wide += [r2, r2]
            cd_wide += [[lab, r1, r2], [lab, r1, r2]]

        theta_wide.append(theta_wide[0])
        r_wide.append(r_wide[0])
        cd_wide.append(cd_wide[0])

        fig.add_trace(
            go.Scatterpolar(
                r=r_wide,
                theta=theta_wide,
                mode="lines",
                line=dict(color=home_color, width=2),
                fill="toself",
                fillcolor=ring_fill,
                customdata=cd_wide,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    + player_1_name + ": %{customdata[1]:.0f}/99<br>"
                    + player_2_name + ": %{customdata[2]:.0f}/99"
                    + "<extra></extra>"
                ),
                name="Player 2",
            )
        )

    fig.update_layout(
        barmode="overlay",
        paper_bgcolor=theme_bg,
        plot_bgcolor=theme_bg,
        margin=dict(l=40, r=40, t=60, b=30),
        height=520,
        showlegend=False,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, 99],
                showticklabels=False,
                ticks="",
                gridcolor="rgba(255,255,255,0.16)",  # slightly more visible grid
                gridwidth=1,
            ),
            angularaxis=dict(
                showticklabels=True,
                tickmode="array",
                tickvals=list(theta),
                ticktext=labels_wrapped,
                tickfont=dict(size=11, color="rgba(255,255,255,0.85)"),  # more visible
                rotation=90,
                direction="clockwise",
                gridcolor="rgba(255,255,255,0.14)",
                gridwidth=1,
            ),
        ),
        font=dict(color="white"),
    )

    if title:
        fig.add_annotation(
            x=0.01, y=1.12, xref="paper", yref="paper",
            text=f"<b>{title}</b>",
            showarrow=False,
            align="left",
            font=dict(size=24, color="white"),
        )
    if subtitle:
        fig.add_annotation(
            x=0.01, y=1.06, xref="paper", yref="paper",
            text=subtitle,
            showarrow=False,
            align="left",
            font=dict(size=12, color=theme_muted),
        )

    return fig


# ============================================================
# MAIN LAYOUT
# ============================================================
left_wide, right_small = st.columns([1.15, 1], gap="small")

with left_wide:

    # keep groups in session_state so radar always has a value
    all_groups = list(STAT_GROUPS.keys())
    if "radar_groups" not in st.session_state:
        st.session_state["radar_groups"] = all_groups
    selected_groups = st.session_state["radar_groups"]

    player_display = str(sel_row.get(name_col, "Player"))
    fig = build_pizza_percentile_chart(
        sel_row=sel_row,
        compare_row=compare_row,
        players_df=players_f,
        stat_groups=STAT_GROUPS,
        selected_groups=selected_groups,
        pctl_suffix=PCTL_SUFFIX,
        title=player_display,
        subtitle=f"Percentile Rank vs. League Players — compared to {compare_name}",
        theme_bg=THEME_BG,
        theme_panel=THEME_PANEL,
        home_color=HOME_COLOR,
        pitch_line_color="rgba(255,255,255,0.14)",
        theme_muted=THEME_MUTED,
        theme_bg_text=THEME_BG,
    )

    if fig is None:
        st.info("Geen percentile data gevonden voor deze selectie.")
    else:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # eigen titel (altijd zichtbaar)
    st.markdown(
        "<div style='color:#FFFFFF; font-weight:900; margin: 0 0 6px 0;'>Select stat groups</div>",
        unsafe_allow_html=True
    )

    # multiselect zonder Streamlit-label
    selected_groups = st.multiselect(
        "",
        options=all_groups,
        default=st.session_state.get("radar_groups", all_groups),
        key="radar_groups",
        label_visibility="collapsed",
    )

    st.markdown("</div>", unsafe_allow_html=True)


with right_small:

    # -------------------------
    # TRANSFERS (expander + your old HTML-table style)
    # -------------------------
    transfer_count = 0
    if isinstance(transfers, dict) and isinstance(transfers.get("transfers"), list):
        transfer_count = len(transfers["transfers"])

    with st.expander(f"Transfers ({transfer_count})", expanded=False):
        if tm_row is None or not isinstance(transfers, dict) or not isinstance(transfers.get("transfers"), list):
            st.markdown("<div class='muted'>Geen transfer data gevonden.</div>", unsafe_allow_html=True)
        else:
            tlist = [t for t in transfers.get("transfers", []) if isinstance(t, dict)]

            # sort newest first if possible
            def _dt(x):
                return pd.to_datetime(x.get("dateUnformatted") or x.get("date"), errors="coerce")

            try:
                tlist = sorted(tlist, key=_dt, reverse=True)
            except Exception:
                pass

            rows = []
            for t in tlist:
                frm = (t.get("from", {}) or {}).get("clubName", "-") if isinstance(t.get("from"), dict) else "-"
                to = (t.get("to", {}) or {}).get("clubName", "-") if isinstance(t.get("to"), dict) else "-"
                rows.append({
                    "Datum": str(t.get("date") or "-"),
                    "Seizoen": str(t.get("season") or "-"),
                    "Van": frm,
                    "Naar": to,
                    "Fee": str(t.get("fee") or "-"),
                    "MV": str(t.get("marketValue") or "-"),
                })

            df_tr = pd.DataFrame(rows)
            render_html_table_card(df_tr, title="Transfer history", height=240)

            fee_sum = transfers.get("feeSum", None)
            st.markdown(
                f"<div class='muted' style='margin-top:8px;'>Total fees (sum): <b style='color:white'>{_eur_short(fee_sum) if fee_sum is not None else '-'}</b></div>",
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # -------------------------
    # INJURIES (expander + your old HTML-table style)
    # -------------------------
    injury_count = len(injuries) if isinstance(injuries, list) else 0

    with st.expander(f"Blessures ({injury_count})", expanded=False):
        if tm_row is None or not isinstance(injuries, list) or len(injuries) == 0:
            st.markdown("<div class='muted'>Geen blessure data gevonden.</div>", unsafe_allow_html=True)
        else:
            rows = []
            for it in injuries:
                if not isinstance(it, dict):
                    continue
                days_raw = it.get("Days") or it.get("days")
                rows.append({
                    "Blessure": str(it.get("Injury") or it.get("injury") or it.get("type") or "-"),
                    "Van": str(it.get("From") or it.get("from") or it.get("start") or "-"),
                    "Tot": str(it.get("Until") or it.get("until") or it.get("end") or "-"),
                    "Dagen": str(days_raw or "-"),
                    "Games missed": str(it.get("GamesMissed") or it.get("gamesMissed") or it.get("Games") or "-"),
                    "Seizoen": str(it.get("Season") or it.get("season") or "-"),
                    "__days_num": _days_to_int(days_raw),
                })

            df_inj = pd.DataFrame(rows)
            # sorteer op meest recente blessure (Van-datum)
            df_inj["__from_date"] = df_inj["Van"].apply(_parse_injury_date_nl)
            df_inj = ( df_inj.sort_values(by="__from_date", ascending=False) .drop(columns=["__days_num", "__from_date"], errors="ignore") )

            render_html_table_card(df_inj, title="Injury history", height=240)

            st.markdown(
                f"<div class='muted' style='margin-top:8px;'>Cases: <b style='color:white'>{len(df_inj)}</b></div>",
                unsafe_allow_html=True
            )
