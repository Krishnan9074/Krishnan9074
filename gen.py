import math, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

W, H, CX, CY, TILT = 1200, 480, 600, 240, math.radians(-3)
FONTS = "/usr/share/fonts/opentype/inter/"
DISPLAY, TEXT = TTFont(FONTS + "InterDisplay-Light.otf"), TTFont(FONTS + "Inter-Regular.otf")

RINGS = [  # (rx, ry, period seconds, tools)
    (360, 126, 36, ["python", "typescript", "c++", "c", "java", "javascript"]),
    (420, 151, 52, ["pytorch", "tensorflow", "keras", "scikit-learn", "opencv", "cuda", "nvidia warp", "mcp", "pandas", "numpy"]),
    (480, 176, 72, ["docker", "aws", "vercel", "mongodb", "mysql", "convex", "firebase",
                    "react", "next.js", "react native", "node", "express", "flask", "django", "spring", "tailwind", "redux"]),
]
THEMES = {"dark": "#f4f4f5", "light": "#18181b"}
FIRST, LAST, NAME_SIZE = "venkat shreyas ", "krishnan", 44

def advance(font, text, size):
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    return sum(hmtx[cmap[ord(c)]][0] for c in text) * size / font["head"].unitsPerEm

def outline(font, text, size, x=0, y=0, anchor="start"):
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    s = size / font["head"].unitsPerEm
    x -= {"start": 0, "middle": 0.5, "end": 1}[anchor] * advance(font, text, size)
    pen = SVGPathPen(glyphs, lambda v: f"{v:.1f}")
    for c in text:
        glyphs[cmap[ord(c)]].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
        x += hmtx[cmap[ord(c)]][0] * s
    return pen.getCommands()

def name(ink):
    x0 = CX - advance(DISPLAY, FIRST + LAST, NAME_SIZE) / 2
    x1 = x0 + advance(DISPLAY, FIRST, NAME_SIZE)
    return (f'<path d="{outline(DISPLAY, FIRST, NAME_SIZE, x0, CY + 16)}" fill="{ink}" opacity=".5"/>'
            f'<path d="{outline(DISPLAY, LAST, NAME_SIZE, x1, CY + 16)}" fill="{ink}"/>')

def orbit(rx, ry, theta):
    ex, ey = rx * math.cos(theta), ry * math.sin(theta)
    return (CX + ex * math.cos(TILT) - ey * math.sin(TILT),
            CY + ex * math.sin(TILT) + ey * math.cos(TILT),
            0.12 + 0.88 * ((math.sin(theta) + 1) / 2) ** 1.6)

def planet(rx, ry, period, phase, label, ink, animate, at=0, frames=72):
    phase += 2 * math.pi * at / period
    steps = [orbit(rx, ry, phase + 2 * math.pi * i / frames) for i in range(frames + 1)]
    x, y, o = steps[0]
    anim = "" if not animate else (
        f'<animateTransform attributeName="transform" type="translate" dur="{period}s" repeatCount="indefinite" '
        f'values="{";".join(f"{a:.1f},{b:.1f}" for a, b, _ in steps)}"/>'
        f'<animate attributeName="opacity" dur="{period}s" repeatCount="indefinite" '
        f'values="{";".join(f"{c:.2f}" for *_, c in steps)}"/>')
    return (f'<g transform="translate({x:.1f},{y:.1f})" opacity="{o:.2f}">{anim}'
            f'<circle r="2.2" fill="{ink}"/><path d="{outline(TEXT, label, 13, 9, 4.5)}" fill="{ink}"/></g>')

def render(ink, animate=True, bg=None, at=0):
    rings = "".join(
        f'<ellipse cx="{CX}" cy="{CY}" rx="{rx}" ry="{ry}" transform="rotate({math.degrees(TILT):.0f} {CX} {CY})"/>'
        for rx, ry, *_ in RINGS)
    planets = "".join(planet(rx, ry, period, 2 * math.pi * i / len(tools) + k, tool, ink, animate, at)
                      for k, (rx, ry, period, tools) in enumerate(RINGS) for i, tool in enumerate(tools))
    corners = (f'<path d="{outline(TEXT, "krishnan9074", 12, 32, 40)}"/>'
               f'<path d="{outline(TEXT, "ai engineer · san francisco", 12, W - 32, H - 30, "end")}"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<title>{FIRST + LAST}: {", ".join(t for *_, ts in RINGS for t in ts)}</title>
{f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else ""}
<g fill="none" stroke="{ink}" stroke-opacity=".12">{rings}</g>
{name(ink)}
<g fill="{ink}" opacity=".45">{corners}</g>
{planets}
</svg>'''

if __name__ == "__main__":
    for theme, ink in THEMES.items():
        open(f"assets/orbit-{theme}.svg", "w").write(render(ink))
    if "preview" in sys.argv:
        out = sys.argv[-1]
        for theme, ink in THEMES.items():
            for at in (0, 9, 23):
                open(f"{out}/orbit-{theme}-{at}.svg", "w").write(render(ink, False, {"dark": "#0d1117", "light": "#ffffff"}[theme], at))
