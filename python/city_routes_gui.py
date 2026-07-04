"""Interactive Tkinter visualization for the C++ city route optimizer."""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ENGINE = ROOT / "bin" / ("route_engine.exe" if os.name == "nt" else "route_engine")

BG = "#08111f"
PANEL = "#101d30"
PANEL_2 = "#14253c"
TEXT = "#eef5ff"
MUTED = "#90a4bd"
CYAN = "#4dd8e8"
AMBER = "#ffc857"
ROUTE = "#ff5c8a"
GREEN = "#57d69b"
CLUSTERS = ["#4dd8e8", "#ff8fab", "#ffc857", "#57d69b", "#a78bfa", "#fb923c", "#60a5fa", "#f472b6", "#a3e635"]


class GraphModel:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.cities: list[dict] = []
        self.roads: list[dict] = []
        self.by_id: dict[int, dict] = {}
        self.weight_min = self.weight_max = 0.0
        self.cluster_count = 0

    def load(self) -> None:
        with (self.data_dir / "cities.csv").open(newline="", encoding="utf-8") as handle:
            self.cities = [
                {"id": int(r["id"]), "name": r["name"], "x": float(r["x"]), "y": float(r["y"])}
                for r in csv.DictReader(handle)
            ]
        with (self.data_dir / "roads.csv").open(newline="", encoding="utf-8") as handle:
            self.roads = [
                {"source": int(r["source"]), "target": int(r["target"]), "weight": float(r["weight"])}
                for r in csv.DictReader(handle)
            ]
        self.by_id = {c["id"]: c for c in self.cities}
        weights = [r["weight"] for r in self.roads]
        self.weight_min, self.weight_max = min(weights), max(weights)
        self._assign_clusters(9)

    def _assign_clusters(self, count: int) -> None:
        """Deterministic k-means over map coordinates for geographic cluster analysis."""
        centers = [(self.cities[i * len(self.cities) // count]["x"], self.cities[i * len(self.cities) // count]["y"])
                   for i in range(count)]
        for _ in range(30):
            groups = [[] for _ in centers]
            for city in self.cities:
                cluster = min(range(count), key=lambda i: (city["x"]-centers[i][0])**2 + (city["y"]-centers[i][1])**2)
                city["cluster"] = cluster; groups[cluster].append(city)
            updated = [(sum(c["x"] for c in group)/len(group), sum(c["y"] for c in group)/len(group))
                       if group else centers[i] for i, group in enumerate(groups)]
            if updated == centers:
                break
            centers = updated
        self.cluster_count = count

    def line_width(self, weight: float) -> float:
        span = self.weight_max - self.weight_min
        return 0.7 if span <= 0 else 0.55 + 3.25 * (weight - self.weight_min) / span

    def route(self, source: int, target: int) -> tuple[float, list[int]]:
        result = subprocess.run(
            [str(ENGINE), "path", str(self.data_dir), str(source), str(target)],
            capture_output=True, text=True, check=False, timeout=15,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "The route engine failed.")
        rows = [line.split(",") for line in result.stdout.strip().splitlines()]
        return float(rows[0][1]), [int(value) for value in rows[1][1:]]


class RouteApp(tk.Tk):
    def __init__(self, model: GraphModel):
        super().__init__()
        self.model = model
        self.title("CityScope · Route Optimizer")
        self.geometry("1400x850")
        self.minsize(1040, 680)
        self.configure(bg=BG)
        self.route_ids: list[int] = []
        self.route_distance = 0.0
        self.scale_factor = 1.0
        self.offset_x = self.offset_y = 0.0
        self.drag_origin = None
        self.city_screen: dict[int, tuple[float, float]] = {}
        self.show_all_labels = tk.BooleanVar(value=False)
        self.show_roads = tk.BooleanVar(value=True)
        self.show_clusters = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready — choose two cities to calculate the optimal route")
        self.metric_route = tk.StringVar(value="—")
        self.metric_stops = tk.StringVar(value="—")
        self._configure_styles()
        self._build_ui()
        self.bind("<Escape>", lambda _: self.clear_route())
        self.after(80, self.draw)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Card.TFrame", background=PANEL_2)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 18))
        style.configure("CardTitle.TLabel", background=PANEL_2, foreground=MUTED, font=("Segoe UI", 8))
        style.configure("CardValue.TLabel", background=PANEL_2, foreground=TEXT, font=("Segoe UI Semibold", 15))
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", PANEL)])
        style.configure("TCombobox", fieldbackground="#0b1728", background=PANEL_2, foreground=TEXT,
                        arrowcolor=CYAN, padding=7, borderwidth=0)
        style.map("TCombobox", fieldbackground=[("readonly", "#0b1728")], foreground=[("readonly", TEXT)])
        style.configure("Accent.TButton", background=CYAN, foreground="#06111b", borderwidth=0,
                        padding=(12, 9), font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", "#78e8f2")])
        style.configure("Quiet.TButton", background=PANEL_2, foreground=TEXT, borderwidth=0, padding=(10, 8))
        style.map("Quiet.TButton", background=[("active", "#1d3553")])

    def _build_ui(self) -> None:
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(shell, style="Panel.TFrame", width=320)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        main = ttk.Frame(shell)
        main.pack(side="left", fill="both", expand=True)

        head = ttk.Frame(self.sidebar, style="Panel.TFrame")
        head.pack(fill="x", padx=22, pady=(23, 20))
        ttk.Label(head, text="CITYSCOPE", style="Title.TLabel").pack(anchor="w")
        ttk.Label(head, text="GRAPH THEORY · ROUTE OPTIMIZATION", style="Muted.TLabel").pack(anchor="w", pady=(2, 0))

        self._separator()
        names = [f'{c["name"]}  ·  #{c["id"]}' for c in self.model.cities]
        form = ttk.Frame(self.sidebar, style="Panel.TFrame")
        form.pack(fill="x", padx=22, pady=19)
        ttk.Label(form, text="STARTING CITY", style="Muted.TLabel").pack(anchor="w")
        self.source_box = ttk.Combobox(form, values=names, state="readonly")
        self.source_box.pack(fill="x", pady=(6, 14))
        self.source_box.current(0)
        ttk.Label(form, text="DESTINATION", style="Muted.TLabel").pack(anchor="w")
        self.target_box = ttk.Combobox(form, values=names, state="readonly")
        self.target_box.pack(fill="x", pady=(6, 14))
        self.target_box.current(min(120, len(names) - 1))
        ttk.Button(form, text="Find optimal route", style="Accent.TButton", command=self.calculate_route).pack(fill="x")
        ttk.Button(form, text="Clear route", style="Quiet.TButton", command=self.clear_route).pack(fill="x", pady=(8, 0))

        metrics = ttk.Frame(self.sidebar, style="Panel.TFrame")
        metrics.pack(fill="x", padx=22, pady=(0, 17))
        left = ttk.Frame(metrics, style="Card.TFrame")
        left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        right = ttk.Frame(metrics, style="Card.TFrame")
        right.pack(side="left", fill="x", expand=True, padx=(5, 0))
        ttk.Label(left, text="DISTANCE", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Label(left, textvariable=self.metric_route, style="CardValue.TLabel").pack(anchor="w", padx=12, pady=(0, 10))
        ttk.Label(right, text="CITIES", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Label(right, textvariable=self.metric_stops, style="CardValue.TLabel").pack(anchor="w", padx=12, pady=(0, 10))

        self._separator()
        options = ttk.Frame(self.sidebar, style="Panel.TFrame")
        options.pack(fill="x", padx=22, pady=17)
        ttk.Label(options, text="MAP LAYERS", style="Muted.TLabel").pack(anchor="w", pady=(0, 7))
        ttk.Checkbutton(options, text="Road connections", variable=self.show_roads, command=self.draw).pack(anchor="w")
        ttk.Checkbutton(options, text="Geographic clusters", variable=self.show_clusters, command=self.draw).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(options, text="Show every city label", variable=self.show_all_labels, command=self.draw).pack(anchor="w", pady=(4, 0))
        controls = ttk.Frame(options, style="Panel.TFrame")
        controls.pack(fill="x", pady=(13, 0))
        ttk.Button(controls, text="−", width=3, style="Quiet.TButton", command=lambda: self.zoom(.82)).pack(side="left")
        ttk.Button(controls, text="Reset view", style="Quiet.TButton", command=self.reset_view).pack(side="left", padx=6, expand=True, fill="x")
        ttk.Button(controls, text="+", width=3, style="Quiet.TButton", command=lambda: self.zoom(1.22)).pack(side="right")

        about = ttk.Frame(self.sidebar, style="Panel.TFrame")
        about.pack(side="bottom", fill="x", padx=22, pady=18)
        ttk.Label(about, text=f"{len(self.model.cities)} cities  ·  {len(self.model.roads)} roads", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(about, text="Dijkstra · O((V + E) log V)", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))

        top = ttk.Frame(main)
        top.pack(fill="x", padx=20, pady=(16, 10))
        ttk.Label(top, text="Synthetic road network", font=("Segoe UI Semibold", 16), foreground=TEXT).pack(side="left")
        ttk.Label(top, textvariable=self.status_var, foreground=MUTED).pack(side="right")

        self.canvas = tk.Canvas(main, bg=BG, highlightthickness=1, highlightbackground="#1d3048", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda _: self.canvas.delete("tooltip"))

        self.legend = tk.Canvas(main, height=58, bg=BG, highlightthickness=0)
        self.legend.pack(fill="x", padx=20, pady=(0, 12))
        self.legend.bind("<Configure>", lambda _: self._draw_legend())

    def _separator(self) -> None:
        tk.Frame(self.sidebar, bg="#263a53", height=1).pack(fill="x", padx=22)

    def _screen(self, city: dict) -> tuple[float, float]:
        w, h = max(100, self.canvas.winfo_width()), max(100, self.canvas.winfo_height())
        margin = 28
        x = margin + city["x"] / 100 * (w - margin * 2)
        y = margin + city["y"] / 100 * (h - margin * 2)
        return ((x - w / 2) * self.scale_factor + w / 2 + self.offset_x,
                (y - h / 2) * self.scale_factor + h / 2 + self.offset_y)

    def draw(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        self.city_screen = {c["id"]: self._screen(c) for c in self.model.cities}
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(60, w, 90):
            self.canvas.create_line(x, 0, x, h, fill="#0d1a2a", width=1)
        for y in range(50, h, 90):
            self.canvas.create_line(0, y, w, y, fill="#0d1a2a", width=1)
        if self.show_roads.get():
            for road in self.model.roads:
                x1, y1 = self.city_screen[road["source"]]; x2, y2 = self.city_screen[road["target"]]
                self.canvas.create_line(x1, y1, x2, y2, fill="#38506a", width=self.model.line_width(road["weight"]), tags="road")
        if self.route_ids:
            for a, b in zip(self.route_ids, self.route_ids[1:]):
                x1, y1 = self.city_screen[a]; x2, y2 = self.city_screen[b]
                self.canvas.create_line(x1, y1, x2, y2, fill="#230c1b", width=8, capstyle="round")
                self.canvas.create_line(x1, y1, x2, y2, fill=ROUTE, width=4, capstyle="round")
        route_set = set(self.route_ids)
        for city in self.model.cities:
            x, y = self.city_screen[city["id"]]
            on_route = city["id"] in route_set
            radius = 4.0 if on_route else 2.2
            color = ROUTE if on_route else (CLUSTERS[city["cluster"] % len(CLUSTERS)] if self.show_clusters.get() else CYAN)
            if self.route_ids and city["id"] == self.route_ids[0]: color, radius = GREEN, 6
            if self.route_ids and city["id"] == self.route_ids[-1]: color, radius = AMBER, 6
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, fill=color, outline=BG if not on_route else TEXT,
                                    width=0 if not on_route else 1, tags=("city", f'city_{city["id"]}'))
            if self.show_all_labels.get() or on_route:
                self.canvas.create_text(x+7, y-7, text=city["name"], anchor="sw", fill=TEXT if on_route else MUTED,
                                        font=("Segoe UI", 8 if on_route else 7))
        self._draw_legend()

    def _draw_legend(self) -> None:
        if not hasattr(self, "legend"):
            return
        c = self.legend; c.delete("all")
        c.create_text(0, 8, text="ROAD WEIGHT  ·  line thickness mapping", anchor="nw", fill=MUTED, font=("Segoe UI", 8))
        values = [self.model.weight_min + (self.model.weight_max - self.model.weight_min) * i / 4 for i in range(5)]
        width = max(500, c.winfo_width())
        segment = min(145, (width - 220) / 5)
        for i, value in enumerate(values):
            x = 10 + i * segment
            c.create_line(x, 38, x + 55, 38, fill="#7892ad", width=self.model.line_width(value), capstyle="round")
            c.create_text(x + 63, 38, text=f"{value:.0f}", anchor="w", fill=TEXT, font=("Segoe UI", 8))
        x = min(width - 215, 10 + 5 * segment + 20)
        c.create_oval(x, 34, x+8, 42, fill=GREEN, outline="")
        c.create_text(x+13, 38, text="Start", anchor="w", fill=MUTED, font=("Segoe UI", 8))
        c.create_oval(x+65, 34, x+73, 42, fill=AMBER, outline="")
        c.create_text(x+78, 38, text="End", anchor="w", fill=MUTED, font=("Segoe UI", 8))
        c.create_line(x+123, 38, x+148, 38, fill=ROUTE, width=4)
        c.create_text(x+154, 38, text="Optimal", anchor="w", fill=MUTED, font=("Segoe UI", 8))

    def calculate_route(self) -> None:
        source, target = self.source_box.current(), self.target_box.current()
        if source == target:
            messagebox.showinfo("Choose two cities", "The start and destination must be different.")
            return
        self.config(cursor="watch"); self.update_idletasks()
        try:
            self.route_distance, self.route_ids = self.model.route(source, target)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            messagebox.showerror("Route engine error", str(exc)); return
        finally:
            self.config(cursor="")
        self.metric_route.set(f"{self.route_distance:.1f} units")
        self.metric_stops.set(str(len(self.route_ids)))
        self.status_var.set(f"Optimal route found · {len(self.route_ids)-1} road segments")
        self.draw()

    def clear_route(self) -> None:
        self.route_ids = []; self.route_distance = 0
        self.metric_route.set("—"); self.metric_stops.set("—")
        self.status_var.set("Route cleared — choose two cities")
        self.draw()

    def zoom(self, factor: float) -> None:
        self.scale_factor = max(.55, min(4.0, self.scale_factor * factor)); self.draw()

    def reset_view(self) -> None:
        self.scale_factor = 1.0; self.offset_x = self.offset_y = 0.0; self.draw()

    def _wheel(self, event) -> None:
        self.zoom(1.12 if event.delta > 0 else .89)

    def _drag_start(self, event) -> None:
        self.drag_origin = (event.x, event.y)

    def _drag_move(self, event) -> None:
        if self.drag_origin:
            self.offset_x += event.x - self.drag_origin[0]; self.offset_y += event.y - self.drag_origin[1]
            self.drag_origin = (event.x, event.y); self.draw()

    def _hover(self, event) -> None:
        nearest, best = None, 11.0
        for city_id, (x, y) in self.city_screen.items():
            d = math.hypot(event.x - x, event.y - y)
            if d < best: nearest, best = city_id, d
        self.canvas.delete("tooltip")
        if nearest is not None:
            city = self.model.by_id[nearest]
            self.canvas.create_rectangle(event.x+12, event.y-32, event.x+132, event.y-5,
                                         fill=PANEL_2, outline="#34506e", tags="tooltip")
            self.canvas.create_text(event.x+20, event.y-18, text=f'{city["name"]}  ·  #{nearest}',
                                    anchor="w", fill=TEXT, font=("Segoe UI", 9), tags="tooltip")


def ensure_engine_and_data() -> None:
    if not ENGINE.exists():
        raise FileNotFoundError(f"C++ engine not found at {ENGINE}. Run build.ps1 first.")
    DATA_DIR.mkdir(exist_ok=True)
    if not (DATA_DIR / "cities.csv").exists() or not (DATA_DIR / "roads.csv").exists():
        result = subprocess.run([str(ENGINE), "generate", str(DATA_DIR), "500", "42"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)


def main() -> int:
    try:
        ensure_engine_and_data()
        model = GraphModel(); model.load()
        app = RouteApp(model); app.mainloop()
        return 0
    except Exception as exc:
        try:
            root = tk.Tk(); root.withdraw(); messagebox.showerror("CityScope could not start", str(exc)); root.destroy()
        except tk.TclError:
            print(f"CityScope could not start: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
