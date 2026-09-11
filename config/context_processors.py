from cuentas.auth import puede_ver, usuario_sesion
from cuentas.store import cargar_json_seguro


def _notificaciones_base():
    almacenadas = cargar_json_seguro("notificaciones.json", [])
    tickets = cargar_json_seguro("requerimientos.json", [])
    automaticas = []
    for ticket in tickets:
        try:
            dias = int(ticket.get("dias_transcurridos") or 0)
        except (TypeError, ValueError):
            dias = 0
        if dias >= 6 and ticket.get("estado_proceso") != "Resuelto":
            tid = ticket.get("id_ticket")
            automaticas.append(
                {
                    "id": f"AUTO-{tid}",
                    "titulo": f"Ticket crítico {tid}",
                    "mensaje": f"{ticket.get('vecino_nombre')} lleva {dias} días en {ticket.get('delegacion')}.",
                    "tipo": "critico",
                    "fecha": ticket.get("fecha_ingreso"),
                    "enlace": f"/requerimientos/{tid}/",
                }
            )
    return list(almacenadas) + automaticas


def sesion_siged(request):
    usuario = usuario_sesion(request)
    leidas = set(request.session.get("notificaciones_leidas") or [])
    notificaciones = _notificaciones_base()
    pendientes = [item for item in notificaciones if item.get("id") not in leidas]
    return {
        "usuario_actual": usuario,
        "puede_requerimientos": puede_ver(usuario, "requerimientos"),
        "puede_matriz_sgr": puede_ver(usuario, "matriz_sgr"),
        "puede_control_gestion": puede_ver(usuario, "control_gestion"),
        "puede_actividades": puede_ver(usuario, "actividades"),
        "puede_agenda": puede_ver(usuario, "agenda"),
        "puede_compromisos": puede_ver(usuario, "compromisos"),
        "puede_notificaciones": puede_ver(usuario, "notificaciones"),
        "puede_encuestas": puede_ver(usuario, "encuestas"),
        "puede_administracion": puede_ver(usuario, "administracion"),
        "notificaciones_pendientes": len(pendientes),
    }
