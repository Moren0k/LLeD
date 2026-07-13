# LLeD

Convertí tu tira LED Bluetooth en la iluminación de tu cuarto: que cambie de
color con la canción que suena en Spotify, que lata al ritmo de la música, que
siga los colores de lo que ves en pantalla y que muestre visuales animados.
Todo desde una app de escritorio, sin saber nada de programación.

## Descargar (Windows)

Bajá la última versión desde la página de Releases:

**https://github.com/Moren0k/LLeD/releases/latest**

Elegí la opción que prefieras:

- **Instalador** (`LLeD-Instalador-x.y.z.exe`): instala la app en tu equipo y te
  deja el acceso directo. Es la opción recomendada para el día a día.
- **Portable** (`LLeD-Portable-x.y.z.exe`): un solo archivo que se abre sin
  instalar nada. Ideal para probarla rápido o llevarla en un USB.

No necesitás tener Python ni nada más instalado. La primera vez, Windows puede
pedirte permiso de firewall para el visual remoto: aceptá en red privada.

## Documentación

Según lo que quieras hacer:

- **Usar y ejecutar el proyecto** (instalar dependencias, correrlo, generar los
  ejecutables): [RUN.md](https://github.com/Moren0k/LLeD/blob/main/RUN.md)
- **Trabajar en el código y aportar mejoras** (montar el entorno, estructura,
  convenciones, cómo publicar versiones): [WorkHere.md](https://github.com/Moren0k/LLeD/blob/main/WorkHere.md)

## Qué es LLeD

LLeD conecta una tira LED Bluetooth a tu computadora y te la deja controlar
desde una interfaz simple: elegís colores, la sincronizás con la música de
Spotify, hacés que reaccione al ritmo, que acompañe lo que pasa en la pantalla o
que muestre fondos animados. También trae un temporizador con aviso luminoso.

La idea es sencilla: darte una forma fácil y bonita de ambientar tu espacio con
luz que acompaña a la música y a lo que estás viendo.

## Cómo funciona

Por dentro, el sistema tiene tres partes que se hablan entre sí:

- **El backend (Python).** Un servidor local por WebSocket es el que controla la
  tira por Bluetooth y coordina todo lo demás (Spotify, ritmo, modo cine,
  visuales y temporizador).
- **La interfaz (Vue 3 en Electron).** La ventana de escritorio con las pantallas
  de control; se comunica con el backend por WebSocket.
- **El visual remoto.** Un servidor local extra publica una página con el visual
  animado para que la abras desde otro dispositivo de tu red (el celular, la TV,
  otra compu) y se vea sincronizada en tiempo real.

Para repartir la app, el backend se empaqueta como un ejecutable aparte y la
interfaz se entrega como instalador, así que en el equipo final no hace falta
tener Python instalado.

## Qué podés hacer

- **Controlar la tira.** Prenderla y apagarla, elegir color y brillo, y
  seleccionar tu dispositivo desde la propia app.
- **Sincronizarla con Spotify.** El color sigue a la canción que suena, ya sea
  por el color de la portada o por el ánimo del tema.
- **Guardar el color de cada canción.** La primera vez que suena un tema, LLeD
  guarda su color para aplicarlo al instante la próxima vez. Podés
  personalizarlo cuando quieras.
- **Transiciones suaves.** Cambios de color graduales entre canciones (o
  instantáneos, si preferís).
- **Modo ritmo.** La tira reacciona al audio del equipo con destellos en los
  golpes de la música.
- **Modo cine.** La tira toma un color ambiente a partir de lo que se ve en la
  pantalla, combinado con la reacción al sonido.
- **Visuales.** Fondos animados (aurora, orbes u ondas) que siguen el color y el
  ritmo, con opción de verlos a pantalla completa o en otro dispositivo.
- **Temporizador.** Cuenta regresiva con aviso luminoso al terminar y un visual
  de reloj o tarjeta mientras corre.
- **Ajustes.** Tus preferencias quedan guardadas, y podés restablecer la
  configuración o el historial de colores cuando lo necesites.

## Tecnologías

- **Backend:** Python 3, asyncio, WebSockets, Bluetooth LE (bleak), integración
  con Spotify (spotipy, OAuth PKCE), análisis de imagen (Pillow, colorthief),
  cálculo numérico (numpy), captura de audio (pyaudiowpatch) y de pantalla (mss).
- **Interfaz:** Vue 3 y Vite.
- **Escritorio:** Electron.
- **Empaquetado:** PyInstaller (backend) y electron-builder con instalador NSIS.
- **Pruebas:** pytest.

## Estructura del proyecto

```
led-spotify/
├── servidor.py            Servidor WebSocket y orquestador del backend
├── led.py                 Control de la tira LED por Bluetooth
├── main.py                Utilidad de línea de comandos para la tira LED
├── spotify_cliente.py     Integración con Spotify (OAuth PKCE)
├── extractor_color.py     Extracción de color a partir de portadas
├── cache_colores.py       Almacenamiento del color por canción
├── transiciones.py        Motor de transiciones de color
├── audio_ritmo_final.py   Detección de ritmo del audio
├── dsp_engine_v3.py       Motor de procesamiento de señal de audio
├── ambilight.py           Captura de pantalla para el modo cine
├── letras.py              Letra sincronizada de las canciones
├── visual_server.py       Servidor del visual remoto
├── timer.py               Temporizador
├── ajustes.py             Preferencias persistentes
├── rutas.py               Rutas de datos y recursos
├── registro.py            Registro de eventos (logging)
├── motor_visual.js        Motor de visuales en canvas (interfaz y visual remoto)
├── electron/              Aplicación de escritorio (Electron)
├── src/                   Interfaz (Vue 3)
│   ├── App.vue            Estructura general y navegación
│   ├── styles.css         Sistema de diseño
│   ├── composables/       Conexión y estado compartido
│   └── components/        Páginas y componentes de la interfaz
├── tests/                 Pruebas automatizadas (pytest)
├── build/                 Recursos de empaquetado (icono, instalador)
├── servidor.spec          Configuración de empaquetado del backend
├── package.json           Dependencias y scripts de la interfaz
├── requirements.txt       Dependencias del backend
└── config.example.json    Plantilla de configuración local
```

## Bueno saberlo

- La tira LED es de un solo color a la vez: muestra un color uniforme en toda su
  extensión.
- La sincronización con Spotify usa tu propia cuenta; cada persona inicia sesión
  con la suya.
- El modo cine funciona por color y sonido, no interpreta la escena. Con
  contenido protegido, si la captura de pantalla no está disponible, sigue
  funcionando solo con el audio.
- El visual remoto se sirve en tu red local: los dispositivos que lo abran tienen
  que estar en la misma red.
- Tus datos (configuración, ajustes, biblioteca de colores y sesión de Spotify)
  se guardan en la carpeta de datos de la aplicación, fuera del proyecto.

## Querés mejorarlo

Genial. Todo lo necesario para montar el entorno de desarrollo, entender cómo
está armado, seguir las convenciones del código y publicar nuevas versiones está
en [WorkHere.md](https://github.com/Moren0k/LLeD/blob/main/WorkHere.md). Si solo
querés ejecutarlo o generar los ejecutables, mirá
[RUN.md](https://github.com/Moren0k/LLeD/blob/main/RUN.md).
