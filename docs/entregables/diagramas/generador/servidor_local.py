"""Servidor local (127.0.0.1) para revisar los .drawio con el modo embed oficial de diagrams.net.

GET  /visor.html?f=archivo.drawio[,otro.drawio]&escala=1.5  -> carga cada página en embed.diagrams.net y la exporta a PNG
GET  /<archivo>.drawio                                     -> entrega el archivo desde la carpeta de diagramas
POST /guardar?nombre=<archivo.png>                         -> guarda el PNG (data URI en el cuerpo) en la carpeta de salida
"""
import base64, functools, http.server, pathlib, re, sys, urllib.parse

DIAGRAMAS = pathlib.Path(sys.argv[1]).resolve()
SALIDA = pathlib.Path(sys.argv[2]).resolve()
PUERTO = int(sys.argv[3]) if len(sys.argv) > 3 else 8765
SALIDA.mkdir(parents=True, exist_ok=True)

VISOR = r"""<!doctype html><html><head><meta charset="utf-8"><title>exportando</title>
<style>body{font:13px Arial;margin:10px}iframe{width:1400px;height:900px;border:1px solid #999}</style></head><body>
<pre id="log"></pre><script>
const log = t => { document.getElementById('log').textContent += t + '\n'; };
const params = new URLSearchParams(location.search);
const archivos = (params.get('f') || '').split(',').filter(Boolean);
const escala = parseFloat(params.get('escala') || '1.5');
const soloPagina = params.get('p');
const frame = document.createElement('iframe');
frame.src = 'https://embed.diagrams.net/?embed=1&proto=json&spin=0&ui=min&lang=es&noSaveBtn=1&noExitBtn=1';
document.body.appendChild(frame);
function esperar(cond) {
  return new Promise(ok => {
    function f(ev) {
      if (ev.source !== frame.contentWindow) return;
      let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
      if (cond(m)) { window.removeEventListener('message', f); ok(m); }
    }
    window.addEventListener('message', f);
  });
}
const enviar = m => frame.contentWindow.postMessage(JSON.stringify(m), '*');
const limpio = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '');
(async () => {
  await esperar(m => m.event === 'init');
  for (const f of archivos) {
    const xml = await (await fetch('/' + encodeURIComponent(f))).text();
    const paginas = xml.match(/<diagram [\s\S]*?<\/diagram>/g) || [];
    const base = f.replace(/\.drawio$/, '');
    for (let i = 0; i < paginas.length; i++) {
      if (soloPagina && !soloPagina.split('-').map(Number).includes(i + 1)) continue;
      const nombre = (paginas[i].match(/name="([^"]*)"/) || [, 'pagina'])[1];
      enviar({ action: 'load', xml: '<mxfile>' + paginas[i] + '</mxfile>', autosave: 0 });
      await esperar(m => m.event === 'load');
      enviar({ action: 'export', format: 'png', scale: escala, border: 12, background: '#ffffff', grid: false, shadow: false, keepTheme: false });
      const r = await esperar(m => m.event === 'export');
      const archivo = base.slice(0, 2) + '_p' + String(i + 1).padStart(2, '0') + '_' + limpio(nombre).slice(0, 50) + '.png';
      await fetch('/guardar?nombre=' + encodeURIComponent(archivo), { method: 'POST', body: r.data });
      log('ok ' + archivo);
    }
  }
  document.title = 'LISTO';
  log('LISTO');
})();
</script></body></html>"""


class Manejador(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        ruta = urllib.parse.urlparse(self.path).path
        if ruta == '/visor.html':
            cuerpo = VISOR.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(cuerpo)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        nombre = urllib.parse.unquote(ruta.lstrip('/'))
        if not re.fullmatch(r'[\w.-]+\.drawio', nombre) or not (DIAGRAMAS / nombre).is_file():
            self.send_error(404)
            return
        cuerpo = (DIAGRAMAS / nombre).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        nombre = q.get('nombre', [''])[0]
        datos = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('ascii', 'ignore')
        if not re.fullmatch(r'[\w.-]+\.png', nombre) or ',' not in datos:
            self.send_error(400)
            return
        (SALIDA / nombre).write_bytes(base64.b64decode(datos.split(',', 1)[1]))
        self.send_response(204)
        self.end_headers()


http.server.ThreadingHTTPServer(('127.0.0.1', PUERTO), Manejador).serve_forever()
