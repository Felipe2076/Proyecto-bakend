// Presentación III Evaluación · Ingeniería de Software · SIGED-SGR
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const SKILL = process.env.PPTX_SKILL;
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));
const IMG = path.join(__dirname, "..", "img");
const DIMS = JSON.parse(fs.readFileSync(path.join(IMG, "dims.json"), "utf8"));
const SALIDA = process.argv[2];

const THEME = {
  name: "SIGED Granate municipal",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "231F20", lt1: "FFFFFF", dk2: "5A1621", lt2: "F6EEF0",
    accent1: "7A1F2B", accent2: "B8892B", accent3: "2E7D5B", accent4: "D9A21B",
    accent5: "B23A3A", accent6: "6B6064", hlink: "7A1F2B", folHlink: "5A1621",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "SIGED-SGR · III Evaluación de Ingeniería de Software";
pres.author = "Felipe Quiroz Vergara y Aixa Vega Zamorano";
pres.subject = "Prototipo y construcción futura del sistema de gestión de delegaciones";
const C = pres.SchemeColor;

// ---------- Layouts ----------
const PIE = "SIGED-SGR · Ingeniería de Software · III Evaluación";
pres.defineSlideMaster({
  title: "PORTADA",
  background: { color: HEX.accent1 },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENIDO",
  background: { color: HEX.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.32, w: 12.1, h: 0.7, fontSize: 30, bold: true, color: C.accent1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "sub", type: "body", x: 0.6, y: 1.0, w: 12.1, h: 0.42, fontSize: 15, color: C.accent6, valign: "top", margin: 0 }, text: "" } },
    { text: { text: PIE, options: { x: 0.6, y: 7.02, w: 8, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 12.15, y: 7.02, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "CIERRE",
  background: { color: HEX.dk2 },
  objects: [],
});

// ---------- Ayudas ----------
const cacheIconos = {};
async function icono(nombre, color = "FFFFFF") {
  const clave = nombre + color;
  if (!cacheIconos[clave]) {
    const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(fa[nombre], { color: "#" + color, size: 256 }));
    const png = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
    cacheIconos[clave] = "image/png;base64," + png.toString("base64");
  }
  return cacheIconos[clave];
}

async function circuloIcono(slide, nombre, x, y, d = 0.62, fondo = C.accent1, colorIcono = "FFFFFF") {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fondo }, line: { color: fondo }, objectName: "Icono fondo " + nombre });
  const p = d * 0.25;
  slide.addImage({ data: await icono(nombre, colorIcono), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, altText: "", objectName: "Icono " + nombre });
}

function texto(slide, contenido, opciones) {
  slide.addText(contenido, Object.assign({ isTextBox: true, margin: 0, valign: "top", fontSize: 15, color: C.text1 }, opciones));
}

function tarjeta(slide, x, y, w, h, fondo = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fondo }, line: { color: fondo }, objectName: "Tarjeta" });
}

// Imagen ajustada sin deformar dentro de un recuadro, con borde fino
function imagen(slide, archivo, x, y, w, h, alt, borde = true) {
  const [iw, ih] = DIMS[archivo];
  const escala = Math.min(w / iw, h / ih);
  const ww = iw * escala, hh = ih * escala;
  const xx = x + (w - ww) / 2, yy = y + (h - hh) / 2;
  slide.addImage({ path: path.join(IMG, archivo), x: xx, y: yy, w: ww, h: hh, altText: alt, objectName: alt });
  if (borde) slide.addShape(pres.shapes.RECTANGLE, { x: xx, y: yy, w: ww, h: hh, fill: { type: "none" }, line: { color: C.accent6, width: 0.75, transparency: 55 }, objectName: "Borde " + alt });
  return { x: xx, y: yy, w: ww, h: hh };
}

function encabezado(slide, titulo, sub) {
  slide.addText(titulo, { placeholder: "title" });
  if (sub) slide.addText(sub, { placeholder: "sub" });
}

// Fila de ícono + título + texto
async function filaIcono(slide, nombre, x, y, w, titulo, cuerpo, tamCuerpo = 14) {
  await circuloIcono(slide, nombre, x, y, 0.56);
  texto(slide, titulo, { x: x + 0.75, y: y - 0.02, w: w - 0.75, h: 0.32, fontSize: 16, bold: true, color: C.text2 });
  texto(slide, cuerpo, { x: x + 0.75, y: y + 0.32, w: w - 0.75, h: 0.62, fontSize: tamCuerpo, color: C.text1 });
}

