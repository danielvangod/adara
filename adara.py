import io
import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# ===================================================================
# [SEGMENTO 1]: CONFIGURACIÓN DE PÁGINA Y ZONA HORARIA
# ===================================================================
st.set_page_config(
    page_title="Control de Permisos de Ausencia", 
    page_icon="📅", 
    layout="wide",
    initial_sidebar_state="expanded"
)

ZONA_HORARIA = pytz.timezone('America/Guatemala')

def obtener_fecha_actual():
    """Devuelve la fecha actual ajustada a la zona horaria local."""
    return datetime.now(ZONA_HORARIA).date()

def obtener_timestamp_actual():
    """Devuelve fecha y hora completa ajustada a la zona horaria local."""
    return datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d %H:%M:%S")


# ===================================================================
# [SEGMENTO 2]: CONFIGURACIÓN DE COLORES Y PALETA VISUAL
# ===================================================================
PALETA_COLORES = {
    "Médica": "#36A2EB",         # Azul
    "Vacaciones": "#4BC0C0",      # Verde turquesa
    "Suspensiones": "#FF6384",    # Rosa / Rojo
    "Sanciones": "#FF9F40",       # Naranja
    "Asunto Personal": "#9966FF", # Morado
    "Otro": "#8E44AD"             # Violeta Oscuro
}

ICONOS_CATEGORIAS = {
    "Médica": "➕", 
    "Vacaciones": "🧳", 
    "Suspensiones": "📋", 
    "Sanciones": "⚖️", 
    "Asunto Personal": "👤", 
    "Otro": "💬"
}


# ===================================================================
# [SEGMENTO 3]: ESTILOS CSS DEL CALENDARIO (PALETA VIOLETA + ENCABEZADO)
# ===================================================================
CSS_CALENDARIO_PERSONALIZADO = """
    /* Forzar variables de color violeta en el contenedor raíz */
    .fc {
        --fc-button-bg-color: #6b78ed !important;          /* Violeta principal */
        --fc-button-border-color: #7a22cc !important;      /* Borde violeta */
        --fc-button-hover-bg-color: #6a1bb8 !important;    /* Violeta oscuro al pasar el mouse */
        --fc-button-hover-border-color: #59169c !important;
        --fc-button-active-bg-color: #4c1185 !important;   /* Violeta profundo para botón activo */
        --fc-button-active-border-color: #3e0d6d !important;
        --fc-button-text-color: #ffffff !important;
    }

    /* Botones inactivos (Semana, Agenda, Flechas) */
    .fc .fc-button,
    .fc .fc-button-primary,
    .fc .fc-button-primary:disabled {
        background-color: #6b78ed !important;
        border-color: #7a22cc !important;
        color: #ffffff !important;
        opacity: 1 !important;
        border-radius: 8px !important;
    }

    /* Botón al pasar el cursor (Hover) */
    .fc .fc-button-primary:hover {
        background-color: #6a1bb8 !important;
        border-color: #59169c !important;
        color: #ffffff !important;
    }

    /* Botón seleccionado / activo (Ejemplo: "Mes") */
    .fc .fc-button-primary.fc-button-active,
    .fc .fc-button-primary:active,
    .fc .fc-button-primary:focus {
        background-color: #4c1185 !important;
        border-color: #3e0d6d !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }

    /* Título del mes */
    .fc-toolbar-title {
        color: #4c1185 !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
        text-transform: lowercase !important;
    }
    .fc-toolbar-title::before {
        content: "📅 ";
        margin-right: 6px;
    }

    /* ENCABEZADO DE LOS DÍAS (Lunes, Martes...) CON FONDO VIOLETA Y TEXTO BLANCO */
    .fc-col-header-cell {
        background-color: #6b78ed !important;
        border-color: #7a22cc !important;
        padding: 12px 0 !important;
    }
    .fc-col-header-cell-cushion {
        color: #ffffff !important;
        font-weight: bold !important;
        text-transform: capitalize !important;
        font-size: 1rem !important;
    }

    /* Cuadrícula interna del calendario */
    .fc-daygrid-body, .fc-scrollgrid-sync-table, .fc-view-harness {
        background-color: #f5f2fd !important;
    }
    .fc-daygrid-day, .fc-theme-standard td, .fc-theme-standard th, .fc-scrollgrid {
        border: 1px solid #e2d9f8 !important;
    }
    .fc-daygrid-day-number {
        color: #4c1185 !important;
        font-weight: bold !important;
        padding: 8px !important;
    }
    .fc-day-today {
        background-color: #eae3fb !important;
    }
    .fc-event {
        border-radius: 10px !important;
        border: none !important;
        padding: 4px 8px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.08) !important;
    }
"""


