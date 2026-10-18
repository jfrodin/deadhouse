"""Conversation portraits, "ink and light" style.

Faces are built from hand-placed Bezier shapes (designed on a 600x760 canvas),
rendered with 3x supersampling and downsampled for clean edges. Lighting is
painted as hard-edged shapes: a warm key light from the right, a neon rim on
the left, violet shadows. Expressions are parameters on brows, lids and mouth.
"""
from __future__ import annotations

import math
import os

import numpy as np
import pygame

PW, PH = 600, 760
SS = 3


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


# ----------------------------------------------------------------------------- path helpers
def bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0]
        y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]
        out.append((x, y))
    return out


def path(*segs):
    """segs: (x, y) start, then tuples of 3 points (cubic) or 1 point (line)."""
    pts = [segs[0]]
    cur = segs[0]
    for s in segs[1:]:
        if len(s) == 3:
            pts += bez(cur, s[0], s[1], s[2])[1:]
            cur = s[2]
        else:
            pts.append(s[0])
            cur = s[0]
    return pts


class Canvas:
    def __init__(self):
        self.s = pygame.Surface((PW * SS, PH * SS), pygame.SRCALPHA)

    def fill(self, pts, color):
        if len(pts) >= 3:
            pygame.draw.polygon(self.s, color, [(x * SS, y * SS) for x, y in pts])

    def stroke(self, pts, width, color, taper=False):
        n = len(pts)
        for i in range(n - 1):
            w = width
            if taper:
                t = i / max(1, n - 2)
                w = max(0.6, width * math.sin(math.pi * min(1.0, max(0.0, t))) ** 0.6)
            a = (pts[i][0] * SS, pts[i][1] * SS)
            b = (pts[i + 1][0] * SS, pts[i + 1][1] * SS)
            r = max(1, int(w * SS / 2))
            pygame.draw.line(self.s, color, a, b, max(1, int(w * SS)))
            pygame.draw.circle(self.s, color, (int(b[0]), int(b[1])), r)

    def circle(self, x, y, r, color):
        pygame.draw.circle(self.s, color, (int(x * SS), int(y * SS)), int(r * SS))

    def blend_circle(self, x, y, r, color):
        """Alpha-blended circle (pygame.draw writes alpha instead of blending)."""
        R = max(1, int(r * SS))
        t = pygame.Surface((R * 2 + 2, R * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(t, color, (R + 1, R + 1), R)
        self.s.blit(t, (int(x * SS) - R - 1, int(y * SS) - R - 1))

    def blend_ellipse(self, x, y, w, h, color):
        t = pygame.Surface((int(w * SS) + 2, int(h * SS) + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(t, color, t.get_rect())
        self.s.blit(t, (int((x - w / 2) * SS), int((y - h / 2) * SS)))

    def blend_fill(self, pts, color):
        t = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(t, color, [(x * SS, y * SS) for x, y in pts])
        self.s.blit(t, (0, 0))

    def ellipse(self, x, y, w, h, color):
        pygame.draw.ellipse(self.s, color, pygame.Rect(int((x - w / 2) * SS), int((y - h / 2) * SS), int(w * SS), int(h * SS)))

    def clip_fill(self, mask_pts, pts, color):
        """Fill pts but only inside mask_pts."""
        layer = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(layer, color, [(x * SS, y * SS) for x, y in pts])
        m = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(m, (255, 255, 255, 255), [(x * SS, y * SS) for x, y in mask_pts])
        la = pygame.surfarray.pixels_alpha(layer)
        ma = pygame.surfarray.array_alpha(m)
        la[:] = np.minimum(la, ma)
        del la
        self.s.blit(layer, (0, 0))

    def finish(self, rng, grain=0.06) -> pygame.Surface:
        out = pygame.transform.smoothscale(self.s, (PW, PH))
        rgb = pygame.surfarray.pixels3d(out)
        a = pygame.surfarray.pixels_alpha(out)
        n = rng.normal(1.0, grain, size=rgb.shape[:2])[..., None]
        rgb[:] = np.clip(rgb.astype(np.float32) * n, 0, 255).astype(np.uint8)
        del rgb, a
        return out


# ----------------------------------------------------------------------------- Vivienne
VIV = dict(
    skin_l=hexc("e6bca6"), skin_m=hexc("c48a7a"), skin_s=hexc("74404e"), skin_d=hexc("3c1e30"),
    rim=hexc("ff5cb8"), key=hexc("ffe2c8"),
    hair=hexc("120e16"), hair_l=hexc("4a3640"), hair_rim=hexc("9a2a74"),
    lip_u=hexc("7e1a36"), lip_l=hexc("a42c48"), lip_h=hexc("e07a8e"),
    iris=hexc("24161a"), white=hexc("dccac2"), white_s=hexc("a48a8c"), liner=hexc("0c080e"),
    gown=hexc("140c16"), gown_l=hexc("3e2c40"), fur=hexc("e8e0d6"), fur_m=hexc("b6aaa2"), fur_s=hexc("6c5c66"),
    pearl=hexc("f2ece6"), bg=hexc("2a1428", 0),
)

EXPR = {
    #          brow L, brow R, lid (upper, 0 = open), lower lid, mouth corner L, R, mouth open, head tilt
    "neutral": dict(bl=0, br=0, lid=0.36, low=0.0, ml=0, mr=0, mo=0.0, tilt=0.0, gaze=(2, 0)),
    "amused": dict(bl=1, br=-10, lid=0.44, low=0.35, ml=-1, mr=-10, mo=0.0, tilt=-3.0, gaze=(5, 0)),
    "cold": dict(bl=6, br=5, lid=0.6, low=0.4, ml=5, mr=5, mo=0.0, tilt=2.0, gaze=(0, 1)),
    "warm": dict(bl=-6, br=-6, lid=0.26, low=0.25, ml=-6, mr=-6, mo=4.0, tilt=-1.5, gaze=(2, -1)),
}


def vivienne(expr: str, rng) -> pygame.Surface:
    c = VIV
    e = EXPR[expr]
    cv = Canvas()

    def T(x, y):
        """Small head tilt around the chin for expressions."""
        a = math.radians(e["tilt"])
        cx, cy = 300, 470
        if y > 480:
            return x, y
        dx, dy = x - cx, y - cy
        return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)

    def P(*segs):
        return [T(x, y) for x, y in path(*segs)]

    # soft dark haze behind (separates her from the street)
    for k in range(14):
        r = 360 - k * 18
        cv.blend_ellipse(300, 440, r * 2, r * 2.15, (24, 10, 26, 14))

    # ---- hair, back mass
    hair_back = P((300, 70), ((410, 66), (468, 150), (458, 262)), ((452, 350), (430, 420), (398, 458)),
                  ((380, 470), (356, 452), (360, 430)), ((300, 430),), ((240, 430),),
                  ((244, 452), (220, 470), (202, 458)), ((168, 420), (146, 350), (144, 262)),
                  ((140, 150), (196, 72), (300, 70)))
    cv.fill(hair_back, c["hair"])

    # ---- neck, shoulders, chest
    body = path((256, 412), ((256, 462), (252, 494), (240, 520)), ((198, 546), (122, 566), (56, 616)),
                ((44, 760),), ((558, 760),), ((550, 620),), ((476, 572), (404, 548), (364, 522)),
                ((350, 494), (346, 462), (346, 412)))
    cv.fill(body, c["skin_m"])
    # key light on the right of the neck and the right shoulder
    cv.clip_fill(body, path((316, 440), ((334, 474), (346, 512), (374, 536)), ((440, 566), (520, 590), (560, 630)),
                            ((560, 760),), ((410, 760),), ((372, 650), (326, 590), (316, 440))), c["skin_l"])
    # shadow under the jaw
    cv.fill(path((254, 430), ((282, 484), (330, 484), (350, 430)), ((352, 470), (338, 500), (300, 504)),
                 ((262, 500), (250, 470), (254, 430))), c["skin_s"])
    # collarbones and the hollow of the throat
    cv.stroke(path((176, 584), ((216, 570), (254, 572), (284, 588))), 2.2, c["skin_s"], taper=True)
    cv.stroke(path((326, 588), ((358, 572), (398, 570), (438, 582))), 2.0, c["skin_s"], taper=True)
    cv.ellipse(300, 586, 16, 7, c["skin_s"])
    # neck tendon shadow
    cv.stroke(path((270, 470), ((266, 504), (264, 530), (280, 566))), 2.4, c["skin_s"], taper=True)

    # ---- gown: black silk, straight neckline
    gown = path((30, 664), ((150, 636), (232, 654), (300, 670)), ((370, 654), (452, 634), (572, 662)),
                ((572, 760),), ((30, 760),))
    cv.fill(gown, c["gown"])
    cv.stroke(path((40, 664), ((150, 638), (232, 656), (300, 672)), ((370, 656), (452, 636), (562, 662))), 2.5, c["gown_l"])
    cv.clip_fill(gown, path((380, 676), ((430, 664), (470, 664), (520, 674)), ((500, 760),), ((420, 760),)), c["gown_l"])
    # a fine chain with a pendant
    cv.stroke(path((258, 520), ((276, 600), (324, 600), (342, 520))), 1.2, hexc("c8b088"))
    cv.circle(300, 598, 5, hexc("c8b088"))
    cv.circle(299, 597, 2, hexc("fff0d0"))

    # ---- fur stole draped over both arms
    for side in (-1, 1):
        lit_side = side > 0
        cx = 300 + side * 222
        top = 572
        spine = path((cx - side * 112, 760), ((cx - side * 96, 680), (cx - side * 64, top), (cx + side * 14, top - 6)),
                     ((cx + side * 74, top - 2), (cx + side * 100, 650), (cx + side * 104, 760)))
        # tufted silhouette: little pointed locks all along the edge
        tuft = []
        for i in range(len(spine) - 1):
            (x0, y0), (x1, y1) = spine[i], spine[i + 1]
            nx, ny = -(y1 - y0), (x1 - x0)
            d = math.hypot(nx, ny) or 1
            nx, ny = nx / d * side, ny / d * side
            tuft.append((x0, y0))
            k = 5 + 3 * math.sin(i * 2.7)
            tuft.append(((x0 + x1) / 2 - nx * k, (y0 + y1) / 2 - ny * k))
        tuft.append(spine[-1])
        base = c["fur"] if lit_side else hexc("cbc0b6")
        cv.fill(tuft, base)
        # inner shading: a darker band toward the body, lighter crest on top
        inner = [(x + side * 22, y + 26) for x, y in spine]
        cv.clip_fill(tuft, inner, c["fur_m"] if lit_side else c["fur_s"])
        crest = [(x - side * 2, y + 4) for x, y in spine[: len(spine) // 2 + 4]]
        # tuft strokes: small curved V-shapes, the way illustrators draw fur
        for k in range(55):
            t = rng.uniform(0.05, 0.95)
            i = int(t * (len(spine) - 1))
            sx, sy = spine[i]
            depth = rng.uniform(8, 120)
            x = sx + side * depth * 0.3
            y = sy + depth
            if y > 752:
                continue
            col = c["fur_s"] if not lit_side or rng.random() < 0.4 else c["fur_m"]
            ln = rng.uniform(6, 11)
            cv.stroke([(x - 3, y - ln * 0.6), (x, y), (x + 3, y - ln * 0.6)], 1.3, col)
        for k in range(18):
            i = int(rng.uniform(0.1, 0.9) * (len(spine) - 1))
            x, y = spine[i]
            cv.stroke([(x, y + 3), (x + side * 2, y + 9)], 1.2, hexc("fffaf2") if lit_side else hexc("ece4da"))
    # neon rim on the left shoulder fur
    cv.stroke(path((66, 640), ((96, 596), (140, 574), (196, 566))), 2.6, c["rim"], taper=True)

    # ---- face
    face = P((208, 250), ((205, 300), (212, 370), (240, 414)), ((262, 446), (284, 468), (302, 470)),
             ((322, 469), (346, 450), (366, 414)), ((390, 372), (396, 300), (392, 250)),
             ((388, 200), (350, 166), (300, 166)), ((250, 168), (212, 200), (208, 250)))
    cv.fill(face, c["skin_l"])
    # side plane of the face turned away from the key light
    cv.clip_fill(face, P((206, 220), ((214, 290), (222, 350), (244, 392)), ((260, 424), (276, 452), (300, 472)),
                         ((276, 446), (260, 414), (258, 388)), ((262, 360), (246, 330), (240, 300)),
                         ((234, 268), (236, 244), (246, 210)), ((230, 190), (214, 200), (206, 220))), c["skin_m"])
    # eye sockets under the brow ridge
    cv.clip_fill(face, P((228, 286), ((246, 270), (280, 272), (294, 292)), ((280, 290), (250, 290), (228, 286))), c["skin_m"])
    cv.clip_fill(face, P((318, 292), ((332, 276), (360, 272), (380, 286)), ((362, 290), (334, 292), (318, 292))), hexc("d4a492"))
    # the nose casts its shadow down and to the left
    cv.clip_fill(face, P((298, 290), ((294, 320), (290, 344), (284, 372)), ((276, 380), (268, 384), (270, 392)),
                         ((286, 392), (300, 388), (306, 380)), ((298, 360), (300, 326), (302, 292))), c["skin_m"])
    # cheekbone hollow, deepest shadow
    cv.clip_fill(face, P((214, 300), ((226, 330), (240, 356), (252, 390)), ((244, 404), (232, 398), (224, 382)),
                         ((214, 356), (210, 328), (214, 300))), c["skin_s"])
    # philtrum and under-lip shadows
    cv.clip_fill(face, P((294, 392), ((298, 398), (306, 398), (310, 392)), ((308, 404), (296, 404), (294, 392))), c["skin_m"])
    cv.clip_fill(face, P((280, 446), ((296, 452), (312, 452), (326, 444)), ((316, 458), (290, 458), (280, 446))), c["skin_m"])
    # key highlight along the lit cheekbone and down the bridge of the nose
    cv.clip_fill(face, P((338, 340), ((356, 330), (378, 334), (390, 352)), ((372, 350), (354, 346), (338, 340))), hexc("f0cab6"))
    cv.stroke(P((304, 300), ((306, 320), (308, 340), (308, 358))), 2.2, c["key"], taper=True)
    # neon rim along the dark contour
    cv.stroke(P((210, 270), ((210, 330), (218, 380), (244, 418)), ((264, 448), (284, 464), (298, 468))), 3.0, c["rim"], taper=True)

    # ---- nose (shadow side line, nostrils, tip highlight)
    cv.stroke(P((296, 300), ((292, 330), (288, 352), (286, 372))), 2.0, c["skin_s"], taper=True)
    cv.fill(P((282, 372), ((290, 384), (300, 388), (312, 384)), ((318, 380), (312, 376), (306, 380)),
              ((300, 382), (292, 380), (282, 372))), c["skin_s"])
    cv.circle(*T(306, 368), 3, c["key"])
    cv.ellipse(*T(291, 382), 7, 3, c["skin_d"])
    cv.ellipse(*T(313, 381), 6, 3, c["skin_d"])

    # ---- eyes
    def eye(cx, cy, side, lit_side):
        w = 30
        white = P((cx - w, cy), ((cx - 15, cy - 15), (cx + 12, cy - 17), (cx + w, cy - 3)),
                  ((cx + 12, cy + 10), (cx - 12, cy + 10), (cx - w, cy)))
        cv.fill(white, c["white"] if lit_side else c["white_s"])
        gx, gy = e["gaze"]
        iris = []
        for i in range(32):
            a = i / 32 * 2 * math.pi
            iris.append(T(cx + gx + math.cos(a) * 12, cy + gy - 1 + math.sin(a) * 12))
        cv.clip_fill(white, iris, c["iris"])
        # heavy upper lid: skin covers the top of the iris
        lid_drop = e["lid"] * 16
        lid = P((cx - w - 2, cy - 1), ((cx - 15, cy - 16), (cx + 12, cy - 18), (cx + w + 2, cy - 4)),
                ((cx + 12, cy - 18 + lid_drop * 1.2), (cx - 15, cy - 16 + lid_drop * 1.2), (cx - w - 2, cy - 1)))
        cv.fill(lid, c["skin_l"] if lit_side else c["skin_m"])
        # lower lid
        low = e["low"] * 7
        if low > 0:
            cv.fill(P((cx - w, cy + 1), ((cx - 12, cy + 10 - low), (cx + 12, cy + 10 - low), (cx + w, cy - 2)),
                      ((cx + 12, cy + 11), (cx - 12, cy + 11), (cx - w, cy + 1))), c["skin_l"] if lit_side else c["skin_m"])
        # catchlight
        cv.circle(*T(cx + gx + 4, cy + gy - 4 + lid_drop * 0.3), 2.2, hexc("fff6f0"))
        # liner along the lid edge, winged at the outer corner
        outer = cx - w if side < 0 else cx + w
        lid_edge = P((cx - w - 2, cy - 1), ((cx - 15, cy - 16 + lid_drop * 1.2), (cx + 12, cy - 18 + lid_drop * 1.2), (cx + w + 2, cy - 4)))
        cv.stroke(lid_edge, 4.2, c["liner"])
        wing = P((outer, cy - 2 if side < 0 else cy - 5), ((outer + side * 10, cy - 8), (outer + side * 14, cy - 12), (outer + side * 18, cy - 15)))
        cv.stroke(wing, 3.0, c["liner"], taper=True)
        # crease
        cv.stroke(P((cx - w + 4, cy - 14), ((cx - 10, cy - 26), (cx + 12, cy - 27), (cx + w - 2, cy - 15))), 1.6, c["skin_s"], taper=True)
        # lower lash line
        cv.stroke(P((cx - w + 6, cy + 4), ((cx - 10, cy + 10), (cx + 10, cy + 10), (cx + w - 4, cy + 1))), 1.2, c["skin_s"], taper=True)

    eye(262, 304, -1, False)
    eye(348, 304, 1, True)

    # ---- brows (thin, arched, expression-driven)
    def brow(x0, xp, x1, y0, yp, y1, dy, lit_side):
        cv.stroke(P((x0, y0 + dy * 0.4), ((xp - 14, yp - 2 + dy), (xp + 10, yp - 2 + dy), (x1, y1 + dy * 0.6))), 4.2, c["hair"], taper=True)
    brow(228, 262, 294, 278, 262, 270, e["bl"], False)
    brow(314, 346, 384, 270, 258, 280, e["br"], True)

    # ---- mouth
    mo = e["mo"]
    ml, mr = e["ml"], e["mr"]
    lx, rx, my = 270, 336, 422
    upper = P((lx, my + ml), ((284, my - 10), (294, my - 13), (303, my - 6)), ((312, my - 13), (324, my - 10), (rx, my + mr)),
              ((318, my + 2 + mr * 0.3), (288, my + 2 + ml * 0.3), (lx, my + ml)))
    lower = P((lx + 2, my + 1 + ml + mo), ((286, my + 20 + mo), (318, my + 20 + mo), (rx - 2, my + 1 + mr + mo)),
              ((318, my + 4 + mo), (288, my + 4 + mo), (lx + 2, my + 1 + ml + mo)))
    if mo > 0:
        cv.fill(P((lx + 4, my + ml), ((290, my + 1), (316, my + 1), (rx - 4, my + mr)),
                  ((316, my + mo + 3), (290, my + mo + 3), (lx + 4, my + ml))), c["skin_d"])
    cv.fill(lower, c["lip_l"])
    cv.fill(upper, c["lip_u"])
    cv.stroke(P((lx, my + ml), ((290, my + 2 + mo * 0.5), (316, my + 2 + mo * 0.5), (rx, my + mr))), 2.0, hexc("3a0a18"))
    cv.ellipse(*T(314, my + 10 + mo), 14, 4, c["lip_h"])
    # corner shadows (the amused smile lives here)
    for (x, y, d) in ((lx - 2, my + ml, -1), (rx + 2, my + mr, 1)):
        cv.stroke(P((x, y), ((x + d * 4, y - 3), (x + d * 6, y - 1), (x + d * 7, y + 2))), 1.4, c["skin_s"], taper=True)
    # beauty mark
    cv.circle(*T(266, 398), 2.4, hexc("3a1e24"))

    # ---- hair, front pieces (framing the face) and the finger wave
    left = P((214, 160), ((184, 230), (176, 330), (200, 420)), ((210, 448), (232, 458), (246, 446)),
             ((226, 404), (214, 322), (226, 238)), ((236, 200), (226, 176), (214, 160)))
    right = P((386, 166), ((420, 236), (428, 340), (402, 426)), ((392, 450), (370, 458), (358, 446)),
              ((380, 404), (392, 322), (380, 240)), ((372, 204), (380, 180), (386, 166)))
    cv.fill(left, c["hair"])
    cv.fill(right, c["hair"])
    wave = P((232, 108), ((300, 88), (386, 100), (426, 168)), ((404, 160), (366, 152), (338, 176)),
             ((318, 194), (296, 204), (272, 200)), ((300, 176), (278, 146), (238, 156)), ((224, 160), (222, 120), (232, 108)))
    cv.fill(wave, c["hair"])
    top = P((300, 70), ((380, 70), (436, 120), (446, 196)), ((420, 150), (380, 110), (300, 104)),
            ((240, 104), (190, 140), (172, 210)), ((176, 130), (226, 72), (300, 70)))
    cv.fill(top, c["hair"])
    # warm highlights along the wave crests (lacquered shine), neon rim on the dark side
    cv.fill(P((262, 112), ((310, 94), (372, 104), (408, 146)), ((380, 126), (330, 112), (262, 112))), c["hair_l"])
    cv.fill(P((300, 182), ((322, 168), (346, 160), (372, 160)), ((352, 170), (330, 176), (300, 182))), c["hair_l"])
    cv.fill(P((396, 214), ((410, 260), (414, 320), (404, 380)), ((402, 320), (400, 260), (396, 214))), c["hair_l"])
    cv.stroke(P((250, 112), ((300, 96), (370, 106), (410, 150))), 3.0, c["hair_l"], taper=True)
    cv.stroke(P((282, 190), ((310, 178), (334, 166), (366, 158))), 2.5, c["hair_l"], taper=True)
    cv.stroke(P((390, 190), ((414, 250), (418, 330), (400, 410))), 2.5, c["hair_l"], taper=True)
    cv.stroke(P((176, 220), ((168, 290), (172, 360), (196, 424))), 3.0, c["hair_rim"], taper=True)
    cv.stroke(P((190, 130), ((214, 96), (250, 80), (290, 76))), 2.0, c["hair_rim"], taper=True)

    # ---- pearl drop earring, just visible under the left bob
    cv.stroke([T(230, 446), T(230, 462)], 1.2, hexc("c8b088"))
    cv.circle(*T(230, 470), 7, c["pearl"])
    cv.circle(*T(228, 467), 2.2, hexc("ffffff"))
    cv.circle(*T(233, 473), 2, hexc("b0a8b0"))

    # ---- cigarette smoke curling up from below the frame
    for strand in range(2):
        for i in range(90):
            t = i / 89
            x = 96 + strand * 22 + math.sin(t * 6.5 + strand) * 22 * t + t * 46
            y = 760 - t * 470
            cv.blend_circle(x, y, 3 + t * 9, (205, 200, 215, int(16 * (1 - t) ** 1.2)))

    out = cv.finish(rng, 0.05)
    return out


def build(out_dir: str) -> list[str]:
    d = os.path.join(out_dir, "portraits")
    os.makedirs(d, exist_ok=True)
    files = []
    for ex in EXPR:
        rng = np.random.default_rng(1954)
        img = vivienne(ex, rng)
        p = os.path.join(d, f"vivienne_{ex}.png")
        pygame.image.save(img, p)
        files.append(p)
    return files
