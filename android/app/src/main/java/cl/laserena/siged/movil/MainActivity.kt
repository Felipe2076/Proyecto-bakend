package cl.laserena.siged.movil

import android.app.AlertDialog
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import android.os.Bundle
import android.os.CountDownTimer
import android.text.InputFilter
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import androidx.core.graphics.drawable.RoundedBitmapDrawableFactory
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException
import java.time.OffsetDateTime
import java.util.concurrent.Executors

/**
 * SIGED Móvil del funcionario municipal.
 *
 * Ingreso con RUT, recuperación de contraseña con código por correo, perfil con foto, trimestre y día en curso,
 * asistencia, actividades del tubo por estado y subida de evidencias (foto o documento).
 * Diseño propio: íconos vectoriales SIGED (res/drawable/ic_*), degradado municipal animado y entradas escalonadas.
 */
class MainActivity : ComponentActivity() {
    private val api = Api()
    private lateinit var vault: Vault
    private lateinit var ui: Ui
    private val io = Executors.newSingleThreadExecutor()
    private var sesion: JSONObject? = null
    private var trabajo: JSONObject? = null
    private var filtro = "TODOS"
    private var volver: (() -> Unit)? = null
    private var ocupado = false
    private lateinit var raiz: FrameLayout
    private var insetArriba = 0
    private lateinit var barraEstado: View

    private var destinoArchivo: String? = null
    private var archivoCamara: File? = null

