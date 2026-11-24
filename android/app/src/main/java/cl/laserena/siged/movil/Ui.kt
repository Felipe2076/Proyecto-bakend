package cl.laserena.siged.movil

import android.animation.ValueAnimator
import android.annotation.SuppressLint
import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.text.InputType
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.animation.DecelerateInterpolator
import android.view.animation.LinearInterpolator
import android.view.animation.OvershootInterpolator
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import com.airbnb.lottie.LottieAnimationView
import com.airbnb.lottie.LottieDrawable
import kotlin.math.cos
import kotlin.math.sin

/** Paleta municipal de La Serena. */
internal object Colores {
    val vino = Color.rgb(84, 19, 39)
    val vinoOscuro = Color.rgb(52, 10, 24)
    val rojo = Color.rgb(156, 24, 48)
    val rosa = Color.rgb(251, 233, 236)
    val tinta = Color.rgb(26, 32, 44)
    val gris = Color.rgb(102, 112, 128)
    val fondo = Color.rgb(246, 243, 239)
    val borde = Color.rgb(232, 226, 219)
    val dorado = Color.rgb(240, 206, 139)
    val blanco = Color.WHITE
    val verde = Color.rgb(22, 135, 90)
    val ambar = Color.rgb(212, 140, 16)
    val azul = Color.rgb(37, 99, 178)
    val morado = Color.rgb(111, 66, 193)
    val gris2 = Color.rgb(108, 117, 125)

    fun estado(estado: String) = when (estado) {
        "INGRESADO" -> azul; "PENDIENTE" -> ambar; "EN PROCESO" -> morado
        "REALIZADO" -> verde; "VENCIDO" -> rojo; else -> gris2
    }

    fun iconoEstado(estado: String) = when (estado) {
        "INGRESADO" -> R.drawable.ic_bandeja; "PENDIENTE" -> R.drawable.ic_reloj; "EN PROCESO" -> R.drawable.ic_progreso
        "REALIZADO" -> R.drawable.ic_check; "VENCIDO" -> R.drawable.ic_alerta; else -> R.drawable.ic_tubo
    }

    fun nombreEstado(estado: String) = when (estado) {
        "INGRESADO" -> "Ingresado"; "PENDIENTE" -> "Pendiente"; "EN PROCESO" -> "En proceso"
        "REALIZADO" -> "Realizado"; "VENCIDO" -> "Vencido"; else -> estado
    }

    /** Mezcla [color] con blanco: 0 = blanco, 1 = color. */
    fun suave(color: Int, f: Float = 0.12f) = Color.rgb(
        (255 + (Color.red(color) - 255) * f).toInt(), (255 + (Color.green(color) - 255) * f).toInt(), (255 + (Color.blue(color) - 255) * f).toInt())
}

internal object Letras {
    val titulo: Typeface = Typeface.create("sans-serif-black", Typeface.NORMAL)
    val medio: Typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
    val normal: Typeface = Typeface.create("sans-serif", Typeface.NORMAL)
    val cifra: Typeface = Typeface.create("sans-serif-condensed", Typeface.BOLD)
}

