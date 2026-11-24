"""Importa la base de organizaciones (JSON) como fichas pendientes de verificación.

- Valida fila por fila e informa el número de cada fila con error, sin detenerse en la primera.
- Los códigos ``ORG-SRC-…`` salen de la clave de origen completa, sin colisiones.
- Por defecto solo simula. ``--aplicar`` guarda; ``--actualizar`` además refresca las fichas
  ya importadas (misma clave de origen) que nadie ha verificado.
"""
import json
import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from control_gestion.models import OrganizacionComunitaria

CAMPOS = {'clave_origen', 'nombre', 'domicilio_legal', 'territorio', 'socios_activos', 'fecha_constitucion',
          'registro_personalidad_juridica', 'fecha_inscripcion', 'registro_directiva'}
OPCIONALES = {'delegacion', 'descripcion', 'tipo', 'telefono', 'correo'}


def codigo_desde_clave(clave):
    """``ORG-SRC-`` + la clave sin símbolos (máx. 30 caracteres en total)."""
    limpio = re.sub(r'[^A-Za-z0-9]', '', str(clave)).upper()
    return ('ORG-SRC-' + limpio)[:30]


class Command(BaseCommand):
    help = 'Importa la base de organizaciones como fichas pendientes de verificación; conserva lo existente.'

    def add_arguments(self, parser):
        parser.add_argument('archivo')
        parser.add_argument('--aplicar', action='store_true', help='Guarda (sin esto solo simula).')
        parser.add_argument('--actualizar', action='store_true',
                            help='Actualiza fichas importadas antes que sigan sin verificar.')

    def handle(self, *args, **options):
        ruta = Path(options['archivo'])
        try:
            rows = json.loads(ruta.read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise CommandError(f'No existe el archivo {ruta}.')
        except json.JSONDecodeError as error:
            raise CommandError(f'El archivo no es JSON válido (línea {error.lineno}): {error.msg}.')
        if not isinstance(rows, list):
            raise CommandError('Se requiere una lista de organizaciones.')

        from cuentas.models import Delegacion
        delegaciones = {d.nombre.casefold(): d for d in Delegacion.objects.all()}
        errores, claves, codigos, filas = [], set(), set(), []
        for numero, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errores.append(f'Fila {numero}: no es un objeto.')
                continue
            faltan, sobran = CAMPOS - set(row), set(row) - CAMPOS - OPCIONALES
            if faltan or sobran:
                errores.append(f'Fila {numero}: faltan {sorted(faltan)} / sobran {sorted(sobran)}.')
                continue
            clave = str(row['clave_origen'] or '').strip()
            if not clave or not str(row['nombre'] or '').strip():
                errores.append(f'Fila {numero}: clave de origen o nombre vacío.')
                continue
            codigo = codigo_desde_clave(clave)
            if clave in claves or codigo in codigos:
                errores.append(f'Fila {numero}: la clave de origen «{clave}» está repetida.')
                continue
            claves.add(clave)
            codigos.add(codigo)
            datos = {k: row[k] for k in CAMPOS | (OPCIONALES & set(row)) if k != 'delegacion'}
            datos['clave_origen'] = clave
            delegacion = None
            if row.get('delegacion'):
                delegacion = delegaciones.get(str(row['delegacion']).casefold())
                if delegacion is None:
                    errores.append(f'Fila {numero}: la delegación «{row["delegacion"]}» no existe.')
                    continue
            obj = OrganizacionComunitaria(codigo=codigo, verificada=False, delegacion=delegacion, **datos)
            try:
                obj.full_clean(exclude=['codigo'], validate_unique=False, validate_constraints=False)
            except ValidationError as error:
                detalle = '; '.join(f'{campo}: {" ".join(m)}' for campo, m in error.message_dict.items())
                errores.append(f'Fila {numero} ({clave}): {detalle}')
                continue
            filas.append(obj)

        if errores:
            for linea in errores[:50]:
                self.stderr.write(linea)
            raise CommandError(f'{len(errores)} fila(s) con error; no se importó nada. Corrija el archivo y repita.')

        existentes = {o.clave_origen: o for o in OrganizacionComunitaria.objects.filter(clave_origen__in=claves)}
        ocupados = set(OrganizacionComunitaria.objects.filter(codigo__in=codigos).exclude(clave_origen__in=claves)
                       .values_list('codigo', flat=True))
        if ocupados:
            raise CommandError(f'Estos códigos ya existen con otra clave: {sorted(ocupados)[:10]}.')
        nuevos = [o for o in filas if o.clave_origen not in existentes]
        actualizables = [o for o in filas if o.clave_origen in existentes and not existentes[o.clave_origen].verificada]
        if options['aplicar']:
            with transaction.atomic():
                for obj in nuevos:
                    obj.save()  # pasa por save(): asigna uuid y fecha de actualización
                if options['actualizar']:
                    for obj in actualizables:
                        actual = existentes[obj.clave_origen]
                        for campo in CAMPOS - {'clave_origen'}:
                            setattr(actual, campo, getattr(obj, campo))
                        actual.save()
        self.stdout.write(
            f"Registros fuente: {len(rows)}; nuevos: {len(nuevos)}; existentes: {len(existentes)}"
            f"{f' (actualizables sin verificar: {len(actualizables)})' if options['actualizar'] else ''}; "
            f"aplicado: {options['aplicar']}")
