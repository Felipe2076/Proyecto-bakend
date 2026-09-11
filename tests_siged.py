import os
import sys
from typing import Any

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import Client
from requerimientos.views import (
    asignar_semaforo,
    cargar_requerimientos_json,
    obtener_clima_la_serena,
    validar_formulario_requerimiento,
)
from control_gestion.views import cargar_json_seguro
from cuentas.vocabulario import DELEGACIONES_OFICIALES, TIPOS_TICKET


def _login(client: Client, username: str = "admin", password: str = "admin123") -> None:
    response = client.post("/login/", {"username": username, "password": password}, follow=True)
    assert response.status_code == 200, f"Login falló para {username}: {response.status_code}"
    assert client.session.get("usuario"), f"No quedó sesión mock para {username}"


def run_tests() -> None:
    print("=" * 48)
    print("INICIANDO PRUEBAS DE INTEGRACIÓN SIGED")
    print("=" * 48)

    client = Client()
    errores: list[str] = []

    print("\n1. Probando carga de archivos JSON...")
    reqs = cargar_requerimientos_json()
    assert len(reqs) > 0, "requerimientos.json está vacío"
    print(f"   [OK] requerimientos.json: {len(reqs)} registros")

    areas = cargar_json_seguro("areas_soporte.json", [])
    assert len(areas) == 4, f"Se esperaban 4 áreas, se encontraron {len(areas)}"
    print(f"   [OK] areas_soporte.json: {len(areas)} áreas estratégicas")

    funcionarios = cargar_json_seguro("funcionarios.json", [])
    assert len(funcionarios) >= 8, "Faltan funcionarios de la matriz SGR"
    print(f"   [OK] funcionarios.json: {len(funcionarios)} fichas")

    usuarios = cargar_json_seguro("usuarios.json", [])
    assert len(usuarios) >= 4, "Faltan usuarios de demostración"
    print(f"   [OK] usuarios.json: {len(usuarios)} perfiles mock")

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

    print("\n5. Probando redirección a login sin sesión...")
    anon = Client()
    response_anon: Any = anon.get("/", follow=False)
    if response_anon.status_code in (301, 302) and "/login/" in response_anon["Location"]:
        print("   [OK] / redirige a /login/ sin sesión")
    else:
        msg = f"Se esperaba redirect a login, se obtuvo {response_anon.status_code}"
        errores.append(msg)
        print(f"   [FAIL] {msg}")

    print("\n6. Probando login mock...")
    bad = client.post("/login/", {"username": "admin", "password": "no-vale"})
    assert bad.status_code == 200
    assert not client.session.get("usuario")
    print("   [OK] Credencial inválida no inicia sesión")
    _login(client)

    primer_ticket_id = reqs[0]["id_ticket"]
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
    ventanilla = Client()
    _login(ventanilla, "ventanilla", "ventanilla123")
    resp_admin: Any = ventanilla.get("/administracion/usuarios/", follow=True)
    if resp_admin.status_code == 200:
        print("   [OK] Ventanilla no entra a administración (redirige al inicio)")
    else:
        msg = f"Admin con ventanilla devolvió {resp_admin.status_code}"
        errores.append(msg)
        print(f"   [FAIL] {msg}")

    print("\n9. Probando validación POST incompleto (no debe guardar)...")
    total_antes = len(cargar_requerimientos_json())
    resp_invalido: Any = client.post(
        "/requerimientos/nuevo/",
        data={"vecino_nombre": "Ana", "telefono_whatsapp": "123"},
        follow=True,
    )
    assert resp_invalido.status_code == 200
    total_despues_invalido = len(cargar_requerimientos_json())
    assert total_despues_invalido == total_antes, "Se guardó un ticket con datos inválidos"
    print("   [OK] POST inválido no persiste el requerimiento")

    print("\n10. Probando creación de nuevo ticket (POST)...")
    data_post = {
        "vecino_nombre": "Prueba Automática Valenzuela",
        "telefono_whatsapp": "+56 9 1234 5678",
        "email": "prueba.auto@serena.cl",
        "delegacion": "Delegación Centro",
        "canal_ingreso": "WhatsApp",
        "tipo_entrada": "CONSULTA",
        "area_tematica": "Seguridad Ciudadana",
        "descripcion": "Ticket de validación automática del sistema de persistencia JSON.",
        "funcionario_asignado": "Patrulla Sector 3 (Seguridad)",
    }
    response_post: Any = client.post("/requerimientos/nuevo/", data=data_post, follow=True)
    assert response_post.status_code == 200, f"Error en POST: {response_post.status_code}"

    reqs_after = cargar_requerimientos_json()
    guardado = any(
        item["vecino_nombre"] == "Prueba Automática Valenzuela"
        and item.get("canal_ingreso") == "WhatsApp"
        for item in reqs_after
    )
    assert guardado, "No se guardó el ticket en requerimientos.json"
    print("   [OK] Ticket insertado y verificado en requerimientos.json")

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