    private val elegirArchivo = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        val destino = destinoArchivo
        if (uri != null && destino != null) procesarArchivo(uri, destino)
    }
    private val tomarFoto = registerForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        val f = archivoCamara; val destino = destinoArchivo
        archivoCamara = null
        if (ok && f != null && destino != null) procesarArchivo(uriDe(f), destino) { f.delete() } else f?.delete()
    }

    private val perfil get() = trabajo?.optJSONObject("perfil") ?: sesion?.optJSONObject("perfil") ?: JSONObject()
    private val cuenta get() = sesion?.optJSONObject("perfil")?.optString("funcionario").orEmpty().ifBlank { "cuenta" }

    override fun onCreate(estado: Bundle?) {
        super.onCreate(estado)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor = android.graphics.Color.TRANSPARENT
        vault = Vault(this); ui = Ui(this)
        raiz = FrameLayout(this).apply { setBackgroundColor(Colores.fondo) }
        setContentView(raiz)
        // Franja bajo la hora y la batería: el contenido que se desplaza no queda debajo de los íconos del sistema.
        barraEstado = View(this).apply { tag = "fijo"; setBackgroundColor(Colores.vinoOscuro); elevation = ui.dp(12).toFloat() }
        raiz.addView(barraEstado, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0))
        // La barra de estado queda sobre el degradado: solo se reserva el espacio inferior y el del teclado.
        ViewCompat.setOnApplyWindowInsetsListener(raiz) { v, insets ->
            val b = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime())
            insetArriba = b.top
            v.setPadding(b.left, 0, b.right, b.bottom)
            barraEstado.layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, b.top)
            v.findViewWithTag<View>("arriba")?.let { it.setPadding(it.paddingLeft, insetArriba + ui.dp(18), it.paddingRight, it.paddingBottom) }
            insets
        }
        archivoCamara = estado?.getString("camara")?.let { File(cacheDir, "camara/$it") }
        destinoArchivo = estado?.getString("destino")
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (ocupado) return
                volver?.invoke() ?: finish()
            }
        })
        sesion = vault.session()
        api.token = sesion?.optString("token").orEmpty()
        if (api.token.isBlank()) pantallaLogin() else {
            trabajo = vault.work(cuenta)
            if (trabajo != null) pantallaInicio() else pantallaCarga("Cargando su información…")
            renovarSiCorresponde(); cargarTrabajo()
        }
    }

    override fun onSaveInstanceState(out: Bundle) {
        super.onSaveInstanceState(out)
        out.putString("camara", archivoCamara?.name); out.putString("destino", destinoArchivo)
    }

    override fun onDestroy() { io.shutdown(); super.onDestroy() }

    // ------------------------------------------------------------------ infraestructura
    /** Cambia de pantalla con un deslizamiento suave; [atras] invierte la dirección. */
    private fun mostrar(contenido: View, alVolver: (() -> Unit)?, atras: Boolean = false, animar: Boolean = true) {
        volver = alVolver
        val d = ui.dp(36).toFloat() * (if (atras) -1 else 1)
        // Todas las pantallas anteriores salen; las que ya iban saliendo se quitan de inmediato
        // (si no, dos cambios seguidos dejaban una pantalla pegada detrás de la nueva).
        for (i in raiz.childCount - 1 downTo 0) {
            val v = raiz.getChildAt(i)
            if (v.tag == "fijo") continue
            if (v.tag == "saliendo" || !animar) { v.animate().cancel(); raiz.removeView(v); continue }
            v.tag = "saliendo"
            v.animate().alpha(0f).translationX(-d / 2).setDuration(200).withEndAction { raiz.removeView(v) }.start()
        }
        if (animar) { contenido.alpha = 0f; contenido.translationX = d }
        raiz.addView(contenido, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        if (animar) contenido.animate().alpha(1f).translationX(0f).setDuration(300).setInterpolator(DecelerateInterpolator(2f)).start()
        barraEstado.bringToFront()
        contenido.findViewWithTag<View>("arriba")?.let { it.setPadding(it.paddingLeft, insetArriba + ui.dp(18), it.paddingRight, it.paddingBottom) }
    }

    private fun desplazable(contenido: View) = ScrollView(this).apply {
        isFillViewport = true; isVerticalScrollBarEnabled = false; overScrollMode = View.OVER_SCROLL_NEVER; addView(contenido)
    }

    private fun <T> enSegundoPlano(tarea: () -> T, listo: (T) -> Unit, error: (Exception) -> Unit = { avisar(it) }) {
        io.execute {
            try { val r = tarea(); runOnUiThread { if (!isFinishing) listo(r) } }
            catch (e: Exception) { runOnUiThread { if (!isFinishing) { if (e is ApiFailure && e.status == 401 && api.token.isNotBlank()) sesionVencida() else error(e) } } }
        }
    }

    private fun avisar(e: Exception) {
        val mensaje = e.message?.takeIf { it.isNotBlank() } ?: "No se pudo completar la operación."
        redondear(AlertDialog.Builder(this).setTitle("No se pudo completar").setMessage(mensaje).setPositiveButton("Entendido", null).show())
    }

    /** Diálogo con esquinas redondeadas y botones en el rojo municipal, a juego con el resto de la app. */
    private fun redondear(d: AlertDialog) {
        d.window?.setBackgroundDrawable(android.graphics.drawable.InsetDrawable(ui.forma(Colores.blanco, 24), ui.dp(24)))
        for (b in listOf(AlertDialog.BUTTON_POSITIVE, AlertDialog.BUTTON_NEGATIVE)) d.getButton(b)?.apply { setTextColor(Colores.rojo); isAllCaps = false; typeface = Letras.medio; textSize = 15f }
    }

    private fun sesionVencida() {
        api.token = ""; sesion = null; trabajo = null; vault.clearSession()
        pantallaLogin("Su sesión terminó. Ingrese nuevamente.")
    }

    /** Muestra un mensaje de error con un pequeño temblor para llamar la atención. */
    private fun error(tv: TextView, mensaje: String?) {
        tv.text = mensaje ?: "No se pudo completar la operación."; tv.visibility = View.VISIBLE
        tv.translationX = 0f
        tv.animate().translationX(ui.dp(8).toFloat()).setDuration(60).withEndAction {
            tv.animate().translationX(-ui.dp(6).toFloat()).setDuration(60).withEndAction {
                tv.animate().translationX(0f).setDuration(120).setInterpolator(OvershootInterpolator(4f)).start()
            }.start()
        }.start()
    }

    private fun textoError() = ui.texto("", 13.5f, Colores.rojo, true).apply {
        visibility = View.GONE; setPadding(ui.dp(4), ui.dp(8), 0, 0)
        setCompoundDrawablesRelativeWithIntrinsicBounds(R.drawable.ic_alerta, 0, 0, 0); compoundDrawablePadding = ui.dp(6)
        compoundDrawableTintList = android.content.res.ColorStateList.valueOf(Colores.rojo)
    }

    private fun pantallaCarga(texto: String) {
        val marco = FrameLayout(this)
        marco.addView(FondoMarca(this, animado = true, curva = false))
        val c = ui.columna(32).apply { gravity = Gravity.CENTER }
        c.addView(marca(76))
        c.addView(ui.animacion(R.raw.siged_carga, 90).apply { (layoutParams as LinearLayout.LayoutParams).topMargin = ui.dp(18) })
        c.addView(ui.texto(texto, 15f, 0xFFF3E3E6.toInt(), true).apply { gravity = Gravity.CENTER; setPadding(0, ui.dp(8), 0, 0) })
        marco.addView(c)
        mostrar(marco, null)
        ui.entrada((0 until c.childCount).map { c.getChildAt(it) })
    }

    private fun pantallaExito(titulo: String, detalle: String, siguiente: () -> Unit) {
        val c = ui.columna(32).apply { gravity = Gravity.CENTER }
        c.addView(ui.animacion(R.raw.siged_exito, 150, repetir = false))
        c.addView(ui.titulo(titulo, 24f).apply { gravity = Gravity.CENTER; setPadding(0, ui.dp(12), 0, ui.dp(6)) })
        c.addView(ui.texto(detalle, 15f, Colores.gris).apply { gravity = Gravity.CENTER })
        c.addView(ui.margen(ui.boton("Continuar", icono = R.drawable.ic_adelante) { siguiente() }, arriba = 28))
        mostrar(c, siguiente)
        ui.entrada((1 until c.childCount).map { c.getChildAt(it) }, 350)
    }

    private fun cubrir(texto: String): View {
        ocupado = true
        val capa = ui.columna(24).apply {
            gravity = Gravity.CENTER; setBackgroundColor(0xE6F6F3EF.toInt()); isClickable = true; alpha = 0f
            val caja = ui.tarjeta(24).apply { gravity = Gravity.CENTER_HORIZONTAL }
            caja.addView(ui.animacion(R.raw.siged_carga, 84))
            caja.addView(ui.texto(texto, 15f, Colores.tinta, true).apply { gravity = Gravity.CENTER; setPadding(ui.dp(12), ui.dp(8), ui.dp(12), 0) })
            addView(caja, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        raiz.addView(capa, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        capa.animate().alpha(1f).setDuration(180).start()
        return capa
    }

    private fun descubrir(capa: View) { ocupado = false; capa.animate().alpha(0f).setDuration(150).withEndAction { raiz.removeView(capa) }.start() }

    /** Sello SIGED: escudo con visto bueno sobre un círculo de vidrio. */
    private fun marca(tam: Int) = ImageView(this).apply {
        setImageResource(R.drawable.ic_marca); imageTintList = android.content.res.ColorStateList.valueOf(Colores.dorado)
        background = ui.forma(0x26FFFFFF, tam, 0x55F0CE8B); val p = ui.dp(tam) / 5; setPadding(p, p, p, p)
        layoutParams = LinearLayout.LayoutParams(ui.dp(tam), ui.dp(tam)).apply { gravity = Gravity.CENTER_HORIZONTAL }
    }

    /** Cabecera con degradado animado, botón de volver opcional, título y subtítulo. */
    private fun encabezado(titulo: String, subtitulo: String? = null, alVolver: (() -> Unit)? = null, alto: Int = 0): FrameLayout {
        val marco = FrameLayout(this)
        marco.addView(FondoMarca(this, animado = true, curva = true))
        val c = ui.columna().apply { tag = "arriba"; setPadding(ui.dp(20), insetArriba + ui.dp(18), ui.dp(20), ui.dp(34 + alto)) }
        val fila = ui.fila()
        if (alVolver != null) {
            fila.addView(ui.presionable(ImageView(this).apply {
                setImageResource(R.drawable.ic_atras); imageTintList = android.content.res.ColorStateList.valueOf(Colores.blanco)
                background = ui.forma(0x26FFFFFF, 14); val p = ui.dp(8); setPadding(p, p, p, p); contentDescription = "Volver"
                setOnClickListener { alVolver() }
                layoutParams = LinearLayout.LayoutParams(ui.dp(40), ui.dp(40)).apply { marginEnd = ui.dp(12) }
            }))
        }
        fila.addView(ui.texto("SIGED · LA SERENA", 11.5f, Colores.dorado, true).apply { letterSpacing = 0.14f })
        c.addView(fila)
        c.addView(ui.titulo(titulo, 26f, Colores.blanco).apply { setPadding(0, ui.dp(10), 0, 0) })
        if (subtitulo != null) c.addView(ui.texto(subtitulo, 14f, 0xFFF3E3E6.toInt()))
        marco.addView(c)
        return marco
    }

    // ------------------------------------------------------------------ ingreso
    private fun pantallaLogin(mensaje: String? = null) {
        val marco = FrameLayout(this)
        marco.addView(FondoMarca(this, animado = true, curva = false))
        val c = ui.columna(24).apply { gravity = Gravity.CENTER_VERTICAL; tag = "arriba" }
        val logo = marca(84)
        c.addView(logo)
        c.addView(ui.titulo("SIGED Móvil", 32f, Colores.blanco).apply { gravity = Gravity.CENTER; setPadding(0, ui.dp(14), 0, 0) })
        c.addView(ui.texto("Delegaciones municipales · La Serena", 14f, 0xFFF3E3E6.toInt()).apply { gravity = Gravity.CENTER; setPadding(0, 0, 0, ui.dp(24)) })
        val tarjeta = ui.tarjeta(22).apply { elevation = ui.dp(12).toFloat() }
        tarjeta.addView(ui.titulo("Ingresar", 22f))
        tarjeta.addView(ui.texto("Use su RUT y la contraseña de la página web.", 13.5f, Colores.gris))
        if (mensaje != null) tarjeta.addView(ui.insignia(mensaje, Colores.rojo, R.drawable.ic_alerta).apply {
            (layoutParams as LinearLayout.LayoutParams).topMargin = ui.dp(10) })
        tarjeta.addView(ui.etiqueta("RUT"))
        val (cajaRut, rut) = ui.campoIcono(R.drawable.ic_tarjeta_id, "12.345.678-5")
        rut.filters = arrayOf(InputFilter.LengthFilter(12))
        rut.setOnFocusChangeListener { v, foco -> v.onFocusChangeListenerOriginal(foco); if (!foco) rut.setText(formatearRut(rut.text.toString())) }
        tarjeta.addView(cajaRut)
        tarjeta.addView(ui.etiqueta("Contraseña"))
        val ojo = ImageView(this).apply {
            setImageResource(R.drawable.ic_ojo); imageTintList = android.content.res.ColorStateList.valueOf(Colores.gris)
            val p = ui.dp(9); setPadding(p, p, p, p); contentDescription = "Mostrar contraseña"
            layoutParams = LinearLayout.LayoutParams(ui.dp(40), ui.dp(40))
        }
        val (cajaClave, clave) = ui.campoIcono(R.drawable.ic_candado, "Su contraseña", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD, ojo)
        ojo.setOnClickListener {
            val oculta = clave.inputType and InputType.TYPE_TEXT_VARIATION_PASSWORD == InputType.TYPE_TEXT_VARIATION_PASSWORD
            clave.inputType = InputType.TYPE_CLASS_TEXT or (if (oculta) InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD else InputType.TYPE_TEXT_VARIATION_PASSWORD)
            clave.typeface = Letras.normal; clave.setSelection(clave.text.length)
            ojo.imageTintList = android.content.res.ColorStateList.valueOf(if (oculta) Colores.rojo else Colores.gris)
            ojo.animate().scaleX(1.2f).scaleY(1.2f).setDuration(90).withEndAction { ojo.animate().scaleX(1f).scaleY(1f).setDuration(160).start() }.start()
        }
        tarjeta.addView(cajaClave)
        val err = textoError()
        tarjeta.addView(err)
        tarjeta.addView(ui.margen(ui.boton("Ingresar", icono = R.drawable.ic_adelante) {
            val r = formatearRut(rut.text.toString()); val p = clave.text.toString()
            when {
                !rutValido(r) -> error(err, "Revise el RUT y su dígito verificador.")
                p.isEmpty() -> error(err, "Escriba su contraseña.")
                else -> {
                    err.visibility = View.GONE
                    val capa = cubrir("Ingresando…")
                    enSegundoPlano({
                        api.post("/api/v1/sesion/", JSONObject().put("rut", r).put("password", p)
                            .put("dispositivo", "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"))
                    }, { s ->
                        descubrir(capa); sesion = s; api.token = s.optString("token"); vault.session(s)
                        pantallaCarga("Cargando su información…"); cargarTrabajo()
                    }, { e -> descubrir(capa); error(err, e.message) })
                }
            }
        }, arriba = 18, abajo = 4))
        tarjeta.addView(ui.enlace("¿Olvidaste tu contraseña?") { recuperarCorreo() }.apply { gravity = Gravity.CENTER })
        c.addView(tarjeta)
        c.addView(ui.texto("Primer ingreso: active su cuenta con el enlace que llegó a su correo.", 12f, 0xFFF3E3E6.toInt())
            .apply { gravity = Gravity.CENTER; setPadding(0, ui.dp(16), 0, 0) })
        marco.addView(desplazable(c))
        mostrar(marco, null)
        logo.scaleX = 0.4f; logo.scaleY = 0.4f
        logo.animate().scaleX(1f).scaleY(1f).setDuration(650).setInterpolator(OvershootInterpolator(2.2f)).start()
        ui.entrada((1 until c.childCount).map { c.getChildAt(it) }, 150)
    }

    /** Conserva el resaltado del campo con ícono cuando se agrega otro oyente de foco. */
    private fun View.onFocusChangeListenerOriginal(foco: Boolean) {
        val caja = parent as? LinearLayout ?: return
        caja.background = ui.forma(if (foco) Colores.blanco else Colores.fondo, 16, if (foco) Colores.rojo else Colores.borde)
        (caja.getChildAt(0) as? ImageView)?.imageTintList = android.content.res.ColorStateList.valueOf(if (foco) Colores.rojo else Colores.gris)
    }

    // ------------------------------------------------------------------ recuperar contraseña (tres pasos)
    private fun pasoRecuperacion(paso: Int, titulo: String, detalle: String, icono: Int, alVolver: () -> Unit): LinearLayout {
        val c = ui.columna()
        c.addView(encabezado("Recuperar contraseña", "Paso $paso de 3 · $titulo", alVolver))
        val cuerpo = ui.columna(20)
        val pasos = ui.fila().apply { setPadding(0, 0, 0, ui.dp(18)) }
        for (i in 1..3) {
            val seg = View(this).apply { background = ui.forma(if (i <= paso) Colores.rojo else Colores.borde, 4) }
            pasos.addView(seg, LinearLayout.LayoutParams(0, ui.dp(6), 1f).apply { if (i < 3) marginEnd = ui.dp(6) })
            if (i == paso) { seg.scaleX = 0f; seg.pivotX = 0f; seg.animate().scaleX(1f).setDuration(500).setStartDelay(200).start() }
        }
        cuerpo.addView(pasos)
        val cab = ui.fila()
        cab.addView(ui.iconoCirculo(icono, Colores.rojo, 48))
        cab.addView(ui.texto(detalle, 14.5f, Colores.gris).apply { setPadding(ui.dp(14), 0, 0, 0) },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        cuerpo.addView(cab)
        c.addView(cuerpo)
        return cuerpo
    }

    private fun recuperarCorreo(correoInicial: String = "") {
        val cuerpo = pasoRecuperacion(1, "Su correo", "Escriba el correo registrado en SIGED. Le enviaremos un código de 6 dígitos.",
            R.drawable.ic_correo) { pantallaLogin() }
        val (caja, correo) = ui.campoIcono(R.drawable.ic_correo, "nombre@correo.cl", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS)
        correo.setText(correoInicial)
        val err = textoError()
        cuerpo.addView(ui.etiqueta("Correo electrónico")); cuerpo.addView(caja); cuerpo.addView(err)
        cuerpo.addView(ui.margen(ui.boton("Enviar código", icono = R.drawable.ic_enviar) {
            val valor = correo.text.toString().trim()
            if (!android.util.Patterns.EMAIL_ADDRESS.matcher(valor).matches()) { error(err, "Ingrese un correo válido."); return@boton }
            val capa = cubrir("Enviando código…")
            enSegundoPlano({ api.post("/api/v1/recuperar/", JSONObject().put("correo", valor)) },
                { r -> descubrir(capa); recuperarCodigo(valor, r.optString("mensaje")) },
                { e -> descubrir(capa); error(err, e.message) })
        }, arriba = 18))
        cuerpo.addView(ui.enlace("Volver al ingreso") { pantallaLogin() }.apply { gravity = Gravity.CENTER })
        mostrar(desplazable(cuerpo.parent as View), { pantallaLogin() })
        ui.entrada((1 until cuerpo.childCount).map { cuerpo.getChildAt(it) })
    }

    private fun recuperarCodigo(correo: String, mensaje: String) {
        val cuerpo = pasoRecuperacion(2, "Código de verificación", mensaje.ifBlank { "Revise su correo." }, R.drawable.ic_bandeja) { recuperarCorreo(correo) }
        cuerpo.addView(ui.insignia("Enviado a $correo", Colores.azul, R.drawable.ic_correo).apply { (layoutParams as LinearLayout.LayoutParams).topMargin = ui.dp(12) })
        val codigo = ui.campo("······", InputType.TYPE_CLASS_NUMBER).apply {
            filters = arrayOf(InputFilter.LengthFilter(6)); textSize = 30f; gravity = Gravity.CENTER; letterSpacing = 0.6f; typeface = Letras.cifra
        }
        val err = textoError()
        cuerpo.addView(ui.etiqueta("Código de 6 dígitos")); cuerpo.addView(codigo); cuerpo.addView(err)
        cuerpo.addView(ui.margen(ui.boton("Verificar código", icono = R.drawable.ic_check) {
            val valor = codigo.text.toString()
            if (!Regex("\\d{6}").matches(valor)) { error(err, "Ingrese los 6 dígitos."); return@boton }
            val capa = cubrir("Verificando…")
            enSegundoPlano({ api.post("/api/v1/recuperar/verificar/", JSONObject().put("correo", correo).put("codigo", valor)) },
                { r -> descubrir(capa); recuperarNueva(r.optString("permiso")) },
                { e -> descubrir(capa); error(err, e.message); codigo.text.clear() })
        }, arriba = 18))
        val reenviar = ui.enlace("Reenviar código") {}
        fun espera() {
            reenviar.isEnabled = false; reenviar.alpha = 0.55f
            object : CountDownTimer(60_000, 1_000) {
                override fun onTick(ms: Long) { reenviar.text = "Reenviar código en ${ms / 1000} s" }
                override fun onFinish() { reenviar.isEnabled = true; reenviar.alpha = 1f; reenviar.text = "Reenviar código" }
            }.start()
        }
        reenviar.setOnClickListener {
            enSegundoPlano({ api.post("/api/v1/recuperar/", JSONObject().put("correo", correo)) },
                { espera(); err.text = "Enviamos un código nuevo. El anterior ya no sirve."; err.setTextColor(Colores.verde); err.visibility = View.VISIBLE })
        }
        espera()
        cuerpo.addView(reenviar.apply { gravity = Gravity.CENTER })
        cuerpo.addView(ui.enlace("Cambiar correo") { recuperarCorreo(correo) }.apply { gravity = Gravity.CENTER })
        mostrar(desplazable(cuerpo.parent as View), { recuperarCorreo(correo) })
        ui.entrada((1 until cuerpo.childCount).map { cuerpo.getChildAt(it) })
        codigo.requestFocus()
    }

    private fun recuperarNueva(permiso: String) {
        val cuerpo = pasoRecuperacion(3, "Nueva contraseña",
            "Al menos 8 caracteres, con mayúscula, minúscula, número y símbolo. Se cerrarán sus sesiones en otros teléfonos.",
            R.drawable.ic_candado) { pantallaLogin() }
        val tipo = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        val (c1, clave) = ui.campoIcono(R.drawable.ic_candado, "Nueva contraseña", tipo)
        val (c2, repetir) = ui.campoIcono(R.drawable.ic_check, "Repita la contraseña", tipo)
        val err = textoError()
        cuerpo.addView(ui.etiqueta("Nueva contraseña")); cuerpo.addView(c1)
        cuerpo.addView(ui.etiqueta("Confirmación")); cuerpo.addView(c2); cuerpo.addView(err)
        cuerpo.addView(ui.margen(ui.boton("Guardar contraseña", icono = R.drawable.ic_check) {
            val a = clave.text.toString(); val b = repetir.text.toString()
            if (a.length < 8) { error(err, "Use al menos 8 caracteres."); return@boton }
            if (a != b) { error(err, "Las contraseñas no coinciden."); return@boton }
            val capa = cubrir("Guardando…")
            enSegundoPlano({ api.post("/api/v1/recuperar/nueva/", JSONObject().put("permiso", permiso).put("password", a).put("confirmacion", b)) },
                { r -> descubrir(capa); pantallaExito("Contraseña actualizada", r.optString("mensaje")) { pantallaLogin() } },
                { e -> descubrir(capa); error(err, e.message) })
        }, arriba = 18))
        mostrar(desplazable(cuerpo.parent as View), { pantallaLogin() })
        ui.entrada((1 until cuerpo.childCount).map { cuerpo.getChildAt(it) })
    }

    // ------------------------------------------------------------------ datos
    private fun renovarSiCorresponde() {
        val expira = try { OffsetDateTime.parse(sesion?.optString("expira")) } catch (_: Exception) { null } ?: return
        if (expira.isAfter(OffsetDateTime.now().plusDays(7))) return
        enSegundoPlano({ api.post("/api/v1/sesion/renovar/") }, { r ->
            api.token = r.optString("token"); sesion = sesion?.put("token", api.token)?.put("expira", r.optString("expira"))
            sesion?.let { vault.session(it) }
        }, { /* sin conexión: se intenta la próxima vez */ })
    }

    private fun cargarTrabajo(alTerminar: (() -> Unit)? = null) {
        enSegundoPlano({ api.get("/api/v1/mi-trabajo/") }, { t ->
            trabajo = t; vault.work(cuenta, t); fotoPerfil = null; pantallaInicio(); alTerminar?.invoke()
        }, { e ->
            if (trabajo != null) { pantallaInicio(); avisar(IOException("Mostrando la última información guardada. ${e.message}")) }
            else { pantallaLogin(e.message) }
        })
    }

    private var fotoPerfil: Bitmap? = null

    private fun cargarFoto(destino: ImageView, iniciales: TextView) {
        val url = perfil.optString("foto_url")
        val bitmap = fotoPerfil
        if (bitmap != null) { ponerFoto(destino, iniciales, bitmap); return }
        if (url.isBlank()) return
        enSegundoPlano({ api.file(url).let { BitmapFactory.decodeByteArray(it, 0, it.size) } }, { b ->
            if (b != null) { fotoPerfil = b; ponerFoto(destino, iniciales, b) }
        }, { })
    }

    private fun ponerFoto(destino: ImageView, iniciales: TextView, b: Bitmap) {
        destino.setImageDrawable(RoundedBitmapDrawableFactory.create(resources, b).apply { isCircular = true })
        destino.alpha = 0f; destino.visibility = View.VISIBLE
        destino.animate().alpha(1f).setDuration(350).withEndAction { iniciales.visibility = View.GONE }.start()
    }

    /** Foto circular con aro dorado; muestra iniciales mientras carga o si no hay foto. */
    private fun avatar(tam: Int): FrameLayout {
        val marco = FrameLayout(this).apply { background = ui.forma(Colores.dorado, tam); val p = ui.dp(3); setPadding(p, p, p, p) }
        val interior = tam - 6
        val iniciales = ui.texto(inicialesDe(perfil.optString("nombre")), (interior / 2.7f), Colores.vino, true).apply {
            gravity = Gravity.CENTER; background = ui.forma(0xFFFFF4E0.toInt(), tam); typeface = Letras.titulo
        }
        val imagen = ImageView(this).apply { scaleType = ImageView.ScaleType.CENTER_CROP; visibility = View.GONE }
        marco.addView(iniciales, FrameLayout.LayoutParams(ui.dp(interior), ui.dp(interior)))
        marco.addView(imagen, FrameLayout.LayoutParams(ui.dp(interior), ui.dp(interior)))
        cargarFoto(imagen, iniciales)
        marco.layoutParams = LinearLayout.LayoutParams(ui.dp(tam), ui.dp(tam)).apply { gravity = Gravity.CENTER_HORIZONTAL }
        return marco
    }

    // ------------------------------------------------------------------ inicio: trimestre, asistencia y actividades
    private fun navegacion(activa: String): View {
        val barra = ui.fila().apply {
            background = ui.forma(Colores.blanco, 24); elevation = ui.dp(10).toFloat(); setPadding(ui.dp(8), ui.dp(6), ui.dp(8), ui.dp(6))
        }
        val items = listOf(Triple("Mi trabajo", R.drawable.ic_inicio, { pantallaInicio() }), Triple("Perfil", R.drawable.ic_perfil, { pantallaPerfil() }))
        for ((nombre, icono, accion) in items) {
            val activo = nombre == activa
            val color = if (activo) Colores.rojo else Colores.gris
            val item = ui.fila().apply {
                gravity = Gravity.CENTER; setPadding(0, ui.dp(10), 0, ui.dp(10))
                if (activo) background = ui.forma(Colores.rosa, 18)
                addView(ui.icono(icono, color, 22))
                if (activo) addView(ui.texto(nombre, 14f, color, true).apply { setPadding(ui.dp(8), 0, 0, 0) })
                contentDescription = nombre
                setOnClickListener { if (!activo) accion() }
            }
            barra.addView(ui.presionable(item), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            if (activo) { item.scaleX = 0.85f; item.scaleY = 0.85f; item.animate().scaleX(1f).scaleY(1f).setDuration(380).setInterpolator(OvershootInterpolator(2.5f)).start() }
        }
        return barra
    }

    private fun conNavegacion(contenido: View, activa: String): View {
        val marco = FrameLayout(this)
        marco.addView(contenido)
        // La barra flota sobre un velo del color de fondo, para que las tarjetas no se vean por debajo.
        val velo = FrameLayout(this).apply {
            background = android.graphics.drawable.GradientDrawable(android.graphics.drawable.GradientDrawable.Orientation.TOP_BOTTOM,
                intArrayOf(0x00F6F3EF, 0xF2F6F3EF.toInt(), Colores.fondo))
            setPadding(ui.dp(20), ui.dp(26), ui.dp(20), ui.dp(14)); clipToPadding = false
        }
        velo.addView(navegacion(activa))
        marco.addView(velo, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM))
        return marco
    }

    private fun saludo(): String {
        val h = java.time.LocalTime.now().hour
        return when { h < 12 -> "Buenos días,"; h < 20 -> "Buenas tardes,"; else -> "Buenas noches," }
    }

    private fun pantallaInicio(conservar: Boolean = false) {
        val previoY = if (conservar) raiz.findViewWithTag<ScrollView>("scrollInicio")?.scrollY ?: 0 else 0
        val previoX = if (conservar) raiz.findViewWithTag<HorizontalScrollView>("chips")?.scrollX ?: 0 else 0
        val t = trabajo ?: return pantallaCarga("Cargando su información…")
        val p = perfil
        val c = ui.columna()
        // Cabecera con foto y datos de la persona
        val cab = FrameLayout(this)
        cab.addView(FondoMarca(this, animado = true, curva = true))
        val filaCab = ui.fila().apply { tag = "arriba"; setPadding(ui.dp(20), insetArriba + ui.dp(18), ui.dp(20), ui.dp(64)) }
        val datos = ui.columna()
        datos.addView(ui.texto(saludo(), 13.5f, Colores.dorado, true))
        datos.addView(ui.titulo(p.optString("nombre").replace("(ficticio)", "").trim(), 22f, Colores.blanco).apply { maxLines = 2 })
        datos.addView(ui.texto(listOf(p.optString("cargo"), p.optString("delegacion")).filter { it.isNotBlank() }.joinToString(" · "), 13f, 0xFFF3E3E6.toInt()))
        filaCab.addView(datos, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        filaCab.addView(ui.presionable(avatar(60).apply { setOnClickListener { pantallaPerfil() } }))
        cab.addView(filaCab)
        c.addView(cab)

        val cuerpo = ui.columna().apply { setPadding(ui.dp(16), 0, ui.dp(16), ui.dp(100)) }
        // Trimestre: tarjeta que se monta sobre la cabecera
        val tri = t.optJSONObject("trimestre") ?: JSONObject()
        val tarjetaTri = ui.tarjeta(18)
        val ft = ui.fila()
        ft.addView(ui.iconoCirculo(R.drawable.ic_calendario, Colores.rojo, 42))
        val tt = ui.columna().apply { setPadding(ui.dp(12), 0, 0, 0) }
        tt.addView(ui.texto("TRIMESTRE VIGENTE", 11f, Colores.gris, true).apply { letterSpacing = 0.1f })
        tt.addView(ui.titulo(tri.optString("periodo"), 19f))
        ft.addView(tt, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val dia = ui.texto("", 24f, Colores.rojo).apply { typeface = Letras.cifra }
        val diaCol = ui.columna().apply { gravity = Gravity.END }
        diaCol.addView(dia); diaCol.addView(ui.texto("de ${tri.optInt("dias_total")} días", 11.5f, Colores.gris).apply { gravity = Gravity.END })
        ft.addView(diaCol)
        tarjetaTri.addView(ft)
        ui.contar(dia, tri.optInt("dia"), { "Día $it" })
        tarjetaTri.addView(ui.margen(ui.barra(tri.optInt("porcentaje")), arriba = 16, abajo = 8))
        val restantes = tri.optInt("restantes")
        tarjetaTri.addView(ui.fila().apply {
            addView(ui.texto("${tri.optString("inicio")} → ${tri.optString("termino")}", 12f, Colores.gris), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            addView(ui.texto(if (restantes > 0) "faltan $restantes días" else "último día", 12f, Colores.rojo, true))
        })
        cuerpo.addView(ui.margen(tarjetaTri, abajo = 14))

        // Asistencia con anillo animado
        val asis = t.optJSONObject("asistencia")
        if (asis != null) {
            val pct = asis.optInt("porcentaje")
            val color = if (pct >= 80) Colores.verde else if (pct >= 60) Colores.ambar else Colores.rojo
            val tarjetaAsis = ui.tarjeta(18)
            val fila = ui.fila()
            val anillo = Anillo(this, color)
            fila.addView(anillo, LinearLayout.LayoutParams(ui.dp(88), ui.dp(88)))
            anillo.animar(pct)
            val izq = ui.columna().apply { setPadding(ui.dp(16), 0, 0, 0) }
            izq.addView(ui.texto("ASISTENCIA DEL TRIMESTRE", 11f, Colores.gris, true).apply { letterSpacing = 0.1f })
            val dias = ui.titulo("", 20f)
            izq.addView(dias)
            ui.contar(dias, asis.optInt("dias_con_registro"), { "$it de ${asis.optInt("dias_habiles")} días" })
            val ultima = asis.optString("ultima_actividad").takeIf { it.isNotBlank() && it != "null" }
            izq.addView(ui.texto(if (ultima != null) "Último registro: ${fechaCorta(ultima)}" else "Sin registros este trimestre", 12f, Colores.gris))
            val hoy = asis.optBoolean("registro_hoy")
            izq.addView(ui.insignia(if (hoy) "Hoy tiene registro" else "Hoy aún sin registro", if (hoy) Colores.verde else Colores.gris2,
                if (hoy) R.drawable.ic_check else R.drawable.ic_reloj).apply { (layoutParams as LinearLayout.LayoutParams).topMargin = ui.dp(8) })
            fila.addView(izq, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            tarjetaAsis.addView(fila)
            cuerpo.addView(ui.margen(tarjetaAsis, abajo = 18))
        }

        // Registrar actividad del día (se refleja en la asistencia y en la web)
        cuerpo.addView(ui.margen(ui.boton("Registrar actividad", icono = R.drawable.ic_camara) { abrirNuevaActividad() }, abajo = 18))

        // Actividades por estado
        val refrescar = ImageView(this).apply {
            setImageResource(R.drawable.ic_actualizar); imageTintList = android.content.res.ColorStateList.valueOf(Colores.rojo)
            background = ui.forma(Colores.rosa, 14); val pd = ui.dp(8); setPadding(pd, pd, pd, pd); contentDescription = "Actualizar"
            layoutParams = LinearLayout.LayoutParams(ui.dp(38), ui.dp(38))
        }
        refrescar.setOnClickListener { ui.girar(refrescar); refrescar.postDelayed({ pantallaCarga("Actualizando…"); cargarTrabajo() }, 450) }
        cuerpo.addView(ui.fila().apply {
            addView(ui.titulo("Mis actividades", 20f), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            addView(ui.presionable(refrescar))
        })
        val conteo = t.optJSONObject("conteo") ?: JSONObject()
        val total = t.optJSONArray("compromisos")?.length() ?: 0
        val chips = ui.fila().apply { setPadding(0, ui.dp(10), ui.dp(16), ui.dp(10)) }
        for (estado in listOf("TODOS", "INGRESADO", "PENDIENTE", "EN PROCESO", "REALIZADO", "VENCIDO")) {
            val n = if (estado == "TODOS") total else conteo.optInt(estado)
            val activo = estado == filtro
            val color = if (estado == "TODOS") Colores.vino else Colores.estado(estado)
            val chip = ui.fila().apply {
                background = if (activo) ui.forma(color, 20) else ui.forma(Colores.blanco, 20, Colores.borde)
                setPadding(ui.dp(12), ui.dp(8), ui.dp(14), ui.dp(8))
                addView(ui.icono(if (estado == "TODOS") R.drawable.ic_tubo else Colores.iconoEstado(estado), if (activo) Colores.blanco else color, 16))
                addView(ui.texto("${if (estado == "TODOS") "Todas" else Colores.nombreEstado(estado)}  $n", 13f, if (activo) Colores.blanco else Colores.tinta, true)
                    .apply { setPadding(ui.dp(6), 0, 0, 0) })
                setOnClickListener { if (filtro != estado) { filtro = estado; pantallaInicio(conservar = true) } }
            }
            chips.addView(ui.presionable(chip), LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginEnd = ui.dp(8) })
        }
        cuerpo.addView(HorizontalScrollView(this).apply { tag = "chips"; isHorizontalScrollBarEnabled = false; clipToPadding = false; addView(chips) })

        val lista = t.optJSONArray("compromisos")
        val visibles = (0 until (lista?.length() ?: 0)).map { lista!!.getJSONObject(it) }
            .filter { filtro == "TODOS" || it.optString("estado") == filtro }
        if (visibles.isEmpty()) {
            cuerpo.addView(ui.animacion(R.raw.siged_vacio, 130))
            cuerpo.addView(ui.texto(if (filtro == "TODOS") "No tiene actividades asignadas." else "No hay actividades en «${Colores.nombreEstado(filtro)}».", 15f, Colores.gris)
                .apply { gravity = Gravity.CENTER })
        }
        for (comp in visibles) cuerpo.addView(ui.margen(tarjetaCompromiso(comp), abajo = 10))
        c.addView(cuerpo, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = -ui.dp(48) })
        val scroll = desplazable(c).apply { tag = "scrollInicio" }
        mostrar(conNavegacion(scroll, "Mi trabajo"), null, animar = !conservar)
        if (conservar) {
            scroll.post { scroll.scrollTo(0, previoY); raiz.findViewWithTag<HorizontalScrollView>("chips")?.scrollTo(previoX, 0) }
            // Solo las tarjetas de la lista entran animadas al cambiar de filtro.
            val inicioLista = (0 until cuerpo.childCount).indexOfFirst { cuerpo.getChildAt(it) is HorizontalScrollView } + 1
            ui.entrada((inicioLista until cuerpo.childCount).map { cuerpo.getChildAt(it) }, 0)
        } else ui.entrada((0 until cuerpo.childCount).map { cuerpo.getChildAt(it) }, 120)
    }

    private fun tarjetaCompromiso(comp: JSONObject): View {
        val estado = comp.optString("estado")
        val color = Colores.estado(estado)
        val tarjeta = ui.tarjeta(0).apply { setOnClickListener { pantallaDetalle(comp.optString("codigo")) } }
        val fila = ui.fila().apply { gravity = Gravity.TOP }
        fila.addView(View(this).apply { background = ui.forma(color, 4) }, LinearLayout.LayoutParams(ui.dp(5), ViewGroup.LayoutParams.MATCH_PARENT).apply {
            setMargins(0, ui.dp(14), 0, ui.dp(14)) })
        val contenido = ui.columna().apply { setPadding(ui.dp(12), ui.dp(14), ui.dp(12), ui.dp(14)) }
        val cab = ui.fila()
        cab.addView(ui.texto(comp.optString("codigo"), 12f, Colores.gris, true).apply { letterSpacing = 0.05f },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        cab.addView(ui.insignia(Colores.nombreEstado(estado), color, Colores.iconoEstado(estado)))
        contenido.addView(cab)
        contenido.addView(ui.texto(comp.optString("descripcion"), 15.5f, Colores.tinta, true).apply { maxLines = 2; setPadding(0, ui.dp(6), 0, ui.dp(8)) })
        val ev = comp.optJSONArray("evidencias")?.length() ?: 0
        val pie = ui.fila()
        for ((ic, txt) in listOf(R.drawable.ic_calendario to fechaCorta(comp.optString("fecha_compromiso")), R.drawable.ic_clip to "$ev")) {
            pie.addView(ui.icono(ic, Colores.gris, 15))
            pie.addView(ui.texto(txt, 12.5f, Colores.gris).apply { setPadding(ui.dp(4), 0, ui.dp(14), 0) })
        }
        pie.addView(ui.texto(comp.optString("solicitante"), 12.5f, Colores.gris).apply { maxLines = 1 }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        contenido.addView(pie)
        fila.addView(contenido, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        fila.addView(ui.icono(R.drawable.ic_adelante, Colores.borde, 18).apply { (layoutParams as LinearLayout.LayoutParams).apply { gravity = Gravity.CENTER_VERTICAL; marginEnd = ui.dp(12) } })
        tarjeta.addView(fila)
        return ui.presionable(tarjeta)
    }

    private fun buscarCompromiso(codigo: String): JSONObject? {
        val lista = trabajo?.optJSONArray("compromisos") ?: return null
        return (0 until lista.length()).map { lista.getJSONObject(it) }.firstOrNull { it.optString("codigo") == codigo }
    }

    private fun filaDato(icono: Int, etiqueta: String, valor: String): View = ui.fila().apply {
        setPadding(0, ui.dp(8), 0, ui.dp(8))
        addView(ui.iconoCirculo(icono, Colores.vino, 36))
        val col = ui.columna().apply { setPadding(ui.dp(12), 0, 0, 0) }
        col.addView(ui.texto(etiqueta.uppercase(), 10.5f, Colores.gris, true).apply { letterSpacing = 0.08f })
        col.addView(ui.texto(valor, 14.5f, Colores.tinta, true))
        addView(col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
    }

    private fun pantallaDetalle(codigo: String) {
        val comp = buscarCompromiso(codigo) ?: return pantallaInicio()
        val estado = comp.optString("estado")
        val c = ui.columna()
        c.addView(encabezado(codigo, "Detalle de la actividad", { pantallaInicio() }, alto = 28))
        val cuerpo = ui.columna().apply { setPadding(ui.dp(16), 0, ui.dp(16), ui.dp(24)) }
        val info = ui.tarjeta(18)
        info.addView(ui.insignia(Colores.nombreEstado(estado), Colores.estado(estado), Colores.iconoEstado(estado)))
        info.addView(ui.titulo(comp.optString("descripcion"), 18f).apply { setPadding(0, ui.dp(10), 0, ui.dp(6)) })
        for ((ic, etq, valor) in listOf(Triple(R.drawable.ic_perfil, "Solicitante", comp.optString("solicitante")),
                Triple(R.drawable.ic_calendario, "Plazo", fechaCorta(comp.optString("fecha_compromiso"))),
                Triple(R.drawable.ic_ubicacion, "Territorio", comp.optString("territorio")),
                Triple(R.drawable.ic_documento, "Observaciones", comp.optString("observaciones")))) {
            if (valor.isBlank() || valor == "null") continue
            info.addView(filaDato(ic, etq, valor))
        }
        cuerpo.addView(ui.margen(info, abajo = 18))

        val evidencias = comp.optJSONArray("evidencias")
        val n = evidencias?.length() ?: 0
        cuerpo.addView(ui.fila().apply {
            addView(ui.titulo("Evidencias", 20f), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            addView(ui.insignia("$n", Colores.vino, R.drawable.ic_clip))
        })
        if (n == 0) {
            cuerpo.addView(ui.tarjeta(18).apply {
                gravity = Gravity.CENTER_HORIZONTAL
                addView(ui.iconoCirculo(R.drawable.ic_imagen, Colores.gris, 52).apply { (layoutParams as LinearLayout.LayoutParams).gravity = Gravity.CENTER_HORIZONTAL })
                addView(ui.texto("Aún no hay evidencias.\nSuba una foto o un documento PDF.", 14f, Colores.gris).apply { gravity = Gravity.CENTER; setPadding(0, ui.dp(10), 0, 0) })
            }.let { ui.margen(it, arriba = 10) })
        } else for (i in 0 until n) {
            val e = evidencias!!.getJSONObject(i)
            val doc = e.optString("tipo") == "DOCUMENTO"
            val filaEv = ui.tarjeta(12).apply { setOnClickListener { abrirEvidencia(e) } }
            val f = ui.fila()
            f.addView(ui.iconoCirculo(if (doc) R.drawable.ic_documento else R.drawable.ic_imagen, if (doc) Colores.azul else Colores.verde, 42))
            val col = ui.columna().apply { setPadding(ui.dp(12), 0, ui.dp(8), 0) }
            col.addView(ui.texto(e.optString("nombre"), 14.5f, Colores.tinta, true).apply { maxLines = 1 })
            col.addView(ui.texto("${if (doc) "Documento" else "Foto"} · ${fechaCorta(e.optString("fecha").take(10))}", 12f, Colores.gris))
            f.addView(col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            f.addView(ui.icono(R.drawable.ic_adelante, Colores.gris, 18))
            filaEv.addView(f)
            cuerpo.addView(ui.margen(ui.presionable(filaEv), arriba = if (i == 0) 10 else 0, abajo = 8))
        }
        val botones = ui.fila().apply { setPadding(0, ui.dp(10), 0, ui.dp(8)) }
        botones.addView(ui.boton("Tomar foto", icono = R.drawable.ic_camara) { pedirFoto("compromiso:$codigo") },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = ui.dp(10) })
        botones.addView(ui.boton("Archivo", primario = false, icono = R.drawable.ic_clip) { pedirArchivo("compromiso:$codigo") },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        cuerpo.addView(botones)
        cuerpo.addView(ui.texto("Fotos JPG/PNG o PDF de hasta 10 MB. Las fotos se reducen antes de enviarlas para ahorrar datos.", 12f, Colores.gris)
            .apply { gravity = Gravity.CENTER })
        c.addView(cuerpo, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = -ui.dp(40) })
        mostrar(desplazable(c), { pantallaInicio() }, atras = false)
        ui.entrada((0 until cuerpo.childCount).map { cuerpo.getChildAt(it) }, 100)
    }

    // ------------------------------------------------------------------ registrar actividad
    private var borrador: BorradorActividad? = null
    private var metasCache: List<Pair<String, String>> = emptyList()

    private fun abrirNuevaActividad() {
        val capa = cubrir("Cargando sus ítems…")
        enSegundoPlano({ metasDe(api.get("/api/v1/panel/")) }, { m ->
            descubrir(capa); metasCache = m
            if (m.isEmpty()) {
                avisar(IOException("No tiene ítems asignados este trimestre. Pida a su delegado que se los asigne."))
            } else {
                borrador = BorradorActividad().apply { if (m.size == 1) meta = m[0].first }
                pantallaNuevaActividad()
            }
        }, { e -> descubrir(capa); avisar(e) })
    }

    /** Fila de opciones que se marcan con un toque; [alElegir] recibe la clave elegida. */
    private fun opciones(lista: List<Pair<String, String>>, elegida: String, alElegir: (String) -> Unit): View {
        val fila = ui.fila().apply { setPadding(0, 0, ui.dp(16), 0) }
        for ((clave, texto) in lista) {
            val activa = clave == elegida
            val chip = ui.fila().apply {
                background = if (activa) ui.forma(Colores.vino, 20) else ui.forma(Colores.blanco, 20, Colores.borde)
                setPadding(ui.dp(14), ui.dp(9), ui.dp(14), ui.dp(9))
                if (activa) addView(ui.icono(R.drawable.ic_check, Colores.blanco, 15).apply { (layoutParams as LinearLayout.LayoutParams).marginEnd = ui.dp(6) })
                addView(ui.texto(texto, 13.5f, if (activa) Colores.blanco else Colores.tinta, true))
                setOnClickListener { alElegir(clave) }
            }
            fila.addView(ui.presionable(chip), LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginEnd = ui.dp(8) })
        }
        return HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false; addView(fila) }
    }

    private fun pantallaNuevaActividad() {
        val b = borrador ?: return pantallaInicio()
        val c = ui.columna()
        c.addView(encabezado("Nueva actividad", "Queda en la web y suma a su asistencia", { borrador = null; pantallaInicio() }, alto = 28))
        val cuerpo = ui.columna().apply { setPadding(ui.dp(16), 0, ui.dp(16), ui.dp(28)) }
        val tarjeta = ui.tarjeta(18)
        val (cajaServ, servicio) = ui.campoIcono(R.drawable.ic_documento, "Ej.: Visita a JJVV por luminarias")
        val (cajaCont, contacto) = ui.campoIcono(R.drawable.ic_perfil, "Ej.: Presidenta JJVV Los Aromos")
        servicio.setText(b.servicio); contacto.setText(b.contacto)
        val guardar = { b.servicio = servicio.text.toString(); b.contacto = contacto.text.toString() }
        tarjeta.addView(ui.etiqueta("Ítem o meta"))
        tarjeta.addView(opciones(metasCache, b.meta) { guardar(); b.meta = it; pantallaNuevaActividad() })
        tarjeta.addView(ui.etiqueta("Tipo de registro"))
        tarjeta.addView(opciones(TiposRegistro.opciones, b.tipo) { guardar(); b.tipo = it; pantallaNuevaActividad() })
        tarjeta.addView(ui.etiqueta("Fecha"))
        val hoy = java.time.LocalDate.now()
        val fechas = (0..2).map { hoy.minusDays(it.toLong()) }.map { d ->
            d.toString() to when (d) { hoy -> "Hoy"; hoy.minusDays(1) -> "Ayer"; else -> fechaCorta(d.toString()) }
        }
        tarjeta.addView(opciones(fechas, b.fecha.toString()) { guardar(); b.fecha = java.time.LocalDate.parse(it); pantallaNuevaActividad() })
        tarjeta.addView(ui.etiqueta("Servicio realizado")); tarjeta.addView(cajaServ)
        tarjeta.addView(ui.etiqueta("Contacto")); tarjeta.addView(cajaCont)
        cuerpo.addView(ui.margen(tarjeta, abajo = 16))

        val ev = ui.tarjeta(16)
        val fe = ui.fila()
        val archivo = b.archivo
        fe.addView(ui.iconoCirculo(if (archivo != null) R.drawable.ic_check else R.drawable.ic_imagen, if (archivo != null) Colores.verde else Colores.gris, 44))
        val col = ui.columna().apply { setPadding(ui.dp(12), 0, 0, 0) }
        col.addView(ui.texto(if (archivo != null) "Evidencia lista" else "Evidencia", 15f, Colores.tinta, true))
        col.addView(ui.texto(if (archivo != null) "${if (b.extension == "pdf") "Documento PDF" else "Foto"} · ${archivo.size / 1024} KB" else "Foto o PDF de hasta 10 MB", 12.5f, Colores.gris))
        fe.addView(col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        ev.addView(fe)
        val bots = ui.fila().apply { setPadding(0, ui.dp(12), 0, 0) }
        bots.addView(ui.boton("Foto", primario = archivo == null, icono = R.drawable.ic_camara) { guardar(); pedirFoto("actividad") },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = ui.dp(10) })
        bots.addView(ui.boton("Archivo", primario = false, icono = R.drawable.ic_clip) { guardar(); pedirArchivo("actividad") },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        ev.addView(bots, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        cuerpo.addView(ui.margen(ev, abajo = 8))
        val err = textoError()
        cuerpo.addView(err)
        cuerpo.addView(ui.margen(ui.boton("Enviar actividad", icono = R.drawable.ic_enviar) {
            guardar()
            val falta = b.falta()
            if (falta != null) { error(err, falta); return@boton }
            val capa = cubrir("Enviando actividad…")
            enSegundoPlano({ api.upload("/api/v1/actividades/", "evidencia", b.archivo!!, b.extension, b.campos()) }, { r ->
                descubrir(capa); borrador = null
                val codigo = r.optJSONObject("actividad")?.optString("codigo").orEmpty()
                pantallaExito("Actividad registrada", "Quedó como $codigo, pendiente de revisión del delegado. Ya se ve en la web.") {
                    pantallaCarga("Actualizando…"); cargarTrabajo()
                }
            }, { e -> descubrir(capa); error(err, e.message) })
        }, arriba = 10))
        c.addView(cuerpo, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = -ui.dp(40) })
        mostrar(desplazable(c), { borrador = null; pantallaInicio() })
        ui.entrada((0 until cuerpo.childCount).map { cuerpo.getChildAt(it) }, 80)
    }

    // ------------------------------------------------------------------ perfil
    private fun pantallaPerfil() {
        val p = perfil
        val c = ui.columna()
        c.addView(encabezado("Mi perfil", null, { pantallaInicio() }, alto = 56))
        val cuerpo = ui.columna().apply { setPadding(ui.dp(16), 0, ui.dp(16), ui.dp(100)) }
        val tarjeta = ui.tarjeta(20).apply { gravity = Gravity.CENTER_HORIZONTAL }
        val foto = avatar(112)
        tarjeta.addView(foto)
        tarjeta.addView(ui.titulo(p.optString("nombre").replace("(ficticio)", "").trim(), 21f).apply { gravity = Gravity.CENTER; setPadding(0, ui.dp(12), 0, 0) })
        tarjeta.addView(ui.insignia(p.optString("rol_nombre").ifBlank { "Funcionario" }, Colores.vino, R.drawable.ic_marca)
            .apply { (layoutParams as LinearLayout.LayoutParams).apply { gravity = Gravity.CENTER_HORIZONTAL; topMargin = ui.dp(6) } })
        val bots = ui.fila().apply { setPadding(0, ui.dp(16), 0, 0) }
        bots.addView(ui.boton("Cámara", icono = R.drawable.ic_camara) { pedirFoto("perfil") },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = ui.dp(10) })
        bots.addView(ui.boton("Galería", primario = false, icono = R.drawable.ic_imagen) { pedirArchivo("perfil") },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        tarjeta.addView(bots, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        cuerpo.addView(ui.margen(tarjeta, abajo = 14))
        val datos = ui.tarjeta(16)
        for ((ic, etq, valor) in listOf(Triple(R.drawable.ic_tarjeta_id, "RUT", formatearRut(p.optString("rut"))),
                Triple(R.drawable.ic_correo, "Correo", p.optString("correo")), Triple(R.drawable.ic_estrella, "Cargo", p.optString("cargo")),
                Triple(R.drawable.ic_ubicacion, "Delegación", p.optString("delegacion")), Triple(R.drawable.ic_tubo, "Código", p.optString("codigo")))) {
            if (valor.isBlank()) continue
            datos.addView(filaDato(ic, etq, valor))
        }
        cuerpo.addView(ui.margen(datos, abajo = 14))
        cuerpo.addView(ui.margen(ui.boton("Cerrar sesión", primario = false, icono = R.drawable.ic_salir) {
            AlertDialog.Builder(this).setTitle("Cerrar sesión").setMessage("¿Desea salir de SIGED Móvil en este teléfono?")
                .setPositiveButton("Salir") { _, _ ->
                    enSegundoPlano({ api.post("/api/v1/sesion/cerrar/") }, { sesionVencidaSinMensaje() }, { sesionVencidaSinMensaje() })
                }.setNegativeButton("Cancelar", null).show().let { redondear(it) }
        }))
        c.addView(cuerpo, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = -ui.dp(70) })
        mostrar(conNavegacion(desplazable(c), "Perfil"), { pantallaInicio() })
        foto.scaleX = 0.5f; foto.scaleY = 0.5f
        foto.animate().scaleX(1f).scaleY(1f).setStartDelay(120).setDuration(550).setInterpolator(OvershootInterpolator(2f)).start()
        ui.entrada((0 until cuerpo.childCount).map { cuerpo.getChildAt(it) }, 100)
    }

    private fun sesionVencidaSinMensaje() { api.token = ""; sesion = null; trabajo = null; fotoPerfil = null; vault.clearSession(); pantallaLogin() }

    // ------------------------------------------------------------------ archivos y evidencias
    private fun pedirFoto(destino: String) {
        destinoArchivo = destino
        val carpeta = File(cacheDir, "camara").apply { mkdirs() }
        val f = File.createTempFile("foto_", ".jpg", carpeta)
        archivoCamara = f
        try { tomarFoto.launch(uriDe(f)) } catch (e: Exception) { f.delete(); avisar(IOException("No hay una aplicación de cámara disponible.")) }
    }

    private fun pedirArchivo(destino: String) {
        destinoArchivo = destino
        elegirArchivo.launch(if (destino == "perfil") arrayOf("image/jpeg", "image/png", "image/webp")
                             else arrayOf("image/jpeg", "image/png", "application/pdf"))
    }

    private fun uriDe(f: File): Uri = FileProvider.getUriForFile(this, "$packageName.archivos", f)

    private fun procesarArchivo(uri: Uri, destino: String, limpiar: () -> Unit = {}) {
        val tipo = contentResolver.getType(uri).orEmpty()
        val esPerfil = destino == "perfil"
        if (destino == "actividad") {
            val capa = cubrir("Preparando evidencia…")
            enSegundoPlano({
                if (tipo == "application/pdf") {
                    val datos = contentResolver.openInputStream(uri)?.use { readLimited(it, 10 * 1024 * 1024) } ?: throw IOException("No se pudo leer el archivo.")
                    if (!(datos.size > 4 && String(datos, 0, 5, Charsets.US_ASCII) == "%PDF-")) throw IOException("El archivo no es un PDF válido.")
                    datos to "pdf"
                } else comprimirImagen(uri, 2048) to "jpg"
            }, { (bytes, ext) -> limpiar(); descubrir(capa); borrador?.apply { archivo = bytes; extension = ext }; pantallaNuevaActividad() },
                { e -> limpiar(); descubrir(capa); avisar(e) })
            return
        }
        val capa = cubrir(if (esPerfil) "Subiendo su foto…" else "Subiendo evidencia…")
        enSegundoPlano({
            val (bytes, ext) = if (tipo == "application/pdf") {
                if (esPerfil) throw IOException("La foto de perfil debe ser una imagen.")
                val datos = contentResolver.openInputStream(uri)?.use { readLimited(it, 10 * 1024 * 1024) } ?: throw IOException("No se pudo leer el archivo.")
                if (!(datos.size > 4 && String(datos, 0, 5, Charsets.US_ASCII) == "%PDF-")) throw IOException("El archivo no es un PDF válido.")
                datos to "pdf"
            } else comprimirImagen(uri, if (esPerfil) 1024 else 2048) to "jpg"
            if (esPerfil) api.upload("/api/v1/perfil/foto/", "foto", bytes, ext)
            else api.upload("/api/v1/compromisos/${destino.removePrefix("compromiso:")}/evidencias/", "archivo", bytes, ext)
        }, { _ ->
            limpiar(); descubrir(capa); fotoPerfil = null
            if (esPerfil) pantallaExito("Foto actualizada", "Su foto ya se ve en la web y en la app.") { pantallaCarga("Actualizando…"); cargarTrabajo { pantallaPerfil() } }
            else pantallaExito("Evidencia subida", "Quedó guardada en la ficha del compromiso y se puede ver desde la web.") {
                pantallaCarga("Actualizando…"); cargarTrabajo { pantallaDetalle(destino.removePrefix("compromiso:")) } }
        }, { e -> limpiar(); descubrir(capa); avisar(e) })
    }

    /** Reduce la imagen a [lado] px como máximo, respeta la orientación de la cámara y la guarda como JPEG. */
    private fun comprimirImagen(uri: Uri, lado: Int): ByteArray {
        val opciones = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opciones) }
        if (opciones.outWidth <= 0) throw IOException("El archivo no es una imagen válida.")
        var muestra = 1
        while (opciones.outWidth / (muestra * 2) >= lado || opciones.outHeight / (muestra * 2) >= lado) muestra *= 2
        var imagen = contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = muestra })
        } ?: throw IOException("No se pudo leer la imagen.")
        val rotacion = try {
            contentResolver.openInputStream(uri)?.use {
                when (ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                    ExifInterface.ORIENTATION_ROTATE_90 -> 90f; ExifInterface.ORIENTATION_ROTATE_180 -> 180f
                    ExifInterface.ORIENTATION_ROTATE_270 -> 270f; else -> 0f
                }
            } ?: 0f
        } catch (_: Exception) { 0f }
        val escala = minOf(1f, lado.toFloat() / maxOf(imagen.width, imagen.height))
        if (rotacion != 0f || escala < 1f) {
            val m = Matrix().apply { postScale(escala, escala); postRotate(rotacion) }
            imagen = Bitmap.createBitmap(imagen, 0, 0, imagen.width, imagen.height, m, true)
        }
        return ByteArrayOutputStream().use { out -> imagen.compress(Bitmap.CompressFormat.JPEG, 85, out); out.toByteArray() }
    }

    private fun abrirEvidencia(e: JSONObject) {
        val capa = cubrir("Abriendo…")
        val doc = e.optString("tipo") == "DOCUMENTO"
        enSegundoPlano({
            val datos = api.file(e.optString("url"))
            val carpeta = File(cacheDir, "compartir").apply { mkdirs(); listFiles()?.forEach { it.delete() } }
            File(carpeta, "evidencia_${e.optInt("id")}.${if (doc) "pdf" else "jpg"}").apply { writeBytes(datos) }
        }, { f ->
            descubrir(capa)
            val intent = Intent(Intent.ACTION_VIEW).setDataAndType(uriDe(f), if (doc) "application/pdf" else "image/*")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            try { startActivity(intent) } catch (_: Exception) { avisar(IOException("No hay una aplicación para abrir este archivo.")) }
        }, { err -> descubrir(capa); avisar(err) })
    }

    // ------------------------------------------------------------------ utilidades
    private fun inicialesDe(nombre: String): String {
        val partes = nombre.replace("(ficticio)", "").split(" ").filter { it.firstOrNull()?.isLetter() == true }
        return ((partes.firstOrNull()?.take(1) ?: "?") + (if (partes.size > 1) partes.last().take(1) else "")).uppercase()
    }

    private fun fechaCorta(iso: String): String {
        val p = iso.take(10).split("-")
        return if (p.size == 3) "${p[2]}/${p[1]}/${p[0]}" else iso
    }
}

/** Módulo 11, igual que el servidor. */
internal fun rutValido(rut: String): Boolean {
    val limpio = rut.replace(".", "").replace("-", "").replace(" ", "").uppercase()
    if (!Regex("\\d{7,8}[\\dK]").matches(limpio)) return false
    val cuerpo = limpio.dropLast(1); var suma = 0; var factor = 2
    for (c in cuerpo.reversed()) { suma += (c - '0') * factor; factor = if (factor == 7) 2 else factor + 1 }
    val dv = when (val r = 11 - suma % 11) { 11 -> "0"; 10 -> "K"; else -> r.toString() }
    return dv == limpio.takeLast(1)
}

internal fun formatearRut(rut: String): String {
    val limpio = rut.replace(".", "").replace("-", "").replace(" ", "").uppercase()
    if (limpio.length < 2) return rut.trim()
    val cuerpo = limpio.dropLast(1); val dv = limpio.takeLast(1)
    return cuerpo.reversed().chunked(3).joinToString(".").reversed() + "-" + dv
}
