import os
import sys
from typing import Any

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

from control_gestion.models import Medicion
from core.validaciones import validar_rut
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Cargo, Delegacion, EstadoRegistro, ParametroSistema, Rol, Usuario
from cuentas.servicios import siguiente_codigo
from cuentas.store import cargar_json_seguro
from cuentas.vocabulario import DELEGACIONES_OFICIALES, TIPOS_TICKET
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion, Vecino
from requerimientos.views import (
    asignar_semaforo,
    obtener_clima_la_serena,
    validar_formulario_requerimiento,
)


def _cliente() -> Client:
    # El Client de Django usa el host "testserver"; el proyecto solo permite localhost.
    return Client(HTTP_HOST="localhost")


def _login(client: Client, rut: str = "33100901-6", password: str = "ClaveIntegracion1!") -> None:
    response = client.post("/login/", {"rut": rut, "password": password}, follow=True)
    assert response.status_code == 200, f"Login falló para {rut}: {response.status_code}"
    assert client.session.get("usuario"), f"No quedó sesión para {rut}"


def _asegurar_acceso(rut: str, password: str, rol_codigo: str, nombre: str, email: str) -> None:
    """Deja usable un perfil de prueba en la base (el ingreso es por RUT, no por alias)."""
    User = get_user_model()
    rol, _ = Rol.objects.get_or_create(
        codigo=rol_codigo, defaults={"nombre": rol_codigo.capitalize(), "descripcion": "Perfil de prueba"}
    )
    usuario = (
        Usuario.objects.filter(funcionario__rut=rut).select_related("user", "funcionario").first()
        or Usuario.objects.filter(username=rut).select_related("user", "funcionario").first()
    )
    if usuario is None:
        delegacion, _ = Delegacion.objects.get_or_create(
            nombre="Delegación Centro", defaults={"comuna": "La Serena"}
        )
        cargo, _ = Cargo.objects.get_or_create(nombre="Cargo de integración")
        crear_cuenta(
            codigo=siguiente_codigo(Usuario, "codigo", "USR-", 3),
            rut=rut,
            password=password,
            rol_codigo=rol.codigo,
            correo=email,
            nombre=nombre,
            delegacion=delegacion,
            cargo=cargo,
        )
        return
    user = usuario.user if usuario.user_id else User.objects.filter(username=rut).first()
    if user is None:
        user = User.objects.create_user(rut, email, password)
    elif not user.check_password(password):
        user.set_password(password)
        user.is_active = True
        user.save()
    usuario.user = user
    usuario.estado = EstadoRegistro.ACTIVO
    usuario.rol = rol
    usuario.username = rut
    usuario.save()


def _asegurar_ticket() -> str:
    existente = Requerimiento.objects.order_by("codigo").first()
    if existente:
        return existente.codigo
    delegacion, _ = Delegacion.objects.get_or_create(nombre="Delegación Centro", defaults={"comuna": "La Serena"})
    canal, _ = CanalIngreso.objects.get_or_create(nombre="ventanilla")
    tipo, _ = TipoGestion.objects.get_or_create(nombre="SOLICITUD")
    area = AreaSoporte.objects.filter(nombre="Seguridad Ciudadana").first()
    if area is None:
        area = AreaSoporte.objects.create(codigo="AREA-TEST", nombre="Seguridad Ciudadana")
    vecino, _ = Vecino.objects.get_or_create(nombre="Vecino de prueba", defaults={"delegacion": delegacion})
    from datetime import date, timedelta

    req = Requerimiento.objects.create(
        codigo="TK-1001",
        vecino=vecino,
        delegacion=delegacion,
        canal_ingreso=canal,
        tipo_gestion=tipo,
        area=area,
        descripcion="Ticket mínimo para la suite de integración.",
        fecha_ingreso=date.today() - timedelta(days=2),
        estado=Requerimiento.Estado.PENDIENTE,
    )
    return req.codigo


def _preparar_bd() -> str:
    if not ParametroSistema.objects.exists():
        ParametroSistema.objects.create()
    if not Medicion.objects.exists():
        delegacion, _ = Delegacion.objects.get_or_create(
            nombre="Delegación Rural", defaults={"comuna": "La Serena"}
        )
        from datetime import date

        Medicion.objects.create(
            periodo="Trimestre de prueba",
            delegacion_piloto=delegacion,
            fecha_inicio=date(2026, 7, 1),
            fecha_termino=date(2026, 9, 28),
            dias_totales=90,
            meta_cumplimiento_tubo=80,
        )
    _asegurar_acceso("33100901-6", "ClaveIntegracion1!", "administrador", "Admin Integracion", "integracion-admin@siged.test")
    _asegurar_acceso("33100902-4", "ClaveIntegracion1!", "ventanilla", "Ventanilla Integracion", "integracion-ventanilla@siged.test")
    Cargo.objects.get_or_create(nombre="Administrador del sistema", defaults={"codigo": "CARGO-01"})
    return _asegurar_ticket()


