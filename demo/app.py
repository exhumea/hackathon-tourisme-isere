"""Démo live, écran projeté : colonne « Backend » (STT + base) | colonne « Frontend » (mockup téléphone).

Lancement : `streamlit run demo/app.py` (le worker doit tourner : `python demo/worker.py`).
Préparation (date simulée, avis d'initialisation) : `DEMO_PREP=1 streamlit run demo/app.py`.
"""

from __future__ import annotations

import html
import json
import math
import os
import time
from datetime import datetime, timedelta
from typing import Any

import bornes
import db
import folium
import pandas as pd
import periods
import reference
import streamlit as st
import worker
from streamlit_folium import st_folium

st.set_page_config(page_title="Borne ressenti · démo live", page_icon="🌲", layout="wide")

PREP = os.environ.get("DEMO_PREP") == "1"
HEARTBEAT_LOST_S = 5  # invariant 6
NULL = "—"
N_LATEST = 10

# Palette (skill dataviz, palette de référence, mode clair)
BLUE, RED, NEUTRAL, MUTED = "#2a78d6", "#e34948", "#f0efec", "#a3a29c"
SEQ_LIGHT, SEQ_DARK = "#cde2fb", "#0d366b"
INK, INK2 = "#0b0b0b", "#52514e"

st.markdown(
    """
<style>
.block-container { padding-top: 2rem; max-width: 100%; }
.st-key-phone {
  max-width: 410px; margin: 0 auto; padding: 26px 14px 18px 14px;
  border: 11px solid #1b1b1d; border-radius: 44px; background: #fcfcfb;
  box-shadow: 0 18px 40px rgba(0,0,0,.25); position: relative; gap: .55rem;
}
.st-key-phone::before {
  content: ""; position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
  width: 110px; height: 22px; background: #1b1b1d; border-radius: 12px;
}
.phone-head { display:flex; justify-content:space-between; align-items:center; margin-top: 6px;
  font-weight: 700; font-size: 1.05rem; color: #0b0b0b; }
.phone-sub { color: #52514e; font-size: .8rem; }
.phone-foot { color: #52514e; font-size: .72rem; text-align: center; border-top: 1px solid #e3e2de;
  padding-top: 8px; }
.badge { display:inline-block; padding: 1px 8px; border-radius: 999px; font-size: .75rem; font-weight: 600; }
.badge-live { background:#e34948; color:#fff; }
.badge-hist { background:#e8e7e3; color:#52514e; }
.badge-all { background:#cde2fb; color:#184f95; }
.badge-sim { background:#fff4d6; color:#7a5500; border: 1px solid #f0d58a; }
.live-box { border: 1px solid #e3e2de; border-radius: 10px; padding: 12px 14px; min-height: 96px;
  background: #fff; font-size: 1.05rem; line-height: 1.5; color: #0b0b0b; }
.live-box .partial { color: #8a8984; font-style: italic; }
.status { font-size: .9rem; color: #52514e; margin-bottom: 6px; }
.dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align: middle; }
.legend-bar { height: 10px; border-radius: 5px; margin: 2px 0; }
.legend-row { display:flex; justify-content:space-between; color:#52514e; font-size:.72rem; }
</style>
""",
    unsafe_allow_html=True,
)

TERR = bornes.load()


@st.cache_resource
def conn() -> Any:
    c = db.connect(db.DEFAULT_PATH)
    db.upsert_bornes(c, TERR.bornes.values())  # la carte s'affiche même sans worker
    return c


@st.cache_data(show_spinner=False)
def frequentations(mois: int) -> tuple[dict[str, reference.Frequentation | None], str | None]:
    try:
        compteurs = {b.id: b.compteur for b in TERR.bornes.values()}
        return reference.frequentations(compteurs, mois), None
    except (FileNotFoundError, KeyError, ValueError) as e:
        return dict.fromkeys(TERR.bornes), str(e)


C = conn()
ss = st.session_state
ss.setdefault("win", None)  # None = demi-journée en cours (live) ; sinon clé de demi-journée
ss.setdefault("expect", None)  # (statut attendu, instant) juste après un clic


def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, periods.TZ).strftime("%d/%m %H:%M")


# --- colonne Backend --------------------------------------------------------------

STATUS_UI = {
    "idle": ("#1baf7a", "Prêt"),
    "recording": (RED, "Enregistrement"),
    "transcribing": ("#eda100", "Transcription finale"),
    "classifying": (BLUE, "Classification Jev"),
    "offline": (MUTED, "Worker arrêté"),
}


def worker_status() -> tuple[str, Any]:
    live = db.get_live(C)
    if live["updated_at"] is None or time.time() - live["updated_at"] > HEARTBEAT_LOST_S:
        return "offline", live
    return live["status"] or "idle", live


