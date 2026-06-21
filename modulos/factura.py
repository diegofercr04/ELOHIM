from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io

# ── Datos del negocio (editar según corresponda) ────────────
NEGOCIO = {
    "nombre":    "Ferretería Elohim",
    "direccion": "San Salvador, El Salvador",
    "telefono":  "2222-3333",
    "nit":       "0000-000000-000-0",   # Actualizar al formalizarse
    "nrc":       "00000-0",             # Actualizar al formalizarse
    "giro":      "Venta de materiales de ferretería y construcción",
}

AZUL     = colors.HexColor("#185FA5")
AZUL_CLR = colors.HexColor("#E6F1FB")
GRIS     = colors.HexColor("#F0F4F9")

def generar_factura_pdf(id_venta, items, total, metodo_pago, fecha_hora, vendedor):
    """
    Genera la factura como bytes PDF en memoria.
    Parámetros:
        id_venta   : int   — número de venta
        items      : list  — lista de dicts con nombre, cantidad, precio_unitario
        total      : float — total de la venta
        metodo_pago: str   — 'efectivo' o 'transferencia'
        fecha_hora : datetime
        vendedor   : str   — nombre del usuario que realizó la venta
    """
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm)

    styles  = getSampleStyleSheet()
    story   = []

    estilo_titulo = ParagraphStyle("titulo",
        fontSize=18, textColor=AZUL, alignment=TA_CENTER, fontName="Helvetica-Bold")
    estilo_sub = ParagraphStyle("sub",
        fontSize=10, textColor=colors.grey, alignment=TA_CENTER)
    estilo_normal = ParagraphStyle("normal",
        fontSize=9, leading=14, fontName="Helvetica")
    estilo_der = ParagraphStyle("der",
        fontSize=9, alignment=TA_RIGHT, fontName="Helvetica")
    estilo_bold = ParagraphStyle("bold",
        fontSize=10, fontName="Helvetica-Bold")

    # ── Encabezado ───────────────────────────────────────────────
    story.append(Paragraph(NEGOCIO["nombre"], estilo_titulo))
    story.append(Paragraph(NEGOCIO["direccion"], estilo_sub))
    story.append(Paragraph(f"Tel: {NEGOCIO['telefono']}", estilo_sub))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=AZUL))
    story.append(Spacer(1, 0.3*cm))

    # ── Datos de la factura ──────────────────────────────────────
    datos_factura = [
        [Paragraph(f"<b>FACTURA No. {id_venta:05d}</b>", estilo_bold),
         Paragraph(f"Fecha: {fecha_hora.strftime('%d/%m/%Y %H:%M')}", estilo_der)],
        [Paragraph(f"NIT: {NEGOCIO['nit']}  |  NRC: {NEGOCIO['nrc']}", estilo_normal),
         Paragraph(f"Atendido por: {vendedor}", estilo_der)],
        [Paragraph(f"Giro: {NEGOCIO['giro']}", estilo_normal),
         Paragraph(f"Pago: {metodo_pago.capitalize()}", estilo_der)],
    ]
    tabla_header = Table(datos_factura, colWidths=[10*cm, 7*cm])
    tabla_header.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(tabla_header)
    story.append(Spacer(1, 0.4*cm))

    # ── Tabla de productos ───────────────────────────────────────
    encabezados = ["#", "Producto", "Cantidad", "Precio unit.", "Subtotal"]
    filas = [encabezados]
    for i, item in enumerate(items, 1):
        subtotal = item["cantidad"] * item["precio_unitario"]
        filas.append([
            str(i),
            item["nombre"],
            str(item["cantidad"]),
            f"${item['precio_unitario']:.2f}",
            f"${subtotal:.2f}"
        ])

    # Fila de total
    filas.append(["", "", "", "TOTAL", f"${total:.2f}"])

    tabla_prod = Table(filas, colWidths=[1*cm, 8*cm, 2.5*cm, 3*cm, 2.5*cm])
    tabla_prod.setStyle(TableStyle([
        # Encabezado azul
        ("BACKGROUND",   (0,0), (-1,0), AZUL),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0), 9),
        ("ALIGN",        (0,0), (-1,0), "CENTER"),
        # Filas alternas
        *[("BACKGROUND", (0,i), (-1,i), GRIS)
          for i in range(2, len(filas)-1, 2)],
        # Fila de total
        ("BACKGROUND",   (0,-1), (-1,-1), AZUL_CLR),
        ("FONTNAME",     (3,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,1), (-1,-1), 9),
        ("ALIGN",        (2,1), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, GRIS]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.lightgrey),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ]))
    story.append(tabla_prod)
    story.append(Spacer(1, 0.5*cm))

    # ── Campos fiscales (preparados para el próximo año) ─────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<i>Documento de control interno. "
        "La emisión de Factura de Consumidor Final y Crédito Fiscal "
        "estará disponible próximamente.</i>",
        estilo_normal))
    story.append(Spacer(1, 0.4*cm))

    # ── Pie de página ────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL))
    story.append(Paragraph(
        "¡Gracias por su compra! — Ferretería Elohim", estilo_sub))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
