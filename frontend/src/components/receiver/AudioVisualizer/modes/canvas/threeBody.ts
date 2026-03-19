import type { AudioEnergy } from '../../../../../audio/audioEnergy';
import { ACCENT_RGB } from '../../../../../utils/theme';

interface Body {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export function createThreeBody(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): { draw: (audio: AudioEnergy) => void } {
  const cx = width / 2;
  const cy = height / 2;

  const bodies: Body[] = [
    { x: cx - 80, y: cy - 40, vx: 0, vy: 0.8 },
    { x: cx + 80, y: cy + 20, vx: 0, vy: -0.8 },
    { x: cx, y: cy + 100, vx: 0.6, vy: 0 },
  ];

  function draw(audio: AudioEnergy) {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.08)';
    ctx.fillRect(0, 0, width, height);

    const G = 0.03 + audio.bass * 0.7;
    const radius = 3 + audio.mid * 18;

    for (let i = 0; i < bodies.length; i++) {
      const a = bodies[i];
      for (let j = 0; j < bodies.length; j++) {
        if (i === j) continue;
        const b = bodies[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.01;
        const force = G / (dist * dist);
        a.vx += (force * dx) / dist;
        a.vy += (force * dy) / dist;
      }
    }

    for (const b of bodies) {
      b.x += b.vx;
      b.y += b.vy;

      ctx.beginPath();
      ctx.arc(b.x, b.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${ACCENT_RGB}, ${0.5 + audio.treble * 0.5})`;
      ctx.fill();
    }
  }

  return { draw };
}