# ===================================================================
# [SEGMENTO 4]: ESTILOS CSS GLOBALES DE STREAMLIT
# ===================================================================
st.markdown("""
    <style>
    [data-testid="stHeader"] a[href*="github.com"] {
        display: none !important;
        visibility: hidden !important;
    }
    </style>
""", unsafe_allow_html=True)


# ===================================================================
# [SEGMENTO 5]: INICIALIZACIÓN DE SESIÓN Y CONEXIÓN
# ===================================================================
if "menu_opcion" not in st.session_state:
    st.session_state["menu_opcion"] = "🏠 Inicio (Permisos de Hoy)"

if "evento_a_modificar" not in st.session_state:
    st.session_state["evento_a_modificar"] = None

if "cal_key" not in st.session_state:
    st.session_state["cal_key"] = 0

if "evento_seleccionado" not in st.session_state:
    st.session_state["evento_seleccionado"] = None

if "mensaje_accion" not in st.session_state:
    st.session_state["mensaje_accion"] = None

conn = st.connection("gsheets", type=GSheetsConnection)


# ===================================================================
# [SEGMENTO 6]: FUNCIONES DE BASE DE DATOS Y UTILIDADES
# ===================================================================
def fmt_fecha(fecha_val, con_hora=False):
    if pd.isna(fecha_val) or not fecha_val or str(fecha_val).strip() == "":
        return "-"
    try:
        dt = pd.to_datetime(fecha_val)
        if con_hora:
            return dt.strftime("%d/%m/%Y %H:%M")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(fecha_val)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        cols_esperadas = [
            "Empleado", "Tipo", "Fecha_Inicio", "Fecha_Fin", 
            "Observaciones", "Alerta", "Fecha_Creacion", "Fecha_Modificacion"
        ]
        for col in cols_esperadas:
            if col not in df.columns:
                df[col] = ""

        if not df.empty:
            df["Fecha_Inicio"] = pd.to_datetime(df["Fecha_Inicio"]).dt.date
            df["Fecha_Fin"] = pd.to_datetime(df["Fecha_Fin"]).dt.date
            
        return df[cols_esperadas]
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame(columns=[
            "Empleado", "Tipo", "Fecha_Inicio", "Fecha_Fin", 
            "Observaciones", "Alerta", "Fecha_Creacion", "Fecha_Modificacion"
        ])

def guardar_o_actualizar_registro(nuevo_dict, df_actual, idx_editar=None):
    ahora_str = obtener_timestamp_actual()

    if idx_editar is not None and str(idx_editar).isdigit():
        idx_int = int(idx_editar)
        if idx_int in df_actual.index:
            f_creac_orig = df_actual.loc[idx_int, "Fecha_Creacion"]
            if pd.isna(f_creac_orig) or not str(f_creac_orig).strip():
                f_creac_orig = ahora_str
                
            nuevo_dict["Fecha_Creacion"] = str(f_creac_orig)
            nuevo_dict["Fecha_Modificacion"] = ahora_str
            df_actual.loc[idx_int] = nuevo_dict
            df_actualizado = df_actual
        else:
            nuevo_dict["Fecha_Creacion"] = ahora_str
            nuevo_dict["Fecha_Modificacion"] = ahora_str
            df_nuevo = pd.DataFrame([nuevo_dict])
            df_actualizado = pd.concat([df_actual, df_nuevo], ignore_index=True)
    else:
        nuevo_dict["Fecha_Creacion"] = ahora_str
        nuevo_dict["Fecha_Modificacion"] = ahora_str
        df_nuevo = pd.DataFrame([nuevo_dict])
        df_actualizado = pd.concat([df_actual, df_nuevo], ignore_index=True)

    conn.update(data=df_actualizado)

def eliminar_registro(df_actual, idx_eliminar):
    if idx_eliminar is not None and str(idx_eliminar).isdigit():
        idx_int = int(idx_eliminar)
        if idx_int in df_actual.index:
            df_actualizado = df_actual.drop(index=idx_int).reset_index(drop=True)
            conn.update(data=df_actualizado)
            return True
    return False

