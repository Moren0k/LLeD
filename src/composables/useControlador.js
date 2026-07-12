import { ref, reactive, computed, watch } from 'vue'
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
  const spotifyAuthUrl = ref('')
  const cancionActual = ref('')
  const artistaActual = ref('')
  const portadaActual = ref('')
  const fuenteColorActual = ref('')

  // ── Letra sincronizada ──
  const letraActual = ref('')
  const letraSiguiente = ref('')
  const letraDisponible = ref(true)

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
    visual_tipo: 'aurora',
    visual_movimiento: true,
    visual_portada: false,
    visual_portada_difuminado: true,
    visual_portada_x: 0.5,
    visual_portada_y: 0.42,
    visual_letra: false,
    visual_letra_x: 0.5,
    visual_letra_y: 0.68,
    visual_letra_escala: 1.0,
    ambilight_fps: 15,
    ambilight_suavizado: 0.6,
    ambilight_saturacion: 1.4,
    ambilight_intensidad_min: 0.08,
    ambilight_intensidad_max: 1.0,
    ambilight_peso_bordes: 0.5,
    ambilight_peso_dominante: 0.3,
    ambilight_reactivo_audio: true,
    ambilight_sensibilidad_audio: 0.6,
    ambilight_monitor: 0,
  })
  const biblioteca = ref([])
  const mostrarFull = ref(false)

  // ── Preferencias de interfaz (se guardan localmente y se restauran al abrir) ──
  const cerrarComportamiento = ref(localStorage.getItem('lled_cerrar') || 'salir') // 'salir' | 'minimizar'
  const fondoTipo = ref(localStorage.getItem('lled_fondo_tipo') || 'visuales')     // 'visuales' | 'solido'
  const fondoColor = reactive(_cargarFondoColor())

  function _cargarFondoColor() {
    try {
      const v = JSON.parse(localStorage.getItem('lled_fondo_color'))
      if (v && Number.isFinite(v.r) && Number.isFinite(v.g) && Number.isFinite(v.b)) return v
    } catch (e) { /* usa el valor por defecto */ }
    return { r: 10, g: 12, b: 22 }
  }

  function setCerrarComportamiento(modo) {
    cerrarComportamiento.value = modo
    localStorage.setItem('lled_cerrar', modo)
    if (window.electronAPI && window.electronAPI.setCerrarModo) {
      window.electronAPI.setCerrarModo(modo)
    }
  }
  function setFondoTipo(tipo) {
    fondoTipo.value = tipo
    localStorage.setItem('lled_fondo_tipo', tipo)
  }
  function setFondoColor({ r, g, b }) {
    fondoColor.r = r; fondoColor.g = g; fondoColor.b = b
    localStorage.setItem('lled_fondo_color', JSON.stringify({ r, g, b }))
  }

  // Informa al proceso principal la preferencia de cierre al arrancar.
  if (window.electronAPI && window.electronAPI.setCerrarModo) {
    window.electronAPI.setCerrarModo(cerrarComportamiento.value)
  }

  // ── Timer ──
  // El timer solo cuenta el tiempo y dispara la alerta LED. QUÉ visual se ve
  // (Reloj / Tarjeta) se elige en la sección Visuales, no acá.
  const timer = reactive({
    activo: false,
    pausado: false,
    tiempoTotal: 0,
    tiempoRestante: 0,
    progreso: 0,
    colorAlerta: { r: 255, g: 0, b: 0 },
    accionAlerta: 'blink',
    // Visual del timer (se controla desde la página Visuales):
    modoVisual: 'splitflap',        // 'splitflap' | 'colorcard'
    usarVisual: true,               // false = mostrar el visual normal durante el timer
    colorFondoVisual: { r: 10, g: 10, b: 30 },
  })

  const coloresAlerta = [
    { nombre: 'Blanco', r: 255, g: 255, b: 255 },
    { nombre: 'Rojo', r: 255, g: 0, b: 0 },
    { nombre: 'Naranja', r: 255, g: 128, b: 0 },
    { nombre: 'Azul', r: 0, g: 100, b: 255 },
    { nombre: 'Morado', r: 150, g: 0, b: 255 },
  ]

  const accionesAlerta = [
    { id: 'flash', label: 'Destello' },
    { id: 'blink', label: 'Titileo' },
    { id: 'fade', label: 'Fundido' },
  ]

  // Visuales exclusivos del timer (aparecen en la grilla de Visuales solo
  // cuando hay un timer activo).
  const visualesTimer = [
    { id: 'splitflap', label: 'Reloj', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/></svg>' },
    { id: 'colorcard', label: 'Tarjeta', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 12h10"/></svg>' },
  ]

  const fondosCard = [
    { nombre: 'Negro', r: 10, g: 10, b: 30 },
    { nombre: 'Gris', r: 40, g: 42, b: 50 },
    { nombre: 'Azul', r: 15, g: 30, b: 80 },
    { nombre: 'Verde', r: 10, g: 50, b: 20 },
    { nombre: 'Granate', r: 60, g: 15, b: 15 },
    { nombre: 'Violeta', r: 40, g: 10, b: 60 },
  ]

  // ── Efectos de ambiente (para el silencio) ──
  const ambienteActivado = ref(false)
  const ambienteEfecto = ref('respiracion')
  const efectosAmbiente = [
    { id: 'respiracion', label: 'Respiración', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12c3-7 15-7 18 0"/><path d="M3 12c3 7 15 7 18 0"/></svg>' },
    { id: 'pulso', label: 'Pulso', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h5l2-6 4 12 2-6h7"/></svg>' },
    { id: 'vela', label: 'Vela', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c2 2.5 3 4 3 6a3 3 0 0 1-6 0c0-2 1-3.5 3-6z"/><path d="M12 12v6"/><path d="M8 21h8"/></svg>' },
    { id: 'fuego', label: 'Fuego', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c3 4 5 6 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 .5 1 1.5 1.5 2 1 0-2-1-4 1-7z"/></svg>' },
    { id: 'ciclo', label: 'Ciclo de color', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg>' },
  ]
  function iniciarAmbiente(efecto) { enviar('ambiente_iniciar', { efecto }) }
  function cambiarEfectoAmbiente(efecto) { enviar('ambiente_efecto', { efecto }) }
  function detenerAmbiente() { enviar('ambiente_detener') }
  function toggleEfectoAmbiente(efecto) {
    if (ambienteActivado.value) {
      if (ambienteEfecto.value === efecto) detenerAmbiente()
      else cambiarEfectoAmbiente(efecto)
    } else {
      iniciarAmbiente(efecto)
    }
  }

  // ── Cine Mode (ambilight) ──
  const ambilightActivado = ref(false)
  const ambilightDisponible = ref(false)
  const monitores = ref([])

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
  let debounceTemp = null
  function aplicarTemperatura(calidez) {
    clearTimeout(debounceTemp)
    debounceTemp = setTimeout(() => enviar('temperatura', { calidez }), 60)
  }

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
  function toggleLetra(v) {
    setAjuste('visual_letra', v, true)
    enviar(v ? 'letra_iniciar' : 'letra_detener')
    if (!v) { letraActual.value = ''; letraSiguiente.value = '' }
  }

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
  function borrarHistorial() { enviar('cache_limpiar') }
  function resetearAjustes() { enviar('ajustes_reset') }

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

  // ── Cine Mode ──
  function toggleAmbilight() {
    enviar(ambilightActivado.value ? 'ambilight_detener' : 'ambilight_iniciar')
  }
  function cargarMonitores() { enviar('ambilight_monitores') }
  let debounceAmbi = null
  function setAmbilight(clave, valor, inmediato = false) {
    ajustes[clave] = valor
    const enviarlo = () => enviar('ambilight_config', { cambios: { [clave]: valor } })
    clearTimeout(debounceAmbi)
    if (inmediato) enviarlo()
    else debounceAmbi = setTimeout(enviarlo, 150)
  }

  // ── Acciones Timer ──
  function cfgVisualTimer() {
    return {
      tipo: timer.modoVisual,
      usar: timer.usarVisual,
      fondo: { ...timer.colorFondoVisual },
    }
  }
  function timerIniciar(tiempo, color, accion) {
    enviar('timer_iniciar', { tiempo, color, accion, visual: cfgVisualTimer() })
  }
  function timerPausar() { enviar('timer_pausar') }
  function timerReanudar() { enviar('timer_reanudar') }
  function timerDetener() { enviar('timer_detener') }
  // Se llama al cambiar el visual del timer desde la página Visuales (en vivo).
  function timerVisual() {
    if (timer.activo) enviar('timer_visual', cfgVisualTimer())
  }

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
    spotifyAuthUrl.value = ''
    enviar('spotify_estado')
  })
  on('spotify_error', (d) => {
    spotifyCargando.value = false
    spotifyAuthUrl.value = ''
    agregarLog(`Error Spotify: ${d.error}`)
  })
  on('spotify_desconectado', () => {
    spotifyAutenticado.value = false
    spotifySincronizando.value = false
    spotifyAuthUrl.value = ''
    cancionActual.value = ''
    artistaActual.value = ''
    portadaActual.value = ''
    letraActual.value = ''
    letraSiguiente.value = ''
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
    if (d.ambilight_activado !== undefined) ambilightActivado.value = d.ambilight_activado
    if (d.ambilight_disponible !== undefined) ambilightDisponible.value = d.ambilight_disponible
    if (d.ambiente_activado !== undefined) ambienteActivado.value = d.ambiente_activado
    if (d.ambiente_efecto) ambienteEfecto.value = d.ambiente_efecto
  })

  on('letra', (d) => { letraActual.value = d.actual || ''; letraSiguiente.value = d.siguiente || '' })
  on('letra_estado', (d) => { letraDisponible.value = !!d.tiene })

  on('ambiente_iniciado', (d) => { ambienteActivado.value = true; if (d.efecto) ambienteEfecto.value = d.efecto })
  on('ambiente_detenido', () => { ambienteActivado.value = false })
  on('ambiente_efecto_cambiado', (d) => { if (d.efecto) ambienteEfecto.value = d.efecto })

  on('ambilight_activado', () => { ambilightActivado.value = true })
  on('ambilight_detenido', () => { ambilightActivado.value = false })
  on('ambilight_error', (d) => {
    ambilightActivado.value = false
    agregarLog(`Cine Mode: ${d.error}`)
  })
  on('ambilight_monitores', (d) => { monitores.value = d.monitores || [] })
  on('ambilight_color', (d) => {
    colorFondo.r = d.r
    colorFondo.g = d.g
    colorFondo.b = d.b
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

  // ── Handlers Timer ──
  on('timer_iniciado', (d) => {
    timer.activo = true
    timer.pausado = false
    timer.tiempoTotal = d.tiempo
    timer.tiempoRestante = d.tiempo
    timer.progreso = 0
    // Al arrancar, el visual del timer se activa automáticamente en Visuales.
    timer.usarVisual = true
  })
  on('timer_tick', (d) => {
    timer.tiempoRestante = d.restante
    timer.progreso = d.progreso
  })
  on('timer_pausado', () => { timer.pausado = true })
  on('timer_reanudado', () => { timer.pausado = false })
  on('timer_completado', () => {
    timer.activo = false
    timer.pausado = false
    timer.tiempoRestante = 0
    timer.progreso = 1
  })
  on('timer_detenido', () => {
    timer.activo = false
    timer.pausado = false
    timer.tiempoRestante = 0
    timer.progreso = 0
  })

  on('spotify_esperando', (d) => {
    spotifyCargando.value = true
    spotifyAuthUrl.value = d.url || ''
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

  // ── Integración con la bandeja del sistema (Electron) ──
  // El menú de la bandeja refleja el estado y dispara acciones sobre la app.
  const modoActual = computed(() => {
    if (ambilightActivado.value) return 'Cine'
    if (ritmoActivado.value) return 'Ritmo'
    if (spotifySincronizando.value) return 'Spotify'
    if (!ledEncendido.value) return 'Apagado'
    return 'Color manual'
  })

  if (window.electronAPI && window.electronAPI.actualizarEstado) {
    const api = window.electronAPI
    const empujarEstado = () => api.actualizarEstado({
      ledEncendido: ledEncendido.value,
      ritmoActivado: ritmoActivado.value,
      ambilightActivado: ambilightActivado.value,
      visualActivo: visual.activo,
      visualUrl: visual.url,
      modo: modoActual.value,
    })
    watch(
      [ledEncendido, ritmoActivado, ambilightActivado, () => visual.activo, () => visual.url, modoActual],
      empujarEstado,
      { immediate: true },
    )

    // Copia la dirección del visual al activarlo desde la bandeja.
    let copiarUrlAlActivar = false
    api.onAccionBandeja((accion) => {
      if (accion === 'power') togglePower()
      else if (accion === 'ritmo') toggleRitmo()
      else if (accion === 'cine') toggleAmbilight()
      else if (accion === 'fullscreen') abrirVisualFull()
      else if (accion === 'visual') {
        if (visual.activo) { detenerVisual() }
        else { copiarUrlAlActivar = true; iniciarVisual() }
      } else if (accion.indexOf('timer:') === 0) {
        const seg = parseInt(accion.slice(6), 10)
        if (seg > 0) timerIniciar(seg, { ...timer.colorAlerta }, timer.accionAlerta)
      }
    })
    watch(() => visual.url, (url) => {
      if (copiarUrlAlActivar && visual.activo && url) {
        api.copiarTexto(url)
        copiarUrlAlActivar = false
      }
    })
  }

  // Se devuelve como `reactive` para que los refs se desenvuelvan solos
  // al inyectarlo en las páginas (se usa como un pequeño store).
  return reactive({
    // estado
    conectadoLed, errorConexion, ledEncendido, colorActual, colorFondo, brilloActual, log,
    ritmoActivado, ritmoDisponible, flashColor, flashDeCancion, flashOnly, modoDeteccion,
    spotifyAutenticado, spotifySincronizando, spotifyCargando, spotifyTieneCredenciales,
    spotifyModo, spotifyAuthUrl, cancionActual, artistaActual, portadaActual, fuenteColorActual,
    letraActual, letraSiguiente, letraDisponible,
    ajustes, biblioteca, mostrarFull,
    cerrarComportamiento, fondoTipo, fondoColor,
    dispositivo, dispositivos, escaneando, visual, beatActivo, beatTick, beatEnergia,
    ambilightActivado, ambilightDisponible, monitores,
    ambienteActivado, ambienteEfecto, efectosAmbiente,
    timer,
    // constantes
    modosDeteccion, coloresFlash, slidersTransicion,
    coloresAlerta, accionesAlerta, visualesTimer, fondosCard,
    // acciones
    aplicarColor, aplicarBrillo, togglePower, encender, apagar, probar, arcoiris, aplicarTemperatura,
    iniciarSesionSpotify, cerrarSesionSpotify, iniciarSincronizacion, detenerSincronizacion,
    cambiarModoSync, pedirEstadoSpotify, toggleLetra,
    toggleRitmo, cambiarFlashColor, flashColorCancion, toggleFlashOnly, cambiarModoDeteccion,
    cambiarModoTransicion, cambiarDuracion, cargarBiblioteca, editarColorCancion, eliminarCancion,
    borrarHistorial, resetearAjustes,
    escanear, conectarDispositivo, iniciarVisual, detenerVisual,
    abrirVisualFull, cerrarVisualFull, setAjuste,
    toggleAmbilight, cargarMonitores, setAmbilight,
    iniciarAmbiente, cambiarEfectoAmbiente, detenerAmbiente, toggleEfectoAmbiente,
    timerIniciar, timerPausar, timerReanudar, timerDetener, timerVisual,
    setCerrarComportamiento, setFondoTipo, setFondoColor,
  })
}
