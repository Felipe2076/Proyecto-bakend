package cl.laserena.siged.movil

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import org.json.JSONObject
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Almacenamiento local cifrado (AES-GCM con llave del AndroidKeyStore), fuera del respaldo de Android.
 * Guarda la sesión y la última copia de «mi trabajo» para mostrarla sin conexión.
 */
internal class Vault(context: Context) {
    private val root = File(context.noBackupFilesDir, "siged").apply { mkdirs() }
    private val key: SecretKey by lazy {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("siged_local_v1", null) as? SecretKey) ?: KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder("siged_local_v1", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
            generateKey()
        }
    }

    private fun write(f: File, plain: ByteArray) {
        val c = Cipher.getInstance("AES/GCM/NoPadding"); c.init(Cipher.ENCRYPT_MODE, key); c.updateAAD(f.name.toByteArray())
        val atom = AtomicFile(f); val stream = atom.startWrite()
        try { stream.write(c.iv + c.doFinal(plain)); atom.finishWrite(stream) } catch (e: Exception) { atom.failWrite(stream); throw e }
    }

    private fun read(f: File): ByteArray? {
        if (!f.exists()) return null
        val b = AtomicFile(f).readFully(); val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, b.copyOfRange(0, 12))); c.updateAAD(f.name.toByteArray())
        return c.doFinal(b.copyOfRange(12, b.size))
    }

    private fun obj(f: File): JSONObject? = try { read(f)?.let { JSONObject(it.toString(Charsets.UTF_8)) } } catch (_: Exception) { null }

    fun session() = obj(File(root, "sesion.enc"))
    fun session(s: JSONObject) = write(File(root, "sesion.enc"), s.toString().toByteArray())
    fun clearSession() {
        AtomicFile(File(root, "sesion.enc")).delete()
        root.listFiles { f -> f.name.startsWith("trabajo_") }?.forEach { it.delete() }
    }

    fun work(cuenta: String): JSONObject? = obj(File(root, "trabajo_${cuenta.filter { it.isLetterOrDigit() || it == '-' }}.enc"))
    fun work(cuenta: String, data: JSONObject) =
        write(File(root, "trabajo_${cuenta.filter { it.isLetterOrDigit() || it == '-' }}.enc"), data.toString().toByteArray())
}
