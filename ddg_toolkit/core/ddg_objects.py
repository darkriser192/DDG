"""ddg_objects is the meat and potatoes of my ddg app containing objects
that enforce data flow and structure. The mathematics itself lives in
``ddg_math``; this module orchestrates it and holds the results.

Promise of the math: A collection of DDG algorithms.

Promise of the objects: A geometric computational kernel built around DDG.

References
----------
https://www.cs.cmu.edu/~kmcrane/Projects/DDG/
"""
# import sys
import pathlib
# from collections.abc import Sequence
from typing import Literal, TypedDict

import numpy as np

import scipy as sp
import trimesh

### Custom Imports
import ddg_toolkit.core.ddg_math as ddgmath
from ddg_toolkit.core.ddg_types import FloatArray, IntArray, SparseMatrix, ERR_TOL
import ddg_toolkit.core.aux_functions as aux

class FaceDots(TypedDict):
    """One entry of ``Geometry.face_dots``: the comparison against one reference.

    A ``TypedDict`` rather than a plain ``dict`` so that ``result["dots"]`` reads
    back as an array while ``result["angles"]`` keeps its ``None`` case, instead
    of both collapsing to the same union.
    """
    dots: FloatArray
    angles: FloatArray | None

### Global Variables
DEBUG: bool = False # Debug flag to print some items as I code
TIMED: bool = False # Debug flag to print time estimates of functions
MEMORY: bool = False # Debug flag for memory probing

### Support Classes
class Surface():
    """
    TODO: In preparation of needing a surface class that does not need to be 
    a none manifold object in 3D
    """
    def __init__(self, name: str = "Default Surface Name") -> None:
        self.name = name

