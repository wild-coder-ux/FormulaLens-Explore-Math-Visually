import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re, os, sys

try:
    import scipy.special as spspecial
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

os.makedirs("outputs", exist_ok=True)

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
BG = "#121212"
PANEL = "#1c1c1c"
FG = "#e8e8e8"
MUTED = "#9a9a9a"
ACCENT = "#ff9f1c"
GOOD = "#5be37f"
BAD = "#ff5c5c"
FONT = ("TkDefaultFont", 10)
FONT_MONO = ("TkFixedFont", 11)
FONT_TITLE = ("TkDefaultFont", 12, "bold")
FONT_SMALL_BOLD = ("TkDefaultFont", 8, "bold")

# ---------------------------------------------------------------------------
# Unicode math normalization
# ---------------------------------------------------------------------------
SUPERSCRIPTS = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
                "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
SUPER_RUN = re.compile("[" + "".join(SUPERSCRIPTS.keys()) + "]+")
_WORDS = r"(?:pi|sqrt|sin|cos|tan|exp|log|gamma|zeta|erf|theta|besselj|factorial|x|y|q|z)"

def normalize_unicode(text):
    text = text.strip()
    def repl(m):
        digits = "".join(SUPERSCRIPTS[c] for c in m.group(0))
        return "**" + digits
    text = re.sub(r"(?<=[\w\)])" + SUPER_RUN.pattern, repl, text)
    text = re.sub(r"(\d)(√|π)", r"\1*\2", text)
    text = re.sub(r"√\s*\(", "sqrt(", text)
    text = re.sub(r"√\s*(\w+)", r"sqrt(\1)", text)
    text = text.replace("π", "pi").replace("×", "*").replace("÷", "/").replace("−", "-")
    text = re.sub(r"(\d)(" + _WORDS + r")\b", r"\1*\2", text)
    text = re.sub(r"(\d)(\()", r"\1*\2", text)
    text = re.sub(r"(\))\s*(\d|" + _WORDS + r")", r"\1*\2", text)
    return text

# ---------------------------------------------------------------------------
# Special functions (work for real AND complex input where possible)
# ---------------------------------------------------------------------------
def jacobi_theta3(x, nome=0.5, terms=15):
    """Truncated Jacobi theta_3 series: sum_n q^(n^2) cos(2*n*pi*x). Educational
    approximation (fixed nome=0.5, 31 terms) rather than the full analytic form."""
    x = np.asarray(x)
    n = np.arange(-terms, terms + 1)
    shape = (len(n),) + (1,) * x.ndim
    n = n.reshape(shape)
    return np.sum((nome ** (n ** 2)) * np.cos(2 * n * np.pi * x), axis=0)

if HAVE_SCIPY:
    _gamma = spspecial.gamma
    _erf = spspecial.erf
    _besselj = spspecial.jv
    _zeta = lambda s: spspecial.zeta(s, 1)  # Riemann zeta via Hurwitz zeta(s,1); real input only
    _factorial = lambda n: spspecial.gamma(n + 1)
else:
    import math
    _gamma = np.vectorize(math.gamma)
    _erf = np.vectorize(math.erf)
    _besselj = lambda n, x: np.zeros_like(np.asarray(x, dtype=float))  # unavailable without scipy
    _zeta = lambda s: np.full_like(np.asarray(s, dtype=float), np.nan)
    _factorial = np.vectorize(math.factorial)

# ---------------------------------------------------------------------------
# Safe Eval Environment
# ---------------------------------------------------------------------------
SAFE_BASE = {
    "pi": np.pi, "e": np.e,
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "exp": np.exp, "log": np.log, "sqrt": np.sqrt, "abs": np.abs,
    "gamma": _gamma, "zeta": _zeta, "erf": _erf,
    "besselj": _besselj, "theta": jacobi_theta3, "factorial": _factorial,
    "range": range,
    "np": np,
}

def parse_eq(eq_text):
    eq_text = normalize_unicode(eq_text.strip())
    eq_text = eq_text.replace("^", "**")
    # Allow 'q' or 'z' as alternate names for the single plotting variable.
    eq_text = re.sub(r"\bq\b", "x", eq_text)
    eq_text = re.sub(r"\bz\b", "x", eq_text)
    return eq_text

