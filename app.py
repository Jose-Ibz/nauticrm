import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import uuid
import gspread
from google.oauth2.service_account import Credentials

params = st.query_params
MODO_FERIA = params.get("modo") == "feria"

st.set_page_config(
    page_title="NautiCRM Feria" if MODO_FERIA else "NautiCRM",
    page_icon="⚓",
    layout="centered" if MODO_FERIA else "wide",
    initial_sidebar_state="collapsed" if MODO_FERIA else "expanded"
)

STAGES = ["Prospecto","Contactado","Interés Confirmado","Propuesta Enviada","Negociación","Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]
FUNNEL_STAGES = [s for s in STAGES if s not in ["Cerrado Perdido","En Pausa / Recuperable"]]
PAUSA_MESES_ARCHIVO = 6
SOURCES = ["Feria Náutica","Web","Referido","RRSS","Llamada Fría","Otro"]
IDIOMAS = ["Español","Inglés","Francés","Italiano","Alemán","Portugués","Holandés","Ruso","Árabe","Chino","Otro"]
STAGE_COLORS = {
    "Prospecto":"#1a4a8a","Contactado":"#2563eb","Interés Confirmado":"#7c3aed",
    "Propuesta Enviada":"#b8860b","Negociación":"#ea580c","Cerrado Ganado":"#16a34a",
    "Cerrado Perdido":"#dc2626","En Pausa / Recuperable":"#374151",
}

st.markdown("""
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
.stButton>button{background:#c9a84c!important;color:#0a1628!important;font-weight:700!important;border:none!important;border-radius:6px!important}
.stButton>button:hover{opacity:.88!important}
.stDataFrame{border:1px solid #1a3050!important;border-radius:8px!important}
.stTabs [data-baseweb="tab-list"]{background:#0a1628;border-radius:8px;gap:4px;padding:4px}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#7a8fa6!important;border-radius:6px!important}
.stTabs [aria-selected="true"]{background:#c9a84c!important;color:#0a1628!important;font-weight:700!important}
.streamlit-expanderHeader{background:#0d1e35!important;border:1px solid #1a3050!important;border-radius:8px!important}
hr{border-color:#1a3050!important}
</style>""", unsafe_allow_html=True)

# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def get_sheet(tab):
    sh = get_client().open_by_key(st.secrets["spreadsheet_id"])
    try: return sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=1000, cols=30)
        return ws

LEAD_COLS = ["id","nombre","empresa","telefono","email","idioma","tipoEmbarcacion","modeloEslora","presupuesto","usoPrevisto","asignadoA","etapa","probabilidad","valorOperacion","fuenteLead","proximaAccion","fechaProximaAccion","historial","fechaCreacion","ultimaActualizacion"]

@st.cache_data(ttl=30)
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
    data = ws.get_all_records()
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
            entries = []
            for e in h.split(";;"):
                parts = e.split("|",2)
                if len(parts)==3: entries.append({"fecha":parts[0],"tipo":parts[1],"nota":parts[2]})
            lead["historial"] = entries
        else:
            lead["historial"] = []
        rows.append(lead)
    return rows

@st.cache_data(ttl=30)
def load_config():
    ws = get_sheet("Config")
    data = ws.get_all_records()
    vendedores = ["Vendedor 1","Vendedor 2","Vendedor 3"]
    boat_types = ["Velero","Motor","Catamarán","Zodiac","Charter","Jeanneau","Beneteau","Sunseeker","Princess","Azimut","Ferretti","Bavaria","Hanse","Lagoon","Otro"]
    archivo    = []
    if not data:
        ws.append_row(["key","value"])
        for i,v in enumerate(vendedores): ws.append_row([f"v{i+1}",v])
        ws.append_row(["boat_types", "||".join(boat_types)])
        return vendedores, boat_types, archivo
    df = pd.DataFrame(data)
    vv = df[df["key"].isin(["v1","v2","v3"])]["value"].tolist()
    if vv: vendedores = vv
    bt_row = df[df["key"]=="boat_types"]["value"].tolist()
    if bt_row: boat_types = bt_row[0].split("||")
    arch_row = df[df["key"]=="archivo_frio"]["value"].tolist()
    if arch_row and arch_row[0]:
        import json
        try: archivo = json.loads(arch_row[0])
        except: archivo = []
    return vendedores, boat_types, archivo

