"""Procedural character rig -> sprite sheets.

Each character = hand-drawn head templates + a parametric body (legs/torso/arms
drawn as chunky pixel capsules with 2-bone IK), dressed by an outfit spec and
posed by per-animation pose functions. A shading pass adds form, an outline
pass gives a consistent ink line. Runtime attaches weapons/lanterns to the
hand anchors exported per frame.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pygame

from . import palette as P
from .char_specs import ANIM_SETS, BODIES, CHARACTERS, HEADS, SKIN
from .gfx import mix, outline, shade, surf

FW, FH = 48, 48
AX, AY = 24, 45  # anchor (feet) inside a frame
COLS = 16

ANIMS = {
    # name: (frames, fps, loop)
    "idle": (4, 3, True), "walk": (6, 10, True), "run": (6, 14, True),
    "attack1": (4, 18, False), "attack2": (4, 18, False), "attack3": (5, 16, False),
    "heavy": (6, 12, False), "dodge": (4, 16, False), "hit": (2, 10, False), "stagger": (4, 8, True),
    "down": (5, 10, False), "throw": (4, 14, False), "aim": (1, 1, True), "shoot": (3, 18, False),
    "climb": (4, 8, True), "interact": (3, 10, False), "takedown": (4, 8, False), "break": (4, 12, False),
    "talk": (4, 4, True), "smoke": (8, 4, True), "windup": (2, 6, True), "blinded": (4, 8, True),
    "match": (4, 6, True), "takedown_victim": (4, 8, False),
}


# ----------------------------------------------------------------------------- geometry
def ik(root, target, a, b, bend):
    """2-bone IK: returns joint position. bend: +1/-1 chooses the elbow/knee side."""
    rx, ry = root
    tx, ty = target
    dx, dy = tx - rx, ty - ry
    d = math.hypot(dx, dy)
    d = max(1e-3, min(d, a + b - 1e-3))
    cos_a = (a * a + d * d - b * b) / (2 * a * d)
    cos_a = max(-1.0, min(1.0, cos_a))
    ang = math.atan2(dy, dx) + bend * math.acos(cos_a)
    return rx + a * math.cos(ang), ry + a * math.sin(ang)


def capsule(s, p0, p1, w, color):
    """Chunky pixel limb: squares of size w stepped along the segment."""
    x0, y0 = p0
    x1, y1 = p1
    n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) * 2))
    half = (w - 1) / 2
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        s.fill(color, pygame.Rect(int(round(x - half)), int(round(y - half)), w, w))


def A(p):
    return (AX + p[0], AY + p[1])


# ----------------------------------------------------------------------------- poses
def base_pose(view, body):
    L, T = body["leg"], body["torso"]
    hw = body["hw"]
    fx = max(1.5, hw / 2 - 1)
    return {
        "dy": 0.0, "lean": 0.0, "hem": 0.0,
        "foot_l": (-fx if view != "N" else fx, 0.0) if view != "E" else (-1.0, 0.0),
        "foot_r": (fx if view != "N" else -fx, 0.0) if view != "E" else (1.0, 0.0),
        "hand_l": None, "hand_r": None,  # None = resting
        "head": (0.0, 0.0), "angle": 90.0, "weapon_behind": view == "N", "lying": 0, "arms_back": False,
    }


def rest_hands(view, body, pose):
    """Default hanging hand positions relative to the anchor."""
    L, T, sw = body["leg"], body["torso"], body["sw"]
    shy = -L - T + pose["dy"]
    if view == "E":
        return (pose["lean"] - 1, shy + 11), (pose["lean"] + 1, shy + 11)
    side = 1 if view == "S" else -1
    # S view: character's right hand is on screen left
    hr = (-side * (sw / 2 + 0.5), shy + 10.5)
    hl = (side * (sw / 2 + 0.5), shy + 10.5)
    return hl, hr


def pose_for(anim, view, i, n, body):
    p = base_pose(view, body)
    L, T, sw = body["leg"], body["torso"], body["sw"]
    t = i / n
    tau = 2 * math.pi * t
    shy = -L - T  # shoulder height
    fwd = {"S": (0, 1), "N": (0, -1), "E": (1, 0)}[view]
    side = 1 if view == "S" else -1

    def hand_fwd(dist, height, lateral=0.0):
        """A point in front of the body (in facing direction)."""
        if view == "E":
            return (p["lean"] + dist, shy + height)
        return (-side * lateral if view == "S" else side * lateral, shy + height + fwd[1] * dist * 0.6)

    if anim == "idle":
        p["dy"] = 1.0 if i in (2, 3) else 0.0
    elif anim in ("walk", "run"):
        run = anim == "run"
        lift = 3.5 if run else 2.6
        # body drops at each foot contact, rises on the passing pose
        p["dy"] = round(abs(math.cos(tau)) * (1.6 if run else 1.2))
        if view == "E":
            stride = 7.5 if run else 6.5
            fl = (math.sin(tau) * stride, -max(0.0, math.cos(tau)) * lift)
            fr = (math.sin(tau + math.pi) * stride, -max(0.0, math.cos(tau + math.pi)) * lift)
            p["foot_l"], p["foot_r"] = fl, fr
            p["lean"] = 2.0 if run else 0.8
            p["hem"] = (-2.5 if run else -1.5) - abs(math.sin(tau)) * 1.5  # coat flares behind the stride
            sh = shy + p["dy"]
            swing = 5.0 if run else 4.5
            p["hand_l"] = (p["lean"] + math.sin(tau + math.pi) * swing, sh + (8 if run else 11))
            p["hand_r"] = (p["lean"] + math.sin(tau) * swing, sh + (8 if run else 10.5))
        else:
            fx = max(1.5, body["hw"] / 2 - 1)
            sgn = 1 if view == "S" else -1
            ll = max(0.0, math.sin(tau)) * lift
            rl = max(0.0, math.sin(tau + math.pi)) * lift
            p["foot_l"] = (sgn * -fx, -ll + math.cos(tau) * sgn * 1.6)
            p["foot_r"] = (sgn * fx, -rl - math.cos(tau) * sgn * 1.6)
            p["lean"] = math.sin(tau) * 0.7  # weight shifts side to side
            p["hem"] = math.sin(tau) * 2.0
            hl, hr = rest_hands(view, body, p)
            sw_amt = 3.0 if run else 2.6
            p["hand_l"] = (hl[0] + math.sin(tau) * 0.8, hl[1] + math.sin(tau) * sw_amt - (3 if run else 0))
            p["hand_r"] = (hr[0] - math.sin(tau) * 0.8, hr[1] - math.sin(tau) * sw_amt - (3 if run else 0))
    elif anim in ("attack1", "attack2"):
        flip = 1 if anim == "attack1" else -1
        keys = [(-6, -2), (6, 6), (5, 9), (0, 10)]  # (lateral, height) in "slash plane"
        lat, h = keys[i]
        if view == "E":
            seq = [(-4, 2), (9, 5), (7, 9), (2, 11)]
            dx, hh = seq[i]
            p["hand_r"] = (dx, shy + hh if flip > 0 else shy + (12 - hh))
            p["lean"] = [-1, 2, 1, 0][i]
            p["angle"] = [-150, 10, 60, 90][i] if flip > 0 else [150, -10, -60, -90][i]
        else:
            lat = lat * flip
            p["hand_r"] = (-side * -lat if view == "S" else side * -lat, shy + 4 + [0, 6, 8, 9][i] * (1 if view == "S" else -0.4))
            p["angle"] = (90 + [-80, 0, 40, 10][i] * flip) if view == "S" else (-90 + [-80, 0, 40, 10][i] * flip)
        p["dy"] = [0, 1, 1, 0][i]
    elif anim == "attack3":
        # lunge stab
        lunge = [0, 2, 5, 5, 2][i]
        if view == "E":
            p["lean"] = lunge * 0.6
            p["foot_r"] = (lunge, 0.0)
            p["foot_l"] = (-2.0, 0.0)
            p["hand_r"] = (p["lean"] + [-2, 2, 11, 10, 4][i], shy + 7)
            p["angle"] = 0
        else:
            p["hand_r"] = (-side * 1.5 if view == "S" else side * 1.5, shy + 6 + fwd[1] * [0, 2, 9, 8, 3][i])
            p["angle"] = 90 if view == "S" else -90
            p["foot_r"] = (p["foot_r"][0], fwd[1] * lunge * 0.6)
        p["dy"] = [0, 1, 2, 2, 1][i]
    elif anim == "heavy":
        stage = [0, 1, 1, 2, 3, 4][i]
        if view == "E":
            seq = [(-2, -1), (-4, -7), (-4, -8), (10, 6), (9, 11), (3, 11)]
            dx, hh = seq[i]
            p["hand_r"] = (dx, shy + hh)
            p["hand_l"] = (dx - 1, shy + hh + 1)
            p["angle"] = [-120, -160, -165, 20, 80, 90][i]
            p["lean"] = [0, -1, -1, 3, 2, 0][i]
        else:
            seq = [(0, 0), (0, -9), (0, -10), (0, 9), (0, 12), (0, 10)]
            _, hh = seq[i]
            lat = 1.5
            p["hand_r"] = (-side * lat if view == "S" else side * lat, shy + 4 + hh * (1 if view == "S" else -0.5))
            p["hand_l"] = (side * lat if view == "S" else -side * lat, shy + 5 + hh * (1 if view == "S" else -0.5))
            p["angle"] = [180, -90, -90, 90, 90, 90][i] if view == "S" else [0, 90, 90, -90, -90, -90][i]
        p["dy"] = [0, 0, 0, 2, 3, 1][i]
    elif anim == "dodge":
        p["dy"] = [2, 4, 4, 1][i]
        p["lean"] = [2, 3, 2, 0][i] if view == "E" else 0
        p["hem"] = [-2, -4, -3, -1][i]
        if view == "E":
            p["foot_l"] = (-5.0, 0.0)
            p["foot_r"] = (4.0, 0.0)
        hl, hr = rest_hands(view, body, p)
        p["hand_l"] = (hl[0] - 1, hl[1] - 3)
        p["hand_r"] = (hr[0] + 1, hr[1] - 3)
    elif anim == "hit":
        p["lean"] = -2.0 if view == "E" else 0.0
        p["head"] = (-1.0 if view == "E" else 0.0, -1.0 if i == 0 else 0.0)
        p["dy"] = 1.0
        hl, hr = rest_hands(view, body, p)
        p["hand_l"] = (hl[0], hl[1] - 4)
        p["hand_r"] = (hr[0], hr[1] - 4)
    elif anim == "stagger":
        p["lean"] = [-2, -1, -2, -3][i] if view == "E" else 0
        p["head"] = ([-1, 0, 1, 0][i], 1.0)
        p["dy"] = [1, 2, 1, 2][i]
        p["foot_l"] = (p["foot_l"][0] - [0, 1, 0, -1][i], 0.0)
        hl, hr = rest_hands(view, body, p)
        p["hand_l"] = (hl[0] + [0, 1, 2, 1][i] * (1 if view != "N" else -1), hl[1] - 2)
        p["hand_r"] = (hr[0] - [1, 2, 1, 0][i] * (1 if view != "N" else -1), hr[1] - 1)
    elif anim in ("down", "takedown_victim"):
        p["dy"] = [2, 5, 0, 0, 0][i]
        p["lying"] = [0, 0, 1, 2, 2][i]
        hl, hr = rest_hands(view, body, p)
        p["hand_l"] = (hl[0] - 1, hl[1] - 2)
        p["hand_r"] = (hr[0] + 1, hr[1] - 2)
    elif anim == "throw":
        if view == "E":
            p["hand_r"] = [(-4, shy - 2), (-5, shy - 4), (8, shy + 2), (6, shy + 8)][i]
            p["lean"] = [0, -1, 2, 1][i]
        else:
            hh = [-3, -6, 4, 9][i]
            p["hand_r"] = (-side * 3 if view == "S" else side * 3, shy + 4 + hh * (1 if view == "S" else -0.5))
        p["angle"] = -90 if i < 2 else 45
    elif anim in ("aim", "shoot"):
        rec = [0, 1, 0][i] if anim == "shoot" else 0
        if view == "E":
            p["hand_r"] = (9 - rec, shy + 3 - rec)
            p["hand_l"] = (7 - rec, shy + 4)
            p["lean"] = -rec * 0.8
            p["angle"] = 0 - rec * 15
        else:
            p["hand_r"] = (-side * 1 if view == "S" else side * 1, shy + 3 + fwd[1] * (8 - rec * 2) * 0.7)
            p["hand_l"] = (side * 1 if view == "S" else -side * 1, shy + 4 + fwd[1] * (7 - rec * 2) * 0.7)
            p["angle"] = 90 if view == "S" else -90
    elif anim == "climb":
        up = i % 2 == 0
        p["hand_l"] = (-3, shy - 6 + (0 if up else 3))
        p["hand_r"] = (3, shy - 6 + (3 if up else 0))
        p["foot_l"] = (-2, -3.0 if up else 0.0)
        p["foot_r"] = (2, 0.0 if up else -3.0)
        p["dy"] = [0, 1, 0, 1][i]
    elif anim == "interact":
        r = [3, 7, 4][i]
        if view == "E":
            p["hand_r"] = (r + 1, shy + 7)
        else:
            p["hand_r"] = (-side * 2 if view == "S" else side * 2, shy + 6 + fwd[1] * r * 0.7)
    elif anim == "takedown":
        if view == "E":
            p["hand_r"] = (8, shy + 1)
            p["hand_l"] = (7, shy + 2 + [0, 1, 1, 0][i])
            p["lean"] = [1, 3, 3, 1][i]
        else:
            p["hand_r"] = (-side * 3 if view == "S" else side * 3, shy + 3 + fwd[1] * 6)
            p["hand_l"] = (side * 3 if view == "S" else -side * 3, shy + 3 + fwd[1] * 6)
        p["dy"] = [0, 1, 2, 1][i]
    elif anim == "break":
        if view == "E":
            p["lean"] = [1, 4, 5, 2][i]
            p["foot_r"] = ([1, 4, 6, 2][i], 0.0)
            p["hand_r"] = (p["lean"] - 1, shy + 7)
            p["hand_l"] = (p["lean"] - 2, shy + 9)
        else:
            p["dy"] = [0, 2, 2, 0][i]
            hl, hr = rest_hands(view, body, p)
            p["hand_l"] = (hl[0] * 0.5, hl[1] - 3)
            p["hand_r"] = (hr[0] * 0.5, hr[1] - 3)
    elif anim == "talk":
        hl, hr = rest_hands(view, body, p)
        g = [0, -3, -4, -2][i]
        if view == "E":
            p["hand_r"] = (hr[0] + 3 + (1 if i == 2 else 0), hr[1] + g)
        else:
            p["hand_r"] = (hr[0] * 0.6, hr[1] + g)
    elif anim == "smoke":
        hl, hr = rest_hands(view, body, p)
        lift = [0, 4, 8, 9, 9, 8, 4, 0][i]
        if view == "E":
            p["hand_r"] = (hr[0] + lift * 0.4, hr[1] - lift)
        elif view == "S":
            p["hand_r"] = (hr[0] + lift * 0.35, hr[1] - lift)
        p["dy"] = 1.0 if i in (3, 4) else 0.0
    elif anim == "windup":
        if view == "E":
            p["hand_r"] = (-5, shy + 2 + i)
            p["hand_l"] = (5, shy + 5)
            p["lean"] = -1
        else:
            p["hand_r"] = (-side * (sw / 2 + 3) if view == "S" else side * (sw / 2 + 3), shy + 1 + i)
        p["dy"] = 1.0
        p["angle"] = -120
    elif anim == "blinded":
        if view == "E":
            p["hand_r"] = (2, shy - 3)
            p["hand_l"] = (1, shy - 2)
            p["lean"] = [-1, -2, -1, 0][i]
        else:
            p["hand_r"] = (-1.5, shy - 4 + [0, 1, 0, 1][i])
            p["hand_l"] = (1.5, shy - 4 + [1, 0, 1, 0][i])
        p["dy"] = [1, 2, 1, 2][i]
        p["head"] = (0, 1)
    elif anim == "match":
        if view == "E":
            p["hand_r"] = (4, shy + 2)
            p["hand_l"] = (3, shy + 3)
        else:
            p["hand_r"] = (-1, shy + 3 + fwd[1] * 3)
            p["hand_l"] = (1, shy + 3 + fwd[1] * 3)
        p["head"] = (0, 1)
    return p


# ----------------------------------------------------------------------------- drawing
def draw_head(s, spec, view, top_left, skin, skin_d):
    rows = HEADS[spec["head"]][view]
    hair, hair_l = spec["hair"], spec.get("hair_l", spec["hair"])
    hat, hat_d = spec.get("hat", spec["hair"]), spec.get("hat_d", shade(spec.get("hat", spec["hair"]), 0.75))
    lips = spec.get("lips", mix(skin, (140, 60, 60, 255), 0.35))
    eye = P.INK
    pal = {"s": skin, "S": skin_d, "e": eye, "l": lips, "h": hair, "H": hair_l, "k": hat, "K": hat_d,
           "g": spec.get("glasses", P.INK), "m": spec.get("moust", hair), "w": (220, 215, 205, 255)}
    x0, y0 = top_left
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c != ".":
                s.set_at((x0 + i, y0 + j), pal[c])


def draw_character_frame(spec, anim, view, i, n) -> tuple[pygame.Surface, dict]:
    body = BODIES[spec["body"]]
    p = pose_for(anim, view, i, n, body)
    s = surf(FW, FH)
    L, T, sw, hw = body["leg"], body["torso"], body["sw"], body["hw"]
    skin, skin_d = SKIN[spec["skin"]]
    coat, coat_d = spec["coat"], spec["coat_d"]
    legs_c, shoes = spec["legs"], spec["shoes"]
    outfit = spec["outfit"]
    dy, lean = p["dy"], p["lean"]
    hip = (lean * 0.3, -L + dy)
    sh_y = -L - T + dy
    sh_c = (lean, sh_y)
    hl_rest, hr_rest = rest_hands(view, body, p)
    hand_l = p["hand_l"] or hl_rest
    hand_r = p["hand_r"] or hr_rest
    limb_w = 3 if body["sw"] >= 11 else 2
    leg_w = 3 if hw >= 7 else 2

    # ---- legs
    def leg(hip_pt, foot, color, bend):
        if view == "E":
            k = ik(A(hip_pt), A(foot), L / 2 + 0.5, L / 2 + 0.5, bend)
            capsule(s, A(hip_pt), k, leg_w, color)
            capsule(s, k, A((foot[0], foot[1] - 1)), leg_w, color)
        else:
            capsule(s, A(hip_pt), A((foot[0], foot[1] - 1)), leg_w, color)
        fx, fy = A(foot)
        if view == "E":
            s.fill(shoes, pygame.Rect(int(round(fx)) - 1, int(round(fy)) - 2, 4, 2))
        else:
            s.fill(shoes, pygame.Rect(int(round(fx)) - 1, int(round(fy)) - 2, 3, 2))

    gown = outfit == "gown"
    if view == "E":
        far, near = ("foot_l", "foot_r")
        leg((hip[0] - 1, hip[1]), p[far], shade(legs_c, 0.75), -1)
    else:
        leg((hip[0] - hw / 2 + 1, hip[1]), p["foot_l"] if view == "S" else p["foot_r"], legs_c, 1)
        leg((hip[0] + hw / 2 - 1, hip[1]), p["foot_r"] if view == "S" else p["foot_l"], legs_c, -1)

    # ---- far arm (E view) / back arms (N view) drawn before torso
    def arm(shoulder, hand, color, bend, bare_forearm=False):
        el = ik(A(shoulder), A(hand), 5.5, 5.5, bend)
        capsule(s, A(shoulder), el, limb_w, color)
        capsule(s, el, A(hand), limb_w, skin if bare_forearm else color)
        hx, hy = A(hand)
        s.fill(skin, pygame.Rect(int(round(hx)) - 1, int(round(hy)) - 1, 2, 2))
        return el

    bare = outfit == "shirt"
    sleeve = coat if outfit != "gown" else skin
    if outfit == "gown":
        bare = True
    if view == "E":
        arm((lean - 1, sh_y + 1), hand_l, shade(sleeve, 0.7), 1, bare)
        leg((hip[0] + 1, hip[1]), p["foot_r"], legs_c, -1)
    if view == "N":
        arm((lean - sw / 2, sh_y + 1), hand_l, shade(sleeve, 0.9), 1, bare)
        arm((lean + sw / 2, sh_y + 1), hand_r, shade(sleeve, 0.9), -1, bare)

    # ---- torso / coat
    hem_y = {"coat_long": -6, "coat_short": -L + 2, "suit": -L + 1, "shirt": -L, "gown": -1, "dress": -6}[outfit] + dy
    if view == "E":
        tw = max(5, sw - 3)
        back = lean - tw / 2
        front = lean + tw / 2
        hem_back = -tw / 2 - (2 if outfit in ("coat_long", "gown", "dress") else 0) + p["hem"]
        hem_front = tw / 2 + (1 if outfit in ("coat_long", "gown", "dress") else 0)
        pts = [A((back, sh_y)), A((front, sh_y)), A((front + 0.5 + body["belly"], (sh_y + hip[1]) / 2)),
               A((hip[0] + hem_front, hem_y)), A((hip[0] + hem_back, hem_y)), A((back - 0.5, (sh_y + hip[1]) / 2))]
    else:
        flare = {"coat_long": 2, "gown": 4, "dress": 2}.get(outfit, 0)
        hem_shift = p["hem"] * 0.5
        pts = [A((lean - sw / 2, sh_y)), A((lean + sw / 2, sh_y)),
               A((hip[0] + hw / 2 + 0.5 + body["belly"], hip[1] - 2)),
               A((hip[0] + hw / 2 + flare + hem_shift, hem_y)), A((hip[0] - hw / 2 - flare + hem_shift, hem_y)),
               A((hip[0] - hw / 2 - 0.5 - body["belly"], hip[1] - 2))]
    pygame.draw.polygon(s, coat, [(round(x), round(y)) for x, y in pts])
    # inner shading: lower half darker for coats, belt line
    if outfit in ("coat_long", "gown", "dress"):
        by = int(round(AY + hip[1] - 2))
        for x in range(FW):
            c = s.get_at((x, by))
            if c.a > 0 and tuple(c) == tuple(coat):
                s.set_at((x, by), coat_d)
        # coat opening line (S view)
        if view == "S" and outfit == "coat_long":
            cx = int(round(AX + lean))
            for y in range(int(AY + sh_y + 3), int(AY + hem_y)):
                if s.get_at((cx, y)).a:
                    s.set_at((cx, y), coat_d)
    if outfit in ("suit", "shirt") and view != "N":
        # trousers waist / belt
        by = int(round(AY + hip[1] + 1))
        for x in range(FW):
            if s.get_at((x, by)).a and s.get_at((x, by - 1)).a:
                s.set_at((x, by), shade(legs_c, 0.7))
    # collar / scarf / shirt front
    neck_x = AX + lean
    neck_y = AY + sh_y
    if view == "S":
        if spec["head"] == "ines":
            s.fill(spec["scarf"], pygame.Rect(int(neck_x) - 3, int(neck_y), 7, 2))
            s.fill(shade(spec["scarf"], 0.8), pygame.Rect(int(neck_x) + 1, int(neck_y) + 2, 2, 5))
            s.set_at((int(neck_x) + 2, int(neck_y) + 7), shade(spec["scarf"], 0.65))
        elif outfit in ("suit", "coat_long", "coat_short"):
            cc = spec["collar"]
            s.fill(cc, pygame.Rect(int(neck_x) - 1, int(neck_y), 3, 3))
            s.set_at((int(neck_x), int(neck_y) + 3), cc)
            if outfit == "suit":
                s.set_at((int(neck_x), int(neck_y) + 2), spec["scarf"])  # tie
                s.set_at((int(neck_x), int(neck_y) + 4), spec["scarf"])
        elif outfit == "gown":
            # bare shoulders and neckline; a pale fur stole draped over both arms
            s.fill(skin, pygame.Rect(int(neck_x) - sw // 2 + 1, int(neck_y), sw - 2, 2))
            s.set_at((int(neck_x), int(neck_y) + 2), skin)
            s.fill(shade(spec["coat"], 1.3), pygame.Rect(int(neck_x) - 1, int(neck_y) + 3, 3, 1))
        elif outfit == "shirt":
            s.fill(shade(coat, 1.12), pygame.Rect(int(neck_x) - 1, int(neck_y), 3, 2))
            # suspenders
            for dx in (-2, 2):
                for y in range(int(neck_y) + 1, int(AY + hip[1])):
                    if s.get_at((int(neck_x) + dx, y)).a:
                        s.set_at((int(neck_x) + dx, y), shade(legs_c, 0.9))
    elif view == "E" and spec["head"] == "ines":
        s.fill(spec["scarf"], pygame.Rect(int(neck_x) - 2, int(neck_y), 5, 2))
        s.fill(spec["scarf"], pygame.Rect(int(neck_x) - 3 + int(p["hem"] * 0.5), int(neck_y) + 1, 2, 4))
    elif view == "E" and outfit == "gown":
        s.fill(skin, pygame.Rect(int(neck_x) - 2, int(neck_y), 5, 2))
        s.fill(spec["collar"], pygame.Rect(int(neck_x) - 3, int(neck_y) + 2, 6, 2))

    # ---- front arms
    if view == "S":
        arm((lean - sw / 2, sh_y + 1), hand_r, sleeve, 1, bare)  # character's right = screen left
        arm((lean + sw / 2, sh_y + 1), hand_l, sleeve, -1, bare)
        if outfit == "gown":
            for sx_ in (lean - sw / 2, lean + sw / 2):
                s.fill(spec["collar"], pygame.Rect(int(round(AX + sx_)) - 1, int(round(AY + sh_y)), 3, 6))
    elif view == "E":
        pass  # near arm after head (may cross the face when raised)

    # ---- head
    hx, hy = p["head"]
    head_top = (int(round(AX + lean + hx)) - 4, int(round(AY + sh_y + hy)) - 8)
    draw_head(s, spec, view, head_top, skin, skin_d)

    if view == "E":
        arm((lean + 0.5, sh_y + 1), hand_r, sleeve, 1, bare)

    # ---- shading pass: soft rim light from the upper left, shadow on the lower right
    a = pygame.surfarray.array_alpha(s) > 0
    rgb = pygame.surfarray.pixels3d(s)
    lit = np.zeros_like(a)
    lit[1:, :] |= a[1:, :] & ~a[:-1, :]
    lit[:, 1:] |= a[:, 1:] & ~a[:, :-1]
    drk = np.zeros_like(a)
    drk[:-1, :] |= a[:-1, :] & ~a[1:, :]
    drk[:, :-1] |= a[:, :-1] & ~a[:, 1:] & (np.arange(FH)[None, :-1] > AY + sh_y + 6)
    f = rgb.astype(np.float32)
    f[lit] *= 1.16
    f[drk & ~lit] *= 0.78
    rgb[:] = np.clip(f, 0, 255).astype(np.uint8)
    del rgb

    meta_hand_r = (hand_r[0] + AX, hand_r[1] + AY)
    meta_hand_l = (hand_l[0] + AX, hand_l[1] + AY)
    head_c = (AX + lean + hx, AY + sh_y + hy - 4)

    # lying down: rotate the full figure so it rests on the ground
    if p["lying"]:
        base = s
        if p["lying"] == 1:
            base = pygame.transform.rotate(s, -45)
        else:
            base = pygame.transform.rotate(s, -90)
        out = surf(FW, FH)
        bw, bh = base.get_size()
        out.blit(base, ((FW - bw) // 2 + (2 if p["lying"] == 2 else 0), AY - bh + (bh - 20) // 2 + (8 if p["lying"] == 2 else 2)))
        s = out
        meta_hand_r = (AX + 8, AY - 3)
        meta_hand_l = (AX + 6, AY - 4)
        head_c = (AX + 14, AY - 4)

    s = outline(s, P.INK)
    # outline() grows the surface by 1px each side: crop back to the frame
    crop = surf(FW, FH)
    crop.blit(s, (0, 0), pygame.Rect(1, 1, FW, FH))
    data = {"hr": [round(meta_hand_r[0], 1), round(meta_hand_r[1], 1)],
            "hl": [round(meta_hand_l[0], 1), round(meta_hand_l[1], 1)],
            "ang": p["angle"], "behind": p["weapon_behind"], "head": [round(head_c[0], 1), round(head_c[1], 1)]}
    return crop, data


def build_sheet(name: str, spec: dict) -> tuple[pygame.Surface, dict]:
    anims = ANIM_SETS[spec["anims"]]
    frames: list[pygame.Surface] = []
    fdata: list[dict] = []
    meta = {"frame": [FW, FH], "anchor": [AX, AY], "cols": COLS, "anims": {}, "frames": fdata}
    for an in anims:
        n, fps, loop = ANIMS[an]
        entry = {"fps": fps, "loop": loop, "dirs": {}}
        views = ("S", "N", "E") if an != "climb" else ("N",)
        for v in views:
            idx = []
            for i in range(n):
                fr, d = draw_character_frame(spec, an, v, i, n)
                idx.append(len(frames))
                frames.append(fr)
                fdata.append(d)
            entry["dirs"][v] = idx
        if an == "climb":
            entry["dirs"]["S"] = entry["dirs"]["N"]
            entry["dirs"]["E"] = entry["dirs"]["N"]
        meta["anims"][an] = entry
    rows = (len(frames) + COLS - 1) // COLS
    sheet = surf(COLS * FW, rows * FH)
    for k, fr in enumerate(frames):
        sheet.blit(fr, ((k % COLS) * FW, (k // COLS) * FH))
    return sheet, meta


def build_all(out_dir: str) -> list[str]:
    d = os.path.join(out_dir, "chars")
    os.makedirs(d, exist_ok=True)
    files = []
    for name, spec in CHARACTERS.items():
        sheet, meta = build_sheet(name, spec)
        p = os.path.join(d, f"{name}.png")
        pygame.image.save(sheet, p)
        files.append(p)
        pj = os.path.join(d, f"{name}.json")
        with open(pj, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        files.append(pj)
    return files
