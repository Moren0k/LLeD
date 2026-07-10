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
    };
    Object.assign(estado, opciones || {});

    var W = 0, H = 0, dpr = 1;
    var pulso = 0;            // 0..1, sube en cada beat y decae
    var t = 0;               // tiempo acumulado
    var raf = null, ultimo = 0;
    var orbes = [], ondasFase = [];

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

    function frame(ms) {
      if (!ultimo) ultimo = ms;
      var dt = Math.min(0.05, (ms - ultimo) / 1000);
      ultimo = ms;
      t += dt;
      pulso *= Math.pow(0.06, dt); // decae rápido pero suave

      if (estado.tipo === 'orbes') drawOrbes(dt);
      else if (estado.tipo === 'ondas') drawOndas(dt);
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
      destruir: function () {
        if (raf) cancelAnimationFrame(raf);
        window.removeEventListener('resize', resize);
      },
    };
  };
})();