def save_lead(lead, is_new=True):
    ws = get_sheet("Leads")
    hist_str = ";;".join([f"{h['fecha']}|{h['tipo']}|{h['nota']}" for h in lead.get("historial",[])])
    row = [lead.get(c,"") for c in LEAD_COLS[:-1]] + [hist_str if c=="historial" else lead.get(c,"") for c in ["ultimaActualizacion"]]
    row = []
    for c in LEAD_COLS:
        if c == "historial": row.append(hist_str)
        else: row.append(lead.get(c,""))
    if is_new:
        ws.append_row(row)
    else:
        data = ws.get_all_records()
        for i,r in enumerate(data):
            if r["id"] == lead["id"]:
                ws.update(f"A{i+2}:{chr(64+len(LEAD_COLS))}{i+2}", [row])
                break
    load_leads.clear()

def delete_lead(lead_id):
    ws = get_sheet("Leads")
    data = ws.get_all_records()
    for i,r in enumerate(data):
        if r["id"] == lead_id:
            ws.delete_rows(i+2); break
    load_leads.clear()

def save_config(vendedores, boat_types, archivo):
    import json
    ws = get_sheet("Config")
    data = ws.get_all_records()
    updates = {"v1":vendedores[0],"v2":vendedores[1],"v3":vendedores[2],
               "boat_types":"||".join(boat_types),
               "archivo_frio":json.dumps(archivo, ensure_ascii=False)}
    for i,r in enumerate(data):
        if r["key"] in updates:
            ws.update_cell(i+2, 2, updates.pop(r["key"]))
    for k,v in updates.items():
        ws.append_row([k,v])
    load_config.clear()

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

# ─── CARGAR DATOS ─────────────────────────────────────────────────────────────
try:
    all_leads_raw = load_leads()
    vendedores, boat_types, archivo_frio = load_config()
except Exception as e:
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
    save_config(vendedores, boat_types, archivo_frio)
    for l in nuevos_arch: delete_lead(l["id"])
    all_leads_raw = activos

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
            st.markdown(f"<div style='background:#0d1e35;border:1px solid #1a3050;border-radius:8px;padding:10px 14px;margin-bottom:6px'><span style='color:#c9a84c;font-weight:700'>{l['nombre']}</span><span style='color:#7a8fa6;font-size:0.78rem'> · {l.get('empresa','')} · {l.get('tipoEmbarcacion','')}</span></div>", unsafe_allow_html=True)
    st.stop()

