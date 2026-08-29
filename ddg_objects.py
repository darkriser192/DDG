"""
ddg_objects is the meant and potatoes of my ddg app containing objects
for enforcing data flow and structure, and the matematical operations as functions
"""
# import sys
import pathlib as path
#from dataclasses import dataclass, field
from typing import Literal


import numpy as np
import scipy as sp
import trimesh

### Custom Imports
import AuxFunctions as aux

### Global Variables
DEBUG = False # Debug flag to print some items as I code
TIMED = False # Debug flag to print time estimates of functions
MEMORY = False # Debug flag for memory probing
ERR = 1e-8 # Defines a global error value for some computations

### Support Classes
class Geometry():
    """
    Container for a triangle mesh and its discrete-geometry quantities.

    Wraps a ``trimesh`` mesh and exposes the quantities used across the
    project. Construction is cheap: only the name, path, and element counts
    are set. Every geometric quantity is computed on request by a
    ``compute_*`` method. Replaces :class:`MeshObject`.

    Parameters
    ----------
    file_path : str
        Path to a mesh file loadable by ``trimesh.load_mesh`` (e.g. an STL).
        Loaded with ``force='mesh'`` so multi-body files collapse to a single
        mesh rather than a ``Scene``.

    Attributes
    ----------
    name : str
        File stem (no extension), reused as the Polyscope structure name.
    path : str
        The file path passed at construction.
    trimesh_object : trimesh.Trimesh
        The underlying loaded mesh.
    number_vertices : int
        Vertex count (V).
    number_faces : int
        Face count (F).
    facet_normals : numpy.ndarray or None, shape (F, 3)
        Unit normal per face.
    normal_magnitude : numpy.ndarray or None, shape (F,)
        Magnitude of each raw face cross product, i.e. twice the face area.
    facet_areas : numpy.ndarray or None, shape (F,)
        Area per face.
    face_centers : numpy.ndarray or None, shape (F, 3)
        Centroid per face. No method currently sets this.
    edges : numpy.ndarray or None, shape (F, 3, 3)
        The three edge vectors per face, stacked edge-index first.
    facet_dots : dict
        Reference name -> ``{"dots": (F,), "angles": (F,) or None}``. Holds one
        entry per reference direction compared against.
    vertex_defects : numpy.ndarray or None, shape (V,)
        Angle defect per vertex: ``2*pi`` minus the incident corner angles.
    vertex_angles : numpy.ndarray or None, shape (F, 3)
        Corner angle at each face corner, in radians.
    face_face_adjacency : scipy.sparse.csr_matrix or None, shape (F, F)
        Symmetric; 1 where two faces share an edge.
    vertex_vertex_adjacency : scipy.sparse.csr_matrix or None, shape (V, V)
        Symmetric; 1 where two vertices share an edge.
    vertex_face_adjacency : numpy.ndarray or None
        Per-vertex incident face indices, from ``trimesh.vertex_faces``.

    Notes
    -----
    Attributes documented ``or None`` stay unset until their ``compute_*``
    method runs. Methods self-heal their own dependencies where they have any,
    so the ``compute_*`` calls are order-independent. :meth:`compute_adjacency`
    is the exception: nothing calls it automatically, because nothing consumes
    the adjacency structures yet.
    """
    # Class constants

    # Initialization sequence
    def __init__(self, file_path: str | None, ) -> None:
        if file_path is None:
            vertices = [[0,0,0],[1,0,0],[0,1,0],[0,0,1]]
            faces = [[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
            # edges_unique       [[0,1],[0,2],[1,2],[0,3],[1,3],[2,3]]
            # faces_unique_edges [[1,2,0],[0,4,3],[3,5,1],[2,5,4]]
            self.name = "Test Tetrahedron"
            self.path = "<none>"
            self.trimesh_object = trimesh.Trimesh(vertices=vertices,faces=faces)
        else:
            # Extract the name of the object
            self.name = path.Path(file_path).stem
            self.path = file_path
            print(self.name)
            # Try to load the schene into the object
            try:
                trimesh_object = trimesh.load_mesh(file_path, force='mesh')
                self.trimesh_object = trimesh_object
            except Exception as e:
                print(f"Trimesh failed to load {self.name}: \n {e}")

        self.number_vertices = len(self.trimesh_object.vertices)
        self.number_faces = len(self.trimesh_object.faces)

        # Property pre-allocation/creation for reference later
        self.facet_normals = None
        self.normal_magnitude = None
        self.facet_areas = None
        self.face_centers = None
        self.edges = None
        self.facet_dots = {}
        self.vertex_defects = None
        self.vertex_angles = None
        self.face_face_adjacency = None
        self.vertex_vertex_adjacency = None
        self.vertex_face_adjacency = None

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_adjacency(self) -> None:
        """Compute and store the three adjacency structures.

        Builds symmetric sparse connectivity matrices from the ``trimesh``
        topology. Nothing calls this automatically -- call it before any
        operation that needs adjacency.

        Side Effects
        ------------
        Sets ``self.face_face_adjacency``, ``self.vertex_vertex_adjacency``,
        and ``self.vertex_face_adjacency``.

        Notes
        -----
        Every stored entry is 1.0: these encode connectivity, not weights.
        Each index pair is stacked in both orders inside a single assignment
        statement, so both concatenations see the pre-swap arrays.
        ``vertex_vertex_adjacency`` is built from ``edges_unique``, which is
        also the index set the boundary operators will need.
        """
        rows, cols = self.trimesh_object.face_adjacency.T
        data = np.ones(2 * len(rows))
        # One statement: the right side is fully evaluated before either name rebinds,
        # so both concatenates see the original arrays.
        rows, cols = np.concatenate([rows, cols]), np.concatenate([cols, rows])
        self.face_face_adjacency = sp.sparse.csr_matrix((data, (rows, cols)),
                                                        shape=(self.number_faces,
                                                               self.number_faces))
        edges_u = self.trimesh_object.edges_unique
        # One statement: the right side is fully evaluated before either name rebinds,
        # so both concatenates see the original arrays.
        vr, vc = np.concatenate([edges_u[:, 0], edges_u[:, 1]]), np.concatenate([edges_u[:, 1], edges_u[:, 0]])
        vdata = np.ones(len(vr))
        self.vertex_vertex_adjacency = sp.sparse.csr_matrix((vdata, (vr, vc)),
                                                            shape = (self.number_vertices,
                                                            self.number_vertices))
        self.vertex_face_adjacency = self.trimesh_object.vertex_faces

    # To be used by a callback or other call operation instead of doing at __init__
    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_mesh_facet_values(self):
        """Compute and store the per-face geometric quantities.

        Thin wrapper over :func:`compute_triangle_data`.

        Side Effects
        ------------
        Sets ``self.facet_normals``, ``self.normal_magnitude``,
        ``self.facet_areas``, and ``self.edges``.
        """
        self.facet_normals, self.normal_magnitude, self.facet_areas, self.edges = compute_triangle_data(self.trimesh_object.vertices[self.trimesh_object.faces])

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_mesh_facet_direction(self, name:str, reference = np.array([0.0,0.0,1.0]), angle = True):
        """Compare face normals against one named reference direction.

        Thin wrapper over :func:`check_normal_direction`. Computes
        ``self.facet_normals`` first if it is unset, so call order does not
        matter for this method.

        Parameters
        ----------
        name : str
            Key to store the result under, e.g. ``"FLOOR"``. Results for
            several reference directions coexist; reusing a key overwrites it.
        reference : numpy.ndarray, shape (3,), optional
            Direction to compare face normals against. Assumed unit length, so
            the dot product reads as ``cos(theta)``. Defaults to +Z.
        Angle : bool, optional
            If True (default), also compute the angle in radians.

        Side Effects
        ------------
        Sets ``self.facet_dots[name]`` to a dict with keys ``"dots"``
        (shape (F,)) and ``"angles"`` (shape (F,), or None when ``Angle`` is
        False).
        """
        if self.facet_normals is None:
            self.compute_mesh_facet_values()

        dots, angles = check_normal_direction(self.facet_normals , reference, angle = angle)

        values = {"dots":dots, "angles":angles}
        self.facet_dots[name] = values

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_mesh_vertex_defect(self):
        """Compute and store the per-vertex angle defect.

        The discrete Gaussian curvature at a vertex: ``2*pi`` minus the sum of
        the corner angles meeting there.

        Side Effects
        ------------
        Sets ``self.vertex_defects`` and ``self.vertex_angles``.

        Computes ``self.edges`` first if it is unset, so call order does not
        matter.

        Raises
        ------
        AssertionError
            If the result disagrees with the ``trimesh`` value by more
            than ``ERR``.

        Notes
        -----
        The trimesh comparison is a deliberate, permanent oracle: it is what
        makes this hand-written curvature safe to refactor. Measured agreement
        on ``rabbit-low-poly.stl`` is about 5e-14, so the tolerance has ample
        margin.
        """
        if self.edges is None:
            self.compute_mesh_facet_values()

        self.vertex_defects, self.vertex_angles = compute_gausian_curvature(self.edges,
                                                                            self.trimesh_object.faces,
                                                                            self.number_vertices)

        assert np.allclose(self.vertex_defects, self.trimesh_object.vertex_defects, atol=ERR)

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def mem_report(self) -> dict:
        """
        Return the memory use of each stored attribute, in MB.

        Returns
        -------
        report : dict
            Attribute name -> size in MB, or None when the attribute holds no
            measurable buffer (strings, scalars, unset fields).
        """
        report = {}
        for name, value in vars(self).items():
            if isinstance(value, np.ndarray):
                report[name] = value.nbytes / 1e6
            elif sp.sparse.issparse(value):
                report[name] = value.data.nbytes / 1e6
            else:
                report[name] = None
        report["trimesh.vertices"] = self.trimesh_object.vertices.nbytes / 1e6
        report["trimesh.faces"] = self.trimesh_object.faces.nbytes / 1e6

        return report

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def geometry_star(self, coordinates: tuple[int,int,int], mode: Literal["vertex", "edge", "face", "all"] = "all"):
        """
        returns the Star surface combinatorial operator
        """
        #TODO: implement
        match mode:
            case "vertex":
                print(f"\nClicked with {mode}:"
                      f"\n- vertex id: {coordinates[0]}")
            case "edge":
                print(f"\nClicked with {mode}:"
                      f"\n- edge id: {coordinates[1]}")
            case "face":
                print(f"\nClicked with {mode}:"
                      f"\n- face id: {coordinates[2]}")
            case "all":
                print(f"\nClicked with {mode}:"
                      f"\n- vertex id: {coordinates[0]}"
                      f"\n- edge id: {coordinates[1]}"
                      f"\n- face id: {coordinates[2]}")
        
    @aux.timed(False)
    @aux.memory(False)
    def __repr__(self):
        return (f"Geometry({self.name!r}\n - V = {self.number_vertices}\n - F = {self.number_faces})")

class SDFObject():
    """
    Data structure representing a functional Signed Distance Field, or 
    more generally a [signed] metric field
    """
    def __init__(self, name, source) -> None:
        """
        Initialization values of the SDF, meant to "prepare" an SDF object prior to 
        actualy generating. Where a mesh comes from a file, an SDF is constructed in code
        can come from a mesh or a equation / kernell
        
        I will probably want to bring Mesh to parity behaviour here to just initialize 
        an object then throw data to it
        """
        self.name = name
        self.source = source # MeshObject 'pointer' or "Kernel"

### Support Functions
@aux.timed(TIMED)
@aux.memory(MEMORY)
def vector_values(vectors):
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
def compute_triangle_data(triangles):
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
def compute_face_center_3d(vertex):
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
def check_normal_direction(normals, reference, angle = False):
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
def compute_gausian_curvature(edges, faces, num_verts):
    """
    Computes the per-vertex gausian curvature error
    """
    def corner_angle(a, b):
        _, a_n = vector_values(a)
        _, b_n = vector_values(b)
        cos = (a_n * b_n).sum(axis=1)
        return np.arccos(np.clip(cos, -1.0, 1.0))

    print("computing curvature edges")
    angle0 = corner_angle( edges[:, 0], -edges[:, 2])   # at v0
    angle1 = corner_angle(-edges[:, 0],  edges[:, 1])   # at v1
    angle2 = corner_angle( edges[:, 2], -edges[:, 1])   # at v2
    if DEBUG:
        print(f"angle0 (deg):\n {np.degrees(angle0)}")
        print(f"angle1 (deg):\n {np.degrees(angle1)}")
        print(f"angle2 (deg):\n {np.degrees(angle2)}")

    corner_angles = np.stack([angle0, angle1, angle2], axis=1)   # (F, 3)

    assert np.allclose(corner_angles.sum(axis=1), np.pi, atol=1e-6)

    angle_sum = np.bincount(faces.ravel(),
                            weights=corner_angles.ravel(),
                            minlength=num_verts)

    gaussian_error = 2*np.pi - angle_sum

    return gaussian_error, corner_angles

## Utility Functions #1 hand coded start, closure and link functions
def reference_simplice_star(edges, face_edges, simplices):
    """
    For a simplictical complex it returns the 'star' operator of the defining arrays

    
    Retrieve the edges connected to a vertex referenced by integer ID
    edges       : (E, 2) int, sorted low->high — the canonical edge list
    face_edges  : (F, 3) int — each face's three edge indices, in winding order
    simplices : (vertices, edges, faces) — a tuple of three sets of indices
    """

    pass

def reference_simplice_closure(edges, face_edges, integer_id: int = 0):
    """
    Retrieve the triangles connected to a vertex referenced by integer ID
    edges       : (E, 2) int, sorted low->high — the canonical edge list
    face_edges  : (F, 3) int — each face's three edge indices, in winding order
    """

    pass

def reference_simplice_link(edges, face_edges, integer_id: int = 0):
    """
    Retrieves the closed loop of edges sorrounding a vertex references by integer ID.
    does not include the vertex itself on the loop
    """

    pass

## Generates an SDF from a mesh
@aux.timed(TIMED)
@aux.memory(MEMORY)
def sdf_from_mesh(mesh_object: Geometry) -> SDFObject:
    """
    Backbone to generate an sdf from a mesh.
    # TODO: No idea how thils will work but it will probably exist.
    # Not married to the idea
    """

    return SDFObject(name="Default Name", source=mesh_object.name)

### Geometric Functions
@aux.timed(TIMED)
@aux.memory(MEMORY)
def normalize(minmax,value):
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

if __name__ == "__main__":
    Geometry(file_path="D:\\DDG\\rabbit-low-poly.stl")
