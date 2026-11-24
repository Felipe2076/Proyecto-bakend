package cl.laserena.siged.movil

import org.json.JSONObject
import java.time.LocalDate
import java.util.UUID

/** Borrador de la actividad que el funcionario está registrando desde la app (sobrevive al ir a la cámara). */
internal class BorradorActividad {
    val clientId: String = UUID.randomUUID().toString()  // evita duplicados si se reintenta el envío
    var meta: String = ""
    var tipo: String = "RESULTADO"
    var fecha: LocalDate = LocalDate.now()
    var servicio: String = ""
    var contacto: String = ""
    var archivo: ByteArray? = null
    var extension: String = "jpg"

    fun campos() = mapOf(
        "client_id" to clientId, "meta" to meta, "tipo_registro" to tipo, "fecha_actividad" to fecha.toString(),
        "servicio" to servicio.trim(), "contacto" to contacto.trim(),
    )

    /** Mensaje del primer dato que falta, o null si se puede enviar. */
    fun falta(): String? = when {
        meta.isBlank() -> "Elija el ítem o meta de la actividad."
        servicio.trim().length < 5 -> "Describa el servicio realizado (al menos 5 letras)."
        contacto.trim().length < 3 -> "Indique con quién se realizó (contacto)."
        archivo == null -> "Adjunte una foto o un documento como evidencia."
        else -> null
    }
}

internal object TiposRegistro {
    val opciones = listOf("RESULTADO" to "Resultado realizado", "COORDINACION" to "Coordinación / seguimiento")
}

/** Ítems asignados al funcionario tal como los entrega GET /api/v1/panel/. */
internal fun metasDe(panel: JSONObject): List<Pair<String, String>> {
    val lista = panel.optJSONArray("metas") ?: return emptyList()
    return (0 until lista.length()).map { lista.getJSONObject(it) }.map { it.optString("codigo") to it.optString("nombre") }
}
