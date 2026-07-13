# LLeD

Aplicación de escritorio para controlar tiras LED Bluetooth y sincronizarlas con
la música y el contenido de la pantalla.

## Descargar (Windows)

Descargá la última versión desde la página de Releases del repositorio:

**https://github.com/Moren0k/LLeD/releases/latest**

Hay dos opciones:

- **Instalador** (`LLeD-Instalador-x.y.z.exe`): instala la aplicación en el
  equipo y crea el acceso directo. Recomendado para uso normal.
- **Portable** (`LLeD-Portable-x.y.z.exe`): un único ejecutable que se abre sin
  instalar nada. Ideal para probarla o llevarla en un USB.

No requiere tener Python ni nada más instalado. En el primer uso, Windows puede
pedir permiso de firewall para el visual remoto (aceptar en red privada).

## Descripción

LLeD conecta una tira LED Bluetooth al equipo y permite controlarla desde una
interfaz gráfica: elegir colores, sincronizar el color con la canción que suena
en Spotify, reaccionar al ritmo de la música, seguir los colores de la pantalla
y mostrar visuales animados. Incluye además un temporizador con aviso luminoso.

## Propósito

Ofrecer una forma simple y visual de ambientar un espacio con luz que acompaña a
la música y a lo que se está viendo, sin necesidad de conocimientos técnicos por
parte del usuario final.

## Arquitectura general

El sistema tiene tres partes que se comunican entre sí:

- **Backend (Python).** Un servidor local por WebSocket controla la tira LED por
  Bluetooth y coordina el resto de funciones (Spotify, ritmo, modo cine, visuales
  y temporizador).
- **Interfaz (Vue 3 en Electron).** La aplicación de escritorio muestra las
  pantallas de control y se comunica con el backend por WebSocket.
- **Visual remoto.** Un servidor local adicional publica una página con el visual
  animado para abrirla desde otros dispositivos de la misma red (celular, TV,
  computadora), sincronizada en tiempo real.

Para la distribución, el backend se empaqueta como ejecutable independiente y la
interfaz se entrega como instalador de escritorio, de modo que el equipo final no
necesita tener Python instalado.

## Tecnologías utilizadas

- **Backend:** Python 3, asyncio, WebSockets, Bluetooth LE (bleak), integración
  con Spotify (spotipy, OAuth PKCE), análisis de imagen (Pillow, colorthief),
  cálculo numérico (numpy), captura de audio (pyaudiowpatch) y de pantalla (mss).
- **Interfaz:** Vue 3 y Vite.
- **Escritorio:** Electron.
- **Empaquetado:** PyInstaller (backend) y electron-builder con instalador NSIS.
- **Pruebas:** pytest.

## Funcionalidades principales

- **Control de la tira LED.** Encendido/apagado, color y brillo de tiras LED
  Bluetooth compatibles, con selección del dispositivo desde la aplicación.
- **Sincronización con Spotify.** El color de la tira sigue a la canción actual,
  ya sea por el color de la portada o por el ánimo del tema.
- **Biblioteca de colores.** Cada canción guarda su color la primera vez que
  suena, para aplicarlo de inmediato la próxima vez. El color de cada canción se
  puede personalizar.
- **Transiciones.** Cambios de color suaves entre canciones, con modo gradual o
  instantáneo.
- **Modo ritmo.** La tira reacciona al audio del equipo con destellos en los
  golpes de la música.
- **Modo cine.** La tira toma un color ambiente a partir de lo que se ve en la
  pantalla, combinado con la reacción al audio.
- **Visuales.** Fondo animado (aurora, orbes u ondas) que sigue el color y el
  ritmo, con posibilidad de verlo a pantalla completa o en otro dispositivo de la
  red.
- **Temporizador.** Cuenta regresiva con aviso luminoso al finalizar y un visual
  de reloj o tarjeta durante la cuenta.
- **Ajustes.** Preferencias persistentes y opción de restablecer la
  configuración o el historial de colores.

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
├── visual_server.py       Servidor del visual remoto
├── timer.py               Temporizador
├── ajustes.py             Preferencias persistentes
├── rutas.py               Rutas de datos y recursos
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

## Información funcional relevante

- La tira LED es monocromática: muestra un único color a la vez en toda su
  extensión.
- La sincronización con Spotify usa la cuenta del propio usuario; cada persona
  inicia sesión con su cuenta.
- El modo cine funciona por color y sonido; no interpreta la escena. Con
  contenido protegido, si la captura de pantalla no está disponible, continúa
  funcionando solo con el audio.
- El visual remoto se sirve en la red local; los dispositivos que lo abren deben
  estar conectados a la misma red.
- Los datos del usuario (configuración, ajustes, biblioteca de colores y sesión
  de Spotify) se guardan en la carpeta de datos de la aplicación, fuera del
  directorio del proyecto.

Para instalar, ejecutar, desarrollar, generar builds y probar el proyecto,
consultar `RUN.md`.
