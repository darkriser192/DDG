# DDG Toolkit

**DDG should make geometry computation inspectable, composable, replaceable, and extensible—not merely executable.**


An interactive mesh-analysis application built on [Polyscope](https://polyscope.run/),
used as a working platform for discrete differential geometry.

Load a triangle mesh, compute per-face and per-vertex quantities, and inspect them
as scalar, vector, and colour fields in a 3D viewer.

**Version 0.0.2** — early development. The API is unstable and the feature set is small by intent; correctness matters more here than coverage.

---

## What it does

| Operation | Produces |
|---|---|
| Compute Mesh Triangle Data | Per-face area, and vertex height along the up axis |
| Compute Mesh Dots vs FLOOR | Dot product and angle of each face normal against a reference direction |
| Compute Normal directions | Face normals as vectors and as an RGB colour field |
| Compute Vertex Error | Per-vertex angle defect — the discrete Gaussian curvature |

The angle defect is computed from scratch and checked against `trimesh`'s own
implementation on every call. That assertion is deliberate and permanent: it is
what makes the hand-written geometry safe to refactor.

---

## Requirements

- **Python 3.14** (`pyproject.toml` pins `== 3.14.*`)
- `numpy`, `scipy`, `trimesh`, `polyscope`
- `tkinter` for the file-open dialog — bundled with Python on Windows and macOS;
  on Debian/Ubuntu install `python3-tk`. It is part of the standard library, so
  there is nothing to install from PyPI
- A GPU with OpenGL support (Polyscope renders through it)

## Install

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install numpy scipy trimesh polyscope
```

## Run

```bash
python ddg_main.py
```

Run it from the repository root. `core` is a namespace package resolved against
the launch directory, so starting from elsewhere will not find it.

`ddg_main.py` pre-loads `meshes/rabbit-low-poly.stl` through the `DEFAULT_MESH`
constant. Set it to `None` to start with an empty viewer and load a mesh through
the GUI instead.

`ddg_poly.py` is also runnable on its own for prototyping the app layer without
the pre-load step:

```bash
python ddg_poly.py
```

## Tests

```bash
pip install pytest
pytest
```

The suite is headless — it never opens a viewer — and covers the math layer
against literal arrays, the `Geometry` container against the built-in
tetrahedron and the sample mesh, and the app layer through a recording stub that
stands in for a Polyscope surface mesh. Tests that need `meshes/rabbit-low-poly.stl`
skip when it is absent.

`Geometry(None)` builds a unit tetrahedron with no file I/O. It is the fixture
most of the suite is written against, and the quickest way to exercise the
mathematics from a REPL.

---

## Using the viewer

The controls appear in the panel on the right.

1. **Load Mesh** opens a file dialog. Any format `trimesh` reads works; STL is the
   usual case. The mesh registers under its filename stem.
2. **Working Mesh** selects which loaded mesh the operations act on. Several meshes
   can be loaded at once; only the selected one is operated on.
3. **Operation buttons** compute a quantity and attach it to the selected mesh.
   They can be pressed in any order — each computes its own prerequisites — and
   pressing one twice is harmless.
4. Displayed quantities appear in Polyscope's own structure panel, where you can
   switch between them, change colour maps, and adjust ranges.
5. **New Mesh Name** + **Save Mesh** exports the selected mesh to STL, relative to
   the working directory. An existing file is overwritten without warning.
6. **Unload** removes the selected mesh from both the viewer and memory.
7. **Debug Mode** toggles diagnostic output, including a per-attribute memory
   breakdown printed when a mesh loads.
8. **UI Scale** resizes the control panel. Clamped to 0.5–2.0.
9. **Vert, Edge, Face** takes three element IDs for **Compute vertex's star**.
   Both are scaffolding: the button prints the IDs it was given and computes
   nothing yet.

**Print … memory** is a placeholder. It prints "Not implemented".

---

## How the code is organised

```
ddg_main.py           entry point; clears the terminal, starts the app
ddg_poly.py           Polyscope layer: AppState, the @operation registry, the callback
ps_wrappers.py        thin wrappers over polyscope.imgui, with docstrings
AuxFunctions.py       timing and memory decorators, file dialog, helpers
core/
  ddg_objects.py      the Geometry container: holds a mesh and its derived quantities
  ddg_math.py         the mathematics: vectorized, pure, no mesh object required
  ddg_types.py        shared array type aliases
tests/                headless pytest suite, one module per source layer
meshes/               sample geometry
```

**Nothing under `core/` imports `ddg_poly.py`.** The dependency runs one way
only, so the mathematics can be exercised without a GUI. This is the main
structural decision in the project and the thing most worth preserving.

Inside `core/`, the same split runs once more: `ddg_math.py` holds free
functions over plain arrays, and `ddg_objects.py` calls them and stores the
results. The mathematics can therefore be tested without constructing a mesh at
all, which is how `tests/test_ddg_math.py` is written.

Adding an operation is one decorated function — the button is generated from the
registry, and the callback needs no edit:

```python
@operation("My Operation")
def _op_my_operation(mesh: Geometry, ps_mesh):
    mesh.compute_something()
    ps_mesh.add_scalar_quantity("Result", defined_on="faces", values=mesh.something)
```

---

## Current limitations

- The reference direction for the dot-product operation is a hardcoded key. A
  selector is planned; until then, only `FLOOR` (+Z) is reachable from the GUI.
- Adjacency structures and face centres are computed on request but nothing
  consumes them yet.
- Degenerate faces are not detected. A zero-area triangle does not crash — it is
  given a zero normal and zero area — but the angle defect at its corners is
  meaningless, and nothing flags it. A fully collapsed triangle, with all three
  corners at the same point, trips the corner-angle assertion in
  `compute_gaussian_curvature`.
- `ERR`, the tolerance used for degenerate-vector detection, is an absolute
  constant. It should be derived from mesh scale.
- Operations mutate the mesh and draw to Polyscope in the same function. Splitting
  those is a prerequisite for moving computation off the render thread.

## Acknowledgements

Discrete differential geometry follows Keenan Crane's
*[Discrete Differential Geometry: An Applied Introduction](https://www.cs.cmu.edu/~kmcrane/Projects/DDG/)*
(CMU 15-458), which is freely available. Mesh I/O and the validation oracle come
from [trimesh](https://github.com/mikedh/trimesh); the viewer is
[Polyscope](https://polyscope.run/) by Nicholas Sharp.
