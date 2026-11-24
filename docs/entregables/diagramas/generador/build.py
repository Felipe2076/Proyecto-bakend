import sys, pathlib, importlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from drawio import guardar

DESTINO = pathlib.Path(sys.argv[1])
DESTINO.mkdir(parents=True, exist_ok=True)
ARCHIVOS = {
    'gen_requerimientos': '01_Requerimientos_SIGED.drawio',
    'gen_casos_uso': '02_Casos_de_Uso_SIGED.drawio',
    'gen_clases': '03_Diagrama_de_Clases_SIGED.drawio',
    'gen_arquitectura': '04_Componentes_y_Despliegue_SIGED.drawio',
    'gen_comportamiento': '05_Secuencia_Actividad_Estados_SIGED.drawio',
    'gen_trazabilidad': '06_Trazabilidad_y_Reflejo_en_Prototipo_SIGED.drawio',
}
solo = sys.argv[2:] or list(ARCHIVOS)
for mod in solo:
    if not (pathlib.Path(__file__).parent / f'{mod}.py').exists():
        continue
    m = importlib.import_module(mod)
    ps = m.paginas()
    ruta = guardar(DESTINO / ARCHIVOS[mod], ps)
    print(f'{ARCHIVOS[mod]}: {len(ps)} páginas')
