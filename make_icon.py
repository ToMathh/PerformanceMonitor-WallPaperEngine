"""
Run ONCE before building:  python make_icon.py
Generates icon.ico in the same folder as this script.
"""
import os, sys
from PIL import Image, ImageDraw

def make():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = []
    for s in sizes:
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        lw = max(1, s // 24)
        # bg
        d.rounded_rectangle([lw, lw, s-lw-1, s-lw-1], radius=max(2, s//8),
                             fill=(14, 14, 14, 255), outline=(210, 0, 0, 255), width=lw)
        # ears (two triangles)
        ew = max(2, s // 5)
        eh = max(3, s // 3)
        d.polygon([(s//5, s//2+2), (s//5+ew//2, s//5), (s//5+ew, s//2+2)],
                  fill=(200, 0, 0, 255))
        d.polygon([(s*4//5-ew, s//2+2), (s*4//5-ew//2, s//5), (s*4//5, s//2+2)],
                  fill=(200, 0, 0, 255))
        # face oval
        fx1, fy1, fx2, fy2 = s//7, s*3//8, s-s//7, s-s//9
        d.ellipse([fx1, fy1, fx2, fy2], fill=(28, 28, 28, 255),
                  outline=(160, 0, 0, 180), width=lw)
        # eyes
        ey = (fy1 + fy2) // 2 - max(1, s//20)
        er = max(2, s // 10)
        for ex in (fx1 + (fx2-fx1)//3, fx2 - (fx2-fx1)//3):
            d.ellipse([ex-er, ey-er, ex+er, ey+er], fill=(210, 0, 0, 255))
        # nose
        nx = s // 2
        ny = ey + er + max(2, s//12)
        nr = max(2, s//14)
        d.polygon([(nx, ny-nr), (nx-nr, ny+nr), (nx+nr, ny+nr)],
                  fill=(190, 55, 55, 255))
        frames.append(img)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    frames[0].save(out, format="ICO",
                   sizes=[(s, s) for s in sizes],
                   append_images=frames[1:])
    print(f"[OK] icon.ico created at: {out}")

if __name__ == "__main__":
    make()
