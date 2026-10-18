"""GLSL sources for the post-processing pipeline.

Pipeline (all world passes run at the low-res canvas size):
  1. LIGHT   albedo * dynamic lights + emissive + wet-street reflections -> lit (HDR)
  2. BRIGHT  extract bright/emissive parts, downsample
  3. BLUR    separable gaussian at half and quarter resolution (bloom + fog glow)
  4. FINAL   sub-pixel camera shift, bloom, fog, tone map, grain, vignette -> screen
  5. QUAD    textured quads (portraits) and the UI layer on top
"""

from ..config import MAX_LIGHTS

FULLSCREEN_VS = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

LIGHT_FS = f"""
#version 330
#define MAX_LIGHTS {MAX_LIGHTS}
uniform sampler2D u_albedo;
uniform sampler2D u_emissive;
uniform sampler2D u_material;
uniform vec2 u_canvas;
uniform vec3 u_ambient;
uniform float u_time;
uniform float u_reflect;
uniform int u_nlights;
uniform vec4 u_lpos[MAX_LIGHTS];   // x, y, radius, intensity
uniform vec4 u_lcol[MAX_LIGHTS];   // r, g, b, specular
uniform vec4 u_ldir[MAX_LIGHTS];   // dir.x, dir.y, cos_inner, cos_outer (cos_outer < -1 => omni)
uniform vec4 u_lclip[MAX_LIGHTS];  // x0, y0, x1, y1 (x1 <= x0 => unclipped)
in vec2 v_uv;
out vec4 f_color;

vec2 to_px(vec2 uv) {{ return uv * u_canvas; }}  // textures are stored y-down
vec2 to_uv(vec2 px) {{ return px / u_canvas; }}

float hash(vec2 p) {{ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }}

// Returns diffuse light in rgb and a specular-ish hotspot term in a.
vec4 light_at(vec2 p) {{
    vec3 acc = u_ambient;
    float spec = 0.0;
    for (int i = 0; i < u_nlights; ++i) {{
        vec4 lp = u_lpos[i];
        vec4 cl = u_lclip[i];
        if (cl.z > cl.x && (p.x < cl.x || p.y < cl.y || p.x > cl.z || p.y > cl.w)) continue;
        vec2 d = p - lp.xy;
        float dist = length(d);
        if (dist > lp.z) continue;
        float k = 1.0 - (dist * dist) / (lp.z * lp.z);
        float f = k * k * lp.w;
        vec4 ld = u_ldir[i];
        if (ld.w > -1.5) {{
            float c = dot(d / max(dist, 0.001), ld.xy);
            f *= smoothstep(ld.w, ld.z, c);
        }}
        acc += u_lcol[i].rgb * f;
        spec += f * k * u_lcol[i].a;
    }}
    return vec4(acc, spec);
}}

void main() {{
    vec2 p = to_px(v_uv);
    vec4 alb = texture(u_albedo, v_uv);
    vec3 emi = texture(u_emissive, v_uv).rgb;
    vec4 mat = texture(u_material, v_uv);
    vec4 L = light_at(p);
    vec3 col = alb.rgb * L.rgb + emi * 1.35;

    float wet = mat.r;
    float dist = mat.g * 255.0;
    if (wet > 0.01) {{
        // glossy hotspot under lamps
        col += L.rgb * L.a * wet * 0.35;
        if (dist > 0.5) {{
            float ripple = sin(p.y * 0.9 + u_time * 2.7) * 0.55 + (hash(floor(p * 0.5) + floor(u_time * 6.0)) - 0.5) * 0.9;
            vec2 rp = vec2(p.x + ripple * wet, p.y - 2.0 * dist);
            if (rp.y > 0.0) {{
                vec2 ruv = to_uv(rp);
                vec3 remi = texture(u_emissive, ruv).rgb;
                vec3 ralb = texture(u_albedo, ruv).rgb;
                vec3 rl = light_at(rp).rgb;
                float fade = exp(-dist / 70.0);
                col += (remi * 1.2 + ralb * rl * 0.55) * wet * u_reflect * fade;
            }}
        }}
    }}
    f_color = vec4(col, 1.0);
}}
"""

BRIGHT_FS = """
#version 330
uniform sampler2D u_lit;
uniform sampler2D u_emissive;
uniform vec2 u_texel;
in vec2 v_uv;
out vec4 f_color;
void main() {
    vec3 acc = vec3(0.0);
    for (int y = 0; y < 2; ++y)
        for (int x = 0; x < 2; ++x) {
            vec2 o = (vec2(x, y) - 0.5) * u_texel;
            vec3 c = texture(u_lit, v_uv + o).rgb;
            vec3 e = texture(u_emissive, v_uv + o).rgb;
            acc += max(c - vec3(0.55), vec3(0.0)) * 0.8 + e * 0.9;
        }
    f_color = vec4(acc * 0.25, 1.0);
}
"""

