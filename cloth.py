import json, os, urllib.request
import numpy as np

LOGIN = "Krishnan9074"
THEMES = {"dark": "#f4f4f5", "light": "#18181b"}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  weeks { contributionDays { weekday contributionLevel } } } } } }"""
W, PAD, FRAMES, PERIOD, SUB, WARMUP = 1200, 48, 48, 9.0, 32, 3
GRAVITY = np.array([0.0, -9.8, 0.0])


def calendar():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        {"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"})
    weeks = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = np.full((7, len(weeks)), np.nan)
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            grid[day["weekday"], col] = LEVEL[day["contributionLevel"]]
    return grid


def springs(rows, cols):
    idx = np.arange(rows * cols).reshape(rows, cols)
    links = []
    for dr, dc, compliance in ((0, 1, 4e-4), (1, 0, 4e-4), (1, 1, 2e-3), (1, -1, 2e-3), (0, 2, 5e-2), (2, 0, 5e-2)):
        i = idx[:rows - dr, max(0, -dc):cols - max(0, dc)].ravel()
        j = idx[dr:, max(0, dc):cols - max(0, -dc)].ravel()
        links.append((i, j, np.full(i.size, compliance)))
    return [np.concatenate(a) for a in zip(*links)]


def simulate(levels):
    rows, cols = levels.shape
    r, c = (a.ravel() for a in np.mgrid[:rows, :cols])
    x = np.stack([c, -r, 0 * r], 1).astype(float)
    w = 1 / (1 + 2.5 * np.nan_to_num(levels).ravel())
    w[(r == 0) & ((c % 6 == 0) | (c == cols - 1))] = 0
    i, j, alpha = springs(rows, cols)
    rest = np.linalg.norm(x[j] - x[i], axis=1)
    deg = np.bincount(np.r_[i, j], minlength=x.shape[0])[:, None]
    free, h = (w > 0)[:, None], PERIOD / FRAMES / SUB
    v, frames = np.zeros_like(x), []
    for step in range((WARMUP + 1) * FRAMES * SUB):
        phase = 2 * np.pi * step * h / PERIOD
        gust = np.sin(phase + 0.22 * x[:, 0]) + 0.5 * np.sin(2 * phase - 0.35 * x[:, 0] + x[:, 1])
        wind = np.stack([2 * gust, 0 * gust, 4 + 12 * gust], 1)
        v += h * free * (GRAVITY + wind * w[:, None])
        p = x + h * v
        d = p[j] - p[i]
        length = np.linalg.norm(d, axis=1)
        s = ((length - rest) / (w[i] + w[j] + alpha / h**2) / length)[:, None] * d
        dp = np.zeros_like(p)
        np.add.at(dp, i, w[i, None] * s)
        np.add.at(dp, j, -w[j, None] * s)
        p += 1.5 * dp / deg
        v, x = 0.998 * (p - x) / h, p
        if step >= WARMUP * FRAMES * SUB and step % SUB == 0:
            frames.append(x.copy())
    return np.array(frames + frames[:1])


def project(frames, cols, yaw=0.08, pitch=0.12, dist=60.0):
    x, y, z = frames[..., 0] - (cols - 1) / 2, frames[..., 1], frames[..., 2]
    x, z = x * np.cos(yaw) + z * np.sin(yaw), z * np.cos(yaw) - x * np.sin(yaw)
    y, z = y * np.cos(pitch) - z * np.sin(pitch), y * np.sin(pitch) + z * np.cos(pitch)
    k = dist / (dist - z)
    screen = np.stack([x * k, -y * k], -1)
    lo, hi = screen.reshape(-1, 2).min(0), screen.reshape(-1, 2).max(0)
    scale = (W - 2 * PAD) / (hi[0] - lo[0])
    return (screen - lo) * scale + PAD, int((hi[1] - lo[1]) * scale + 2 * PAD)


def render(levels, screen, height, ink):
    rows, cols = levels.shape
    pts = screen.reshape(len(screen), rows, cols, 2)

    def anim(attr, values):
        return f'<animate attributeName="{attr}" dur="{PERIOD}s" repeatCount="indefinite" values="{";".join(values)}"/>'

    def thread(line):
        ds = ["M" + " ".join(f"{a:.0f} {b:.0f}" for a, b in f) for f in line]
        return f'<path d="{ds[0]}">{anim("d", ds)}</path>'

    threads = [thread(pts[:, r]) for r in range(rows)] + [thread(pts[:, :, c]) for c in range(cols)]
    dots = []
    for r, c in zip(*np.nonzero(~np.isnan(levels))):
        lvl, track = levels[r, c], pts[:, r, c]
        xs, ys = [f"{a:.0f}" for a in track[:, 0]], [f"{b:.0f}" for b in track[:, 1]]
        dots.append(f'<circle cx="{xs[0]}" cy="{ys[0]}" r="{1.3 + 0.75 * lvl:.1f}" opacity="{0.22 + 0.195 * lvl:.2f}">'
                    f'{anim("cx", xs)}{anim("cy", ys)}</circle>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}">'
            f'<title>{LOGIN} contributions, simulated as cloth</title>'
            f'<g fill="none" stroke="{ink}" stroke-opacity=".08">{"".join(threads)}</g>'
            f'<g fill="{ink}">{"".join(dots)}</g></svg>')


if __name__ == "__main__":
    levels = calendar()
    screen, height = project(simulate(levels), levels.shape[1])
    for theme, ink in THEMES.items():
        with open(f"assets/cloth-{theme}.svg", "w") as f:
            f.write(render(levels, screen, height, ink))