# ---------------------------------------------------------------------------
# Presets — tagged with a difficulty LEVEL and a short educational blurb.
# mode: "line" = y=f(x), "contour" = f(x,y)=0, "complex" = domain coloring of f(x)
# ---------------------------------------------------------------------------
PRESETS = {
    "-- free text below --": None,
}
PRESET_MODE = {}
PRESET_LEVEL = {}
PRESET_DESC = {}

def _add(name, eq, mode, level, desc):
    PRESETS[name] = eq
    PRESET_MODE[name] = mode
    PRESET_LEVEL[name] = level
    PRESET_DESC[name] = desc

# --- Beginner ---
_add("[Geometry] Circle x²+y²=1", "x**2 + y**2 - 1", "contour", "Beginner",
     "All points at distance 1 from the origin.")
_add("[Geometry] Ellipse x²/4+y²=1", "x**2/4 + y**2 - 1", "contour", "Beginner",
     "A stretched circle — squashed along the x-axis.")
_add("[Geometry] Hyperbola x²-y²=1", "x**2 - y**2 - 1", "contour", "Beginner",
     "Two mirrored curves that never meet, opening left and right.")
_add("[Trigonometry] Sine wave", "sin(x) - y", "contour", "Beginner",
     "The classic smooth up-and-down wave.")
_add("[Trigonometry] Cosine wave", "cos(x) - y", "contour", "Beginner",
     "Same shape as sine, shifted a quarter-turn earlier.")
_add("[Calculus] Parabola y=x²", "x**2 - y", "contour", "Beginner",
     "The simplest curve with a single turning point (a minimum).")

# --- Intermediate ---
_add("[Calculus] Cubic y=x³-x", "x**3 - x - y", "contour", "Intermediate",
     "An S-shaped curve with a local max and min.")
_add("[Calculus] Absolute value", "abs(x) - y", "contour", "Intermediate",
     "A sharp V — not smooth (not differentiable) at x=0.")
_add("[AI/ML] Sigmoid", "1/(1+exp(-x)) - y", "contour", "Intermediate",
     "Squashes any input into the range (0,1) — used to output probabilities.")
_add("[AI/ML] Gaussian bell", "exp(-x**2) - y", "contour", "Intermediate",
     "The bell curve — peaks at 0, symmetric, never quite touches zero.")
_add("[AI/ML] ReLU", "np.maximum(0, x) - y", "contour", "Intermediate",
     "Zero for negative inputs, identity for positive — the default neural-net activation.")
_add("[Trig+Calculus] Damped wave", "exp(-x**2/5)*cos(4*x)", "line", "Intermediate",
     "🌊 An oscillation whose amplitude decays away from the origin.")

# --- Advanced (Cartesian implicit curves) ---
_add("[Cartesian Curve] Heart", "(x**2+y**2-1)**3 - x**2*y**3", "contour", "Advanced",
     "❤️ A classic implicit-curve heart shape.")
_add("[Cartesian Curve] Lemniscate", "(x**2+y**2)**2 - 2*(x**2-y**2)", "contour", "Advanced",
     "∞ A figure-eight curve, the locus of points whose distances to two foci multiply to a constant.")
_add("[Cartesian Curve] Folium of Descartes", "x**3+y**3-3*x*y", "contour", "Advanced",
     "🍃 A looped curve first studied by Descartes in 1638.")

# --- Advanced (Complex-plane domain coloring) ---
_add("[Complex] Power q⁵", "q**5", "complex", "Advanced",
     "Power function with 5-fold symmetry — watch the phase (color) wind around the origin 5 times.")
_add("[Complex] sin(10q)", "sin(10*q)", "complex", "Advanced",
     "Trigonometric oscillation — the coloring reveals evenly spaced zeros and poles-free structure.")
_add("[Complex] Essential singularity exp(1/q)", "exp(1/q)", "complex", "Advanced",
     "Near q=0 the function takes almost every complex value infinitely often (Picard's theorem) — the colors churn wildly close to the origin.")
_add("[Complex] Jacobi theta θ(q)", "theta(q)", "complex", "Advanced",
     "A truncated Jacobi theta series (modular-form family) — quasi-periodic structure visible in the color bands.")

LEVELS = ["All", "Beginner", "Intermediate", "Advanced"]