def mostrar_mensaje_alerta():
    if st.session_state.get("mensaje_accion"):
        tipo, texto = st.session_state["mensaje_accion"]
        if tipo == "success":
            st.success(texto)
        elif tipo == "info":
            st.info(texto)
        elif tipo == "warning":
            st.warning(texto)
        st.session_state["mensaje_accion"] = None

def callback_iniciar_edicion(props):
    st.session_state["evento_a_modificar"] = {
        "id": props.get("id"),
        "Empleado": props.get("empleado"),
        "Tipo": props.get("tipo"),
        "Fecha_Inicio": props.get("fecha_inicio"),
        "Fecha_Fin": props.get("fecha_fin"),
        "Observaciones": props.get("observaciones"),
        "Alerta": props.get("alerta"),
        "Fecha_Creacion": props.get("fecha_creacion"),
        "Fecha_Modificacion": props.get("fecha_modificacion")
    }
    st.session_state["evento_seleccionado"] = None
    st.session_state["cal_key"] += 1
    st.session_state["menu_opcion"] = "➕ Registrar Permiso"
    st.session_state["mensaje_accion"] = ("info", f"✏️ **Acción realizada:** Se cargaron los datos de **{props.get('empleado')}** en el formulario de edición.")

def sincronizar_fecha_fin(key_ini, key_fin):
    if key_ini in st.session_state:
        st.session_state[key_fin] = st.session_state[key_ini]


