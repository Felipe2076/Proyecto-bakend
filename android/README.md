# SIGED Móvil (Android, Kotlin)

App del funcionario municipal de La Serena. Identificador `cl.laserena.siged.movil`, Android 8.0 o superior.
Usa la API v1 del Django (`/api/v1/`), la misma base MySQL y los mismos archivos que la web.

## Qué hace (solo esto)
- **Ingreso** con RUT y contraseña. Enlace **«¿Olvidaste tu contraseña?»**: recuperación en tres pasos
  (correo → código de verificación de 6 dígitos que llega por correo → nueva contraseña). El código vence en
  10 minutos, se puede reenviar cada 60 s y cambiar la clave cierra las sesiones en otros teléfonos.
- **Perfil**: foto (cámara o galería), nombre, RUT, correo, cargo, delegación. Cerrar sesión.
- **Trimestre**: periodo vigente, día en curso (día N de M), avance y días restantes.
- **Asistencia**: días hábiles del trimestre con al menos una actividad registrada y si hoy ya hay registro.
- **Mis actividades** (tubo de trabajo): filtro por **Ingresado, Pendiente, En proceso, Realizado y Vencido**.
- **Evidencias**: en cada actividad, **Tomar foto** o **Subir foto o documento PDF** (hasta 10 MB; las fotos se
  reducen y se corrige la orientación antes de enviarlas). Se ven también en la ficha web del compromiso.
- **Animaciones Lottie** escritas en texto plano (JSON) en `app/src/main/res/raw/`: `siged_carga.json`
  (carga), `siged_exito.json` (visto de éxito) y `siged_vacio.json` (lista vacía). Se pueden abrir y editar en
  lottiefiles.com.

## Código
| Archivo | Contenido |
|---|---|
| `MainActivity.kt` | Todas las pantallas: ingreso, recuperación, inicio, detalle, perfil, subida de archivos |
| `Api.kt` | Cliente HTTPS sin librerías externas; errores del servidor en español |
| `Vault.kt` | Sesión y última copia de «mi trabajo» cifradas con AES-GCM (AndroidKeyStore), fuera del respaldo |
| `Ui.kt` | Colores municipales y componentes (tarjetas, botones, insignias, barras, animaciones) |

## Compilar y probar
Abrir la carpeta `android` en Android Studio (JDK incluido en Android Studio, SDK 37).

- Contra un Django local con datos ficticios (emulador):
  `gradlew.bat :app:assembleDebug -PsigedTestUrl=http://10.0.2.2:8765`
- Versión para entregar (usa `https://54.205.69.94`): `gradlew.bat :app:assembleRelease` y firmar con la llave
  de la entrega (no se guarda en el código).

## Servidor necesario
Endpoints: `sesion/`, `sesion/renovar/`, `sesion/cerrar/`, `recuperar/`, `recuperar/verificar/`,
`recuperar/nueva/`, `mi-trabajo/`, `perfil/foto/`, `usuarios/<codigo>/foto/`, `compromisos/<codigo>/evidencias/`,
`evidencias/<id>/`. Detalle en `web/docs/API_MOVIL.md`. Requieren desplegar las migraciones nuevas del Django
(hasta `control_gestion.0017_evidencia_compromiso`) y tener el correo SMTP configurado para enviar los códigos.
