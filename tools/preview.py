"""Dev helper: crop + upscale an image for quick inspection.

    python tools/preview.py <src.png> <out.png> [x y w h] [scale]
"""
import sys

import pygame

src, out = sys.argv[1], sys.argv[2]
img = pygame.image.load(src)
if len(sys.argv) >= 7:
    x, y, w, h = map(int, sys.argv[3:7])
    img = img.subsurface(pygame.Rect(x, y, w, h)).copy()
scale = int(sys.argv[7]) if len(sys.argv) >= 8 else 2
bg = pygame.Surface(img.get_size())
bg.fill((255, 0, 255))
bg.blit(img, (0, 0))
pygame.image.save(pygame.transform.scale_by(bg, scale), out)
