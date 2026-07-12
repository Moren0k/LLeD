const { app, BrowserWindow, dialog, Menu, shell } = require('electron')
const path = require('path')

// Sin barra de menú nativa (Archivo/Editar/Ver…): se ve como app propia.
Menu.setApplicationMenu(null)
const fs = require('fs')
const { spawn } = require('child_process')

let ventanaPrincipal = null
let procesoPython = null
const ES_DESARROLLO = !app.isPackaged
const PUERTO_VITE = 5173

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

  ventanaPrincipal.on('closed', () => {
    ventanaPrincipal = null
  })
}

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
  detenerServidorPython()
})
