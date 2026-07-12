<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          Ajustes
          <AyudaInfo>Elegí a qué luz Bluetooth conectarte y cómo cambian los colores entre canciones.</AyudaInfo>
        </h1>
        <p class="page-subtitle">Dispositivo y comportamiento de los colores.</p>
      </div>
    </div>

    <!-- Dispositivo LED -->
    <div class="glass card">
      <div class="fila-disp">
        <div class="estado-disp">
          <span class="dot" :class="{ on: ctrl.dispositivo.conectado }"></span>
          <div class="disp-text">
            <span class="disp-titulo">Dispositivo LED <AyudaInfo>Tocá Escanear para ver las luces Bluetooth cercanas y elegí la tuya. Funciona con tiras LED Bluetooth compatibles.</AyudaInfo></span>
            <span class="disp-sub">{{ ctrl.dispositivo.conectado ? ctrl.dispositivo.direccion : 'Sin conectar' }}</span>
          </div>
        </div>
        <button class="btn btn-glass" :disabled="ctrl.escaneando" @click="ctrl.escanear">
          {{ ctrl.escaneando ? 'Buscando…' : 'Escanear' }}
        </button>
      </div>

      <div v-if="ctrl.dispositivos.length" class="lista-disp">
        <button
          v-for="d in ctrl.dispositivos"
          :key="d.direccion"
          class="disp-item"
          :class="{ actual: d.direccion === ctrl.dispositivo.direccion }"
          @click="ctrl.conectarDispositivo(d.direccion)"
        >
          <span class="disp-nombre">
            {{ d.nombre }}
            <span v-if="d.probable_led" class="pill">LED</span>
          </span>
          <span class="disp-mac">{{ d.direccion }}</span>
        </button>
      </div>
      <p v-else-if="!ctrl.escaneando" class="nota">Escaneá para ver las luces Bluetooth cercanas y conectá la que quieras.</p>
    </div>

    <div class="glass card">
      <div class="fila">
        <span class="field-label">Transición</span>
        <AyudaInfo><b>Gradiente</b>: al cambiar de canción baja el brillo mientras analiza y sube con el color nuevo (o funde directo si ya lo tenía guardado). <b>Brusco</b>: cambia al instante.</AyudaInfo>
        <div class="segmented">
          <button :class="{ active: ctrl.ajustes.modo_transicion === 'gradiente' }" @click="ctrl.cambiarModoTransicion('gradiente')">Gradiente</button>
          <button :class="{ active: ctrl.ajustes.modo_transicion === 'brusco' }" @click="ctrl.cambiarModoTransicion('brusco')">Brusco</button>
        </div>
      </div>
      <p class="nota" v-if="ctrl.ajustes.modo_transicion === 'gradiente'">
        Al detectar una canción nueva el LED baja el brillo mientras se analiza y vuelve a subir con el color nuevo. Si el color ya está guardado, el cambio es un fundido directo de un color a otro.
      </p>
      <p class="nota" v-else>Los cambios de color son instantáneos, sin fundidos.</p>
    </div>

    <div class="glass card" v-if="ctrl.ajustes.modo_transicion === 'gradiente'">
      <span class="field-label bloque">Duración de los fundidos</span>
      <div class="fila" v-for="s in ctrl.slidersTransicion" :key="s.clave">
        <span class="mini-label">{{ s.label }}</span>
        <input
          class="slider"
          type="range" min="0" max="2" step="0.05"
          :value="ctrl.ajustes[s.clave]"
          @input="ctrl.cambiarDuracion(s.clave, $event.target.value)"
        />
        <span class="valor">{{ Number(ctrl.ajustes[s.clave]).toFixed(2) }}s</span>
      </div>
    </div>

    <!-- Reinicio -->
    <div class="glass card">
      <div class="fila-titulo">
        <span class="sub">Reinicio</span>
        <AyudaInfo>Volvé todo a los valores de fábrica o borrá el historial de colores por canción (biblioteca). No afecta tu dispositivo ni la sesión de Spotify.</AyudaInfo>
      </div>
      <div class="acciones">
        <button class="btn btn-glass" @click="restablecer">Restablecer ajustes</button>
        <button class="btn btn-glass peligro" @click="borrar">Borrar historial de colores</button>
      </div>
      <p v-if="msg" class="ok-msg">{{ msg }}</p>
    </div>
  </div>
</template>

<script setup>
import { inject, ref } from 'vue'
import AyudaInfo from './AyudaInfo.vue'
const ctrl = inject('ctrl')
const msg = ref('')

function aviso(t) { msg.value = t; setTimeout(() => { msg.value = '' }, 2500) }

function restablecer() {
  if (confirm('¿Restablecer todos los ajustes a los valores por defecto?')) {
    ctrl.resetearAjustes()
    aviso('Ajustes restablecidos.')
  }
}
function borrar() {
  if (confirm('¿Borrar el historial de colores de todas las canciones? Esto no se puede deshacer.')) {
    ctrl.borrarHistorial()
    aviso('Historial de colores borrado.')
  }
}
</script>

<style scoped>
.pagina { display: flex; flex-direction: column; gap: 16px; }
.card { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.bloque { display: block; }
.fila { display: flex; align-items: center; gap: 12px; }
.mini-label { font-size: 0.8rem; color: var(--text2); min-width: 78px; }
.valor { font-size: 0.82rem; font-weight: 600; color: var(--text2); min-width: 44px; text-align: right; }
.nota { font-size: 0.78rem; color: var(--text3); line-height: 1.55; }

/* Reinicio */
.fila-titulo { display: flex; align-items: center; gap: 8px; }
.sub { font-size: 0.95rem; font-weight: 600; }
.acciones { display: flex; gap: 8px; flex-wrap: wrap; }
.acciones .btn { flex: 1; min-width: 150px; }
.btn-glass.peligro { color: var(--red); }
.btn-glass.peligro:hover { background: rgba(255, 91, 82, 0.14); border-color: rgba(255, 91, 82, 0.4); }
.ok-msg { font-size: 0.78rem; color: var(--green); }

/* Dispositivo */
.fila-disp { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.estado-disp { display: flex; align-items: center; gap: 10px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--red); flex-shrink: 0; }
.dot.on { background: var(--green); box-shadow: 0 0 8px var(--green); }
.disp-text { display: flex; flex-direction: column; }
.disp-titulo { font-size: 0.9rem; font-weight: 600; }
.disp-sub { font-size: 0.75rem; color: var(--text2); font-family: 'SF Mono', 'Consolas', monospace; }

.lista-disp { display: flex; flex-direction: column; gap: 6px; max-height: 220px; overflow-y: auto; }
.disp-item {
  display: flex; flex-direction: column; gap: 2px; text-align: left;
  background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border);
  border-radius: 12px; padding: 10px 12px; cursor: pointer; font-family: inherit;
  transition: border-color 0.15s, background 0.15s;
}
.disp-item:hover { border-color: var(--glass-border-strong); background: rgba(255,255,255,0.06); }
.disp-item.actual { border-color: var(--tint); }
.disp-nombre { font-size: 0.86rem; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 8px; }
.disp-mac { font-size: 0.72rem; color: var(--text3); font-family: 'SF Mono', 'Consolas', monospace; }
.pill { font-size: 0.6rem; font-weight: 700; color: var(--tint); background: rgba(125,75,255,0.16); padding: 1px 6px; border-radius: 6px; }
</style>