BLUR_FS = """
#version 330
uniform sampler2D u_src;
uniform vec2 u_dir;   // texel step in uv, along one axis
in vec2 v_uv;
out vec4 f_color;
void main() {
    float w[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    vec3 acc = texture(u_src, v_uv).rgb * w[0];
    for (int i = 1; i < 5; ++i) {
        acc += texture(u_src, v_uv + u_dir * float(i) * 1.4).rgb * w[i];
        acc += texture(u_src, v_uv - u_dir * float(i) * 1.4).rgb * w[i];
    }
    f_color = vec4(acc, 1.0);
}
"""

FINAL_FS = """
#version 330
uniform sampler2D u_lit;
uniform sampler2D u_bloom_a;   // half res
uniform sampler2D u_bloom_b;   // quarter res
uniform vec2 u_canvas;         // canvas size incl. margin
uniform vec2 u_view;           // visible size
uniform vec2 u_frac;           // sub-pixel camera offset in canvas pixels [0,1)
uniform vec2 u_cam;            // camera world position (px) for anchoring fog noise
uniform float u_time;
uniform float u_fog;
uniform vec3 u_fog_color;
uniform float u_bloom;
uniform float u_exposure;
uniform float u_flash;
uniform vec3 u_flash_color;
uniform float u_fade;          // 0 = visible, 1 = black
uniform float u_hurt;          // red edge vignette strength
uniform float u_grain;
uniform float u_saturation;
in vec2 v_uv;
out vec4 f_color;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i), b = hash(i + vec2(1, 0)), c = hash(i + vec2(0, 1)), d = hash(i + vec2(1, 1));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fbm(vec2 p) {
    float s = 0.0, a = 0.5;
    for (int i = 0; i < 4; ++i) { s += vnoise(p) * a; p *= 2.03; a *= 0.5; }
    return s;
}

vec3 tonemap(vec3 x) {
    // ACES fitted curve (Narkowicz)
    x *= u_exposure;
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}

void main() {
    // pixel position inside the visible view (y down)
    vec2 vp = vec2(v_uv.x * u_view.x, (1.0 - v_uv.y) * u_view.y);
    vec2 cp = vp + vec2(1.0) + u_frac;           // canvas pixel (margin = 1)
    vec2 snapped = floor(cp) + 0.5;
    vec2 uv = snapped / u_canvas;
    vec2 suv = cp / u_canvas;

    vec3 col = texture(u_lit, uv).rgb;
    vec3 ba = texture(u_bloom_a, suv).rgb;
    vec3 bb = texture(u_bloom_b, suv).rgb;
    col += (ba * 0.55 + bb * 0.65) * u_bloom;

    // drifting fog, lit by the surrounding light (reuses the wide bloom)
    vec2 wp = (vp + u_cam) * 0.012;
    float n = fbm(wp + vec2(u_time * 0.05, u_time * 0.015));
    float fog = u_fog * smoothstep(0.35, 0.85, n);
    col = mix(col, u_fog_color * 0.25 + bb * 2.2 + ba * 0.6, fog);

    col = tonemap(col);
    float luma = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(luma), col, u_saturation);

    // vignette + hurt
    vec2 c = v_uv - 0.5;
    float vig = smoothstep(0.85, 0.25, length(c * vec2(1.0, 1.15)));
    col *= mix(0.55, 1.0, vig);
    col = mix(col, vec3(0.55, 0.02, 0.03), u_hurt * (1.0 - vig) * 0.8);

    col += u_flash_color * u_flash;
    float g = hash(floor(vp) + fract(u_time * 13.17) * 91.0) - 0.5;
    col += g * u_grain;
    col *= (1.0 - u_fade);
    f_color = vec4(col, 1.0);
}
"""

QUAD_VS = """
#version 330
in vec2 in_pos;
uniform vec4 u_rect;    // x, y, w, h in NDC (y up)
uniform vec4 u_src;     // u0, v0, u1, v1
out vec2 v_uv;
void main() {
    vec2 t = in_pos * 0.5 + 0.5;
    v_uv = mix(u_src.xy, u_src.zw, vec2(t.x, 1.0 - t.y));
    gl_Position = vec4(u_rect.xy + t * u_rect.zw, 0.0, 1.0);
}
"""

QUAD_FS = """
#version 330
uniform sampler2D u_tex;
uniform vec4 u_tint;
in vec2 v_uv;
out vec4 f_color;
void main() {
    vec4 c = texture(u_tex, v_uv);
    f_color = vec4(c.rgb * u_tint.rgb, c.a * u_tint.a);
}
"""
