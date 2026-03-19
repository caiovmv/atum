import type { AudioEnergy } from '../../../../../audio/audioEnergy';

const MAX_ITER = 80;

export function createFractal(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): { draw: (audio: AudioEnergy) => void } {
  let time = 0;

  function draw(audio: AudioEnergy) {
    time += 0.02;
    const zoom = 1.1 + audio.treble * 0.8;
    const offsetX = Math.sin(time * 0.2 + audio.bass * 4) * 0.15;
    const offsetY = Math.cos(time * 0.2 + audio.mid * 4) * 0.15;

    const baseScale = Math.min(width, height) / 2.5;
    const scale = baseScale / zoom;
    const aspect = width / height;
    const scaleX = aspect >= 1 ? scale : scale * aspect;
    const scaleY = aspect >= 1 ? scale / aspect : scale;

    const ox = width / 2;
    const oy = height / 2;

    const imgData = ctx.createImageData(width, height);
    const data = imgData.data;

    for (let py = 0; py < height; py++) {
      for (let px = 0; px < width; px++) {
        const cr = (px - ox) / scaleX + offsetX;
        const ci = (py - oy) / scaleY + offsetY;
        let zr = 0;
        let zi = 0;
        let i = 0;

        for (; i < MAX_ITER; i++) {
          const zr2 = zr * zr;
          const zi2 = zi * zi;
          if (zr2 + zi2 > 4) break;
          const newZr = zr2 - zi2 + cr;
          const newZi = 2 * zr * zi + ci;
          zr = newZr;
          zi = newZi;
        }

        const t = i / MAX_ITER;
        const idx = (py * width + px) * 4;
        const hue = (t * 360 + time * 20) % 360;
        const r = Math.floor(127 + 127 * Math.sin((hue * Math.PI) / 180));
        const g = Math.floor(127 + 127 * Math.sin(((hue + 120) * Math.PI) / 180));
        const b = Math.floor(127 + 127 * Math.sin(((hue + 240) * Math.PI) / 180));
        data[idx] = r;
        data[idx + 1] = g;
        data[idx + 2] = b;
        data[idx + 3] = 255;
      }
    }

    ctx.putImageData(imgData, 0, 0);
  }

  return { draw };
}
