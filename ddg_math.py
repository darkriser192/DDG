"""ddg_math will become the file containing the fundamental
discrete geomerty ath operations. should be as close to "pure"
as possible

utilizes numpy and scipy as the bckbone of the system
"""
# Imports
## Standard library imports
from collections.abc import Sequence
# from typing import Literal, TypedDict

import numpy as np
import numpy.typing as npt
import scipy as sp

## Custom Imports
import AuxFunctions as aux

# Module Constants
### Global Constants
DEBUG: bool = False # Debug flag to print some items as I code
TIMED: bool = False # Debug flag to print time estimates of functions
MEMORY: bool = False # Debug flag for memory probing
ERR: float = 1e-8 # Defines a global error value for some computations

### Type Aliases
FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]
SparseMatrix = sp.sparse.csr_matrix

# Support Functions
@aux.timed(TIMED)
@aux.memory(MEMORY)
def vector_values(vectors: FloatArray) -> tuple[FloatArray, FloatArray]:
    """
    Compute the magnitude and unit direction of a batch of vectors.

    Safe against zero-length vectors: rows with magnitude below ``ERR`` get a
    zero direction instead of producing ``NaN`` or a divide-by-zero warning.

    Parameters
    ----------
    vectors : numpy.ndarray, shape (N, 3)
        Stack of N vectors, one per row.

    Returns
    -------
    magnitude : numpy.ndarray, shape (N,)
        Euclidean norm of each input vector (unmodified, including zeros).
    direction : numpy.ndarray, shape (N, 3)
        Unit vector per row; rows whose magnitude is below ``ERR`` are set to
        the zero vector.

    Notes
    -----
    ``ERR`` is the module-level threshold (Reference document global variables).
    """
    magnitude = np.linalg.norm(vectors, axis=1)
    valid_mask = magnitude >= ERR
    safe_mag = np.where(valid_mask, magnitude, 1.0)
    direction = vectors / safe_mag[:, np.newaxis]
    direction[~valid_mask] = 0.0

    return magnitude, direction

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_triangle_data(triangles: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """
    Compute per-face edges, normals, normal magnitudes, and areas.

    Fully vectorized over all faces. Edges are taken in winding order; the
    face normal is the cross product of two edges sharing vertex 0, and the
    area is half the magnitude of that cross product.

    Parameters
    ----------
    triangles : numpy.ndarray, shape (F, 3, 3)
        Per-face vertex coordinates, indexed as ``[face, corner, xyz]`` (i.e.
        ``mesh.vertices[mesh.faces]``).

    Returns
    -------
    normal : numpy.ndarray, shape (F, 3)
        Unit face normal (zero for degenerate faces; see :func:`vector_values`).
    normal_magnitude : numpy.ndarray, shape (F,)
        Magnitude of the raw cross product, i.e. twice the face area.
    areas : numpy.ndarray, shape (F,)
        Face area (``normal_magnitude / 2``).
    edges : numpy.ndarray, shape (F, 3, 3)
        The three edge vectors per face, stacked edge-index first:
        ``edges[:,0]`` = v1-v0, ``edges[:,1]`` = v2-v1, ``edges[:,2]`` = v0-v2.

    Notes
    -----
    Degenerate (zero-area) faces yield a zero normal and zero area without
    raising or emitting divide warnings, thanks to :func:`vector_values`.
    """
    if DEBUG:
        print(f"Triangles:\n{triangles}")

    ## Computes Edges
    edge1 = triangles[:,1] - triangles[:,0] # Vertex 0 to Vertex 1
    edge2 = triangles[:,2] - triangles[:,1] # Vertex 1 to Vertex 2
    edge3 = triangles[:,0] - triangles[:,2] # Vertex 0 to Vertex 3

    edges = np.stack([edge1, edge2, edge3], axis=1)

    if DEBUG:
        print(f"Edges:\n {edges}")

    ## Computes the face values
    cross_products = np.cross(edge1, -1 * edge3)
    normal_magnitude, normal = vector_values(cross_products)
    areas = normal_magnitude / 2  # zeros already handled by vector_values

    return normal, normal_magnitude, areas, edges

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_face_center_3d(vertex: FloatArray) -> FloatArray:
    """Compute the centroid of each triangular face.

    Vectorized over all faces: averages the three corner vertices of each
    triangle along the corner axis.

    Parameters
    ----------
    Vertex : numpy.ndarray, shape (F, 3, 3)
        Per-face vertex coordinates, indexed as ``[face, corner, xyz]``
        (i.e. ``mesh.vertices[mesh.faces]``).

    Returns
    -------
    centers : numpy.ndarray, shape (F, 3)
        Centroid (mean of the three corners) of each face.
    """
    ## Computes face centers
    centers = np.mean(vertex, axis=1)

    return centers

@aux.timed(TIMED)
@aux.memory(MEMORY)
def check_normal_direction(normals: FloatArray,
                           reference: FloatArray,
                           angle: bool = False) -> tuple[FloatArray, FloatArray | None]:
    """Compare face normals against a single reference direction.

    Computes the dot product of every normal with a reference vector and,
    optionally, the corresponding angle.

    Parameters
    ----------
    normals : numpy.ndarray, shape (F, 3)
        Unit face normals, one per row.
    reference : numpy.ndarray, shape (3,)
        Direction to compare against (e.g. ``FLOOR``). Assumed unit length so
        the dot product reads as ``cos θ``.
    angle : bool, optional
        If True, also return the angle (radians) between each normal and
        ``reference``. Defaults to False, in which case ``angles`` is ``None``.

    Returns
    -------
    dots : numpy.ndarray, shape (F,)
        Dot product of each normal with ``reference``.
    angles : numpy.ndarray or None, shape (F,)
        Per-face angle in radians when ``angle`` is True, otherwise ``None``.

    Notes
    -----
    
    """

    dots = np.dot(normals, reference)

    if DEBUG:
        print("Dots: \n", dots)

    angles = None

    if angle:
        angles = np.arccos(np.clip(dots, -1.0, 1.0))

    return dots, angles

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_gausian_curvature(edges: FloatArray,
                              faces: IntArray,
                              num_verts: int) -> tuple[FloatArray, FloatArray, FloatArray]:
    """
    Computes the per-vertex gausian curvature error
    """
    _, a_n = vector_values(edges[:,0])
    _, b_n = vector_values(edges[:,1])
    _, c_n = vector_values(edges[:,2])

    def corner_angle(a: FloatArray, b: FloatArray) -> FloatArray:
        cos = (a * b).sum(axis=1)
        return np.arccos(np.clip(cos, -1.0, 1.0))

    print("computing curvature edges")
    angle0 = corner_angle( a_n, -c_n)   # at v0
    angle1 = corner_angle(-a_n,  b_n)   # at v1
    angle2 = corner_angle( c_n, -b_n)   # at v2
    if DEBUG:
        print(f"angle0 (deg):\n {np.degrees(angle0)}")
        print(f"angle1 (deg):\n {np.degrees(angle1)}")
        print(f"angle2 (deg):\n {np.degrees(angle2)}")

    corner_angles = np.stack([angle0, angle1, angle2], axis=1)   # (F, 3)

    assert np.allclose(corner_angles.sum(axis=1), np.pi, atol=1e-6)

    angle_sum = np.bincount(
        faces.ravel(),
        weights =corner_angles.ravel(),
        minlength =num_verts
        )

    gaussian_error = 2*np.pi - angle_sum

    ratio = (1 / (2*np.pi)) * gaussian_error

    return gaussian_error, corner_angles, ratio

## Utility Functions #1 hand coded star, closure and link functions
def _as_index_triple(
        simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Coerce a ``(vertices, edges, faces)`` triple to flat int64 arrays.

    Guards the set operators against empty Python lists, which numpy would
    otherwise turn into ``float64`` arrays and propagate into every index.
    """
    vertices, edge_ids, face_ids = (
        np.asarray(s, dtype=np.int64).ravel() for s in simplices)
    return vertices, edge_ids, face_ids

def unique_face_vertices(edges: IntArray, face_edges: IntArray) -> IntArray:
    """Return the three vertex IDs of each face, ascending.

    Parameters
    ----------
    edges : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edges : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face.

    Returns
    -------
    face_vertices : numpy.ndarray, shape (F, 3)
        Vertex IDs per face, ascending.

    Notes
    -----
    A face's three edges contribute six endpoints, and on a valid triangle each
    of the three vertices appears in exactly two of them. Sorting each row and
    taking every other entry therefore drops the duplicates.

    ``np.unique(..., axis=1)`` cannot do this: it deduplicates whole columns
    across every face at once, so it returns the input unchanged with shape
    ``(F, 3, 2)``. Numpy has no vectorised per-row unique.
    """
    endpoints = np.sort(edges[face_edges].reshape(len(face_edges), -1), axis=1)
    return endpoints[:, ::2]

def reference_simplex_closure(
        edges: IntArray,
        face_edges: IntArray,
        simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Return the closure of a set of simplices.

    ``Cl(S)`` is the smallest simplicial complex containing ``S``: every simplex
    of ``S`` together with all of its faces.

    Parameters
    ----------
    edges : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edges : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face, in winding order.
    simplices : tuple of numpy.ndarray
        ``(vertices, edges, faces)`` -- three arrays of indices, any of which
        may be empty.

    Returns
    -------
    closure : tuple of numpy.ndarray
        ``(vertices, edges, faces)`` of the closure, each sorted and unique.

    Notes
    -----
    **Closure only descends in dimension.** A face contributes its three edges
    and its three vertices; an edge contributes its two endpoints; a vertex
    contributes itself. Nothing is ever added at a higher dimension -- that is
    :func:`reference_simplex_star`.
    """
    vertices, edge_ids, face_ids = _as_index_triple(simplices)

    closure_faces = np.unique(face_ids)

    closure_edges = np.unique(np.concatenate([
        edge_ids,
        face_edges[closure_faces].ravel(),
        ]))

    # The endpoints of closure_edges already include every vertex of every face
    # in face_ids, because those faces contributed their edges above.
    closure_vertices = np.unique(np.concatenate([
        vertices,
        edges[closure_edges].ravel(),
        ]))

    return closure_vertices, closure_edges, closure_faces

def reference_simplex_star(
        edges: IntArray,
        face_edges: IntArray,
        simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Return the star of a set of simplices.

    ``St(S) = { t : s is a face of t, for some s in S }`` -- every simplex that
    *contains* an input simplex.

    Parameters
    ----------
    edges : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edges : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face, in winding order.
    simplices : tuple of numpy.ndarray
        ``(vertices, edges, faces)`` -- three arrays of indices, any of which
        may be empty.

    Returns
    -------
    star : tuple of numpy.ndarray
        ``(vertices, edges, faces)`` of the star, each sorted and unique.

    Notes
    -----
    **Star only ascends in dimension.** The input vertices pass through
    unchanged, because nothing except a vertex itself can both contain a vertex
    and be one.

    Two tempting additions are wrong. Given ``St(v)``: the *other* endpoints of
    the incident edges are not in the star, and the other edges of the incident
    faces are not either -- neither of those contains ``v``. Descending is what
    :func:`reference_simplex_closure` does.

    The star of a set is generally not a complex; its closure is.
    """
    vertices, edge_ids, face_ids = _as_index_triple(simplices)

    face_vertices = unique_face_vertices(edges, face_edges)

    star_edges = np.unique(np.concatenate([
        edge_ids,
        np.flatnonzero(np.isin(edges, vertices).any(axis=1)),
        ]))

    star_faces = np.unique(np.concatenate([
        face_ids,
        np.flatnonzero(
            np.isin(face_edges, edge_ids).any(axis=1)
            | np.isin(face_vertices, vertices).any(axis=1)),
        ]))

    return np.unique(vertices), star_edges, star_faces

def reference_simplex_link(
        edges: IntArray,
        face_edges: IntArray,
        simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Return the link of a set of simplices.

    ``Lk(S) = Cl(St(S))`` minus ``St(Cl(S))`` -- the boundary of the neighbourhood of
    ``S``, with ``S`` and everything touching it removed.

    Parameters
    ----------
    edges : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edges : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face, in winding order.
    simplices : tuple of numpy.ndarray
        ``(vertices, edges, faces)`` -- three arrays of indices, any of which
        may be empty.

    Returns
    -------
    link : tuple of numpy.ndarray
        ``(vertices, edges, faces)`` of the link, each sorted and unique.

    Notes
    -----
    The subtracted term is ``St(Cl(S))``, **not** ``St(S)``. The two coincide
    only when ``Cl(S) == S``, which holds for a set of vertices and fails as
    soon as an edge or a face is present. The link of a single vertex is
    therefore the same under either form, while the link of an edge is not:
    using ``St(S)`` leaves the edge's own endpoints in the result.

    On a closed triangle mesh the link of an interior vertex is its one-ring
    boundary: a cycle of vertices and edges, with no faces.
    """
    star_of_s = reference_simplex_star(edges, face_edges, simplices)
    closure_of_star = reference_simplex_closure(edges, face_edges, star_of_s)

    closure_of_s = reference_simplex_closure(edges, face_edges, simplices)
    star_of_closure = reference_simplex_star(edges, face_edges, closure_of_s)

    link_vertices, link_edges, link_faces = (
        np.setdiff1d(outer, inner)
        for outer, inner in zip(closure_of_star, star_of_closure))

    return link_vertices, link_edges, link_faces

### Geometric Functions
@aux.timed(TIMED)
@aux.memory(MEMORY)
def normalize(minmax: Sequence[float], value: float | FloatArray) -> float | FloatArray:
    """Map a value onto the [0, 1] span defined by a (min, max) pair.

    Linear rescale reporting where ``value`` falls between ``minmax[0]`` and
    ``minmax[1]``. The result is intentionally *not* clamped, so values outside
    the range map below 0 or above 1 — which lets it act as a cross-item scale
    comparator.

    Parameters
    ----------
    minmax : sequence of float, length 2
        The ``(min, max)`` endpoints defining the span. ``minmax[1] ==
        minmax[0]`` yields a division by zero.
    value : float or numpy.ndarray
        Value(s) to normalize; broadcasts if an array is passed.

    Returns
    -------
    float or numpy.ndarray
        ``(value - minmax[0]) / (minmax[1] - minmax[0])``, unclamped.

    Notes
    -----
    Useful for comparing a value against a range taken from a *different* item,
    where out-of-[0, 1] results carry meaning.
    """

    span = minmax[1] - minmax[0]
    progress = value - minmax[0]
    normalized = progress/span
    return normalized

# Main entry point
if __name__ == "__main__":
    print("Main Entry Point")

    print("Main Exit point")
