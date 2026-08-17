# Reading List

Curated for this project's trajectory — DDG, robust meshing, SDFs/shaders, and
the software-craft to hold it together. Not a generic bibliography: ordered by
*when it becomes useful*, not by topic. See `PROJECT_CONTEXT.md` for the goals
these map to.

> **Guiding principle:** pull books off the shelf *just-in-time*, when the
> project reaches them — not before. Reading plumbing references ahead of need
> feeds anxiety without moving the work. The substance (DDG, meshing) is where
> the effort belongs.
>
> **The real bottleneck (from a shelf audit):** almost everything owned is
> *started-not-finished* (`S`). The growth edge is **depth, not breadth** — pick
> ONE and close it out before opening the next. Breadth is the comfort zone.

**Status legend:** R = read · R+ = repeat reads · S = started/skimmed ·
E = used for school · D = deferred/scared.

---

## Two insights from the shelf (technical leverage, not morale)

- **Pahl & Beitz = software architecture you already own.** *Engineering Design:
  A Systematic Approach* (R+, owned) IS a design methodology: requirements →
  function structure → concept → embodiment → detail. Software architecture is
  the same method in a different dialect (decompose function, manage coupling,
  design interfaces before details). The "architecture scares me" gap is a
  *filing error*, not a missing skill. Ousterhout (below) is just the translation.
- **DSP / Nyquist = the tessellation & SDF sampling framework.** The controls +
  signals core (Kirk, Discrete-Time Signal Processing, Harmonic Analysis, Linear
  Algebra) maps directly onto the geometry work: tessellation is *sampling a
  continuous surface*, so curvature-driven refinement is **spatial Nyquist** and
  under-refinement is **aliasing**. SDFs are fields/signals; grid evaluation is
  sampling, marching cubes is reconstruction. Re-read the DSP book through this
  lens — the toolkit is already owned, just not yet walked across.

---

## Start today (the spine) — *finish one before starting the next*

- [ ] **Keenan Crane — *Discrete Differential Geometry: An Applied Introduction***
  — FREE PDF (CMU course notes) + YouTube lectures (CMU 15-458). *The* DDG
  resource for exactly this profile. **Designated finish-target:** it's free,
  it's the spine, and completing it breaks the started-not-finished pattern.
- [ ] **Devadoss & O'Rourke — *Discrete and Computational Geometry*** — ✅ OWNED
  (S). A gem. Visual, rigorous, humane. Read *before* de Berg for CG intuition.
- [ ] **Ousterhout — *A Philosophy of Software Design*** — short, cheap.
  **Reframed:** not a new skill — it's Pahl & Beitz (which you re-read) in
  software dialect. A low-effort/high-leverage quick win, not a mountain.
- [ ] **Kaleniuk — *Geometry for Programmers*** (Manning) — ✅ OWNED (S), active.
  Keep going. The glue between math and code.

## Already owned — re-read with the new lens (free leverage)

- [ ] **Discrete-Time Signal Processing** (E, owned) — re-read the sampling /
  aliasing / reconstruction chapters *as meshing theory*. This is the
  tessellation-Nyquist framework; the toolkit is already yours.
- [ ] **Pahl & Beitz — *Engineering Design*** (R+, owned) — no re-read needed;
  just *apply* it to the software. It already answers "how do I architect this."

## Buy soon (daily drivers as the mesh toolkit grows)

- [ ] **Botsch, Kobbelt, Pauly, Alliez, Lévy — *Polygon Mesh Processing*** —
  highest-value *purchase* for right now. The practical bible: normals,
  curvature, adjacency, smoothing, remeshing. Bridges Crane's theory and the
  `MeshObject` code.
- [ ] **Slatkin — *Effective Python*** — closes the "not expert in Python idioms"
  gap. Bite-sized, immediately applicable to the scratchpad.

## Robustness & meshing (product 1 — the kernel)

- [ ] **Shewchuk — papers, FREE.** *"Robust Adaptive Floating-Point Geometric
  Predicates"* + "Lecture Notes on Geometric Robustness." The antidote to the
  robustness fear — turns a vague worry into known techniques.
- [ ] **Cheng, Dey, Shewchuk — *Delaunay Mesh Generation*** — rigorous,
  provably-correct meshing. Buy when actually building the tessellator.
- [ ] **de Berg et al. — *Computational Geometry: Algorithms and Applications***
  — ✅ OWNED. The formal companion/reference. Read *after* Devadoss, don't
  parallel them.

## SDF / shaders (product 2 — the modeler)

- [ ] **Inigo Quilez — iquilezles.org, FREE.** Re-read as a pipeline *builder*
  now, not a user. SDF primitives, smooth booleans, gradient normals, raymarch.
- [ ] **Jamie Wong — "Ray Marching and Signed Distance Functions," FREE blog.**
  Best from-scratch raymarching explainer. The "smallest spike" reading.
- [ ] **Pharr, Jakob, Humphreys — *Physically Based Rendering (PBRT)*, FREE
  online.** Encyclopedic. Reference, not cover-to-cover.
- [ ] **Akenine-Möller et al. — *Real-Time Rendering*** — the graphics bible.
  Skim the GPU-pipeline chapters to demystify moderngl/Polyscope.

## NURBS / B-rep spike

- [ ] **Piegl & Tiller — *The NURBS Book*** — *the* reference, dense. Buy only
  when committing to the pythonocc NURBS-reading spike.
- [ ] **Benedetto — *Harmonic Analysis and its Applications*** (D, owned) —
  **moved out of the scared pile.** Frequency-domain thinking about fields is
  relevant to SDF detail/filtering. Not urgent, but no longer "not for me."

## Requirements / "what am I building"

- [ ] **Gause & Weinberg — *Exploring Requirements: Quality Before Design*** —
  ✅ OWNED. Not geometry — figuring out *what* to build. Relevant to the open
  strategic questions (SDF/mesh boundary, minimum NURBS spike).

---

## Owned but deferred (don't feel you "should" be reading these yet)

- **Modern Vulkan Cookbook (Kakkar et al.)** — 🚩 the grueling-plumbing rabbit
  hole. Wrong layer for now; for SDFs you want a fragment/compute shader +
  moderngl or taichi, never raw Vulkan. Shelve until the project is big enough
  to justify it (a good problem to have, years out).
- **Modern CMake for C++ (Świdziński)** — for the *eventual* C++ core rewrite,
  not the Python learning phase. Boxed until actually compiling C++.
- **Math for Programmers (Orland)** — below current math level. Use as a
  Python-implementation reference for math already known; don't study it.

---

## The revised plan (post shelf-audit)

The old advice was "buy three." The new advice is **finish one, and stop
buying until you do.** Breadth is already covered; the shelf proves it.

1. **Finish Crane's free DDG notes.** One book, closed out, free. Breaks the
   started-not-finished pattern and lays the spine. This is the whole priority.
2. **Read Ousterhout in a weekend** — quick confidence win; it just renames
   design skills you already have (Pahl & Beitz).
3. **Buy exactly one:** *Polygon Mesh Processing*, when the toolkit work needs
   it — not before.

Everything else is just-in-time. The failure mode to avoid is acquiring more
than you finish.
