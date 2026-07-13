# Guía para trabajar en LLeD (desarrollo)

Todo lo necesario para clonar, montar el entorno, entender el proyecto, hacer
mejoras y publicar versiones. Para instrucciones más breves de ejecución mirá
también `RUN.md`; para la descripción del sistema, `README.md`.

Repositorio: https://github.com/Moren0k/LLeD

---

## 1. Requisitos

- **Windows 10 u 11** con Bluetooth (la tira se controla por Bluetooth LE).
- **Node.js 18 o superior** (la CI usa 20).
- **Python 3.10 a 3.12** (la CI usa 3.12).
- **Git**.
- Para el **modo ritmo / cine**: la captura de audio del sistema debe estar
  habilitada en Windows (dispositivo de grabación tipo "Mezcla estéreo").
- Una **tira LED Bluetooth compatible** para probar contra hardware real
  (opcional: gran parte se puede desarrollar sin ella, ver más abajo).

En Windows, cuidado con el alias falso de Python de la Microsoft Store: si
`python` abre la Store o falla, usá el intérprete real (por ejemplo el de
`py -3.12` o la ruta absoluta de tu instalación).

---

## 2. Clonar el repositorio

```
git clone https://github.com/Moren0k/LLeD.git
cd LLeD
```

La raíz del repositorio **es** la carpeta del proyecto (ahí están `package.json`,
`servidor.py`, `src/`, etc.).

---

## 3. Instalación

Dependencias del backend (Python):

```
pip install -r requirements.txt
```

Dependencias de la interfaz (Node):

```
npm install
```

Para poder correr las pruebas, además:

```
pip install -r requirements-dev.txt
```

---

## 4. Configuración

La aplicación funciona **sin configuración manual**: trae incluido lo necesario
para conectarse con Spotify (usa OAuth PKCE, así que **no hay ningún secreto que
poner**). Puntos a tener en cuenta:

- **Dispositivo LED**: no se configura a mano; se elige desde la app (sección
  Ajustes) escaneando por Bluetooth.
- **Configuración local opcional**: si querés usar tu propia aplicación de
  Spotify, copiá `config.example.json` a `config.json` y completá el
  identificador de cliente. `config.json` está en `.gitignore` (no se versiona).
- **Datos del usuario**: la configuración, ajustes, biblioteca de colores y
  sesión de Spotify se guardan fuera del proyecto (en la carpeta de datos de la
  aplicación). En desarrollo se usan archivos locales dentro del proyecto que
  también están en `.gitignore` (`ajustes.json`, `color_cache.json`,
  `.spotify_cache`).
- **Logs detallados en desarrollo**: por defecto, en desarrollo se ven logs de
  nivel informativo; en la app compilada solo advertencias y errores. Para
  forzar el modo detallado, definí la variable de entorno `LLED_DEBUG=1` antes de
  arrancar el backend.

No hay más variables que configurar para desarrollar.

---

## 5. Ejecutar en modo desarrollo

Todo junto (arranca backend + interfaz + ventana de escritorio):

```
npm run dev
```

O cada parte por separado, en terminales distintas:

```
python servidor.py      # backend: servidor WebSocket local (puerto 8765)
npm run dev:front        # interfaz Vite en modo desarrollo (puerto 5173)
npm run dev:electron     # ventana de escritorio (Electron), abre las DevTools
```

Notas:

- En `npm run dev:electron`, Electron carga la interfaz desde Vite
  (`http://localhost:5173`) y abre las herramientas de desarrollo.
- **Sin hardware**: el backend arranca igual aunque no haya tira conectada (usa
  un dispositivo "nulo" que no hace nada). Podés desarrollar y probar casi todo
  (interfaz, Spotify, letras, visuales, temporizador) sin la tira. Solo el efecto
  físico en las luces requiere el dispositivo.
- Si `config.json` tiene una dirección de dispositivo guardada y la tira no está,
  el backend puede tardar unos segundos intentando conectarse por Bluetooth.

---

## 6. Arquitectura general

Tres piezas que se comunican entre sí:

- **Backend (Python)** — `servidor.py`: un servidor WebSocket local
  (`ws://localhost:8765`). Controla la tira por Bluetooth y coordina los modos
  (Spotify, ritmo, cine, ambiente, temporizador, letra). La interfaz le manda
  comandos y él responde con eventos.
- **Interfaz (Vue 3 + Vite, dentro de Electron)** — `src/`: las pantallas de
  control. Se comunica con el backend por WebSocket.
- **Visual remoto** — `visual_server.py`: un servidor HTTP (puerto 8770) que
  sirve una página con el mismo visual, y un WebSocket (puerto 8771) que le
  difunde en vivo color, ritmo, portada, letra, etc. Se abre desde otro
  dispositivo de la misma red.

El **motor de visuales** (`motor_visual.js`) es un archivo de canvas compartido
por la interfaz y por la página del visual remoto: un cambio ahí afecta a ambos.

---

## 7. Estructura del proyecto

