import type { CustomLayerInterface, CustomRenderMethodInput, Map as LibreMap } from 'maplibre-gl';
import type { BangkokGrid, GridHeader } from '@/lib/bangkok-grid';
import type { ScoredGrid } from '@/lib/scoring-grid-react';
import type { StationRatings } from '@/lib/types';
import { gridMesh } from '@/lib/bangkok-grid-mesh';
import { gridPixels } from '@/lib/bangkok-grid-colors';
import { recordPrototypeGridPaint } from '@/lib/bangkok-prototype';
import { measure } from '@/lib/render-profile';
import { profileGridGpu } from './profile-map';
import { gridTintOpacity } from './map-colors';

const vertex = `#version 300 es
in vec2 a_position;
in vec2 a_uv;
uniform mat4 u_matrix;
out vec2 v_uv;
void main() { gl_Position = u_matrix * vec4(a_position, 0.0, 1.0); v_uv = a_uv; }`;
const fragment = `#version 300 es
precision highp float;
uniform sampler2D u_grid;
uniform float u_opacity;
uniform float u_lines;
in vec2 v_uv;
out vec4 fragColor;
void main() {
  vec4 c = texture(u_grid, v_uv);
  vec2 cell = v_uv * vec2(textureSize(u_grid, 0));
  vec2 edge = min(fract(cell), 1.0 - fract(cell));
  vec2 line = 1.0 - smoothstep(vec2(0.0), max(fwidth(cell) * 0.7, vec2(0.0001)), edge);
  c.rgb = mix(c.rgb, vec3(1.0), max(line.x, line.y) * 0.2 * u_lines);
  c.a *= u_opacity;
  fragColor = vec4(c.rgb * c.a, c.a);
}`;

export class GridTextureLayer implements CustomLayerInterface {
  readonly id = 'bkk-grid-texture';
  readonly type = 'custom' as const;
  readonly renderingMode = '2d' as const;
  visible = false;
  uploads = 0;
  draws = 0;
  updateMs = 0;
  private map: LibreMap | null = null;
  private mesh;
  private pixels: Uint8Array;
  private matrix = new Float32Array(16);
  private dirty = true;
  private gl: WebGL2RenderingContext | null = null;
  private resources: { program: WebGLProgram; vao: WebGLVertexArrayObject; vertices: WebGLBuffer; indices: WebGLBuffer; texture: WebGLTexture; matrix: WebGLUniformLocation | null; sampler: WebGLUniformLocation | null; opacity: WebGLUniformLocation | null; lines: WebGLUniformLocation | null } | null = null;
  constructor(private header: GridHeader) {
    this.mesh = measure('grid.mesh', () => gridMesh(header));
    this.pixels = new Uint8Array(header.nx * header.ny * 4);
  }
  get gpuBytes() { return this.pixels.byteLength + this.mesh.vertices.byteLength + this.mesh.indices.byteLength; }
  update(grid: BangkokGrid, scored: ScoredGrid, dimension: keyof StationRatings | null) {
    const start = performance.now();
    measure('grid.colors', () => gridPixels(grid, scored.scores, scored.pass, scored.anchors, dimension, scored.districts, this.pixels), grid.cells.length, this.pixels.byteLength);
    this.updateMs = performance.now() - start;
    this.dirty = true;
    this.map?.triggerRepaint();
  }
  onAdd(map: LibreMap, gl: WebGL2RenderingContext) {
    this.map = map; this.gl = gl;
    measure('grid.resources', () => this.createResources(gl), 1, this.gpuBytes);
  }
  private createResources(gl: WebGL2RenderingContext) {
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type)!; gl.shaderSource(shader, source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) { const error = gl.getShaderInfoLog(shader); gl.deleteShader(shader); throw new Error(error ?? 'Grid shader compilation failed'); }
      return shader;
    };
    const vs = compile(gl.VERTEX_SHADER, vertex), fs = compile(gl.FRAGMENT_SHADER, fragment);
    const program = gl.createProgram()!;
    gl.attachShader(program, vs); gl.attachShader(program, fs); gl.linkProgram(program);
    gl.deleteShader(vs); gl.deleteShader(fs);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) { const error = gl.getProgramInfoLog(program); gl.deleteProgram(program); throw new Error(error ?? 'Grid shader linking failed'); }
    const vao = gl.createVertexArray()!, vertices = gl.createBuffer()!, indices = gl.createBuffer()!, texture = gl.createTexture()!;
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, vertices); gl.bufferData(gl.ARRAY_BUFFER, this.mesh.vertices, gl.STATIC_DRAW);
    const pos = gl.getAttribLocation(program, 'a_position'), uv = gl.getAttribLocation(program, 'a_uv');
    gl.enableVertexAttribArray(pos); gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 16, 0);
    gl.enableVertexAttribArray(uv); gl.vertexAttribPointer(uv, 2, gl.FLOAT, false, 16, 8);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indices); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, this.mesh.indices, gl.STATIC_DRAW);
    gl.bindVertexArray(null);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, this.header.nx, this.header.ny, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    this.resources = { program, vao, vertices, indices, texture, matrix: gl.getUniformLocation(program, 'u_matrix'), sampler: gl.getUniformLocation(program, 'u_grid'), opacity: gl.getUniformLocation(program, 'u_opacity'), lines: gl.getUniformLocation(program, 'u_lines') };
    this.dirty = true;
  }
  render(gl: WebGL2RenderingContext, options: CustomRenderMethodInput) {
    const r = this.resources;
    if (!this.visible || !r || gl.isContextLost()) return;
    gl.useProgram(r.program); gl.bindVertexArray(r.vao);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, r.texture);
    if (this.dirty) {
      gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1); gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 0); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, 0);
      measure('grid.upload.submit', () => gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, this.header.nx, this.header.ny, gl.RGBA, gl.UNSIGNED_BYTE, this.pixels), 1, this.pixels.byteLength);
      this.dirty = false; this.uploads++; recordPrototypeGridPaint();
    }
    const m = options.defaultProjectionData.mainMatrix;
    this.matrix.set(m);
    // Translate in double precision before uploading: global float32 positions
    // visibly jitter at street zoom. Vertices use offsets from the city origin.
    for (let row = 0; row < 4; row++) this.matrix[12 + row] = m[12 + row] + m[row] * this.mesh.origin[0] + m[4 + row] * this.mesh.origin[1];
    gl.uniformMatrix4fv(r.matrix, false, this.matrix); gl.uniform1i(r.sampler, 0);
    // Fade the analytical tint as street detail grows. Uniform-only updates:
    // no scoring, allocation or texture upload on pan/zoom/pitch.
    const zoom = this.map?.getZoom() ?? 11;
    gl.uniform1f(r.opacity, gridTintOpacity(zoom));
    gl.uniform1f(r.lines, Math.max(0, Math.min(1, (zoom - 12) / 2)));
    profileGridGpu(gl, () => measure('grid.draw.submit', () => gl.drawElements(gl.TRIANGLES, this.mesh.indices.length, gl.UNSIGNED_SHORT, 0), 1));
    gl.bindVertexArray(null); this.draws++;
  }
  onRemove(map: LibreMap, gl: WebGL2RenderingContext) {
    const r = this.resources;
    if (r && !gl.isContextLost()) { gl.deleteProgram(r.program); gl.deleteVertexArray(r.vao); gl.deleteBuffer(r.vertices); gl.deleteBuffer(r.indices); gl.deleteTexture(r.texture); }
    this.resources = null; this.map = null; this.gl = null;
  }
}
