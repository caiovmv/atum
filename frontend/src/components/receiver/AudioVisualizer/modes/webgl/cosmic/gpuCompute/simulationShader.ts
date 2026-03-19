export const simulationVertexShader = /* glsl */ `
  void main() {
    gl_Position = vec4(position, 1.0);
  }
`;

export const velocityFragmentShader = /* glsl */ `
  uniform sampler2D positionTex;
  uniform sampler2D velocityTex;
  uniform float bass;
  uniform float mid;
  uniform vec2 resolution;

  void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    vec3 pos = texture2D(positionTex, uv).xyz;
    vec3 vel = texture2D(velocityTex, uv).xyz;

    float gravity = 0.0008 + bass * 0.025;
    vec3 dir = normalize(vec3(0.0) - pos);
    float dist = length(pos) + 0.01;
    vel += dir * gravity / (dist * dist);

    vel += vec3(
      sin(pos.y * 0.2) * mid,
      cos(pos.x * 0.2) * mid,
      sin(pos.z * 0.2) * mid
    ) * 0.002;

    gl_FragColor = vec4(vel, 1.0);
  }
`;

export const positionFragmentShader = /* glsl */ `
  uniform sampler2D positionTex;
  uniform sampler2D velocityTex;
  uniform vec2 resolution;

  void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    vec3 pos = texture2D(positionTex, uv).xyz;
    vec3 vel = texture2D(velocityTex, uv).xyz;
    pos += vel;
    gl_FragColor = vec4(pos, 1.0);
  }
`;
