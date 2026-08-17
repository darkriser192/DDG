# Style & Tactical Notes

Implementation-level learnings and conventions. Not strategic — see
`PROJECT_CONTEXT.md` for goals. Reference this when coding, not when planning.

Where possible stick to ASD-STE100 simplified english guidelines

---

## Coding conventions

- **Enforce what must stay true; document the rest.** Put invariants into things
  that fail when violated (type annotations, `assert`, tests). Reserve docstrings
  for intent, "why", gotchas, and math references — not restating the code.
- **Docstrings drift; guard against it.** Keep `DOCSTRING_TEMPLATE.md`
  authoritative; treat "update docstrings to match code" as a periodic pass.
- **Scale-relative constants only.** Any hardcoded length (radius, tolerance,
  coordinate epsilon) is a latent scale bug. Derive from `mesh.scale` (AABB
  diagonal) or an edge-length statistic instead of a magic number.

## Python craft

- `@decorator` syntax only applies to `def` / `class`. Elsewhere apply manually
  (`fn = deco()(fn)`), or use a **context manager** to time a block/assignment.
- Don't decorate a **class** with a function-style decorator — it replaces the
  name with a function and breaks `isinstance`/subclassing. Decorate `__init__`.
- `assert` = internal sanity / type-narrowing (e.g.
  `assert isinstance(self.Geometry, trimesh.Trimesh)` to drop `# type: ignore`),
  NOT input validation (stripped under `python -O`). Never `assert(cond, msg)` —
  that asserts a truthy tuple.

## Polyscope / GUI

- Immediate-mode callback runs ~30x/sec: gate heavy work behind button guards;
  disable timing on the callback.
- Polyscope **auto-normalizes the view** — on-screen size is not a reliable
  signal of coordinate scale; read the length-scale/bbox instead.
- Persistent UI/app state lives in a module-level dict (`app_state`) that
  survives frames. Store meshes as a **dict keyed by name**.
- **Don't duplicate state Polyscope owns** — registration status
  (`ps.has_surface_mesh`) and live gizmo transforms (`ps_mesh.get_transform()`).
  Let ps own live state; `app_state` holds only what ps can't tell you.
- Open decision: flat vs nested `app_state["Meshes"]` entries. Nesting
  (`{"MeshObject":..., "Transforms":{...}}`) keeps a mesh and its transform
  together and avoids parallel-dict desync.

## Tkinter file dialog (inside a render loop)

- Creating/destroying a `tk.Tk()` root per call inside a GL render loop crashes
  on repeat. Use a **lazy singleton** hidden root, created once and never
  destroyed; return `None` on cancel (don't `raise SystemExit`).
- Not destroying a root does NOT leak past process exit, but DOES accumulate in a
  long-lived Jupyter kernel — the singleton handles both.
- Deeper: a modal Tk loop inside a GL/ImGui loop is inherently fragile. Long-term,
  move the dialog out of the render loop or use an in-GUI (ImGui) picker.

## File formats / units

- **STL is unitless** (free-form 80-byte header; coords are bare numbers;
  convention is mm). **3MF / AMF / STEP / glTF** carry or convention units.
- STEP/IGES are exact B-rep — need a CAD kernel (OpenCASCADE) to tessellate;
  trimesh never holds the B-rep. `mesh.units` is `None` for STL.
- CAD tessellation yields anisotropic triangles (slivers on flats, dense at
  fillets) — treat tessellation quality as an experiment parameter, since it
  changes discrete-curvature results.