def presets_for_level(level):
    names = ["-- free text below --"]
    for name in PRESETS:
        if name == "-- free text below --":
            continue
        if level == "All" or PRESET_LEVEL.get(name) == level:
            names.append(name)
    return names

# ---------------------------------------------------------------------------
# Domain coloring (complex-plane visualization)
# ---------------------------------------------------------------------------
def domain_color_image(F):
    """Map a complex array to RGB: hue = phase, brightness = log-scaled magnitude.
    Bright/white regions -> poles or large values, dark regions -> zeros."""
    mag = np.abs(F)
    phase = np.angle(F)
    hue = (phase + np.pi) / (2 * np.pi)
    with np.errstate(all="ignore"):
        light = np.log1p(mag)
    finite = light[np.isfinite(light)]
    maxv = finite.max() if finite.size and finite.max() > 0 else 1.0
    light = np.clip(light / maxv, 0.05, 0.95)
    light = np.nan_to_num(light, nan=0.5, posinf=0.95, neginf=0.05)
    hue = np.nan_to_num(hue, nan=0.0)
    sat = np.ones_like(hue)
    hsv = np.stack([hue, sat, light], axis=-1)
    return mcolors.hsv_to_rgb(hsv)

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
fig, ax = None, None

def render(*_args):
    global fig, ax
    R = float(r_var.get())
    mode = mode_var.get()

    ax.clear()
    status.config(text="")

    preset_name = preset_var.get()
    preset_eq = PRESETS.get(preset_name)

    try:
        if preset_eq is not None:
            eq_clean = parse_eq(preset_eq)
            label = preset_name
        else:
            eq_clean = parse_eq(entry.get())
            label = eq_clean[:44]

        if mode == "complex":
            # Domain coloring over the complex plane: z = x + iy
            N = 500
            xs = np.linspace(-R, R, N)
            ys = np.linspace(-R, R, N)
            Xc, Yc = np.meshgrid(xs, ys)
            Z = Xc + 1j * Yc
            env = dict(SAFE_BASE)
            env["x"] = Z
            F = np.asarray(eval(eq_clean, {"__builtins__": {}}, env), dtype=complex)
            rgb = domain_color_image(F)
            ax.imshow(rgb, extent=[-R, R, -R, R], origin="lower")
            ax.set_title(label + "  (hue=phase, bright=|f|)", color=FG, fontsize=8)
        elif mode == "line":
            x = np.linspace(-R, R, 800)
            y = np.linspace(-R, R, 800)
            X, Y = np.meshgrid(x, y)
            has_y = bool(re.search(r'\by\b', eq_clean.replace('sqrt', '').replace('exp', '').replace('log', '')))

            if has_y:
                env = dict(SAFE_BASE)
                env['x'] = X
                env['y'] = Y
                F = np.asarray(eval(eq_clean, {"__builtins__": {}}, env), dtype=float)
                ax.contour(X, Y, F, levels=[0], colors=ACCENT, linewidths=2)
            else:
                env = dict(SAFE_BASE)
                env['x'] = x

                if 'sum(' in eq_clean and 'for' in eq_clean:
                    # Merge into ONE dict so the generator-expression's inner
                    # scope can see x/n/np (exec with 2 dicts hides locals
                    # from comprehension/genexp bodies).
                    exec_globals = dict(env)
                    exec_globals['__builtins__'] = {}
                    exec_globals['sum'] = lambda gen: np.sum(list(gen), axis=0)
                    exec(f"result = {eq_clean}", exec_globals)
                    F1d = exec_globals['result']
                else:
                    F1d = np.asarray(eval(eq_clean, {"__builtins__": {}}, env), dtype=float)

                ax.plot(x, F1d, color=ACCENT, lw=2)
                ax.axhline(0, color='#444', lw=1)
                ax.axvline(0, color='#444', lw=1)
                ax.set_xlim(-R, R)
                ax.set_ylim(-R, R)
                ax.set_aspect('equal', adjustable='box')
        else:
            x = np.linspace(-R, R, 800)
            y = np.linspace(-R, R, 800)
            X, Y = np.meshgrid(x, y)
            env = dict(SAFE_BASE)
            env['x'] = X
            env['y'] = Y
            F = np.asarray(eval(eq_clean, {"__builtins__": {}}, env), dtype=float)
            ax.contour(X, Y, F, levels=[0], colors=ACCENT, linewidths=2)

        if mode != "complex":
            ax.axhline(0, color='#444', lw=1)
            ax.axvline(0, color='#444', lw=1)
            ax.set_xlim(-R, R)
            ax.set_ylim(-R, R)
            ax.set_aspect('equal', adjustable='box')
            ax.set_title(label, color=FG, fontsize=9)

        ax.set_facecolor(BG)
        status.config(text="OK", fg=GOOD)
        desc = PRESET_DESC.get(preset_name, "")
        desc_label.config(text=desc)

    except Exception as e:
        status.config(text=f"Error: {e}", fg=BAD)
        ax.text(0.5, 0.5, f"error:\n{e}", ha="center", va="center", color=BAD,
                fontsize=9, transform=ax.transAxes, wrap=True)

    fig.patch.set_facecolor(BG)
    canvas.draw()

