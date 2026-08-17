"""
ddg_objects is the meant and potatoes of my ddg app containing objects
for enforcing data flow and structure, and the matematical operations as functions
"""
import numpy as np
import scipy as sp
import trimesh

### Custom Imports
import AuxFunctions as aux

### Global Variables
DEBUG = True # Debug flag to print some items as I code
TIMED = True # Debug flag to print time estimates of functions
MEMORY = True # Debug flag for memory probing
ERR = 1e-8 # Defines a global error value for some computations

### Support Classes
class MeshObject():
    """
    Container that loads a mesh and precomputes connectivity and face data.

    Wraps a ``trimesh`` mesh and eagerly computes the quantities used
    throughout the project (face normals/areas, edges, and the three
    adjacency structures), exposing them as plain attributes for easy access.

    Parameters
    ----------
    FilePath : str
        Path to a mesh file loadable by ``trimesh.load`` (e.g. an STL).
        Loaded with ``force='mesh'`` so multi-body files collapse to a single
        mesh rather than a ``Scene``.
    Name : str
        Human-readable label for the mesh, reused as the Polyscope name.

    Attributes
    ----------
    Name : str
        The label passed in at construction.
    Geometry : trimesh.Trimesh
        The underlying loaded mesh.
    FacetNormals : numpy.ndarray, shape (F, 3)
        Unit normal per face.
    NormalMagnitude : numpy.ndarray, shape (F,)
        Magnitude of each raw face cross product (twice the area).
    FacetAreas : numpy.ndarray, shape (F,)
        Area of each face.
    edges : numpy.ndarray, shape (F, 3, 3)
        The three edge vectors per face, stacked edge-index first.
    NumVerts : int
        Number of vertices (V).
    NumFaces : int
        Number of faces (F).
    vertex_face_adjacency : numpy.ndarray
        Per-vertex incident face indices (from ``trimesh.vertex_faces``).
    vertex_vertex_adjacency : scipy.sparse.csr_matrix, shape (V, V)
        Symmetric vertex-adjacency matrix (1 where two vertices share an edge).
    face_face_adjacency : scipy.sparse.csr_matrix, shape (F, F)
        Symmetric face-adjacency matrix (1 where two faces share an edge).

    Notes
    -----
    All quantities are computed eagerly in ``__init__``. 
    """

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def __init__(self,FilePath, Name) -> None:
        # Required initiations
        self.Name = Name
        try:
            self.Geometry = trimesh.load(FilePath, force='mesh')
        except Exception as e:
            print("failed to load trimesh mesh")
            print(e)

        assert isinstance(self.Geometry, trimesh.Trimesh)

        self.NumVerts = len(self.Geometry.vertices)
        self.NumFaces = len(self.Geometry.faces)
        rows, cols = self.Geometry.face_adjacency.T
        data = np.ones(2 * len(rows))
        r = np.concatenate([rows, cols])
        c = np.concatenate([cols, rows])
        self.face_face_adjacency = sp.sparse.csr_matrix((data, (r, c)),
                                                        shape=(self.NumFaces, self.NumFaces))
        edges_u = self.Geometry.edges_unique
        vr = np.concatenate([edges_u[:, 0], edges_u[:, 1]])
        vc = np.concatenate([edges_u[:, 1], edges_u[:, 0]])
        vdata = np.ones(len(vr))
        self.vertex_vertex_adjacency = sp.sparse.csr_matrix((vdata, (vr, vc)),
                                                            shape = (self.NumVerts,
                                                                     self.NumVerts))
        self.vertex_face_adjacency = self.Geometry.vertex_faces

        # Memory pre-alocation (Questionable if needed)
        self.FacetNormals = None
        self.NormalMagnitude = None
        self.FacetAreas = None
        _, _, _, self.Edges = compute_triangle_data(self.Geometry.vertices[self.Geometry.faces])
        self.FacetDots = None
        self.Angles = None
        # Data that will be computed upon request
        self.Centers = compute_face_center_3d(self.Geometry.vertices[self.Geometry.faces])
        self.TrimeshVertexDefect = trimesh.curvature.vertex_defects(self.Geometry)
        self.vertex_defect = None
        self.corner_angles = None

        ## Prints for debugging
        print("Loaded Correctly")
        print(f"Name: \n {self.Name}")
        print(f"Num Verts: \n {self.NumVerts}")
        print(f"Num Faces: \n {self.NumFaces}")
        if DEBUG:
            print("Vertices: \n", self.Geometry.vertices)
            print("Faces: \n", self.Geometry.faces)
            print("Tri Coords: \n", self.Geometry.vertices[self.Geometry.faces])
            print("Face Adjacency: \n", self.face_face_adjacency)
            print("Face Centers: \n", self.Centers)
            print("Edges: \n", self.Edges)

    # To be used by a callback or other call operation instead of doing at __init__
    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_mesh_facet_values(self):
        """Populate the per-face geometric attributes on this mesh.

        Thin wrapper over :func:`compute_triangle_data`; computes and stores
        the face normals, normal magnitudes, areas, and edge vectors.

        Side Effects
        ------------
        Sets ``self.FacetNormals``, ``self.NormalMagnitude``,
        ``self.FacetAreas``, and ``self.Edges``.
        """
        self.FacetNormals, self.NormalMagnitude, self.FacetAreas, self.Edges = compute_triangle_data(self.Geometry.vertices[self.Geometry.faces])

    @aux.timed(TIMED)
    @aux.memory(MEMORY)
    def compute_mesh_facet_direction(self, reference = np.array([0.0,0.0,1.0]), Angle = True):
        """
        Populate the normal-vs-reference attributes on this mesh.

        Thin wrapper over :func:`check_normal_direction`; requires
        ``self.FacetNormals`` to already be set (see
        :meth:`_compute_mesh_facet_values`).

        Parameters
        ----------
        reference : numpy.ndarray, shape (3,), optional
            Direction to compare face normals against. Defaults to ``FLOOR``.

        Side Effects
        ------------
        Sets ``self.FacetDots`` and ``self.Angles``.
        """
        if self.FacetNormals is None:
            self.compute_mesh_facet_values()

        self.FacetDots, self.Angles = check_normal_direction(self.FacetNormals,
                                                             reference,
                                                             angle = Angle)

    @aux.timed(TIMED)
    @aux.memory(MEMORY)  
    def compute_mesh_vertex_defect(self):
        """
        Self compute of vertex defect quantity
        """
        self.vertex_defect, self.corner_angles = compute_gausian_curvature(self.Edges,
                                                                           self.Geometry.faces,
                                                                           self.NumVerts)
        assert np.allclose(self.vertex_defect, self.TrimeshVertexDefect, atol=1e-6)

class SDFObject():
    """
    Data structure representing a functional Signed Distance Field, or 
    more generally a [signed] metric field
    """
    def __init__(self, Name, Source) -> None:
        """
        Initialization values of the SDF, meant to "prepare" an SDF object prior to 
        actualy generating. Where a mesh comes from a file, an SDF is constructed in code
        can come from a mesh or a equation / kernell
        
        I will probably want to bring Mesh to parity behaviour here to just initialize 
        an object then throw data to it
        """
        self.Name = Name
        self.Source = Source # MeshObject 'pointer' or "Kernel"

        pass

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

@aux.timed(False)
@aux.memory(False)
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

## Generates an SDF from a mesh
@aux.timed(TIMED)
@aux.memory(MEMORY)
def sdf_from_mesh(mesh_object: MeshObject) -> SDFObject:
    """
    Backbone to generate an sdf from a mesh.
    # TODO: No idea how thils will work but it will probably exist.
    # Not married to the idea
    """

    return SDFObject(Name="A", Source=mesh_object.Name)