async function main() {
  // ===== 1. Portada =====
  pres.addSection({ title: "Inicio" });
  let s = pres.addSlide({ masterName: "PORTADA", sectionTitle: "Inicio" });
  texto(s, "INGENIERÍA DE SOFTWARE · III EVALUACIÓN", { x: 0.7, y: 1.05, w: 6.6, h: 0.35, fontSize: 13, bold: true, color: C.background1, charSpacing: 2 });
  texto(s, "SIGED-SGR", { x: 0.7, y: 1.55, w: 6.6, h: 1.1, fontSize: 60, bold: true, color: C.background1, fontFace: THEME.headFontFace });
  texto(s, "Prototipo funcional y construcción futura del sistema de gestión de las delegaciones municipales de La Serena",
    { x: 0.7, y: 2.8, w: 6.4, h: 1.2, fontSize: 20, color: C.background1 });
  texto(s, [
    { text: "Felipe Quiroz Vergara (representante) · Aixa Vega Zamorano", options: { bold: true, breakLine: true } },
    { text: "Profesor: Francisco Gabriel Caiceo León", options: { breakLine: true } },
    { text: "INACAP La Serena · Noviembre de 2026" },
  ], { x: 0.7, y: 4.75, w: 6.4, h: 1.1, fontSize: 15, color: C.background1, paraSpaceAfter: 4 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.55, y: 1.75, w: 5.2, h: 3.15, rectRadius: 0.12, fill: { color: C.background1 }, line: { color: C.background1 }, objectName: "Marco captura" });
  imagen(s, "cap_tubo_cartas.png", 7.67, 1.87, 4.96, 2.91, "Captura del tubo de cartas del prototipo", false);
  texto(s, "Tubo de cartas del prototipo desplegado en AWS (datos ficticios)", { x: 7.55, y: 5.0, w: 5.2, h: 0.3, fontSize: 11, color: C.background1, italic: true });
  s.addNotes("Felipe (≈40 s). Presentar al equipo y al profesor. Decir en una frase qué vamos a mostrar: un prototipo que ya funciona en la nube, cómo cumple la rúbrica (requerimientos, metodología, calidad, seguridad y casos de uso) y cómo se terminará de construir.");

  // ===== 2. Problema y nuevo requerimiento =====
  pres.addSection({ title: "Contexto" });
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Contexto" });
  encabezado(s, "Qué resuelve SIGED y qué pidió el cliente", "Correo de la Coordinación de Delegaciones (8 de octubre de 2026) y archivos de la Unidad 3");
  tarjeta(s, 0.6, 1.65, 5.2, 5.15);
  await circuloIcono(s, "FaMapMarkedAlt", 0.9, 1.95, 0.7);
  texto(s, "Seis delegaciones, una sola forma de trabajar", { x: 1.8, y: 1.98, w: 3.8, h: 0.7, fontSize: 18, bold: true, color: C.text2, fontFace: THEME.headFontFace });
  texto(s, [
    { text: "Centro, Rural, La Antena, La Pampa, Avenida del Mar y Las Compañías llevaban la matriz SGR en planillas.", options: { bullet: true, breakLine: true } },
    { text: "Los compromisos con vecinos no tenían responsable ni fecha visibles.", options: { bullet: true, breakLine: true } },
    { text: "Objetivo: registrar, asignar y medir cada atención, actividad y compromiso, con evidencia.", options: { bullet: true } },
  ], { x: 0.95, y: 2.95, w: 4.6, h: 2.6, fontSize: 15, paraSpaceAfter: 10 });
  texto(s, "6", { x: 0.95, y: 5.55, w: 1.9, h: 0.75, fontSize: 40, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  texto(s, "delegaciones", { x: 0.95, y: 6.3, w: 1.9, h: 0.3, fontSize: 13, color: C.accent6 });
  texto(s, "2.709", { x: 3.0, y: 5.55, w: 2.6, h: 0.75, fontSize: 40, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  texto(s, "organizaciones comunitarias", { x: 3.0, y: 6.3, w: 2.6, h: 0.3, fontSize: 13, color: C.accent6 });
  texto(s, "Nuevo requerimiento del cliente (Unidad 3)", { x: 6.3, y: 1.7, w: 6.4, h: 0.4, fontSize: 18, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  await filaIcono(s, "FaClipboardCheck", 6.3, 2.3, 6.4, "Reglas de la matriz SGR", "Máximo 7 actividades al día, cierre semanal el martes, solo suma el resultado y tope de 120 % por ítem");
  await filaIcono(s, "FaUsers", 6.3, 3.4, 6.4, "Organizaciones comunitarias", "Base de juntas de vecinos y organizaciones funcionales (2.709 registros) por delegación y territorio");
  await filaIcono(s, "FaColumns", 6.3, 4.5, 6.4, "Tubo de compromisos en tarjetas", "Formato Card / Canvas: una columna por estado y totales arriba");
  await filaIcono(s, "FaIdBadge", 6.3, 5.6, 6.4, "Funciones por cargo", "Descriptor de funciones: delegado, gestor social, apoyo administrativo, organizaciones…");
  s.addNotes("Felipe (≈50 s). El problema: seis delegaciones sin un modelo común ni trazabilidad. Luego el nuevo requerimiento de la Unidad 3: el correo con las reglas de la matriz, la base de organizaciones, el tubo en tarjetas y el descriptor de funciones. Todo esto quedó incorporado al prototipo.");

  // ===== 3. Tendencias tecnológicas (3.1.1) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Contexto" });
  encabezado(s, "Tendencias: el sistema ya corre en la nube", "Criterio 3.1.1 · SaaS, IaaS y cloud computing aplicados a SIGED");
  imagen(s, "d_despliegue_rec.png", 0.6, 1.75, 8.1, 4.75, "Diagrama de despliegue en AWS");
  await filaIcono(s, "FaServer", 8.95, 1.85, 3.8, "IaaS · infraestructura", "AWS EC2 entrega el servidor virtual; el equipo administra Docker, MySQL y respaldos");
  await filaIcono(s, "FaGlobe", 8.95, 3.35, 3.8, "SaaS · software como servicio", "La municipalidad usa SIGED desde el navegador: sin instalar nada y con una sola versión");
  await filaIcono(s, "FaCloud", 8.95, 4.85, 3.8, "Cloud computing", "Pago por uso, acceso con HTTPS desde cualquier delegación y crecimiento sin comprar equipos");
  texto(s, "Diagrama de despliegue real: Apache con HTTPS, contenedor app (Django) y contenedor db (MySQL 8.4)", { x: 0.6, y: 6.6, w: 8.1, h: 0.3, fontSize: 11, color: C.accent6, italic: true });
  s.addNotes("Felipe (≈50 s). IaaS: arrendamos el servidor en AWS y nosotros administramos lo de arriba (Docker, base, respaldos). Para la municipalidad SIGED es SaaS: entra por el navegador. Ventajas de la nube: no compran servidores, pagan por uso y las seis delegaciones acceden igual. Si preguntan por PaaS: sería delegar también el sistema operativo, por ejemplo con Elastic Beanstalk.");

  // ===== 4. Requerimientos y casos de uso =====
  pres.addSection({ title: "Requerimientos y prototipo" });
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Requerimientos y prototipo" });
  encabezado(s, "De los requerimientos a los casos de uso", "61 diagramas UML/SysML trazables; aquí, el caso de uso general. Nuevos de la Unidad 3: RF-17 a RF-26, EP-13 a EP-16 y CU-E13 a CU-E20");
  const cifras = [["26", "requerimientos funcionales"], ["10", "no funcionales"], ["16", "épicas"], ["67", "historias de usuario"], ["20", "casos de uso detallados"]];
  tarjeta(s, 0.6, 1.65, 2.55, 5.2);
  cifras.forEach(([n, etq], i) => {
    const y = 1.8 + i * 1.0;
    texto(s, n, { x: 0.85, y, w: 2.1, h: 0.6, fontSize: 32, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
    texto(s, etq, { x: 0.85, y: y + 0.58, w: 2.2, h: 0.3, fontSize: 12, color: C.accent6 });
  });
  imagen(s, "d_cu_general_rec.png", 3.4, 1.65, 9.33, 5.2, "Diagrama de casos de uso general");
  s.addNotes("Felipe (≈45 s). No leer los 26 requerimientos: dar las cifras y mostrar el caso de uso general. Explicar que cada rol hereda lo del anterior (operador, funcionario, jefatura, administrador de delegación y superusuario) y que las seis funciones principales se detallan en 20 casos de uso.");

  // ===== 5. Reflejo de casos de uso en el prototipo (rúbrica 5) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Requerimientos y prototipo" });
  encabezado(s, "Cada caso de uso tiene su pantalla en el prototipo", "Rúbrica · reflejo de los diagramas de casos de uso: menú real del sistema → caso de uso que realiza");
  imagen(s, "d_reflejo_rec.png", 0.6, 1.65, 8.4, 5.2, "Mapa de pantallas del prototipo y sus casos de uso");
  texto(s, "19 de 20", { x: 9.3, y: 1.7, w: 3.4, h: 0.85, fontSize: 48, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
  texto(s, "casos de uso detallados tienen pantalla. CU-E12 (cierre mensual) queda como diseño propuesto.", { x: 9.3, y: 2.55, w: 3.4, h: 0.9, fontSize: 14, color: C.accent6 });
  texto(s, "Ejemplo de trazabilidad", { x: 9.3, y: 3.65, w: 3.4, h: 0.35, fontSize: 16, bold: true, color: C.text2 });
  const cadena = ["RF-20 · Tubo en tarjetas", "EP-15 · Tubo de compromisos", "CU-G02 · Trabajo territorial", "CU-E14 · Mover compromisos", "Pantalla /control/tubo-cartas/"];
  for (let i = 0; i < cadena.length; i++) {
    const y = 4.1 + i * 0.55;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.3, y, w: 3.4, h: 0.42, rectRadius: 0.08, fill: { color: i === cadena.length - 1 ? C.accent1 : C.background2 }, line: { color: i === cadena.length - 1 ? C.accent1 : C.background2 }, objectName: "Paso " + (i + 1) });
    texto(s, cadena[i], { x: 9.42, y: y + 0.06, w: 3.2, h: 0.3, fontSize: 13, bold: i === cadena.length - 1, color: i === cadena.length - 1 ? C.background1 : C.text1 });
  }
  s.addNotes("Felipe (≈55 s). Este es el punto 5 de la rúbrica. Señalar dos o tres filas: Ingresar ticket realiza CU-E01, Tubo de cartas realiza CU-E14 y CU-E19. Recorrer el ejemplo de la derecha: del requerimiento RF-20 hasta la ruta real. Si el docente quiere, abrir esa pantalla en vivo.");

  // ===== 6. Prototipo: requerimientos funcionales (rúbrica 1) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Requerimientos y prototipo" });
  encabezado(s, "Requerimientos funcionales funcionando en el prototipo", "Rúbrica · implementación de requerimientos: capturas del sistema desplegado en AWS (datos ficticios)");
  const capturas = [
    ["cap_ticket.png", "Ingreso de ticket", "RF-09, RF-10 · CU-E01", "Canal, tipificación, delegación y responsable; valida correo si el canal es correo."],
    ["cap_tubo_cartas.png", "Tubo de cartas", "RF-20 · CU-E14", "Arrastrar entre estados; «Vencido» se calcula por fecha y cada cambio guarda su autor."],
    ["cap_actividad.png", "Actividad y evidencia", "RF-01, RF-04, RF-18 · CU-E02", "Máximo 7 por día, cierre el martes, evidencia de hasta 10 MB y código verificador."],
  ];
  for (let i = 0; i < capturas.length; i++) {
    const [arch, tit, tag, desc] = capturas[i];
    const x = 0.6 + i * 4.1;
    imagen(s, arch, x, 1.7, 3.9, 2.45, "Captura " + tit);
    texto(s, tit, { x, y: 4.35, w: 3.9, h: 0.35, fontSize: 17, bold: true, color: C.text2 });
    texto(s, tag, { x, y: 4.72, w: 3.9, h: 0.3, fontSize: 13, bold: true, color: C.accent1 });
    texto(s, desc, { x, y: 5.08, w: 3.9, h: 0.9, fontSize: 14 });
  }
  tarjeta(s, 0.6, 6.1, 12.1, 0.7);
  texto(s, "También funcionan: compromisos y agenda, semáforo de desempeño, organizaciones comunitarias, ausencias, configuración trimestral automática, encuesta 1–5 y administración por delegación.",
    { x: 0.85, y: 6.2, w: 11.6, h: 0.5, fontSize: 14, valign: "middle" });
  s.addNotes("Felipe (≈55 s). Tres pantallas que muestran requerimientos clave, incluido lo nuevo de la Unidad 3 (tubo en tarjetas y reglas de la matriz en Actividad). Mencionar la franja inferior: el resto de los módulos también está operativo. Aquí pasa la palabra a Aixa.");

  // ===== 7. Requerimientos no funcionales (rúbrica 1) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Requerimientos y prototipo" });
  encabezado(s, "Requerimientos no funcionales: cómo los cumple", "Rúbrica · calidad del prototipo (rendimiento, usabilidad, seguridad, integridad)");
  const enc = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.accent1 }, fontSize: 14 } });
  const est = (t, ok) => ({ text: t, options: { bold: true, color: ok ? HEX.accent3 : HEX.accent2, fontSize: 14 } });
  const filas = [
    [enc("Requerimiento"), enc("Evidencia en SIGED"), enc("Estado")],
    ["RNF-01 Autorización", "Permisos por rol; cada administrador ve solo su delegación y el superusuario las seis (validado en el servidor)", est("Cumplido", true)],
    ["RNF-02 Integridad", "Transacciones y bloqueo de fila al aprobar o mover; una aprobación suma una sola vez", est("Cumplido", true)],
    ["RNF-03 Usabilidad", "Plantillas adaptables (Bootstrap 5); barra del trimestre siempre visible", est("Falta prueba a 360 px", false)],
    ["RNF-04 Rendimiento", "Meta: 95 % de consultas en 3 s o menos con 30 usuarios", est("Prueba de carga pendiente", false)],
    ["RNF-05 Privacidad", "HTTPS; datos del vecino solo para perfiles autorizados", est("Cumplido", true)],
    ["RNF-06 Configurabilidad", "Trimestre con nombre y días automáticos; parámetros del semáforo sin programar", est("Cumplido", true)],
    ["RNF-07 Respaldo", "Respaldo de MySQL, .env y archivos antes de cada despliegue, con reversión", est("Cumplido", true)],
    ["RNF-08 Trazabilidad", "Historial de revisiones y de cambios de estado; aviso si otra persona cambió el registro", est("Cumplido", true)],
  ];
  s.addTable(filas, { x: 0.6, y: 1.6, w: 12.1, colW: [2.6, 7.3, 2.2], fontSize: 14, color: HEX.dk1, fontFace: THEME.bodyFontFace,
    border: { type: "solid", pt: 0.5, color: "D9CED1" }, fill: { color: HEX.lt1 }, rowH: 0.55, valign: "middle", margin: [0.04, 0.1, 0.04, 0.1], objectName: "Tabla RNF" });
  s.addNotes("Aixa (≈50 s). Recorrer la tabla por estado: seis cumplidos con evidencia en el código y dos pendientes declarados con honestidad (prueba a 360 px y prueba de carga). Destacar RNF-01: el encapsulamiento por delegación con superusuario.");

  // ===== 8. Arquitectura =====
  pres.addSection({ title: "Construcción" });
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Construcción" });
  encabezado(s, "Arquitectura: una aplicación Django por capas", "Cómo está construido y cómo se seguirá construyendo");
  imagen(s, "d_componentes_rec.png", 0.6, 1.65, 8.0, 5.2, "Diagrama de componentes por capas");
  await filaIcono(s, "FaLayerGroup", 8.95, 1.8, 3.8, "Django modular", "Tres apps (cuentas, requerimientos, control_gestion); las reglas viven en módulos propios");
  await filaIcono(s, "FaMobileAlt", 8.95, 3.05, 3.8, "API REST /api/v1/", "La app Android usa la misma lógica y permisos; nunca entra a MySQL");
  await filaIcono(s, "FaDatabase", 8.95, 4.3, 3.8, "MySQL 8.4 · 33 clases", "Delegación es el eje: casi todo registro pertenece a una delegación");
  await filaIcono(s, "FaBoxes", 8.95, 5.55, 3.8, "Docker en AWS", "Contenedores app y db; solo el puerto 443 queda público");
  s.addNotes("Aixa (≈45 s). Leer el diagrama por capas de arriba hacia abajo: clientes, presentación, negocio, servicios transversales y datos. Por qué Django: autenticación, permisos y ORM incluidos. La app Android consumirá la API, que ya existe.");

  // ===== 9. Metodología (rúbrica 2) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Construcción" });
  encabezado(s, "Metodología: Scrum complementado con Kanban", "Rúbrica · aplicación de la metodología: roles, entregables y procesos");
  const pasos = ["Product Backlog", "Sprint Planning", "Sprint de 2 semanas · Daily", "Review con la municipalidad", "Retrospectiva"];
  for (let i = 0; i < pasos.length; i++) {
    const x = 0.6 + i * 2.39;
    s.addShape(i === 0 ? pres.shapes.PENTAGON : pres.shapes.CHEVRON, { x, y: 1.7, w: 2.55, h: 0.9, fill: { color: i % 2 ? C.accent1 : C.text2 }, line: { color: i % 2 ? C.accent1 : C.text2 }, objectName: "Etapa " + pasos[i] });
    texto(s, pasos[i], { x: x + 0.4, y: 1.78, w: 1.75, h: 0.74, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
  }
  const columnas = [
    ["FaUserFriends", "Roles", ["Product Owner: prioriza el backlog con la contraparte municipal", "Scrum Master: facilita los eventos y quita impedimentos", "Developers: Felipe y Aixa construyen y verifican"]],
    ["FaListAlt", "Entregables", ["Product Backlog: 67 historias en 16 épicas", "Sprint Backlog y avance en Planner", "Incremento: versión desplegada en AWS"]],
    ["FaColumns", "Kanban del equipo", ["Por hacer → En desarrollo → En verificación → Terminado", "Máximo 2 tareas en curso", "Terminado = criterios aceptados, pruebas y revisión cruzada"]],
  ];
  for (let i = 0; i < columnas.length; i++) {
    const [ic, tit, items] = columnas[i];
    const x = 0.6 + i * 4.1;
    tarjeta(s, x, 2.9, 3.9, 3.0);
    await circuloIcono(s, ic, x + 0.3, 3.1, 0.6);
    texto(s, tit, { x: x + 1.05, y: 3.2, w: 2.7, h: 0.4, fontSize: 18, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    texto(s, items.map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < items.length - 1 } })),
      { x: x + 0.3, y: 3.85, w: 3.35, h: 2.0, fontSize: 14, paraSpaceAfter: 6 });
  }
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 6.05, w: 12.1, h: 0.78, rectRadius: 0.12, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "Por qué Scrum" });
  texto(s, "Por qué Scrum: el cliente cambió y agregó requerimientos durante el semestre (correo de la Unidad 3) y el backlog los absorbió sprint a sprint, sin rehacer lo terminado.",
    { x: 0.9, y: 6.12, w: 11.5, h: 0.64, fontSize: 15, bold: true, color: C.background1, valign: "middle" });
  s.addNotes("Aixa (≈55 s). Por qué Scrum: los requerimientos cambiaron durante el semestre (ejemplo: el correo de la Unidad 3 llegó a mitad de camino) y el backlog absorbió esos cambios. Kanban limita el trabajo en curso de un equipo de dos personas. Explicar la Definición de Terminado. Confirmar en voz alta quién cumplió cada rol.");

  // ===== 10. Calidad (rúbrica 3) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Construcción" });
  encabezado(s, "Estándares de calidad en el desarrollo y la gestión", "Rúbrica · documentación, pruebas, revisión y gestión de versiones");
  tarjeta(s, 0.6, 1.65, 4.0, 5.15, C.accent1);
  texto(s, "222", { x: 0.9, y: 2.0, w: 3.4, h: 1.3, fontSize: 72, bold: true, color: C.background1, fontFace: THEME.headFontFace });
  texto(s, "pruebas automatizadas", { x: 0.9, y: 3.35, w: 3.4, h: 0.45, fontSize: 20, bold: true, color: C.background1 });
  texto(s, "214 aprobadas. Las otras 8 necesitan los archivos de datos de simulación, que no están en esta copia del proyecto.", { x: 0.9, y: 4.0, w: 3.4, h: 1.4, fontSize: 14, color: C.background1 });
  texto(s, "Cubren permisos por rol y delegación, reglas de la matriz, revisión de evidencias, tubo y trimestre.", { x: 0.9, y: 5.45, w: 3.4, h: 1.1, fontSize: 14, color: C.background1 });
  const calidad = [
    ["FaCheckDouble", "ISO/IEC 25010", "Seguridad, fiabilidad, usabilidad y mantenibilidad como criterios de aceptación"],
    ["FaCode", "PEP 8 y revisión cruzada", "Convención de código Python; cada cambio lo revisa la otra persona del equipo antes de terminarlo"],
    ["FaCodeBranch", "Gestión de versiones", "Cada despliegue verifica SHA-256, respalda y revierte solo si algo falla"],
    ["FaProjectDiagram", "Trazabilidad documental", "61 diagramas desde el código: requerimiento → caso de uso → pantalla"],
  ];
  for (let i = 0; i < calidad.length; i++) {
    const [ic, tit, txt] = calidad[i];
    const x = 4.95 + (i % 2) * 3.9, y = 1.65 + Math.floor(i / 2) * 2.6;
    tarjeta(s, x, y, 3.75, 2.45);
    await circuloIcono(s, ic, x + 0.3, y + 0.3, 0.6);
    texto(s, tit, { x: x + 0.3, y: y + 1.05, w: 3.2, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
    texto(s, txt, { x: x + 0.3, y: y + 1.45, w: 3.2, h: 0.9, fontSize: 14 });
  }
  s.addNotes("Aixa (≈50 s). Dar la cifra de pruebas con honestidad: 214 de 222 aprueban y las 8 restantes dependen de archivos de datos que no van en el repositorio. Explicar el despliegue seguro: se compara el código del servidor por hash, se respalda y, si el sitio no responde, vuelve solo a la versión anterior.");

  // ===== 11. Seguridad (rúbrica 4) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Construcción" });
  encabezado(s, "Seguridad: OWASP Top 10 aplicado al prototipo", "Rúbrica · autenticación, permisos, manejo de datos y cifrado");
  const enc2 = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.accent1 }, fontSize: 14 } });
  const owasp = [
    [enc2("Riesgo OWASP (2021)"), enc2("Control en SIGED")],
    ["A01 Control de acceso", "Permisos por rol y encapsulamiento por delegación en el servidor; otra delegación por URL se rechaza"],
    ["A02 Fallas criptográficas", "HTTPS; contraseñas con hash PBKDF2 de Django; códigos de recuperación con HMAC-SHA256"],
    ["A03 Inyección", "Consultas por el ORM de Django (parametrizadas) y formularios validados en el servidor"],
    ["A04 Diseño inseguro", "Nadie aprueba su propia evidencia; MySQL con usuario de mínimo privilegio"],
    ["A05 Configuración", "DEBUG desactivado, cabeceras de seguridad y MySQL sin puerto público"],
    ["A07 Autenticación", "Límite de intentos con espera de 15 minutos, códigos de un solo uso y respuesta genérica"],
    ["A08 Integridad", "Token CSRF en formularios y despliegue verificado con SHA-256"],
    ["A09 Registro", "Historial con autor de revisiones y cambios; los registros no guardan datos sensibles"],
  ];
  s.addTable(owasp, { x: 0.6, y: 1.6, w: 12.1, colW: [3.0, 9.1], fontSize: 14, color: HEX.dk1, fontFace: THEME.bodyFontFace,
    border: { type: "solid", pt: 0.5, color: "D9CED1" }, fill: { color: HEX.lt1 }, rowH: 0.55, valign: "middle", margin: [0.04, 0.1, 0.04, 0.1], objectName: "Tabla OWASP" });
  s.addNotes("Aixa (≈55 s). Elegir tres filas para explicar: A01 (cada administrador encapsulado en su delegación, el superusuario ve todo), A04 (separación de funciones: nadie aprueba lo propio; base con mínimo privilegio) y A07 (límite de intentos y códigos de un uso). Presentarlo como reducción de riesgo, no como seguridad absoluta.");

  // ===== 12. Confiabilidad, ética y normativa (3.1.2) =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Construcción" });
  encabezado(s, "Confiabilidad, ética y normativa", "Criterio 3.1.2 · por qué la municipalidad puede confiar en las cifras de SIGED");
  const leyes = [
    ["FaGavel", "Ley 21.459 · Delitos informáticos (2022)", "Sanciona el acceso ilícito, la interceptación y el fraude informático. SIGED reduce ese riesgo con control de acceso, mínimo privilegio y registro del autor de cada cambio."],
    ["FaUserShield", "Leyes 19.628 y 21.719 · Datos personales", "Los datos del vecino se usan solo para atenderlo y los ve solo quien tiene permiso. La Ley 21.719 rige desde diciembre de 2026 y exige finalidad, seguridad y responsabilidad."],
    ["FaBalanceScale", "Código de ética ACM/IEEE-CS", "Interés público, calidad y honestidad: probamos con datos ficticios y declaramos qué está implementado y qué es propuesta."],
  ];
  for (let i = 0; i < leyes.length; i++) {
    const [ic, tit, txt] = leyes[i];
    const x = 0.6 + i * 4.1;
    tarjeta(s, x, 1.65, 3.9, 3.85);
    await circuloIcono(s, ic, x + 0.3, 1.95, 0.7);
    texto(s, tit, { x: x + 0.3, y: 2.85, w: 3.35, h: 0.75, fontSize: 17, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    texto(s, txt, { x: x + 0.3, y: 3.65, w: 3.35, h: 1.85, fontSize: 14 });
  }
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.85, w: 12.1, h: 0.95, rectRadius: 0.12, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "Mensaje confiabilidad" });
  texto(s, "Confiabilidad para el negocio: cada punto del semáforo tiene una evidencia revisada por otra persona, y cada cambio queda con su autor y su fecha.",
    { x: 0.9, y: 5.95, w: 11.5, h: 0.75, fontSize: 16, bold: true, color: C.background1, valign: "middle" });
  s.addNotes("Aixa (≈50 s). Relacionar cada norma con una decisión de diseño concreta. Ley 21.459: control de acceso y trazabilidad. Datos personales: finalidad y acceso restringido; la nueva Ley 21.719 entra en vigencia en diciembre de 2026. Ética: honestidad sobre lo pendiente. Cerrar con la frase de confiabilidad.");

  // ===== 13. Cierre =====
  pres.addSection({ title: "Cierre" });
  s = pres.addSlide({ masterName: "CIERRE", sectionTitle: "Cierre" });
  texto(s, "Construcción futura", { x: 0.7, y: 0.6, w: 12, h: 0.8, fontSize: 36, bold: true, color: C.background1, fontFace: THEME.headFontFace });
  texto(s, "Lo que falta para pasar del prototipo al sistema en operación", { x: 0.7, y: 1.4, w: 12, h: 0.45, fontSize: 17, color: C.background2 });
  const futuro = [
    ["FaMobileAlt", "App Android", "Terminar la app sobre la API ya construida"],
    ["FaCalendarCheck", "Cierre mensual", "Congelar resultados e informe (CU-E12)"],
    ["FaUsers", "Organizaciones", "Validar las 2.709 con cada delegación"],
    ["FaBell", "Avisos y carga", "Avisos al vecino y prueba de carga"],
  ];
  for (let i = 0; i < futuro.length; i++) {
    const [ic, tit, txt] = futuro[i];
    const x = 0.7 + i * 3.05;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.3, w: 2.8, h: 2.7, rectRadius: 0.12, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "Paso futuro " + (i + 1) });
    await circuloIcono(s, ic, x + 0.3, 2.6, 0.7, C.background1, HEX.accent1);
    texto(s, `${i + 1}. ${tit}`, { x: x + 0.3, y: 3.5, w: 2.3, h: 0.45, fontSize: 18, bold: true, color: C.background1 });
    texto(s, txt, { x: x + 0.3, y: 4.0, w: 2.3, h: 0.9, fontSize: 14, color: C.background1 });
  }
  texto(s, "¿Preguntas?", { x: 0.7, y: 5.6, w: 12, h: 0.9, fontSize: 40, bold: true, color: C.background1, fontFace: THEME.headFontFace });
  s.addNotes("Felipe (≈40 s). Resumir: el prototipo ya cumple los requerimientos principales y lo nuevo del cliente; faltan cuatro piezas para operar. Abrir preguntas. Tiempo total previsto: unos 10 minutos.");

  await pres.writeFile({ fileName: SALIDA });
  await applyTheme(SALIDA, THEME);
  console.log("ok", SALIDA);
}

main().catch((e) => { console.error(e); process.exit(1); });