def simulated_ts() -> int | None:
    """Mode préparation : horodatage choisi (date simulée), sinon None (horloge du worker)."""
    if not PREP:
        return None
    local = datetime.combine(ss.sim_date, ss.sim_time, periods.TZ)
    return int(local.timestamp())


def _send(cmd: str) -> None:
    if cmd == "start":
        db.push_command(C, "start", borne_id=ss.borne, event_ts_override=simulated_ts())
        ss.expect = ("recording", time.monotonic())
    else:
        db.push_command(C, "stop")
        ss.expect = ("transcribing", time.monotonic())


@st.fragment(run_every=1.0)
def live_panel() -> None:
    status, live = worker_status()
    exp = ss.expect
    if exp and time.monotonic() - exp[1] < 3 and status not in (exp[0], "offline"):  # noqa: PLR2004
        status = exp[0]  # le worker n'a pas encore pris la commande en compte
    elif exp:
        ss.expect = None
    future = PREP and (simulated_ts() or 0) > time.time()
    if status == "recording":
        st.button("■  Stop", type="primary", width="stretch", key="btn_stop", on_click=_send, args=("stop",))
    else:
        st.button(
            "●  Enregistrer",
            type="primary",
            width="stretch",
            key="btn_start",
            disabled=status != "idle" or future,
            on_click=_send,
            args=("start",),
        )
    if status == "offline":
        st.error("Worker arrêté (pas de heartbeat depuis plus de 5 s) : lancer `python demo/worker.py`.", icon="⚠️")
    if future:
        st.warning("Date simulée dans le futur : refusée.")
    color, label = STATUS_UI.get(status, (MUTED, status))
    lang = f" · langue : <b>{html.escape(live['langue'])}</b>" if live["langue"] else ""
    msg = f" — {html.escape(live['message'])}" if live["message"] and status != "offline" else ""
    st.markdown(
        f'<div class="status"><span class="dot" style="background:{color}"></span><b>{label}</b>{lang}{msg}</div>',
        unsafe_allow_html=True,
    )
    committed = html.escape(live["committed_text"] or "")
    partial = html.escape(live["partial_text"] or "")
    body = committed + (f' <span class="partial">{partial}</span>' if partial else "")
    body = body or '<span class="partial">La transcription apparaît ici pendant l\'enregistrement…</span>'
    st.markdown(f'<div class="live-box">{body}</div>', unsafe_allow_html=True)


def _fmt_score(v: float | None) -> str:
    return NULL if v is None else f"{v:.0f}"


def _status(r: Any) -> str:
    return {"ok": "✅ ok", "error": "⚠️ erreur", None: "⏳ en cours"}[r["status"]]


def _reclassify(tid: int) -> None:
    worker.classify_transcription(C, tid, TERR)


def _delete(tid: int) -> None:
    db.delete_transcription(C, tid)


@st.fragment(run_every=1.0)
def latest_panel() -> None:
    rows = db.latest(C, N_LATEST)
    if not rows:
        st.info("Aucun avis en base pour l'instant.")
        return
    df = pd.DataFrame(
        [
            {
                "#": r["id"],
                "heure": fmt_ts(r["event_ts"]),
                "borne": r["borne_name"],
                "texte": r["texte"] if len(r["texte"]) <= 70 else r["texte"][:69] + "…",  # noqa: PLR2004
                "satisf.": _fmt_score(r["satisfaction"]),
                "affl.": _fmt_score(r["affluence"]),
                "provenance": r["provenance"] or NULL,
                "transport": r["transport"] or NULL,
                "profil": r["profil"] or NULL,
                "statut": _status(r),
            }
            for r in rows
        ]
    )
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "#": st.column_config.NumberColumn(width=40),
            "heure": st.column_config.TextColumn(width=90),
            "texte": st.column_config.TextColumn(width="medium"),
            "statut": st.column_config.TextColumn(width=95),
        },
    )
    for r in [r for r in rows if r["status"] == "error"][:3]:
        err = json.loads(r["jev_raw"]).get("error", "") if r["jev_raw"] else ""
        c1, c2 = st.columns([3, 1])
        c1.caption(f"⚠️ #{r['id']} : {html.escape(str(err)[:140])}")
        c2.button(f"Re-classifier #{r['id']}", key=f"recl_{r['id']}", on_click=_reclassify, args=(r["id"],))
    ids = [r["id"] for r in rows]
    c1, c2 = st.columns([3, 1])
    tid = c1.selectbox("Détail d'une ligne", ids, format_func=lambda i: f"#{i}", key="detail", index=0)
    c2.button("🗑 Supprimer", key="del", on_click=_delete, args=(tid,), width="stretch")
    r = next(r for r in rows if r["id"] == tid)
    st.caption(f"#{tid} · {r['borne_name']} · langue {r['langue'] or NULL}" + (" · init" if r["is_init"] else ""))
    st.markdown(f"> {html.escape(r['texte'])}")
    if r["jev_raw"]:
        st.json(json.loads(r["jev_raw"]), expanded=False)


