const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  esElectron: true,
  // Comunica al proceso principal qué hacer al cerrar la ventana:
  // 'salir' (cerrar del todo) o 'minimizar' (ir al área de notificación).
  setCerrarModo: (modo) => ipcRenderer.send('lled:set-cerrar-modo', modo),
  // Envía el estado actual de la app para reflejarlo en el menú de la bandeja.
  actualizarEstado: (estado) => ipcRenderer.send('lled:estado', estado),
  // Copia texto al portapapeles del sistema.
  copiarTexto: (texto) => ipcRenderer.send('lled:copiar', texto),
  // Suscribe un manejador a las acciones disparadas desde el menú de la bandeja.
  onAccionBandeja: (callback) => {
    const manejador = (_evento, accion) => callback(accion)
    ipcRenderer.on('lled:tray-accion', manejador)
    return () => ipcRenderer.removeListener('lled:tray-accion', manejador)
  },
})
