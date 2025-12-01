/**
 * Threads Background Effect
 * Converted from React/OGL to vanilla JavaScript/WebGL
 * For use with Flask templates
 */

class ThreadsBackground {
    constructor(container, options = {}) {
        this.container = container;
        this.color = options.color || [0.74, 0.14, 0.25]; // Burgundy/red color
        this.amplitude = options.amplitude || 1;
        this.distance = options.distance || 0;
        this.enableMouseInteraction = options.enableMouseInteraction !== false;
        
        this.currentMouse = [0.5, 0.5];
        this.targetMouse = [0.5, 0.5];
        this.animationFrameId = null;
        
        this.init();
    }

    init() {
        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.style.cssText = 'position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;';
        this.container.appendChild(this.canvas);

        // Get WebGL context
        this.gl = this.canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false });
        if (!this.gl) {
            console.warn('WebGL not supported');
            return;
        }

        const gl = this.gl;
        gl.clearColor(0, 0, 0, 0);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        // Create shaders
        this.program = this.createProgram();
        if (!this.program) return;

        // Create geometry (full-screen triangle)
        this.createGeometry();

        // Get uniform locations
        this.uniforms = {
            iTime: gl.getUniformLocation(this.program, 'iTime'),
            iResolution: gl.getUniformLocation(this.program, 'iResolution'),
            uColor: gl.getUniformLocation(this.program, 'uColor'),
            uAmplitude: gl.getUniformLocation(this.program, 'uAmplitude'),
            uDistance: gl.getUniformLocation(this.program, 'uDistance'),
            uMouse: gl.getUniformLocation(this.program, 'uMouse')
        };

        // Setup event listeners
        this.resize = this.resize.bind(this);
        this.update = this.update.bind(this);
        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.handleMouseLeave = this.handleMouseLeave.bind(this);

        window.addEventListener('resize', this.resize);
        
        if (this.enableMouseInteraction) {
            document.addEventListener('mousemove', this.handleMouseMove);
            document.addEventListener('mouseleave', this.handleMouseLeave);
        }

        this.resize();
        this.startTime = performance.now();
        this.update();
    }

    createProgram() {
        const gl = this.gl;

        const vertexShader = `
            attribute vec2 position;
            void main() {
                gl_Position = vec4(position, 0.0, 1.0);
            }
        `;

        const fragmentShader = `
            precision highp float;
            uniform float iTime;
            uniform vec3 iResolution;
            uniform vec3 uColor;
            uniform float uAmplitude;
            uniform float uDistance;
            uniform vec2 uMouse;

            #define PI 3.1415926538
            const int u_line_count = 40;
            const float u_line_width = 7.0;
            const float u_line_blur = 10.0;

            float Perlin2D(vec2 P) {
                vec2 Pi = floor(P);
                vec4 Pf_Pfmin1 = P.xyxy - vec4(Pi, Pi + 1.0);
                vec4 Pt = vec4(Pi.xy, Pi.xy + 1.0);
                Pt = Pt - floor(Pt * (1.0 / 71.0)) * 71.0;
                Pt += vec2(26.0, 161.0).xyxy;
                Pt *= Pt;
                Pt = Pt.xzxz * Pt.yyww;
                vec4 hash_x = fract(Pt * (1.0 / 951.135664));
                vec4 hash_y = fract(Pt * (1.0 / 642.949883));
                vec4 grad_x = hash_x - 0.49999;
                vec4 grad_y = hash_y - 0.49999;
                vec4 grad_results = inversesqrt(grad_x * grad_x + grad_y * grad_y)
                    * (grad_x * Pf_Pfmin1.xzxz + grad_y * Pf_Pfmin1.yyww);
                grad_results *= 1.4142135623730950;
                vec2 blend = Pf_Pfmin1.xy * Pf_Pfmin1.xy * Pf_Pfmin1.xy
                           * (Pf_Pfmin1.xy * (Pf_Pfmin1.xy * 6.0 - 15.0) + 10.0);
                vec4 blend2 = vec4(blend, vec2(1.0 - blend));
                return dot(grad_results, blend2.zxzx * blend2.wwyy);
            }

            float pixel(float count, vec2 resolution) {
                return (1.0 / max(resolution.x, resolution.y)) * count;
            }

            float lineFn(vec2 st, float width, float perc, float offset, vec2 mouse, float time, float amplitude, float distance) {
                float split_offset = (perc * 0.4);
                float split_point = 0.1 + split_offset;
                float amplitude_normal = smoothstep(split_point, 0.7, st.x);
                float amplitude_strength = 0.5;
                float finalAmplitude = amplitude_normal * amplitude_strength
                                       * amplitude * (1.0 + (mouse.y - 0.5) * 0.2);
                float time_scaled = time / 10.0 + (mouse.x - 0.5) * 1.0;
                float blur = smoothstep(split_point, split_point + 0.05, st.x) * perc;
                float xnoise = mix(
                    Perlin2D(vec2(time_scaled, st.x + perc) * 2.5),
                    Perlin2D(vec2(time_scaled, st.x + time_scaled) * 3.5) / 1.5,
                    st.x * 0.3
                );
                float y = 0.5 + (perc - 0.5) * distance + xnoise / 2.0 * finalAmplitude;
                float line_start = smoothstep(
                    y + (width / 2.0) + (u_line_blur * pixel(1.0, iResolution.xy) * blur),
                    y,
                    st.y
                );
                float line_end = smoothstep(
                    y,
                    y - (width / 2.0) - (u_line_blur * pixel(1.0, iResolution.xy) * blur),
                    st.y
                );
                return clamp(
                    (line_start - line_end) * (1.0 - smoothstep(0.0, 1.0, pow(perc, 0.3))),
                    0.0,
                    1.0
                );
            }

            void main() {
                vec2 uv = gl_FragCoord.xy / iResolution.xy;
                float line_strength = 1.0;
                for (int i = 0; i < u_line_count; i++) {
                    float p = float(i) / float(u_line_count);
                    line_strength *= (1.0 - lineFn(
                        uv,
                        u_line_width * pixel(1.0, iResolution.xy) * (1.0 - p),
                        p,
                        (PI * 1.0) * p,
                        uMouse,
                        iTime,
                        uAmplitude,
                        uDistance
                    ));
                }
                float colorVal = 1.0 - line_strength;
                gl_FragColor = vec4(uColor * colorVal, colorVal * 0.6);
            }
        `;

        const vs = this.compileShader(gl.VERTEX_SHADER, vertexShader);
        const fs = this.compileShader(gl.FRAGMENT_SHADER, fragmentShader);
        if (!vs || !fs) return null;

        const program = gl.createProgram();
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);

        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error('Program link error:', gl.getProgramInfoLog(program));
            return null;
        }

        return program;
    }

    compileShader(type, source) {
        const gl = this.gl;
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);

        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error('Shader compile error:', gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }

        return shader;
    }

    createGeometry() {
        const gl = this.gl;

        // Full-screen triangle
        const vertices = new Float32Array([
            -1, -1,
             3, -1,
            -1,  3
        ]);

        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

        const positionLocation = gl.getAttribLocation(this.program, 'position');
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
    }

    resize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.canvas.width = width;
        this.canvas.height = height;
        this.gl.viewport(0, 0, width, height);
    }

    handleMouseMove(e) {
        const rect = this.container.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = 1.0 - (e.clientY - rect.top) / rect.height;
        this.targetMouse = [x, y];
    }

    handleMouseLeave() {
        this.targetMouse = [0.5, 0.5];
    }

    update() {
        const gl = this.gl;
        if (!gl || !this.program) return;

        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.useProgram(this.program);

        // Smooth mouse movement
        if (this.enableMouseInteraction) {
            const smoothing = 0.05;
            this.currentMouse[0] += smoothing * (this.targetMouse[0] - this.currentMouse[0]);
            this.currentMouse[1] += smoothing * (this.targetMouse[1] - this.currentMouse[1]);
        }

        // Update uniforms
        const time = (performance.now() - this.startTime) * 0.001;
        gl.uniform1f(this.uniforms.iTime, time);
        gl.uniform3f(this.uniforms.iResolution, this.canvas.width, this.canvas.height, this.canvas.width / this.canvas.height);
        gl.uniform3f(this.uniforms.uColor, this.color[0], this.color[1], this.color[2]);
        gl.uniform1f(this.uniforms.uAmplitude, this.amplitude);
        gl.uniform1f(this.uniforms.uDistance, this.distance);
        gl.uniform2f(this.uniforms.uMouse, this.currentMouse[0], this.currentMouse[1]);

        // Draw
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        this.animationFrameId = requestAnimationFrame(this.update);
    }

    destroy() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }
        window.removeEventListener('resize', this.resize);
        if (this.enableMouseInteraction) {
            document.removeEventListener('mousemove', this.handleMouseMove);
            document.removeEventListener('mouseleave', this.handleMouseLeave);
        }
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
        if (this.gl) {
            const ext = this.gl.getExtension('WEBGL_lose_context');
            if (ext) ext.loseContext();
        }
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('threads-bg');
    if (container) {
        new ThreadsBackground(container, {
            color: [0.74, 0.14, 0.25], // Burgundy/red matching theme
            amplitude: 1,
            distance: 0,
            enableMouseInteraction: true
        });
    }
});

