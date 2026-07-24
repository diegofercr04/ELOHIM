import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from modulos.config.conexion import get_connection

SV_TZ = pytz.timezone("America/El_Salvador")


def mostrar():
    st.title("💰 Arqueo de Caja")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    fecha = st.date_input("Seleccionar fecha", value=datetime.now(SV_TZ).date())
    st.divider()

    # ── Ventas del día ───────────────────────────────────────────
    df_ventas_met = pd.read_sql("""
        SELECT metodo_pago,
               SUM(total) AS total_ingresado,
               COUNT(*)   AS num_ventas
        FROM VENTAS
        WHERE DATE(fecha) = %s
        GROUP BY metodo_pago""", conn, params=(str(fecha),))

    efectivo      = df_ventas_met[df_ventas_met["metodo_pago"]=="efectivo"]["total_ingresado"].sum()
    transferencia = df_ventas_met[df_ventas_met["metodo_pago"]=="transferencia"]["total_ingresado"].sum()
    total_ventas  = efectivo + transferencia

    # ── Compras completadas del día ──────────────────────────────
    df_compras_dia = pd.read_sql("""
        SELECT COALESCE(SUM(cantidad * precio_unitario), 0) AS total_compras,
               COUNT(*) AS num_compras
        FROM COMPRAS
        WHERE DATE(fecha) = %s AND estado = 'completada'""",
        conn, params=(str(fecha),))
    total_compras = float(df_compras_dia["total_compras"].iloc[0])
    num_compras   = int(df_compras_dia["num_compras"].iloc[0])

    # ── Retiros del día ──────────────────────────────────────────
    df_retiros_dia = pd.read_sql("""
        SELECT COALESCE(SUM(monto), 0) AS total_retiros,
               COUNT(*) AS num_retiros
        FROM RETIROS_CAJA
        WHERE DATE(fecha) = %s""",
        conn, params=(str(fecha),))
    total_retiros = float(df_retiros_dia["total_retiros"].iloc[0])
    num_retiros   = int(df_retiros_dia["num_retiros"].iloc[0])

    # ── Balance neto ─────────────────────────────────────────────
    beneficio_neto = total_ventas - total_compras - total_retiros

    # ── Métricas ─────────────────────────────────────────────────
    st.subheader("📊 Resumen del día")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💵 Efectivo",       f"${efectivo:.2f}")
    c2.metric("🏦 Transferencias", f"${transferencia:.2f}")
    c3.metric("📦 Total ventas",   f"${total_ventas:.2f}")
    c4.metric("🛒 Total compras",  f"${total_compras:.2f}")
    c5.metric("💸 Retiros",        f"${total_retiros:.2f}",
             delta=f"-${total_retiros:.2f}" if total_retiros > 0 else None,
             delta_color="inverse")

    st.divider()

    # ── Balance neto destacado ───────────────────────────────────
    if beneficio_neto >= 0:
        st.success(
            f"✅ Beneficio neto del día: **${beneficio_neto:.2f}**  \n"
            f"*(Ventas ${total_ventas:.2f} − Compras ${total_compras:.2f} − Retiros ${total_retiros:.2f})*"
        )
    else:
        st.error(
            f"⚠️ Balance negativo del día: **${beneficio_neto:.2f}**  \n"
            f"*(Ventas ${total_ventas:.2f} − Compras ${total_compras:.2f} − Retiros ${total_retiros:.2f})*"
        )

    st.divider()

    # ── Registrar retiro ─────────────────────────────────────────
    st.subheader("💸 Registrar retiro de dinero")
    st.caption("Úsalo cuando se retire dinero de caja para gastos o uso personal.")

    cr1, cr2 = st.columns([1, 2])
    with cr1:
        monto_retiro = st.number_input(
            "Monto a retirar ($)",
            min_value=0.01, format="%.2f", key="retiro_monto"
        )
    with cr2:
        descripcion_retiro = st.text_input(
            "Descripción / motivo",
            placeholder="Ej: pago de servicio, gastos personales...",
            key="retiro_desc"
        )

    if st.button("💸 Registrar retiro", use_container_width=True,
                 type="primary", key="btn_retiro"):
        if not descripcion_retiro:
            st.error("Por favor escribe una descripción del motivo.")
        else:
            ahora_sv = datetime.now(SV_TZ)
            cursor   = conn.cursor()
            cursor.execute(
                "INSERT INTO RETIROS_CAJA (monto, descripcion, usuario_id, fecha) VALUES (%s,%s,%s,%s)",
                (monto_retiro, descripcion_retiro,
                 st.session_state.get("usuario_id"), ahora_sv)
            )
            conn.commit()
            st.success(f"✅ Retiro de **${monto_retiro:.2f}** registrado correctamente.")
            st.rerun()

    st.divider()

    # ── Detalle de retiros del día ───────────────────────────────
    st.subheader("💸 Retiros del día")
    conn2 = get_connection()
    df_retiros = pd.read_sql("""
        SELECT r.id, r.fecha, r.monto, r.descripcion,
               u.usuario AS registrado_por
        FROM RETIROS_CAJA r
        JOIN USUARIO u ON r.usuario_id = u.id
        WHERE DATE(r.fecha) = %s
        ORDER BY r.fecha DESC""",
        conn2, params=(str(fecha),))
    if df_retiros.empty:
        st.info("No hay retiros registrados en este día.")
    else:
        st.dataframe(df_retiros, use_container_width=True)
    conn2.close()

    st.divider()

    # ── Detalle ventas del día ───────────────────────────────────
    st.subheader("🧾 Ventas del día")
    conn3 = get_connection()
    df_ventas = pd.read_sql("""
        SELECT v.id, v.fecha, v.total, v.metodo_pago,
               GROUP_CONCAT(p.nombre SEPARATOR ', ') AS productos
        FROM VENTAS v
        JOIN DETALLE_VENTA dv ON dv.id_venta   = v.id
        JOIN PRODUCTOS     p  ON dv.id_producto = p.id
        WHERE DATE(v.fecha) = %s
        GROUP BY v.id ORDER BY v.fecha DESC""",
        conn3, params=(str(fecha),))
    st.dataframe(df_ventas, use_container_width=True)
    conn3.close()

    # ── Detalle compras del día ──────────────────────────────────
    st.subheader("🛒 Compras completadas del día")
    conn4 = get_connection()
    df_compras = pd.read_sql("""
        SELECT c.id, p.empresa AS proveedor, pr.nombre AS producto,
               c.cantidad, c.precio_unitario,
               (c.cantidad * c.precio_unitario) AS total, c.fecha
        FROM COMPRAS c
        JOIN PROVEEDORES p  ON c.id_proveedor = p.id
        JOIN PRODUCTOS   pr ON c.id_producto  = pr.id
        WHERE DATE(c.fecha) = %s AND c.estado = 'completada'
        ORDER BY c.fecha DESC""",
        conn4, params=(str(fecha),))
    st.dataframe(df_compras, use_container_width=True)
    st.caption(f"{num_compras} compra(s) — {num_retiros} retiro(s) en este día")
    conn4.close()
    conn.close(
