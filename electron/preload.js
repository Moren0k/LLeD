const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  esElectron: true,
  // Comunica al proceso principal qué hacer al cerrar la ventana:
  // 'salir' (cerrar del todo) o 'minimizar' (ir al área de notificación).
  setCerrarModo: (modo) => ipcRenderer.send('lled:set-cerrar-modo', modo),
})
