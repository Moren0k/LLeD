import { ref, onMounted, onUnmounted } from 'vue'

const PUERTO = 8765

export function useWebSocket() {
  const conectado = ref(false)
  const error = ref(null)
  let socket = null
  let manejadores = {}
  let reintentarTimeout = null

  function conectar() {
    if (socket && socket.readyState === WebSocket.OPEN) return

    socket = new WebSocket(`ws://localhost:${PUERTO}`)

    socket.onopen = () => {
      conectado.value = true
      error.value = null
    }

    socket.onclose = () => {
      conectado.value = false
      reintentarTimeout = setTimeout(conectar, 3000)
    }

    socket.onerror = () => {
      error.value = 'Error al conectar con el servidor LED'
    }

    socket.onmessage = (evento) => {
      try {
        const datos = JSON.parse(evento.data)
        if (manejadores[datos.evento]) {
          manejadores[datos.evento](datos)
        }
      } catch {
        console.warn('Mensaje inválido:', evento.data)
      }
    }
  }

  function enviar(comando, datos = {}) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ comando, ...datos }))
    } else {
      console.warn('WebSocket no conectado, no se pudo enviar:', comando)
    }
  }

  function on(evento, callback) {
    manejadores[evento] = callback
  }

  function desconectar() {
    if (reintentarTimeout) {
      clearTimeout(reintentarTimeout)
    }
    if (socket) {
      socket.close()
      socket = null
    }
  }

  onMounted(() => conectar())
  onUnmounted(() => desconectar())

  return { conectado, error, enviar, on, desconectar }
}