# --- colonne Frontend (mockup téléphone) ------------------------------------------

CRITERES = {"satisfaction": "Satisfaction", "affluence": "Affluence", "provenance": "Provenance"}
CRIT_LABEL = {
    "satisfaction": "Satisfaction globale moyenne",
    "affluence": "Affluence ressentie moyenne",
    "provenance": "Part hors département",
}


def _hex(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _mix(a: str, b: str, t: float) -> str:
    ra, rb = _hex(a), _hex(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb, strict=True))


def color_for(crit: str, v: float) -> str:
    """0..100 → couleur. Divergente (rouge = défavorable, gris au milieu) ; séquentielle pour la provenance."""
    t = v / 100
    if crit == "provenance":
        return _mix(SEQ_LIGHT, SEQ_DARK, t)
    low, high = (RED, BLUE) if crit == "satisfaction" else (BLUE, RED)
    return _mix(low, NEUTRAL, t * 2) if t < 0.5 else _mix(NEUTRAL, high, (t - 0.5) * 2)  # noqa: PLR2004


def legend_html(crit: str) -> str:
    stops = ", ".join(color_for(crit, v) for v in (0, 25, 50, 75, 100))
    ends = {
        "satisfaction": ("0 · insatisfait", "100 · satisfait"),
        "affluence": ("0 · personne", "100 · trop de monde"),
        "provenance": ("0 % hors dépt.", "100 % hors dépt."),
    }[crit]
    return (
        f'<div class="legend-bar" style="background:linear-gradient(90deg,{stops})"></div>'
        f'<div class="legend-row"><span>{ends[0]}</span><span>{ends[1]}</span></div>'
        '<div class="phone-sub" style="font-size:.72rem;margin-top:4px">Taille : fréquentation par demi-journée '
        '(éco-compteur) <span class="badge badge-sim">simulé</span> · '
        f'<span style="border:2px dashed {MUTED};border-radius:50%;display:inline-block;width:10px;'
        'height:10px;vertical-align:middle"></span> sans avis</div>'
    )


def _radius(freq: reference.Frequentation | None, vmax: float) -> float:
    if freq is None or vmax <= 0:
        return 8.0
    return 7 + 18 * math.sqrt(freq.valeur / vmax)


def _tooltip(agg: Any, crit: str, val: float | None, freq: reference.Frequentation | None) -> str:
    unit = " %" if crit == "provenance" else " / 100"
    crit_txt = f"{CRIT_LABEL[crit]} : {val:.0f}{unit}" if val is not None else f"{CRIT_LABEL[crit]} : {NULL}"
    freq_txt = (
        f"Fréquentation ≈ {freq.valeur:.0f} passages / demi-journée (simulé : moyenne du mois, "
        f"compteur « {freq.compteur} », {freq.periode})"
        if freq
        else "Fréquentation : indisponible"
    )
    return f"<b>{html.escape(agg['name'])}</b><br>{agg['n_avis']} avis<br>{crit_txt}<br>{html.escape(freq_txt)}"


CRIT_COLUMN = {"satisfaction": "satisfaction", "affluence": "affluence", "provenance": "part_hors"}


def build_map(aggs: list[Any], crit: str, freqs: dict[str, reference.Frequentation | None]) -> folium.Map:
    m = folium.Map(tiles="OpenStreetMap")
    m.fit_bounds(
        [
            (min(a["lat"] for a in aggs), min(a["lon"] for a in aggs)),
            (max(a["lat"] for a in aggs), max(a["lon"] for a in aggs)),
        ],
        padding=(30, 30),
    )
    vmax = max((f.valeur for f in freqs.values() if f), default=0.0)
    for a in aggs:
        val = a[CRIT_COLUMN[crit]]
        freq = freqs.get(a["borne_id"])
        tip = _tooltip(a, crit, val, freq)
        style: dict[str, Any] = (
            {"color": "#ffffff", "weight": 2, "fill_color": color_for(crit, val), "fill_opacity": 0.95}
            if val is not None
            else {"color": MUTED, "weight": 2, "dash_array": "4 4", "fill_color": "#ffffff", "fill_opacity": 0.05}
        )
        folium.CircleMarker(
            location=(a["lat"], a["lon"]),
            radius=_radius(freq, vmax),
            tooltip=folium.Tooltip(tip, style="white-space: normal; width: 230px; font-size: 12px;"),
            popup=folium.Popup(tip, max_width=260),
            **style,
        ).add_to(m)
    return m


