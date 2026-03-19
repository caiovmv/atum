import type { AudioEnergy } from '../../../../../audio/audioEnergy';
import { ACCENT_HEX } from '../../../../../utils/theme';

export function createOscilloscopeTunnel(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): { draw: (audio: AudioEnergy) => void } {
  let time = 0;
  const cx = width / 2;
  const cy = height / 2;

  function draw(audio: AudioEnergy) {
    time += 0.02;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, width, height);

    const depth = 150 + audio.bass * 550;
    const rotation = time + audio.mid * 3.5;
    const segments = 200;

    ctx.strokeStyle = ACCENT_HEX;
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let i = 0; i < segments; i++) {
      const t = i / segments;
      const x =
        cx +
        Math.sin(t * 10 + rotation) * depth * (1 - t);
      const y =
        cy +
        Math.cos(t * 10 + rotation) * depth * (1 - t);

      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }

    ctx.stroke();
  }

  return { draw };
}
