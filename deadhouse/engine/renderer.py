"""GPU post-processing renderer.

The game draws three low-res layers on the CPU with pygame each frame:
  albedo   - what things look like under neutral light
  emissive - what glows by itself (neon, windows, lamp bulbs, cigarette tips)
  material - R: wetness, G: distance (px) to the reflection mirror line
These are uploaded and combined on the GPU with dynamic lights, reflections,
bloom, fog and film grading. The UI layer and portrait quads are drawn on top.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import moderngl
import numpy as np
import pygame

from .. import config as C
from . import shaders


@dataclass
class Light:
    x: float
    y: float
    radius: float
    color: tuple[float, float, float]
    intensity: float = 1.0
    specular: float = 1.0
    direction: tuple[float, float] | None = None  # cone lights only
    cos_inner: float = 0.9
    cos_outer: float = 0.7
    clip: tuple[float, float, float, float] | None = None  # world rect x0,y0,x1,y1


@dataclass
class PostParams:
    ambient: tuple[float, float, float] = (0.06, 0.07, 0.11)
    fog: float = 0.0
    fog_color: tuple[float, float, float] = (0.2, 0.22, 0.3)
    bloom: float = 1.0
    exposure: float = 1.1
    reflect: float = 1.0
    grain: float = 0.035
    saturation: float = 1.0
    flash: float = 0.0
    flash_color: tuple[float, float, float] = (1.0, 0.95, 0.8)
    fade: float = 0.0
    hurt: float = 0.0


@dataclass
class Quad:
    texture_key: str
    rect: tuple[float, float, float, float]  # x, y, w, h in UI pixels
    alpha: float = 1.0
    tint: tuple[float, float, float] = (1.0, 1.0, 1.0)
    src: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    above_ui: bool = False


class Renderer:
    def __init__(self, ctx: moderngl.Context, window_size: tuple[int, int]):
        self.ctx = ctx
        self.window_size = window_size
        cw, ch = C.CANVAS_W, C.CANVAS_H
        quad = np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4")
        self.vbo = ctx.buffer(quad.tobytes())

        def prog(fs, vs=shaders.FULLSCREEN_VS):
            p = ctx.program(vertex_shader=vs, fragment_shader=fs)
            return p, ctx.vertex_array(p, [(self.vbo, "2f", "in_pos")])

        self.p_light, self.va_light = prog(shaders.LIGHT_FS)
        self.p_bright, self.va_bright = prog(shaders.BRIGHT_FS)
        self.p_blur, self.va_blur = prog(shaders.BLUR_FS)
        self.p_final, self.va_final = prog(shaders.FINAL_FS)
        self.p_quad, self.va_quad = prog(shaders.QUAD_FS, shaders.QUAD_VS)

        def tex(w, h, comps=4, dtype="f1", filt=moderngl.NEAREST):
            t = ctx.texture((w, h), comps, dtype=dtype)
            t.filter = (filt, filt)
            t.repeat_x = t.repeat_y = False
            return t

        self.t_albedo = tex(cw, ch)
        self.t_emissive = tex(cw, ch)
        self.t_material = tex(cw, ch)
        # CPU canvases are pygame's native 32-bit BGRA: upload raw bytes and let the sampler swizzle
        for t in (self.t_albedo, self.t_emissive, self.t_material):
            t.swizzle = "BGRA"
        self.t_lit = tex(cw, ch, dtype="f2")
        self.f_lit = ctx.framebuffer([self.t_lit])
        hw, hh = cw // 2, ch // 2
        qw, qh = cw // 4, ch // 4
        lin = moderngl.LINEAR
        self.t_ha, self.t_hb = tex(hw, hh, dtype="f2", filt=lin), tex(hw, hh, dtype="f2", filt=lin)
        self.t_qa, self.t_qb = tex(qw, qh, dtype="f2", filt=lin), tex(qw, qh, dtype="f2", filt=lin)
        self.f_ha, self.f_hb = ctx.framebuffer([self.t_ha]), ctx.framebuffer([self.t_hb])
        self.f_qa, self.f_qb = ctx.framebuffer([self.t_qa]), ctx.framebuffer([self.t_qb])
        self.t_ui = tex(C.UI_W, C.UI_H)
        self.t_ui.swizzle = "BGRA"
        self.textures: dict[str, moderngl.Texture] = {}
        self.time = 0.0

    # ------------------------------------------------------------------ utils
    def resize(self, size: tuple[int, int]) -> None:
        self.window_size = size

    def view_rect(self) -> tuple[int, int, int, int]:
        """Largest 16:9 rectangle that fits the window (letterboxed)."""
        w, h = self.window_size
        scale = min(w / C.VIEW_W, h / C.VIEW_H)
        if scale >= 1:
            # Prefer integer scaling when it loses less than 15% of the window.
            si = int(scale)
            if si >= 1 and si / scale > 0.85:
                scale = si
        vw, vh = int(C.VIEW_W * scale), int(C.VIEW_H * scale)
        return (w - vw) // 2, (h - vh) // 2, vw, vh

    def register_texture(self, key: str, surface: pygame.Surface, smooth: bool = True) -> None:
        if key in self.textures:
            self.textures[key].release()
        data = pygame.image.tobytes(surface, "RGBA")
        t = self.ctx.texture(surface.get_size(), 4, data)
        f = moderngl.LINEAR if smooth else moderngl.NEAREST
        t.filter = (f, f)
        self.textures[key] = t

    _BGRA = (0xFF0000, 0xFF00, 0xFF, 0xFF000000)

    @classmethod
    def _upload(cls, t: moderngl.Texture, surf: pygame.Surface) -> None:
        """Zero-copy upload for BGRA surfaces with a tight pitch (the canvases); fall back to a conversion."""
        if surf.get_masks() == cls._BGRA and surf.get_pitch() == surf.get_width() * 4:
            t.write(surf.get_buffer())
        else:
            t.write(pygame.image.tobytes(surf, "BGRA"))

    def _set_lights(self, lights: list[Light], cam_x: float, cam_y: float) -> None:
        n = min(len(lights), C.MAX_LIGHTS)
        pos = np.zeros((C.MAX_LIGHTS, 4), "f4")
        col = np.zeros((C.MAX_LIGHTS, 4), "f4")
        dirs = np.full((C.MAX_LIGHTS, 4), -2.0, "f4")
        clip = np.zeros((C.MAX_LIGHTS, 4), "f4")
        ox, oy = -cam_x + C.MARGIN, -cam_y + C.MARGIN
        for i, L in enumerate(lights[:n]):
            pos[i] = (L.x + ox, L.y + oy, L.radius, L.intensity)
            col[i] = (*L.color, L.specular)
            if L.direction is not None:
                dirs[i] = (L.direction[0], L.direction[1], L.cos_inner, L.cos_outer)
            if L.clip is not None:
                x0, y0, x1, y1 = L.clip
                clip[i] = (x0 + ox, y0 + oy, x1 + ox, y1 + oy)
        self.p_light["u_nlights"].value = n
        self.p_light["u_lpos"].write(pos.tobytes())
        self.p_light["u_lcol"].write(col.tobytes())
        self.p_light["u_ldir"].write(dirs.tobytes())
        self.p_light["u_lclip"].write(clip.tobytes())

    # ------------------------------------------------------------------ frame
    def render(
        self,
        albedo: pygame.Surface,
        emissive: pygame.Surface,
        material: pygame.Surface,
        lights: list[Light],
        cam: tuple[float, float],
        post: PostParams,
        ui: pygame.Surface | None,
        quads: list[Quad],
        dt: float,
    ) -> None:
        ctx = self.ctx
        self.time += dt
        cam_x, cam_y = cam
        ix, iy = int(np.floor(cam_x)), int(np.floor(cam_y))
        fx, fy = cam_x - ix, cam_y - iy
        cw, ch = C.CANVAS_W, C.CANVAS_H

        self._upload(self.t_albedo, albedo)
        self._upload(self.t_emissive, emissive)
        self._upload(self.t_material, material)

        # 1. lighting -- lights are given in world space; canvas origin is (ix-1, iy-1)
        self._set_lights(lights, ix, iy)
        p = self.p_light
        p["u_albedo"].value, p["u_emissive"].value, p["u_material"].value = 0, 1, 2
        p["u_canvas"].value = (cw, ch)
        p["u_ambient"].value = post.ambient
        p["u_time"].value = self.time
        p["u_reflect"].value = post.reflect
        self.t_albedo.use(0)
        self.t_emissive.use(1)
        self.t_material.use(2)
        self.f_lit.use()
        ctx.viewport = (0, 0, cw, ch)
        ctx.disable(moderngl.BLEND)
        self.va_light.render(moderngl.TRIANGLE_STRIP)

        # 2. bright extract -> half res
        p = self.p_bright
        p["u_lit"].value, p["u_emissive"].value = 0, 1
        p["u_texel"].value = (1.0 / cw, 1.0 / ch)
        self.t_lit.use(0)
        self.t_emissive.use(1)
        self.f_ha.use()
        ctx.viewport = (0, 0, cw // 2, ch // 2)
        self.va_bright.render(moderngl.TRIANGLE_STRIP)

        # 3. blur: half (ha <-> hb), then quarter (qa <-> qb)
        def blur(src_a, fb_b, t_b, fb_a, size):
            w, h = size
            self.p_blur["u_src"].value = 0
            ctx.viewport = (0, 0, w, h)
            src_a.use(0)
            self.p_blur["u_dir"].value = (1.0 / w, 0.0)
            fb_b.use()
            self.va_blur.render(moderngl.TRIANGLE_STRIP)
            t_b.use(0)
            self.p_blur["u_dir"].value = (0.0, 1.0 / h)
            fb_a.use()
            self.va_blur.render(moderngl.TRIANGLE_STRIP)

        blur(self.t_ha, self.f_hb, self.t_hb, self.f_ha, (cw // 2, ch // 2))
        # downsample half -> quarter via a blur pass reading the half texture
        self.p_blur["u_src"].value = 0
        ctx.viewport = (0, 0, cw // 4, ch // 4)
        self.t_ha.use(0)
        self.p_blur["u_dir"].value = (2.0 / (cw // 2), 0.0)
        self.f_qb.use()
        self.va_blur.render(moderngl.TRIANGLE_STRIP)
        self.t_qb.use(0)
        self.p_blur["u_dir"].value = (0.0, 2.0 / (ch // 2))
        self.f_qa.use()
        self.va_blur.render(moderngl.TRIANGLE_STRIP)
        blur(self.t_qa, self.f_qb, self.t_qb, self.f_qa, (cw // 4, ch // 4))

        # 4. final composite to the screen
        ctx.screen.use()
        ww, wh = self.window_size
        ctx.viewport = (0, 0, ww, wh)
        ctx.clear(0.0, 0.0, 0.0)
        vx, vy, vw, vh = self.view_rect()
        ctx.viewport = (vx, wh - vy - vh, vw, vh)
        p = self.p_final
        p["u_lit"].value, p["u_bloom_a"].value, p["u_bloom_b"].value = 0, 1, 2
        p["u_canvas"].value = (cw, ch)
        p["u_view"].value = (C.VIEW_W, C.VIEW_H)
        p["u_frac"].value = (fx, fy)
        p["u_cam"].value = (cam_x, cam_y)
        p["u_time"].value = self.time
        p["u_fog"].value = post.fog
        p["u_fog_color"].value = post.fog_color
        p["u_bloom"].value = post.bloom
        p["u_exposure"].value = post.exposure
        p["u_flash"].value = post.flash
        p["u_flash_color"].value = post.flash_color
        p["u_fade"].value = post.fade
        p["u_hurt"].value = post.hurt
        p["u_grain"].value = post.grain
        p["u_saturation"].value = post.saturation
        self.t_lit.use(0)
        self.t_ha.use(1)
        self.t_qa.use(2)
        self.va_final.render(moderngl.TRIANGLE_STRIP)

        # 5. quads + UI (UI pixel space -> view NDC)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        for q in quads:
            if not q.above_ui:
                self._draw_quad(q)
        if ui is not None:
            self._upload(self.t_ui, ui)
            self._draw_tex(self.t_ui, (0, 0, C.UI_W, C.UI_H), (0, 0, 1, 1), (1, 1, 1, 1))
        for q in quads:
            if q.above_ui:
                self._draw_quad(q)
        ctx.disable(moderngl.BLEND)

    def _draw_quad(self, q: Quad) -> None:
        t = self.textures.get(q.texture_key)
        if t is None:
            return
        self._draw_tex(t, q.rect, q.src, (*q.tint, q.alpha))

    def _draw_tex(self, t, rect, src, tint) -> None:
        x, y, w, h = rect
        nx = x / C.UI_W * 2 - 1
        nw = w / C.UI_W * 2
        ny = 1 - (y + h) / C.UI_H * 2
        nh = h / C.UI_H * 2
        self.p_quad["u_rect"].value = (nx, ny, nw, nh)
        self.p_quad["u_src"].value = src
        self.p_quad["u_tint"].value = tint
        self.p_quad["u_tex"].value = 0
        t.use(0)
        self.va_quad.render(moderngl.TRIANGLE_STRIP)

    def read_screen(self) -> pygame.Surface:
        """Grab the current back buffer view area as a pygame surface (for screenshots)."""
        vx, vy, vw, vh = self.view_rect()
        wh = self.window_size[1]
        data = self.ctx.screen.read(viewport=(vx, wh - vy - vh, vw, vh), components=3)
        surf = pygame.image.frombytes(data, (vw, vh), "RGB")
        return pygame.transform.flip(surf, False, True)
