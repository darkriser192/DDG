# Project Context — Strategic

Seed context for planning / ideation. Strategic altitude only: goals, terms,
tools, study items, workflow, UX. Tactical/implementation learnings live in
`STYLE_NOTES.md`.

where possible, utilize ASD-STE100 simplified technical english guidelines

---

## Vision — two end products

1. **A free, open-source Polygonica competitor** — a robust B-rep → mesh
   tessellator / geometry kernel.
2. **An SDF modeler that uses shaders as the backend for both rendering *and*
   modeling** — shaders as the compute substrate for modeling, not just display.

## Guiding thesis

- **Rendering vs. analysis are separate objects.** Rendering = a (possibly
  non-watertight) surface mesh that still understands inside/outside. Analysis =
  **SDFs** for interior queries and internal values. This lets us *drop*
  watertightness/stitching as hard constraints and recover inside/outside from
  the SDF instead — offloading a hard topological invariant onto an
  easier-to-robustify field.
- **Correctness and robustness over memory.** Willing to spend RAM/compute for
  provably-correct results; do not trade correctness for memory frugality.
- **Robustness is the real differentiator.** Beating Polygonica is about
  robustness on dirty / degenerate / near-tangent B-reps, not the core
  tessellation math.
- **DDG is a means, not an end** — it's the toolkit for writing robust geometric
  algorithms. The mesher is both a goal and a stepping stone.
- **Scale-agnostic by principle.** Inputs arrive at arbitrary/unknown scale
  (esp. STL, which is unitless), so the system derives all thresholds from the
  geometry itself rather than absolute constants.

## Objectives (milestones, roughly ordered)

- Robust mesh analysis toolkit (curvature, normals, adjacency) — *in progress*.
- Interactive viewer/analysis app (load, inspect, compare meshes).
- Read raw NURBS/B-rep from STEP/IGES (not just pre-tessellated meshes).
- Prototype an adaptive / curvature-driven tessellator from raw surfaces.
- SDF layer: represent interior/fields; move toward shader-backed evaluation.
- Shader-backed SDF modeling (the second product).

## Terms / glossary

- **B-rep** — boundary representation: exact NURBS + analytic surfaces +
  topology (what CAD kernels store; what STEP contains).
- **NURBS** — the exact parametric surfaces inside a B-rep.
- **Tessellation** — converting exact surfaces into a triangle mesh
  (approximation; quality is a tunable parameter).
- **Watertight / manifold** — a sealed mesh; the classic prerequisite for
  inside/outside tests (deliberately being dropped here in favor of SDF).
- **SDF** — signed distance field; gives continuous inside/outside + distance,
  natural fit for shader evaluation.
- **DDG** — discrete differential geometry; discrete analogues of curvature,
  Laplacians, etc. for robust algorithms on meshes.
- **Polygonica** — commercial robust meshing/geometry SDK; the benchmark to beat.

## Libraries — in use

- **trimesh** — mesh loading + geometry utilities (curvature, adjacency, graphs).
- **polyscope** (+ imgui) — interactive 3D viewer and GUI.
- **numpy / scipy** — vectorized math, sparse adjacency.

## Libraries — candidates / to evaluate

- **`pythonocc-core`** — direct OpenCASCADE bindings; **the** path to raw NURBS
  from STEP/IGES (required for a custom tessellator).
- **`cascadio`** — easy STEP/IGES load (via OCCT → glTF), but **pre-tessellated**
  (no NURBS access). Good for quick import, not for the kernel goal.
- **gmsh / meshio** — STEP reading + meshing with element-size control;
  format interchange.
- **FreeCAD** (Python API) — full OCCT, scriptable CAD ops.
- **SDF / shader stack** — TBD (e.g. moderngl / taichi / raw GLSL / compute
  shaders) for the shader-backed SDF product.

## Study items

- DDG: discrete curvature (Gaussian/mean), cotangent Laplacian, discrete
  operators, convergence/robustness.
- Tessellation theory: adaptive subdivision, curvature-driven refinement,
  trimmed-surface handling, robustness on degenerate input.
- SDF construction from meshes/surfaces; boolean/field operations; rendering
  (raymarching) and *modeling* on the GPU.
- NURBS evaluation and B-rep topology traversal (via OCCT).

## Workflow

- Source geometry from CAD (SolidWorks / 3DXpert available). Export options:
  **3MF** (units baked in) or STL (unitless) for meshes; **STEP** for exact
  B-rep to tessellate in-code later.
- Iterate in a scratch pipeline (`DDG_scratchpad.py` + `AuxFunctions.py`), visualize
  in Polyscope.
- Prefer feeding unit-carrying formats (3MF) when scale matters; otherwise rely
  on scale-agnostic derivation.

## User experience (target)

- Load multiple meshes, keep them in memory, and **register/show on demand**
  (loaded ≠ displayed) — e.g. a name dropdown + toggle.
- Inspect scalar fields (area, curvature, normals-vs-reference) interactively.
- Longer term: an SDF modeling UX where operations are field edits evaluated on
  the GPU, with the mesh as the surface view and the SDF as the source of truth
  for interior/analysis.

## Open strategic questions

- Where is the boundary between the mesh object and the SDF object in the data
  model? (surface vs. field ownership)
- What's the minimum viable NURBS-reading spike to de-risk the tessellator?
- Which shader/compute stack for SDFs, and how early to commit to it?