def on_preset_selected(*_args):
    name = preset_var.get()
    eq = PRESETS.get(name)
    if eq is not None:
        # Show the actual formula being plotted, so students can read/copy it.
        entry.delete(0, tk.END)
        entry.insert(0, eq)
    m = PRESET_MODE.get(name)
    if m is not None:
        mode_var.set(m)
    render()

def on_entry_edited(_event=None):
    # If the student hand-edits the equation, it's no longer "the preset" —
    # drop back to free text so the dropdown doesn't lie about what's plotted.
    name = preset_var.get()
    preset_eq = PRESETS.get(name)
    if preset_eq is not None and entry.get().strip() != preset_eq.strip():
        preset_var.set("-- free text below --")
        desc_label.config(text="")

def on_level_selected(*_args):
    level = level_var.get()
    names = presets_for_level(level)
    preset_menu["values"] = names
    if preset_var.get() not in names:
        preset_var.set("-- free text below --")
    render()

# ---------------------------------------------------------------------------
# Window / layout
# ---------------------------------------------------------------------------
root = tk.Tk()
root.title("FormulaLens — Explore Math Visually")
root.configure(bg=BG)
root.geometry("560x860")
root.minsize(480, 660)

def on_close():
    try:
        plt.close("all")
    except Exception:
        pass
    root.quit()
    root.destroy()
    sys.exit(0)

root.protocol("WM_DELETE_WINDOW", on_close)

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass
style.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG)
style.configure("Horizontal.TScale", background=BG)

header = tk.Frame(root, bg=BG)
header.pack(fill="x", padx=16, pady=(14, 6))
tk.Label(header, text="FormulaLens", font=FONT_TITLE, fg=ACCENT, bg=BG).pack(anchor="w")
tk.Label(header, text="Explore Math Visually — circles, calculus, trig, complex functions, and any f(x,y)=0",
         font=FONT, fg=MUTED, bg=BG).pack(anchor="w")

controls = tk.Frame(root, bg=PANEL, highlightbackground="#2a2a2a", highlightthickness=1)
controls.pack(fill="x", padx=16, pady=8)

level_row = tk.Frame(controls, bg=PANEL)
level_row.pack(fill="x", padx=12, pady=(10, 2))
tk.Label(level_row, text="LEVEL", font=FONT_SMALL_BOLD, fg=MUTED, bg=PANEL).pack(side="left")
level_var = tk.StringVar(value="All")
level_menu = ttk.Combobox(level_row, textvariable=level_var, values=LEVELS,
                           state="readonly", font=FONT, width=14)
level_menu.pack(side="left", padx=(8, 0))
level_menu.bind("<<ComboboxSelected>>", on_level_selected)
tk.Label(level_row, text="  filter presets by difficulty — beginners start here, advanced students dig into Complex/Cartesian",
         font=("TkDefaultFont", 8), fg=MUTED, bg=PANEL).pack(side="left")

tk.Label(controls, text="PRESET", font=FONT_SMALL_BOLD, fg=MUTED, bg=PANEL).pack(
    anchor="w", padx=12, pady=(8, 2))
preset_var = tk.StringVar(value="-- free text below --")
preset_menu = ttk.Combobox(controls, textvariable=preset_var, values=presets_for_level("All"),
                            state="readonly", font=FONT)
preset_menu.pack(fill="x", padx=12, pady=(0, 4))
preset_menu.bind("<<ComboboxSelected>>", on_preset_selected)

