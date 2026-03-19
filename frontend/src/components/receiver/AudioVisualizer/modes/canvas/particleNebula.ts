import type { AudioEnergy } from '../../../../../audio/audioEnergy';

const PARTICLES = 2000;

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export function createParticleNebula(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): { draw: (audio: AudioEnergy) => void } {
  const particles: Particle[] = Array.from({ length: PARTICLES }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: 0,
    vy: 0,
  }));

  function draw(audio: AudioEnergy) {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.fillRect(0, 0, width, height);

    const turbulence = audio.bass * 4;
    const speed = 0.4 + audio.mid * 3.5;
    const brightness = 120 + audio.treble * 135;

    for (const p of particles) {
      p.vx += (Math.random() - 0.5) * turbulence;
      p.vy += (Math.random() - 0.5) * turbulence;

      p.x += p.vx * speed;
      p.y += p.vy * speed;

      if (p.x < 0) p.x = width;
      if (p.x > width) p.x = 0;
      if (p.y < 0) p.y = height;
      if (p.y > height) p.y = 0;

      ctx.fillStyle = `rgb(${brightness}, ${brightness}, 255)`;
      ctx.fillRect(p.x, p.y, 1.5, 1.5);
    }
  }

  return { draw };
}
