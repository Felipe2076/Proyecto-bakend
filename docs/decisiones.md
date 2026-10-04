# Decisiones de la prioridad 1

Inventario hecho sobre el repositorio en el tag `sumativa2-backend` (commit `fd2fb32`). No hubo acceso a un MySQL local ni a la instancia del curso, así que los conteos son los del código y los fixtures, no un `SELECT` en el servidor.

## EQ-01 — qué había antes de reescribir

- `fixtures/02_datos_sistema.json`: 10 funcionarios, 4 usuarios, 21 vecinos. Cuatro RUT de vecino (pk 18–21) no pasaban el dígito verificador.
- `data/usuarios.json`: cuatro claves en texto plano y correos con nombres propios. Esos valores no se vuelven a escribir aquí.
- Nombres de personas en funcionarios, vecinos y textos de contacto. No había un RUT de funcionario: el acceso era un alias (`admin`, `jefatura`, …).
- El historial de Git conserva esos datos. No se reescribió.

## Decisiones

- **D-1.** No reescribir la historia. El tag `sumativa2-backend` queda en el commit ya evaluado y no se mueve.
- **D-2.** Se mantiene `django.contrib.auth` y el ORM. Quitar el ORM es otra tarea y queda a la espera de confirmación del profesor. Los scripts `V017`, `D003`, `V018` y `V019` describen el mismo cambio de esquema.
- **D-3.** La recuperación envía un código de 6 dígitos por correo (consola si `DEBUG=True`). Vive en `codigo_un_uso` (`V019`, propósito `RECUPERAR_CLAVE`). El hash es HMAC-SHA256 (hex de 64 caracteres, `hmac.compare_digest`). La clave es `SIGED_CODE_HMAC_KEY` y, si no está definida, `SECRET_KEY`; las dos salen del entorno y no hay un valor fijo en el código. No es un cifrado reversible ni `make_password`. Vence a los 10 minutos y admite 5 intentos. Un acierto escribe `usado_en`; emitir otro escribe `anulado_en` en los anteriores vigentes. La sesión guarda el id del usuario y, después de acertar, una marca de verificado. No guarda el código. `V023` del plan (EQ-41, `rol.exige_mfa` y sesión en `cuentas_usuario`) no es esta tabla.
- **D-4.** RUT de simulación en `33.100.001–33.100.999` (funcionarios) y `33.500.001–33.509.999` (vecinos), con dígito verificador válido. El nombre guardado no lleva la marca; `es_simulacion` (ya en `V017`) la agrega solo al mostrar. Correos `@siged.test`. Teléfonos `+5690000NNNN`.
- Cada cuenta de simulación recibe una clave distinta al correr `importar_json`. El archivo `.demo_credentials.local` queda fuera del repositorio. `SIGED_DEMO_PASSWORD` es opcional y solo para pruebas. El fixture y `D003` guardan `!`, así que un hash anterior deja de autenticar. Una clave que llegó a publicarse en el cuerpo del pull request no debe usarse: queda invalidada por diseño.
- El `CHECK (REGEXP_LIKE …)` está en `V018` y en un `RunPython` solo para MySQL dentro de `cuentas.0003`. La suite corre en SQLite, que no implementa esa función. La unicidad y el `NOT NULL` sí están en el ORM.
- Los enlaces al sitio oficial de la municipalidad en la portada pública se dejan: no son datos de semilla ni RUT de personas.
