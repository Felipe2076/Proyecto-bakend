"""Foto de perfil: validación, recorte, entrega autenticada y pantalla «Mi perfil».

- Se aceptan JPG, PNG y WebP de hasta 5 MB.
- Se valida el contenido real con Pillow (no solo la extensión) y se limita la resolución.
- Se recorta al centro en cuadrado, se reduce a 512×512 y se vuelve a codificar como JPEG.
  Eso elimina metadatos (EXIF, ubicación GPS del celular) y cualquier contenido incrustado.
- El archivo vive en el volumen privado (MEDIA_ROOT/fotos/<uuid>.jpg) y solo se entrega por
  una vista con sesión o token, con el mismo alcance por delegación que la lista de usuarios.
"""
import hashlib
from io import BytesIO

from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponseNotModified
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELES = 40_000_000
LADO = 512
FORMATOS = {"JPEG", "MPO", "PNG", "WEBP"}


class FotoInvalida(ValueError):
    pass


def procesar_foto(archivo):
    """Devuelve un ContentFile JPEG 512×512 listo para guardar, o lanza FotoInvalida."""
    if archivo is None:
        raise FotoInvalida("Elija una imagen.")
    if archivo.size > MAX_BYTES:
        raise FotoInvalida(f"La imagen pesa {archivo.size / 1048576:.1f} MB; el máximo es 5 MB.")
    try:
        imagen = Image.open(archivo)
        if imagen.format not in FORMATOS:
            raise FotoInvalida("Use una imagen JPG, PNG o WebP.")
        ancho, alto = imagen.size
        if ancho * alto > MAX_PIXELES:
            raise FotoInvalida("La imagen tiene una resolución demasiado alta.")
        if min(ancho, alto) < 64:
            raise FotoInvalida("La imagen es demasiado pequeña (mínimo 64×64 píxeles).")
        imagen.verify()
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen = ImageOps.exif_transpose(imagen)  # respeta la orientación del celular antes de borrar EXIF
        imagen = ImageOps.fit(imagen.convert("RGB"), (LADO, LADO), Image.Resampling.LANCZOS)
    except FotoInvalida:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise FotoInvalida("El archivo no es una imagen válida o está dañado.")
    finally:
        try:
            archivo.seek(0)
        except (AttributeError, OSError):
            pass
    salida = BytesIO()
    imagen.save(salida, "JPEG", quality=85, optimize=True, progressive=True)
    return ContentFile(salida.getvalue(), name="foto.jpg")


def guardar_foto(usuario, archivo):
    """Reemplaza la foto del usuario; borra el archivo anterior solo después de guardar la nueva."""
    contenido = procesar_foto(archivo)
    anterior = usuario.foto.name if usuario.foto else ""
    usuario.foto.save("foto.jpg", contenido, save=False)
    usuario.foto_actualizada = timezone.now()
    usuario.save(update_fields=["foto", "foto_actualizada"])
    if anterior and anterior != usuario.foto.name:
        usuario.foto.storage.delete(anterior)


def quitar_foto(usuario):
    if usuario.foto:
        nombre = usuario.foto.name
        usuario.foto = None
        usuario.foto_actualizada = timezone.now()
        usuario.save(update_fields=["foto", "foto_actualizada"])
        usuario.foto.storage.delete(nombre)


def iniciales(nombre):
    partes = [p for p in (nombre or "").replace("(ficticio)", "").split() if p[:1].isalpha()]
    return ((partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")) if partes else "?").upper()


def url_foto(usuario):
    """URL autenticada de la foto, con versión para que el navegador no muestre una antigua."""
    if not usuario or not usuario.foto or not usuario.codigo:
        return ""
    from django.urls import reverse

    version = int(usuario.foto_actualizada.timestamp()) if usuario.foto_actualizada else 0
    return f"{reverse('foto_usuario', args=[usuario.codigo])}?v={version}"


def puede_ver_foto(perfil, usuario):
    """Misma regla que la lista de usuarios: la propia, superusuario o la misma delegación."""
    if perfil is None or usuario is None:
        return False
    if perfil.pk == usuario.pk or perfil.rol.codigo == "superusuario":
        return True
    return bool(perfil.delegacion_id) and perfil.delegacion_id == usuario.delegacion_id


def respuesta_foto(request, usuario):
    if not usuario.foto:
        raise Http404("Sin foto")
    etiqueta = '"' + hashlib.sha256(f"{usuario.foto.name}:{usuario.foto_actualizada}".encode()).hexdigest()[:32] + '"'
    if request.headers.get("If-None-Match") == etiqueta:
        respuesta = HttpResponseNotModified()
    else:
        try:
            respuesta = FileResponse(usuario.foto.open("rb"), content_type="image/jpeg")
        except (FileNotFoundError, OSError):
            raise Http404("Sin foto")
    respuesta["ETag"] = etiqueta
    respuesta["Cache-Control"] = "private, max-age=300"
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return respuesta


@require_safe
def ver_foto(request, codigo):
    from cuentas.models import Usuario

    perfil = getattr(request, "_perfil_siged", None)
    usuario = Usuario.objects.select_related("rol").filter(codigo=codigo).first()
    if not puede_ver_foto(perfil, usuario):
        raise Http404("Sin foto")
    respuesta = respuesta_foto(request, usuario)
    # La cabecera no-store general de páginas privadas no aplica a la imagen versionada.
    respuesta["Cache-Control"] = "private, max-age=300"
    return respuesta


@require_http_methods(["GET", "POST"])
def mi_perfil(request):
    perfil = getattr(request, "_perfil_siged", None)
    if perfil is None:
        return redirect("login")
    error = ""
    if request.method == "POST":
        accion = request.POST.get("accion", "subir")
        if accion == "quitar":
            quitar_foto(perfil)
            messages.success(request, "Se quitó su foto de perfil.")
            return redirect("mi_perfil")
        try:
            guardar_foto(perfil, request.FILES.get("foto"))
        except FotoInvalida as motivo:
            error = str(motivo)
            messages.error(request, f"No se guardó la foto: {error}")
        else:
            messages.success(request, "Foto de perfil actualizada.")
            return redirect("mi_perfil")
    funcionario = perfil.funcionario if perfil.funcionario_id else None
    return render(request, "cuentas/mi_perfil.html", {
        "perfil": perfil,
        "funcionario": funcionario,
        "foto_url": url_foto(perfil),
        "iniciales": iniciales(perfil.nombre),
        "error_foto": error,
    })