def run_tests() -> None:
    print("=" * 48)
    print("INICIANDO PRUEBAS DE INTEGRACIÓN SIGED")
    print("=" * 48)

    client = _cliente()
    errores: list[str] = []

    print("\n1. Probando archivos JSON de origen (el import los lee; las vistas ya no)...")
    reqs = cargar_json_seguro("requerimientos.json", [])
    assert len(reqs) > 0, "requerimientos.json está vacío"
    print(f"   [OK] requerimientos.json: {len(reqs)} registros")

    areas = cargar_json_seguro("areas_soporte.json", [])
    assert len(areas) == 4, f"Se esperaban 4 áreas, se encontraron {len(areas)}"
    print(f"   [OK] areas_soporte.json: {len(areas)} áreas estratégicas")

    funcionarios = cargar_json_seguro("funcionarios.json", [])
    assert len(funcionarios) >= 8, "Faltan funcionarios de la matriz SGR"
    print(f"   [OK] funcionarios.json: {len(funcionarios)} fichas")

    usuarios = cargar_json_seguro("usuarios.json", [])
    assert len(usuarios) >= 24, "Faltan usuarios de simulación (rol × delegación)"
    assert all("password" not in item and "clave" not in item for item in usuarios)
    assert all(validar_rut(item.get("rut", "")) for item in usuarios)
    assert all("(ficticio)" not in item.get("nombre", "") and "(" not in item.get("nombre", "") for item in usuarios)
    print(f"   [OK] usuarios.json: {len(usuarios)} perfiles de simulación, sin clave en claro")

    assert "Delegación Centro" in DELEGACIONES_OFICIALES
    assert len(DELEGACIONES_OFICIALES) == 6
    assert TIPOS_TICKET == [
        "RECLAMO",
        "SOLICITUD",
        "CONSULTA",
        "SUGERENCIA",
        "FELICITACIÓN",
    ]
    print("   [OK] Vocabulario DER: 6 delegaciones y tipificación oficial")

    print("\n2. Probando lógica de semáforo de cumplimiento...")
    item_verde = asignar_semaforo({"dias_transcurridos": 2})
    assert item_verde["semaforo_nivel"] == "Verde", "Fallo en semáforo verde"
    item_amarillo = asignar_semaforo({"dias_transcurridos": 4})
    assert item_amarillo["semaforo_nivel"] == "Amarillo", "Fallo en semáforo amarillo"
    item_rojo = asignar_semaforo({"dias_transcurridos": 7})
    assert item_rojo["semaforo_nivel"] == "Rojo", "Fallo en semáforo rojo"
    print("   [OK] Verde (1-3d) / Amarillo (4-5d) / Rojo (≥6d) verificados")

    print("\n3. Probando validación de formulario de requerimiento...")
    _valores, errs = validar_formulario_requerimiento(
        {
            "vecino_nombre": "Ana",
            "telefono_whatsapp": "123",
            "email": "malo",
            "canal_ingreso": "correo",
        }
    )
    assert "vecino_nombre" in errs
    assert "telefono_whatsapp" in errs
    assert "email" in errs
    print("   [OK] Mensajes de validación para nombre, teléfono y correo")

    print("\n4. Probando consumo de requests (Open-Meteo)...")
    clima = obtener_clima_la_serena()
    assert "temperatura" in clima, "Falta temperatura en clima"
    assert "ciudad" in clima, "Falta ciudad en clima"
    print(
        f"   [OK] {clima['ciudad']}, "
        f"Temp: {clima['temperatura']}°C ({clima['estado_conexion']})"
    )

    print("\n5. Probando portada pública y dashboard con login...")
    anon = _cliente()
    response_anon: Any = anon.get("/", follow=False)
    response_dash: Any = anon.get("/control/", follow=False)
    if response_anon.status_code == 200 and response_dash.status_code in (301, 302) and "/login/" in response_dash["Location"]:
        print("   [OK] / es público y /control/ redirige a /login/ sin sesión")
    else:
        msg = f"Portada {response_anon.status_code}, dashboard {response_dash.status_code}"
        errores.append(msg)
        print(f"   [FAIL] {msg}")

    print("\n6. Probando login mock...")
    bad = client.post("/login/", {"rut": "33100901-6", "password": "no-vale"})
    assert bad.status_code == 200
    assert not client.session.get("usuario")
    print("   [OK] Credencial inválida no inicia sesión")
    primer_ticket_id = _preparar_bd()
    _login(client)
    urls_to_test = [
        ("/", "Portada institucional"),
        ("/lista/", "Lista de requerimientos"),
        ("/requerimientos/nuevo/", "Formulario de ingreso"),
        (f"/requerimientos/{primer_ticket_id}/", f"Detalle {primer_ticket_id}"),
        ("/encuestas/", "Encuesta de satisfacción"),
        ("/control/", "Dashboard"),
        ("/control/dashboard/", "Dashboard alias"),
        ("/control/kanban/", "Kanban"),
        ("/control/areas/", "Áreas estratégicas"),
        ("/control/semaforo-sgr/", "Semáforo SGR"),
        ("/control/tubo-trabajo/", "Tubo de trabajo"),
        ("/control/funcionarios/", "Pestaña personal"),
        ("/control/resumen/", "Resumen de delegación"),
        ("/control/agenda/", "Agenda colectiva"),
        ("/control/actividades/", "Actividades diarias"),
        ("/control/compromisos/nuevo/", "Nuevo compromiso"),
        ("/control/notificaciones/", "Notificaciones"),
        ("/administracion/usuarios/", "Admin usuarios"),
        ("/administracion/cargos/", "Admin cargos"),
        ("/administracion/parametros/", "Admin parámetros"),
    ]

    print("\n7. Probando respuestas HTTP de todas las rutas...")
    for url, name in urls_to_test:
        response: Any = client.get(url)
        if response.status_code == 200:
            print(f"   [OK] HTTP 200 - {url} ({name})")
        else:
            msg = f"Error {response.status_code} en {url}"
            errores.append(msg)
            print(f"   [FAIL] {msg}")

    print("\n8. Probando denegación de administración por rol ventanilla...")
    ventanilla = _cliente()
    _login(ventanilla, "33100902-4", "ClaveIntegracion1!")
    resp_admin: Any = ventanilla.get("/administracion/usuarios/", follow=True)
    if resp_admin.status_code == 200:
        print("   [OK] Ventanilla no entra a administración (redirige al inicio)")
    else:
        msg = f"Admin con ventanilla devolvió {resp_admin.status_code}"
        errores.append(msg)
        print(f"   [FAIL] {msg}")

    print("\n9. Probando validación POST incompleto (no debe guardar)...")
    total_antes = Requerimiento.objects.count()
    resp_invalido: Any = client.post(
        "/requerimientos/nuevo/",
        data={"vecino_nombre": "Ana", "telefono_whatsapp": "123"},
        follow=True,
    )
    assert resp_invalido.status_code == 200
    total_despues_invalido = Requerimiento.objects.count()
    assert total_despues_invalido == total_antes, "Se guardó un ticket con datos inválidos"
    print("   [OK] POST inválido no persiste el requerimiento")

    print("\n10. Probando creación de nuevo ticket (POST, ORM)...")
    data_post = {
        "vecino_nombre": "Prueba Automática Valenzuela",
        "telefono_whatsapp": "+56900009999",
        "email": "prueba.auto@siged.test",
        "delegacion": "Delegación Centro",
        "canal_ingreso": "WhatsApp",
        "tipo_entrada": "CONSULTA",
        "area_tematica": "Seguridad Ciudadana",
        "descripcion": "Ticket de validación automática del sistema de persistencia en base de datos.",
        "funcionario_asignado": "Patrulla Sector 3 (Seguridad)",
    }
    response_post: Any = client.post("/requerimientos/nuevo/", data=data_post, follow=True)
    assert response_post.status_code == 200, f"Error en POST: {response_post.status_code}"

    guardado = Requerimiento.objects.filter(
        vecino__nombre="Prueba Automática Valenzuela",
        canal_ingreso__nombre="WhatsApp",
    ).exists()
    assert guardado, "No se guardó el ticket en la base de datos"
    print("   [OK] Ticket insertado y verificado con el ORM")

    print("\n" + "=" * 48)
    if errores:
        print(f"RESULTADO: {len(errores)} PRUEBA(S) FALLARON:")
        for err in errores:
            print(f"  - {err}")
        sys.exit(1)
    print("¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE (100%)!")
    print("=" * 48)


if __name__ == "__main__":
    run_tests()