/** Fondo de marca: degradado vino → rojo con círculos translúcidos que flotan y curva inferior opcional. */
internal class FondoMarca(ctx: Context, private val animado: Boolean, private val curva: Boolean) : View(ctx) {
    private val pintura = Paint(Paint.ANTI_ALIAS_FLAG)
    private val burbuja = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }
    private val aro = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; color = Colores.dorado }
    private val forma = Path()
    private var fase = 0f
    private var anim: ValueAnimator? = null

    override fun onSizeChanged(w: Int, h: Int, ow: Int, oh: Int) {
        pintura.shader = LinearGradient(0f, 0f, w.toFloat(), h.toFloat(), intArrayOf(Colores.vinoOscuro, Colores.vino, Colores.rojo),
            floatArrayOf(0f, 0.45f, 1f), Shader.TileMode.CLAMP)
        aro.strokeWidth = w * 0.006f
        forma.reset()
        if (curva) {
            val c = h * 0.12f
            forma.moveTo(0f, 0f); forma.lineTo(w.toFloat(), 0f); forma.lineTo(w.toFloat(), h - c)
            forma.quadTo(w / 2f, h + c * 0.9f, 0f, h - c); forma.close()
        } else forma.addRect(0f, 0f, w.toFloat(), h.toFloat(), Path.Direction.CW)
    }

    override fun onDraw(canvas: Canvas) {
        val w = width.toFloat(); val h = height.toFloat()
        canvas.save(); canvas.clipPath(forma)
        canvas.drawPath(forma, pintura)
        burbuja.alpha = 20; canvas.drawCircle(w * 0.88f + 14 * cos(fase), h * 0.18f + 10 * sin(fase), w * 0.32f, burbuja)
        burbuja.alpha = 14; canvas.drawCircle(w * 0.08f + 12 * sin(fase), h * 0.92f + 8 * cos(fase), w * 0.26f, burbuja)
        burbuja.alpha = 26; canvas.drawCircle(w * 0.62f + 18 * sin(fase * 1.3f), h * 0.62f, w * 0.05f, burbuja)
        aro.alpha = 70; canvas.drawCircle(w * 0.18f + 10 * cos(fase), h * 0.22f, w * 0.09f, aro)
        canvas.restore()
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        if (!animado) return
        anim = ValueAnimator.ofFloat(0f, (2 * Math.PI).toFloat()).apply {
            duration = 9000; repeatCount = ValueAnimator.INFINITE; interpolator = LinearInterpolator()
            addUpdateListener { fase = it.animatedValue as Float; invalidate() }; start()
        }
    }

    override fun onDetachedFromWindow() { anim?.cancel(); super.onDetachedFromWindow() }
}

/** Anillo de progreso animado con el porcentaje al centro. */
internal class Anillo(ctx: Context, private val tono: Int, private val grosorDp: Float = 9f) : View(ctx) {
    private val d = ctx.resources.displayMetrics.density
    private val trazo = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeCap = Paint.Cap.ROUND; strokeWidth = grosorDp * d }
    private val texto = Paint(Paint.ANTI_ALIAS_FLAG).apply { textAlign = Paint.Align.CENTER; typeface = Letras.cifra; color = tono }
    private val caja = RectF()
    private var valor = 0f

    override fun onDraw(c: Canvas) {
        val m = trazo.strokeWidth / 2 + d
        caja.set(m, m, width - m, height - m)
        trazo.color = Colores.suave(tono, 0.15f); c.drawArc(caja, 0f, 360f, false, trazo)
        trazo.color = tono; c.drawArc(caja, -90f, 3.6f * valor, false, trazo)
        texto.textSize = height * 0.26f
        c.drawText("${valor.toInt()}%", width / 2f, height / 2f - (texto.descent() + texto.ascent()) / 2, texto)
    }

    fun animar(hasta: Int, retraso: Long = 250) = ValueAnimator.ofFloat(0f, hasta.coerceIn(0, 100).toFloat()).apply {
        duration = 1200; startDelay = retraso; interpolator = DecelerateInterpolator(1.6f)
        addUpdateListener { valor = it.animatedValue as Float; invalidate() }; start()
    }
}

internal class Ui(private val ctx: Context) {
    fun dp(n: Int) = (n * ctx.resources.displayMetrics.density + 0.5f).toInt()

    fun forma(color: Int, radio: Int = 16, borde: Int? = null) = GradientDrawable().apply {
        setColor(color); cornerRadius = dp(radio).toFloat(); if (borde != null) setStroke(dp(1), borde)
    }

    fun degradado(radio: Int = 16, vararg colores: Int) = GradientDrawable(GradientDrawable.Orientation.TL_BR, colores).apply { cornerRadius = dp(radio).toFloat() }

    private fun conOnda(fondo: GradientDrawable, onda: Int = 0x33FFFFFF) = RippleDrawable(ColorStateList.valueOf(onda), fondo, null)

    fun columna(padding: Int = 0) = LinearLayout(ctx).apply {
        orientation = LinearLayout.VERTICAL; if (padding > 0) setPadding(dp(padding), dp(padding), dp(padding), dp(padding))
    }

