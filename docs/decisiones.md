# Decisiones de la prioridad 1

Inventario hecho sobre el repositorio en el tag `sumativa2-backend` (commit `fd2fb32`). No hubo acceso a un MySQL local ni a la instancia del curso, así que los conteos son los del código y los fixtures, no un `SELECT` en el servidor.

## EQ-01 — qué había antes de reescribir

- `fixtures/02_datos_sistema.json`: 10 funcionarios, 4 usuarios, 21 vecinos. Cuatro RUT de vecino (pk 18–21) no pasaban el dígito verificador.
- `data/usuarios.json`: cuatro claves en texto plano (`admin123`, `jefatura123`, `funcionario123`, `ventanilla123`) y correos con nombres propios.
- Nombres de personas en funcionarios, vecinos y textos de contacto. No había un RUT de funcionario: el acceso era un alias (`admin`, `jefatura`, …).
- El historial de Git conserva esos datos. No se reescribió.

## Decisiones

- **D-1.** No reescribir la historia. El tag `sumativa2-backend` queda en el commit ya evaluado y no se mueve.
- **D-2.** Se mantiene `django.contrib.auth` y el ORM. Quitar el ORM es otra tarea y queda a la espera de confirmación del profesor. Los scripts `V017`, `D003` y `V018` describen el mismo cambio de esquema.
- **D-3.** La recuperación de clave sigue siendo la de correo que ya estaba (el código se muestra en pantalla). Pasarla a códigos hasheados es de una prioridad posterior.
- **D-4.** RUT de simulación en `33.100.001–33.100.999` (funcionarios) y `33.500.001–33.509.999` (vecinos), con dígito verificador válido. Todo nombre de simulación lleva `(ficticio)`. Correos `@siged.test`. Teléfonos `+5690000NNNN`.
- La clave de demostración es una convención única, documentada en el README, y en SQL/JSON solo existe el hash. El plan pedía entregar las claves por otro canal; el encargo de esta tarea pide que cada rol pueda entrar y que la convención quede escrita una sola vez.
- El `CHECK (REGEXP_LIKE …)` está en `V018` y en un `RunPython` solo para MySQL dentro de `cuentas.0003`. La suite corre en SQLite, que no implementa esa función. La unicidad y el `NOT NULL` sí están en el ORM.
- Los enlaces al sitio oficial de la municipalidad en la portada pública se dejan: no son datos de semilla ni RUT de personas.