desc_label = tk.Label(controls, text="", font=("TkDefaultFont", 9, "italic"), fg=ACCENT, bg=PANEL,
                       wraplength=520, justify="left")
desc_label.pack(anchor="w", padx=12, pady=(0, 8))

tk.Label(controls, text="EQUATION  (use x, y, x², √, π. e.g. x**2+y**2-1, sin(x), gamma(x), q**5)",
         font=FONT_SMALL_BOLD, fg=MUTED, bg=PANEL).pack(anchor="w", padx=12, pady=(0, 2))
entry = tk.Entry(controls, font=FONT_MONO, bg="#0d0d0d", fg=FG, insertbackground=FG,
                  relief="flat", highlightthickness=1, highlightbackground="#333", highlightcolor=ACCENT)
entry.insert(0, "x**2 + y**2 - 1")
entry.pack(fill="x", padx=12, pady=(0, 8), ipady=6)
entry.bind("<Return>", render)
entry.bind("<KeyRelease>", on_entry_edited)

# --- EXPLANATION FRAME ---
info_frame = tk.Frame(controls, bg="#252525", highlightbackground="#333", highlightthickness=1)
info_frame.pack(fill="x", padx=12, pady=(0, 10))

tk.Label(info_frame, text=" VIEW MODE", font=FONT_SMALL_BOLD, fg=ACCENT, bg="#252525").pack(
    anchor="w", padx=10, pady=(8, 4))

tk.Label(info_frame,
         text="Line plot (y=f(x)):  Type function like 'sin(x)' or 'x**2'. Draws y = f(x)",
         font=("TkDefaultFont", 9), fg=MUTED, bg="#252525", justify="left").pack(
    anchor="w", padx=10, pady=(0, 2))

tk.Label(info_frame,
         text="Implicit plot (f(x,y)=0):  Type equation like 'x²+y²-1'. Draws curve where f(x,y)=0",
         font=("TkDefaultFont", 9), fg=MUTED, bg="#252525", justify="left").pack(
    anchor="w", padx=10, pady=(0, 2))

tk.Label(info_frame,
         text="Complex domain (hue=phase, brightness=|f|):  Visualizes f(x) as a function on the complex plane — great for seeing poles, zeros, and singularities.",
         font=("TkDefaultFont", 9), fg=MUTED, bg="#252525", justify="left").pack(
    anchor="w", padx=10, pady=(0, 8))

mode_row = tk.Frame(controls, bg=PANEL)
mode_row.pack(fill="x", padx=12, pady=(0, 10))
tk.Label(mode_row, text="SELECT MODE", font=FONT_SMALL_BOLD, fg=MUTED, bg=PANEL).pack(anchor="w")
mode_btn_row = tk.Frame(controls, bg=PANEL)
mode_btn_row.pack(fill="x", padx=12, pady=(0, 10))
mode_var = tk.StringVar(value="line")
for val, txt in [("line", "Line (y=f(x))"), ("contour", "Implicit (f(x,y)=0)"), ("complex", "Complex plane")]:
    tk.Radiobutton(mode_btn_row, text=txt, variable=mode_var, value=val, command=render,
                   font=FONT, fg=FG, bg=PANEL, selectcolor="#0d0d0d",
                   activebackground=PANEL, activeforeground=ACCENT).pack(side="left", padx=(0, 10))

status = tk.Label(root, text="", bg=BG, font=FONT_MONO, fg=FG)
status.pack(pady=(2, 6))

slider_frame = tk.Frame(root, bg=BG)
slider_frame.pack(fill="x", padx=16)
r_var = tk.StringVar(value="5")
tk.Label(slider_frame, text="Range (±R)", font=FONT, fg=MUTED, bg=BG).pack(anchor="w")
ttk.Scale(slider_frame, from_=1, to=20, variable=r_var, orient="horizontal",
          command=lambda v: render()).pack(fill="x")

tk.Button(root, text="DRAW", command=render, bg=ACCENT, fg="#1a1a1a",
          font=("TkDefaultFont", 10, "bold"), relief="flat", activebackground="#ffb84d",
          cursor="hand2").pack(pady=10, ipadx=18, ipady=6)

canvas_frame = tk.Frame(root, bg=BG)
canvas_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

fig, ax = plt.subplots(figsize=(5, 5), dpi=110)
fig.patch.set_facecolor(BG)
canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)

render()
root.mainloop()