def _nav(action: str) -> None:
    cur = periods.demi_journee(int(time.time()))
    if action == "prev":
        ss.win = periods.decaler(ss.win or cur, -1)
    elif action == "next" and ss.win:
        nxt = periods.decaler(ss.win, 1)
        ss.win = None if periods.intervalle(nxt) >= periods.intervalle(cur) else nxt
    elif action == "live":
        ss.win, ss.all_past = None, False


def window_controls() -> tuple[str, bool]:
    """Retourne (demi-journée affichée, tout le passé ?) et affiche le badge."""
    cur = periods.demi_journee(int(time.time()))
    if ss.win and periods.intervalle(ss.win) >= periods.intervalle(cur):
        ss.win = None
    all_past = bool(ss.get("all_past"))
    c1, c2, c3 = st.columns([1, 1, 1.4])
    c1.button("◀", key="prev", width="stretch", disabled=all_past, on_click=_nav, args=("prev",))
    c2.button("▶", key="next", width="stretch", disabled=ss.win is None or all_past, on_click=_nav, args=("next",))
    c3.button(
        "● Live", key="live", width="stretch", disabled=ss.win is None and not all_past, on_click=_nav, args=("live",)
    )
    st.toggle("Tout le passé", key="all_past")
    dj = ss.win or cur
    if ss.all_past:
        badge = '<span class="badge badge-all">Tout le passé</span>'
    elif ss.win is None:
        badge = f'<span class="badge badge-live">● LIVE</span> <span class="phone-sub">{periods.libelle(dj)}</span>'
    else:
        badge = f'<span class="badge badge-hist">Historique</span> <span class="phone-sub">{periods.libelle(dj)}</span>'
    st.markdown(badge, unsafe_allow_html=True)
    return dj, bool(ss.all_past)


@st.fragment(run_every=1.0)
def phone() -> None:
    now = datetime.now(periods.TZ)
    st.markdown(
        f'<div class="phone-head"><span>🌲 Ressenti des visiteurs</span>'
        f'<span class="phone-sub">{now:%H:%M}</span></div>',
        unsafe_allow_html=True,
    )
    crit = st.segmented_control(
        "Critère",
        list(CRITERES),
        format_func=lambda k: CRITERES[k],
        key="crit",
        required=True,
        default="satisfaction",
        width="stretch",
        label_visibility="collapsed",
    )
    dj, all_past = window_controls()
    debut, fin = (None, None) if all_past else periods.intervalle(dj)
    aggs = db.agregats(C, debut, fin)
    freqs, err = frequentations(periods.mois(dj))
    st_folium(build_map(aggs, crit, freqs), height=330, use_container_width=True, returned_objects=[], key="map")
    st.markdown(legend_html(crit), unsafe_allow_html=True)
    n = sum(a["n_avis"] for a in aggs)
    pending = n - sum(a["n_ok"] or 0 for a in aggs)
    sub = f"{n} avis dans la fenêtre" + (f" · {pending} non classé(s)" if pending else "")
    st.markdown(f'<div class="phone-sub">{sub}</div>', unsafe_allow_html=True)
    if err:
        st.caption(f"⚠️ Fréquentation de référence indisponible : {err}")
    st.markdown(
        '<div class="phone-foot">Démo POC — avis anonymisés, enregistrement audio non conservé.</div>',
        unsafe_allow_html=True,
    )


# --- mise en page -----------------------------------------------------------------

col_b, col_f = st.columns([1.45, 1], gap="large")
with col_b:
    st.markdown("### 🛠️ Backend")
    st.selectbox(
        "Borne",
        list(TERR.bornes),
        format_func=lambda k: f"{TERR.bornes[k].name} · {TERR.bornes[k].commune} ({TERR.bornes[k].id_ens})",
        key="borne",
    )
    if PREP:
        now = datetime.now(periods.TZ)
        c1, c2 = st.columns(2)
        c1.date_input("Date simulée", key="sim_date", value=now.date(), max_value=now.date())
        c2.time_input(
            "Heure", key="sim_time", value=now.time().replace(second=0, microsecond=0), step=timedelta(minutes=15)
        )
        st.caption("🧪 Mode préparation : les avis enregistrés sont marqués « initialisation » (`is_init=1`).")
    live_panel()
    st.markdown(f"#### Dernières lignes ({N_LATEST})")
    latest_panel()

with col_f:
    st.markdown("### 📱 Frontend")
    with st.container(key="phone"):
        phone()
