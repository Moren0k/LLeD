"""Servidor del visual remoto.

Expone en la red local:
  - HTTP (puerto 8770): una página con el fondo "liquid glass" a pantalla
    completa, sincronizado con el color del LED y con el modo ritmo.
  - WebSocket (puerto 8771): difunde en tiempo real color, beats y estado del
    ritmo a todas las pantallas conectadas.

Cualquier celular/PC/TV en la misma red abre http://<ip-lan>:8770 y ve el
mismo visual que la app.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import websockets
from websockets.exceptions import ConnectionClosed

PUERTO_HTTP = 8770
PUERTO_WS = 8771

from rutas import ruta_recurso

_MOTOR_JS = ruta_recurso("motor_visual.js")


def _leer_motor() -> str:
    try:
        with open(_MOTOR_JS, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def lan_ip() -> str:
    """Devuelve la IP LAN de esta máquina (o 127.0.0.1 si no hay red)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def _pagina_html() -> str:
    return (_HTML
            .replace("/*__MOTOR__*/", _leer_motor())
            .replace("__WS_PORT__", str(PUERTO_WS)))


class _HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return
        cuerpo = _pagina_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):  # silencia el log de acceso
        pass


class VisualHub:
    """Estado compartido y difusión a las pantallas del visual remoto."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._clientes: set = set()
        self.estado = {
            "r": 0, "g": 0, "b": 0, "ritmo": False,
            "cancion": "", "artista": "", "portada": "",
            "titulo": True, "titulo_escala": 1.0, "titulo_x": 0.5, "titulo_y": 0.85,
            "tipo": "aurora", "movimiento": True,
            # Carátula del álbum como visual.
            "portada_tarjeta": False, "portada_difuminado": True,
            "portada_x": 0.5, "portada_y": 0.42,
            # Letra sincronizada.
            "letra": "", "letra_sig": "",
            # Estado del timer (para el reloj flip / tarjeta en el remoto).
            "timer_on": False, "timer_progreso": 0.0, "timer_restante": 0.0,
            "timer_fondo_r": 10, "timer_fondo_g": 10, "timer_fondo_b": 30,
        }
        self._ws_server = None
        self._http_server: ThreadingHTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self.activo = False

    # ── Arranque / parada ─────────────────────────────────────────

    async def iniciar(self) -> dict:
        """Arranca los servidores (idempotente). Devuelve las URLs para compartir."""
        if self.activo:
            return self.info()
        self._loop = asyncio.get_running_loop()

        self._http_server = ThreadingHTTPServer(("0.0.0.0", PUERTO_HTTP), _HttpHandler)
        self._http_thread = threading.Thread(
            target=self._http_server.serve_forever, daemon=True
        )
        self._http_thread.start()

        self._ws_server = await websockets.serve(self._handler, "0.0.0.0", PUERTO_WS)
        self.activo = True
        return self.info()

    def detener(self) -> None:
        if self._http_server:
            self._http_server.shutdown()
            self._http_server = None
        if self._ws_server:
            self._ws_server.close()
            self._ws_server = None
        self.activo = False

    def info(self) -> dict:
        ip = lan_ip()
        return {
            "activo": self.activo,
            "url": f"http://{ip}:{PUERTO_HTTP}",
            "url_local": f"http://localhost:{PUERTO_HTTP}",
            "ip": ip,
            "puerto": PUERTO_HTTP,
        }

    # ── WebSocket ─────────────────────────────────────────────────

    async def _handler(self, ws):
        self._clientes.add(ws)
        try:
            await ws.send(json.dumps({"t": "estado", **self.estado}))
            async for _ in ws:
                pass  # las pantallas solo reciben
        except ConnectionClosed:
            pass
        finally:
            self._clientes.discard(ws)

    async def _broadcast(self, obj: dict) -> None:
        if not self._clientes:
            return
        muertos = []
        mensaje = json.dumps(obj)
        for ws in list(self._clientes):
            try:
                await ws.send(mensaje)
            except Exception:
                muertos.append(ws)
        for ws in muertos:
            self._clientes.discard(ws)

    def _emitir(self, obj: dict) -> None:
        """Programa una difusión en el loop, seguro desde cualquier hilo/tarea."""
        if not self.activo or self._loop is None or not self._clientes:
            return
        self._loop.call_soon_threadsafe(lambda: asyncio.create_task(self._broadcast(obj)))

    # ── API para el servidor de LEDs ──────────────────────────────

    def set_color(self, r: int, g: int, b: int) -> None:
        self.estado["r"], self.estado["g"], self.estado["b"] = int(r), int(g), int(b)
        self._emitir({"t": "color", "r": int(r), "g": int(g), "b": int(b)})

    def set_ritmo(self, activo: bool) -> None:
        self.estado["ritmo"] = bool(activo)
        self._emitir({"t": "ritmo", "on": bool(activo)})

    def pulse(self, energia: float) -> None:
        self._emitir({"t": "beat", "e": round(float(energia), 3)})

    def set_cancion(self, nombre: str, artista: str = "", portada: str = "") -> None:
        self.estado["cancion"] = nombre or ""
        self.estado["artista"] = artista or ""
        self.estado["portada"] = portada or ""
        self._emitir({
            "t": "cancion", "nombre": nombre or "", "artista": artista or "",
            "portada": portada or "",
        })

    def set_visual(self, tipo: str, movimiento: bool, portada: dict | None = None) -> None:
        self.estado["tipo"] = tipo
        self.estado["movimiento"] = bool(movimiento)
        if portada:
            for k in ("portada_difuminado", "portada_x", "portada_y"):
                if k in portada:
                    self.estado[k] = portada[k]
        self._emitir({
            "t": "visual", "tipo": tipo, "movimiento": bool(movimiento),
            "pd": self.estado["portada_difuminado"],
            "px": self.estado["portada_x"], "py": self.estado["portada_y"],
        })

    def set_titulo(self, cfg: dict) -> None:
        """cfg: {titulo, titulo_escala, titulo_x, titulo_y, portada_tarjeta}."""
        for k in ("titulo", "titulo_escala", "titulo_x", "titulo_y"):
            if k in cfg:
                self.estado[k] = cfg[k]
        if "portada_tarjeta" in cfg:
            self.estado["portada_tarjeta"] = bool(cfg["portada_tarjeta"])
        self._emitir({
            "t": "titulo",
            "on": self.estado["titulo"],
            "escala": self.estado["titulo_escala"],
            "x": self.estado["titulo_x"],
            "y": self.estado["titulo_y"],
            "portada_tarjeta": self.estado["portada_tarjeta"],
        })

    # ── Timer (reloj flip / tarjeta en el remoto) ─────────────────

    def set_timer_estado(self, on: bool) -> None:
        self.estado["timer_on"] = bool(on)
        self._emitir({"t": "timer_estado", "on": bool(on)})

    def set_timer_tick(self, progreso: float, restante: float) -> None:
        self.estado["timer_progreso"] = float(progreso)
        self.estado["timer_restante"] = float(restante)
        self._emitir({
            "t": "timer_tick",
            "p": round(float(progreso), 4),
            "restante": round(float(restante), 2),
        })

    def set_letra(self, actual: str, siguiente: str = "") -> None:
        self.estado["letra"] = actual or ""
        self.estado["letra_sig"] = siguiente or ""
        self._emitir({"t": "letra", "actual": actual or "", "siguiente": siguiente or ""})

    def set_timer_fondo(self, r: int, g: int, b: int) -> None:
        self.estado["timer_fondo_r"] = int(r)
        self.estado["timer_fondo_g"] = int(g)
        self.estado["timer_fondo_b"] = int(b)
        self._emitir({"t": "timer_fondo", "r": int(r), "g": int(g), "b": int(b)})


# Singleton de proceso.
hub = VisualHub()


_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>LLeD Visual</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{height:100%;width:100%;overflow:hidden;background:#05060a}
  #cv{position:fixed;inset:0;width:100%;height:100%;display:block}
  .estado{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom));transform:translateX(-50%);
    font-family:-apple-system,Segoe UI,sans-serif;font-size:12px;color:rgba(255,255,255,.35);
    letter-spacing:.05em;transition:opacity .4s;pointer-events:none;text-align:center}
  .oculto{opacity:0}
  .tarjeta{position:fixed;left:50%;top:85%;transform:translate(-50%,-50%);
    font-family:-apple-system,Segoe UI,sans-serif;text-align:center;
    padding:min(3vw,18px) min(5vw,30px);border-radius:22px;pointer-events:none;max-width:88vw;
    background:rgba(255,255,255,.07);backdrop-filter:blur(24px) saturate(180%);
    -webkit-backdrop-filter:blur(24px) saturate(180%);
    border:1px solid rgba(255,255,255,.14);
    box-shadow:0 8px 32px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.14);
    transition:opacity .4s}
  .t-nombre{color:#fff;font-weight:700;line-height:1.15;
    font-size:calc(clamp(20px,5.2vw,40px) * var(--esc,1));
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:84vw}
  .t-artista{color:rgba(255,255,255,.62);font-weight:500;margin-top:4px;
    font-size:calc(clamp(13px,3vw,20px) * var(--esc,1))}
  .t-portada{width:calc(clamp(64px,18vw,150px) * var(--esc,1));height:calc(clamp(64px,18vw,150px) * var(--esc,1));
    border-radius:16px;object-fit:cover;margin:0 auto 12px;display:none;
    box-shadow:0 8px 24px rgba(0,0,0,.45)}
  .t-portada.ver{display:block}
  .tarjeta.oculto{opacity:0}
  .letra{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);text-align:center;
    width:min(92vw,900px);pointer-events:none;transition:opacity .3s;
    font-family:-apple-system,Segoe UI,sans-serif}
  .letra-actual{color:#fff;font-weight:800;line-height:1.2;
    font-size:clamp(24px,5.5vw,52px);text-shadow:0 2px 18px rgba(0,0,0,.6)}
  .letra-sig{color:rgba(255,255,255,.5);font-weight:600;margin-top:10px;
    font-size:clamp(15px,3vw,26px)}
  .letra.oculto{opacity:0}
</style>
</head>
<body>
  <canvas id="cv"></canvas>
  <div class="letra oculto" id="letra">
    <div class="letra-actual" id="letraActual"></div>
    <div class="letra-sig" id="letraSig"></div>
  </div>
  <div class="tarjeta oculto" id="tarjeta">
    <img class="t-portada" id="tportada" alt="">
    <div class="t-nombre" id="tnombre"></div>
    <div class="t-artista" id="tartista"></div>
  </div>
  <div class="estado" id="estado">conectando…</div>
<script>/*__MOTOR__*/</script>
<script>
(function(){
  var estado=document.getElementById('estado');
  var letra=document.getElementById('letra');
  var letraActual=document.getElementById('letraActual');
  var letraSig=document.getElementById('letraSig');
  var tarjeta=document.getElementById('tarjeta');
  var tnombre=document.getElementById('tnombre');
  var tartista=document.getElementById('tartista');
  var tportada=document.getElementById('tportada');
  var ocultarT=null, mostrarTitulo=true;
  var cancionNombre='', cancionArtista='', cancionPortada='', portadaTarjeta=false;
  var timerOn=false, timerRestante=0;
  var vis=window.CrearVisual(document.getElementById('cv'),{});

  function fmtTiempo(t){
    t=Math.max(0,Math.floor(t));
    var h=Math.floor(t/3600), m=Math.floor((t%3600)/60), s=t%60;
    var mm=(m<10?'0':'')+m, ss=(s<10?'0':'')+s;
    return h>0 ? h+':'+mm+':'+ss : mm+':'+ss;
  }
  function aplicarCancion(nombre,artista,portada){
    cancionNombre=nombre||''; cancionArtista=artista||'';
    if(portada!==undefined){ cancionPortada=portada||''; if(vis.setPortada) vis.setPortada(cancionPortada); }
    refrescarTarjeta();
  }
  function refrescarTarjeta(){
    if(timerOn){
      tportada.classList.remove('ver');
      tnombre.textContent='TIMER';
      tartista.textContent=fmtTiempo(timerRestante)+' restantes';
      tarjeta.classList.toggle('oculto',!mostrarTitulo);
      return;
    }
    tnombre.textContent=cancionNombre;
    tartista.textContent=cancionArtista;
    var verPortada=portadaTarjeta && cancionPortada.length>0;
    if(verPortada && tportada.getAttribute('src')!==cancionPortada) tportada.setAttribute('src',cancionPortada);
    tportada.classList.toggle('ver',verPortada);
    var hay=cancionNombre.length>0 || verPortada;
    tarjeta.classList.toggle('oculto',!(mostrarTitulo&&hay));
  }
  function aplicarTitulo(on,esc,x,y,pt){
    mostrarTitulo=!!on;
    if(pt!==undefined) portadaTarjeta=!!pt;
    tarjeta.style.setProperty('--esc',esc||1);
    tarjeta.style.left=((x!=null?x:0.5)*100)+'%';
    tarjeta.style.top=((y!=null?y:0.85)*100)+'%';
    refrescarTarjeta();
  }
  function aplicarLetra(actual,siguiente){
    letraActual.textContent=actual||'';
    letraSig.textContent=siguiente||'';
    letra.classList.toggle('oculto',!(actual&&actual.length));
  }
  function marcaEstado(txt){
    estado.textContent=txt; estado.classList.remove('oculto');
    clearTimeout(ocultarT);
    ocultarT=setTimeout(function(){estado.classList.add('oculto')},2500);
  }

  function conectar(){
    var ws=new WebSocket('ws://'+location.hostname+':__WS_PORT__');
    ws.onopen=function(){marcaEstado('sincronizado')};
    ws.onclose=function(){marcaEstado('reconectando…');setTimeout(conectar,1500)};
    ws.onmessage=function(ev){
      var d; try{d=JSON.parse(ev.data)}catch(e){return}
      if(d.t==='color'){vis.setColor(d.r,d.g,d.b)}
      else if(d.t==='beat'){vis.beat(d.e)}
      else if(d.t==='ritmo'){vis.setRitmo(d.on)}
      else if(d.t==='visual'){vis.setTipo(d.tipo);vis.setMovimiento(d.movimiento);if(vis.setPortadaCfg)vis.setPortadaCfg(d.pd,d.px,d.py)}
      else if(d.t==='cancion'){aplicarCancion(d.nombre,d.artista,d.portada)}
      else if(d.t==='titulo'){aplicarTitulo(d.on,d.escala,d.x,d.y,d.portada_tarjeta)}
      else if(d.t==='timer_estado'){timerOn=!!d.on;refrescarTarjeta()}
      else if(d.t==='timer_tick'){timerRestante=d.restante;vis.setTimerProgreso(d.p,d.restante);if(timerOn)refrescarTarjeta()}
      else if(d.t==='timer_fondo'){vis.setTimerFondoColor(d.r,d.g,d.b)}
      else if(d.t==='letra'){aplicarLetra(d.actual,d.siguiente)}
      else if(d.t==='estado'){
        vis.setColor(d.r,d.g,d.b);vis.setRitmo(d.ritmo);
        vis.setTipo(d.tipo);vis.setMovimiento(d.movimiento);
        if(vis.setPortadaCfg)vis.setPortadaCfg(d.portada_difuminado,d.portada_x,d.portada_y);
        vis.setTimerFondoColor(d.timer_fondo_r,d.timer_fondo_g,d.timer_fondo_b);
        vis.setTimerProgreso(d.timer_progreso,d.timer_restante);
        timerRestante=d.timer_restante; timerOn=!!d.timer_on;
        aplicarTitulo(d.titulo,d.titulo_escala,d.titulo_x,d.titulo_y,d.portada_tarjeta);
        aplicarCancion(d.cancion,d.artista,d.portada);
        aplicarLetra(d.letra,d.letra_sig);
      }
    };
  }
  conectar();
})();
</script>
</body>
</html>
"""
