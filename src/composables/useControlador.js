import { ref, reactive } from 'vue'
import { useWebSocket } from './useWebSocket.js'

/**
 * Estado y acciones compartidas de toda la app.
 * Se crea UNA vez en App.vue y se reparte a las páginas con provide/inject.
 */
export function useControlador() {
  const { conectado: conectadoLed, error: errorConexion, enviar, on } = useWebSocket()

  // ── Estado LED / color ──
  const ledEncendido = ref(true)
  const colorActual = reactive({ r: 255, g: 0, b: 0 })
  // Color del fondo/visuales: sigue cada paso de la transición (fluido).
  const colorFondo = reactive({ r: 255, g: 0, b: 0 })
  const brilloActual = ref(255)

  // ── Log ──
  const log = reactive([])

  // ── Ritmo ──
  const ritmoActivado = ref(false)
  const ritmoDisponible = ref(false)
  const flashColor = reactive({ r: 255, g: 255, b: 255 })
  const flashDeCancion = ref(false)
  const flashOnly = ref(false)
  const modoDeteccion = ref('kick')

  // ── Spotify ──
  const spotifyAutenticado = ref(false)
  const spotifySincronizando = ref(false)
  const spotifyCargando = ref(false)
  const spotifyTieneCredenciales = ref(false)
  const spotifyModo = ref('portada')
  const cancionActual = ref('')
  const artistaActual = ref('')
  const portadaActual = ref('')
  const fuenteColorActual = ref('')

  // ── Ajustes / biblioteca ──
  const ajustes = reactive({
    modo_transicion: 'gradiente',
    duracion_crossfade: 0.6,
    duracion_fade_out: 0.35,
    duracion_fade_in: 0.5,
    fps_transicion: 30,
    sync_modo: 'portada',
    intervalo_spotify: 0.8,
    visual_titulo: true,
    visual_titulo_escala: 1.0,
    visual_titulo_x: 0.5,
    visual_titulo_y: 0.85,
  })
  const biblioteca = ref([])
  const mostrarFull = ref(false)

  // ── Dispositivo BLE ──
  const dispositivo = reactive({ direccion: null, conectado: false })
  const dispositivos = ref([])
  const escaneando = ref(false)

  // ── Visual remoto ──
  const visual = reactive({ activo: false, url: '', url_local: '', ip: '', puerto: 0 })

  // ── Beat (para animar el fondo) ──
  const beatActivo = ref(false)
  const beatTick = ref(0)
  const beatEnergia = ref(0.6)
  let beatTimer = null

  const modosDeteccion = [
    { modo: 'kick', label: 'Kicks' },
    { modo: 'bass', label: 'Bajos' },
    { modo: 'full', label: 'Ambos' },
  ]

  const coloresFlash = [
    { nombre: 'Blanco', r: 255, g: 255, b: 255 },
    { nombre: 'Rojo', r: 255, g: 0, b: 0 },
    { nombre: 'Naranja', r: 255, g: 128, b: 0 },
    { nombre: 'Amarillo', r: 255, g: 255, b: 0 },
    { nombre: 'Verde', r: 0, g: 255, b: 0 },
    { nombre: 'Cian', r: 0, g: 255, b: 255 },
    { nombre: 'Azul', r: 0, g: 0, b: 255 },
    { nombre: 'Morado', r: 128, g: 0, b: 255 },
    { nombre: 'Rosa', r: 255, g: 0, b: 255 },
  ]

  const slidersTransicion = [
    { clave: 'duracion_crossfade', label: 'Directo' },
    { clave: 'duracion_fade_out', label: 'Apagado' },
    { clave: 'duracion_fade_in', label: 'Encendido' },
  ]

  let debounceDuracion = null

  function agregarLog(mensaje) {
    log.unshift(mensaje)
    if (log.length > 25) log.pop()
  }

  // ── Acciones LED ──
  function aplicarColor({ r, g, b }) {
    colorActual.r = r
    colorActual.g = g
    colorActual.b = b
    colorFondo.r = r
    colorFondo.g = g
    colorFondo.b = b
    enviar('color', { r, g, b })
  }

  function aplicarBrillo(valor) {
    brilloActual.value = valor
    enviar('brillo', { valor })
  }

  function togglePower() {
    // Usa el estado REAL de la tira (no el de la conexión).
    if (ledEncendido.value) {
      enviar('apagar')
    } else {
      enviar('encender')
    }
  }

  function encender() { enviar('encender') }
  function apagar() { enviar('apagar') }
  function probar() { enviar('probar') }
  function arcoiris() { enviar('arcoiris', { pasos: 12, demora: 0.8 }) }

  // ── Acciones Spotify ──
  function iniciarSesionSpotify() {
    spotifyCargando.value = true
    enviar('spotify_login')
  }
  function cerrarSesionSpotify() { enviar('spotify_logout') }
  function iniciarSincronizacion(modo) { enviar('spotify_iniciar', { modo }) }
  function detenerSincronizacion() { enviar('spotify_detener') }
  function cambiarModoSync(modo) {
    spotifyModo.value = modo
    enviar('spotify_modo', { modo })
  }
  function pedirEstadoSpotify() { enviar('spotify_estado') }

  // ── Acciones Ritmo ──
  function toggleRitmo() {
    if (ritmoActivado.value) enviar('ritmo_detener')
    else enviar('ritmo_iniciar')
  }
  function cambiarFlashColor(r, g, b) {
    flashDeCancion.value = false
    flashColor.r = r
    flashColor.g = g
    flashColor.b = b
    enviar('ritmo_flash_color', { r, g, b })
  }
  function flashColorCancion() {
    flashDeCancion.value = true
    flashColor.r = colorActual.r
    flashColor.g = colorActual.g
    flashColor.b = colorActual.b
    enviar('ritmo_flash_color', { r: colorActual.r, g: colorActual.g, b: colorActual.b })
  }
  function toggleFlashOnly() { enviar('ritmo_flash_only', { activado: flashOnly.value }) }
  function cambiarModoDeteccion(modo) {
    modoDeteccion.value = modo
    enviar('ritmo_modo_deteccion', { modo })
  }

  // ── Acciones Ajustes / biblioteca ──
  function cambiarModoTransicion(modo) {
    ajustes.modo_transicion = modo
    enviar('ajustes_guardar', { cambios: { modo_transicion: modo } })
  }
  function cambiarDuracion(clave, valor) {
    const num = Number(valor)
    ajustes[clave] = num
    clearTimeout(debounceDuracion)
    debounceDuracion = setTimeout(() => {
      enviar('ajustes_guardar', { cambios: { [clave]: num } })
    }, 200)
  }
  function cargarBiblioteca() { enviar('cache_listar') }

  // ── Dispositivo ──
  function escanear() {
    escaneando.value = true
    dispositivos.value = []
    enviar('escanear')
  }
  function conectarDispositivo(direccion) { enviar('conectar_dispositivo', { direccion }) }

  // ── Visual ──
  function iniciarVisual() { enviar('visual_iniciar') }
  function detenerVisual() { enviar('visual_detener') }
  function abrirVisualFull() { mostrarFull.value = true }
  function cerrarVisualFull() { mostrarFull.value = false }

  // ── Ajuste genérico (con debounce para sliders/arrastre) ──
  let debounceAjuste = null
  function setAjuste(clave, valor, inmediato = false) {
    ajustes[clave] = valor
    const enviarlo = () => enviar('ajustes_guardar', { cambios: { [clave]: valor } })
    if (inmediato) {
      clearTimeout(debounceAjuste)
      enviarlo()
    } else {
      clearTimeout(debounceAjuste)
      debounceAjuste = setTimeout(enviarlo, 120)
    }
  }
  function editarColorCancion(cancionId, { r, g, b }) {
    enviar('cache_editar', { cancion_id: cancionId, r, g, b })
  }
  function eliminarCancion(cancionId) { enviar('cache_eliminar', { cancion_id: cancionId }) }

  // ── Handlers de eventos del servidor ──
  on('conectado', (d) => {
    agregarLog('Conectado al servidor LED')
    ledEncendido.value = true // el servidor enciende la tira al conectar
    if (d && d.dispositivo) Object.assign(dispositivo, d.dispositivo)
    setTimeout(() => {
      pedirEstadoSpotify()
      cargarBiblioteca()
    }, 400)
  })

  on('encendido', () => { ledEncendido.value = true })
  on('apagado', () => { ledEncendido.value = false })

  on('color', (d) => {
    // El servidor confirma; si estaba apagado, un color lo "enciende".
    if (d.r || d.g || d.b) ledEncendido.value = true
  })

  on('spotify_autenticado', () => {
    spotifyAutenticado.value = true
    spotifyCargando.value = false
    enviar('spotify_estado')
  })
  on('spotify_error', (d) => {
    spotifyCargando.value = false
    agregarLog(`Error Spotify: ${d.error}`)
  })
  on('spotify_desconectado', () => {
    spotifyAutenticado.value = false
    spotifySincronizando.value = false
    cancionActual.value = ''
    artistaActual.value = ''
    portadaActual.value = ''
  })
  on('spotify_estado', (d) => {
    spotifyAutenticado.value = d.autenticado
    spotifySincronizando.value = d.sincronizando
    spotifyTieneCredenciales.value = d.tiene_credenciales
    spotifyModo.value = d.modo || 'portada'
    if (d.ritmo_activado !== undefined) ritmoActivado.value = d.ritmo_activado
    if (d.ritmo_disponible !== undefined) ritmoDisponible.value = d.ritmo_disponible
    if (d.flash_color) {
      flashColor.r = d.flash_color.r
      flashColor.g = d.flash_color.g
      flashColor.b = d.flash_color.b
    }
    if (d.flash_only !== undefined) flashOnly.value = d.flash_only
    if (d.modo_deteccion !== undefined) modoDeteccion.value = d.modo_deteccion
    if (d.ajustes) Object.assign(ajustes, d.ajustes)
    if (d.dispositivo) Object.assign(dispositivo, d.dispositivo)
    if (d.visual) Object.assign(visual, d.visual)
  })

  on('dispositivos', (d) => {
    escaneando.value = false
    dispositivos.value = d.lista || []
  })
  on('dispositivo', (d) => { if (d.dispositivo) Object.assign(dispositivo, d.dispositivo) })
  on('dispositivo_conectado', (d) => {
    if (d.dispositivo) Object.assign(dispositivo, d.dispositivo)
    if (d.ok) ledEncendido.value = true
    if (d.error) agregarLog(d.error)
  })
  on('sin_dispositivo', (d) => { agregarLog(d.error) })

  on('visual', (d) => {
    visual.activo = d.activo
    visual.url = d.url || ''
    visual.url_local = d.url_local || ''
    visual.ip = d.ip || ''
    visual.puerto = d.puerto || 0
  })

  on('beat', (d) => {
    beatActivo.value = true
    beatEnergia.value = d.energy != null ? d.energy : 0.6
    beatTick.value++
    clearTimeout(beatTimer)
    beatTimer = setTimeout(() => { beatActivo.value = false }, 150)
  })

  // Cada paso real de la transición de color (para el fondo/visuales).
  on('visual_color', (d) => {
    colorFondo.r = d.r
    colorFondo.g = d.g
    colorFondo.b = d.b
  })
  on('spotify_esperando', (d) => {
    spotifyCargando.value = true
    agregarLog(d.mensaje)
  })
  on('spotify_sincronizando', () => { spotifySincronizando.value = true })
  on('spotify_detenido', () => { spotifySincronizando.value = false })
  on('spotify_modo_cambiado', (d) => { spotifyModo.value = d.modo })
  on('spotify_info', (d) => {
    if (d.cancion) {
      cancionActual.value = d.cancion.nombre
      artistaActual.value = d.cancion.artista
      portadaActual.value = d.cancion.url_portada
    }
  })
  on('spotify_color', (d) => {
    colorActual.r = d.r
    colorActual.g = d.g
    colorActual.b = d.b
    cancionActual.value = d.cancion || ''
    artistaActual.value = d.artista || ''
    portadaActual.value = d.url_portada || ''
    fuenteColorActual.value = d.fuente || ''
    ledEncendido.value = true
    if (flashDeCancion.value) {
      enviar('ritmo_flash_color', { r: d.r, g: d.g, b: d.b })
    }
    cargarBiblioteca()
  })

  on('ritmo_activado', () => { ritmoActivado.value = true })
  on('ritmo_detenido', () => { ritmoActivado.value = false })
  on('ritmo_error', (d) => {
    ritmoActivado.value = false
    agregarLog(`Ritmo: ${d.error}`)
  })
  on('ritmo_flash_color_actualizado', (d) => {
    flashColor.r = d.r
    flashColor.g = d.g
    flashColor.b = d.b
  })
  on('ritmo_modo_deteccion_actualizado', (d) => { modoDeteccion.value = d.modo })
  on('ritmo_flash_only_actualizado', (d) => { flashOnly.value = d.flash_only })

  on('ajustes', (d) => { if (d.ajustes) Object.assign(ajustes, d.ajustes) })
  on('cache_lista', (d) => { biblioteca.value = d.canciones || [] })
  on('cache_editado', (d) => { if (d.canciones) biblioteca.value = d.canciones })
  on('cache_eliminado', (d) => { if (d.canciones) biblioteca.value = d.canciones })
  on('cache_limpiado', () => { biblioteca.value = [] })

  // Se devuelve como `reactive` para que los refs se desenvuelvan solos
  // al inyectarlo en las páginas (se usa como un pequeño store).
  return reactive({
    // estado
    conectadoLed, errorConexion, ledEncendido, colorActual, colorFondo, brilloActual, log,
    ritmoActivado, ritmoDisponible, flashColor, flashDeCancion, flashOnly, modoDeteccion,
    spotifyAutenticado, spotifySincronizando, spotifyCargando, spotifyTieneCredenciales,
    spotifyModo, cancionActual, artistaActual, portadaActual, fuenteColorActual,
    ajustes, biblioteca, mostrarFull,
    dispositivo, dispositivos, escaneando, visual, beatActivo, beatTick, beatEnergia,
    // constantes
    modosDeteccion, coloresFlash, slidersTransicion,
    // acciones
    aplicarColor, aplicarBrillo, togglePower, encender, apagar, probar, arcoiris,
    iniciarSesionSpotify, cerrarSesionSpotify, iniciarSincronizacion, detenerSincronizacion,
    cambiarModoSync, pedirEstadoSpotify,
    toggleRitmo, cambiarFlashColor, flashColorCancion, toggleFlashOnly, cambiarModoDeteccion,
    cambiarModoTransicion, cambiarDuracion, cargarBiblioteca, editarColorCancion, eliminarCancion,
    escanear, conectarDispositivo, iniciarVisual, detenerVisual,
    abrirVisualFull, cerrarVisualFull, setAjuste,
  })
}
