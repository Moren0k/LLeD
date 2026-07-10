<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="#1db954"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>
          Spotify
          <AyudaInfo>Conectá tu cuenta y tocá Sincronizar: la tira toma el color de cada canción. <b>Portada</b> usa el color del arte del álbum; <b>Humor</b> usa la energía y el ánimo del tema.</AyudaInfo>
        </h1>
        <p class="page-subtitle">Sincroniza el color con lo que estés escuchando.</p>
      </div>
    </div>

    <div v-if="!ctrl.spotifyTieneCredenciales" class="glass card">
      <p class="aviso">Configura <code>spotify_cliente_id</code> y <code>spotify_cliente_secreto</code> en <code>config.json</code>.</p>
    </div>

    <template v-else>
      <!-- Conexión -->
      <div class="glass card conexion">
        <div class="estado">
          <span class="dot" :class="{ on: ctrl.spotifyAutenticado }"></span>
          <span>{{ ctrl.spotifyAutenticado ? 'Conectado a Spotify' : 'Sin conectar' }}</span>
        </div>
        <button
          v-if="!ctrl.spotifyAutenticado"
          class="btn btn-tint"
          :disabled="ctrl.spotifyCargando"
          @click="ctrl.iniciarSesionSpotify"
        >{{ ctrl.spotifyCargando ? 'Conectando…' : 'Conectar' }}</button>
        <button v-else class="btn btn-glass" @click="ctrl.cerrarSesionSpotify">Desconectar</button>
      </div>

      <template v-if="ctrl.spotifyAutenticado">
        <!-- Canción actual -->
        <div class="glass card track" :style="glowActual">
          <div class="portada" :style="{ background: portadaBg }">
            <img v-if="ctrl.portadaActual" :src="ctrl.portadaActual" alt="" />
          </div>
          <div class="track-text">
            <span class="track-name">{{ ctrl.cancionActual || 'Ninguna canción' }}</span>
            <span class="track-artist">{{ ctrl.artistaActual }}</span>
            <span v-if="ctrl.fuenteColorActual" class="fuente" :class="ctrl.fuenteColorActual">{{ etiquetaFuente }}</span>
          </div>
        </div>

        <!-- Modo y sincronización -->
        <div class="glass card">
          <div class="fila">
            <span class="field-label">Modo</span>
            <div class="segmented">
              <button :class="{ active: ctrl.spotifyModo === 'portada' }" @click="ctrl.cambiarModoSync('portada')">Portada</button>
              <button :class="{ active: ctrl.spotifyModo === 'humor' }" @click="ctrl.cambiarModoSync('humor')">Humor</button>
            </div>
          </div>

          <button
            v-if="!ctrl.spotifySincronizando"
            class="btn btn-tint sync"
            :disabled="ctrl.spotifyCargando"
            @click="ctrl.iniciarSincronizacion(ctrl.spotifyModo)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Sincronizar
          </button>
          <button v-else class="btn btn-tint peligro sync" @click="ctrl.detenerSincronizacion">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
            Detener
          </button>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { inject, computed } from 'vue'
import AyudaInfo from './AyudaInfo.vue'

const ctrl = inject('ctrl')

const portadaBg = computed(() =>
  `rgb(${ctrl.colorActual.r}, ${ctrl.colorActual.g}, ${ctrl.colorActual.b})`
)
const glowActual = computed(() => ({
  boxShadow: `0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.14), 0 0 40px -12px rgb(${ctrl.colorActual.r},${ctrl.colorActual.g},${ctrl.colorActual.b})`,
}))
const etiquetaFuente = computed(() => ({
  cache: 'desde cache',
  auto: 'color automático',
  usuario: 'color tuyo',
}[ctrl.fuenteColorActual] || ''))
</script>

<style scoped>
.pagina { display: flex; flex-direction: column; gap: 16px; }
.card { padding: 18px; display: flex; flex-direction: column; gap: 14px; }

.aviso { font-size: 0.85rem; color: #ffb347; line-height: 1.5; }
.aviso code { background: rgba(0,0,0,0.3); padding: 1px 5px; border-radius: 5px; }

.conexion { flex-direction: row; align-items: center; justify-content: space-between; }
.estado { display: flex; align-items: center; gap: 10px; font-size: 0.9rem; font-weight: 500; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--text3); }
.dot.on { background: #1db954; box-shadow: 0 0 8px #1db954; }

.track { flex-direction: row; align-items: center; gap: 14px; }
.portada { width: 60px; height: 60px; border-radius: 14px; overflow: hidden; flex-shrink: 0; }
.portada img { width: 100%; height: 100%; object-fit: cover; }
.track-text { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.track-name { font-size: 1rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.track-artist { font-size: 0.82rem; color: var(--text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fuente {
  font-size: 0.66rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
  margin-top: 3px; width: fit-content; padding: 2px 7px; border-radius: 6px;
  color: var(--text2); background: rgba(255,255,255,0.08);
}
.fuente.usuario { color: var(--tint); background: rgba(125,75,255,0.16); }

.fila { display: flex; align-items: center; gap: 12px; }
.sync { width: 100%; justify-content: center; }
</style>
