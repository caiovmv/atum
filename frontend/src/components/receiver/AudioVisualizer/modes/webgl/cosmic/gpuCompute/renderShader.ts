export const particleVertexShader = /* glsl */ `
  attribute vec2 reference;
  uniform sampler2D positionTex;
  uniform float size;

  varying vec2 vReference;

  void main() {
    vReference = reference;
    vec4 posData = texture2D(positionTex, reference);
    vec3 pos = posData.xyz;

    vec4 mvPos = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mvPos;
    gl_PointSize = size * (300.0 / -mvPos.z);
  }
`;

/** Cores Cosmic VU: bass #e53935, mid #ff9800, treble #00e5c8 */
export const particleFragmentShader = /* glsl */ `
  uniform float bass;
  uniform float mid;
  uniform float treble;

  varying vec2 vReference;

  void main() {
    vec3 col;
    if (vReference.y < 0.333) {
      col = vec3(0.898, 0.224, 0.208);
    } else if (vReference.y < 0.666) {
      col = vec3(1.0, 0.596, 0.0);
    } else {
      col = vec3(0.0, 0.898, 0.784);
    }
    float intensity = 0.6 + bass * 0.2 + mid * 0.2 + treble * 0.2;
    gl_FragColor = vec4(col * intensity, 0.8);
  }
`;
