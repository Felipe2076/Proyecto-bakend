package cl.laserena.siged.movil

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/** Error del servidor con su código HTTP y un mensaje en español listo para mostrar. */
internal class ApiFailure(val status: Int, message: String) : IOException(message)

/**
 * Cliente de la API v1 de SIGED (sin librerías externas).
 * Solo HTTPS; en depuración permite HTTP hacia el emulador (10.0.2.2) para probar un Django local.
 */
internal class Api {
    @Volatile var token = ""
    val base = BuildConfig.BASE_URL.trimEnd('/')

    fun get(path: String): JSONObject = parse(request("GET", path, null, null))

    fun post(path: String, body: JSONObject = JSONObject()): JSONObject =
        parse(request("POST", path, body.toString().toByteArray(Charsets.UTF_8), "application/json"))

    fun delete(path: String): JSONObject = parse(request("DELETE", path, null, null))

    /** Envía un archivo (multipart) en el campo [field]. [ext]: jpg, png o pdf. */
    fun upload(path: String, field: String, file: ByteArray, ext: String, extra: Map<String, String> = emptyMap()): JSONObject {
        require(ext in setOf("png", "jpg", "pdf"))
        val boundary = "siged-" + UUID.randomUUID()
        val out = ByteArrayOutputStream()
        fun line(s: String) = out.write(s.toByteArray(Charsets.UTF_8))
        for ((key, value) in extra) {
            line("--$boundary\r\nContent-Disposition: form-data; name=\"$key\"\r\n\r\n$value\r\n")
        }
        val mime = when (ext) { "png" -> "image/png"; "pdf" -> "application/pdf"; else -> "image/jpeg" }
        line("--$boundary\r\nContent-Disposition: form-data; name=\"$field\"; filename=\"archivo.$ext\"\r\nContent-Type: $mime\r\n\r\n")
        out.write(file); line("\r\n--$boundary--\r\n")
        return parse(request("POST", path, out.toByteArray(), "multipart/form-data; boundary=$boundary"))
    }

    /** Descarga binaria autenticada (fotos de perfil, evidencias). */
    fun file(path: String): ByteArray = request("GET", path, null, null)

    private fun parse(bytes: ByteArray) = JSONObject(bytes.toString(Charsets.UTF_8))

    private fun request(method: String, path: String, body: ByteArray?, type: String?): ByteArray {
        require(path.startsWith("/api/v1/") && !path.contains("\\") && !path.contains(".."))
        val url = URL(base + path)
        check(url.protocol == "https" || (BuildConfig.DEBUG && url.protocol == "http" && url.host in setOf("10.0.2.2", "127.0.0.1", BuildConfig.TEST_HOST)))
        val con = url.openConnection() as HttpURLConnection
        try {
            con.instanceFollowRedirects = false; con.useCaches = false
            con.connectTimeout = 12000; con.readTimeout = 30000
            con.requestMethod = method
            con.setRequestProperty("Accept", "application/json, application/octet-stream")
            con.setRequestProperty("User-Agent", "SIGED-Movil/${BuildConfig.VERSION_NAME} Android")
            if (token.isNotEmpty()) con.setRequestProperty("Authorization", "Bearer $token")
            if (body != null) {
                con.doOutput = true; con.setRequestProperty("Content-Type", type)
                con.setFixedLengthStreamingMode(body.size)
                con.outputStream.use { it.write(body) }
            }
            val status = con.responseCode
            if (status !in 200..299) {
                val raw = con.errorStream?.use { readLimited(it, 128 * 1024) }?.toString(Charsets.UTF_8).orEmpty()
                val message = try {
                    val e = JSONObject(raw); val campos = e.optJSONObject("campos")
                    val detalle = campos?.keys()?.asSequence()?.map { k ->
                        val v = campos.opt(k)
                        if (v is org.json.JSONArray) (0 until v.length()).joinToString(" ") { i ->
                            v.optJSONObject(i)?.optString("message") ?: v.optString(i) } else v.toString()
                    }?.joinToString("\n")
                    listOf(e.optString("error"), detalle.orEmpty()).filter { it.isNotBlank() }.distinct().joinToString("\n")
                        .ifBlank { "El servidor respondió $status." }
                } catch (_: Exception) {
                    when (status) { 413 -> "El archivo supera el límite del servidor."; 502, 503, 504 -> "El servidor no está disponible. Intente más tarde."; else -> "El servidor respondió $status." }
                }
                throw ApiFailure(status, message)
            }
            return con.inputStream.use { readLimited(it, 24 * 1024 * 1024) }
        } catch (e: java.net.UnknownHostException) {
            throw IOException("Sin conexión a Internet.")
        } catch (e: java.net.SocketTimeoutException) {
            throw IOException("El servidor tardó demasiado en responder.")
        } finally { con.disconnect() }
    }
}

internal fun readLimited(input: java.io.InputStream, limit: Int): ByteArray {
    val out = ByteArrayOutputStream(); val buffer = ByteArray(8192)
    while (true) {
        val n = input.read(buffer); if (n < 0) break
        if (out.size() + n > limit) throw IOException("El archivo supera el tamaño permitido.")
        out.write(buffer, 0, n)
    }
    return out.toByteArray()
}