class Geometry():
    """
    Container for a triangle mesh and its discrete-geometry quantities.

    Wraps a ``trimesh`` mesh and exposes the quantities used across the
    project. Construction is cheap: only the name, path, and element counts
    are set. Every geometric quantity is computed on request by a
    ``compute_*`` method.

    Parameters
    ----------
    file_path : str or None
        Path to a mesh file loadable by ``trimesh.load_mesh`` (e.g. an STL).
        Loaded with ``force='mesh'`` so multi-body files collapse to a single
        mesh rather than a ``Scene``. None builds the unit tetrahedron
        instead, named ``"Test Tetrahedron"``, which is the fixture the tests
        are written against.

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
    face_normals : numpy.ndarray or None, shape (F, 3)
        Unit normal per face.
    normal_magnitudes : numpy.ndarray or None, shape (F,)
        Magnitude of each raw face cross product, i.e. twice the face area.
    face_areas : numpy.ndarray or None, shape (F,)
        Area per face.
    face_centers : numpy.ndarray or None, shape (F, 3)
        Centroid per face. No method currently sets this.
    edge_magnitudes : numpy.ndarray or None, shape (F, 3)
        Length of each of the three edges per face.
    edge_directions : numpy.ndarray or None, shape (F, 3, 3)
        Unit edge vectors per face, stacked edge-index first, in winding order.
    face_dots : dict
        Reference name -> ``{"dots": (F,), "angles": (F,) or None}``. Holds one
        entry per reference direction compared against.
    vertex_defects : numpy.ndarray or None, shape (V,)
        Angle defect per vertex: ``2*pi`` minus the incident corner angles.
    corner_angles : numpy.ndarray or None, shape (F, 3)
        Corner angle at each face corner, in radians. Indexed by face and
        corner, not by vertex.
    defect_ratio : numpy.ndarray or None, shape (V,)
        ``vertex_defects / (2*pi)`` -- the angle defect as a fraction of a full
        turn, so 0 means locally flat.
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

    # Attribute declarations. These bind no value -- they only tell a type
    # checker what each attribute holds once a compute_* method has run, which
    # is what makes `assert x is not None` narrow to a usable array downstream.
    name: str
    path: str
    trimesh_object: trimesh.Trimesh
    number_vertices: int
    number_faces: int
    face_normals: FloatArray | None
    normal_magnitudes: FloatArray | None
    face_areas: FloatArray | None
    face_centers: FloatArray | None
    edge_magnitudes: FloatArray | None
    edge_directions: FloatArray | None
    face_dots: dict[str, FaceDots]
    vertex_defects: FloatArray | None
    corner_angles: FloatArray | None
    defect_ratio: FloatArray | None
    face_face_adjacency: SparseMatrix | None
    vertex_vertex_adjacency: SparseMatrix | None
    vertex_face_adjacency: IntArray | None

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
            self.name = pathlib.Path(file_path).stem
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
        self.face_normals = None
        self.normal_magnitudes = None
        self.face_areas = None
        self.face_centers = None
        self.edge_magnitudes = None
        self.edge_directions = None
        self.face_dots = {}
        self.vertex_defects = None
        self.corner_angles = None
        self.face_face_adjacency = None
        self.vertex_vertex_adjacency = None
        self.vertex_face_adjacency = None
        self.defect_ratio = None

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
    def compute_face_values(self) -> None:
        """Compute and store the per-face geometric quantities.

        Thin wrapper over :func:`compute_triangle_data`.

        Side Effects
        ------------
        Sets ``self.face_normals``, ``self.normal_magnitudes``,
        ``self.face_areas``, ``self.edge_magnitudes``, and
        ``self.edge_directions``.
        """
        self.face_normals, self.normal_magnitudes, self.face_areas, self.edge_magnitudes, self.edge_directions = ddgmath.compute_triangle_data(self.trimesh_object.vertices[self.trimesh_object.faces])

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_face_direction(self,
                                     name: str,
                                     reference: FloatArray = np.array([0.0,0.0,1.0]),
                                     angle: bool = True) -> None:
        """Compare face normals against one named reference direction.

        Thin wrapper over :func:`compute_normal_direction`. Computes
        ``self.face_normals`` first if it is unset, so call order does not
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
        Sets ``self.face_dots[name]`` to a dict with keys ``"dots"``
        (shape (F,)) and ``"angles"`` (shape (F,), or None when ``Angle`` is
        False).
        """
        if self.face_normals is None:
            self.compute_face_values()
        # The call above sets it; the assert is what lets the checker see that.
        assert self.face_normals is not None

        dots, angles = ddgmath.compute_normal_direction(self.face_normals , reference, angle = angle)

        values: FaceDots = {"dots":dots, "angles":angles}
        self.face_dots[name] = values

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_vertex_defects(self, ERR = ERR_TOL) -> None:
        """Compute and store the per-vertex angle defect.

        The discrete Gaussian curvature at a vertex: ``2*pi`` minus the sum of
        the corner angles meeting there.

        Side Effects
        ------------
        Sets ``self.vertex_defects``, ``self.corner_angles``, and
        ``self.defect_ratio``.

        Computes ``self.edge_directions`` first if it is unset, so call order
        does not matter.

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
        if self.edge_directions is None:
            self.compute_face_values()
        # The call above sets it; the assert is what lets the checker see that.
        assert self.edge_directions is not None

        self.vertex_defects, self.corner_angles, self.defect_ratio = ddgmath.compute_gaussian_curvature(
            self.edge_directions,
            self.trimesh_object.faces,
            self.number_vertices)
        
        assert self.vertex_defects is not None

        assert np.allclose(self.vertex_defects, self.trimesh_object.vertex_defects, atol=ERR)

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def memory_report(self) -> dict[str, float | None]:
        """
        Return the memory use of each stored attribute, in MB.

        Returns
        -------
        report : dict
            Attribute name -> size in MB, or None when the attribute holds no
            measurable buffer (strings, scalars, unset fields).
        """
        report: dict[str, float | None] = {}
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
    def geometry_star(self,
                      element_ids: tuple[int,int,int],
                      mode: Literal["vertex", "edge", "face", "all"] = "all") -> None:
        """
        Returns the Star surface combinatorial operator
        """
        #TODO: implement
        match mode:
            case "vertex":
                print(f"\nClicked with {mode}:"
                      f"\n- vertex id: {element_ids[0]}")
            case "edge":
                print(f"\nClicked with {mode}:"
                      f"\n- edge id: {element_ids[1]}")
            case "face":
                print(f"\nClicked with {mode}:"
                      f"\n- face id: {element_ids[2]}")
            case "all":
                print(f"\nClicked with {mode}:"
                      f"\n- vertex id: {element_ids[0]}"
                      f"\n- edge id: {element_ids[1]}"
                      f"\n- face id: {element_ids[2]}")

    @aux.timed(False)
    @aux.memory(False)
    def __repr__(self) -> str:
        return (f"Geometry({self.name!r}\n - V = {self.number_vertices}\n - F = {self.number_faces})")

class SignedDistanceField():
    """
    Data structure representing a functional Signed Distance Field, or 
    more generally a [signed] metric field
    """
    name: str
    source: str

    def __init__(self, name: str, source: str) -> None:
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
## Generates an SDF from a mesh
@aux.timed(TIMED)
@aux.memory(MEMORY)
def sdf_from_mesh(mesh_object: Geometry) -> SignedDistanceField:
    """
    Backbone to generate an sdf from a mesh.
    # TODO: No idea how thils will work but it will probably exist.
    # Not married to the idea
    """
    return SignedDistanceField(name = "Default Name", source = mesh_object.name)

# Main entry point
if __name__ == "__main__":
    print("Main Entry Point")
    print(Geometry(file_path = None).__repr__)
    print(Geometry(file_path = ".\\meshes\\rabbit-low-poly.stl").__repr__)
    print("Main exit point")
