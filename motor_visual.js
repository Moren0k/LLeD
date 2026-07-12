/*
 * Motor de visuales en canvas para LLeD.
 * Sin dependencias ni módulos: define window.CrearVisual para poder usarse
 * igual desde la app (Vite) y desde la página remota (script inline).
 *
 * window.CrearVisual(canvas, opciones) -> {
 *   setColor(r,g,b), setTipo(nombre), setMovimiento(bool),
 *   setRitmo(bool), beat(energia), destruir()
 * }
 *
 * Tipos: "aurora" (nubes de luz que se desplazan), "orbes" (bolitas que se
 * mueven y rebotan), "ondas" (ondas que recorren la pantalla).
 */
(function () {
  function mezcla(a, x) { return Math.round(a * 0.55 + x * 0.45); }

  window.CrearVisual = function (canvas, opciones) {
    var ctx = canvas.getContext('2d');
    var estado = {
      r: 255, g: 0, b: 0,
      tipo: 'aurora', movimiento: true, ritmo: false,
      timerProgreso: 0, timerRestante: 0,
      timerFondoColor: { r: 10, g: 10, b: 30 },
    };
    Object.assign(estado, opciones || {});

    var W = 0, H = 0, dpr = 1;
    var pulso = 0;            // 0..1, sube en cada beat y decae
    var t = 0;               // tiempo acumulado
    var raf = null, ultimo = 0;
    var orbes = [], ondasFase = [];
    // Estado de la animación split-flap (por dígito visible).
    var flapShown = null, flapFrom = [], flapT = [];

    function c1(a) { return 'rgba(' + estado.r + ',' + estado.g + ',' + estado.b + ',' + a + ')'; }
    function c2(a) {
      var r = mezcla(estado.r, 125), g = mezcla(estado.g, 75), b = mezcla(estado.b, 255);
      return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
    }

    function resize() {
      dpr = window.devicePixelRatio || 1;
      W = canvas.clientWidth || canvas.parentNode.clientWidth || window.innerWidth;
      H = canvas.clientHeight || canvas.parentNode.clientHeight || window.innerHeight;
      canvas.width = Math.max(1, Math.floor(W * dpr));
      canvas.height = Math.max(1, Math.floor(H * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      initOrbes();
    }

    function initOrbes() {
      orbes = [];
      var n = Math.max(6, Math.min(16, Math.round((W * H) / 55000)));
      for (var i = 0; i < n; i++) {
        orbes.push({
          x: Math.random() * W, y: Math.random() * H,
          vx: (Math.random() - 0.5) * 60, vy: (Math.random() - 0.5) * 60,
          r: 12 + Math.random() * 46, fase: Math.random() * 6.28,
        });
      }
      ondasFase = [0, 1.6, 3.1, 4.7];
    }

    // ── Render por tipo ──────────────────────────────────────────
    function fondo() {
      var g = ctx.createRadialGradient(W / 2, 0, 0, W / 2, 0, Math.max(W, H));
      g.addColorStop(0, '#12131a');
      g.addColorStop(1, '#05060a');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);
    }

    function drawAurora(dt) {
      fondo();
      ctx.globalCompositeOperation = 'lighter';
      var nubes = [
        { ax: 0.22, ay: 0.18, r: 0.55, sp: 0.06, col: c1 },
        { ax: 0.80, ay: 0.30, r: 0.50, sp: 0.05, col: c2 },
        { ax: 0.55, ay: 0.85, r: 0.48, sp: 0.07, col: c1 },
      ];
      for (var i = 0; i < nubes.length; i++) {
        var n = nubes[i];
        var mx, my;
        if (estado.movimiento) {
          mx = (n.ax + 0.28 * Math.sin(t * n.sp + i)) * W;
          my = (n.ay + 0.24 * Math.cos(t * n.sp * 1.3 + i * 2)) * H;
        } else {
          mx = (n.ax + 0.03 * Math.sin(t * 0.4 + i)) * W;
          my = (n.ay + 0.03 * Math.cos(t * 0.4 + i)) * H;
        }
        var rad = n.r * Math.min(W, H) * (0.85 + 0.18 * pulso);
        var g = ctx.createRadialGradient(mx, my, 0, mx, my, rad);
        g.addColorStop(0, n.col(0.55 + 0.25 * pulso));
        g.addColorStop(1, n.col(0));
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(mx, my, rad, 0, 6.2832);
        ctx.fill();
      }
      ctx.globalCompositeOperation = 'source-over';
    }

    function drawOrbes(dt) {
      fondo();
      ctx.globalCompositeOperation = 'lighter';
      var vel = estado.movimiento ? 1 : 0.12;
      for (var i = 0; i < orbes.length; i++) {
        var o = orbes[i];
        o.x += o.vx * dt * vel;
        o.y += o.vy * dt * vel;
        if (o.x < -o.r) o.x = W + o.r; if (o.x > W + o.r) o.x = -o.r;
        if (o.y < -o.r) o.y = H + o.r; if (o.y > H + o.r) o.y = -o.r;
        var rr = o.r * (1 + 0.35 * pulso);
        var col = (i % 2 === 0) ? c1 : c2;
        var g = ctx.createRadialGradient(o.x, o.y, 0, o.x, o.y, rr);
        g.addColorStop(0, col(0.9));
        g.addColorStop(0.4, col(0.5));
        g.addColorStop(1, col(0));
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(o.x, o.y, rr, 0, 6.2832);
        ctx.fill();
      }
      ctx.globalCompositeOperation = 'source-over';
    }

    function drawOndas(dt) {
      fondo();
      ctx.globalCompositeOperation = 'lighter';
      var capas = 4;
      for (var l = 0; l < capas; l++) {
        if (estado.movimiento) ondasFase[l] += dt * (0.6 + l * 0.25);
        else ondasFase[l] += dt * 0.12;
        var amp = (H * 0.06) * (1 + l * 0.4) * (1 + 1.1 * pulso);
        var baseY = H * (0.35 + l * 0.16);
        var col = (l % 2 === 0) ? c1 : c2;
        ctx.beginPath();
        ctx.moveTo(0, H);
        for (var x = 0; x <= W; x += 12) {
          var y = baseY + amp * Math.sin((x / W) * 6.2832 * (1 + l * 0.5) + ondasFase[l]);
          ctx.lineTo(x, y);
        }
        ctx.lineTo(W, H);
        ctx.closePath();
        var g = ctx.createLinearGradient(0, baseY - amp, 0, H);
        g.addColorStop(0, col(0.28));
        g.addColorStop(1, col(0));
        ctx.fillStyle = g;
        ctx.fill();
      }
      ctx.globalCompositeOperation = 'source-over';
    }

    // ── Helper roundRect ─────────────────────────────────────────
    function roundRect(ctx, x, y, w, h, r) {
      r = Math.min(r, w / 2, h / 2);
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + w - r, y);
      ctx.arcTo(x + w, y, x + w, y + r, r);
      ctx.lineTo(x + w, y + h - r);
      ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
      ctx.lineTo(x + r, y + h);
      ctx.arcTo(x, y + h, x, y + h - r, r);
      ctx.lineTo(x, y + r);
      ctx.arcTo(x, y, x + r, y, r);
      ctx.closePath();
    }

    // ── Split-flap: tablero de aeropuerto con dígitos que "voltean" ──
    function sfTileBG(x, y, w, h) {
      var r = h * 0.1;
      roundRect(ctx, x, y, w, h, r);
      var g = ctx.createLinearGradient(0, y, 0, y + h);
      g.addColorStop(0, '#2a2d38');
      g.addColorStop(0.49, '#1c1f28');
      g.addColorStop(0.5, '#15171f');
      g.addColorStop(1, '#0e0f16');
      ctx.fillStyle = g;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    function sfDigit(x, y, w, h, d) {
      ctx.save();
      roundRect(ctx, x, y, w, h, h * 0.1);
      ctx.clip();
      ctx.shadowColor = c1(0.4);
      ctx.shadowBlur = h * 0.08;
      ctx.fillStyle = '#f4f5f9';
      ctx.font = 'bold ' + Math.round(h * 0.66) + 'px "Courier New", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(d, x + w / 2, y + h / 2 + h * 0.02);
      ctx.shadowBlur = 0;
      ctx.restore();
    }
    function sfSeam(x, y, w, h) {
      var my = y + h / 2;
      ctx.strokeStyle = 'rgba(0,0,0,0.55)';
      ctx.lineWidth = Math.max(2, h * 0.02);
      ctx.beginPath();
      ctx.moveTo(x + 2, my); ctx.lineTo(x + w - 2, my); ctx.stroke();
      ctx.strokeStyle = 'rgba(255,255,255,0.05)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x + 2, my + 1.2); ctx.lineTo(x + w - 2, my + 1.2); ctx.stroke();
    }
    function sfStatic(x, y, w, h, d) {
      sfTileBG(x, y, w, h);
      sfDigit(x, y, w, h, d);
      sfSeam(x, y, w, h);
    }
    function sfHalf(x, y, w, h, d, region) {
      ctx.save();
      var my = y + h / 2;
      ctx.beginPath();
      if (region === 'top') ctx.rect(x - 1, y - 1, w + 2, h / 2 + 1);
      else ctx.rect(x - 1, my, w + 2, h / 2 + 2);
      ctx.clip();
      sfTileBG(x, y, w, h);
      sfDigit(x, y, w, h, d);
      ctx.restore();
    }
    function sfLeaf(x, y, w, h, d, region, scaleY) {
      ctx.save();
      var my = y + h / 2;
      ctx.beginPath();
      if (region === 'top') ctx.rect(x - 1, y - 1, w + 2, h / 2 + 1);
      else ctx.rect(x - 1, my, w + 2, h / 2 + 2);
      ctx.clip();
      ctx.translate(0, my);
      ctx.scale(1, Math.max(0.0001, scaleY));
      ctx.translate(0, -my);
      sfTileBG(x, y, w, h);
      sfDigit(x, y, w, h, d);
      ctx.restore();
    }
    function sfFlip(x, y, w, h, oldD, newD, tt) {
      if (tt < 0.5) {
        var a = tt / 0.5;
        sfHalf(x, y, w, h, newD, 'top');      // el nuevo dígito ya asoma arriba
        sfHalf(x, y, w, h, oldD, 'bottom');   // el viejo sigue abajo
        sfLeaf(x, y, w, h, oldD, 'top', 1 - a); // hoja vieja plegándose
      } else {
        var b = (tt - 0.5) / 0.5;
        sfHalf(x, y, w, h, newD, 'top');
        sfHalf(x, y, w, h, oldD, 'bottom');
        sfLeaf(x, y, w, h, newD, 'bottom', b);  // hoja nueva desplegándose
      }
      sfSeam(x, y, w, h);
    }
    function sfColon(x, y, w, h) {
      var cx = x + w / 2, r = Math.max(2, h * 0.045);
      ctx.fillStyle = c1(0.85);
      ctx.beginPath(); ctx.arc(cx, y + h * 0.36, r, 0, 6.2832); ctx.fill();
      ctx.beginPath(); ctx.arc(cx, y + h * 0.64, r, 0, 6.2832); ctx.fill();
    }

    function drawSplitFlap(dt) {
      fondo();

      var mins = Math.max(0, Math.floor(estado.timerRestante / 60));
      var segs = Math.max(0, Math.floor(estado.timerRestante % 60));
      var mm = String(mins); if (mm.length < 2) mm = '0' + mm;
      var ss = String(segs); if (ss.length < 2) ss = '0' + ss;
      var chars = (mm + ss).split('');
      var n = chars.length;
      var colonIdx = mm.length; // el colon va antes de este dígito (entre min y seg)

      // (Re)inicializa el estado de flip si cambió la cantidad de dígitos.
      if (!flapShown || flapShown.length !== n) {
        flapShown = chars.slice();
        flapFrom = chars.slice();
        flapT = [];
        for (var k = 0; k < n; k++) flapT.push(1);
      }
      for (var i = 0; i < n; i++) {
        if (chars[i] !== flapShown[i] && flapT[i] >= 1) {
          flapFrom[i] = flapShown[i];
          flapShown[i] = chars[i];
          flapT[i] = 0;
        }
        if (flapT[i] < 1) flapT[i] = Math.min(1, flapT[i] + dt / 0.45);
      }

      // Layout centrado.
      var tileW = Math.min((W * 0.8) / (n + 0.6), H * 0.32);
      var tileH = tileW * 1.5;
      var gap = tileW * 0.16;
      var colonW = tileW * 0.6;
      var totalW = tileW * n + gap * n + colonW; // n gaps + colon
      var topY = H / 2 - tileH / 2;
      var x = (W - totalW) / 2;

      // Etiqueta "TIMER".
      ctx.fillStyle = 'rgba(255,255,255,0.42)';
      ctx.font = '600 ' + Math.round(tileH * 0.13) + 'px system-ui, "Segoe UI", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.fillText('T I M E R', W / 2, topY - tileH * 0.16);

      for (var j = 0; j < n; j++) {
        if (j === colonIdx) { sfColon(x, topY, colonW, tileH); x += colonW + gap; }
        if (flapT[j] >= 1) sfStatic(x, topY, tileW, tileH, flapShown[j]);
        else sfFlip(x, topY, tileW, tileH, flapFrom[j], flapShown[j], flapT[j]);
        x += tileW + gap;
      }

      // Barra de progreso.
      var barW = totalW;
      var barX = (W - barW) / 2;
      var barH = Math.max(3, tileH * 0.045);
      var barY = topY + tileH + tileH * 0.22;
      ctx.fillStyle = 'rgba(255,255,255,0.1)';
      roundRect(ctx, barX, barY, barW, barH, barH / 2);
      ctx.fill();
      ctx.fillStyle = c1(0.9);
      roundRect(ctx, barX, barY, barW * Math.min(1, estado.timerProgreso), barH, barH / 2);
      ctx.fill();
    }

    function drawColorCard(dt) {
      var bg = estado.timerFondoColor;
      ctx.fillStyle = 'rgb(' + bg.r + ',' + bg.g + ',' + bg.b + ')';
      ctx.fillRect(0, 0, W, H);

      // Viñeta suave para dar profundidad.
      var vg = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.2, W / 2, H / 2, Math.max(W, H) * 0.75);
      vg.addColorStop(0, 'rgba(0,0,0,0)');
      vg.addColorStop(1, 'rgba(0,0,0,0.35)');
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, W, H);

      var lum = (0.299 * bg.r + 0.587 * bg.g + 0.114 * bg.b) / 255;
      var ink = lum > 0.55 ? '0,0,0' : '255,255,255';
      var A = function (a) { return 'rgba(' + ink + ',' + a + ')'; };

      var mins = Math.max(0, Math.floor(estado.timerRestante / 60));
      var segs = Math.max(0, Math.floor(estado.timerRestante % 60));
      var tiempo = (mins < 10 ? '0' : '') + mins + ':' + (segs < 10 ? '0' : '') + segs;

      var pocoTiempo = estado.timerRestante > 0 && estado.timerRestante < 60;
      var pulso = pocoTiempo ? (0.9 + 0.1 * Math.sin(t * 5)) : 1;
      var fontSize = Math.min(W, H) * 0.2 * pulso;

      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Etiqueta.
      ctx.fillStyle = A(0.55);
      ctx.font = '600 ' + Math.round(fontSize * 0.16) + 'px system-ui, "Segoe UI", sans-serif';
      ctx.fillText('T I M E R', W / 2, H / 2 - fontSize * 0.62);

      // Tiempo.
      ctx.fillStyle = A(0.96);
      ctx.font = 'bold ' + Math.round(fontSize) + 'px "Courier New", monospace';
      ctx.fillText(tiempo, W / 2, H / 2);

      // Barra de progreso.
      var barW = Math.min(W * 0.6, fontSize * 4);
      var barX = W / 2 - barW / 2;
      var barH = Math.max(3, fontSize * 0.03);
      var barY = H / 2 + fontSize * 0.6;
      ctx.fillStyle = A(0.15);
      roundRect(ctx, barX, barY, barW, barH, barH / 2);
      ctx.fill();
      ctx.fillStyle = A(0.7);
      roundRect(ctx, barX, barY, barW * Math.min(1, estado.timerProgreso), barH, barH / 2);
      ctx.fill();
    }

    function frame(ms) {
      if (!ultimo) ultimo = ms;
      var dt = Math.min(0.05, (ms - ultimo) / 1000);
      ultimo = ms;
      t += dt;
      pulso *= Math.pow(0.06, dt);

      if (estado.tipo === 'orbes') drawOrbes(dt);
      else if (estado.tipo === 'ondas') drawOndas(dt);
      else if (estado.tipo === 'splitflap') drawSplitFlap(dt);
      else if (estado.tipo === 'colorcard') drawColorCard(dt);
      else drawAurora(dt);

      raf = requestAnimationFrame(frame);
    }

    window.addEventListener('resize', resize);
    resize();
    raf = requestAnimationFrame(frame);

    return {
      setColor: function (r, g, b) { estado.r = r; estado.g = g; estado.b = b; },
      setTipo: function (tipo) { estado.tipo = tipo; },
      setMovimiento: function (m) { estado.movimiento = !!m; },
      setRitmo: function (x) { estado.ritmo = !!x; },
      beat: function (e) { pulso = Math.max(pulso, Math.min(1, (e || 0.6) + 0.35)); },
      setTimerProgreso: function (p, restante) {
        estado.timerProgreso = p;
        estado.timerRestante = restante;
      },
      setTimerFondoColor: function (r, g, b) {
        estado.timerFondoColor.r = r;
        estado.timerFondoColor.g = g;
        estado.timerFondoColor.b = b;
      },
      destruir: function () {
        if (raf) cancelAnimationFrame(raf);
        window.removeEventListener('resize', resize);
      },
    };
  };
})();