```
Backend (Python)
  servidor.py            Servidor WebSocket y orquestador (comandos + bucles de cada modo)
  led.py                 Control de la tira por Bluetooth (+ corrección de gamma)
  spotify_cliente.py     Integración con Spotify (OAuth PKCE, canción actual, progreso)
  extractor_color.py     Color a partir de la portada del álbum
  cache_colores.py       Color guardado por canción
  transiciones.py        Motor de transiciones de color (crossfade / fades)
  audio_ritmo_final.py   Detección de ritmo del audio del sistema
  dsp_engine_v3.py       Motor de procesamiento de señal de audio
  ambilight.py           Captura de pantalla para el modo cine
  letras.py              Letra sincronizada (fuente LRCLIB) + parseo LRC
  timer.py               Temporizador
  ajustes.py             Preferencias persistentes (ajustes.json) con validación
  rutas.py               Resolución de rutas de datos y recursos
  registro.py            Logging central (silencioso en producción)
  main.py                Utilidad de línea de comandos para la tira (opcional)
  motor_visual.js        Motor de visuales en canvas (interfaz + visual remoto)

Interfaz (Vue 3)
  index.html, vite.config.js
  src/main.js            Punto de entrada de Vue
  src/App.vue            Estructura general, barra superior, pestañas, fondo
  src/styles.css         Sistema de diseño (clases compartidas)
  src/composables/
    useWebSocket.js      Conexión WebSocket con el backend
    useControlador.js    Estado y acciones compartidas (store central)
  src/components/
    Pagina*.vue          Una pantalla por pestaña (Color, Spotify, Ritmo, Timer,
                         Visuales, Cine, Biblioteca, Ajustes)
    SelectorColor.vue    Selector de color HSV propio
    VisualCanvas.vue     Lienzo del visual (usa motor_visual.js)
    VisualFullscreen.vue Visual a pantalla completa (título, portada, letra)
    AyudaInfo.vue        Botón de ayuda "(i)" con globo informativo

Escritorio y empaquetado
  electron/main.js       Proceso principal de Electron (ventana, bandeja, backend)
  electron/preload.js    Puente seguro entre interfaz y proceso principal
  servidor.spec          Configuración de PyInstaller (congela el backend)
  build_backend.ps1      Script que congela el backend a ejecutable
  build/                 Recursos de empaquetado (icono, script del instalador)

Configuración y meta
  requirements.txt / requirements-dev.txt   Dependencias Python
  package.json           Dependencias y scripts de la interfaz + config de build
  pytest.ini             Configuración de pruebas
  config.example.json    Plantilla de configuración local
  .github/workflows/release.yml   Compilación y publicación automática (ver §11)
  tests/                 Pruebas automatizadas (pytest)
```

---

## 8. Tecnologías

- **Backend**: Python 3, asyncio, WebSockets, Bluetooth LE (bleak), Spotify
  (spotipy, OAuth PKCE), imagen (Pillow, colorthief), numpy, captura de audio
  (pyaudiowpatch), captura de pantalla (mss), HTTP (requests, para LRCLIB).
- **Interfaz**: Vue 3 (Composition API) y Vite.
- **Escritorio**: Electron.
- **Empaquetado**: PyInstaller (backend) y electron-builder (instalador NSIS y
  ejecutable portable).
- **Pruebas**: pytest (con pytest-asyncio).

---

## 9. Convenciones del frontend (importante al hacer mejoras)

- **Sistema de diseño centralizado en `src/styles.css`**: usá las clases
  compartidas (`.pagina`, `.card`, `.sub` para títulos de sección, `.fila`,
  `.nota`, `.valor`, `.estado`/`.dot`, `.segmented`, `.toggle`, `.slider`,
  `.swatch`, `.badge`, `.input`, `.btn`/`.btn-tint`/`.btn-glass`, etc.). No
  dupliques estilos por página: si algo se repite, va en `styles.css`.
- **Ayuda**: la información técnica o explicaciones largas van dentro de un
  `<AyudaInfo>` (el botón "(i)"), no sueltas en la interfaz.
- **Estado y acciones**: se manejan en `useControlador.js` (se inyecta como
  `ctrl` en las páginas con `provide/inject`). Los comandos al backend se mandan
  con `enviar(...)` y los eventos se escuchan con `on(...)`.
- **Visual remoto**: si un dato tiene que verse también en el visual remoto,
  hay que difundirlo desde el hub (`visual_server.py`) y aplicarlo en la página
  remota (el HTML embebido en ese archivo).

### Cómo agregar una mejora típica

- **Un ajuste nuevo**: agregarlo a `DEFAULTS` y a la validación en `ajustes.py`,
  a la reactiva `ajustes` en `useControlador.js`, y un control en la página
  correspondiente con `ctrl.setAjuste('clave', valor)`.
- **Un comando nuevo**: manejarlo en `servidor.py` (dentro de `manejar_cliente`)
  y exponer una acción en `useControlador.js` que haga `enviar('comando', ...)`.
