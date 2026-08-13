import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import uuid
import html as _html
import gspread
from google.oauth2.service_account import Credentials

params = st.query_params
MODO_FERIA = params.get("modo") == "feria"

st.set_page_config(
    page_title="Náutica Viamar Feria" if MODO_FERIA else "Náutica Viamar — NautiCRM",
    page_icon="⚓",
    layout="centered" if MODO_FERIA else "wide",
    initial_sidebar_state="collapsed" if MODO_FERIA else "expanded"
)

# ─── LOGIN ───────────────────────────────────────────────────────────────────
def check_login():
    if st.session_state.get("logged_in"): return True
    st.markdown("""
    <style>
    .block-container{display:flex;justify-content:center}
    </style>
    <div style="max-width:380px;margin:60px auto 0;background:#0d1e35;border:1px solid #1a3050;border-radius:14px;padding:40px 36px;text-align:center">
      <div style="font-family:serif;color:#c9a84c;font-size:1.9rem;margin-bottom:4px">⚓ NautiCRM</div>
      <div style="color:#7a8fa6;font-size:0.82rem;margin-bottom:28px">Gestión de Ventas Náuticas</div>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_form"):
        usuario  = st.text_input("👤 Usuario",    placeholder="tu usuario")
        password = st.text_input("🔑 Contraseña", type="password", placeholder="••••••••")
        ok = st.form_submit_button("Entrar", use_container_width=True)
        if ok:
            usuarios = dict(st.secrets.get("usuarios", {}))
            if usuario in usuarios and usuarios[usuario] == password:
                st.session_state["logged_in"]       = True
                st.session_state["usuario_activo"]  = usuario
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    return False

if not MODO_FERIA and not check_login():
    st.stop()

STAGES = ["Prospecto","Contactado","Interés Confirmado","Propuesta Enviada","Negociación","Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]
FUNNEL_STAGES = [s for s in STAGES if s not in ["Cerrado Perdido","En Pausa / Recuperable"]]
PAUSA_MESES_ARCHIVO = 6
IDIOMAS = ["Español","Inglés","Francés","Italiano","Alemán","Portugués","Holandés","Ruso","Árabe","Chino","Otro"]
STAGE_COLORS = {
    "Prospecto":"#1a4a8a","Contactado":"#2563eb","Interés Confirmado":"#7c3aed",
    "Propuesta Enviada":"#b8860b","Negociación":"#ea580c","Cerrado Ganado":"#16a34a",
    "Cerrado Perdido":"#dc2626","En Pausa / Recuperable":"#374151",
}

# Webs oficiales de astilleros para generación de emails
BRAND_SITES = {
    "Jeanneau":    "jeanneau.com",
    "Beneteau":    "beneteau.com",
    "Sunseeker":   "sunseeker.com",
    "Princess":    "princess.co.uk",
    "Azimut":      "azimut-yachts.com",
    "Ferretti":    "ferretti-yachts.com",
    "Bavaria":     "bavariayachts.com",
    "Hanse":       "hanseyachts.com",
    "Lagoon":      "catamarans.com",
    "Fairline":    "fairline.com",
    "Cranchi":     "cranchi.com",
    "Sessa":       "sessamarine.it",
    "Prestige":    "prestige-yachts.com",
    "Dufour":      "dufour-yachts.com",
    "X-Yachts":    "x-yachts.com",
    "Elan":        "elan-yachts.com",
    "Nautitech":   "nautitech-catamarans.com",
    "Fountaine Pajot": "fountaine-pajot.com",
    "Leopard":     "leopardcatamarans.com",
    "Sasga":       "sasgayachts.com",
    "Lasai":       "lasai.es",
    "Karnic":      "karnic.com",
    "Wellcraft":   "wellcraft.com",
    "Quicksilver": "quicksilver-boats.com",
    "Ranieri":     "ranieri.it",
    "Fiart":       "fiart.it",
}

st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;background-color:#060e1a!important;color:#e8e0d0!important}
.main{background-color:#060e1a!important}.block-container{padding:1.5rem 2rem!important}
section[data-testid="stSidebar"]{background:#0a1628!important;border-right:1px solid #1a3050}
section[data-testid="stSidebar"] *{color:#e8e0d0!important}
h1,h2,h3{font-family:'Playfair Display',serif!important;color:#c9a84c!important}
[data-testid="metric-container"]{background:#0d1e35;border:1px solid #1a3050;border-radius:10px;padding:1rem 1.2rem}
[data-testid="metric-container"] label{color:#7a8fa6!important;font-size:0.7rem!important;text-transform:uppercase;letter-spacing:1px}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#c9a84c!important;font-family:monospace!important;font-size:1.6rem!important}
.stTextInput input,.stNumberInput input,.stTextArea textarea{background:#091220!important;color:#e8e0d0!important;border:1px solid #1a3050!important}
.stButton>button,[data-testid="stFormSubmitButton"]>button{background:#c9a84c!important;color:#0a1628!important;font-weight:700!important;border:none!important;border-radius:6px!important}
.stButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover{opacity:.88!important}
.stDataFrame{border:1px solid #1a3050!important;border-radius:8px!important}
.stTabs [data-baseweb="tab-list"]{background:#0a1628;border-radius:8px;gap:4px;padding:4px}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#7a8fa6!important;border-radius:6px!important}
.stTabs [aria-selected="true"]{background:#c9a84c!important;color:#0a1628!important;font-weight:700!important}
.streamlit-expanderHeader{background:#0d1e35!important;border:1px solid #1a3050!important;border-radius:8px!important}
hr{border-color:#1a3050!important}
</style>''', unsafe_allow_html=True)

# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────
import time as _time

def _api_error_msg(e):
    """Extrae código HTTP y mensaje real del APIError de gspread."""
    try:
        r = e.response
        return f"HTTP {r.status_code}: {r.json().get('error',{}).get('message', r.text[:200])}"
    except Exception:
        return str(e)

@st.cache_resource(ttl=3300)  # renovar credenciales antes de que expire el token de 1h
def _get_sh_and_ws():
    """Abre la hoja y carga el índice completo de worksheets en UNA sola lectura."""
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["spreadsheet_id"])
    ws_dict = {ws.title: ws for ws in sh.worksheets()}
    return sh, ws_dict

def _get_spreadsheet():
    sh, _ = _get_sh_and_ws()
    return sh

def get_sheet(tab):
    last_exc = None
    for _attempt in range(3):
        try:
            sh, ws_dict = _get_sh_and_ws()
            if tab in ws_dict:
                return ws_dict[tab]
            ws = sh.add_worksheet(title=tab, rows=1000, cols=30)
            _get_sh_and_ws.clear()
            return ws
        except gspread.exceptions.APIError as e:
            last_exc = e
            try: _status = e.response.status_code
            except: _status = 0
            if _status == 429:
                break
            _get_sh_and_ws.clear()
            if _attempt < 2:
                _time.sleep(2 ** _attempt)
    raise RuntimeError(f"Error conectando con Google Sheets — {_api_error_msg(last_exc)}")

LEAD_COLS = ["id","nombre","empresa","telefono","email","idioma","tipoEmbarcacion","modeloEslora","presupuesto","usoPrevisto","asignadoA","etapa","probabilidad","valorOperacion","fuenteLead","proximaAccion","fechaProximaAccion","historial","fechaCreacion","ultimaActualizacion"]
ARCH_COLS  = LEAD_COLS + ["fechaArchivo", "motivoArchivo"]
PASIV_COLS = LEAD_COLS + ["fechaPasivo"]

@st.cache_data(ttl=180)
def load_leads():
    ws = get_sheet("Leads")
    all_values = ws.get_all_values()
    # Si la hoja está vacía del todo, crear cabeceras
    if not all_values:
        ws.append_row(LEAD_COLS)
        return []
    # Si solo hay una fila (las cabeceras), no hay leads aún
    if len(all_values) <= 1:
        return []
    headers = all_values[0]
    data = [dict(zip(headers, row)) for row in all_values[1:]]
    rows = []
    for r in data:
        # Saltar filas que sean cabeceras duplicadas
        if r.get("id") == "id" or r.get("nombre") == "nombre":
            continue
        lead = {c: r.get(c,"") for c in LEAD_COLS}
        lead["presupuesto"]    = int(float(lead["presupuesto"]))    if lead["presupuesto"]    else 0
        lead["valorOperacion"] = int(float(lead["valorOperacion"])) if lead["valorOperacion"] else 0
        lead["probabilidad"]   = int(float(lead["probabilidad"]))   if lead["probabilidad"]   else 0
        # historial como lista
        h = lead["historial"]
        if isinstance(h, str) and h:
            import json as _jl
            if h.startswith("["):  # JSON (nuevo formato)
                try: lead["historial"] = _jl.loads(h)
                except: lead["historial"] = []
            else:  # legacy: "fecha|tipo|nota;;fecha|tipo|nota"
                entries = []
                for e in h.split(";;"):
                    parts = e.split("|", 2)
                    if len(parts) == 3: entries.append({"fecha": parts[0], "tipo": parts[1], "nota": parts[2]})
                lead["historial"] = entries
        else:
            lead["historial"] = []
        rows.append(lead)
    return rows

@st.cache_data(ttl=191)
def load_config():
    ws = get_sheet("Config")
    all_values = ws.get_all_values()
    vendedores = ["Vendedor 1","Vendedor 2","Vendedor 3"]
    boat_types = ["Velero","Motor","Catamarán","Zodiac","Charter","Jeanneau","Beneteau","Sunseeker","Princess","Azimut","Ferretti","Bavaria","Hanse","Lagoon","Otro"]
    sources    = ["Feria Náutica","Web","Referido","RRSS","Llamada Fría","Otro"]
    if not all_values or len(all_values) <= 1:
        data = []
    else:
        headers = all_values[0]
        data = [dict(zip(headers, row)) for row in all_values[1:]]
    if not data:
        ws.append_row(["key","value"])
        for i,v in enumerate(vendedores): ws.append_row([f"v{i+1}",v])
        ws.append_row(["boat_types", "||".join(boat_types)])
        ws.append_row(["sources", "||".join(sources)])
        return vendedores, boat_types, sources
    df = pd.DataFrame(data)
    vv = df[df["key"].isin(["v1","v2","v3"])]["value"].tolist()
    if vv: vendedores = vv
    bt_row = df[df["key"]=="boat_types"]["value"].tolist()
    if bt_row: boat_types = bt_row[0].split("||")
    src_row = df[df["key"]=="sources"]["value"].tolist()
    if src_row: sources = src_row[0].split("||")
    return vendedores, boat_types, sources

def save_lead(lead, is_new=True):
    ws = get_sheet("Leads")
    import json as _jsl
    hist_str = _jsl.dumps(lead.get("historial", []), ensure_ascii=False)
    row = [lead.get(c,"") for c in LEAD_COLS[:-1]] + [hist_str if c=="historial" else lead.get(c,"") for c in ["ultimaActualizacion"]]
    row = []
    for c in LEAD_COLS:
        if c == "historial": row.append(hist_str)
        else: row.append(lead.get(c,""))
    if is_new:
        ws.append_row(row)
    else:
        all_values = ws.get_all_values()
        if all_values and len(all_values) > 1:
            headers = all_values[0]
            data = [dict(zip(headers, row)) for row in all_values[1:]]
            for i,r in enumerate(data):
                if r.get("id") == lead["id"]:
                    ws.update([row], f"A{i+2}:{chr(64+len(LEAD_COLS))}{i+2}")
                    break
    load_leads.clear()

def delete_lead(lead_id):
    ws = get_sheet("Leads")
    all_values = ws.get_all_values()
    if all_values and len(all_values) > 1:
        headers = all_values[0]
        data = [dict(zip(headers, row)) for row in all_values[1:]]
        for i,r in enumerate(data):
            if r.get("id") == lead_id:
                ws.delete_rows(i+2); break
    load_leads.clear()

def _sheet_exists(name):
    try:
        _, ws_dict = _get_sh_and_ws()
        return name in ws_dict
    except: return False

def _ensure_sheet(name, cols):
    sh, ws_dict = _get_sh_and_ws()
    if name not in ws_dict:
        ws = sh.add_worksheet(title=name, rows=200, cols=len(cols)+2)
        ws.update([cols], "A1")
        _get_sh_and_ws.clear()
        return ws
    return ws_dict[name]

def _serialize_lead_row(l, col_list):
    import json as _js
    hist = l.get("historial", [])
    if isinstance(hist, list):
        hist_str = _js.dumps(hist, ensure_ascii=False)
    else:
        hist_str = str(hist)
    row = []
    for c in col_list:
        if c == "historial":
            row.append(hist_str)
        else:
            v = l.get(c, "")
            row.append(str(v) if v is not None else "")
    return row

def _deserialize_lead_rows(ws_rows, col_list):
    if not ws_rows or len(ws_rows) <= 1: return []
    headers = ws_rows[0]
    result = []
    for row in ws_rows[1:]:
        if not any(row): continue
        padded = row + [""] * max(0, len(headers) - len(row))
        l = dict(zip(headers, padded))
        h_raw = l.get("historial", "")
        if h_raw:
            import json as _jdr
            if h_raw.startswith("["):  # JSON (nuevo formato)
                try: l["historial"] = _jdr.loads(h_raw)
                except: l["historial"] = []
            else:  # legacy: "fecha|tipo|nota;;..."
                try:
                    entries = [e.split("|", 2) for e in h_raw.split(";;") if e]
                    l["historial"] = [{"fecha": e[0], "tipo": e[1] if len(e) > 1 else "", "nota": e[2] if len(e) > 2 else ""} for e in entries]
                except: l["historial"] = []
        else:
            l["historial"] = []
        result.append(l)
    return result

@st.cache_data(ttl=203)
def load_archivo_frio():
    try:
        if not _sheet_exists("ArchivoFrio"):
            _migrate_archivo_from_config()
            return load_archivo_frio()
        ws = get_sheet("ArchivoFrio")
        return _deserialize_lead_rows(ws.get_all_values(), ARCH_COLS)
    except: return []

@st.cache_data(ttl=217)
def load_clientes_pasivos():
    try:
        if not _sheet_exists("ClientesPasivos"):
            _migrate_pasivos_from_config()
            return load_clientes_pasivos()
    except: return []
    try:
        ws = get_sheet("ClientesPasivos")
        return _deserialize_lead_rows(ws.get_all_values(), PASIV_COLS)
    except: return []

def save_archivo_frio(archivo):
    ws = _ensure_sheet("ArchivoFrio", ARCH_COLS)
    rows = [ARCH_COLS] + [_serialize_lead_row(l, ARCH_COLS) for l in (archivo or [])]
    ws.clear()
    ws.update(rows, "A1")
    load_archivo_frio.clear()

def save_clientes_pasivos(pasivos):
    ws = _ensure_sheet("ClientesPasivos", PASIV_COLS)
    rows = [PASIV_COLS] + [_serialize_lead_row(l, PASIV_COLS) for l in (pasivos or [])]
    ws.clear()
    ws.update(rows, "A1")
    load_clientes_pasivos.clear()

def _migrate_archivo_from_config():
    """Migración única: mueve archivo_frio de celda JSON de Config a hoja ArchivoFrio."""
    import json as _jm
    try:
        ws_cfg = get_sheet("Config")
        rows = ws_cfg.get_all_values()
        df = {r[0]: r[1] for r in rows[1:] if len(r) >= 2}
        raw = df.get("archivo_frio", "")
        archivo = _jm.loads(raw) if raw else []
        save_archivo_frio(archivo)
    except: save_archivo_frio([])

def _migrate_pasivos_from_config():
    """Migración única: mueve clientes_pasivos de celda JSON de Config a hoja ClientesPasivos."""
    import json as _jm
    try:
        ws_cfg = get_sheet("Config")
        rows = ws_cfg.get_all_values()
        df = {r[0]: r[1] for r in rows[1:] if len(r) >= 2}
        raw = df.get("clientes_pasivos", "")
        pasivos = _jm.loads(raw) if raw else []
        save_clientes_pasivos(pasivos)
    except: save_clientes_pasivos([])

def con_cambio_etapa(lead_dict, etapa_anterior):
    """Si la etapa cambió, añade entrada automática al historial."""
    nueva = lead_dict.get("etapa","")
    if etapa_anterior and nueva and etapa_anterior != nueva:
        hist = lead_dict.get("historial",[]).copy()
        hist.append({"fecha":str(date.today()),"tipo":"Cambio etapa","nota":f"{etapa_anterior} → {nueva}"})
        return {**lead_dict,"historial":hist}
    return lead_dict

def save_config(vendedores, boat_types, sources, archivo=None, pasivos=None):
    ws = get_sheet("Config")
    rows = [
        ["key", "value"],
        ["v1", vendedores[0]],
        ["v2", vendedores[1]],
        ["v3", vendedores[2]],
        ["boat_types", "||".join(boat_types)],
        ["sources", "||".join(sources)],
    ]
    ws.clear()
    ws.update(rows, "A1")
    load_config.clear()
    if archivo is not None:
        save_archivo_frio(archivo)
    if pasivos is not None:
        save_clientes_pasivos(pasivos)

def _migrar_tipo_embarcacion(old_name, new_name):
    """Sustituye old_name por new_name en tipoEmbarcacion en los tres sheets de datos."""
    resultados = {}
    for sheet_name, col_list, loader, cache_clear in [
        ("Leads",           LEAD_COLS,  load_leads,           load_leads.clear),
        ("ArchivoFrio",     ARCH_COLS,  load_archivo_frio,    load_archivo_frio.clear),
        ("ClientesPasivos", PASIV_COLS, load_clientes_pasivos, load_clientes_pasivos.clear),
    ]:
        try:
            lead_list = loader()
            afectados = [l for l in lead_list if l.get("tipoEmbarcacion","") == old_name]
            if not afectados:
                resultados[sheet_name] = 0
                continue
            updated = [{**l, "tipoEmbarcacion": new_name} if l.get("tipoEmbarcacion","") == old_name else l
                       for l in lead_list]
            ws = get_sheet(sheet_name)
            rows = [col_list] + [_serialize_lead_row(l, col_list) for l in updated]
            ws.clear()
            ws.update(rows, "A1")
            cache_clear()
            resultados[sheet_name] = len(afectados)
        except Exception as _me:
            resultados[sheet_name] = f"Error: {_me}"
    return resultados

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def fmt_eur(n):
    try: return f"€{int(n):,}".replace(",",".")
    except: return "—"

def urg_emoji(ds):
    if not ds: return "⚪"
    try:
        diff=(datetime.strptime(str(ds),"%Y-%m-%d").date()-date.today()).days
        return "🔴" if diff<0 else "🟡" if diff==0 else "🟢"
    except: return "⚪"

def days_since(ds):
    try: return (date.today()-datetime.strptime(str(ds),"%Y-%m-%d").date()).days
    except: return 0

def months_since(ds):
    if not ds: return 999
    try:
        d=datetime.strptime(str(ds),"%Y-%m-%d").date()
        return (date.today().year-d.year)*12+(date.today().month-d.month)
    except: return 0

def _lead_display(l):
    """Clave de visualización única para selectboxes: 'Nombre · Empresa'."""
    empresa = (l.get("empresa") or "").strip()
    return f"{l['nombre']} · {empresa}" if empresa else l["nombre"]

# ─── EMAIL GENERATOR ──────────────────────────────────────────────────────────
import urllib.parse as _urlparse, re as _re

def _detectar_marca(tipo_emb):
    """Detecta la marca del astillero a partir del campo tipoEmbarcacion."""
    if not tipo_emb: return None, None
    t = tipo_emb.strip()
    for marca in sorted(BRAND_SITES.keys(), key=len, reverse=True):
        if marca.lower() in t.lower():
            modelo = _re.sub(_re.escape(marca), "", t, flags=_re.IGNORECASE).strip(" -·/")
            return marca, modelo or t
    # Si no hay marca conocida, devolver el texto completo como modelo sin marca
    return None, t

def _fetch_model_info(marca, modelo_eslora):
    """Busca info del modelo en la web oficial del astillero vía DuckDuckGo."""
    import requests as _rq
    site = BRAND_SITES.get(marca, "")
    if not site:
        return None, None, f"Astillero '{marca}' no está en el directorio de webs."

    # Componer búsqueda: marca + modelo en la web oficial
    query = f"{marca} {modelo_eslora} site:{site}"
    hdrs  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"}
    try:
        sr = _rq.get(
            f"https://html.duckduckgo.com/html/?q={_urlparse.quote(query)}",
            headers=hdrs, timeout=12
        )
        # Extraer primera URL del dominio oficial
        urls = _re.findall(
            r'href="(https?://(?:www\.)?' + _re.escape(site) + r'[^"&]*)"',
            sr.text
        )
        # Filtrar redirecciones de DuckDuckGo
        urls = [u for u in urls if site in u and "duckduckgo" not in u]
        if not urls:
            return None, None, f"No se encontró la página de '{modelo_eslora}' en {site}."

        page_url = urls[0]
        pr = _rq.get(page_url, headers=hdrs, timeout=12)
        pr.encoding = "utf-8"
        raw = pr.text

        # Limpiar HTML: eliminar scripts, estilos, nav, footer
        for tag in ("script","style","nav","footer","header","noscript"):
            raw = _re.sub(rf"<{tag}[^>]*>.*?</{tag}>", " ", raw, flags=_re.DOTALL|_re.IGNORECASE)
        text = _re.sub(r"<[^>]+>", " ", raw)
        text = _re.sub(r"\s+", " ", text).strip()

        # Quedarnos con los primeros 3.500 caracteres útiles
        return text[:3500], page_url, None

    except Exception as e:
        return None, None, str(e)

def _generar_email(lead, info_web, url_modelo):
    """Genera email de seguimiento con Claude. info_web puede ser None."""
    import anthropic as _ant
    _ac = _ant.Anthropic(api_key=st.secrets["anthropic_api_key"])

    nombre   = lead.get("nombre","")
    idioma   = lead.get("idioma","Español")
    tipo     = lead.get("tipoEmbarcacion","")
    modelo   = lead.get("modeloEslora","")
    pres     = lead.get("presupuesto",0)
    notas    = lead.get("usoPrevisto","")
    etapa    = lead.get("etapa","")

    info_block = ""
    aviso_web  = ""
    if info_web:
        info_block = f"\n\nINFORMACIÓN OFICIAL DEL MODELO (extraída de {url_modelo}):\n{info_web}"
    else:
        aviso_web = "\n⚠️ No se encontró información específica del modelo en la web del astillero. Genera un email de presentación general."

    prompt = f"""Eres el equipo comercial de Náutica Viamar, distribuidores oficiales para Ibiza y Formentera.

Genera un email comercial en {idioma} para este cliente:
- Nombre: {nombre}
- Interés: {tipo} {modelo}
- Presupuesto aprox: {"€{:,}".format(pres) if pres else "No indicado"}
- Notas internas (NO mencionar textualmente): {notas}
- Etapa comercial: {etapa}
{info_block}{aviso_web}

INSTRUCCIONES:
- Escríbelo en {idioma}
- Agradece su interés/visita de forma natural y cálida
- Preséntanos como distribuidores exclusivos para Ibiza y Formentera{"de " + tipo.split()[0] if tipo else ""}
{"- Destaca 2-3 puntos clave del modelo basándote en la info de la web (sin inventar datos)" if info_web else "- Email de presentación general: quiénes somos, cómo podemos ayudar, disposición total"}
- Invita a visitar el showroom o agendar una llamada
- Trato de USTED siempre, es un cliente nuevo que no conocemos — nunca tutees
- Tono profesional pero cercano, sin ser demasiado comercial
- Añade asunto del email en la primera línea: "Asunto: ..."
- Firma: Equipo Náutica Viamar — Distribuidores Ibiza & Formentera"""

    resp = _ac.messages.create(
        model="claude-opus-4-5",
        max_tokens=1800,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.content[0].text

# ─── BACKUP ───────────────────────────────────────────────────────────────────
BACKUP_MAX = 30  # máximo de copias a conservar

def _backup_name_today():
    return f"Bak_{date.today().strftime('%Y%m%d')}"

def _list_backup_sheets():
    """Devuelve lista de hojas Bak_ (solo Leads) ordenadas de más reciente a más antigua."""
    try:
        _, ws_dict = _get_sh_and_ws()
        sheets = [ws for title, ws in ws_dict.items()
                  if title.startswith("Bak_") and not title.startswith(("BakCfg_","BakArch_","BakPas_"))]
        return sorted(sheets, key=lambda x: x.title, reverse=True)
    except: return []

def _backup_sheet(sp, src_name, bak_prefix, today_str, existing_titles, ws_dict):
    """Crea copia de seguridad de una hoja si no existe ya para hoy."""
    bname = f"{bak_prefix}{today_str}"
    if bname in existing_titles: return
    if src_name not in existing_titles: return
    src_ws = ws_dict.get(src_name)
    if src_ws is None: return
    data = src_ws.get_all_values()
    nrows = max(len(data) + 10, 50)
    ncols = max(len(data[0]) if data else 5, 5)
    bak_ws = sp.add_worksheet(title=bname, rows=nrows, cols=ncols)
    if data: bak_ws.update(data, "A1")
    existing_titles.add(bname)

def _do_backup():
    """Crea la copia del día si no existe. Devuelve (creada:bool, msg:str)."""
    try:
        today_str = date.today().strftime('%Y%m%d')
        bname = f"Bak_{today_str}"
        sh, ws_dict = _get_sh_and_ws()
        sp = sh
        existing_titles = set(ws_dict.keys())
        if bname in existing_titles:
            return False, f"Ya existe copia de hoy ({bname})"
        # Leer datos actuales de Leads
        leads_ws = ws_dict.get("Leads") or get_sheet("Leads")
        all_data = leads_ws.get_all_values()
        nrows = max(len(all_data) + 10, 50)
        bak_ws = sp.add_worksheet(title=bname, rows=nrows, cols=len(LEAD_COLS)+2)
        if all_data:
            bak_ws.update(all_data, "A1")
        existing_titles.add(bname)
        # Backup de las demás hojas importantes (sin lecturas API adicionales)
        _backup_sheet(sp, "Config", "BakCfg_", today_str, existing_titles, ws_dict)
        _backup_sheet(sp, "ArchivoFrio", "BakArch_", today_str, existing_titles, ws_dict)
        _backup_sheet(sp, "ClientesPasivos", "BakPas_", today_str, existing_titles, ws_dict)
        # Purgar copias antiguas usando existing_titles en memoria (sin releer la API)
        bak_titles = sorted([t for t in existing_titles
                              if t.startswith("Bak_") and not t.startswith(("BakCfg_","BakArch_","BakPas_"))])
        while len(bak_titles) > BACKUP_MAX:
            old_title = bak_titles[0]
            old_ws = ws_dict.get(old_title)
            if old_ws:
                sp.del_worksheet(old_ws)
            bak_titles = bak_titles[1:]
            existing_titles.discard(old_title)
        for prefix in ("BakCfg_","BakArch_","BakPas_"):
            _aux = sorted([t for t in existing_titles if t.startswith(prefix)])
            while len(_aux) > BACKUP_MAX:
                old_title = _aux[0]
                old_ws = ws_dict.get(old_title)
                if old_ws:
                    sp.del_worksheet(old_ws)
                _aux = _aux[1:]
                existing_titles.discard(old_title)
        _get_sh_and_ws.clear()  # invalidar caché — se crearon hojas nuevas
        return True, bname
    except Exception as e:
        return False, str(e)

def _restore_backup(sheet_name):
    """Restaura la hoja Leads desde una copia de seguridad."""
    try:
        sh, ws_dict = _get_sh_and_ws()
        bak_ws = ws_dict.get(sheet_name)
        if bak_ws is None:
            return False, f"Hoja '{sheet_name}' no encontrada en caché — recarga la página e inténtalo."
        all_data = bak_ws.get_all_values()
        if not all_data:
            return False, "La copia está vacía."
        leads_ws = ws_dict.get("Leads") or get_sheet("Leads")
        leads_ws.clear()
        leads_ws.update(all_data, "A1")
        load_leads.clear()
        return True, f"✅ Leads restaurados desde {sheet_name} ({len(all_data)-1} registros)"
    except Exception as e:
        return False, str(e)

def _backup_to_json(sheet_name):
    """Exporta una copia de seguridad como JSON."""
    import json as _jbak
    try:
        _, ws_dict = _get_sh_and_ws()
        bak_ws = ws_dict.get(sheet_name)
        if bak_ws is None: return None
        rows = bak_ws.get_all_values()
        if not rows: return None
        headers, data = rows[0], rows[1:]
        leads = [dict(zip(headers, row)) for row in data if any(row)]
        # Deserializar historial
        for l in leads:
            raw_h = l.get("historial","")
            if raw_h:
                try: l["historial"] = _jbak.loads(raw_h)
                except: pass
        return _jbak.dumps({"backup": sheet_name, "fecha_exportacion": str(date.today()), "registros": leads}, ensure_ascii=False, indent=2)
    except: return None

@st.cache_data(ttl=300)
def _last_backup_date():
    """Devuelve la fecha del último backup como date, o None. Cache 5 min."""
    try:
        baks = _list_backup_sheets()
        if not baks: return None
        name = baks[0].title  # más reciente
        ds = name[4:12]  # "20260504"
        return datetime(int(ds[:4]), int(ds[4:6]), int(ds[6:8])).date()
    except: return None

def _backup_to_github(all_leads, archivo, pasivos):
    """Sube un JSON completo a un repositorio privado de GitHub."""
    import requests as _req, base64 as _b64, json as _jg
    token = st.secrets.get("github_token","").strip()
    repo  = st.secrets.get("backup_repo","").strip()
    if not token or not repo:
        return False, "github_token / backup_repo no configurados en secrets"
    try:
        export = {
            "fecha": str(date.today()),
            "generado_por": "NautiCRM - Náutica Viamar",
            "leads_activos":    all_leads,
            "archivo_frio":     archivo,
            "clientes_pasivos": pasivos,
        }
        content_bytes = _jg.dumps(export, ensure_ascii=False, indent=2).encode("utf-8")
        content_b64   = _b64.b64encode(content_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        base   = f"https://api.github.com/repos/{repo}"
        fname  = f"backup_{date.today().strftime('%Y%m%d')}.json"
        url    = f"{base}/contents/{fname}"

        # Intentar Contents API (funciona si el repo tiene al menos un commit)
        r_get = _req.get(url, headers=headers, timeout=15)
        sha   = r_get.json().get("sha") if r_get.status_code == 200 else None
        payload = {"message": f"NautiCRM backup {date.today()}", "content": content_b64}
        if sha: payload["sha"] = sha
        r_put = _req.put(url, headers=headers, json=payload, timeout=20)

        if r_put.status_code in [200, 201]:
            return True, f"GitHub: {repo}/{fname}"

        # Si falla (repo vacío sin commits), usar Git Data API de bajo nivel
        if r_put.status_code == 404:
            # 1. Crear blob
            rb = _req.post(f"{base}/git/blobs", headers=headers,
                           json={"content": content_b64, "encoding": "base64"}, timeout=15)
            if rb.status_code != 201:
                return False, f"Git blob error {rb.status_code}: {rb.json().get('message','')}"
            blob_sha = rb.json()["sha"]
            # 2. Crear tree
            rt = _req.post(f"{base}/git/trees", headers=headers,
                           json={"tree": [{"path": fname, "mode": "100644", "type": "blob", "sha": blob_sha}]}, timeout=15)
            if rt.status_code != 201:
                return False, f"Git tree error {rt.status_code}: {rt.json().get('message','')}"
            tree_sha = rt.json()["sha"]
            # 3. Crear commit
            rc = _req.post(f"{base}/git/commits", headers=headers,
                           json={"message": f"NautiCRM backup {date.today()}", "tree": tree_sha}, timeout=15)
            if rc.status_code != 201:
                return False, f"Git commit error {rc.status_code}: {rc.json().get('message','')}"
            commit_sha = rc.json()["sha"]
            # 4. Crear rama main
            rr = _req.post(f"{base}/git/refs", headers=headers,
                           json={"ref": "refs/heads/main", "sha": commit_sha}, timeout=15)
            if rr.status_code in [200, 201]:
                return True, f"GitHub: {repo}/{fname} (repo inicializado)"
            else:
                return False, f"Git ref error {rr.status_code}: {rr.json().get('message','')}"

        _detail = r_put.json()
        return False, f"Error {r_put.status_code}: {_detail.get('message','')} {_detail.get('errors','')}"
    except Exception as e:
        return False, str(e)

def _github_backup_configured():
    return bool(st.secrets.get("github_token","") and st.secrets.get("backup_repo",""))

@st.cache_data(ttl=300)
def _last_github_backup_date():
    """Comprueba la fecha del backup más reciente en GitHub. Cache 5 min."""
    import requests as _req
    token = st.secrets.get("github_token","")
    repo  = st.secrets.get("backup_repo","")
    if not token or not repo: return None
    try:
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        r = _req.get(f"https://api.github.com/repos/{repo}/contents/", headers=headers, timeout=10)
        if r.status_code != 200: return None
        bak_files = sorted([f["name"] for f in r.json() if f["name"].startswith("backup_") and f["name"].endswith(".json")], reverse=True)
        if not bak_files: return None
        ds = bak_files[0][7:15]  # "20260504" from "backup_20260504.json"
        return datetime(int(ds[:4]), int(ds[4:6]), int(ds[6:8])).date()
    except: return None

# ─── CARGAR DATOS ─────────────────────────────────────────────────────────────
try:
    all_leads_raw = load_leads()
    vendedores, boat_types, sources = load_config()
    archivo_frio = load_archivo_frio()
    clientes_pasivos = load_clientes_pasivos()
except Exception as e:
    _emsg = str(e)
    if "429" in _emsg:
        st.warning("⏳ Google Sheets está temporalmente saturado (cuota de lecturas excedida). Espera 30–60 segundos y recarga la página.")
        st.caption("No es un problema de configuración — la cuota se libera automáticamente.")
    else:
        st.error(f"❌ Error conectando con Google Sheets: {e}")
        st.info("Comprueba que los Secrets están bien configurados en Streamlit Cloud.")
    st.stop()

# Auto-archivar
def auto_archivar(leads):
    activos, archivados = [], []
    for l in leads:
        if l.get("etapa")=="En Pausa / Recuperable" and months_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))>=PAUSA_MESES_ARCHIVO:
            archivados.append({**l,"fechaArchivo":str(date.today())}); continue
        activos.append(l)
    return activos, archivados

activos, nuevos_arch = auto_archivar(all_leads_raw)
if nuevos_arch:
    archivo_frio.extend(nuevos_arch)
    save_archivo_frio(archivo_frio)
    for l in nuevos_arch: delete_lead(l["id"])
    all_leads_raw = activos

# Auto-pasar a pasivo: Cerrado Ganado con 12+ meses
_nuevos_pasivos=[l for l in all_leads_raw
    if l.get("etapa")=="Cerrado Ganado" and months_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))>=12]
if _nuevos_pasivos:
    clientes_pasivos.extend([{**l,"fechaPasivo":str(date.today())} for l in _nuevos_pasivos])
    save_clientes_pasivos(clientes_pasivos)
    for l in _nuevos_pasivos: delete_lead(l["id"])
    all_leads_raw=[l for l in all_leads_raw if l["id"] not in {x["id"] for x in _nuevos_pasivos}]

# Auto-backup diario (una vez por sesión, silencioso)
if not st.session_state.get("_backup_done"):
    st.session_state["_backup_done"] = True
    try: _do_backup()                                                          # Google Sheets
    except: pass
    try: _backup_to_github(all_leads_raw, archivo_frio, clientes_pasivos)     # GitHub (si configurado)
    except: pass

# ══ MODO FERIA ════════════════════════════════════════════════════════════════
if MODO_FERIA:
    st.markdown("""<style>
    .block-container{padding:1rem!important}
    .stButton>button{width:100%;padding:.8rem!important;font-size:1rem!important;border-radius:10px!important;margin-top:8px!important}
    </style>""", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;font-size:1.5rem;margin-bottom:0'>⚓ Alta Rápida</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#7a8fa6;font-size:0.82rem;margin-top:2px'>Modo Feria — registro rápido de contactos</p>", unsafe_allow_html=True)
    st.markdown("---")
    with st.form("feria_form", clear_on_submit=True):
        nombre   = st.text_input("👤 Nombre completo *")
        empresa  = st.text_input("🏢 Empresa")
        telefono = st.text_input("📱 Teléfono / WhatsApp")
        email    = st.text_input("📧 Email")
        idioma   = st.selectbox("🌍 Idioma", IDIOMAS)
        tipo     = st.selectbox("🚢 Tipo / Marca", boat_types)
        modelo   = st.text_input("📐 Modelo / Eslora")
        presu    = st.number_input("💶 Presupuesto aprox. (€)", min_value=0, step=10000)
        asig     = st.selectbox("👔 Asignar a", vendedores)
        nota_ini = st.text_area("📝 Nota inicial", placeholder="Observaciones...", height=80)
        ok = st.form_submit_button("✅ GUARDAR LEAD", use_container_width=True)
        if ok:
            if not nombre.strip(): st.error("El nombre es obligatorio.")
            else:
                nuevo = {"id":str(uuid.uuid4()),"nombre":nombre,"empresa":empresa,"telefono":telefono,"email":email,"idioma":idioma,"tipoEmbarcacion":tipo,"modeloEslora":modelo,"presupuesto":int(presu),"usoPrevisto":"","asignadoA":asig,"etapa":"Prospecto","probabilidad":10,"valorOperacion":int(presu),"fuenteLead":"Feria Náutica","proximaAccion":"Contactar post-feria","fechaProximaAccion":str(date.today()+timedelta(days=3)),"historial":[{"fecha":str(date.today()),"tipo":"Nota","nota":nota_ini.strip()}] if nota_ini.strip() else [],"fechaCreacion":str(date.today()),"ultimaActualizacion":str(date.today())}
                save_lead(nuevo, is_new=True)
                st.success(f"✅ **{nombre}** guardado."); st.balloons()
    st.markdown("---")
    recientes=[l for l in all_leads_raw if l.get("fuenteLead")=="Feria Náutica"][-5:]
    if recientes:
        st.caption(f"Últimos {len(recientes)} leads de feria:")
        for l in reversed(recientes):
            st.markdown(f"<div style='background:#0d1e35;border:1px solid #1a3050;border-radius:8px;padding:10px 14px;margin-bottom:6px'><span style='color:#c9a84c;font-weight:700'>{_html.escape(l['nombre'])}</span><span style='color:#7a8fa6;font-size:0.78rem'> · {_html.escape(l.get('empresa',''))} · {_html.escape(l.get('tipoEmbarcacion',''))}</span></div>", unsafe_allow_html=True)
    st.stop()

# ══ SIDEBAR ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    try:
        st.image("LOGO-viamar - bueno.jpg", use_container_width=True)
    except:
        pass
    st.markdown("## ⚓ NautiCRM")
    st.markdown("*Náutica Viamar*")
    st.markdown("---")
    active_user  = st.selectbox("👤 Usuario activo", vendedores)
    my_portfolio = st.checkbox("📂 Ver solo mi cartera")
    st.markdown("---")
    # Navegación con soporte de redirección desde kanban/lista
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "⊞ Funnel Kanban"
    if st.session_state.get("_nav_request"):
        st.session_state["nav_page"] = st.session_state["_nav_request"]
        st.session_state["_nav_request"] = None
    if st.session_state.get("goto_lead"):
        st.session_state["nav_page"] = "➕ Nuevo / Editar Lead"
    page = st.radio("Navegación",[
        "⊞ Funnel Kanban","📅 Próximas Acciones","➕ Nuevo / Editar Lead",
        "📊 Informes","💬 Asistente IA","≡ Lista de Leads","🧊 Archivo Frío","⚙️ Configuración"
    ], key="nav_page")
    if page != "➕ Nuevo / Editar Lead":
        st.session_state["goto_lead"] = None
    st.markdown("---")
    if st.button("🔄 Actualizar datos"): load_leads.clear(); load_config.clear(); load_archivo_frio.clear(); load_clientes_pasivos.clear(); _last_backup_date.clear(); _last_github_backup_date.clear(); st.rerun()
    n_arch=len(archivo_frio)
    if n_arch>0: st.markdown(f"<div style='background:#1a3050;border-radius:6px;padding:6px 10px;font-size:0.75rem;color:#7a8fa6;margin-bottom:4px'>🧊 Archivo Frío: <b style='color:#e8e0d0'>{n_arch}</b></div>", unsafe_allow_html=True)
    n_pas=len(clientes_pasivos)
    if n_pas>0: st.markdown(f"<div style='background:#1a3050;border-radius:6px;padding:6px 10px;font-size:0.75rem;color:#7a8fa6'>👤 Clientes Pasivos: <b style='color:#e8e0d0'>{n_pas}</b></div>", unsafe_allow_html=True)
    # Indicador de backup
    _lbd = _last_backup_date()
    if _lbd:
        _dias_bak = (date.today() - _lbd).days
        _bak_color = "#2d7a2d" if _dias_bak==0 else "#b8860b" if _dias_bak<=3 else "#8b1a1a"
        _bak_label = "hoy" if _dias_bak==0 else f"hace {_dias_bak}d"
        st.markdown(f"<div style='background:{_bak_color};border-radius:6px;padding:5px 10px;font-size:0.72rem;color:#e8e0d0;margin-top:4px'>💾 Sheets: <b>{_bak_label}</b></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background:#8b1a1a;border-radius:6px;padding:5px 10px;font-size:0.72rem;color:#e8e0d0;margin-top:4px'>💾 Sin copias en Sheets</div>", unsafe_allow_html=True)
    if _github_backup_configured():
        _lbd_gh = _last_github_backup_date()
        if _lbd_gh:
            _dias_gh = (date.today() - _lbd_gh).days
            _gh_color = "#1a3a6b" if _dias_gh==0 else "#b8860b" if _dias_gh<=3 else "#8b1a1a"
            _gh_label = "hoy" if _dias_gh==0 else f"hace {_dias_gh}d"
            st.markdown(f"<div style='background:{_gh_color};border-radius:6px;padding:5px 10px;font-size:0.72rem;color:#e8e0d0;margin-top:3px'>🐙 GitHub: <b>{_gh_label}</b></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='background:#8b1a1a;border-radius:6px;padding:5px 10px;font-size:0.72rem;color:#e8e0d0;margin-top:3px'>🐙 GitHub: sin copias</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    app_url = st.secrets.get("app_url","https://nauticrm-trn2jrtqldn9vfd4zic6hz.streamlit.app")
    st.markdown(f"<a href='{app_url}/?modo=feria' target='_blank' style='background:#c9a84c;color:#0a1628;padding:8px 14px;border-radius:6px;font-weight:700;font-size:0.8rem;text-decoration:none'>📱 Abrir modo Feria</a>", unsafe_allow_html=True)

leads = all_leads_raw
if my_portfolio: leads=[l for l in leads if l["asignadoA"]==active_user]

# ══ KANBAN ════════════════════════════════════════════════════════════════════
if "Kanban" in page:
    # ── Motivo de cierre / pausa pendiente ────────────────────────────────────
    if st.session_state.get("pending_causa"):
        _pc=st.session_state["pending_causa"]
        _es_perdido=_pc["etapa"]=="Cerrado Perdido"
        st.warning(f"{'❌ Cierre como perdido' if _es_perdido else '⏸️ Pasar a pausa'}: **{_pc['nombre']}**")
        _causa_k=st.text_area("¿Cuál es el motivo?" + (" (precio, competencia, sin presupuesto...)" if _es_perdido else " (aplaza decisión, fuera de temporada...)"),
                               key="causa_k_input", height=90)
        _kc1,_kc2=st.columns(2)
        if _kc1.button("✅ Confirmar y guardar", use_container_width=True, key="causa_k_ok"):
            _lead_pc=_pc["lead"]
            _hist_pc=_lead_pc.get("historial",[]).copy()
            if _pc.get("etapa_anterior") and _pc["etapa_anterior"]!=_pc["etapa"]:
                _hist_pc.append({"fecha":str(date.today()),"tipo":"Cambio etapa","nota":f"{_pc['etapa_anterior']} → {_pc['etapa']}"})
            _tipo_pc="Cierre perdido" if _es_perdido else "Pausa"
            _hist_pc.append({"fecha":str(date.today()),"tipo":_tipo_pc,"nota":_causa_k.strip() or "Sin motivo indicado"})
            _lead_pc["historial"]=_hist_pc
            save_lead(_lead_pc,is_new=False)
            st.session_state["pending_causa"]=None
            st.rerun()
        if _kc2.button("↩ Cancelar", use_container_width=True, key="causa_k_cancel"):
            st.session_state["pending_causa"]=None
            st.rerun()
        st.stop()

    st.markdown("## ⊞ Funnel de Ventas")
    st.markdown("<br>", unsafe_allow_html=True)
    funnel_leads=[l for l in leads if l["etapa"] in FUNNEL_STAGES]
    cols=st.columns(len(FUNNEL_STAGES))
    for col,stage in zip(cols,FUNNEL_STAGES):
        cards=[l for l in funnel_leads if l["etapa"]==stage]
        total=sum(l.get("valorOperacion",0) for l in cards)
        color=STAGE_COLORS[stage]
        with col:
            st.markdown(f"""<div style="background:{color};border-radius:6px 6px 0 0;padding:5px 10px;display:flex;justify-content:space-between;align-items:center">
                <span style="color:white;font-size:0.6rem;font-weight:700;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:75%">{stage}</span>
                <span style="background:rgba(0,0,0,0.35);color:white;border-radius:10px;padding:1px 8px;font-size:0.85rem;font-weight:700;flex-shrink:0">{len(cards)}</span>
            </div><div style="background:#091220;border-radius:0 0 6px 6px;padding:5px;min-height:80px">
            {"<div style='text-align:center;padding:4px 2px 6px;font-family:monospace;font-size:1rem;font-weight:700;color:#c9a84c'>"+fmt_eur(total)+"</div>" if total>0 else ""}""", unsafe_allow_html=True)
            for l in cards:
                d=days_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))
                btn_label=f"{urg_emoji(l.get('fechaProximaAccion'))} {l['nombre']}|{l.get('modeloEslora') or l['tipoEmbarcacion']}|{fmt_eur(l.get('valorOperacion',0))} · {l['asignadoA'].replace('Vendedor','V.')} · {d}d"
                st.markdown(f"""<style>
                div[data-testid="stButton"] button[kind="secondary"]{{
                    background:#0d1e35!important;border:1px solid #1a3050!important;
                    border-left:3px solid {color}!important;border-radius:6px!important;
                    padding:7px 9px!important;margin:2px 0!important;width:100%!important;
                    text-align:left!important;color:#e8e0d0!important;font-size:0.72rem!important;
                    white-space:normal!important;line-height:1.4!important;
                }}
                div[data-testid="stButton"] button[kind="secondary"]:hover{{
                    background:#1a3050!important;border-color:{color}!important;
                }}
                </style>""", unsafe_allow_html=True)
                if st.button(btn_label, key=f"kb_{l['id']}"):
                    st.session_state["goto_lead"] = l["id"]; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚡ Cambio rápido de estado"):
        c1,c2,c3=st.columns(3)
        _leads_k_sorted=[l for l in sorted(all_leads_raw,key=lambda l:max(l.get("ultimaActualizacion","") or "",l.get("fechaCreacion","") or ""),reverse=True) if l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido"]]
        _leads_k_dict={_lead_display(l):l for l in _leads_k_sorted}
        sel_k=c1.selectbox("Lead",["— Selecciona —"]+list(_leads_k_dict.keys()),key="sel_k")
        nueva_etapa=c2.selectbox("Nueva etapa",STAGES,key="etapa_k")
        if c3.button("✅ Cambiar"):
            if sel_k!="— Selecciona —":
                lead_upd=_leads_k_dict[sel_k]
                _etapa_ant_k=lead_upd.get("etapa","")
                lead_upd["etapa"]=nueva_etapa; lead_upd["ultimaActualizacion"]=str(date.today())
                _nombre_k=lead_upd.get("nombre","")
                if nueva_etapa in ["Cerrado Perdido","En Pausa / Recuperable"]:
                    st.session_state["pending_causa"]={"lead":lead_upd,"nombre":_nombre_k,"etapa":nueva_etapa,"etapa_anterior":_etapa_ant_k}
                else:
                    save_lead(con_cambio_etapa(lead_upd,_etapa_ant_k), is_new=False)
                    st.success(f"✅ {_nombre_k} → {nueva_etapa}")
                st.rerun()

    st.markdown("<div style='margin:8px 0 16px;padding:8px 14px;background:#0d1e35;border:1px solid #1a3050;border-radius:8px;font-size:0.78rem;color:#7a8fa6'>🔴 Vencida &nbsp;|&nbsp; 🟡 Hoy &nbsp;|&nbsp; 🟢 Futura &nbsp;|&nbsp; ⚪ Sin fecha asignada</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#1a3050'>", unsafe_allow_html=True)
    bc1,bc2,bc3=st.columns(3)
    for col,stage in zip([bc1,bc2,bc3],["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]):
        # Excluir cerrados/pausa con más de 13 meses sin actividad
        cards=[l for l in all_leads_raw if l["etapa"]==stage and months_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))<=13]
        total=sum(l.get("valorOperacion",0) for l in cards)
        color=STAGE_COLORS[stage]
        icon="✅" if stage=="Cerrado Ganado" else ("❌" if stage=="Cerrado Perdido" else "⏸️")
        with col:
            st.markdown(f"""<div style="background:{color};border-radius:6px 6px 0 0;padding:5px 12px;display:flex;justify-content:space-between;align-items:center">
                <span style="color:white;font-size:0.65rem;font-weight:700;text-transform:uppercase">{icon} {stage}</span>
                <span style="background:rgba(0,0,0,0.3);color:white;border-radius:10px;padding:0 6px;font-size:0.85rem;font-weight:700">{len(cards)}</span>
            </div><div style="background:#091220;border-radius:0 0 6px 6px;padding:5px;min-height:80px">
            {"<div style='text-align:center;padding:4px 2px 6px;font-family:monospace;font-size:1rem;font-weight:700;color:#c9a84c'>"+fmt_eur(total)+"</div>" if total>0 else ""}""", unsafe_allow_html=True)
            for l in cards[:5]:
                st.markdown(f"""<div style="background:#0d1e35;border:1px solid #1a3050;border-left:3px solid {color};border-radius:5px;padding:5px 8px;margin:3px 0;font-size:0.7rem">
                    <div style="font-weight:600;color:#e8e0d0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_html.escape(l['nombre'])}</div>
                    <div style="color:#7a8fa6;font-size:0.62rem">{_html.escape(l['empresa'])}·{fmt_eur(l.get('valorOperacion',0))}</div></div>""", unsafe_allow_html=True)
            if len(cards)>5: st.markdown(f"<small style='color:#7a8fa6;padding:0 5px'>+{len(cards)-5} más</small>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ══ LISTA ══════════════════════════════════════════════════════════════════════
elif "Lista" in page:
    st.markdown("## ≡ Lista de Leads")
    c1,c2,c3,c4=st.columns(4)
    q=c1.text_input("🔍 Buscar",placeholder="Nombre, empresa...")
    fv=c2.selectbox("Vendedor",["Todos"]+vendedores)
    fe=c3.selectbox("Etapa",["Todas"]+STAGES)
    ft=c4.selectbox("Tipo",["Todos"]+boat_types)
    filtered=leads
    if q: filtered=[l for l in filtered if q.lower() in (l.get("nombre","")+" "+l.get("empresa","")+" "+l.get("modeloEslora","")).lower()]
    if fv!="Todos": filtered=[l for l in filtered if l["asignadoA"]==fv]
    if fe!="Todas": filtered=[l for l in filtered if l["etapa"]==fe]
    if ft!="Todos": filtered=[l for l in filtered if l["tipoEmbarcacion"]==ft]
    st.caption(f"{len(filtered)} leads")
    if not filtered: st.info("Sin resultados.")
    else:
        for l in filtered:
            c1,c2=st.columns([8,1])
            with c1:
                color=STAGE_COLORS.get(l["etapa"],"#1a3050")
                st.markdown(f"""<div style="background:#0d1e35;border:1px solid #1a3050;border-left:3px solid {color};border-radius:6px;padding:8px 12px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center">
                    <div><span style="color:#e8e0d0;font-weight:700;font-size:0.85rem">{urg_emoji(l.get('fechaProximaAccion'))} {_html.escape(l['nombre'])}</span>
                    <span style="background:{color};color:white;border-radius:10px;padding:1px 7px;font-size:0.62rem;font-weight:700;margin-left:8px">{_html.escape(l['etapa'])}</span>
                    <span style="color:#7a8fa6;font-size:0.72rem;margin-left:8px">{_html.escape(l.get('empresa',''))}</span></div>
                    <div style="text-align:right"><span style="color:#2ecc71;font-family:monospace;font-size:0.78rem;font-weight:700">{fmt_eur(l.get('valorOperacion',0))}</span>
                    <span style="color:#7a8fa6;font-size:0.7rem;margin-left:8px">{_html.escape(l.get('tipoEmbarcacion',''))} {_html.escape(l.get('modeloEslora',''))}</span></div>
                </div>""", unsafe_allow_html=True)
            with c2:
                if st.button("✏️", key=f"lst_{l['id']}", help="Ir a ficha"):
                    st.session_state["goto_lead"] = l["id"]; st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        rows_exp=[{"Urg":urg_emoji(l.get("fechaProximaAccion")),"Nombre":l["nombre"],"Empresa":l["empresa"],"Idioma":l.get("idioma","—"),"Embarcación":f"{l['tipoEmbarcacion']}·{l['modeloEslora']}","Etapa":l["etapa"],"Valor €":fmt_eur(l.get("valorOperacion",0)),"Prob%":f"{l.get('probabilidad',0)}%","Vendedor":l["asignadoA"],"Próx. Acción":l.get("fechaProximaAccion","—")} for l in filtered]
        import io as _io
        _buf_lista=_io.BytesIO()
        pd.DataFrame(rows_exp).to_excel(_buf_lista,index=False,engine="openpyxl")
        st.download_button("⬇️ Exportar Excel",data=_buf_lista.getvalue(),file_name="nauticrm_leads.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ══ INFORMES ══════════════════════════════════════════════════════════════════
elif "Informes" in page:
    st.markdown("## 📊 Informes y Análisis")
    # ── Cálculo de KPIs ───────────────────────────────────────────────────────
    _hoy      = date.today()
    _mes_ini  = _hoy.replace(day=1)
    _mes_ant  = (_mes_ini - timedelta(days=1)).replace(day=1)
    active    = [l for l in all_leads_raw if l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]]
    _ganados  = [l for l in all_leads_raw if l["etapa"] == "Cerrado Ganado"]
    _perdidos = [l for l in all_leads_raw if l["etapa"] == "Cerrado Perdido"]
    _pipeline = sum(l.get("valorOperacion",0) for l in active)
    _forecast = sum(l.get("valorOperacion",0)*l.get("probabilidad",0)/100 for l in all_leads_raw if l["etapa"] not in ["Cerrado Perdido","En Pausa / Recuperable"])
    _revenue  = sum(l.get("valorOperacion",0) for l in _ganados)
    _n_gan    = len(_ganados); _n_per = len(_perdidos)
    _conv     = _n_gan/(_n_gan+_n_per)*100 if (_n_gan+_n_per)>0 else 0
    _ticket   = _revenue//_n_gan if _n_gan>0 else 0
    _propuestas = len([l for l in all_leads_raw if l["etapa"] in ["Propuesta Enviada","Negociación"]])
    _pendientes = len([l for l in active if l.get("proximaAccion","").strip()])
    _vencidas   = len([l for l in active if l.get("fechaProximaAccion") and
                       days_since(l["fechaProximaAccion"]) > 0])
    _sin_act    = [l for l in active if days_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))>7]
    # Variación mes actual vs mes anterior
    _act_este_mes  = len([l for l in active if (l.get("fechaCreacion","") or "") >= str(_mes_ini)])
    _act_mes_ant   = len([l for l in active if str(_mes_ant) <= (l.get("fechaCreacion","") or "") < str(_mes_ini)])
    _var_act = f"↗ +{_act_este_mes} nuevos este mes" if _act_este_mes else "Sin altas este mes"
    _gan_mes  = len([l for l in _ganados if (l.get("ultimaActualizacion","") or "") >= str(_mes_ini)])

    def _kpi_card(titulo, valor, subtitulo, icono, color_icono, color_sub="#2ecc71"):
        return f"""<div style="background:#0d1e35;border:1px solid #1a3050;border-radius:12px;
            padding:18px 20px;position:relative;min-height:96px;height:100%">
          <div style="font-size:0.68rem;color:#7a8fa6;text-transform:uppercase;
              letter-spacing:1px;margin-bottom:6px;padding-right:44px">{titulo}</div>
          <div style="font-size:1.75rem;font-weight:700;color:#e8e0d0;line-height:1.1;
              font-family:'Playfair Display',serif">{valor}</div>
          <div style="font-size:0.72rem;color:{color_sub};margin-top:7px">{subtitulo}</div>
          <div style="position:absolute;top:16px;right:16px;background:{color_icono};
              border-radius:9px;width:38px;height:38px;display:flex;align-items:center;
              justify-content:center;font-size:18px">{icono}</div>
        </div>"""

    _r1c = st.columns(4)
    _r1c[0].markdown(_kpi_card("Leads Activos", len(active), _var_act, "👥", "#2563eb"), unsafe_allow_html=True)
    _r1c[1].markdown(_kpi_card("Oportunidades Abiertas", len([l for l in active if l["etapa"] in ["Prospecto","Contactado","Interés Confirmado"]]),
        f"↗ {len([l for l in active if l['etapa']=='Prospecto'])} prospectos nuevos", "🎯", "#7c3aed"), unsafe_allow_html=True)
    _r1c[2].markdown(_kpi_card("Propuestas Activas", _propuestas,
        f"↗ {len([l for l in all_leads_raw if l['etapa']=='Propuesta Enviada'])} enviadas · {len([l for l in all_leads_raw if l['etapa']=='Negociación'])} en negociación",
        "📄", "#ea580c"), unsafe_allow_html=True)
    _r1c[3].markdown(_kpi_card("Acciones Pendientes", _pendientes,
        f"🔴 {_vencidas} vencidas" if _vencidas else "✅ Sin vencidas", "✅", "#16a34a",
        color_sub="#e74c3c" if _vencidas else "#2ecc71"), unsafe_allow_html=True)
    st.markdown("<div style='margin:10px 0'></div>", unsafe_allow_html=True)
    _r2c = st.columns(4)
    _r2c[0].markdown(_kpi_card("Ventas Cerradas", fmt_eur(_revenue),
        f"↗ {_gan_mes} cierre{'s' if _gan_mes!=1 else ''} este mes · {_n_gan} total", "💰", "#16a34a"), unsafe_allow_html=True)
    _r2c[1].markdown(_kpi_card("Tasa de Conversión", f"{_conv:.1f}%",
        f"{_n_gan} ganados · {_n_per} perdidos", "📈", "#e74c3c"), unsafe_allow_html=True)
    _r2c[2].markdown(_kpi_card("Pipeline Activo", fmt_eur(_pipeline),
        f"Forecast ponderado: {fmt_eur(int(_forecast))}", "🏷️", "#b8860b"), unsafe_allow_html=True)
    _r2c[3].markdown(_kpi_card("Ticket Medio", fmt_eur(_ticket),
        f"Sobre {_n_gan} venta{'s' if _n_gan!=1 else ''} cerrada{'s' if _n_gan!=1 else ''}", "🎫", "#7c3aed"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    tab1,tab2,tab3,tab4=st.tabs(["🔻 Embudo","📊 Pipeline & Fuentes","🤖 Informe IA","📖 Diario"])
    with tab1:
        st.markdown("#### Embudo de Ventas")
        # Todas las etapas: funnel normal + cerrados/pausa con <13 meses
        ALL_FUNNEL = ["Prospecto","Contactado","Interés Confirmado","Propuesta Enviada","Negociación","Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]
        def en_funnel(l):
            if l["etapa"] in FUNNEL_STAGES: return True
            if l["etapa"] in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]:
                return months_since(l.get("ultimaActualizacion") or l.get("fechaCreacion","")) <= 13
            return False
        leads_funnel = [l for l in all_leads_raw if en_funnel(l)]
        fd=[{"Etapa":s,"Leads":len([l for l in leads_funnel if l["etapa"]==s]),"Valor":sum(l.get("valorOperacion",0) for l in leads_funnel if l["etapa"]==s),"Color":STAGE_COLORS[s]} for s in ALL_FUNNEL]
        fd=[d for d in fd if d["Leads"]>0 or d["Valor"]>0]
        if not fd:
            st.info("Sin datos de pipeline todavía.")
        else:
            # ── Embudo SVG de forma fija ──────────────────────────────────────
            fd_f = [d for d in fd if d["Etapa"] in FUNNEL_STAGES]
            if fd_f:
                _n_ref  = fd_f[0]["Leads"] if fd_f[0]["Leads"] > 0 else 1
                _n      = len(fd_f)
                _W      = 520          # ancho total del SVG
                _SH     = 80           # alto de cada franja
                _W_TOP  = 500          # ancho máximo (franja superior)
                _W_BOT  = 160          # ancho mínimo (franja inferior)
                _cx     = _W / 2
                _total_h = _n * _SH + 20
                _svgparts = [
                    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {_total_h}" '
                    f'style="display:block;margin:0 auto;max-width:540px">'
                ]
                for _i, _d in enumerate(fd_f):
                    _wt = _W_TOP - _i * (_W_TOP - _W_BOT) / max(_n - 1, 1)
                    _wb = _W_TOP - (_i + 1) * (_W_TOP - _W_BOT) / max(_n - 1, 1)
                    _yt = _i * _SH
                    _yb = (_i + 1) * _SH
                    _xl_t = _cx - _wt / 2; _xr_t = _cx + _wt / 2
                    _xl_b = _cx - _wb / 2; _xr_b = _cx + _wb / 2
                    _pts  = f"{_xl_t:.1f},{_yt} {_xr_t:.1f},{_yt} {_xr_b:.1f},{_yb} {_xl_b:.1f},{_yb}"
                    _col  = _d["Color"]
                    _pct  = _d["Leads"] / _n_ref * 100
                    _val  = fmt_eur(_d["Valor"])
                    _conv = ""
                    if _i > 0 and fd_f[_i-1]["Leads"] > 0:
                        _conv = f"  · ↓{_d['Leads']/fd_f[_i-1]['Leads']*100:.0f}%"
                    _yc   = _yt + _SH / 2
                    _svgparts += [
                        f'<polygon points="{_pts}" fill="{_col}" stroke="#060e1a" stroke-width="1.5"/>',
                        f'<text x="{_cx}" y="{_yc-20:.1f}" text-anchor="middle" '
                        f'font-family="Inter,Arial,sans-serif" font-size="13" font-weight="700" fill="white">'
                        f'{_html.escape(_d["Etapa"])}</text>',
                        f'<text x="{_cx}" y="{_yc+2:.1f}" text-anchor="middle" '
                        f'font-family="Inter,Arial,sans-serif" font-size="12" fill="rgba(255,255,255,0.9)">'
                        f'{_d["Leads"]} ({_pct:.1f}%){_conv}</text>',
                        f'<text x="{_cx}" y="{_yc+20:.1f}" text-anchor="middle" '
                        f'font-family="Inter,Arial,sans-serif" font-size="12" font-weight="600" fill="#f0d060">'
                        f'{_val}</text>',
                    ]
                _svgparts.append("</svg>")
                _col_svg, _ = st.columns([2, 1])
                with _col_svg:
                    st.markdown("".join(_svgparts), unsafe_allow_html=True)
            _filas_f="".join(f"""<tr>
                <td style='padding:8px 14px;color:#e8e0d0;font-size:0.83rem;border-bottom:1px solid #1a3050'>
                  <span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:{d["Color"]};margin-right:8px;vertical-align:middle'></span>{d["Etapa"]}
                </td>
                <td style='padding:8px 14px;text-align:center;color:#c9a84c;font-weight:700;font-size:0.9rem;border-bottom:1px solid #1a3050'>{d["Leads"]}</td>
                <td style='padding:8px 14px;text-align:center;color:#2ecc71;font-family:monospace;font-size:0.85rem;border-bottom:1px solid #1a3050'>{fmt_eur(d["Valor"])}</td>
                <td style='padding:8px 14px;text-align:center;color:#7a8fa6;font-family:monospace;font-size:0.85rem;border-bottom:1px solid #1a3050'>{fmt_eur(d["Valor"]//d["Leads"]) if d["Leads"]>0 else "—"}</td>
            </tr>""" for d in fd)
            st.markdown(f"""<table style='width:100%;border-collapse:collapse;background:#091220;border-radius:8px;overflow:hidden;margin-top:8px'>
                <thead><tr style='background:#0d1e35'>
                  <th style='padding:9px 14px;text-align:left;color:#7a8fa6;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px'>Etapa</th>
                  <th style='padding:9px 14px;text-align:center;color:#7a8fa6;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px'>Leads</th>
                  <th style='padding:9px 14px;text-align:center;color:#7a8fa6;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px'>Valor Pipeline</th>
                  <th style='padding:9px 14px;text-align:center;color:#7a8fa6;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px'>Ticket Medio</th>
                </tr></thead>
                <tbody>{_filas_f}</tbody>
            </table>""", unsafe_allow_html=True)
    with tab2:
        c1,c2=st.columns(2)
        with c1:
            st.markdown("#### Pipeline por Vendedor")
            pv={v:sum(l.get("valorOperacion",0) for l in active if l["asignadoA"]==v) for v in vendedores}
            df_pv=pd.DataFrame({"Vendedor":list(pv.keys()),"Valor":list(pv.values())})
            fig=px.bar(df_pv,x="Vendedor",y="Valor",color_discrete_sequence=["#c9a84c"],text=df_pv["Valor"].apply(fmt_eur))
            fig.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="#e8e0d0",showlegend=False,xaxis=dict(gridcolor="#1a3050"),yaxis=dict(gridcolor="#1a3050"),margin=dict(t=20,b=10,l=10,r=10))
            fig.update_traces(textposition="outside",textfont_color="white"); st.plotly_chart(fig,use_container_width=True)
        with c2:
            st.markdown("#### Leads por Fuente")
            src={}
            for l in all_leads_raw: src[l.get("fuenteLead","Otro")]=src.get(l.get("fuenteLead","Otro"),0)+1
            fig2=px.pie(pd.DataFrame({"Fuente":list(src.keys()),"N":list(src.values())}),names="Fuente",values="N",hole=0.52,color_discrete_sequence=["#c9a84c","#2563eb","#7c3aed","#ea580c","#16a34a","#dc2626"])
            fig2.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="white",margin=dict(t=20,b=10,l=10,r=10),legend=dict(font=dict(color="white")))
            fig2.update_traces(textfont_color="white",textfont_size=13)
            st.plotly_chart(fig2,use_container_width=True)
        st.markdown("#### Leads por Idioma")
        ic={}
        for l in all_leads_raw: ic[l.get("idioma","—")]=ic.get(l.get("idioma","—"),0)+1
        df_id=pd.DataFrame({"Idioma":list(ic.keys()),"Leads":list(ic.values())}).sort_values("Leads",ascending=False)
        fig3=px.bar(df_id,x="Idioma",y="Leads",color_discrete_sequence=["#2563eb"],text="Leads")
        fig3.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="#e8e0d0",showlegend=False,xaxis=dict(gridcolor="#1a3050"),yaxis=dict(gridcolor="#1a3050"),margin=dict(t=10,b=10,l=10,r=10),height=220)
        fig3.update_traces(textposition="outside",textfont_color="white"); st.plotly_chart(fig3,use_container_width=True)
    with tab3:
        st.markdown("#### 🤖 Informe IA — Análisis y Patrones")
        st.markdown("<div style='color:#7a8fa6;font-size:0.82rem;margin-bottom:16px'>Claude analiza todos los datos del CRM y detecta patrones, tendencias y oportunidades de mejora.</div>",unsafe_allow_html=True)

        # ── Filtro de período ─────────────────────────────────────────────────
        _ia1,_ia2,_ia3=st.columns(3)
        _periodo=_ia1.selectbox("Período",["Todo","Este año","Este trimestre","Este mes","Fechas personalizadas"],key="ia_periodo")
        _hoy=date.today()
        if _periodo=="Este mes":
            _d_ini=_hoy.replace(day=1); _d_fin=_hoy
        elif _periodo=="Este trimestre":
            _q=(_hoy.month-1)//3; _d_ini=date(_hoy.year,_q*3+1,1); _d_fin=_hoy
        elif _periodo=="Este año":
            _d_ini=date(_hoy.year,1,1); _d_fin=_hoy
        elif _periodo=="Fechas personalizadas":
            _d_ini=_ia2.date_input("Desde",value=date(_hoy.year,1,1),key="ia_desde")
            _d_fin=_ia3.date_input("Hasta",value=_hoy,key="ia_hasta")
        else:
            _d_ini=None; _d_fin=None

        def _en_periodo(l):
            if not _d_ini: return True
            try: return _d_ini<=datetime.strptime(str(l.get("fechaCreacion","")),"%Y-%m-%d").date()<=_d_fin
            except: return False

        _leads_ia=[l for l in all_leads_raw if _en_periodo(l)]
        _arch_ia=[l for l in archivo_frio if not _d_ini or (lambda d: _d_ini<=d<=_d_fin if d else False)(
            (lambda s: datetime.strptime(s,"%Y-%m-%d").date() if s else None)(l.get("fechaArchivo","")))]

        st.caption(f"{len(_leads_ia)} leads activos + {len(_arch_ia)} en archivo frío en el período seleccionado")

        if st.button("🤖 Generar informe IA",use_container_width=True):
            # ── Preparar resumen de datos ─────────────────────────────────────
            _todos=_leads_ia+_arch_ia
            _por_etapa={s:len([l for l in _leads_ia if l["etapa"]==s]) for s in STAGES}
            _por_tipo={}
            for l in _todos:
                t=l.get("tipoEmbarcacion","—"); _por_tipo[t]=_por_tipo.get(t,0)+1
            _por_fuente={}
            for l in _todos:
                f=l.get("fuenteLead","—"); _por_fuente[f]=_por_fuente.get(f,0)+1
            _por_idioma={}
            for l in _todos:
                i=l.get("idioma","—"); _por_idioma[i]=_por_idioma.get(i,0)+1
            _actividad=[]
            for l in _leads_ia:
                for h in l.get("historial",[]):
                    _actividad.append({"lead":l["nombre"],"fecha":h["fecha"],"tipo":h["tipo"],"nota":h["nota"][:300]})
            _actividad.sort(key=lambda x:x["fecha"],reverse=True)
            _act_por_tipo={}
            for a in _actividad:
                _act_por_tipo[a["tipo"]]=_act_por_tipo.get(a["tipo"],0)+1
            # Actividad por mes
            _act_por_mes={}
            for a in _actividad:
                try: _mes=a["fecha"][:7]
                except: _mes="—"
                _act_por_mes[_mes]=_act_por_mes.get(_mes,0)+1
            # Altas por mes
            _altas_por_mes={}
            for l in _leads_ia:
                try: _mes=l.get("fechaCreacion","")[:7]
                except: _mes="—"
                if _mes: _altas_por_mes[_mes]=_altas_por_mes.get(_mes,0)+1
            def _prox_futura(l):
                try: return datetime.strptime(str(l.get("fechaProximaAccion","")),"%Y-%m-%d").date()>=date.today()
                except: return False
            # Sin actividad: sin historial Y sin próxima acción planificada Y alta hace más de 14 días
            _sin_actividad=[l["nombre"] for l in _leads_ia
                if not l.get("historial") and not l.get("proximaAccion") and not _prox_futura(l)
                and days_since(l.get("fechaCreacion",""))>14
                and l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido"]]
            # Estancados: sin movimiento +30 días Y sin próxima acción futura planificada
            _estancados=[l["nombre"] for l in _leads_ia
                if days_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))>30
                and not _prox_futura(l)
                and l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]]
            _pipeline_activo=sum(l.get("valorOperacion",0) for l in _leads_ia if l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"])
            _valor_ganado=sum(l.get("valorOperacion",0) for l in _leads_ia if l["etapa"]=="Cerrado Ganado")
            _valor_perdido=sum(l.get("valorOperacion",0) for l in _leads_ia if l["etapa"]=="Cerrado Perdido")
            # Progresión de etapas — conteo de transiciones desde el historial
            _progresion={}
            for l in _leads_ia+_arch_ia:
                for h in l.get("historial",[]):
                    if h.get("tipo")=="Cambio etapa" and " → " in h.get("nota",""):
                        k=h["nota"].strip(); _progresion[k]=_progresion.get(k,0)+1
            # Historial completo de leads cerrados (ganado + perdido)
            _cerrados_hist=[]
            for l in _leads_ia:
                if l["etapa"] in ["Cerrado Ganado","Cerrado Perdido"]:
                    _h_lines=" | ".join(f"[{h['fecha']}] {h['tipo']}: {h['nota'][:150]}" for h in l.get("historial",[]))
                    _cerrados_hist.append(
                        f"- {l['nombre']} ({l['etapa']}) | €{l.get('valorOperacion',0)} | "
                        f"alta:{l.get('fechaCreacion','')} | cierre:{l.get('ultimaActualizacion','')} | "
                        + (_h_lines or "sin historial")
                    )
            # Leads en pausa — motivo registrado
            _pausa_hist=[]
            for l in _leads_ia:
                if l["etapa"]=="En Pausa / Recuperable":
                    _motivo_p=next((h["nota"][:200] for h in reversed(l.get("historial",[])) if h.get("tipo")=="Pausa"),"sin motivo registrado")
                    _pausa_hist.append(f"- {l['nombre']} | desde:{l.get('ultimaActualizacion','')} | motivo: {_motivo_p}")
            # Archivo frío — motivos de archivo
            _arch_motivos=[
                f"- {l.get('nombre','')} | archivado:{l.get('fechaArchivo','')} | motivo: {l.get('motivoArchivo','—')[:200]}"
                for l in _arch_ia[:25]
            ]

            _prompt=f"""Eres un consultor experto en ventas náuticas analizando los datos del CRM de Náutica Viamar, una empresa especializada en embarcaciones de recreo.

PERÍODO ANALIZADO: {"Todo el histórico" if not _d_ini else f"{_d_ini} a {_d_fin}"}

## DATOS DEL CRM

### Resumen general
- Total leads en período: {len(_leads_ia)} activos + {len(_arch_ia)} en archivo frío
- Pipeline activo: €{_pipeline_activo:,}
- Valor cerrado ganado: €{_valor_ganado:,}
- Valor cerrado perdido: €{_valor_perdido:,}
- Tasa de conversión: {round(len([l for l in _leads_ia if l['etapa']=='Cerrado Ganado'])/max(len(_leads_ia),1)*100,1)}%

### Leads por etapa
{chr(10).join(f"- {k}: {v}" for k,v in _por_etapa.items() if v>0)}

### Leads por tipo de embarcación
{chr(10).join(f"- {k}: {v}" for k,v in sorted(_por_tipo.items(),key=lambda x:-x[1]))}

### Leads por fuente de captación
{chr(10).join(f"- {k}: {v}" for k,v in sorted(_por_fuente.items(),key=lambda x:-x[1]))}

### Leads por idioma
{chr(10).join(f"- {k}: {v}" for k,v in sorted(_por_idioma.items(),key=lambda x:-x[1]))}

### Actividad registrada ({len(_actividad)} interacciones)
Por tipo: {', '.join(f"{k}: {v}" for k,v in _act_por_tipo.items())}
Por mes: {', '.join(f"{k}: {v}" for k,v in sorted(_act_por_mes.items()))}

### Altas de nuevos leads por mes
{', '.join(f"{k}: {v}" for k,v in sorted(_altas_por_mes.items()))}

### Progresión de etapas (transiciones registradas en historial)
{chr(10).join(f"- {k}: {v} veces" for k,v in sorted(_progresion.items(),key=lambda x:-x[1])) or "- Sin datos de cambios de etapa registrados"}

### Tiempos de ciclo de venta (calculados desde historial)
{(lambda _tiempos: chr(10).join(f"- {n}: {v}" for n,v in _tiempos.items()) if _tiempos else "- Sin datos suficientes aún")(dict(filter(lambda kv: kv[1] is not None, {
    "Días promedio desde Alta hasta primera interacción": (lambda vals: round(sum(vals)/len(vals)) if vals else None)(
        [v for v in [(lambda h,fc: (datetime.strptime(h[0]["fecha"],"%Y-%m-%d")-datetime.strptime(fc,"%Y-%m-%d")).days
            if h and fc else None)(
            sorted([x for x in l.get("historial",[]) if x["tipo"] not in ["Cambio etapa"]],key=lambda x:x["fecha"]),
            l.get("fechaCreacion",""))
         for l in _leads_ia] if v is not None and v>=0]),
    "Días promedio hasta enviar propuesta (leads con ese cambio)": (lambda vals: round(sum(vals)/len(vals)) if vals else None)(
        [v for v in [(lambda h,fc: (datetime.strptime(next((x["fecha"] for x in h if "Propuesta" in x.get("nota","")),None) or "","%Y-%m-%d")-datetime.strptime(fc,"%Y-%m-%d")).days
            if next((x for x in h if "Propuesta" in x.get("nota","")),None) and fc else None)(
            l.get("historial",[]),l.get("fechaCreacion",""))
         for l in _leads_ia] if v is not None and v>=0]),
}.items())))}


### Leads activos — detalle (etapa, alta, días en etapa actual, próxima acción)
{chr(10).join((lambda _dias_etapa, _pf: f"- {l['nombre']} | {l['etapa']} | alta:{l.get('fechaCreacion','?')} | días_en_etapa:{_dias_etapa} | próx.acción:{l.get('proximaAccion','—')} ({l.get('fechaProximaAccion','sin fecha')}) | {'⚠️ sin plan' if not _pf and _dias_etapa>21 else '✅ con plan' if _pf else '🕐 reciente'}")(
    days_since(next((h["fecha"] for h in reversed(l.get("historial",[])) if h.get("tipo")=="Cambio etapa" and l["etapa"] in h.get("nota","")), l.get("ultimaActualizacion") or l.get("fechaCreacion",""))),
    (lambda s: (lambda d: d>=date.today())(datetime.strptime(s,"%Y-%m-%d").date()) if s else False)(l.get("fechaProximaAccion","")))
    for l in _leads_ia if l['etapa'] not in ['Cerrado Ganado','Cerrado Perdido','En Pausa / Recuperable'])[:60]}

### Leads cerrados — historial completo ({len(_cerrados_hist)} leads)
{chr(10).join(_cerrados_hist) or "- Sin leads cerrados en el período"}

### Leads en pausa / recuperable — motivos ({len(_pausa_hist)} leads)
{chr(10).join(_pausa_hist) or "- Sin leads en pausa"}

### Archivo frío — motivos de archivo ({len(_arch_ia)} leads, mostrando {min(len(_arch_ia),25)})
{chr(10).join(_arch_motivos) or "- Archivo vacío"}

### Alertas
- Leads sin actividad ni plan (alta >14 días, sin historial y sin próxima acción) ({len(_sin_actividad)}): {', '.join(_sin_actividad[:10])}{'...' if len(_sin_actividad)>10 else ''}
- Leads estancados +30 días sin movimiento ni acción futura planificada ({len(_estancados)}): {', '.join(_estancados[:10])}{'...' if len(_estancados)>10 else ''}

### Actividad reciente (últimas 30 interacciones con notas completas)
{chr(10).join(f"- [{a['fecha']}] {a['lead']} | {a['tipo']}: {a['nota']}" for a in _actividad[:30])}

## INSTRUCCIONES
Genera un informe completo en español con estas secciones:
1. **Resumen ejecutivo** (3-4 frases clave)
2. **Análisis de pipeline** (estado del embudo, conversión, valor en juego)
3. **Patrones detectados** (estacionalidad, tipos de cliente que cierran más, fuentes más rentables, idiomas relevantes, patrones en los motivos de cierre/pérdida/pausa)
4. **Velocidad de ventas** (usa la progresión de etapas y tiempos de ciclo: dónde se atascan los leads, cuánto tardan en avanzar, en qué transición se pierden más)
5. **Alertas y riesgos** (leads en riesgo, estancamientos, oportunidades perdidas, leads en pausa que conviene recuperar)
6. **Recomendaciones concretas** (mínimo 5 acciones específicas y prioritarias, apoyadas en datos reales del historial)

CONTEXTO DEL PROCESO DE VENTA DE NÁUTICA VIAMAR (aplícalo siempre al interpretar los datos):
El pipeline sigue este flujo específico:
1. PROSPECTO → fecha de entrada al CRM (primer contacto, habitualmente en feria o salón). Es el inicio del proceso.
2. CONTACTADO → se ha contactado para completar datos o confirmar interés. Puede durar días.
3. INTERÉS CONFIRMADO → el cliente ha confirmado interés, se está preparando la propuesta o esperando respuesta suya. Normal que dure 1-3 semanas.
4. PROPUESTA ENVIADA → se ha enviado el presupuesto/oferta. La fecha de entrada a esta etapa ES la fecha de envío de la propuesta. Es completamente normal que el cliente tarde días o semanas en responder; NO es estancamiento salvo que supere 30 días sin ningún movimiento ni plan de seguimiento.
5. NEGOCIACIÓN → el cliente no ha rechazado; se está negociando precio, condiciones, financiación. Puede durar semanas.
6. CERRADO GANADO / CERRADO PERDIDO → resolución final.
7. EN PAUSA / RECUPERABLE → cliente válido pero no está listo aún (tiene barco sin vender, espera liquidez, fuera de temporada, etc.). No es un lead perdido, es una oportunidad futura.

Reglas para las alertas:
- "Propuesta Enviada" con menos de 30 días en la etapa y/o con próxima acción futura planificada = proceso normal, NO alertar.
- "Interés Confirmado" o "Negociación" con próxima acción planificada = proceso activo, NO alertar.
- Solo alertar por estancamiento real: más de 30 días en cualquier etapa activa SIN ningún movimiento ni plan de seguimiento.
- "En Pausa / Recuperable" NO es un problema: es gestión proactiva de oportunidades diferidas.

IMPORTANTE: No analices ni desgloses por vendedor asignado salvo que se pregunte expresamente. El equipo trabaja de forma conjunta y los leads no tienen una asignación significativa por vendedor.

Sé directo, usa datos concretos del informe y enfócate en lo accionable. Formato markdown."""

            with st.spinner("🤖 Claude está analizando los datos..."):
                try:
                    import anthropic as _anthropic
                    _client=_anthropic.Anthropic(api_key=st.secrets["anthropic_api_key"])
                    # Separar contexto de datos (system, cacheable) de las instrucciones (user)
                    _split = _prompt.split("## INSTRUCCIONES", 1)
                    _sys_inf  = _split[0].strip()
                    _user_inf = ("## INSTRUCCIONES" + _split[1]) if len(_split) > 1 else _prompt
                    _msg=_client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=2000,
                        system=[{"type":"text","text":_sys_inf,"cache_control":{"type":"ephemeral"}}],
                        messages=[{"role":"user","content":_user_inf}]
                    )
                    _informe=_msg.content[0].text
                    st.markdown("---")
                    st.markdown(_informe)
                    st.markdown("---")
                    import io as _io_ia, re as _re

                    def _to_pdf(txt):
                        import os as _os
                        from reportlab.lib.pagesizes import A4
                        from reportlab.lib import colors as _rc
                        from reportlab.lib.units import cm
                        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as _RLImage, HRFlowable
                        from reportlab.lib.styles import ParagraphStyle
                        _buf=_io_ia.BytesIO()
                        _doc=SimpleDocTemplate(_buf,pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=2*cm,bottomMargin=2*cm)
                        _GOLD=_rc.HexColor("#C9A84C"); _BLUE=_rc.HexColor("#2563eb"); _DARK=_rc.HexColor("#111111")
                        _s_tit=ParagraphStyle("t",fontName="Helvetica-Bold",fontSize=17,textColor=_GOLD,spaceAfter=4)
                        _s_sub=ParagraphStyle("s",fontName="Helvetica",fontSize=9,textColor=_rc.HexColor("#555555"),spaceAfter=10)
                        _s_h1=ParagraphStyle("h1",fontName="Helvetica-Bold",fontSize=13,textColor=_GOLD,spaceBefore=14,spaceAfter=5)
                        _s_h2=ParagraphStyle("h2",fontName="Helvetica-Bold",fontSize=11,textColor=_BLUE,spaceBefore=10,spaceAfter=4)
                        _s_body=ParagraphStyle("b",fontName="Helvetica",fontSize=10,textColor=_DARK,spaceAfter=4,leading=14)
                        _s_bull=ParagraphStyle("bl",fontName="Helvetica",fontSize=10,textColor=_DARK,spaceAfter=3,leftIndent=14,leading=13)
                        _logo_path=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),"logo_viamar.jpg")
                        _elems=[]
                        if _os.path.exists(_logo_path):
                            try:
                                _img=_RLImage(_logo_path,width=5*cm,height=1.6*cm,kind="proportional")
                                _elems.append(_img)
                                _elems.append(Spacer(1,0.3*cm))
                            except Exception: pass
                        _elems+=[Paragraph("NautiCRM — Informe IA",_s_tit),
                                Paragraph(f"Generado: {date.today().strftime('%d/%m/%Y')}",_s_sub),
                                HRFlowable(width="100%",thickness=1,color=_GOLD,spaceAfter=10)]
                        for _ln in txt.split("\n"):
                            _ln=_ln.strip()
                            if not _ln: _elems.append(Spacer(1,0.18*cm)); continue
                            def _bold(_t): return _re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',_t)
                            if _ln.startswith("## "): _elems.append(Paragraph(_ln[3:],_s_h1))
                            elif _ln.startswith("### "): _elems.append(Paragraph(_ln[4:],_s_h2))
                            elif _ln.startswith(("- ","* ")): _elems.append(Paragraph("• "+_bold(_ln[2:]),_s_bull))
                            else: _elems.append(Paragraph(_bold(_ln),_s_body))
                        _doc.build(_elems)
                        return _buf.getvalue()

                    _fname=f"informe_ia_{date.today()}"
                    _dc1,_dc2=st.columns(2)
                    _dc1.download_button("⬇️ Descargar TXT",data=_informe.encode("utf-8"),file_name=f"{_fname}.txt",mime="text/plain",use_container_width=True)
                    try:
                        _dc2.download_button("⬇️ Descargar PDF",data=_to_pdf(_informe),file_name=f"{_fname}.pdf",mime="application/pdf",use_container_width=True)
                    except Exception as _ex3:
                        _dc2.warning(f"PDF no disponible: {_ex3}")
                except Exception as _e:
                    st.error(f"Error al generar el informe: {_e}")

    with tab4:
        st.markdown("#### 📖 Diario de actividad")
        _dcol1,_dcol2,_dcol3=st.columns([1,1,2])
        _diario_desde=_dcol1.date_input("Desde",value=date.today()-timedelta(days=30),key="diario_desde")
        _diario_hasta=_dcol2.date_input("Hasta",value=date.today(),key="diario_hasta")
        _TIPOS_DIARIO=["Alta","Cambio etapa","Email","Llamada","Reunión","WhatsApp","Nota","Cierre perdido","Pausa"]
        _TIPO_ICONO={"Alta":"🆕","Cambio etapa":"🔄","Email":"📧","Llamada":"📞","Reunión":"🤝","WhatsApp":"💬","Nota":"📝","Cierre perdido":"❌","Pausa":"⏸️"}
        _TIPO_COLOR={"Alta":"#16a34a","Cambio etapa":"#c9a84c","Email":"#2563eb","Llamada":"#0891b2",
                     "Reunión":"#7c3aed","WhatsApp":"#25d366","Nota":"#b8860b","Cierre perdido":"#dc2626","Pausa":"#6b7280"}
        _diario_filtro=_dcol3.multiselect("Filtrar por tipo",_TIPOS_DIARIO,default=[],key="diario_tipos",placeholder="Todos los tipos")
        # Construir eventos
        _eventos=[]
        for _l in all_leads_raw:
            if _l.get("fechaCreacion"):
                _desc=f"{_l.get('tipoEmbarcacion','')} {_l.get('modeloEslora','')}".strip()
                _desc=f"{_desc} · {_l.get('fuenteLead','')}" if _l.get('fuenteLead') else _desc
                _eventos.append({"fecha":_l["fechaCreacion"],"tipo":"Alta","lead":_l["nombre"],
                    "empresa":_l.get("empresa",""),"nota":_desc or "—","etapa":_l["etapa"]})
            for _h in _l.get("historial",[]):
                _eventos.append({"fecha":_h["fecha"],"tipo":_h["tipo"],"lead":_l["nombre"],
                    "empresa":_l.get("empresa",""),"nota":_h["nota"],"etapa":_l["etapa"]})
        _eventos=[e for e in _eventos
            if str(_diario_desde)<=e["fecha"]<=str(_diario_hasta)
            and (not _diario_filtro or e["tipo"] in _diario_filtro)]
        _eventos.sort(key=lambda e:e["fecha"],reverse=True)
        # Contadores resumen
        _res={}
        for _e in _eventos: _res[_e["tipo"]]=_res.get(_e["tipo"],0)+1
        if _res:
            _rcols=st.columns(min(len(_res),5))
            for _i,(_t,_n) in enumerate(sorted(_res.items(),key=lambda x:-x[1])[:5]):
                _rcols[_i].metric(f"{_TIPO_ICONO.get(_t,'•')} {_t}",_n)
        import html as _html_mod
        import streamlit.components.v1 as _comp_d
        def _render_diario(eventos, tipo_icono, tipo_color, d_desde, d_hasta):
            filas=""
            fecha_actual=None
            for ev in eventos:
                if ev["fecha"]!=fecha_actual:
                    fecha_actual=ev["fecha"]
                    try:
                        _dt=datetime.strptime(fecha_actual,"%Y-%m-%d")
                        _fmt=_dt.strftime("%A %d de %B de %Y").capitalize()
                    except: _fmt=fecha_actual
                    filas+=f"<tr><td colspan='4' class='dia'>{_fmt}</td></tr>"
                col=tipo_color.get(ev["tipo"],"#555")
                ico=tipo_icono.get(ev["tipo"],"·")
                lead=_html_mod.escape(ev["lead"])
                empresa=_html_mod.escape(ev.get("empresa",""))
                nota=_html_mod.escape(ev.get("nota",""))
                etapa=_html_mod.escape(ev.get("etapa",""))
                filas+=f"""<tr>
                  <td class="tipo-cell"><span class="badge" style="background:{col}">{ico} {_html_mod.escape(ev["tipo"])}</span></td>
                  <td class="lead-cell"><b>{lead}</b>{"<br><span class='emp'>"+empresa+"</span>" if empresa else ""}</td>
                  <td class="etapa-cell">{etapa}</td>
                  <td class="nota-cell">{nota}</td>
                </tr>"""
            if not filas:
                filas="<tr><td colspan='4' style='text-align:center;padding:32px;color:#888'>Sin eventos en el período seleccionado.</td></tr>"
            per=f"{d_desde.strftime('%d/%m/%Y')} — {d_hasta.strftime('%d/%m/%Y')}"
            return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body{{font-family:"Segoe UI",Arial,sans-serif;font-size:13px;color:#1a1a1a;background:#fff;padding:16px 20px;margin:0}}
  .btn-print{{background:#0d3b6e;color:#fff;border:none;border-radius:6px;padding:8px 20px;font-size:13px;font-weight:700;cursor:pointer;margin-bottom:16px}}
  .btn-print:hover{{background:#2563eb}}
  h2{{font-size:16px;color:#0d3b6e;margin:0 0 2px}} .per{{color:#888;font-size:12px;margin-bottom:14px}}
  table{{width:100%;border-collapse:collapse}}
  th{{background:#0d3b6e;color:#fff;padding:7px 10px;text-align:left;font-size:12px;font-weight:600}}
  td{{padding:7px 10px;border-bottom:1px solid #eee;vertical-align:top}}
  tr:hover td{{background:#f5f8ff}}
  td.dia{{background:#f0f4ff;color:#0d3b6e;font-weight:700;font-size:12px;padding:8px 10px;border-bottom:2px solid #c9a84c;text-transform:uppercase;letter-spacing:.5px}}
  .badge{{display:inline-block;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;white-space:nowrap}}
  .emp{{color:#888;font-size:11px}} .etapa-cell{{color:#555;font-size:12px;white-space:nowrap}} .nota-cell{{color:#333}}
  @media print{{.btn-print{{display:none}}body{{padding:6px}}}}
</style></head><body>
<button class="btn-print" onclick="window.print()">🖨️ Imprimir / Guardar PDF</button>
<h2>📖 Diario de actividad — Náutica Viamar</h2>
<div class="per">{per} · {len(eventos)} eventos</div>
<table>
  <thead><tr><th style="width:130px">Tipo</th><th style="width:200px">Lead</th><th style="width:160px">Etapa</th><th>Nota</th></tr></thead>
  <tbody>{filas}</tbody>
</table>
</body></html>"""
        _html_diario=_render_diario(_eventos,_TIPO_ICONO,_TIPO_COLOR,_diario_desde,_diario_hasta)
        _altura_d=min(2600, max(400, len(_eventos)*38+200))
        _comp_d.html(_html_diario, height=_altura_d, scrolling=True)

        if _eventos:
            def _diario_pdf(eventos, tipo_color, d_desde, d_hasta):
                import io as _io2
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors as _rc
                from reportlab.lib.units import cm
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib.styles import ParagraphStyle
                import html as _hm
                _buf=_io2.BytesIO()
                _doc=SimpleDocTemplate(_buf,pagesize=A4,leftMargin=1.8*cm,rightMargin=1.8*cm,topMargin=2*cm,bottomMargin=2*cm)
                _GOLD=_rc.HexColor("#C9A84C"); _BLUE=_rc.HexColor("#0d3b6e"); _DARK=_rc.HexColor("#111")
                _s_tit=ParagraphStyle("t",fontName="Helvetica-Bold",fontSize=15,textColor=_BLUE,spaceAfter=2)
                _s_sub=ParagraphStyle("s",fontName="Helvetica",fontSize=9,textColor=_rc.HexColor("#666"),spaceAfter=12)
                _s_cell=ParagraphStyle("c",fontName="Helvetica",fontSize=8,textColor=_DARK,leading=11)
                _s_bold=ParagraphStyle("b",fontName="Helvetica-Bold",fontSize=8,textColor=_DARK,leading=11)
                _s_dia=ParagraphStyle("d",fontName="Helvetica-Bold",fontSize=9,textColor=_BLUE)
                _elems=[Paragraph("Diario de actividad — Náutica Viamar",_s_tit),
                        Paragraph(f"{d_desde.strftime('%d/%m/%Y')} — {d_hasta.strftime('%d/%m/%Y')} · {len(eventos)} eventos",_s_sub)]
                _data=[["Tipo","Lead / Empresa","Etapa","Nota"]]
                _row_styles=[("BACKGROUND",(0,0),(-1,0),_BLUE),("TEXTCOLOR",(0,0),(-1,0),_rc.white),
                             ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),8),
                             ("ROWBACKGROUNDS",(0,1),(-1,-1),[_rc.white,_rc.HexColor("#f5f8ff")]),
                             ("GRID",(0,0),(-1,-1),0.3,_rc.HexColor("#dddddd")),
                             ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
                             ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]
                _fecha_prev=None; _row_idx=1
                for ev in eventos:
                    if ev["fecha"]!=_fecha_prev:
                        _fecha_prev=ev["fecha"]
                        try: _dfmt=datetime.strptime(ev["fecha"],"%Y-%m-%d").strftime("%A %d de %B de %Y").capitalize()
                        except: _dfmt=ev["fecha"]
                        _data.append([Paragraph(_dfmt,_s_dia),"","",""])
                        _row_styles+=[("SPAN",(0,_row_idx),(-1,_row_idx)),
                                      ("BACKGROUND",(0,_row_idx),(-1,_row_idx),_rc.HexColor("#e8eeff")),
                                      ("LINEBELOW",(0,_row_idx),(-1,_row_idx),1,_GOLD)]
                        _row_idx+=1
                    _col=_rc.HexColor(tipo_color.get(ev["tipo"],"#555555"))
                    _empresa=f"\n{ev['empresa']}" if ev.get("empresa") else ""
                    _data.append([Paragraph(ev["tipo"],ParagraphStyle("tp",fontName="Helvetica-Bold",fontSize=8,textColor=_rc.white,backColor=_col,leading=11,borderPadding=2)),
                                  Paragraph(f"<b>{_hm.escape(ev['lead'])}</b><font color='#888888' size='7'>{_hm.escape(_empresa)}</font>",_s_cell),
                                  Paragraph(_hm.escape(ev.get("etapa","")),_s_cell),
                                  Paragraph(_hm.escape(ev.get("nota","")),_s_cell)])
                    _row_idx+=1
                _t=Table(_data,colWidths=[3.2*cm,5*cm,4*cm,None])
                _t.setStyle(TableStyle(_row_styles))
                _elems.append(_t)
                _doc.build(_elems)
                return _buf.getvalue()
            try:
                _pdf_d=_diario_pdf(_eventos,_TIPO_COLOR,_diario_desde,_diario_hasta)
                st.download_button("⬇️ Exportar diario PDF",data=_pdf_d,
                    file_name=f"diario_{_diario_desde}_{_diario_hasta}.pdf",mime="application/pdf",use_container_width=True)
            except Exception as _epdf:
                st.warning(f"PDF no disponible: {_epdf}")

# ══ LEAD FORM ═════════════════════════════════════════════════════════════════
elif "Lead" in page:
    st.markdown("## ➕ Nuevo / Editar Lead")

    # ── Motivo de cierre / pausa pendiente ───────────────────────────────────
    if st.session_state.get("pending_causa"):
        _pc=st.session_state["pending_causa"]
        _es_perdido=_pc["etapa"]=="Cerrado Perdido"
        st.warning(f"{'❌ Cierre como perdido' if _es_perdido else '⏸️ Pasar a pausa'}: **{_pc['nombre']}**")
        _causa_f=st.text_area("¿Cuál es el motivo?" + (" (precio, competencia, sin presupuesto...)" if _es_perdido else " (aplaza decisión, fuera de temporada...)"),
                               key="causa_f_input", height=90)
        _fc1,_fc2=st.columns(2)
        if _fc1.button("✅ Confirmar y guardar", use_container_width=True, key="causa_f_ok"):
            _lead_pc=_pc["lead"]
            _hist_pc=_lead_pc.get("historial",[]).copy()
            if _pc.get("etapa_anterior") and _pc["etapa_anterior"]!=_pc["etapa"]:
                _hist_pc.append({"fecha":str(date.today()),"tipo":"Cambio etapa","nota":f"{_pc['etapa_anterior']} → {_pc['etapa']}"})
            _tipo_pc="Cierre perdido" if _es_perdido else "Pausa"
            _hist_pc.append({"fecha":str(date.today()),"tipo":_tipo_pc,"nota":_causa_f.strip() or "Sin motivo indicado"})
            _lead_pc["historial"]=_hist_pc
            save_lead(_lead_pc,is_new=False)
            st.session_state["pending_causa"]=None
            st.session_state["_nav_request"]="⊞ Funnel Kanban"
            st.rerun()
        if _fc2.button("↩ Cancelar", use_container_width=True, key="causa_f_cancel"):
            st.session_state["pending_causa"]=None
            st.rerun()
        st.stop()

    # ── Confirmación de borrado (prioridad máxima, bloquea el resto) ──────────
    if st.session_state.get("pending_delete_id"):
        _del_id     = st.session_state["pending_delete_id"]
        _del_nombre = st.session_state["pending_delete_nombre"]
        st.warning(f"⚠️ ¿Seguro que quieres eliminar a **{_del_nombre}**? Esta acción no se puede deshacer.")
        _c1, _c2 = st.columns(2)
        if _c1.button("🗑️ Sí, eliminar definitivamente", use_container_width=True):
            delete_lead(_del_id)
            st.session_state["pending_delete_id"]     = None
            st.session_state["pending_delete_nombre"] = None
            st.session_state["_nav_request"] = "⊞ Funnel Kanban"
            st.rerun()
        if _c2.button("↩ Cancelar", use_container_width=True):
            st.session_state["pending_delete_id"]     = None
            st.session_state["pending_delete_nombre"] = None
            st.rerun()
        st.stop()

    # ── Selector de lead ──────────────────────────────────────────────────────
    leads_editables=sorted(all_leads_raw,key=lambda l:max(l.get("ultimaActualizacion","") or "",l.get("fechaCreacion","") or ""),reverse=True)
    _leads_edit_dict={_lead_display(l):l for l in leads_editables}
    display_lista=["— Crear nuevo lead —"]+list(_leads_edit_dict.keys())
    _goto=st.session_state.get("goto_lead")
    if _goto:
        # goto_lead puede contener un ID (nuevo) o un nombre (compatibilidad)
        _disp_goto=next((_lead_display(l) for l in leads_editables if l["id"]==_goto or l["nombre"]==_goto),None)
        st.session_state["sel_lead"] = _disp_goto if _disp_goto in display_lista else display_lista[0]
        st.session_state["goto_lead"] = None
    if st.session_state.get("_sel_lead_request"):
        st.session_state["sel_lead"] = st.session_state["_sel_lead_request"]
        st.session_state["_sel_lead_request"] = None
    if "sel_lead" not in st.session_state or st.session_state["sel_lead"] not in display_lista:
        st.session_state["sel_lead"] = display_lista[0]
    sel=st.selectbox("Seleccionar lead existente",display_lista,key="sel_lead")
    existing=None if sel=="— Crear nuevo lead —" else _leads_edit_dict.get(sel)
    d=existing or {}
    if existing:
        st.markdown("---")
        st.markdown("##### ⚡ Cambio rápido de estado")
        c1,c2=st.columns([3,1])
        etapa_r=c1.selectbox("Nueva etapa",STAGES,index=STAGES.index(existing["etapa"]) if existing["etapa"] in STAGES else 0,key="etapa_r")
        if c2.button("✅ Actualizar"):
            _etapa_ant_r=existing.get("etapa","")
            existing["etapa"]=etapa_r; existing["ultimaActualizacion"]=str(date.today())
            if etapa_r in ["Cerrado Perdido","En Pausa / Recuperable"]:
                st.session_state["pending_causa"]={"lead":existing,"nombre":existing["nombre"],"etapa":etapa_r,"etapa_anterior":_etapa_ant_r}
            else:
                save_lead(con_cambio_etapa(existing,_etapa_ant_r),is_new=False); st.success(f"✅ → {etapa_r}")
            st.rerun()
        st.markdown("---")
    if st.session_state.get("_ultimo_guardado"):
        st.success(f"✅ Lead **{st.session_state['_ultimo_guardado']}** guardado correctamente.")
        st.session_state["_ultimo_guardado"] = None

    with st.form(f"lead_form_{d.get('id','new')}"):
        st.markdown("### 👤 Datos de Contacto")
        c1,c2,c3=st.columns(3)
        nombre =c1.text_input("Nombre *",value=d.get("nombre",""))
        empresa=c2.text_input("Empresa",value=d.get("empresa",""))
        idioma =c3.selectbox("Idioma",IDIOMAS,index=IDIOMAS.index(d["idioma"]) if d.get("idioma") in IDIOMAS else 0)
        c4,c5=st.columns(2)
        tel  =c4.text_input("Teléfono",value=d.get("telefono",""))
        email=c5.text_input("Email",value=d.get("email",""))
        st.markdown("### 🚢 Embarcación de Interés")
        c6,c7=st.columns(2)
        tipo  =c6.selectbox("Tipo / Marca",boat_types,index=boat_types.index(d["tipoEmbarcacion"]) if d.get("tipoEmbarcacion") in boat_types else 0)
        modelo=c7.text_input("Modelo / Eslora",value=d.get("modeloEslora",""))
        uso   =st.text_area("Notas internas",value=d.get("usoPrevisto",""),placeholder="Observaciones internas, contexto del cliente...",height=80)
        st.markdown("### 📋 Gestión Comercial")
        c9,c10,c11,c12=st.columns(4)
        etapa =c9.selectbox("Etapa",STAGES,index=STAGES.index(d["etapa"]) if d.get("etapa") in STAGES else 0)
        asig  =c10.selectbox("Asignado a",vendedores,index=vendedores.index(d["asignadoA"]) if d.get("asignadoA") in vendedores else 0)
        fuente=c11.selectbox("Fuente",sources,index=sources.index(d["fuenteLead"]) if d.get("fuenteLead") in sources else 0)
        prob  =c12.number_input("Probabilidad (%)",value=float(d.get("probabilidad",20) or 20),min_value=0.0,max_value=100.0,step=5.0)
        c13,c14,c15=st.columns(3)
        valor =c13.number_input("Valor operación (€)",value=float(d.get("valorOperacion",0) or 0),min_value=0.0,step=5000.0)
        prox_a=c14.text_input("Próxima acción",value=d.get("proximaAccion",""))
        try:    prox_d=c15.date_input("Fecha próx. acción",value=datetime.strptime(str(d.get("fechaProximaAccion","")),"%Y-%m-%d").date())
        except: prox_d=c15.date_input("Fecha próx. acción",value=date.today())
        submitted=st.form_submit_button("💾 Guardar Lead",use_container_width=True)
        if submitted:
            if not nombre.strip(): st.error("El nombre es obligatorio.")
            else:
                new_lead={"id":d.get("id","") or str(uuid.uuid4()),"nombre":nombre,"empresa":empresa,"telefono":tel,"email":email,"idioma":idioma,"tipoEmbarcacion":tipo,"modeloEslora":modelo,"presupuesto":int(valor),"usoPrevisto":uso,"asignadoA":asig,"etapa":etapa,"probabilidad":int(prob),"valorOperacion":int(valor),"fuenteLead":fuente,"proximaAccion":prox_a,"fechaProximaAccion":str(prox_d),"historial":d.get("historial",[]),"fechaCreacion":d.get("fechaCreacion","") or str(date.today()),"ultimaActualizacion":str(date.today())}
                # Guard anti-doble-guardado
                _lead_key = f"{new_lead['id']}|{etapa}|{nombre}|{str(date.today())}"
                if st.session_state.get("_last_lead_key") == _lead_key:
                    st.rerun()
                else:
                    st.session_state["_last_lead_key"] = _lead_key
                    _etapa_ant_form = d.get("etapa","") if existing else ""
                    if etapa in ["Cerrado Perdido","En Pausa / Recuperable"]:
                        st.session_state["pending_causa"]={"lead":new_lead,"nombre":nombre,"etapa":etapa,"etapa_anterior":_etapa_ant_form}
                    else:
                        if existing: new_lead=con_cambio_etapa(new_lead,_etapa_ant_form)
                        save_lead(new_lead,is_new=not bool(existing))
                        st.session_state["_ultimo_guardado"] = nombre
                        st.session_state["_sel_lead_request"] = _lead_display(new_lead)
                    st.rerun()

    if existing:
        # ── Registrar actividad ───────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### 📝 Registrar actividad")
        _a1, _a2 = st.columns([1, 3])
        _act_tipo = _a1.selectbox("Tipo de contacto", ["Email","Llamada","Reunión","WhatsApp","Nota"], key="act_tipo")
        _act_nota = _a2.text_area("Descripción", placeholder="Qué se dijo, qué se envió, qué contestó el lead...", height=90, key="act_nota", label_visibility="collapsed")
        st.markdown("<div style='color:#7a8fa6;font-size:0.75rem;margin:6px 0 2px'>↳ Próximo paso (opcional)</div>", unsafe_allow_html=True)
        _b1, _b2 = st.columns([3, 1])
        _prox_a = _b1.text_input("Próxima acción", value=existing.get("proximaAccion",""), placeholder="Ej: Llamada de seguimiento, Enviar contrato...", key="act_prox_a", label_visibility="collapsed")
        try:    _prox_d_def = datetime.strptime(str(existing.get("fechaProximaAccion","")), "%Y-%m-%d").date()
        except: _prox_d_def = date.today() + timedelta(days=7)
        _prox_d = _b2.date_input("Fecha", value=_prox_d_def, key="act_prox_d", label_visibility="collapsed")
        if st.button("➕ Registrar actividad y actualizar plan", use_container_width=True):
            if not _act_nota.strip():
                st.warning("Escribe la descripción antes de registrar.")
            else:
                # Guard anti-doble-clic: clave única por lead + tipo + texto + día
                _act_key = f"{existing['id']}|{_act_tipo}|{_act_nota.strip()}|{date.today()}"
                if st.session_state.get("_last_act_key") == _act_key:
                    st.rerun()  # ya guardado en esta sesión, ignorar segunda pulsación
                else:
                    _hist = existing.get("historial", []).copy()
                    _hist.append({"fecha": str(date.today()), "tipo": _act_tipo, "nota": _act_nota.strip()})
                    _upd = {**existing, "historial": _hist, "ultimaActualizacion": str(date.today())}
                    if _prox_a.strip():
                        _upd["proximaAccion"]      = _prox_a.strip()
                        _upd["fechaProximaAccion"] = str(_prox_d)
                    save_lead(_upd, is_new=False)
                    st.session_state["_last_act_key"] = _act_key
                    st.session_state["_sel_lead_request"] = _lead_display(existing)
                    st.rerun()

        # ── Historial de comunicaciones ───────────────────────────────────────
        st.markdown("---")
        st.markdown("##### 🕐 Historial de comunicaciones")
        _hist_list = existing.get("historial", [])
        if not _hist_list:
            st.caption("Sin actividad registrada aún.")
        else:
            TIPO_COLOR = {"Email":"#2563eb","Llamada":"#16a34a","Reunión":"#7c3aed","WhatsApp":"#25d366","Nota":"#c9a84c"}
            for h in reversed(_hist_list):
                _col = TIPO_COLOR.get(h["tipo"], "#7a8fa6")
                st.markdown(f"""<div style='background:#091220;border:1px solid #1a3050;border-left:3px solid {_col};border-radius:6px;padding:10px 14px;margin-bottom:6px'>
                    <div style='display:flex;align-items:center;gap:8px;margin-bottom:5px'>
                        <span style='color:#c9a84c;font-size:0.78rem;font-weight:700'>{_html.escape(h['fecha'])}</span>
                        <span style='background:{_col};color:white;border-radius:4px;padding:1px 8px;font-size:0.68rem;font-weight:700'>{_html.escape(h['tipo'])}</span>
                    </div>
                    <div style='color:#e8e0d0;font-size:0.84rem;white-space:pre-wrap'>{_html.escape(h['nota'])}</div>
                </div>""", unsafe_allow_html=True)

        # ── Generador de email ────────────────────────────────────────────────
        st.markdown("---")
        with st.expander("✉️ Generar email de seguimiento con IA"):
            _marca_det, _modelo_det = _detectar_marca(
                (existing.get("tipoEmbarcacion","") + " " + existing.get("modeloEslora","")).strip()
            )
            if _marca_det:
                st.info(f"🔍 Se buscará: **{_marca_det}** › **{_modelo_det}** en `{BRAND_SITES.get(_marca_det,'')}`")
            else:
                st.warning("⚠️ Marca no reconocida en el directorio — se generará email de presentación general.")

            _idioma_email = existing.get("idioma","Español")
            st.caption(f"Idioma del email: **{_idioma_email}** (según ficha del cliente)")

            if st.button("✉️ Generar email ahora", key="btn_gen_email", use_container_width=True):
                with st.spinner("Buscando información del modelo y redactando…"):
                    _info_w, _url_w, _err_w = (None, None, None)
                    if _marca_det:
                        _info_w, _url_w, _err_w = _fetch_model_info(_marca_det, _modelo_det)
                    if _err_w:
                        st.warning(f"⚠️ {_err_w} — Se generará email general sin info del modelo.")
                    elif _url_w:
                        st.success(f"✅ Info encontrada en: {_url_w}")
                    _email_txt = _generar_email(existing, _info_w, _url_w)
                    st.session_state["_email_generado"] = _email_txt

            if st.session_state.get("_email_generado"):
                st.markdown("**📧 Email generado — copia y edita según necesites:**")
                st.text_area("", value=st.session_state["_email_generado"],
                             height=380, key="email_output_area")
                if st.button("🗑️ Limpiar email", key="btn_clear_email"):
                    st.session_state["_email_generado"] = None
                    st.rerun()

        # ── Ficha imprimible ──────────────────────────────────────────────────
        st.markdown("---")
        if st.button("🖨️ Ver ficha para imprimir", use_container_width=True, key="toggle_ficha"):
            _ficha_abierta = st.session_state.get("show_ficha_lead")
            if _ficha_abierta == existing["id"]:
                st.session_state["show_ficha_lead"] = None
            else:
                st.session_state["show_ficha_lead"] = existing["id"]
        if st.session_state.get("show_ficha_lead") == existing["id"]:
            def _ficha_html(l):
                _hist_rows="".join(f"""<tr><td style='padding:6px 10px;color:#555;font-size:12px;white-space:nowrap;border-bottom:1px solid #eee'>{h['fecha']}</td>
                    <td style='padding:6px 10px;font-size:12px;border-bottom:1px solid #eee'><span style='background:#2563eb;color:white;border-radius:3px;padding:2px 8px;font-size:11px;font-weight:700'>{h['tipo']}</span></td>
                    <td style='padding:6px 10px;font-size:12px;border-bottom:1px solid #eee'>{h['nota']}</td></tr>""" for h in reversed(l.get("historial",[]))
                ) or "<tr><td colspan='3' style='padding:8px 10px;color:#999;font-size:12px;font-style:italic'>Sin actividad registrada</td></tr>"
                _prox=f"<b>{l.get('proximaAccion','')}</b> &nbsp;·&nbsp; {l.get('fechaProximaAccion','')}" if l.get("proximaAccion") else "—"
                _etapa_color={"Prospecto":"#1a4a8a","Contactado":"#2563eb","Interés Confirmado":"#7c3aed","Propuesta Enviada":"#b8860b","Negociación":"#ea580c","Cerrado Ganado":"#16a34a","Cerrado Perdido":"#dc2626","En Pausa / Recuperable":"#374151"}.get(l.get("etapa",""),"#0d3b6e")
                return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Ficha {l['nombre']}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#fff;color:#1a1a2e;padding:24px 32px;font-size:13px;line-height:1.5}}
  .header{{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:16px;border-bottom:2px solid #0d3b6e;margin-bottom:18px}}
  .header-left h1{{font-size:24px;color:#0d3b6e;margin-bottom:4px}}
  .header-left .sub{{color:#555;font-size:13px}}
  .badge{{display:inline-block;background:{_etapa_color};color:white;border-radius:4px;padding:3px 12px;font-size:12px;font-weight:700;margin-top:6px}}
  .logo{{height:38px}}
  .section-title{{font-size:13px;font-weight:700;color:#2563eb;text-transform:uppercase;letter-spacing:.6px;margin:18px 0 8px;border-bottom:1px solid #dde;padding-bottom:4px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px 24px;margin-bottom:4px}}
  .field .lbl{{color:#888;font-size:11px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:1px}}
  .field .val{{font-size:13px;font-weight:600;color:#1a1a2e}}
  .prox-box{{background:#fff8e1;border:1px solid #f0c040;border-radius:6px;padding:10px 16px;font-size:13px}}
  table{{width:100%;border-collapse:collapse;margin-top:4px;font-size:12px}}
  thead tr{{background:#0d3b6e}} thead th{{color:white;padding:7px 10px;text-align:left;font-size:11px;font-weight:600}}
  tbody tr:nth-child(even){{background:#f7f8fc}}
  .notas{{background:#f9f9f9;border:1px solid #e0e0e0;border-radius:6px;padding:10px 14px;white-space:pre-wrap;font-size:12.5px}}
  .footer{{margin-top:28px;padding-top:10px;border-top:1px solid #eee;color:#aaa;font-size:10px;display:flex;justify-content:space-between}}
  .print-btn{{display:inline-block;background:#0d3b6e;color:white;border:none;border-radius:6px;padding:9px 22px;font-size:13px;font-weight:700;cursor:pointer;margin-bottom:20px}}
  .print-btn:hover{{background:#2563eb}}
  @media print{{.print-btn{{display:none}}body{{padding:10px 14px}}}}
</style></head><body>
<button class='print-btn' onclick='window.print()'>🖨️ Imprimir / Guardar PDF</button>
<div class='header'>
  <div class='header-left'>
    <h1>{l['nombre']}</h1>
    <div class='sub'>{l.get('empresa','') or '—'} &nbsp;·&nbsp; {l.get('telefono','') or '—'} &nbsp;·&nbsp; {l.get('email','') or '—'}</div>
    <span class='badge'>{l.get('etapa','')}</span>
  </div>
  <img class='logo' src='https://raw.githubusercontent.com/Jose-Ibz/nauticrm/main/logo_viamar.jpg' onerror="this.style.display='none'">
</div>
<div class='section-title'>Datos comerciales</div>
<div class='grid'>
  <div class='field'><div class='lbl'>Embarcación</div><div class='val'>{l.get('tipoEmbarcacion','—')} {l.get('modeloEslora','')}</div></div>
  <div class='field'><div class='lbl'>Valor operación</div><div class='val'>€{int(l.get('valorOperacion',0) or 0):,}</div></div>
  <div class='field'><div class='lbl'>Probabilidad</div><div class='val'>{l.get('probabilidad','—')}%</div></div>
  <div class='field'><div class='lbl'>Fuente</div><div class='val'>{l.get('fuenteLead','—')}</div></div>
  <div class='field'><div class='lbl'>Idioma</div><div class='val'>{l.get('idioma','—')}</div></div>
  <div class='field'><div class='lbl'>Alta CRM</div><div class='val'>{l.get('fechaCreacion','—')}</div></div>
</div>
{'<div class="section-title">Notas internas</div><div class="notas">'+l.get("usoPrevisto","")+'</div>' if l.get("usoPrevisto") else ''}
<div class='section-title'>Próxima acción</div>
<div class='prox-box'>{_prox}</div>
<div class='section-title'>Historial de comunicaciones</div>
<table><thead><tr><th>Fecha</th><th>Tipo</th><th>Nota</th></tr></thead>
<tbody>{_hist_rows}</tbody></table>
<div class='footer'><span>NautiCRM · Náutica Viamar</span><span>Generado: {date.today().strftime('%d/%m/%Y')}</span></div>
</body></html>"""
            import streamlit.components.v1 as _comp
            _n_hist = len(existing.get("historial", []))
            _altura = min(900, 480 + _n_hist * 40)
            _comp.html(_ficha_html(existing), height=_altura, scrolling=True)

        if existing.get("etapa")=="Cerrado Ganado":
            st.markdown("---")
            st.markdown("<div style='color:#7a8fa6;font-size:0.8rem'>Este cliente ha cerrado operación. Si ya no va a comprar más (se ha ido de Ibiza, etc.) puedes pasarlo a pasivo: saldrá del pipeline pero sus datos quedan en la BBDD histórica.</div>", unsafe_allow_html=True)
            if st.button("👤 Pasar a cliente pasivo", use_container_width=True):
                clientes_pasivos.append({**existing,"fechaPasivo":str(date.today())})
                save_clientes_pasivos(clientes_pasivos)
                delete_lead(existing["id"])
                st.session_state["_nav_request"]="⊞ Funnel Kanban"
                st.success(f"✅ {existing['nombre']} pasado a clientes pasivos.")
                st.rerun()

        st.markdown("---")
        if st.button("🗑️ Eliminar este lead"):
            st.session_state["pending_delete_id"]     = existing["id"]
            st.session_state["pending_delete_nombre"] = existing["nombre"]
            st.rerun()

# ══ PRÓXIMAS ACCIONES ══════════════════════════════════════════════════════════
elif "Acciones" in page:
    st.markdown("## 📅 Próximas Acciones")
    c1,c2,c3=st.columns(3)
    fv_pa=c1.selectbox("Vendedor",["Todos"]+vendedores,key="fv_pa")
    fe_pa=c2.selectbox("Etapa",["Todas"]+FUNNEL_STAGES,key="fe_pa")
    solo_v=c3.checkbox("Solo vencidas / urgentes")
    acciones=[l for l in all_leads_raw if (l.get("proximaAccion") or l.get("fechaProximaAccion")) and l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]]
    if fv_pa!="Todos": acciones=[l for l in acciones if l["asignadoA"]==fv_pa]
    if fe_pa!="Todas": acciones=[l for l in acciones if l["etapa"]==fe_pa]
    if solo_v: acciones=[l for l in acciones if urg_emoji(l.get("fechaProximaAccion")) in ["🔴","🟡"]]
    acciones.sort(key=lambda l:(lambda ds:(datetime.strptime(str(ds),"%Y-%m-%d").date() if ds else date(9999,12,31)))(l.get("fechaProximaAccion","")))
    sin_accion=[l for l in all_leads_raw if not l.get("proximaAccion") and not l.get("fechaProximaAccion") and l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]]
    k1,k2,k3,k4=st.columns(4)
    k1.metric("🔴 Vencidas",len([l for l in acciones if urg_emoji(l.get("fechaProximaAccion"))=="🔴"]))
    k2.metric("🟡 Hoy",len([l for l in acciones if urg_emoji(l.get("fechaProximaAccion"))=="🟡"]))
    k3.metric("🟢 Próximas",len([l for l in acciones if urg_emoji(l.get("fechaProximaAccion"))=="🟢"]))
    k4.metric("⚪ Sin acción",len(sin_accion))
    st.markdown("<br>", unsafe_allow_html=True)
    current_sec=None
    for l in acciones:
        try:
            diff=(datetime.strptime(str(l.get("fechaProximaAccion","")),"%Y-%m-%d").date()-date.today()).days
            sec="🔴 Vencidas" if diff<0 else "🟡 Para hoy" if diff==0 else "📆 Esta semana" if diff<=7 else "🟢 Próximas"
            dias_txt=f"Venció hace {abs(diff)}d" if diff<0 else "Hoy" if diff==0 else f"En {diff}d"
            dtcol="#e74c3c" if diff<0 else "#f1c40f" if diff==0 else "#2ecc71"
        except: sec,dias_txt,dtcol="⚪ Sin fecha","Sin fecha","#7a8fa6"
        if sec!=current_sec: current_sec=sec; st.markdown(f"### {sec}")
        color=STAGE_COLORS.get(l["etapa"],"#1a3050")
        _pc1,_pc2=st.columns([11,1])
        with _pc1:
            st.markdown(f"""<div style="background:#0d1e35;border:1px solid #1a3050;border-left:4px solid {color};border-radius:8px;padding:12px 16px;margin-bottom:2px;display:flex;justify-content:space-between;align-items:center">
                <div style="flex:1"><div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">
                    <span style="color:#e8e0d0;font-weight:700;font-size:0.88rem">{_html.escape(l['nombre'])}</span>
                    <span style="background:{color};color:white;border-radius:10px;padding:1px 8px;font-size:0.62rem;font-weight:700">{_html.escape(l['etapa'])}</span>
                    <span style="color:#7a8fa6;font-size:0.72rem">{_html.escape(l['asignadoA'].replace('Vendedor','V.'))}</span></div>
                <div style="color:#c9a84c;font-size:0.82rem;margin-bottom:3px">↳ {_html.escape(l.get('proximaAccion','Sin descripción'))}</div>
                <div style="color:#7a8fa6;font-size:0.72rem">{_html.escape(l.get('empresa',''))} · {_html.escape(l.get('tipoEmbarcacion',''))} {_html.escape(l.get('modeloEslora',''))}</div></div>
                <div style="text-align:right;flex-shrink:0;margin-left:16px">
                    <div style="color:#e8e0d0;font-size:0.82rem;font-weight:700">{_html.escape(l.get('fechaProximaAccion','—'))}</div>
                    <div style="font-size:0.72rem;color:{dtcol}">{dias_txt}</div>
                    <div style="color:#2ecc71;font-family:monospace;font-size:0.72rem;margin-top:2px">{fmt_eur(l.get('valorOperacion',0))}</div>
                </div></div>""", unsafe_allow_html=True)
        with _pc2:
            if st.button("✏️", key=f"pa_{l['id']}", help="Ir a ficha y registrar actividad"):
                st.session_state["goto_lead"] = l["id"]
                st.session_state["_nav_request"] = "➕ Nuevo / Editar Lead"
                st.rerun()
    if sin_accion:
        st.markdown("---"); st.markdown("### ⚪ Sin próxima acción")
        for l in sin_accion:
            color=STAGE_COLORS.get(l["etapa"],"#1a3050")
            st.markdown(f"<div style='background:#0d1e35;border:1px solid #1a3050;border-left:4px solid {color};border-radius:8px;padding:10px 16px;margin-bottom:6px'><span style='color:#e8e0d0;font-weight:600'>{_html.escape(l['nombre'])}</span><span style='background:{color};color:white;border-radius:10px;padding:1px 8px;font-size:0.62rem;font-weight:700;margin:0 8px'>{_html.escape(l['etapa'])}</span><span style='color:#7a8fa6;font-size:0.75rem'>{_html.escape(l.get('empresa',''))}·{_html.escape(l['asignadoA'].replace('Vendedor','V.'))}</span></div>", unsafe_allow_html=True)

    # ── PDF Próximas Acciones ──────────────────────────────────────────────
    st.markdown("---")
    if st.button("🖨️ Generar PDF — Agenda de hoy y esta semana"):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        import io as _io_pdf
        _buf_pdf=_io_pdf.BytesIO()
        doc=SimpleDocTemplate(_buf_pdf,pagesize=landscape(A4),leftMargin=1.5*cm,rightMargin=1.5*cm,topMargin=1.5*cm,bottomMargin=1.5*cm)
        styles=getSampleStyleSheet()
        NAVY_C=colors.HexColor("#0A1628"); GOLD_C=colors.HexColor("#C9A84C"); LIGHT_C=colors.HexColor("#E8E0D0"); MID_C=colors.HexColor("#0D1E35")
        RED_C=colors.HexColor("#DC2626"); YEL_C=colors.HexColor("#B8860B"); GRN_C=colors.HexColor("#16A34A"); BLU_C=colors.HexColor("#2563EB")
        title_style=ParagraphStyle("title",fontName="Helvetica-Bold",fontSize=16,textColor=GOLD_C,spaceAfter=4)
        sub_style=ParagraphStyle("sub",fontName="Helvetica",fontSize=9,textColor=LIGHT_C,spaceAfter=12)
        sec_style=ParagraphStyle("sec",fontName="Helvetica-Bold",fontSize=11,textColor=GOLD_C,spaceBefore=12,spaceAfter=6)
        cell_style=ParagraphStyle("cell",fontName="Helvetica",fontSize=8,textColor=colors.black,leading=10)
        elems=[]
        elems.append(Paragraph("⚓  NautiCRM — Agenda de Próximas Acciones", title_style))
        elems.append(Paragraph(f"Generado: {date.today().strftime('%d/%m/%Y')}  ·  Vendedor: {fv_pa if fv_pa!='Todos' else 'Todos'}", sub_style))
        grupos=[("🔴 Vencidas", [l for l in acciones if urg_emoji(l.get("fechaProximaAccion"))=="🔴"], RED_C),
                ("🟡 Para hoy",  [l for l in acciones if urg_emoji(l.get("fechaProximaAccion"))=="🟡"], YEL_C),
                ("📆 Esta semana",[l for l in acciones if urg_emoji(l.get("fechaProximaAccion"))=="🟢" and (datetime.strptime(str(l.get("fechaProximaAccion","")),"%Y-%m-%d").date()-date.today()).days<=7], BLU_C),
                ("🟢 Próximas",  [l for l in acciones if urg_emoji(l.get("fechaProximaAccion"))=="🟢" and (datetime.strptime(str(l.get("fechaProximaAccion","")),"%Y-%m-%d").date()-date.today()).days>7], GRN_C),
        ]
        col_w=[5*cm,5*cm,2.5*cm,7*cm,2.5*cm,4*cm]
        for sec_name,sec_leads,sec_color in grupos:
            if not sec_leads: continue
            elems.append(Paragraph(sec_name, sec_style))
            tdata=[["Cliente","Empresa","Fecha","Próxima Acción","Etapa","Valor"]]
            for l in sec_leads:
                tdata.append([
                    Paragraph(l.get("nombre",""),cell_style),
                    Paragraph(l.get("empresa",""),cell_style),
                    l.get("fechaProximaAccion","—"),
                    Paragraph(l.get("proximaAccion",""),cell_style),
                    Paragraph(l.get("etapa",""),cell_style),
                    fmt_eur(l.get("valorOperacion",0)),
                ])
            t=Table(tdata,colWidths=col_w,repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),NAVY_C),("TEXTCOLOR",(0,0),(-1,0),GOLD_C),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),8),
                ("FONTNAME",(0,1),(-1,-1),"Helvetica"),("FONTSIZE",(0,1),(-1,-1),8),
                ("BACKGROUND",(0,1),(-1,-1),colors.HexColor("#F5F5F5")),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F0F4F8")]),
                ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CCCCCC")),
                ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
                ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LINEBELOW",(0,0),(-1,0),1.5,sec_color),
            ]))
            elems.append(t)
            elems.append(Spacer(1,0.3*cm))
        doc.build(elems)
        st.download_button("⬇️ Descargar PDF",data=_buf_pdf.getvalue(),file_name=f"agenda_acciones_{date.today()}.pdf",mime="application/pdf")

# ══ ARCHIVO FRÍO ══════════════════════════════════════════════════════════════
elif "Archivo" in page:
    st.markdown("## 🧊 Archivo Frío & Clientes Pasivos")
    _tab_arch, _tab_pas = st.tabs([f"🧊 Archivo Frío ({len(archivo_frio)})", f"👤 Clientes Pasivos ({len(clientes_pasivos)})"])
    with _tab_pas:
        st.markdown("Clientes que han comprado pero ya no están en el circuito activo de ventas. Sus datos quedan disponibles para informes históricos.")
        if not clientes_pasivos:
            st.info("No hay clientes pasivos todavía.")
        else:
            _rows_p=[{"Nombre":l.get("nombre",""),"Empresa":l.get("empresa",""),
                "Embarcación":f"{l.get('tipoEmbarcacion','')} {l.get('modeloEslora','')}".strip(),
                "Valor €":fmt_eur(l.get("valorOperacion",0)),
                "Email":l.get("email",""),"Teléfono":l.get("telefono",""),
                "Alta CRM":l.get("fechaCreacion",""),"Pasivo desde":l.get("fechaPasivo","")} for l in clientes_pasivos]
            st.dataframe(pd.DataFrame(_rows_p),use_container_width=True,hide_index=True)
            st.markdown("---"); st.markdown("**♻️ Reactivar cliente pasivo**")
            _pas_by_disp={_lead_display(l):l for l in clientes_pasivos}
            _sel_p=st.selectbox("Seleccionar",["— Selecciona —"]+list(_pas_by_disp.keys()),key="sel_pasivo")
            if _sel_p!="— Selecciona —" and st.button("♻️ Reactivar como Prospecto",key="btn_react_pas"):
                _lp=_pas_by_disp[_sel_p]
                _nl={**_lp,"etapa":"Prospecto","ultimaActualizacion":str(date.today())}
                _nl.pop("fechaPasivo",None)
                save_lead(_nl,is_new=True)
                _cp_nuevo=[l for l in clientes_pasivos if l.get("id")!=_lp.get("id")]
                save_clientes_pasivos(_cp_nuevo)
                st.success(f"✅ {_lp.get('nombre','')} reactivado como Prospecto."); st.rerun()
    with _tab_arch:
        st.markdown("Contactos en pausa más de **6 meses**.")
        if st.session_state.get("pending_arch"):
            _pa=st.session_state["pending_arch"]
            st.warning(f"⚠️ Archivando a **{_pa['nombre']}**")
            _motivo_a=st.text_area("Motivo del archivo frío (obligatorio)",placeholder="Ej: Sin interés por precio, barco vendido, sin respuesta prolongada...",key="motivo_arch_input")
            _pac1,_pac2=st.columns(2)
            if _pac1.button("✅ Confirmar archivo",key="btn_conf_arch",use_container_width=True):
                if not _motivo_a.strip():
                    st.error("Indica el motivo antes de archivar.")
                else:
                    _l_arch={**_pa["lead"],"fechaArchivo":str(date.today()),"motivoArchivo":_motivo_a.strip()}
                    archivo_frio.append(_l_arch)
                    save_archivo_frio(archivo_frio)
                    delete_lead(_pa["lead"]["id"])
                    st.session_state.pop("pending_arch",None)
                    st.rerun()
            if _pac2.button("❌ Cancelar",key="btn_cancel_arch",use_container_width=True):
                st.session_state.pop("pending_arch",None)
                st.rerun()
            st.stop()
    pausados=[l for l in all_leads_raw if l.get("etapa")=="En Pausa / Recuperable"]
    if pausados:
        with st.expander(f"📥 Archivar manualmente ({len(pausados)} en pausa)"):
            for l in pausados:
                c1,c2=st.columns([4,1])
                c1.markdown(f"**{l['nombre']}** — {l['empresa']} · {months_since(l.get('ultimaActualizacion') or l.get('fechaCreacion',''))} meses")
                if c2.button("Archivar",key=f"arch_{l['id']}"):
                    st.session_state["pending_arch"]={"lead":l,"nombre":l["nombre"]}
    if not archivo_frio: st.info("El archivo frío está vacío.")
    else:
        st.markdown("#### 🔎 Segmentación")
        _fa1,_fa2,_fa3=st.columns(3)
        q_a   =_fa1.text_input("🔍 Buscar nombre / empresa",key="q_arch")
        ft_a  =_fa2.selectbox("Embarcación",["Todos"]+boat_types,key="ft_arch")
        fi_a  =_fa3.selectbox("Idioma",["Todos"]+IDIOMAS,key="fi_arch")
        _fb1,_fb2,_fb3=st.columns(3)
        fv_a  =_fb1.selectbox("Vendedor",["Todos"]+vendedores,key="fv_arch")
        _presu_vals=[l.get("valorOperacion",0) or l.get("presupuesto",0) for l in archivo_frio if l.get("valorOperacion",0) or l.get("presupuesto",0)]
        _pmin=int(min(_presu_vals)) if _presu_vals else 0
        _pmax=int(max(_presu_vals)) if _presu_vals else 500000
        if _pmax>_pmin:
            _rango=_fb2.slider("Presupuesto (€)",min_value=_pmin,max_value=_pmax,value=(_pmin,_pmax),step=5000,key="fp_arch",format="€%d")
        else:
            _rango=(_pmin,_pmax)

        filtrado=archivo_frio
        if q_a:        filtrado=[l for l in filtrado if q_a.lower() in (l.get("nombre","")+" "+l.get("empresa","")).lower()]
        if ft_a!="Todos": filtrado=[l for l in filtrado if l.get("tipoEmbarcacion")==ft_a]
        if fi_a!="Todos": filtrado=[l for l in filtrado if l.get("idioma")==fi_a]
        if fv_a!="Todos": filtrado=[l for l in filtrado if l.get("asignadoA")==fv_a]
        filtrado=[l for l in filtrado if _rango[0]<=(l.get("valorOperacion",0) or l.get("presupuesto",0))<=_rango[1]]

        st.caption(f"**{len(filtrado)}** contactos seleccionados de {len(archivo_frio)} en total")
        rows=[{
            "Nombre":l.get("nombre",""),"Empresa":l.get("empresa",""),
            "Idioma":l.get("idioma","—"),
            "Embarcación":f"{l.get('tipoEmbarcacion','')} {l.get('modeloEslora','')}".strip(),
            "Valor €":fmt_eur(l.get("valorOperacion",0) or l.get("presupuesto",0)),
            "Email":l.get("email",""),"Teléfono":l.get("telefono",""),
            "Vendedor":l.get("asignadoA",""),"Archivado":l.get("fechaArchivo",""),
            "Motivo":l.get("motivoArchivo","")
        } for l in filtrado]
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

        import io as _io2
        rows_xl=[{
            "Nombre":l.get("nombre",""),"Empresa":l.get("empresa",""),
            "Email":l.get("email",""),"Teléfono":l.get("telefono",""),
            "Idioma":l.get("idioma","—"),
            "Embarcación":f"{l.get('tipoEmbarcacion','')} {l.get('modeloEslora','')}".strip(),
            "Notas internas":l.get("usoPrevisto",""),
            "Valor €":l.get("valorOperacion",0) or l.get("presupuesto",0),
            "Vendedor":l.get("asignadoA",""),
            "Fecha entrada":l.get("fechaCreacion",""),
            "Archivado":l.get("fechaArchivo","")
        } for l in filtrado]
        _sufijo="_".join(filter(None,[ft_a if ft_a!="Todos" else "",fi_a if fi_a!="Todos" else "",fv_a if fv_a!="Todos" else ""]))
        _fname=f"archivo_frio{'_'+_sufijo if _sufijo else ''}_{date.today()}.xlsx"
        _buf_arch=_io2.BytesIO()
        pd.DataFrame(rows_xl).to_excel(_buf_arch,index=False,engine="openpyxl")
        st.download_button("⬇️ Exportar segmento a Excel",data=_buf_arch.getvalue(),file_name=_fname,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown("---"); st.markdown("**♻️ Reactivar contacto**")
        _arch_by_disp={_lead_display(l):l for l in archivo_frio}
        sel_r=st.selectbox("Seleccionar",["— Selecciona —"]+list(_arch_by_disp.keys()))
        if sel_r!="— Selecciona —" and st.button("♻️ Reactivar como Prospecto"):
            lr=_arch_by_disp[sel_r]
            nuevo_lead={**lr,"etapa":"Prospecto","ultimaActualizacion":str(date.today())}
            nuevo_lead.pop("fechaArchivo",None)
            save_lead(nuevo_lead,is_new=True)
            archivo_frio_nuevo=[l for l in archivo_frio if l.get("id")!=lr.get("id")]
            save_archivo_frio(archivo_frio_nuevo)
            st.success(f"✅ {lr.get('nombre','')} reactivado."); st.rerun()

# ══ ASISTENTE IA ══════════════════════════════════════════════════════════════
elif "Asistente" in page:
    import anthropic as _anth, json as _json_chat
    st.markdown("## 💬 Asistente IA")
    st.caption("Pregunta en lenguaje natural sobre leads, clientes, pipeline e historial. Acceso completo a todos los datos del CRM.")

    # ── Serializar un lead completo para el contexto de la IA ─────────────────
    def _lead_to_text(l, include_historial=True):
        hist=l.get("historial",[])
        hist_txt=""
        if include_historial and hist:
            entradas=[f"    [{h.get('fecha','')}] {h.get('tipo','')}: {h.get('nota','')}" for h in hist]
            hist_txt=" | historial:\n"+"\n".join(entradas)
        return (
            f"  NOMBRE: {l.get('nombre','')} | EMPRESA: {l.get('empresa','')} | "
            f"EMAIL: {l.get('email','')} | TEL: {l.get('telefono','')} | IDIOMA: {l.get('idioma','')} | "
            f"BARCO: {l.get('tipoEmbarcacion','')} {l.get('modeloEslora','')} | "
            f"ETAPA: {l.get('etapa','')} | FUENTE: {l.get('fuenteLead','')} | "
            f"VENDEDOR: {l.get('asignadoA','')} | "
            f"VALOR: €{l.get('valorOperacion',0) or l.get('presupuesto',0)} | "
            f"PROB: {l.get('probabilidad',0)}% | "
            f"NOTAS: {l.get('usoPrevisto','')} | "
            f"ALTA: {l.get('fechaCreacion','')} | ULT.CONTACTO: {l.get('ultimaActualizacion','')} | "
            f"PRÓX.ACCIÓN: {l.get('proximaAccion','')} ({l.get('fechaProximaAccion','')})"
            + hist_txt
        )

    def _build_crm_context():
        lines=[f"FECHA HOY: {date.today()}"]
        # Separar activos por tipo
        _pipeline=[l for l in all_leads_raw if l.get("etapa") not in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]]
        _ganados=[l for l in all_leads_raw if l.get("etapa")=="Cerrado Ganado"]
        _perdidos=[l for l in all_leads_raw if l.get("etapa")=="Cerrado Perdido"]
        _pausa=[l for l in all_leads_raw if l.get("etapa")=="En Pausa / Recuperable"]

        lines.append(f"\n=== PIPELINE ACTIVO ({len(_pipeline)} leads) ===")
        for l in _pipeline: lines.append(_lead_to_text(l))

        if _ganados:
            lines.append(f"\n=== CERRADOS GANADOS EN CRM ({len(_ganados)}) ===")
            for l in _ganados: lines.append(_lead_to_text(l))

        if _perdidos:
            lines.append(f"\n=== CERRADOS PERDIDOS ({len(_perdidos)}) ===")
            for l in _perdidos: lines.append(_lead_to_text(l))

        if _pausa:
            lines.append(f"\n=== EN PAUSA / RECUPERABLE ({len(_pausa)}) ===")
            for l in _pausa: lines.append(_lead_to_text(l))

        if archivo_frio:
            lines.append(f"\n=== ARCHIVO FRÍO ({len(archivo_frio)}) ===")
            for l in archivo_frio:
                lines.append(
                    f"  {l.get('nombre','')} | {l.get('empresa','')} | {l.get('tipoEmbarcacion','')} {l.get('modeloEslora','')} | "
                    f"fuente:{l.get('fuenteLead','')} | archivado:{l.get('fechaArchivo','')} | motivo:{l.get('motivoArchivo','')} | "
                    f"email:{l.get('email','')} | tel:{l.get('telefono','')} | notas:{l.get('usoPrevisto','')}"
                )

        if clientes_pasivos:
            lines.append(f"\n=== CLIENTES PASIVOS / COMPRAS HISTÓRICAS ({len(clientes_pasivos)}) ===")
            for l in clientes_pasivos:
                lines.append(
                    f"  {l.get('nombre','')} | {l.get('empresa','')} | {l.get('tipoEmbarcacion','')} {l.get('modeloEslora','')} | "
                    f"valor:€{l.get('valorOperacion',0)} | vendedor:{l.get('asignadoA','')} | "
                    f"email:{l.get('email','')} | tel:{l.get('telefono','')} | "
                    f"cierre:{l.get('ultimaActualizacion','')} | pasivo_desde:{l.get('fechaPasivo','')}"
                )
        return "\n".join(lines)

    _SYS_BASE = (
        "Eres el asistente CRM de Náutica Viamar, empresa náutica en Ibiza especializada en venta de barcos de motor, vela y catamarán. "
        "Tienes acceso completo a TODOS los datos del CRM: pipeline activo, cerrados ganados/perdidos, leads en pausa, archivo frío y clientes pasivos históricos. "
        "Responde SIEMPRE en español, de forma concisa y estructurada. Usa tablas markdown para listados. "
        "Cuando busques modelos de barco, busca tanto en tipoEmbarcacion como en modeloEslora y también en las notas (campo NOTAS). "
        "Fuente 'Feria Náutica' o 'Salón' = captado en feria/salón náutico. "
        "El pipeline es: Prospecto → Contactado → Interés Confirmado → Propuesta Enviada → Negociación → Cerrado Ganado/Perdido. "
        "Los cerrados perdidos y archivo frío pueden reactivarse. Los clientes pasivos compraron y ya no están en seguimiento activo. "
        "Puedes calcular estadísticas, hacer conteos, buscar por cualquier campo incluyendo notas e historial de actividad.\n\n"
    )
    # Cachear el contexto CRM en session_state: solo se reconstruye si cambia el nº de leads
    _ctx_key = f"chat_ctx_{len(all_leads_raw)}_{len(archivo_frio)}_{len(clientes_pasivos)}"
    if st.session_state.get("_chat_ctx_key") != _ctx_key:
        st.session_state["_chat_ctx"]     = _build_crm_context()
        st.session_state["_chat_ctx_key"] = _ctx_key
    _SYS_CHAT = _SYS_BASE + st.session_state["_chat_ctx"]

    # ── UI ─────────────────────────────────────────────────────────────────────
    _total_reg = len(all_leads_raw) + len(archivo_frio) + len(clientes_pasivos)
    _c1, _c2 = st.columns([6,2])
    _c1.markdown(f"<div style='padding:8px 0;font-size:0.85rem;color:#7a8fa6'>📊 <b style='color:#e8e0d0'>{_total_reg}</b> registros totales en el CRM</div>", unsafe_allow_html=True)
    with _c2:
        if st.button("🗑️ Nueva conversación", use_container_width=True):
            st.session_state["chat_ia"] = []; st.rerun()

    st.markdown("---")

    # ── Historial de chat ──────────────────────────────────────────────────────
    if "chat_ia" not in st.session_state:
        st.session_state["chat_ia"] = []

    for msg in st.session_state["chat_ia"]:
        with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"]=="user" else "🤖"):
            st.markdown(msg["content"])

    if _pregunta := st.chat_input("Ej: ¿Quién quería un Sasga? ¿Cuántos leads del salón de Palma? ¿Qué clientes hablan francés?"):
        st.session_state["chat_ia"].append({"role":"user","content":_pregunta})
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(_pregunta)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Consultando datos..."):
                try:
                    _client_chat = _anth.Anthropic(api_key=st.secrets["anthropic_api_key"])
                    # Máximo 20 mensajes para evitar contexto desbordado
                    _msgs_recientes = st.session_state["chat_ia"][-20:]
                    _messages_api = [{"role": m["role"], "content": m["content"]} for m in _msgs_recientes]
                    _resp = _client_chat.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=2000,
                        system=[{"type":"text","text":_SYS_CHAT,"cache_control":{"type":"ephemeral"}}],
                        messages=_messages_api
                    )
                    _respuesta = _resp.content[0].text
                except Exception as _e:
                    _respuesta = f"❌ Error al consultar la IA: {_e}"
            st.markdown(_respuesta)

        st.session_state["chat_ia"].append({"role":"assistant","content":_respuesta})
        st.rerun()

# ══ CONFIG ════════════════════════════════════════════════════════════════════
elif "Config" in page:
    st.markdown("## ⚙️ Configuración")
    tab1,tab2,tab3,tab4=st.tabs(["👥 Equipo de ventas","🚢 Catálogo de embarcaciones","📡 Fuentes de lead","💾 Copias de seguridad"])
    def _cfg_save(fn, *args, msg_ok="✅ Guardado."):
        """Wrapper para guardar config mostrando error legible si falla."""
        try:
            fn(*args); st.success(msg_ok); st.rerun()
        except Exception as _e:
            st.error(f"⚠️ No se pudo guardar: {_e}\n\nEspera unos segundos e inténtalo de nuevo.")

    with tab1:
        with st.form("cfg_v"):
            names=[st.text_input(f"Vendedor {i+1}",value=v) for i,v in enumerate(vendedores)]
            if st.form_submit_button("💾 Guardar nombres"):
                _cfg_save(save_config, names, boat_types, sources)
    with tab2:
        st.caption("Gestiona los valores del desplegable de embarcación. Puedes añadir, renombrar o eliminar entradas.")
        st.markdown("<br>", unsafe_allow_html=True)
        _editando_bt = st.session_state.get("_edit_bt_idx", None)
        bt_rename_from = None; bt_rename_to = None
        for i, bt in enumerate(boat_types):
            c1, c2, c3 = st.columns([4, 1, 1])
            if _editando_bt == i:
                nuevo_nombre = c1.text_input("", value=bt, key=f"rename_val_{i}", label_visibility="collapsed")
                if c2.button("✓", key=f"ok_{i}", help="Guardar nombre"):
                    if nuevo_nombre.strip() and nuevo_nombre.strip() != bt:
                        bt_rename_from = bt; bt_rename_to = nuevo_nombre.strip()
                    st.session_state["_edit_bt_idx"] = None
                if c3.button("✕", key=f"cancel_{i}", help="Cancelar"):
                    st.session_state["_edit_bt_idx"] = None; st.rerun()
            else:
                c1.markdown(f"<div style='background:#0d1e35;border:1px solid #1a3050;border-radius:6px;padding:6px 12px;font-size:0.84rem;color:#e8e0d0'>{_html.escape(bt)}</div>", unsafe_allow_html=True)
                if c2.button("✏️", key=f"edit_{i}", help="Renombrar"):
                    st.session_state["_edit_bt_idx"] = i; st.rerun()
                if c3.button("✕", key=f"del_{i}", help="Eliminar"):
                    st.session_state["_confirm_del_bt"] = bt; st.rerun()
        if bt_rename_from and bt_rename_to:
            new_bt = [bt_rename_to if x == bt_rename_from else x for x in boat_types]
            _cfg_save(save_config, vendedores, new_bt, sources)
        _confirm_del_bt = st.session_state.get("_confirm_del_bt")
        if _confirm_del_bt:
            st.warning(f"¿Está seguro de querer borrar **'{_html.escape(_confirm_del_bt)}'**?")
            _dby, _dbn = st.columns(2)
            if _dby.button("✅ Sí, borrar", use_container_width=True, key="confirm_del_bt_yes"):
                st.session_state.pop("_confirm_del_bt", None)
                _cfg_save(save_config, vendedores, [x for x in boat_types if x != _confirm_del_bt], sources)
            if _dbn.button("❌ Cancelar", use_container_width=True, key="confirm_del_bt_no"):
                st.session_state.pop("_confirm_del_bt", None); st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("cfg_b"):
            c1, c2 = st.columns([3, 1])
            nueva = c1.text_input("Nueva marca/tipo", placeholder="Ej: Beneteau Motor, Lasai 36...", label_visibility="collapsed")
            if c2.form_submit_button("➕ Añadir"):
                if nueva.strip() and nueva.strip() not in boat_types:
                    _cfg_save(save_config, vendedores, boat_types+[nueva.strip()], sources, msg_ok=f"✅ '{nueva.strip()}' añadido.")
                elif nueva.strip() in boat_types: st.warning("Ya existe.")
        # ── Migración masiva de tipo ──────────────────────────────────────────
        with st.expander("🔄 Renombrar tipo en toda la base de datos"):
            st.caption("Cambia el tipo de embarcación en **todos los registros** (leads activos, archivo frío y clientes pasivos). Útil para consolidar duplicados como 'Beneteau Flyer' → 'Beneteau Motor'.")
            _mc1, _mc2 = st.columns(2)
            _mig_from = _mc1.selectbox("Tipo actual (a reemplazar)", boat_types, key="mig_from")
            _mig_to   = _mc2.selectbox("Nuevo tipo", boat_types, key="mig_to")
            if st.button("▶ Ejecutar migración", use_container_width=True, key="btn_mig"):
                if _mig_from == _mig_to:
                    st.warning("El tipo de origen y destino son el mismo.")
                else:
                    with st.spinner("Actualizando registros..."):
                        _res = _migrar_tipo_embarcacion(_mig_from, _mig_to)
                    _total = sum(v for v in _res.values() if isinstance(v, int))
                    if _total == 0:
                        st.info(f"No hay registros con tipo '{_mig_from}'.")
                    else:
                        _det = ", ".join(f"{s}: {n}" for s, n in _res.items() if isinstance(n, int) and n > 0)
                        st.success(f"✅ {_total} registro(s) actualizados ({_det}).")
                    _errs = {s: v for s, v in _res.items() if isinstance(v, str)}
                    if _errs:
                        st.error(f"Errores: {_errs}")
    with tab3:
        st.caption("Gestiona los valores del desplegable de fuente de lead.")
        st.markdown("<br>", unsafe_allow_html=True)
        cols_src=st.columns(4)
        for i,src in enumerate(sources):
            with cols_src[i%4]:
                c1,c2=st.columns([3,1])
                c1.markdown(f"<div style='background:#0d1e35;border:1px solid #1a3050;border-radius:6px;padding:5px 10px;font-size:0.82rem;color:#e8e0d0'>{src}</div>", unsafe_allow_html=True)
                if c2.button("✕",key=f"del_src_{i}"):
                    st.session_state["_confirm_del_src"] = src; st.rerun()
        _confirm_del_src = st.session_state.get("_confirm_del_src")
        if _confirm_del_src:
            st.warning(f"¿Está seguro de querer borrar **'{_html.escape(_confirm_del_src)}'**?")
            _dsy, _dsn = st.columns(2)
            if _dsy.button("✅ Sí, borrar", use_container_width=True, key="confirm_del_src_yes"):
                st.session_state.pop("_confirm_del_src", None)
                _cfg_save(save_config, vendedores, boat_types, [x for x in sources if x != _confirm_del_src])
            if _dsn.button("❌ Cancelar", use_container_width=True, key="confirm_del_src_no"):
                st.session_state.pop("_confirm_del_src", None); st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("cfg_src"):
            c1,c2=st.columns([3,1])
            nueva_src=c1.text_input("Nueva fuente",placeholder="Ej: LinkedIn, Partner, Evento...",label_visibility="collapsed")
            if c2.form_submit_button("➕ Añadir"):
                if nueva_src.strip() and nueva_src.strip() not in sources:
                    _cfg_save(save_config, vendedores, boat_types, sources+[nueva_src.strip()], msg_ok=f"✅ '{nueva_src.strip()}' añadido.")
                elif nueva_src.strip() in sources: st.warning("Ya existe.")
    with tab4:
        st.markdown("### 💾 Copias de Seguridad")
        st.caption(f"Copia automática cada día al abrir la app. Últimas **{BACKUP_MAX}** en Google Sheets + copia independiente en GitHub si está configurado.")

        # ── Estado Google Sheets ──
        _bak_list = _list_backup_sheets()
        _lbd2 = _last_backup_date()
        _sh1, _sh2 = st.columns(2)
        with _sh1:
            st.markdown("#### 📊 Google Sheets")
            if _lbd2:
                _dias2 = (date.today() - _lbd2).days
                _badge = "🟢 Hoy" if _dias2==0 else f"🟡 Hace {_dias2} días" if _dias2<=3 else f"🔴 Hace {_dias2} días"
                st.success(f"Última: **{_lbd2.strftime('%d/%m/%Y')}** {_badge}")
                st.caption(f"{len(_bak_list)} copias guardadas")
            else:
                st.warning("Sin copias todavía")
            if st.button("📸 Copia Sheets ahora", use_container_width=True):
                with st.spinner("Creando copia..."):
                    _created, _msg = _do_backup()
                if _created: st.success(f"✅ {_msg}")
                else: st.info(f"ℹ️ {_msg}")
                st.rerun()

        # ── Estado GitHub ──
        with _sh2:
            st.markdown("#### 🐙 GitHub (independiente)")
            if _github_backup_configured():
                _lbd_gh2 = _last_github_backup_date()
                if _lbd_gh2:
                    _dias_gh2 = (date.today() - _lbd_gh2).days
                    _badge_gh = "🟢 Hoy" if _dias_gh2==0 else f"🟡 Hace {_dias_gh2} días" if _dias_gh2<=3 else f"🔴 Hace {_dias_gh2} días"
                    st.success(f"Última: **{_lbd_gh2.strftime('%d/%m/%Y')}** {_badge_gh}")
                else:
                    st.warning("Configurado pero sin copias aún")
                if st.button("🐙 Copia GitHub ahora", use_container_width=True):
                    with st.spinner("Subiendo a GitHub..."):
                        _ok_gh, _msg_gh = _backup_to_github(all_leads_raw, archivo_frio, clientes_pasivos)
                    if _ok_gh: st.success(f"✅ {_msg_gh}")
                    else: st.error(f"❌ {_msg_gh}")
            else:
                st.info("No configurado")
                st.caption("Añade a Streamlit secrets:")
                st.code("github_token = \"ghp_xxxx\"\nbackup_repo = \"Jose-Ibz/nauticrm-backups\"", language="toml")

        st.markdown("---")
        st.markdown("#### 📋 Copias disponibles")
        if not _bak_list:
            st.info("No hay copias todavía.")
        else:
            for _bws in _bak_list:
                _bname = _bws.title
                _bdate_str = _bname[4:12]
                _bfecha = f"{_bdate_str[6:8]}/{_bdate_str[4:6]}/{_bdate_str[:4]}"
                _bc1, _bc2, _bc3 = st.columns([3,2,2])
                _bc1.markdown(f"**{_bfecha}**")
                # Descargar como JSON
                _bak_json = _backup_to_json(_bname)
                if _bak_json:
                    _bc2.download_button(
                        "⬇️ JSON",
                        data=_bak_json.encode("utf-8"),
                        file_name=f"backup_{_bname}.json",
                        mime="application/json",
                        key=f"dl_{_bname}",
                        use_container_width=True
                    )
                # Restaurar (con confirmación)
                if st.session_state.get("_confirm_restore")==_bname:
                    st.warning(f"⚠️ ¿Restaurar todos los leads desde **{_bfecha}**? Los datos actuales se sobreescribirán.")
                    _cr1, _cr2 = st.columns(2)
                    if _cr1.button("✅ Sí, restaurar", key=f"restore_ok_{_bname}", use_container_width=True):
                        with st.spinner("Restaurando..."):
                            _ok, _rmsg = _restore_backup(_bname)
                        st.session_state.pop("_confirm_restore",None)
                        if _ok: st.success(_rmsg)
                        else: st.error(f"❌ Error: {_rmsg}")
                        st.rerun()
                    if _cr2.button("❌ Cancelar", key=f"restore_cancel_{_bname}", use_container_width=True):
                        st.session_state.pop("_confirm_restore",None)
                        st.rerun()
                else:
                    if _bc3.button("↩️ Restaurar", key=f"restore_{_bname}", use_container_width=True):
                        st.session_state["_confirm_restore"] = _bname
                        st.rerun()

    st.markdown("---")
    st.markdown("##### 📱 Enlace Modo Feria")
    app_url=st.secrets.get("app_url","https://nauticrm-trn2jrtqldn9vfd4zic6hz.streamlit.app")
    st.code(f"{app_url}/?modo=feria")
    st.caption("Comparte esta URL con los vendedores para registro rápido desde móvil en ferias.")
