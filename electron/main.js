const { app, BrowserWindow, dialog, Menu, shell, Tray, nativeImage, ipcMain, clipboard } = require('electron')
const path = require('path')

// Sin barra de menú nativa (Archivo/Editar/Ver…): se ve como app propia.
Menu.setApplicationMenu(null)
const fs = require('fs')
const { spawn } = require('child_process')

let ventanaPrincipal = null
let procesoPython = null
let bandeja = null
// Comportamiento al cerrar la ventana: 'salir' | 'minimizar'.
let cerrarModo = 'salir'
// Marca cuando el cierre es definitivo (para no minimizar al salir de verdad).
let saliendoDeVerdad = false
const ES_DESARROLLO = !app.isPackaged
const PUERTO_VITE = 5173

const RUTA_ICONO = path.join(app.getAppPath(), 'build', 'icon.ico')

// Estado de la app que informa la interfaz, para reflejarlo en el menú de la bandeja.
let estadoApp = {
  ledEncendido: true,
  ritmoActivado: false,
  ambilightActivado: false,
  visualActivo: false,
  visualUrl: '',
  modo: 'Color manual',
}

function mostrarVentana() {
  if (!ventanaPrincipal) return
  ventanaPrincipal.show()
  ventanaPrincipal.setSkipTaskbar(false)
  ventanaPrincipal.focus()
}

function salirDeVerdad() {
  saliendoDeVerdad = true
  app.quit()
}

// Envía una acción del menú de la bandeja a la interfaz para que la ejecute.
function enviarAccion(accion) {
  if (accion === 'fullscreen') mostrarVentana()
  if (ventanaPrincipal) ventanaPrincipal.webContents.send('lled:tray-accion', accion)
}

function construirMenuBandeja() {
  const e = estadoApp
  const items = [
    { label: 'Abrir LLeD', click: mostrarVentana },
    { type: 'separator' },
    { label: `Modo actual: ${e.modo || 'Color manual'}`, enabled: false },
    { type: 'separator' },
    { label: e.ledEncendido ? 'Apagar luces' : 'Encender luces', click: () => enviarAccion('power') },
    { label: e.ritmoActivado ? 'Desactivar modo ritmo' : 'Activar modo ritmo', click: () => enviarAccion('ritmo') },
    { label: e.ambilightActivado ? 'Desactivar modo cine' : 'Activar modo cine', click: () => enviarAccion('cine') },
    { type: 'separator' },
    { label: e.visualActivo ? 'Detener visual remoto' : 'Activar visual remoto', click: () => enviarAccion('visual') },
  ]
  if (e.visualActivo && e.visualUrl) {
    items.push({ label: 'Copiar dirección del visual', click: () => clipboard.writeText(e.visualUrl) })
  }
  items.push({ label: 'Ver visual en pantalla completa', click: () => enviarAccion('fullscreen') })
  items.push({ type: 'separator' })
  items.push({ label: 'Temporizador · 5 minutos', click: () => enviarAccion('timer:300') })
  items.push({ label: 'Temporizador · 10 minutos', click: () => enviarAccion('timer:600') })
  items.push({ label: 'Temporizador · 15 minutos', click: () => enviarAccion('timer:900') })
  items.push({ type: 'separator' })
  items.push({ label: 'Salir', click: salirDeVerdad })
  return Menu.buildFromTemplate(items)
}

function refrescarMenuBandeja() {
  if (bandeja) bandeja.setContextMenu(construirMenuBandeja())
}

function asegurarBandeja() {
  if (bandeja) return
  let imagen = nativeImage.createFromPath(RUTA_ICONO)
  if (imagen.isEmpty()) imagen = nativeImage.createEmpty()
  bandeja = new Tray(imagen)
  bandeja.setToolTip('LLeD')
  refrescarMenuBandeja()
  bandeja.on('click', mostrarVentana)
}