- **Un modo nuevo** (como ritmo/cine/ambiente): un bucle asíncrono en
  `servidor.py`, comandos para iniciarlo/detenerlo, estado en `spotify_estado`,
  limpieza en el `finally` de la conexión, y su UI en una `Pagina*.vue`.

---

## 10. Pruebas y validación

Correr la suite (sin hardware ni red, con tira y Spotify simulados):

```
pytest
```

Antes de subir cambios grandes, validá al menos:

- La interfaz compila sin errores: `npm run build:front`.
- Las pruebas pasan: `pytest`.
- Si cambiaste comportamiento de la app, probalo end-to-end en `npm run dev`.

---

## 11. Versionado y publicación (cómo subir una versión)

Las versiones descargables se publican **automáticamente en GitHub** al subir un
**tag** `vX.Y.Z`. Los push normales a `main` NO generan ni actualizan la
descarga: solo el tag dispara la compilación y el Release.

### Cuándo subir la versión (versionado semántico X.Y.Z)

- **X (mayor)**: cambios grandes o que rompen compatibilidad.
- **Y (menor)**: funcionalidades nuevas que no rompen nada.
- **Z (parche)**: correcciones de errores y ajustes menores.

Subí una versión cuando quieras dejar disponible un ejecutable estable para
descargar. El trabajo del día a día (commits/push a `main`) no necesita versión.

### Cómo subir la versión (paso a paso)

1. Asegurate de que `main` esté como querés publicar (probado, tests en verde).
2. Subí el número en `package.json` para que el archivo tenga ese número; por
   ejemplo, `2.1.0`. Se puede hacer a mano o con:

   ```
   npm version 2.1.0 --no-git-tag-version
   ```

3. Commiteá y subí ese cambio:

   ```
   git add package.json package-lock.json
   git commit -m "Versión 2.1.0"
   git push origin main
   ```

4. Creá y subí el tag (debe empezar con `v` y coincidir con `package.json`):

   ```
   git tag v2.1.0
   git push origin v2.1.0
   ```

5. Eso dispara el flujo de GitHub Actions (`.github/workflows/release.yml`), que
   en Windows compila la interfaz, congela el backend y arma el instalador y el
   portable, y los publica como un Release. En unos minutos quedan para
   descargar en la página de Releases. Podés seguir el avance en la pestaña
   **Actions** del repositorio.

Los archivos publicados son:

- `LLeD-Instalador-X.Y.Z.exe` — instalador.
- `LLeD-Portable-X.Y.Z.exe` — ejecutable portable (sin instalar).

(GitHub además adjunta automáticamente el "Source code" en zip a cualquier tag;
es normal e independiente de los ejecutables.)

Descargas: https://github.com/Moren0k/LLeD/releases/latest

---

## 12. Compilar localmente (opcional)

Normalmente no hace falta (de la compilación se encarga la CI al subir el tag),
pero si querés generar los ejecutables en tu equipo:

```
npm run build
```

Hace, en orden: `build:front` (interfaz), `build:backend` (congela el backend con
PyInstaller) y `build:electron` (instalador + portable, sin publicar). El
resultado queda en `dist_installer/`:

- `dist_installer/LLeD-Instalador-X.Y.Z.exe` (instalador)
- `dist_installer/LLeD-Portable-X.Y.Z.exe` (portable)

Importante:

- En Windows, electron-builder necesita permiso para crear enlaces simbólicos:
  activá el **Modo de desarrollador** de Windows o corré la terminal como
  **Administrador** antes del build.
- El archivo `dist_installer/win-unpacked/LLeD.exe` **no** se comparte: es la app
  "cruda" que depende de toda esa carpeta. Para repartir se usan el instalador o
  el portable.

---

## 13. Flujo de Git

- Rama principal: **`main`** (es de donde se publican las versiones).
- Para cambios chicos: commiteá y `git push origin main`.
- Para funcionalidades grandes: trabajá en una rama aparte y luego integrala a
  `main` (por merge directo o con un Pull Request).
- Los avisos de "LF will be replaced by CRLF" al hacer commit en Windows son
  normales e inofensivos.

---

## 14. Solución de problemas

- **`python` no funciona / abre la Store**: es el alias falso de Windows. Usá el
  Python real (`py -3.12 ...` o la ruta de tu instalación).
- **El botón "Conectar" de Spotify no responde**: se abre el navegador para
  iniciar sesión y el backend captura el retorno en `127.0.0.1:8888`. Si el
  navegador no abre solo, en la app hay un enlace de respaldo.
- **El ritmo o el cine no reaccionan al audio**: falta habilitar la "Mezcla
  estéreo" en la configuración de sonido de Windows.
- **No hay letra en una canción**: no todas tienen letra sincronizada en LRCLIB;
  se avisa en la sección Visuales.
- **El build local falla en el paso de electron-builder**: activá el Modo de
  desarrollador de Windows o corré la terminal como Administrador (ver §12).

---

## 15. Enlaces útiles

- Repositorio: https://github.com/Moren0k/LLeD
- Descargas (Releases): https://github.com/Moren0k/LLeD/releases
- Descripción del sistema: `README.md`
- Ejecución rápida: `RUN.md`
