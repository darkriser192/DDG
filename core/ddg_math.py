"""ddg_math will become the file containing the fundamental
discrete geometry and operations. should be as close to "pure"
as possible

utilizes numpy and scipy as the backbone of the system
"""
# Imports
## Standard library imports
from collections.abc import Sequence
import numpy as np

## Custom Imports
from core.ddg_types import FloatArray, IntArray
import core.AuxFunctions as aux

# Module Constants
### Global Constants
DEBUG: bool = False # Debug flag to print some items as I code
TIMED: bool = False # Debug flag to print time estimates of functions
MEMORY: bool = False # Debug flag for memory probing
ERR: float = 1e-8 # Defines a global error value for some computations

# Support Functions
@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_vector_values(vectors: FloatArray) -> tuple[FloatArray, FloatArray]:
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
    magnitude = np.linalg.norm(vectors, axis=-1)
    valid_mask = magnitude >= ERR
    safe_mag = np.where(valid_mask, magnitude, 1.0)
    direction = vectors / safe_mag[..., np.newaxis]
    direction[~valid_mask] = 0.0

    return magnitude, direction

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_triangle_data(triangle_coordinates: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, FloatArray]:
    """
    Compute per-face normals, areas, and edge lengths and directions.

    Fully vectorized over all faces. Edges are taken in winding order; the
    face normal is the cross product of two edges sharing vertex 0, and the
    area is half the magnitude of that cross product.

    Parameters
    ----------
    triangle_coordinates : numpy.ndarray, shape (F, 3, 3)
        Per-face vertex coordinates, indexed as ``[face, corner, xyz]`` (i.e.
        ``mesh.vertices[mesh.faces]``).

    Returns
    -------
    normal : numpy.ndarray, shape (F, 3)
        Unit face normal (zero for degenerate faces; see :func:`compute_vector_values`).
    normal_magnitudes : numpy.ndarray, shape (F,)
        Magnitude of the raw cross product, i.e. twice the face area.
    areas : numpy.ndarray, shape (F,)
        Face area (``normal_magnitudes / 2``).
    edge_magnitudes : numpy.ndarray, shape (F, 3)
        Length of each of the three edges per face.
    edge_directions : numpy.ndarray, shape (F, 3, 3)
        Unit edge vectors, stacked edge-index first, in winding order:
        index 0 = v1-v0, index 1 = v2-v1, index 2 = v0-v2. Zero for a
        degenerate edge.

    Notes
    -----
    Degenerate (zero-area) faces yield a zero normal and zero area without
    raising or emitting divide warnings, thanks to :func:`compute_vector_values`.
    """
    if DEBUG:
        print(f"Triangles:\n{triangle_coordinates}")

    ## Computes Edges
    edge1 = triangle_coordinates[:,1] - triangle_coordinates[:,0] # Vertex 0 to Vertex 1
    edge2 = triangle_coordinates[:,2] - triangle_coordinates[:,1] # Vertex 1 to Vertex 2
    edge3 = triangle_coordinates[:,0] - triangle_coordinates[:,2] # Vertex 0 to Vertex 3

    edge_vectors = np.stack([edge1, edge2, edge3], axis=1)

    edge_magnitudes, edge_directions = compute_vector_values(edge_vectors)

    if DEBUG:
        print(f"Edges:\n {edge_vectors}")

    ## Computes the face values
    cross_products = np.cross(edge1, -1 * edge3)
    normal_magnitudes, normal = compute_vector_values(cross_products)
    areas = normal_magnitudes / 2  # zeros already handled by compute_vector_values

    return normal, normal_magnitudes, areas, edge_magnitudes, edge_directions

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_face_centers(triangle_coordinates: FloatArray) -> FloatArray:
    """Compute the centroid of each triangular face.

    Vectorized over all faces: averages the three corner vertices of each
    triangle along the corner axis.

    Parameters
    ----------
    triangle_coordinates : numpy.ndarray, shape (F, 3, 3)
        Per-face vertex coordinates, indexed as ``[face, corner, xyz]``
        (i.e. ``mesh.vertices[mesh.faces]``).

    Returns
    -------
    centers : numpy.ndarray, shape (F, 3)
        Centroid (mean of the three corners) of each face.
    """
    ## Computes face centers
    centers = np.mean(triangle_coordinates, axis=1)

    return centers

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_normal_direction(normals: FloatArray,
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
    ``reference`` is not normalized here. A non-unit reference rescales every
    dot product, and the angle then reads as ``arccos`` of a value that is no
    longer a cosine.

    The dot products are clipped to [-1, 1] before ``arccos``, so a normal a
    hair outside unit length from rounding yields 0 or pi rather than NaN.
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
def compute_gaussian_curvature(edge_directions: FloatArray,
                               face_vertex_ids: IntArray,
                               number_vertices: int) -> tuple[FloatArray, FloatArray, FloatArray]:
    """
    Computes the per-vertex gaussian curvature error
    """
    def corner_angle(a: FloatArray, b: FloatArray) -> FloatArray:
        cos = (a * b).sum(axis=1)
        return np.arccos(np.clip(cos, -1.0, 1.0))

    if DEBUG:
        print("computing curvature")
    angle0 = corner_angle( edge_directions[:,0], -edge_directions[:,2])   # at v0
    angle1 = corner_angle(-edge_directions[:,0],  edge_directions[:,1])   # at v1
    angle2 = corner_angle( edge_directions[:,2], -edge_directions[:,1])   # at v2
    if DEBUG:
        print(f"angle0 (deg):\n {np.degrees(angle0)}")
        print(f"angle1 (deg):\n {np.degrees(angle1)}")
        print(f"angle2 (deg):\n {np.degrees(angle2)}")

    corner_angles = np.stack([angle0, angle1, angle2], axis=1)   # (F, 3)

    assert np.allclose(corner_angles.sum(axis=1), np.pi, atol=1e-6)

    angle_sum = np.bincount(
        face_vertex_ids.ravel(),
        weights =corner_angles.ravel(),
        minlength =number_vertices
        )

    gaussian_error = 2*np.pi - angle_sum

    ratio = (1 / (2*np.pi)) * gaussian_error

    return gaussian_error, corner_angles, ratio

## Utility Functions #1 hand coded star, closure and link functions
def _as_index_triple(
    simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Coerce a ``(vertices, edge_vertex_ids, faces)`` triple to flat int64 arrays.

    Guards the set operators against empty Python lists, which numpy would
    otherwise turn into ``float64`` arrays and propagate into every index.
    """
    vertices, edge_ids, face_ids = (
        np.asarray(s, dtype=np.int64).ravel() for s in simplices)
    return vertices, edge_ids, face_ids

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_face_vertex_ids(edge_vertex_ids: IntArray,
                            face_edge_ids: IntArray) -> IntArray:
    """Return the three vertex IDs of each face, ascending.

    Parameters
    ----------
    edge_vertex_ids : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edge_ids : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face.

    Returns
    -------
    face_vertices : numpy.ndarray, shape (F, 3)
        Vertex IDs per face, ascending.

    Notes
    -----
    A face's three edge_vertex_ids contribute six endpoints, and on a valid triangle each
    of the three vertices appears in exactly two of them. Sorting each row and
    taking every other entry therefore drops the duplicates.

    ``np.unique(..., axis=1)`` cannot do this: it deduplicates whole columns
    across every face at once, so it returns the input unchanged with shape
    ``(F, 3, 2)``. Numpy has no vectorised per-row unique.
    """
    endpoints = np.sort(edge_vertex_ids[face_edge_ids].reshape(len(face_edge_ids), -1), axis=1)
    return endpoints[:, ::2]

def reference_simplex_closure(
    edge_vertex_ids: IntArray,
    face_edge_ids: IntArray,
    simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Return the closure of a set of simplices.

    ``Cl(S)`` is the smallest simplicial complex containing ``S``: every simplex
    of ``S`` together with all of its faces.

    Parameters
    ----------
    edge_vertex_ids : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edge_ids : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face, in winding order.
    simplices : tuple of numpy.ndarray
        ``(vertices, edge_vertex_ids, faces)`` -- three arrays of indices, any of which
        may be empty.

    Returns
    -------
    closure : tuple of numpy.ndarray
        ``(vertices, edge_vertex_ids, faces)`` of the closure, each sorted and unique.

    Notes
    -----
    **Closure only descends in dimension.** A face contributes its three edge_vertex_ids
    and its three vertices; an edge contributes its two endpoints; a vertex
    contributes itself. Nothing is ever added at a higher dimension -- that is
    :func:`reference_simplex_star`.
    """
    vertices, edge_ids, face_ids = _as_index_triple(simplices)

    closure_faces = np.unique(face_ids)

    closure_edges = np.unique(np.concatenate([
        edge_ids,
        face_edge_ids[closure_faces].ravel(),
        ]))

    # The endpoints of closure_edges already include every vertex of every face
    # in face_ids, because those faces contributed their edge_vertex_ids above.
    closure_vertices = np.unique(np.concatenate([
        vertices,
        edge_vertex_ids[closure_edges].ravel(),
        ]))

    return closure_vertices, closure_edges, closure_faces

def reference_simplex_star(
        edge_vertex_ids: IntArray,
        face_edge_ids: IntArray,
        simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Return the star of a set of simplices.

    ``St(S) = { t : s is a face of t, for some s in S }`` -- every simplex that
    *contains* an input simplex.

    Parameters
    ----------
    edge_vertex_ids : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edge_ids : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face, in winding order.
    simplices : tuple of numpy.ndarray
        ``(vertices, edge_vertex_ids, faces)`` -- three arrays of indices, any of which
        may be empty.

    Returns
    -------
    star : tuple of numpy.ndarray
        ``(vertices, edge_vertex_ids, faces)`` of the star, each sorted and unique.

    Notes
    -----
    **Star only ascends in dimension.** The input vertices pass through
    unchanged, because nothing except a vertex itself can both contain a vertex
    and be one.

    Two tempting additions are wrong. Given ``St(v)``: the *other* endpoints of
    the incident edge_vertex_ids are not in the star, and the other edge_vertex_ids of the incident
    faces are not either -- neither of those contains ``v``. Descending is what
    :func:`reference_simplex_closure` does.

    The star of a set is generally not a complex; its closure is.
    """
    vertices, edge_ids, face_ids = _as_index_triple(simplices)

    face_vertices = compute_face_vertex_ids(edge_vertex_ids, face_edge_ids)

    star_edges = np.unique(np.concatenate([
        edge_ids,
        np.flatnonzero(np.isin(edge_vertex_ids, vertices).any(axis=1)),
        ]))

    star_faces = np.unique(np.concatenate([
        face_ids,
        np.flatnonzero(
            np.isin(face_edge_ids, edge_ids).any(axis=1)
            | np.isin(face_vertices, vertices).any(axis=1)),
        ]))

    return np.unique(vertices), star_edges, star_faces

def reference_simplex_link(
        edge_vertex_ids: IntArray,
        face_edge_ids: IntArray,
        simplices: tuple[IntArray, IntArray, IntArray]) -> tuple[IntArray, IntArray, IntArray]:
    """Return the link of a set of simplices.

    ``Lk(S) = Cl(St(S))`` minus ``St(Cl(S))`` -- the boundary of the neighbourhood of
    ``S``, with ``S`` and everything touching it removed.

    Parameters
    ----------
    edge_vertex_ids : numpy.ndarray, shape (E, 2)
        Canonical edge list, each row sorted low -> high.
    face_edge_ids : numpy.ndarray, shape (F, 3)
        The three edge IDs of each face, in winding order.
    simplices : tuple of numpy.ndarray
        ``(vertices, edge_vertex_ids, faces)`` -- three arrays of indices, any of which
        may be empty.

    Returns
    -------
    link : tuple of numpy.ndarray
        ``(vertices, edge_vertex_ids, faces)`` of the link, each sorted and unique.

    Notes
    -----
    The subtracted term is ``St(Cl(S))``, **not** ``St(S)``. The two coincide
    only when ``Cl(S) == S``, which holds for a set of vertices and fails as
    soon as an edge or a face is present. The link of a single vertex is
    therefore the same under either form, while the link of an edge is not:
    using ``St(S)`` leaves the edge's own endpoints in the result.

    On a closed triangle mesh the link of an interior vertex is its one-ring
    boundary: a cycle of vertices and edge_vertex_ids, with no faces.
    """
    star_of_s = reference_simplex_star(edge_vertex_ids, face_edge_ids, simplices)
    closure_of_star = reference_simplex_closure(edge_vertex_ids, face_edge_ids, star_of_s)

    closure_of_s = reference_simplex_closure(edge_vertex_ids, face_edge_ids, simplices)
    star_of_closure = reference_simplex_star(edge_vertex_ids, face_edge_ids, closure_of_s)

    link_vertices, link_edges, link_faces = (
        np.setdiff1d(outer, inner)
        for outer, inner in zip(closure_of_star, star_of_closure))

    return link_vertices, link_edges, link_faces

### Generic  Functions
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

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_triangle_ratio(edge_magnitudes: FloatArray) -> FloatArray:
    """
    Returns the ratio of each tringale's longest/smallest edge
    """
    longest = edge_magnitudes.max(axis=1)
    shortest = edge_magnitudes.min(axis=1)

    # Degenerate triangles have a zero-length edge. Report 0.0 rather than
    # dividing, matching how :func:`compute_vector_values` handles zero vectors.
    valid_mask = shortest >= ERR
    ratios = np.where(valid_mask, longest / np.where(valid_mask, shortest, 1.0), 0.0)

    return ratios

@aux.timed(TIMED)
@aux.memory(MEMORY)
def compute_triangle_jacobian(triangle_coordinates: FloatArray):
    """
    Computes the jacobian of each individual triangle
    """
    x1 = triangle_coordinates[:,0,:]
    x2 = triangle_coordinates[:,1,:]
    x3 = triangle_coordinates[:,2,:]

    u = x2 - x1  # Edge 1 vector
    v = x3 - x1  # Edge 2 vector

    jacobians = np.stack([u, v], axis=-1)

    return jacobians

# Main entry point
if __name__ == "__main__":
    import pytest
    print("Main Entry Point")

    print("Main Exit point")
