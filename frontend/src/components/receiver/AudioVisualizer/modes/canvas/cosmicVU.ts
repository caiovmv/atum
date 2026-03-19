import type { AudioEnergy } from '../../../../../audio/audioEnergy';
import { ACCENT_HEX } from '../../../../../utils/theme';

export function createCosmicVU(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): { draw: (audio: AudioEnergy) => void } {
  const cx = width / 2;
  const cy = height / 2;

  function drawRing(
    radius: number,
    value: number,
    color: string
  ) {
    const segments = 60;
    const active = Math.floor(Math.min(1, value) * segments);

    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      const x1 = cx + Math.cos(angle) * radius;
      const y1 = cy + Math.sin(angle) * radius;
      const x2 = cx + Math.cos(angle) * (radius + 10);
      const y2 = cy + Math.sin(angle) * (radius + 10);

      ctx.strokeStyle = i < active ? color : 'rgba(80, 80, 80, 0.3)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
  }

  function draw(audio: AudioEnergy) {
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, width, height);

    drawRing(80, audio.bass, '#e53935');
    drawRing(110, audio.mid, '#ff9800');
    drawRing(140, audio.treble, ACCENT_HEX);
  }

  return { draw };
}
