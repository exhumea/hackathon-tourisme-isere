"""Démo live — écran projeté : colonne « Backend » (STT + BDD) | colonne « Frontend » (mockup téléphone).

Lancement : `uv run streamlit run app.py` (le worker doit tourner : `uv run python worker.py`).
"""

from __future__ import annotations

import html
import json
import time
from datetime import datetime, time as dtime, timedelta

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

import bornes
import db
import stats
from periods import TZ, HalfDay, current_half_day, local_from_naive, now_utc, parse_ts

st.set_page_config(page_title="Avis rando · démo live", page_icon="🏔️", layout="wide")

# Palette (skill dataviz, palette de référence, mode clair)
BLUE, ORANGE, MUTED = "#2a78d6", "#eb6834", "#a3a29c"
INK, INK2 = "#0b0b0b", "#52514e"
WORKER_TIMEOUT_S = 15

st.markdown(
    """
<style>
.block-container { padding-top: 2.2rem; max-width: 100%; }
.st-key-phone {
  max-width: 410px; margin: 0 auto; padding: 22px 16px 26px 16px;
  border: 11px solid #1b1b1d; border-radius: 44px; background: #fcfcfb;
  box-shadow: 0 18px 40px rgba(0,0,0,.25); min-height: 780px; position: relative;
}
.st-key-phone::before {  /* encoche */
  content: ""; position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
  width: 110px; height: 22px; background: #1b1b1d; border-radius: 12px;
}
.phone-head { display:flex; justify-content:space-between; align-items:center; margin-top: 14px;
  font-weight: 700; font-size: 1.05rem; color: #0b0b0b; }
.phone-sub { color: #52514e; font-size: .8rem; }
.badge { display:inline-block; padding: 1px 8px; border-radius: 999px; font-size: .75rem; font-weight: 600; }
.badge-live { background:#e34948; color:#fff; }
.badge-hist { background:#e8e7e3; color:#52514e; }
.badge-all { background:#cde2fb; color:#184f95; }
.live-box { border: 1px solid #e3e2de; border-radius: 10px; padding: 12px 14px; min-height: 96px;
  background: #fff; font-size: 1.05rem; line-height: 1.5; }
.live-box .partial { color: #8a8984; font-style: italic; }
.status { font-size: .85rem; color: #52514e; margin-bottom: 6px; }
.dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align: middle; }
.kpi { font-size: 2.2rem; font-weight: 700; color:#0b0b0b; line-height: 1; }
.kpi-sub { color:#52514e; font-size: .8rem; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def conn():
    return db.connect(db.DEFAULT_PATH)


C = conn()
ss = st.session_state
ss.setdefault("win", None)        # None = demi-journée en cours (live) ; sinon clé de demi-journée
ss.setdefault("all_past", False)
ss.setdefault("expect", None)     # (statut attendu, instant) juste après un clic, le temps que le worker réagisse


def fmt_local(iso: str, with_date: bool = False) -> str:
    t = parse_ts(iso).astimezone(TZ)
    return t.strftime("%d/%m %H:%M" if with_date else "%H:%M:%S")


def worker_state() -> tuple[str, str]:
    live = db.get_live(C)
    status = live["status"]
    hb = live["heartbeat_at"]
    if status == "loading":
        return "loading", live["message"] or "chargement…"
    if status == "offline" or hb is None or (now_utc() - parse_ts(hb)).total_seconds() > WORKER_TIMEOUT_S:
        return "offline", "worker arrêté ou ne répond pas — lancer `uv run python worker.py`"
    return status, live["message"] or ""


# --- sidebar : mode préparation -------------------------------------------------

with st.sidebar:
    st.subheader("Réglages")
    prep = st.toggle("Mode préparation", key="prep", help="Masquer pendant le show.")
    if prep:
        st.caption("Les avis enregistrés ici sont marqués « initialisation ».")
        st.caption(f"Base : `{db.DEFAULT_PATH}`")
        sim = st.toggle("Date simulée", key="sim")
        if sim:
            ss.setdefault("sim_date", datetime.now(TZ).date() - timedelta(days=1))
            st.date_input("Jour", key="sim_date")
            st.time_input("Heure", key="sim_time", value=dtime(10, 0), step=timedelta(minutes=15))
            hd = HalfDay(ss.sim_date, "matin" if ss.sim_time.hour < 13 else "apres_midi")
            st.caption(f"→ {hd.label}")


def start_kwargs() -> dict:
    kw = {"borne_id": ss.borne, "source": ss.source, "is_init": int(bool(ss.get("prep")))}
    if ss.get("prep") and ss.get("sim"):
        kw["event_ts_override"] = local_from_naive(ss.sim_date, ss.sim_time.hour, ss.sim_time.minute).isoformat()
    return kw


# --- colonne Backend ------------------------------------------------------------

STATUS_UI = {
    "idle": ("#1baf7a", "Prêt"),
    "recording": ("#e34948", "Enregistrement"),
    "transcribing": ("#eda100", "Transcription finale"),
    "classifying": ("#2a78d6", "Classification Jev"),
    "loading": ("#eda100", "Chargement du modèle"),
    "offline": ("#a3a29c", "Worker hors ligne"),
}


def _send(cmd: str) -> None:
    """Callback des boutons (exécuté avant le rerun : l'affichage qui suit est déjà cohérent)."""
    if cmd == "start":
        db.push_command(C, "start", **start_kwargs())
        ss.expect = ("recording", time.monotonic())
    else:
        db.push_command(C, "stop")
        ss.expect = ("transcribing", time.monotonic())


@st.fragment(run_every=0.7)
def live_panel() -> None:
    status, message = worker_state()
    exp = ss.expect
    if exp and time.monotonic() - exp[1] < 3 and status not in (exp[0], "offline"):
        status = exp[0]  # le worker n'a pas encore pris la commande en compte
    elif exp:
        ss.expect = None
    live = db.get_live(C)

    recording = status == "recording"
    can_start = status in ("idle", "classifying")
    if recording:
        st.button("■  Stop", type="primary", width="stretch", key="btn_stop", on_click=_send, args=("stop",))
    else:
        st.button("●  Enregistrer", type="primary", width="stretch", disabled=not can_start, key="btn_start",
                  on_click=_send, args=("start",))

    color, label = STATUS_UI.get(status, ("#a3a29c", status))
    where = ""
    if recording and live["borne_id"] in bornes.BORNES:
        where = f" · {bornes.BORNES[live['borne_id']].court} ({live['source']})"
    lang = f" · langue : <b>{html.escape(live['langue'])}</b>" if live["langue"] else ""
    st.markdown(
        f'<div class="status"><span class="dot" style="background:{color}"></span><b>{label}</b>{where}{lang}'
        f' — {html.escape(message)}</div>',
        unsafe_allow_html=True,
    )
    committed = html.escape(live["committed_text"] or "")
    partial = html.escape(live["partial_text"] or "")
    body = committed + (f' <span class="partial">{partial}</span>' if partial else "")
    if not body:
        body = '<span class="partial">La transcription apparaît ici pendant l\'enregistrement…</span>'
    st.markdown(f'<div class="live-box">{body}</div>', unsafe_allow_html=True)


NULL = "—"


@st.fragment(run_every=1.0)
def latest_panel() -> None:
    rows = db.latest_avis(C, 10)
    if not rows:
        st.info("Aucun avis en base pour l'instant.")
        return
    data = []
    for r in rows:
        b = bornes.BORNES.get(r["borne_id"])
        data.append({
            "#": r["id"],
            "quand": fmt_local(r["event_ts"], with_date=True),
            "borne": b.court if b else r["borne_id"],
            "source": r["source"],
            "statut": {"ok": "✅ ok", "pending": "⏳ Jev…", "error": "⚠️ erreur"}[r["classif_status"]],
            "note": f"{r['note']:.1f}" if r["note"] is not None else NULL,
            "profil": r["profil"] or NULL,
            "origine": r["origine"] or NULL,
            "groupe": r["groupe"] or NULL,
            "venue": r["mode_venue"] or NULL,
            "affluence": r["affluence"] or NULL,
            "revenir": r["revenir"] or NULL,
            "lat, lon": f"{r['lat']:.4f}, {r['lon']:.4f}",
            "transcription": r["transcript"],
        })
    st.dataframe(
        pd.DataFrame(data), hide_index=True, width="stretch", height=388,
        column_config={"transcription": st.column_config.TextColumn(width="large")},
    )
    errors = [r for r in rows if r["classif_status"] == "error"]
    if errors:
        cols = st.columns(min(len(errors), 4) + 1)
        cols[0].caption(f"⚠️ {html.escape((errors[0]['classif_error'] or '')[:120])}")
        for c, r in zip(cols[1:], errors[:4]):
            c.button(f"Re-classifier #{r['id']}", key=f"recl_{r['id']}",
                     on_click=db.push_command, args=(C, "reclassify"), kwargs={"avis_id": r["id"]})
    if st.toggle("Afficher la réponse brute Jev (dernier avis classifié)", key="show_raw"):
        r = next((r for r in rows if r["jev_raw"]), None)
        if r:
            st.caption(f"Avis #{r['id']} · {r['jev_model']}")
            st.json(json.loads(r["jev_raw"]), expanded=2)
        else:
            st.caption("Aucun avis classifié dans les 10 derniers.")


# --- colonne Frontend (mockup téléphone) -----------------------------------------

def _base_chart(df: pd.DataFrame) -> alt.Chart:
    return alt.Chart(df).properties(height=230)


def _bar_h(df, cat, val, color=BLUE, sort=None, fmt="d", title=None, tooltip_extra=()):
    tips = [alt.Tooltip(f"{cat}:N", title=title or cat), alt.Tooltip(f"{val}:Q", format=fmt, title="avis" if fmt == "d" else val)]
    tips += list(tooltip_extra)
    bars = _base_chart(df).mark_bar(cornerRadiusEnd=4, height=18, color=color).encode(
        y=alt.Y(f"{cat}:N", sort=sort, title=None, axis=alt.Axis(labelLimit=150, labelColor=INK2)),
        x=alt.X(f"{val}:Q", title=None, axis=alt.Axis(grid=True, gridColor="#ecebe7", labelColor=INK2, tickMinStep=1,
                                                       format=fmt)),
        tooltip=tips,
    )
    labels = bars.mark_text(align="left", dx=4, color=INK2, fontSize=11).encode(text=alt.Text(f"{val}:Q", format=fmt))
    return (bars + labels).configure_view(stroke=None)


def view_notes(df):
    hist, mean, n = stats.notes(df)
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="kpi">{mean:.1f}<span style="font-size:1rem;color:#52514e"> /5</span></div>'
                f'<div class="kpi-sub">note moyenne</div>' if mean is not None else
                '<div class="kpi">—</div><div class="kpi-sub">note moyenne</div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi">{n}</div><div class="kpi-sub">avis notés</div>', unsafe_allow_html=True)
    hist["étoiles"] = hist["note"].map(lambda k: "★" * k)
    chart = _base_chart(hist).mark_bar(cornerRadiusEnd=4, width=34, color=BLUE).encode(
        x=alt.X("étoiles:N", sort=[("★" * k) for k in range(1, 6)], title=None, axis=alt.Axis(labelAngle=0, labelColor=INK2)),
        y=alt.Y("avis:Q", title=None, axis=alt.Axis(tickMinStep=1, gridColor="#ecebe7", labelColor=INK2)),
        tooltip=[alt.Tooltip("note:O", title="note"), alt.Tooltip("avis:Q", title="avis")],
    ).configure_view(stroke=None)
    st.altair_chart(chart, width="stretch")
    st.caption("Note inférée par Jev (1-5), arrondie pour l'histogramme ; moyenne sur la valeur continue.")


def view_profil(df):
    out, nm = stats.categorical(df, "profil")
    out["%"] = out["part"] * 100
    st.altair_chart(_bar_h(out, "valeur", "%", fmt=".0f", title="profil", sort=None,
                           tooltip_extra=[alt.Tooltip("avis:Q", title="avis")]), width="stretch")
    st.caption(f"Part parmi les avis où le profil est mentionné ({int(out['avis'].sum())}) · non mentionné : {nm}")


def view_volume(df):
    vol = stats.volume(df)
    st.markdown(f'<div class="kpi">{len(df)}</div><div class="kpi-sub">avis dans la fenêtre</div>', unsafe_allow_html=True)
    vol["source"] = vol["source"].map({"borne": "Borne", "app": "App"})
    chart = _base_chart(vol).mark_bar(height=18, stroke="#fcfcfb", strokeWidth=2).encode(
        y=alt.Y("borne:N", title=None, sort=[b.court for b in bornes.BORNES.values()], axis=alt.Axis(labelColor=INK2)),
        x=alt.X("sum(avis):Q", title=None, axis=alt.Axis(tickMinStep=1, gridColor="#ecebe7", labelColor=INK2)),
        color=alt.Color("source:N", scale=alt.Scale(domain=["Borne", "App"], range=[BLUE, ORANGE]),
                        legend=alt.Legend(orient="top", title=None, labelColor=INK2)),
        order=alt.Order("source:N", sort="descending"),
        tooltip=[alt.Tooltip("borne:N"), alt.Tooltip("source:N"), alt.Tooltip("avis:Q", title="avis")],
    ).configure_view(stroke=None)
    st.altair_chart(chart, width="stretch")


def view_venue(df):
    out, nm = stats.categorical(df, "mode_venue")
    st.markdown("**Mode de venue**")
    st.altair_chart(_bar_h(out, "valeur", "avis", title="mode", sort="-x"), width="stretch")
    st.caption(f"Non mentionné : {nm}")
    aff = stats.affluence_par_borne(df)
    st.markdown("**Affluence ressentie par borne** (1 faible · 2 normale · 3 saturée)")
    chart = _base_chart(aff).mark_bar(cornerRadiusEnd=4, height=18, color=BLUE).encode(
        y=alt.Y("borne:N", title=None, sort=[b.court for b in bornes.BORNES.values()], axis=alt.Axis(labelColor=INK2)),
        x=alt.X("affluence:Q", title=None, scale=alt.Scale(domain=[0, 3]),
                axis=alt.Axis(values=[1, 2, 3], gridColor="#ecebe7", labelColor=INK2)),
        tooltip=[alt.Tooltip("borne:N"), alt.Tooltip("affluence:Q", format=".2f", title="moyenne"),
                 alt.Tooltip("avis:Q", title="avis")],
    ).configure_view(stroke=None)
    st.altair_chart(chart, width="stretch")


def view_saturation(df):
    sat = stats.saturation(df)
    total = int(sat["avis"].sum())
    k = int(sat.loc[sat["mention"] == "Saturée", "avis"].iloc[0])
    st.markdown(f'<div class="kpi">{(100 * k / total) if total else 0:.0f}%</div>'
                f'<div class="kpi-sub">des avis signalent une saturation ({k}/{total})</div>', unsafe_allow_html=True)
    sat["couleur"] = sat["mention"].map({"Saturée": BLUE, "Non saturée": BLUE, stats.NM_LABEL: MUTED})
    chart = _base_chart(sat).mark_bar(cornerRadiusEnd=4, height=18).encode(
        y=alt.Y("mention:N", title=None, sort=list(sat["mention"]), axis=alt.Axis(labelColor=INK2)),
        x=alt.X("avis:Q", title=None, axis=alt.Axis(tickMinStep=1, gridColor="#ecebe7", labelColor=INK2)),
        color=alt.Color("couleur:N", scale=None),
        tooltip=[alt.Tooltip("mention:N"), alt.Tooltip("avis:Q", title="avis")],
    ).configure_view(stroke=None)
    st.altair_chart(chart, width="stretch")


VIEWS = {"notes": view_notes, "profil": view_profil, "volume": view_volume, "venue": view_venue,
         "saturation": view_saturation}


def map_view(df: pd.DataFrame) -> None:
    pts = df[["lat", "lon", "source"]].copy()
    pts["color"] = pts["source"].map({"borne": [42, 120, 214, 200], "app": [235, 104, 52, 200]})
    bdf = pd.DataFrame([{"lat": b.lat, "lon": b.lon, "nom": b.court} for b in bornes.BORNES.values()])
    layers = [
        pdk.Layer("ScatterplotLayer", bdf, get_position="[lon, lat]", get_radius=900, get_fill_color=[11, 11, 11, 40],
                  get_line_color=[11, 11, 11, 200], stroked=True, line_width_min_pixels=2, radius_min_pixels=7,
                  pickable=True),
        pdk.Layer("ScatterplotLayer", pts, get_position="[lon, lat]", get_radius=350, get_fill_color="color",
                  get_line_color=[252, 252, 251], stroked=True, line_width_min_pixels=1, radius_min_pixels=5),
        pdk.Layer("TextLayer", bdf, get_position="[lon, lat]", get_text="nom", get_size=12, get_pixel_offset=[0, -16],
                  get_color=[11, 11, 11]),
    ]
    st.pydeck_chart(pdk.Deck(layers=layers, map_style="light",
                             initial_view_state=pdk.ViewState(latitude=45.15, longitude=5.86, zoom=8.1),
                             tooltip={"text": "{nom}"}), height=230, width="stretch")
    st.markdown(
        '<div class="phone-sub"><span style="color:#55554f">◉</span> borne · '
        f'<span style="color:{BLUE}">●</span> avis à la borne · '
        f'<span style="color:{ORANGE}">●</span> avis via l\'app (≤ 2 km)</div>',
        unsafe_allow_html=True,
    )


def _nav(action: str) -> None:
    cur = current_half_day()
    if action == "prev":
        ss.win = (HalfDay.from_key(ss.win) if ss.win else cur).shift(-1).key
    elif action == "next" and ss.win:
        nxt = HalfDay.from_key(ss.win).shift(1)
        ss.win = None if nxt >= cur else nxt.key
    elif action == "live":
        ss.win, ss.all_past = None, False


def window_controls() -> tuple[str | None, str]:
    """Retourne (clé de demi-journée ou None pour tout le passé, badge HTML)."""
    cur = current_half_day()
    if ss.win and HalfDay.from_key(ss.win) >= cur:  # la demi-journée « historique » est devenue la courante
        ss.win = None
    is_live = ss.win is None
    c1, c2, c3 = st.columns([1, 1, 1.4])
    c1.button("◀", key="prev", width="stretch", disabled=ss.all_past, on_click=_nav, args=("prev",))
    c2.button("▶", key="next", width="stretch", disabled=is_live or ss.all_past, on_click=_nav, args=("next",))
    c3.button("● Live", key="live", width="stretch", disabled=is_live and not ss.all_past, on_click=_nav, args=("live",))
    st.toggle("Tout le passé", key="all_past")
    if ss.all_past:
        return None, '<span class="badge badge-all">Tout le passé</span>'
    if is_live:
        return cur.key, f'<span class="badge badge-live">● LIVE</span> <span class="phone-sub">{cur.label}</span>'
    return ss.win, f'<span class="badge badge-hist">Historique</span> <span class="phone-sub">{HalfDay.from_key(ss.win).label}</span>'


def phone_body() -> None:
    st.markdown('<div class="phone-head"><span>🏔️ Isère Rando · Avis</span>'
                '<span class="phone-sub">' + datetime.now(TZ).strftime("%H:%M") + "</span></div>",
                unsafe_allow_html=True)
    crit = st.selectbox("Critère", list(stats.CRITERES), format_func=stats.CRITERES.get, key="crit",
                        label_visibility="collapsed")
    key, badge = window_controls()
    st.markdown(badge, unsafe_allow_html=True)
    df = stats.to_df(db.avis_in_window(C, key))
    pending = int((df["classif_status"] == "pending").sum())
    if pending:
        st.caption(f"⏳ {pending} avis en cours de classification")
    VIEWS[crit](df)
    map_view(df)


@st.fragment(run_every=2.0)
def phone() -> None:
    phone_body()


# --- mise en page ---------------------------------------------------------------

col_b, col_f = st.columns([1.45, 1], gap="large")
with col_b:
    st.markdown("### 🛠️ Backend")
    c1, c2 = st.columns([1.6, 1])
    c1.selectbox("Borne", list(bornes.BORNES), format_func=lambda k: f"{bornes.BORNES[k].nom} · {bornes.BORNES[k].massif}",
                 key="borne")
    c2.radio("Source", bornes.SOURCES, format_func={"borne": "Borne", "app": "App (≤ 2 km)"}.get, key="source",
             horizontal=True)
    if ss.get("prep"):
        st.caption("🧪 Mode préparation actif")
    live_panel()
    st.markdown("#### Dernières lignes de la base")
    latest_panel()

with col_f:
    st.markdown("### 📱 Frontend")
    with st.container(key="phone"):
        phone()
