<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          Biblioteca
          <AyudaInfo>Cada canción que suena guarda su color acá para que la próxima vez el cambio sea instantáneo. Tocá el cuadro de color para elegir otro; ese color queda como tuyo y no se reemplaza. La ✕ borra la canción del cache.</AyudaInfo>
        </h1>
        <p class="page-subtitle">El color de cada canción se guarda al sonar. Cambiá el que quieras: tu elección se respeta.</p>
      </div>
      <button class="btn btn-glass" @click="ctrl.cargarBiblioteca">Actualizar</button>
    </div>

    <div v-if="ctrl.biblioteca.length === 0" class="glass card vacio">
      <span>Todavía no hay canciones analizadas.</span>
      <span class="hint">Poné música y sincronizá Spotify para empezar a llenarla.</span>
    </div>

    <div v-else class="lista">
      <div v-for="c in ctrl.biblioteca" :key="c.cancion_id" class="glass item">
        <label class="color" :style="{ background: `rgb(${c.r},${c.g},${c.b})` }" title="Cambiar color">
          <input type="color" :value="rgbHex(c)" @change="editar(c.cancion_id, $event.target.value)" />
        </label>
        <div class="texto">
          <span class="nombre">{{ c.nombre || 'Sin título' }}</span>
          <span class="artista">{{ c.artista }}</span>
        </div>
        <span v-if="c.fuente === 'usuario'" class="badge">tuyo</span>
        <button class="del" title="Quitar" @click="ctrl.eliminarCancion(c.cancion_id)">✕</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import AyudaInfo from './AyudaInfo.vue'
const ctrl = inject('ctrl')

function rgbHex(c) {
  const h = (n) => Math.max(0, Math.min(255, n | 0)).toString(16).padStart(2, '0')
  return `#${h(c.r)}${h(c.g)}${h(c.b)}`
}
function editar(id, hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  ctrl.editarColorCancion(id, { r, g, b })
}
</script>

<style scoped>
/* Estilos propios de la página; el resto viene del sistema (styles.css). */
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }

.vacio { padding: 28px 18px; display: flex; flex-direction: column; gap: 6px; align-items: center; text-align: center; color: var(--text2); font-size: 0.9rem; }
.vacio .hint { font-size: 0.78rem; color: var(--text3); }

.lista { display: flex; flex-direction: column; gap: 10px; }
.item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; }

.color {
  position: relative; width: 38px; height: 38px; border-radius: 12px; flex-shrink: 0; cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.16);
}
.color input[type="color"] { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; border: none; padding: 0; }

.texto { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.nombre { font-size: 0.9rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.artista { font-size: 0.78rem; color: var(--text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.del {
  background: none; border: none; color: var(--text3); font-size: 0.9rem; cursor: pointer;
  padding: 5px 7px; border-radius: 8px; flex-shrink: 0; transition: all 0.15s;
}
.del:hover { color: var(--red); background: rgba(255, 91, 82, 0.14); }
</style>
