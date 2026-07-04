# CityScope — Graph Theory & Route Optimization

CityScope is a complete desktop project for studying a synthetic 500-city road network. The graph and shortest paths are handled in **C++**; the interactive visualization is written entirely in **Python/Tkinter**. There is no web application and no JavaScript.

## What it demonstrates

- A deterministic weighted, undirected graph with 500 city vertices and roughly 1,500 road edges
- Dijkstra's shortest-path algorithm using an adjacency list and min-priority queue
- Time complexity: `O((V + E) log V)`; graph storage: `O(V + E)`
- Interactive start/destination selection and a clearly highlighted optimal route
- Road thickness mapped to edge weight, with a visible scale below the map
- Optional geographic cluster coloring (deterministic k-means over city coordinates)
- Hover details, route metrics, labels, layer controls, zoom, and pan

## Quick start (Windows)

From PowerShell in this folder:

```powershell
.\build.ps1
.\run.ps1
```

The build script compiles `cpp/route_engine.cpp` with `g++` and generates `data/cities.csv` plus `data/roads.csv`. Python uses only its standard library; Tkinter is included with the usual python.org Windows installation.

## Controls

1. Select a starting city and destination.
2. Press **Find optimal route**.
3. The pink line is the computed route; green is the start and amber is the destination.
4. Scroll or use `+`/`−` to zoom. Drag the map to pan. Press `Esc` to clear the route.
5. Toggle **Geographic clusters** to inspect the spatial grouping of cities.

## C++ command line

```powershell
# Generate a graph (directory, number of cities, random seed)
.\bin\route_engine.exe generate .\data 500 42

# Find a path using zero-based city IDs
.\bin\route_engine.exe path .\data 0 499

# Print network statistics
.\bin\route_engine.exe stats .\data
```

The CSV format intentionally keeps the C++/Python boundary simple and inspectable.

## Verification

```powershell
python -m unittest discover -s tests -v
```

Tests cover graph size, valid IDs and positive weights, C++ route endpoints, same-city routes, network statistics, line-weight mapping, and all nine geographic clusters.

## Project structure

```text
cpp/route_engine.cpp          C++ graph generation, loading, Dijkstra, statistics
python/city_routes_gui.py     Tkinter visualization and C++ process integration
data/                         Generated city and road CSV files
tests/test_project.py         Integration and model tests
build.ps1                     One-command compiler/data build
run.ps1                       Desktop app launcher
```