function iniciarServidorPython() {
  // En producción se lanza el backend congelado (servidor.exe) incluido como
  // extraResources. Los datos escribibles van a userData vía LLED_DATA_DIR.
  const userData = app.getPath('userData')
  const dirBackend = path.join(process.resourcesPath, 'backend')
  const rutaExe = path.join(dirBackend, 'servidor.exe')
  const logPath = path.join(userData, 'backend.log')

  let logStream = null
  try {
    logStream = fs.createWriteStream(logPath, { flags: 'a' })
  } catch (e) {
    logStream = null
  }

  procesoPython = spawn(rutaExe, [], {
    cwd: dirBackend,
    env: { ...process.env, LLED_DATA_DIR: userData },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  const escribir = (etiqueta) => (datos) => {
    const txt = `[${etiqueta}] ${datos.toString().trim()}`
    console.log(txt)
    if (logStream) logStream.write(txt + '\n')
  }
  procesoPython.stdout.on('data', escribir('servidor'))
  procesoPython.stderr.on('data', escribir('servidor'))

  procesoPython.on('error', () => {
    dialog.showErrorBox(
      'No se pudo iniciar la aplicación',
      'Hubo un problema al iniciar la aplicación. Cerrala y volvé a abrirla. Si el problema continúa, reinstalala.'
    )
  })

  procesoPython.on('close', (codigo) => {
    console.log(`Servidor Python terminado (código ${codigo})`)
    procesoPython = null
  })
}

function detenerServidorPython() {
  if (procesoPython) {
    procesoPython.kill()
    procesoPython = null
  }
}

async function crearVentana() {
  ventanaPrincipal = new BrowserWindow({
    width: 960,
    height: 700,
    minWidth: 600,
    minHeight: 500,
    title: 'LLeD',
    darkTheme: true,
    autoHideMenuBar: true,
    backgroundColor: '#05060a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  // Los enlaces externos (p. ej. el inicio de sesión de Spotify) se abren en el
  // navegador del sistema, no dentro de la ventana de la aplicación.
  ventanaPrincipal.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      shell.openExternal(url)
    }
    return { action: 'deny' }
  })

  if (ES_DESARROLLO) {
    await ventanaPrincipal.loadURL(`http://localhost:${PUERTO_VITE}`)
    ventanaPrincipal.webContents.openDevTools({ mode: 'detach' })
  } else {
    await ventanaPrincipal.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  // Al pulsar la X: minimizar al área de notificación o cerrar del todo,
  // según la preferencia elegida por el usuario en Ajustes.
  ventanaPrincipal.on('close', (evento) => {
    if (cerrarModo === 'minimizar' && !saliendoDeVerdad) {
      evento.preventDefault()
      ventanaPrincipal.hide()
      ventanaPrincipal.setSkipTaskbar(true)
    }
  })

  ventanaPrincipal.on('closed', () => {
    ventanaPrincipal = null
  })
}

// La preferencia de cierre llega desde la interfaz (Ajustes).
ipcMain.on('lled:set-cerrar-modo', (_evento, modo) => {
  cerrarModo = modo === 'minimizar' ? 'minimizar' : 'salir'
  if (cerrarModo === 'minimizar') asegurarBandeja()
})

// La interfaz informa su estado para actualizar el menú de la bandeja.
ipcMain.on('lled:estado', (_evento, estado) => {
  if (estado && typeof estado === 'object') {
    estadoApp = { ...estadoApp, ...estado }
    refrescarMenuBandeja()
  }
})

// Copia texto al portapapeles del sistema (p. ej. la dirección del visual).
ipcMain.on('lled:copiar', (_evento, texto) => {
  clipboard.writeText(String(texto || ''))
})

app.whenReady().then(async () => {
  // En desarrollo el backend lo arranca `npm run dev` (dev:servidor).
  if (!ES_DESARROLLO) {
    iniciarServidorPython()
  }
  await crearVentana()
})

app.on('window-all-closed', () => {
  detenerServidorPython()
  app.quit()
})

app.on('before-quit', () => {
  // Cierre definitivo: permite que la ventana se cierre (aunque esté en modo
  // minimizar), libera el backend y quita el icono del área de notificación.
  saliendoDeVerdad = true
  detenerServidorPython()
  if (bandeja) { bandeja.destroy(); bandeja = null }
})
