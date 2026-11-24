# API móvil SIGED v1 (`/api/v1/`)

JSON sobre HTTPS. Autenticación con `Authorization: Bearer <token>` (nunca cookies). Todas las respuestas,
incluidos los errores, son JSON: `{"error": "texto en español", "campos": {"campo": ["motivo"]}}`.

| Código | Significado |
|---|---|
| 200 / 201 | Correcto / creado |
| 400 | Parámetro mal formado (p. ej. `desde`) |
| 401 | Token vencido, revocado, o cambió la contraseña: volver a iniciar sesión |
| 403 | El perfil no tiene ese permiso |
| 404 | No existe o está fuera de la delegación |
| 409 | Conflicto: otra persona cambió el registro (viene `servidor` con la versión vigente) o `client_id` reutilizado con otros datos |
| 413 | Envío demasiado grande |
| 422 | Datos inválidos (ver `campos`) |
| 429 | Demasiados intentos o solicitudes: esperar |

## Sesión
| Método y ruta | Uso |
|---|---|
| `POST sesion/` `{rut, password, dispositivo?}` | Devuelve `token` (30 días), `expira`, `perfil` |
| `POST sesion/renovar/` | Token nuevo; el anterior queda anulado. Llamarlo cuando falten < 7 días |
| `POST sesion/cerrar/` | Cierra la sesión actual |
| `GET sesiones/` · `DELETE sesiones/<id>/` | Ver y cerrar sesiones abiertas en otros dispositivos |

Cambiar la contraseña o desactivar la cuenta invalida todos los tokens.

## Perfil, usuarios y fotos
| Método y ruta | Uso |
|---|---|
| `GET perfil/` | Datos propios, `foto_url` y permisos (`organizaciones_crear/editar`) |
| `POST perfil/foto/` (multipart `foto`) | JPG/PNG/WebP ≤ 5 MB; el servidor la recorta a 512×512 y quita EXIF/GPS |
| `DELETE perfil/foto/` | Quita la foto |
| `GET usuarios/?desde=` | Usuarios de su delegación (superusuario: todos). Sin RUT de terceros |
| `GET usuarios/<codigo>/foto/` | Imagen JPEG con Bearer; responde `ETag` (usar `If-None-Match`) |

## Organizaciones comunitarias
| Método y ruta | Uso |
|---|---|
| `GET organizaciones/?desde=&cursor=` | Hasta 500 por página; seguir con `siguiente` mientras no sea `null` |
| `POST organizaciones/` | Alta. Obligatorio `client_id` (UUID generado en el teléfono). Reintentar con el mismo `client_id` devuelve la misma ficha (`repetido: true`) |
| `GET organizaciones/<codigo>/` | Una ficha |
| `PATCH organizaciones/<codigo>/` | Cambio parcial. Obligatorio `version` (la que tiene el teléfono) |

Campos: `nombre, tipo (JJVV|FUNCIONAL|DEPORTIVA|ADULTO_MAYOR|CULTURAL|OTRA), telefono, correo, descripcion,
domicilio_legal, delegacion (id), territorio, presidente_nombre, presidente_rut, tesorero_nombre, tesorero_rut,
secretario_nombre, secretario_rut, vigencia_directiva_hasta, socios_activos, fecha_constitucion,
registro_personalidad_juridica, fecha_inscripcion, registro_directiva, verificada, activa`. Fechas `AAAA-MM-DD`.
Las mismas validaciones del sitio web; los RUT con dígito incorrecto se aceptan y vuelven en `avisos`.
Los RUT de la directiva solo se entregan a perfiles con permiso de edición.

## Catálogos y sincronización
| Método y ruta | Uso |
|---|---|
| `GET catalogos/` | Delegaciones, territorios y tipos de organización |
| `GET sync/?desde=<servidor_ahora anterior>` | Todo lo cambiado desde esa marca: `perfil, usuarios, delegaciones, territorios, organizaciones` (+ `organizaciones_siguiente`) y `bajas` |

### Protocolo recomendado para el SQLite del teléfono
1. Primera vez: `GET sync/` sin `desde`; guardar cada fila por `uuid` y guardar `servidor_ahora`.
2. Siguientes: `GET sync/?desde=<servidor_ahora guardado>`; hacer *upsert* por `uuid`; borrar localmente los `uuid` de `bajas`
   (y las organizaciones con `eliminado_en`/`activa=false` según la pantalla). Si `organizaciones_siguiente` no es nulo,
   seguir con `GET organizaciones/?desde=…&cursor=…`.
3. Cambios hechos sin conexión: cola local. Altas con `client_id` fijo por registro; cambios con la `version` local.
   Ante 409, mostrar la ficha de `servidor` y dejar que la persona decida (no sobrescribir en silencio).
4. Guardar el nuevo `servidor_ahora` solo después de aplicar todo el lote.

Tabla local sugerida: `organizacion(uuid PK, codigo, nombre, tipo, telefono, correo, delegacion_id, territorio,
datos_json, version, actualizado, pendiente_envio, client_id)`; `usuario(uuid PK, codigo, nombre, cargo,
delegacion, foto_url, foto_local, version)`; `meta_sync(clave PK, valor)` para `servidor_ahora`.

## Despliegue
Las columnas nuevas nacen vacías. Tras desplegar, una vez: `python manage.py completar_sincronizacion --aplicar`
(y opcionalmente `asignar_delegacion_organizaciones` para revisar las organizaciones sin delegación).