# ===================================================================
# [SEGMENTO 7]: VISTA 1 - INICIO
# ===================================================================
def vista_inicio(df_permisos):
    mostrar_mensaje_alerta()
    st.title("📋 Control de Ausencias - Inicio")
    hoy = obtener_fecha_actual()
    st.markdown(f"**Fecha actual:** {hoy.strftime('%d/%m/%Y')}")
    st.markdown("---")
    
    st.subheader("👥 Empleados ausentes o con permiso el día de hoy")
    
    if not df_permisos.empty:
        activos_hoy = df_permisos[
            (df_permisos["Fecha_Inicio"] <= hoy) & (df_permisos["Fecha_Fin"] >= hoy)
        ]
        
        if not activos_hoy.empty:
            for idx, row in activos_hoy.iterrows():
                tipo_permiso = row['Tipo']
                f_ini_fmt = fmt_fecha(row['Fecha_Inicio'])
                f_fin_fmt = fmt_fecha(row['Fecha_Fin'])
                
                with st.expander(f"🔴 **{row['Empleado']}** — *{tipo_permiso}*"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Periodo:** Desde {f_ini_fmt} hasta {f_fin_fmt}")
                        st.write(f"**Observaciones:** {row['Observaciones']}")
                    with col2:
                        alerta_txt = str(row['Alerta'])
                        if alerta_txt.strip() and alerta_txt.lower() != "nan" and alerta_txt != "Ninguna":
                            st.warning(f"⚠️ **Alerta / Recordatorio:** {alerta_txt}")
                        else:
                            st.info("Sin alertas activas para este permiso.")
                            
                    st.caption(f"🗓️ *Creado:* {fmt_fecha(row.get('Fecha_Creacion'), con_hora=True)} | *Última Modificación:* {fmt_fecha(row.get('Fecha_Modificacion'), con_hora=True)}")
        else:
            st.success("🎉 No hay ausencias ni permisos registrados para el día de hoy.")
    else:
        st.info("No hay datos registrados en la base de datos de Google Sheets.")


# ===================================================================
# [SEGMENTO 8]: VISTA 2 - REGISTRAR / EDITAR PERMISO
# ===================================================================
def vista_registrar_permiso(df_permisos):
    mostrar_mensaje_alerta()
    st.title("📝 Registrar / Modificar Permiso")
    
    datos_mod = st.session_state.get("evento_a_modificar")
    hoy = obtener_fecha_actual()

    if datos_mod:
        st.info(f"✏️ **Modo Edición activo (Fila {datos_mod.get('id')}):** Modificando datos de **{datos_mod['Empleado']}**.")
        col_canc, col_del, _ = st.columns([0.18, 0.22, 0.60])
        with col_canc:
            if st.button("❌ Cancelar edición", use_container_width=True):
                emp_nom = datos_mod.get('Empleado', '')
                st.session_state["evento_a_modificar"] = None
                st.session_state["mensaje_accion"] = ("info", f"ℹ️ Se canceló la edición del registro de **{emp_nom}**.")
                st.rerun()
        with col_del:
            if st.button("🗑️ Eliminar permiso", type="primary", use_container_width=True):
                emp_nom = datos_mod.get('Empleado', '')
                if eliminar_registro(df_permisos, datos_mod.get("id")):
                    st.session_state["evento_a_modificar"] = None
                    st.session_state["mensaje_accion"] = ("success", f"✅ **Acción realizada:** Se ha eliminado exitosamente el permiso de **{emp_nom}**.")
                    st.rerun()

    idx_editar = datos_mod.get("id") if datos_mod else "nuevo"
    def_empleado = datos_mod.get("Empleado", "") if datos_mod else ""
    def_tipo = str(datos_mod.get("Tipo", "Vacaciones")).strip() if datos_mod else "Vacaciones"
    def_inicio = pd.to_datetime(datos_mod.get("Fecha_Inicio")).date() if datos_mod else hoy
    def_fin = pd.to_datetime(datos_mod.get("Fecha_Fin")).date() if datos_mod else hoy
    def_obs = datos_mod.get("Observaciones", "") if datos_mod else ""
    def_alerta = datos_mod.get("Alerta", "") if datos_mod else ""

    list_tipos = list(PALETA_COLORES.keys())
    
    idx_tipo = 0
    for i, t in enumerate(list_tipos):
        if t.lower() == def_tipo.lower():
            idx_tipo = i
            break

    key_ini = f"f_ini_{idx_editar}"
    key_fin = f"f_fin_{idx_editar}"

    if key_ini not in st.session_state:
        st.session_state[key_ini] = def_inicio
    if key_fin not in st.session_state:
        st.session_state[key_fin] = def_fin

    col1, col2 = st.columns(2)
    
    with col1:
        empleado = st.text_input("Nombre completo del empleado *", value=def_empleado)
        tipo = st.selectbox("Tipo de Permiso / Ausencia *", list_tipos, index=idx_tipo)
        
    with col2:
        fecha_inicio = st.date_input(
            "Fecha de inicio *", 
            format="DD/MM/YYYY",
            key=key_ini,
            on_change=sincronizar_fecha_fin,
            args=(key_ini, key_fin)
        )
        
        fecha_fin = st.date_input(
            "Fecha de fin *", 
            min_value=fecha_inicio,
            format="DD/MM/YYYY",
            key=key_fin
        )

    with st.form(key=f"form_permisos_{idx_editar}", clear_on_submit=False):
        observaciones = st.text_area("Observaciones o motivo:", value=def_obs)
        alerta = st.text_input(
            "Alerta de recordatorio (Opcional):", 
            value=def_alerta,
            placeholder="Ej: Solicitar constancia médica / Llamar a las 10:00 AM"
        )
        
        texto_boton = "💾 Actualizar Permiso Existente" if datos_mod else "💾 Guardar Nuevo Permiso"
        btn_guardar = st.form_submit_button(texto_boton)
        
        if btn_guardar:
            if not empleado.strip():
                st.error("⚠️ Por favor, ingresa el nombre del empleado.")
            else:
                registro_dict = {
                    "Empleado": empleado.strip(),
                    "Tipo": tipo,
                    "Fecha_Inicio": str(fecha_inicio),
                    "Fecha_Fin": str(fecha_fin),
                    "Observaciones": observaciones.strip(),
                    "Alerta": alerta.strip() if alerta.strip() else "Ninguna"
                }
                
                idx_real = datos_mod.get("id") if datos_mod else None
                guardar_o_actualizar_registro(registro_dict, df_permisos, idx_editar=idx_real)
                
                accion_str = "actualizó" if datos_mod else "creó y guardó"
                st.session_state["mensaje_accion"] = ("success", f"✅ **Acción realizada:** Se {accion_str} correctamente el permiso de **{empleado.strip()}** ({tipo}).")
                st.session_state["evento_a_modificar"] = None
                
                if key_ini in st.session_state:
                    del st.session_state[key_ini]
                if key_fin in st.session_state:
                    del st.session_state[key_fin]
                
                st.rerun()


# ===================================================================
# [SEGMENTO 9]: VISTA 3 - CALENDARIO VISUAL (NOMBRES DE DÍAS COMPLETOS)
# ===================================================================
def vista_calendario(df_permisos):
    mostrar_mensaje_alerta()

    st.title("📅 Calendario de Control de Permisos de Empleados")
    st.markdown("---")

    st.subheader("🏷️ Categorías de Permisos")

    cols = st.columns(6)
    for i, (cat, color) in enumerate(PALETA_COLORES.items()):
        icono = ICONOS_CATEGORIAS.get(cat, "📌")
        cols[i].markdown(
            f"""
            <div style="
                background-color: white; 
                padding: 10px 14px; 
                border-radius: 12px; 
                border: 1px solid #EAEAEA; 
                text-align: center; 
                box-shadow: 0px 2px 5px rgba(0,0,0,0.03);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            ">
                <span style="background-color: {color}; color: white; padding: 6px 10px; border-radius: 8px; font-size: 16px;">{icono}</span>
                <span style="font-size: 15px; font-weight: 800; color: #2D006B;">{cat}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.get("evento_seleccionado"):
        props = st.session_state["evento_seleccionado"]
        f_ini_fmt = fmt_fecha(props.get('fecha_inicio'))
        f_fin_fmt = fmt_fecha(props.get('fecha_fin'))

        st.info("🔎 **Detalle del permiso seleccionado:**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Empleado:** {props.get('empleado')}")
            st.write(f"**Categoría:** {props.get('tipo')}")
            st.write(f"**Periodo:** {f_ini_fmt} al {f_fin_fmt}")
        with col_b:
            st.write(f"**Observaciones:** {props.get('observaciones')}")
            alerta_evt = str(props.get('alerta'))
            if alerta_evt and alerta_evt != "Ninguna" and alerta_evt.lower() != "nan":
                st.warning(f"⚠️ **Alerta:** {alerta_evt}")

        col_mod, col_elim, col_cerrar, _ = st.columns([0.15, 0.15, 0.12, 0.58])
        with col_mod:
            st.button("✏️ Modificar", key="btn_mod_si", use_container_width=True, on_click=callback_iniciar_edicion, args=(props,))
        with col_elim:
            if st.button("🗑️ Eliminar", key="btn_elim_si", type="primary", use_container_width=True):
                emp_nom = props.get("empleado")
                if eliminar_registro(df_permisos, props.get("id")):
                    st.session_state["evento_seleccionado"] = None
                    st.session_state["cal_key"] += 1
                    st.session_state["mensaje_accion"] = ("success", f"🗑️ **Acción realizada:** Se eliminó correctamente el permiso de **{emp_nom}**.")
                    st.rerun()
        with col_cerrar:
            if st.button("❌ Cerrar", key="btn_mod_no", use_container_width=True):
                st.session_state["evento_seleccionado"] = None
                st.session_state["cal_key"] += 1
                st.rerun()

        st.markdown("---")

    if not df_permisos.empty:
        eventos = []
        for idx, row in df_permisos.iterrows():
            f_inicio = str(row['Fecha_Inicio'])
            f_fin_cal = str(pd.to_datetime(row['Fecha_Fin']) + pd.Timedelta(days=1))[:10]
            icono = ICONOS_CATEGORIAS.get(row['Tipo'], '📌')

            eventos.append({
                "id": str(idx),
                "title": f"{icono} {row['Empleado']} ({row['Tipo']})",
                "start": f_inicio,
                "end": f_fin_cal,
                "backgroundColor": PALETA_COLORES.get(row['Tipo'], "#8A2BE2"),
                "borderColor": PALETA_COLORES.get(row['Tipo'], "#8A2BE2"),
                "textColor": "#FFFFFF",
                "extendedProps": {
                    "id": str(idx),
                    "empleado": str(row['Empleado']),
                    "tipo": str(row['Tipo']),
                    "fecha_inicio": f_inicio,
                    "fecha_fin": str(row['Fecha_Fin']),
                    "observaciones": str(row.get('Observaciones', '')),
                    "alerta": str(row.get('Alerta', 'Ninguna')),
                    "fecha_creacion": str(row.get('Fecha_Creacion', '')),
                    "fecha_modificacion": str(row.get('Fecha_Modificacion', ''))
                }
            })
            
        opciones_cal = {
            "locale": "es",
            "dayHeaderFormat": {"weekday": "long"},  # <-- Muestra el nombre del día completo (Lunes, Martes...)
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,listMonth"
            },
            "buttonText": {
                "today": "🗓️ Hoy",
                "month": "Mes",
                "week": "Semana",
                "list": "Agenda"
            },
            "initialView": "dayGridMonth",
            "selectable": True
        }
        
        key_actual = f"cal_permisos_{st.session_state['cal_key']}"
        
        st.markdown(f"<style>{CSS_CALENDARIO_PERSONALIZADO}</style>", unsafe_allow_html=True)
        
        cal_resultado = calendar(
            events=eventos, 
            options=opciones_cal,
            custom_css=CSS_CALENDARIO_PERSONALIZADO,
            key=key_actual
        )
        
        if cal_resultado and "eventClick" in cal_resultado:
            evento_info = cal_resultado["eventClick"]["event"]
            props = evento_info.get("extendedProps", {})
            if st.session_state.get("evento_seleccionado") != props:
                st.session_state["evento_seleccionado"] = props
                st.rerun()
    else:
        st.info("No hay permisos registrados para mostrar en el calendario.")


# ===================================================================
# [SEGMENTO 10]: VISTA 4 - HISTORIAL COMPLETO (FILTROS Y EXCEL)
# ===================================================================
def vista_historial(df_permisos):
    mostrar_mensaje_alerta()
    st.title("📂 Historial Completo de Permisos")
    st.write("Consulta, filtra y descarga el registro histórico de ausencias.")
    
    if not df_permisos.empty:
        df_filtrado = df_permisos.copy()
        df_filtrado["_dt_inicio"] = pd.to_datetime(df_filtrado["Fecha_Inicio"], errors="coerce")

        st.subheader("🔍 Filtros de Búsqueda")
        col_filtro_mes, col_filtro_tipo = st.columns(2)

        with col_filtro_mes:
            df_filtrado["_mes_año"] = df_filtrado["_dt_inicio"].dt.strftime("%m/%Y")
            meses_disponibles = sorted(
                [m for m in df_filtrado["_mes_año"].unique() if pd.notna(m)],
                reverse=True
            )
            opciones_mes = ["Todos los meses"] + meses_disponibles
            mes_seleccionado = st.selectbox("Filtrar por Mes (MM/YYYY):", opciones_mes)

        with col_filtro_tipo:
            tipos_disponibles = list(PALETA_COLORES.keys())
            opciones_tipo = ["Todos los tipos"] + tipos_disponibles
            tipo_seleccionado = st.selectbox("Filtrar por Tipo de Permiso:", opciones_tipo)

        if mes_seleccionado != "Todos los meses":
            df_filtrado = df_filtrado[df_filtrado["_mes_año"] == mes_seleccionado]

        if tipo_seleccionado != "Todos los tipos":
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == tipo_seleccionado]

        cols_limpias = [col for col in df_permisos.columns if not col.startswith("_")]
        df_mostrar = df_filtrado[cols_limpias].copy()

        df_vista = df_mostrar.copy()
        df_vista["Fecha_Inicio"] = df_vista["Fecha_Inicio"].apply(fmt_fecha)
        df_vista["Fecha_Fin"] = df_vista["Fecha_Fin"].apply(fmt_fecha)
        df_vista["Fecha_Creacion"] = df_vista["Fecha_Creacion"].apply(lambda x: fmt_fecha(x, con_hora=True))
        df_vista["Fecha_Modificacion"] = df_vista["Fecha_Modificacion"].apply(lambda x: fmt_fecha(x, con_hora=True))

        st.markdown(f"**Registros encontrados:** `{len(df_vista)}`")
        st.dataframe(df_vista, use_container_width=True)

        if not df_mostrar.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_mostrar.to_excel(writer, index=False, sheet_name="Historial_Permisos")
            
            st.download_button(
                label="📥 Descargar reporte en Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"historial_permisos_{obtener_fecha_actual().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
    else:
        st.info("No hay registros almacenados actualmente.")


# ===================================================================
# [SEGMENTO 11]: CONTROLADOR PRINCIPAL Y MENÚ DE NAVEGACIÓN
# ===================================================================
def main():
    st.sidebar.title("📌 Menú de Navegación")
    
    opciones_menu = [
        "🏠 Inicio (Permisos de Hoy)", 
        "➕ Registrar Permiso", 
        "📅 Calendario Visual", 
        "📂 Historial Completo"
    ]

    opcion = st.sidebar.radio(
        "Selecciona una sección:",
        opciones_menu,
        key="menu_opcion"
    )
    
    df_permisos = cargar_datos()

    if opcion == "🏠 Inicio (Permisos de Hoy)":
        vista_inicio(df_permisos)
    elif opcion == "➕ Registrar Permiso":
        vista_registrar_permiso(df_permisos)
    elif opcion == "📅 Calendario Visual":
        vista_calendario(df_permisos)
    elif opcion == "📂 Historial Completo":
        vista_historial(df_permisos)

if __name__ == "__main__":
    main()