    fun fila() = LinearLayout(ctx).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }

    fun texto(t: CharSequence, tam: Float = 15f, color: Int = Colores.tinta, negrita: Boolean = false) = TextView(ctx).apply {
        text = t; textSize = tam; setTextColor(color); typeface = if (negrita) Letras.medio else Letras.normal
        setLineSpacing(0f, 1.15f)
    }

    fun titulo(t: CharSequence, tam: Float = 22f, color: Int = Colores.tinta) = texto(t, tam, color).apply { typeface = Letras.titulo; letterSpacing = -0.01f }

    fun icono(res: Int, color: Int, tam: Int = 22) = ImageView(ctx).apply {
        setImageResource(res); imageTintList = ColorStateList.valueOf(color)
        layoutParams = LinearLayout.LayoutParams(dp(tam), dp(tam))
    }

    /** Ícono dentro de un círculo de color suave. */
    fun iconoCirculo(res: Int, color: Int, tam: Int = 40) = ImageView(ctx).apply {
        setImageResource(res); imageTintList = ColorStateList.valueOf(color)
        background = forma(Colores.suave(color, 0.13f), tam); val p = dp(tam) / 4; setPadding(p, p, p, p)
        layoutParams = LinearLayout.LayoutParams(dp(tam), dp(tam))
    }

    /** Se encoge levemente al tocar, para que todo lo presionable responda. */
    @SuppressLint("ClickableViewAccessibility")
    fun presionable(v: View): View {
        v.setOnTouchListener { vista, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> vista.animate().scaleX(0.97f).scaleY(0.97f).setDuration(90).start()
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> vista.animate().scaleX(1f).scaleY(1f).setDuration(260)
                    .setInterpolator(OvershootInterpolator(3f)).start()
            }
            false
        }
        return v
    }

    fun tarjeta(padding: Int = 16) = columna(padding).apply {
        background = forma(Colores.blanco, 20); elevation = dp(3).toFloat(); translationZ = 0f
        outlineAmbientShadowColor(this)
    }

    private fun outlineAmbientShadowColor(v: View) {
        if (android.os.Build.VERSION.SDK_INT >= 28) { v.outlineAmbientShadowColor = Colores.vino; v.outlineSpotShadowColor = Colores.vino }
    }

    fun boton(t: String, primario: Boolean = true, icono: Int? = null, accion: () -> Unit): View {
        val color = if (primario) Colores.blanco else Colores.rojo
        val b = fila().apply {
            gravity = Gravity.CENTER; minimumHeight = dp(54); isClickable = true; isFocusable = true
            background = if (primario) conOnda(degradado(16, Colores.rojo, Colores.vino))
                         else conOnda(forma(Colores.blanco, 16, Colores.suave(Colores.rojo, 0.45f)), 0x229C1830)
            if (primario) { elevation = dp(4).toFloat(); outlineAmbientShadowColor(this) }
            setPadding(dp(18), 0, dp(18), 0)
            if (icono != null) addView(icono(icono, color, 20).apply { (layoutParams as LinearLayout.LayoutParams).marginEnd = dp(10) })
            addView(texto(t, 15.5f, color, true))
            contentDescription = t
            setOnClickListener { accion() }
        }
        return presionable(b)
    }

    fun enlace(t: String, accion: () -> Unit) = texto(t, 14f, Colores.rojo, true).apply {
        setPadding(dp(4), dp(10), dp(4), dp(10)); setOnClickListener { accion() }
    }

    fun campo(pista: String, tipo: Int = InputType.TYPE_CLASS_TEXT) = EditText(ctx).apply {
        // isSingleLine va ANTES de inputType: si va después, Android quita el ocultamiento de la contraseña.
        isSingleLine = true; hint = pista; inputType = tipo; typeface = Letras.normal
        textSize = 16f; setTextColor(Colores.tinta); setHintTextColor(Colores.gris)
        background = forma(Colores.blanco, 14, Colores.borde); setPadding(dp(14), dp(14), dp(14), dp(14))
        setOnFocusChangeListener { _, foco -> background = forma(Colores.blanco, 14, if (foco) Colores.rojo else Colores.borde) }
    }

    /** Campo con ícono a la izquierda y un accesorio opcional a la derecha (p. ej., mostrar contraseña). */
    fun campoIcono(icono: Int, pista: String, tipo: Int = InputType.TYPE_CLASS_TEXT, accesorio: View? = null): Pair<View, EditText> {
        val caja = fila().apply { background = forma(Colores.fondo, 16, Colores.borde); setPadding(dp(14), 0, dp(8), 0); minimumHeight = dp(54) }
        val ic = icono(icono, Colores.gris, 20)
        val e = EditText(ctx).apply {
            isSingleLine = true; hint = pista; inputType = tipo; typeface = Letras.normal; textSize = 16f
            setTextColor(Colores.tinta); setHintTextColor(Colores.gris); background = null; setPadding(dp(12), dp(14), dp(6), dp(14))
        }
        e.setOnFocusChangeListener { _, foco ->
            caja.background = forma(if (foco) Colores.blanco else Colores.fondo, 16, if (foco) Colores.rojo else Colores.borde)
            ic.imageTintList = ColorStateList.valueOf(if (foco) Colores.rojo else Colores.gris)
        }
        caja.addView(ic); caja.addView(e, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        if (accesorio != null) caja.addView(accesorio)
        return caja to e
    }

    fun etiqueta(t: String) = texto(t.uppercase(), 11.5f, Colores.gris, true).apply { letterSpacing = 0.08f; setPadding(dp(2), dp(14), 0, dp(6)) }

    fun insignia(t: String, color: Int, icono: Int? = null): View = fila().apply {
        background = forma(Colores.suave(color, 0.14f), 20); setPadding(dp(10), dp(5), dp(12), dp(5))
        if (icono != null) addView(icono(icono, color, 14).apply { (layoutParams as LinearLayout.LayoutParams).marginEnd = dp(5) })
        addView(texto(t, 12f, color, true))
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT)
    }

    fun barra(porcentaje: Int, color: Int = Colores.rojo, animar: Boolean = true) = ProgressBar(ctx, null, android.R.attr.progressBarStyleHorizontal).apply {
        max = 1000; progress = if (animar) 0 else porcentaje * 10
        progressTintList = ColorStateList.valueOf(color); progressBackgroundTintList = ColorStateList.valueOf(Colores.suave(color, 0.18f))
        scaleY = 1.6f
        if (animar) ValueAnimator.ofInt(0, porcentaje.coerceIn(0, 100) * 10).apply {
            duration = 1100; startDelay = 300; interpolator = DecelerateInterpolator(1.6f)
            addUpdateListener { progress = it.animatedValue as Int }; start()
        }
    }

    /** Hace subir un número desde 0 (efecto contador). */
    fun contar(tv: TextView, hasta: Int, formato: (Int) -> String = { it.toString() }, retraso: Long = 250) {
        tv.text = formato(0)
        ValueAnimator.ofInt(0, hasta).apply {
            duration = 900; startDelay = retraso; interpolator = DecelerateInterpolator()
            addUpdateListener { tv.text = formato(it.animatedValue as Int) }; start()
        }
    }

    /** Entrada escalonada: cada vista sube y aparece un poco después de la anterior. */
    fun entrada(vistas: List<View>, inicio: Long = 60) {
        vistas.forEachIndexed { i, v ->
            v.alpha = 0f; v.translationY = dp(28).toFloat()
            v.animate().alpha(1f).translationY(0f).setStartDelay(inicio + i * 55L).setDuration(420)
                .setInterpolator(DecelerateInterpolator(2f)).start()
        }
    }

    fun girar(v: View) { v.animate().rotationBy(360f).setDuration(700).setInterpolator(DecelerateInterpolator()).start() }

    fun animacion(raw: Int, tam: Int, repetir: Boolean = true) = LottieAnimationView(ctx).apply {
        setAnimation(raw); repeatCount = if (repetir) LottieDrawable.INFINITE else 0; playAnimation()
        layoutParams = LinearLayout.LayoutParams(dp(tam), dp(tam)).apply { gravity = Gravity.CENTER_HORIZONTAL }
    }

    fun margen(v: View, arriba: Int = 0, abajo: Int = 12, ancho: Int = ViewGroup.LayoutParams.MATCH_PARENT): View {
        v.layoutParams = LinearLayout.LayoutParams(ancho, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(arriba); bottomMargin = dp(abajo)
        }
        return v
    }
}