# ══ SIDEBAR ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚓ NautiCRM")
    st.markdown("*Gestión de Ventas Náuticas*")
    st.markdown("---")
    active_user  = st.selectbox("👤 Usuario activo", vendedores)
    my_portfolio = st.checkbox("📂 Ver solo mi cartera")
    st.markdown("---")
    page = st.radio("Navegación",[
        "⊞ Funnel Kanban","≡ Lista de Leads","📊 Informes",
        "➕ Nuevo / Editar Lead","📅 Próximas Acciones","🧊 Archivo Frío","⚙️ Configuración"
    ])
    st.markdown("---")
    if st.button("🔄 Actualizar datos"): load_leads.clear(); load_config.clear(); st.rerun()
    n_arch=len(archivo_frio)
    if n_arch>0: st.markdown(f"<div style='background:#1a3050;border-radius:6px;padding:6px 10px;font-size:0.75rem;color:#7a8fa6'>🧊 Archivo Frío: <b style='color:#e8e0d0'>{n_arch}</b></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    app_url = st.secrets.get("app_url","http://localhost:8501")
    st.markdown(f"<a href='{app_url}/?modo=feria' target='_blank' style='background:#c9a84c;color:#0a1628;padding:8px 14px;border-radius:6px;font-weight:700;font-size:0.8rem;text-decoration:none'>📱 Abrir modo Feria</a>", unsafe_allow_html=True)

leads = all_leads_raw
if my_portfolio: leads=[l for l in leads if l["asignadoA"]==active_user]

# ══ KANBAN ════════════════════════════════════════════════════════════════════
if "Kanban" in page:
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
            {"<small style='color:#7a8fa6;font-family:monospace;padding:0 4px;font-size:0.65rem'>"+fmt_eur(total)+"</small>" if total>0 else ""}""", unsafe_allow_html=True)
            for l in cards:
                d=days_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))
                st.markdown(f"""<div style="background:#0d1e35;border:1px solid #1a3050;border-left:3px solid {color};border-radius:6px;padding:7px 9px;margin:4px 0">
                    <div style="font-weight:700;color:#e8e0d0;font-size:0.75rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{urg_emoji(l.get('fechaProximaAccion'))} {l['nombre']}</div>
                    <div style="color:#c9a84c;font-size:0.65rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:3px">{l.get('modeloEslora') or l['tipoEmbarcacion']}</div>
                    <div style="display:flex;justify-content:space-between">
                        <span style="color:#2ecc71;font-family:monospace;font-weight:700;font-size:0.7rem">{fmt_eur(l.get('valorOperacion',0))}</span>
                        <span style="color:#7a8fa6;font-size:0.62rem">{l['asignadoA'].replace('Vendedor','V.')}·{d}d</span>
                    </div></div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚡ Cambio rápido de estado"):
        c1,c2,c3=st.columns(3)
        nombres_k=[l["nombre"] for l in all_leads_raw if l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido"]]
        sel_k=c1.selectbox("Lead",["— Selecciona —"]+nombres_k,key="sel_k")
        nueva_etapa=c2.selectbox("Nueva etapa",STAGES,key="etapa_k")
        if c3.button("✅ Cambiar"):
            if sel_k!="— Selecciona —":
                lead_upd=next(l for l in all_leads_raw if l["nombre"]==sel_k)
                lead_upd["etapa"]=nueva_etapa; lead_upd["ultimaActualizacion"]=str(date.today())
                save_lead(lead_upd, is_new=False)
                st.success(f"✅ {sel_k} → {nueva_etapa}"); st.rerun()

    st.markdown("<hr style='border-color:#1a3050'>", unsafe_allow_html=True)
    bc1,bc2,bc3=st.columns(3)
    for col,stage in zip([bc1,bc2,bc3],["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]):
        cards=[l for l in all_leads_raw if l["etapa"]==stage]
        total=sum(l.get("valorOperacion",0) for l in cards)
        color=STAGE_COLORS[stage]
        icon="✅" if stage=="Cerrado Ganado" else ("❌" if stage=="Cerrado Perdido" else "⏸️")
        with col:
            st.markdown(f"""<div style="background:{color};border-radius:6px 6px 0 0;padding:5px 12px;display:flex;justify-content:space-between;align-items:center">
                <span style="color:white;font-size:0.65rem;font-weight:700;text-transform:uppercase">{icon} {stage}</span>
                <span style="background:rgba(0,0,0,0.3);color:white;border-radius:10px;padding:0 6px;font-size:0.85rem;font-weight:700">{len(cards)}</span>
            </div><div style="background:#091220;border-radius:0 0 6px 6px;padding:5px;min-height:80px">
            {"<small style='color:#7a8fa6;font-family:monospace;padding:0 4px;font-size:0.65rem'>"+fmt_eur(total)+"</small>" if total>0 else ""}""", unsafe_allow_html=True)
            for l in cards[:5]:
                st.markdown(f"""<div style="background:#0d1e35;border:1px solid #1a3050;border-left:3px solid {color};border-radius:5px;padding:5px 8px;margin:3px 0;font-size:0.7rem">
                    <div style="font-weight:600;color:#e8e0d0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{l['nombre']}</div>
                    <div style="color:#7a8fa6;font-size:0.62rem">{l['empresa']}·{fmt_eur(l.get('valorOperacion',0))}</div></div>""", unsafe_allow_html=True)
            if len(cards)>5: st.markdown(f"<small style='color:#7a8fa6;padding:0 5px'>+{len(cards)-5} más</small>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:12px;padding:8px 14px;background:#0d1e35;border:1px solid #1a3050;border-radius:8px;font-size:0.72rem;color:#7a8fa6'>🔴 Vencida &nbsp;|&nbsp; 🟡 Hoy &nbsp;|&nbsp; 🟢 Futura &nbsp;|&nbsp; ⚪ Sin fecha</div>", unsafe_allow_html=True)

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
        rows=[{"Urg":urg_emoji(l.get("fechaProximaAccion")),"Nombre":l["nombre"],"Empresa":l["empresa"],"Idioma":l.get("idioma","—"),"Embarcación":f"{l['tipoEmbarcacion']}·{l['modeloEslora']}","Etapa":l["etapa"],"Valor €":fmt_eur(l.get("valorOperacion",0)),"Prob%":f"{l.get('probabilidad',0)}%","Vendedor":l["asignadoA"],"Próx. Acción":l.get("fechaProximaAccion","—")} for l in filtered]
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        csv=pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar CSV",data=csv,file_name="nauticrm_leads.csv",mime="text/csv")

# ══ INFORMES ══════════════════════════════════════════════════════════════════
elif "Informes" in page:
    st.markdown("## 📊 Informes y Análisis")
    active=[l for l in all_leads_raw if l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido","En Pausa / Recuperable"]]
    pipeline=sum(l.get("valorOperacion",0) for l in active)
    forecast=sum(l.get("valorOperacion",0)*l.get("probabilidad",0)/100 for l in all_leads_raw if l["etapa"]!="Cerrado Perdido")
    no_act=[l for l in active if days_since(l.get("ultimaActualizacion") or l.get("fechaCreacion",""))>7]
    k1,k2,k3,k4=st.columns(4)
    k1.metric("Total Leads",len(all_leads_raw),f"{len(active)} activos")
    k2.metric("Pipeline Activo",fmt_eur(pipeline))
    k3.metric("Forecast Mensual",fmt_eur(forecast),"Valor × Prob%")
    k4.metric("Sin actividad +7d",len(no_act),delta="⚠️ Revisar" if no_act else "✅ OK",delta_color="off")
    st.markdown("<br>", unsafe_allow_html=True)
    tab1,tab2,tab3=st.tabs(["🔻 Embudo","📊 Pipeline & Fuentes","📋 Actividad"])
    with tab1:
        st.markdown("#### Embudo de Ventas")
        fd=[{"Etapa":s,"Leads":len([l for l in all_leads_raw if l["etapa"]==s]),"Valor":sum(l.get("valorOperacion",0) for l in all_leads_raw if l["etapa"]==s),"Color":STAGE_COLORS[s]} for s in FUNNEL_STAGES]
        c1,c2=st.columns(2)
        with c1:
            st.markdown("**Por número de leads**")
            fig1=go.Figure(go.Funnel(y=[d["Etapa"] for d in fd],x=[d["Leads"] for d in fd],textinfo="value+percent initial",marker=dict(color=[d["Color"] for d in fd]),textfont=dict(color="white",size=12)))
            fig1.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="#e8e0d0",margin=dict(t=10,b=10,l=10,r=10),height=360)
            st.plotly_chart(fig1,use_container_width=True)
        with c2:
            st.markdown("**Por valor (€)**")
            fig2=go.Figure(go.Funnel(y=[d["Etapa"] for d in fd],x=[d["Valor"] for d in fd],texttemplate=[fmt_eur(d["Valor"])+"<br>%{percentInitial}" for d in fd],marker=dict(color=[d["Color"] for d in fd]),textfont=dict(color="white",size=11)))
            fig2.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="#e8e0d0",margin=dict(t=10,b=10,l=10,r=10),height=360)
            st.plotly_chart(fig2,use_container_width=True)
        rows_f=[{"Etapa":d["Etapa"],"Leads":d["Leads"],"Valor Pipeline":fmt_eur(d["Valor"]),"Ticket Medio":fmt_eur(d["Valor"]/d["Leads"]) if d["Leads"]>0 else "—"} for d in fd]
        st.dataframe(pd.DataFrame(rows_f),use_container_width=True,hide_index=True)
    with tab2:
        c1,c2=st.columns(2)
        with c1:
            st.markdown("#### Pipeline por Vendedor")
            pv={v:sum(l.get("valorOperacion",0) for l in active if l["asignadoA"]==v) for v in vendedores}
            df_pv=pd.DataFrame({"Vendedor":list(pv.keys()),"Valor":list(pv.values())})
            fig=px.bar(df_pv,x="Vendedor",y="Valor",color_discrete_sequence=["#c9a84c"],text=df_pv["Valor"].apply(fmt_eur))
            fig.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="#e8e0d0",showlegend=False,xaxis=dict(gridcolor="#1a3050"),yaxis=dict(gridcolor="#1a3050"),margin=dict(t=20,b=10,l=10,r=10))
            fig.update_traces(textposition="outside"); st.plotly_chart(fig,use_container_width=True)
        with c2:
            st.markdown("#### Leads por Fuente")
            src={}
            for l in all_leads_raw: src[l.get("fuenteLead","Otro")]=src.get(l.get("fuenteLead","Otro"),0)+1
            fig2=px.pie(pd.DataFrame({"Fuente":list(src.keys()),"N":list(src.values())}),names="Fuente",values="N",hole=0.52,color_discrete_sequence=["#c9a84c","#2563eb","#7c3aed","#ea580c","#16a34a","#dc2626"])
            fig2.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="#e8e0d0",margin=dict(t=20,b=10,l=10,r=10))
            st.plotly_chart(fig2,use_container_width=True)
        st.markdown("#### Leads por Idioma")
        ic={}
        for l in all_leads_raw: ic[l.get("idioma","—")]=ic.get(l.get("idioma","—"),0)+1
        df_id=pd.DataFrame({"Idioma":list(ic.keys()),"Leads":list(ic.values())}).sort_values("Leads",ascending=False)
        fig3=px.bar(df_id,x="Idioma",y="Leads",color_discrete_sequence=["#2563eb"],text="Leads")
        fig3.update_layout(plot_bgcolor="#091220",paper_bgcolor="#0d1e35",font_color="#e8e0d0",showlegend=False,xaxis=dict(gridcolor="#1a3050"),yaxis=dict(gridcolor="#1a3050"),margin=dict(t=10,b=10,l=10,r=10),height=220)
        fig3.update_traces(textposition="outside"); st.plotly_chart(fig3,use_container_width=True)
    with tab3:
        c1,c2=st.columns(2)
        with c1:
            st.markdown("#### Actividad Reciente")
            hist_all=[]
            for l in all_leads_raw:
                for h in l.get("historial",[]): hist_all.append({**h,"lead":l["nombre"]})
            hist_all.sort(key=lambda x:x["fecha"],reverse=True)
            for h in hist_all[:10]:
                st.markdown(f"<div style='padding:7px 0;border-bottom:1px solid #1a3050'><span style='color:#c9a84c;font-size:0.78rem;font-weight:700'>{h['lead']}</span><span style='color:#7a8fa6;font-size:0.72rem'> · {h['fecha']}</span><span style='background:#1a3050;color:#7a8fa6;border-radius:4px;padding:1px 5px;font-size:0.65rem;margin-left:5px'>{h['tipo']}</span><div style='color:#e8e0d0;font-size:0.78rem;margin-top:3px'>{h['nota']}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown("#### Sin actividad +7 días")
            if not no_act: st.success("✅ Todo al día.")
            else:
                for l in no_act:
                    d=days_since(l.get("ultimaActualizacion","") or l.get("fechaCreacion",""))
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:6px 10px;margin-bottom:5px;background:#0d1e35;border:1px solid #e74c3c33;border-radius:6px'><span style='color:#e8e0d0;font-size:0.82rem'>{l['nombre']}</span><span style='color:#e74c3c;font-size:0.78rem'>{d}d·{l['asignadoA'].replace('Vendedor','V.')}</span></div>", unsafe_allow_html=True)
    st.markdown("---")
    csv_inf=pd.DataFrame([{k:v for k,v in l.items() if k!="historial"} for l in all_leads_raw]).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV",data=csv_inf,file_name="nauticrm_informe.csv",mime="text/csv")

# ══ LEAD FORM ═════════════════════════════════════════════════════════════════
elif "Lead" in page:
    st.markdown("## ➕ Nuevo / Editar Lead")
    nombres_lista=["— Crear nuevo lead —"]+[l["nombre"] for l in all_leads_raw]
    sel=st.selectbox("Seleccionar lead existente",nombres_lista)
    existing=None if sel=="— Crear nuevo lead —" else next((l for l in all_leads_raw if l["nombre"]==sel),None)
    d=existing or {}
    if existing:
        st.markdown("---")
        st.markdown("##### ⚡ Cambio rápido de estado")
        c1,c2=st.columns([3,1])
        etapa_r=c1.selectbox("Nueva etapa",STAGES,index=STAGES.index(existing["etapa"]) if existing["etapa"] in STAGES else 0,key="etapa_r")
        if c2.button("✅ Actualizar"):
            existing["etapa"]=etapa_r; existing["ultimaActualizacion"]=str(date.today())
            save_lead(existing,is_new=False); st.success(f"✅ → {etapa_r}"); st.rerun()
        st.markdown("---")
    with st.form("lead_form"):
        st.markdown("### 👤 Datos de Contacto")
        c1,c2,c3=st.columns(3)
        nombre =c1.text_input("Nombre *",value=d.get("nombre",""))
        empresa=c2.text_input("Empresa",value=d.get("empresa",""))
        idioma =c3.selectbox("Idioma",IDIOMAS,index=IDIOMAS.index(d["idioma"]) if d.get("idioma") in IDIOMAS else 0)
        c4,c5=st.columns(2)
        tel  =c4.text_input("Teléfono",value=d.get("telefono",""))
        email=c5.text_input("Email",value=d.get("email",""))
        st.markdown("### 🚢 Embarcación de Interés")
        c6,c7,c8=st.columns(3)
        tipo  =c6.selectbox("Tipo / Marca",boat_types,index=boat_types.index(d["tipoEmbarcacion"]) if d.get("tipoEmbarcacion") in boat_types else 0)
        modelo=c7.text_input("Modelo / Eslora",value=d.get("modeloEslora",""))
        presu =c8.number_input("Presupuesto (€)",value=float(d.get("presupuesto",0) or 0),min_value=0.0,step=5000.0)
        uso   =st.text_input("Uso previsto",value=d.get("usoPrevisto",""))
        st.markdown("### 📋 Gestión Comercial")
        c9,c10,c11,c12=st.columns(4)
        etapa =c9.selectbox("Etapa",STAGES,index=STAGES.index(d["etapa"]) if d.get("etapa") in STAGES else 0)
        asig  =c10.selectbox("Asignado a",vendedores,index=vendedores.index(d["asignadoA"]) if d.get("asignadoA") in vendedores else 0)
        fuente=c11.selectbox("Fuente",SOURCES,index=SOURCES.index(d["fuenteLead"]) if d.get("fuenteLead") in SOURCES else 0)
        prob  =c12.number_input("Probabilidad (%)",value=float(d.get("probabilidad",20) or 20),min_value=0.0,max_value=100.0,step=5.0)
        c13,c14,c15=st.columns(3)
        valor =c13.number_input("Valor operación (€)",value=float(d.get("valorOperacion",0) or 0),min_value=0.0,step=5000.0)
        prox_a=c14.text_input("Próxima acción",value=d.get("proximaAccion",""))
        try:    prox_d=c15.date_input("Fecha próx. acción",value=datetime.strptime(str(d.get("fechaProximaAccion","")),"%Y-%m-%d").date())
        except: prox_d=c15.date_input("Fecha próx. acción",value=date.today())
        st.markdown("### 📝 Historial")
        hist_entries=d.get("historial",[]).copy()
        if hist_entries:
            for h in reversed(hist_entries):
                st.markdown(f"<div style='background:#091220;border-radius:6px;padding:8px 12px;margin-bottom:5px;border-left:3px solid #c9a84c'><span style='color:#c9a84c;font-size:0.78rem;font-weight:700'>{h['fecha']}</span><span style='background:#1a3050;color:#7a8fa6;border-radius:4px;padding:1px 6px;font-size:0.65rem;margin-left:8px'>{h['tipo']}</span><div style='color:#e8e0d0;font-size:0.82rem;margin-top:4px'>{h['nota']}</div></div>", unsafe_allow_html=True)
        else: st.caption("Sin interacciones aún.")
        nc1,nc2=st.columns([1,4])
        new_tipo=nc1.selectbox("Tipo",["Email","Llamada","Reunión","Nota"])
        new_nota=nc2.text_input("Nota",placeholder="Describe la interacción...")
        submitted=st.form_submit_button("💾 Guardar Lead",use_container_width=True)
        if submitted:
            if not nombre.strip(): st.error("El nombre es obligatorio.")
            else:
                if new_nota.strip(): hist_entries.append({"fecha":str(date.today()),"tipo":new_tipo,"nota":new_nota.strip()})
                new_lead={"id":d.get("id","") or str(uuid.uuid4()),"nombre":nombre,"empresa":empresa,"telefono":tel,"email":email,"idioma":idioma,"tipoEmbarcacion":tipo,"modeloEslora":modelo,"presupuesto":int(presu),"usoPrevisto":uso,"asignadoA":asig,"etapa":etapa,"probabilidad":int(prob),"valorOperacion":int(valor),"fuenteLead":fuente,"proximaAccion":prox_a,"fechaProximaAccion":str(prox_d),"historial":hist_entries,"fechaCreacion":d.get("fechaCreacion","") or str(date.today()),"ultimaActualizacion":str(date.today())}
                save_lead(new_lead,is_new=not bool(existing))
                st.success("✅ Lead guardado."); st.rerun()
    if existing:
        st.markdown("---")
        if st.button("🗑️ Eliminar este lead"):
            delete_lead(existing["id"]); st.success("Lead eliminado."); st.rerun()

# ══ PRÓXIMAS ACCIONES ══════════════════════════════════════════════════════════
elif "Acciones" in page:
    st.markdown("## 📅 Próximas Acciones")
    c1,c2,c3=st.columns(3)
    fv_pa=c1.selectbox("Vendedor",["Todos"]+vendedores,key="fv_pa")
    fe_pa=c2.selectbox("Etapa",["Todas"]+FUNNEL_STAGES,key="fe_pa")
    solo_v=c3.checkbox("Solo vencidas / urgentes")
    acciones=[l for l in all_leads_raw if (l.get("proximaAccion") or l.get("fechaProximaAccion")) and l["etapa"] not in ["Cerrado Ganado","Cerrado Perdido"]]
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
        st.markdown(f"""<div style="background:#0d1e35;border:1px solid #1a3050;border-left:4px solid {color};border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
            <div style="flex:1"><div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">
                <span style="color:#e8e0d0;font-weight:700;font-size:0.88rem">{l['nombre']}</span>
                <span style="background:{color};color:white;border-radius:10px;padding:1px 8px;font-size:0.62rem;font-weight:700">{l['etapa']}</span>
                <span style="color:#7a8fa6;font-size:0.72rem">{l['asignadoA'].replace('Vendedor','V.')}</span></div>
            <div style="color:#c9a84c;font-size:0.82rem;margin-bottom:3px">↳ {l.get('proximaAccion','Sin descripción')}</div>
            <div style="color:#7a8fa6;font-size:0.72rem">{l.get('empresa','')} · {l.get('tipoEmbarcacion','')} {l.get('modeloEslora','')}</div></div>
            <div style="text-align:right;flex-shrink:0;margin-left:16px">
                <div style="color:#e8e0d0;font-size:0.82rem;font-weight:700">{l.get('fechaProximaAccion','—')}</div>
                <div style="font-size:0.72rem;color:{dtcol}">{dias_txt}</div>
                <div style="color:#2ecc71;font-family:monospace;font-size:0.72rem;margin-top:2px">{fmt_eur(l.get('valorOperacion',0))}</div>
            </div></div>""", unsafe_allow_html=True)
    if sin_accion:
        st.markdown("---"); st.markdown("### ⚪ Sin próxima acción")
        for l in sin_accion:
            color=STAGE_COLORS.get(l["etapa"],"#1a3050")
            st.markdown(f"<div style='background:#0d1e35;border:1px solid #1a3050;border-left:4px solid {color};border-radius:8px;padding:10px 16px;margin-bottom:6px'><span style='color:#e8e0d0;font-weight:600'>{l['nombre']}</span><span style='background:{color};color:white;border-radius:10px;padding:1px 8px;font-size:0.62rem;font-weight:700;margin:0 8px'>{l['etapa']}</span><span style='color:#7a8fa6;font-size:0.75rem'>{l.get('empresa','')}·{l['asignadoA'].replace('Vendedor','V.')}</span></div>", unsafe_allow_html=True)

# ══ ARCHIVO FRÍO ══════════════════════════════════════════════════════════════
elif "Archivo" in page:
    st.markdown("## 🧊 Archivo Frío")
    st.markdown("Contactos en pausa más de **6 meses**.")
    pausados=[l for l in all_leads_raw if l.get("etapa")=="En Pausa / Recuperable"]
    if pausados:
        with st.expander(f"📥 Archivar manualmente ({len(pausados)} en pausa)"):
            for l in pausados:
                c1,c2=st.columns([4,1])
                c1.markdown(f"**{l['nombre']}** — {l['empresa']} · {months_since(l.get('ultimaActualizacion') or l.get('fechaCreacion',''))} meses")
                if c2.button("Archivar",key=f"arch_{l['id']}"):
                    archivo_frio.append({**l,"fechaArchivo":str(date.today())})
                    save_config(vendedores,boat_types,archivo_frio)
                    delete_lead(l["id"]); st.rerun()
    if not archivo_frio: st.info("El archivo frío está vacío.")
    else:
        c1,c2,c3=st.columns(3)
        q_a=c1.text_input("🔍 Buscar",key="q_arch"); ft_a=c2.selectbox("Tipo",["Todos"]+boat_types,key="ft_arch"); fv_a=c3.selectbox("Vendedor",["Todos"]+vendedores,key="fv_arch")
        filtrado=archivo_frio
        if q_a: filtrado=[l for l in filtrado if q_a.lower() in (l.get("nombre","")+" "+l.get("empresa","")).lower()]
        if ft_a!="Todos": filtrado=[l for l in filtrado if l.get("tipoEmbarcacion")==ft_a]
        if fv_a!="Todos": filtrado=[l for l in filtrado if l.get("asignadoA")==fv_a]
        st.caption(f"{len(filtrado)} de {len(archivo_frio)} contactos")
        rows=[{"Nombre":l.get("nombre",""),"Empresa":l.get("empresa",""),"Idioma":l.get("idioma","—"),"Embarcación":f"{l.get('tipoEmbarcacion','')}·{l.get('modeloEslora','')}","Presupuesto":fmt_eur(l.get("presupuesto",0)),"Email":l.get("email",""),"Teléfono":l.get("telefono",""),"Vendedor":l.get("asignadoA",""),"Archivado":l.get("fechaArchivo","")} for l in filtrado]
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        csv=pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar CSV",data=csv,file_name="archivo_frio.csv",mime="text/csv")
        st.markdown("---"); st.markdown("**♻️ Reactivar contacto**")
        sel_r=st.selectbox("Seleccionar",["— Selecciona —"]+[l["nombre"] for l in archivo_frio])
        if sel_r!="— Selecciona —" and st.button("♻️ Reactivar como Prospecto"):
            lr=next(l for l in archivo_frio if l["nombre"]==sel_r)
            nuevo_lead={**lr,"etapa":"Prospecto","ultimaActualizacion":str(date.today())}
            nuevo_lead.pop("fechaArchivo",None)
            save_lead(nuevo_lead,is_new=True)
            archivo_frio_nuevo=[l for l in archivo_frio if l["nombre"]!=sel_r]
            save_config(vendedores,boat_types,archivo_frio_nuevo)
            st.success(f"✅ {sel_r} reactivado."); st.rerun()

# ══ CONFIG ════════════════════════════════════════════════════════════════════
elif "Config" in page:
    st.markdown("## ⚙️ Configuración")
    tab1,tab2=st.tabs(["👥 Equipo de ventas","🚢 Catálogo de embarcaciones"])
    with tab1:
        with st.form("cfg_v"):
            names=[st.text_input(f"Vendedor {i+1}",value=v) for i,v in enumerate(vendedores)]
            if st.form_submit_button("💾 Guardar nombres"):
                save_config(names,boat_types,archivo_frio); st.success("✅ Actualizado."); st.rerun()
    with tab2:
        st.caption("Gestiona los valores del desplegable de embarcación.")
        st.markdown("<br>", unsafe_allow_html=True)
        cols_bt=st.columns(4); to_delete=None
        for i,bt in enumerate(boat_types):
            with cols_bt[i%4]:
                c1,c2=st.columns([3,1])
                c1.markdown(f"<div style='background:#0d1e35;border:1px solid #1a3050;border-radius:6px;padding:5px 10px;font-size:0.82rem;color:#e8e0d0'>{bt}</div>", unsafe_allow_html=True)
                if c2.button("✕",key=f"del_{i}"): to_delete=bt
        if to_delete:
            new_bt=[x for x in boat_types if x!=to_delete]
            save_config(vendedores,new_bt,archivo_frio); st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("cfg_b"):
            c1,c2=st.columns([3,1])
            nueva=c1.text_input("Nueva marca/tipo",placeholder="Ej: Hallberg-Rassy, Dufour...",label_visibility="collapsed")
            if c2.form_submit_button("➕ Añadir"):
                if nueva.strip() and nueva.strip() not in boat_types:
                    save_config(vendedores,boat_types+[nueva.strip()],archivo_frio); st.success(f"✅ '{nueva.strip()}' añadido."); st.rerun()
                elif nueva.strip() in boat_types: st.warning("Ya existe.")
        if st.button("↺ Restaurar por defecto"):
            save_config(vendedores,["Velero","Motor","Catamarán","Zodiac","Charter","Jeanneau","Beneteau","Sunseeker","Princess","Azimut","Ferretti","Bavaria","Hanse","Lagoon","Otro"],archivo_frio); st.rerun()
    st.markdown("---")
    st.markdown("##### 📱 Enlace Modo Feria")
    app_url=st.secrets.get("app_url","https://tu-app.streamlit.app")
    st.code(f"{app_url}/?modo=feria")
    st.caption("Comparte esta URL con los vendedores para registro rápido desde móvil en ferias.")
