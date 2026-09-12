"""Tests for the pure math layer.

Deliberately free of ``trimesh`` and of ``Geometry``: every fixture here is a
literal array, so a failure points at ``core.ddg_math`` and nothing else. Tests
that need a loaded mesh live in ``test_ddg_objects``.

The reference solid is the unit tetrahedron built by ``Geometry(None)``. Its
edge and face tables are the ones written into the comments of
``Geometry.__init__``; ``test_tetrahedron_tables_match_trimesh`` in
``test_ddg_objects`` checks that they still agree with what trimesh derives.
"""
import numpy as np
import pytest

import ddg_toolkit.core.ddg_math as ddgmath

### Reference solid: the unit tetrahedron
TETRA_VERTICES = np.array([[0.0, 0.0, 0.0],
                           [1.0, 0.0, 0.0],
                           [0.0, 1.0, 0.0],
                           [0.0, 0.0, 1.0]])
TETRA_FACES = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
TETRA_EDGE_VERTEX_IDS = np.array([[0, 1], [0, 2], [1, 2], [0, 3], [1, 3], [2, 3]])
TETRA_FACE_EDGE_IDS = np.array([[1, 2, 0], [0, 4, 3], [3, 5, 1], [2, 5, 4]])
TETRA_TRIANGLES = TETRA_VERTICES[TETRA_FACES]

# Three right-angled faces of area 1/2, and one equilateral face of side sqrt(2).
TETRA_AREAS = np.array([0.5, 0.5, 0.5, np.sqrt(3.0) / 2.0])
# Corner sums: 3 x 90 deg at the origin, and 90 + 45 + 45 = 150 deg at each other vertex.
TETRA_DEFECTS = np.array([2 * np.pi - 3 * (np.pi / 2)]
                         + [2 * np.pi - np.deg2rad(150.0)] * 3)

### compute_vector_values
def test_vector_values_returns_magnitude_and_unit_direction():
    vectors = np.array([[3.0, 4.0, 0.0], [0.0, 0.0, 2.0]])

    magnitude, direction = ddgmath.compute_vector_values(vectors)

    assert np.allclose(magnitude, [5.0, 2.0])
    assert np.allclose(direction, [[0.6, 0.8, 0.0], [0.0, 0.0, 1.0]])

def test_vector_values_sends_a_zero_vector_to_a_zero_direction():
    """A zero row must not become NaN, and must not emit a divide warning."""
    vectors = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    with np.errstate(divide="raise", invalid="raise"):
        magnitude, direction = ddgmath.compute_vector_values(vectors)

    assert np.allclose(direction[0], 0.0)
    assert not np.isnan(direction).any()
    # The magnitude is reported unmodified; only the direction is substituted.
    assert magnitude[0] == 0.0

def test_vector_values_keeps_the_leading_shape():
    """Used on (F, 3, 3) edge stacks as well as on plain (N, 3) vectors."""
    magnitude, direction = ddgmath.compute_vector_values(np.ones((4, 3, 3)))

    assert magnitude.shape == (4, 3)
    assert direction.shape == (4, 3, 3)


### compute_triangle_data
def test_triangle_data_areas_match_the_closed_form():
    _, _, areas, _, _ = ddgmath.compute_triangle_data(TETRA_TRIANGLES)

    assert np.allclose(areas, TETRA_AREAS)

def test_triangle_data_normal_magnitude_is_twice_the_area():
    _, normal_magnitudes, areas, _, _ = ddgmath.compute_triangle_data(TETRA_TRIANGLES)

    assert np.allclose(normal_magnitudes, 2.0 * areas)

def test_triangle_data_returns_unit_normals_and_unit_edge_directions():
    normals, _, _, _, edge_directions = ddgmath.compute_triangle_data(TETRA_TRIANGLES)

    assert np.allclose(np.linalg.norm(normals, axis=-1), 1.0)
    assert np.allclose(np.linalg.norm(edge_directions, axis=-1), 1.0)

def test_triangle_data_edges_close_the_loop():
    """The three edges are taken in winding order, so they must sum to zero."""
    _, _, _, edge_magnitudes, edge_directions = ddgmath.compute_triangle_data(TETRA_TRIANGLES)

    edge_vectors = edge_directions * edge_magnitudes[..., np.newaxis]

    assert np.allclose(edge_vectors.sum(axis=1), 0.0)

def test_triangle_data_edge_magnitudes_are_the_side_lengths():
    _, _, _, edge_magnitudes, _ = ddgmath.compute_triangle_data(TETRA_TRIANGLES)

    # Face 0 is (0,0,0) -> (0,1,0) -> (1,0,0): two unit legs and one sqrt(2) hypotenuse.
    assert np.allclose(edge_magnitudes[0], [1.0, np.sqrt(2.0), 1.0])

def test_triangle_data_normal_is_perpendicular_to_the_face():
    normals, _, _, _, _ = ddgmath.compute_triangle_data(TETRA_TRIANGLES)

    # Face 3 spans (1,0,0), (0,1,0), (0,0,1): its normal is the (1,1,1) diagonal.
    assert np.allclose(np.abs(normals[3]), np.full(3, 1.0 / np.sqrt(3.0)))


### compute_face_centers
def test_face_centers_are_the_corner_means():
    centers = ddgmath.compute_face_centers(TETRA_TRIANGLES)

    assert centers.shape == (4, 3)
    assert np.allclose(centers[0], [1 / 3, 1 / 3, 0.0])
    assert np.allclose(centers[3], [1 / 3, 1 / 3, 1 / 3])


### compute_normal_direction
NORMALS_AGAINST_UP = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
UP = np.array([0.0, 0.0, 1.0])

def test_normal_direction_returns_the_dot_products():
    dots, angles = ddgmath.compute_normal_direction(NORMALS_AGAINST_UP, UP)

    assert np.allclose(dots, [1.0, -1.0, 0.0])
    assert angles is None, "angles must stay None unless angle=True"

def test_normal_direction_returns_angles_when_asked():
    _, angles = ddgmath.compute_normal_direction(NORMALS_AGAINST_UP, UP, angle=True)

    assert angles is not None
    assert np.allclose(angles, [0.0, np.pi, np.pi / 2])

def test_normal_direction_clips_before_arccos():
    """A normal a hair longer than unit must not produce NaN."""
    _, angles = ddgmath.compute_normal_direction(np.array([[0.0, 0.0, 1.0 + 1e-12]]),
                                                 UP, angle=True)

    assert angles is not None
    assert not np.isnan(angles).any()


### compute_gaussian_curvature
@pytest.fixture(name="tetra_edge_directions")
def fixture_tetra_edge_directions():
    """The (F, 3, 3) unit edge directions of the reference tetrahedron."""
    _, _, _, _, edge_directions = ddgmath.compute_triangle_data(TETRA_TRIANGLES)
    return edge_directions

def test_gaussian_curvature_matches_the_closed_form(tetra_edge_directions):
    defects, _, _ = ddgmath.compute_gaussian_curvature(tetra_edge_directions,
                                                       TETRA_FACES,
                                                       len(TETRA_VERTICES))

    assert np.allclose(defects, TETRA_DEFECTS)

def test_gaussian_curvature_corner_angles_sum_to_pi(tetra_edge_directions):
    _, corner_angles, _ = ddgmath.compute_gaussian_curvature(tetra_edge_directions,
                                                             TETRA_FACES,
                                                             len(TETRA_VERTICES))

    assert corner_angles.shape == (4, 3)
    assert np.allclose(corner_angles.sum(axis=1), np.pi)

def test_gaussian_curvature_satisfies_gauss_bonnet(tetra_edge_directions):
    """Total angle defect is 2*pi*chi, and a tetrahedron is a sphere: chi = 2."""
    defects, _, _ = ddgmath.compute_gaussian_curvature(tetra_edge_directions,
                                                       TETRA_FACES,
                                                       len(TETRA_VERTICES))

    assert defects.sum() == pytest.approx(2 * np.pi * 2)

def test_gaussian_curvature_ratio_is_the_defect_over_a_full_turn(tetra_edge_directions):
    defects, _, ratio = ddgmath.compute_gaussian_curvature(tetra_edge_directions,
                                                           TETRA_FACES,
                                                           len(TETRA_VERTICES))

    assert np.allclose(ratio, defects / (2 * np.pi))


### Degenerate input
# These record measured behaviour, not an aspiration. Robustness on degenerate
# input is a stated project goal, so the boundary is worth pinning down: a
# flattened triangle is handled, a fully collapsed one is not.
def test_degenerate_face_yields_zero_area_and_zero_normal():
    collinear = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]])

    normals, _, areas, _, _ = ddgmath.compute_triangle_data(collinear)

    assert areas[0] == 0.0
    assert np.allclose(normals[0], 0.0)

def test_collinear_face_still_passes_the_corner_angle_check():
    """Zero area alone does not trip the assert: the angles are 0, 180, 0."""
    collinear = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]])
    _, _, _, _, edge_directions = ddgmath.compute_triangle_data(collinear)

    _, corner_angles, _ = ddgmath.compute_gaussian_curvature(edge_directions,
                                                             np.array([[0, 1, 2]]), 3)

    assert np.allclose(corner_angles.sum(axis=1), np.pi)

def test_fully_collapsed_face_trips_the_corner_angle_assert():
    """All three corners identical, so every edge direction is zero. Each
    corner angle falls back to arccos(0) = 90 deg and the row sums to 270."""
    _, _, _, _, edge_directions = ddgmath.compute_triangle_data(np.zeros((1, 3, 3)))

    with pytest.raises(AssertionError):
        ddgmath.compute_gaussian_curvature(edge_directions, np.array([[0, 1, 2]]), 3)


### compute_face_vertex_ids
def test_face_vertex_ids_recovers_the_faces_from_the_edge_tables():
    face_vertices = ddgmath.compute_face_vertex_ids(TETRA_EDGE_VERTEX_IDS,
                                                    TETRA_FACE_EDGE_IDS)

    assert np.array_equal(face_vertices, np.sort(TETRA_FACES, axis=1))

def test_face_vertex_ids_returns_three_ascending_ids_per_face():
    face_vertices = ddgmath.compute_face_vertex_ids(TETRA_EDGE_VERTEX_IDS,
                                                    TETRA_FACE_EDGE_IDS)

    assert face_vertices.shape == (4, 3)
    assert (np.diff(face_vertices, axis=1) > 0).all(), "ids must be strictly ascending"


### Combinatorial operators: closure, star, link
def _operands(vertices=(), edges=(), faces=()):
    """Build the ``(vertices, edges, faces)`` triple the operators take."""
    return (np.array(vertices, dtype=np.int64),
            np.array(edges, dtype=np.int64),
            np.array(faces, dtype=np.int64))

def _closure(simplices):
    return ddgmath.reference_simplex_closure(TETRA_EDGE_VERTEX_IDS,
                                             TETRA_FACE_EDGE_IDS, simplices)

def _star(simplices):
    return ddgmath.reference_simplex_star(TETRA_EDGE_VERTEX_IDS,
                                          TETRA_FACE_EDGE_IDS, simplices)

def _link(simplices):
    return ddgmath.reference_simplex_link(TETRA_EDGE_VERTEX_IDS,
                                          TETRA_FACE_EDGE_IDS, simplices)

def _as_lists(result):
    return [array.tolist() for array in result]

def test_closure_of_a_vertex_is_the_vertex():
    assert _as_lists(_closure(_operands(vertices=[0]))) == [[0], [], []]

def test_closure_of_an_edge_adds_its_endpoints():
    # Edge 0 is (0, 1). Closure descends only, so no face is added.
    assert _as_lists(_closure(_operands(edges=[0]))) == [[0, 1], [0], []]

def test_closure_of_a_face_adds_its_edges_and_vertices():
    # Face 0 carries edges 1, 2, 0, whose endpoints are vertices 0, 1, 2.
    assert _as_lists(_closure(_operands(faces=[0]))) == [[0, 1, 2], [0, 1, 2], [0]]

def test_star_of_a_vertex_is_everything_that_contains_it():
    # Vertex 0 sits on edges 0, 1, 3 and on faces 0, 1, 2.
    assert _as_lists(_star(_operands(vertices=[0]))) == [[0], [0, 1, 3], [0, 1, 2]]

def test_star_of_an_edge_adds_only_faces():
    # Nothing but a vertex contains a vertex, so the vertex slot stays empty.
    assert _as_lists(_star(_operands(edges=[0]))) == [[], [0], [0, 1]]

def test_star_of_a_face_is_the_face_alone():
    """A face is maximal in a 2-complex, so nothing contains it."""
    assert _as_lists(_star(_operands(faces=[0]))) == [[], [], [0]]

def test_link_of_a_vertex_is_its_one_ring():
    # The opposite face of the tetrahedron: a closed cycle, with no faces of its own.
    assert _as_lists(_link(_operands(vertices=[0]))) == [[1, 2, 3], [2, 4, 5], []]

def test_link_of_an_edge_is_the_two_opposite_vertices():
    """Guards the ``Lk(S) = Cl(St(S)) - St(Cl(S))`` form.

    The subtracted term is ``St(Cl(S))``, not ``St(S)``. With ``St(S)`` the
    edge's own endpoints, vertices 0 and 1, would survive into the result.
    """
    assert _as_lists(_link(_operands(edges=[0]))) == [[2, 3], [], []]

def test_link_of_a_face_is_empty():
    """St(f) is f alone, and Cl(St(f)) is contained in St(Cl(f))."""
    assert _as_lists(_link(_operands(faces=[0]))) == [[], [], []]

@pytest.mark.parametrize("operator", [_closure, _star, _link])
def test_operators_accept_empty_input(operator):
    assert all(len(part) == 0 for part in operator(_operands()))

@pytest.mark.parametrize("operator", [_closure, _star, _link])
def test_operators_accept_bare_python_lists(operator):
    """Empty lists must not become float64 arrays and poison the indexing."""
    result = operator(([], [], []))

    assert all(np.issubdtype(part.dtype, np.integer) for part in result)

@pytest.mark.parametrize("simplices", [
    _operands(vertices=[0]),
    _operands(edges=[0]),
    _operands(faces=[0]),
    _operands(vertices=[0, 3], edges=[1, 5], faces=[2]),
])
def test_closure_is_idempotent(simplices):
    once = _closure(simplices)

    assert all(np.array_equal(a, b) for a, b in zip(once, _closure(once)))

@pytest.mark.parametrize("simplices", [
    _operands(vertices=[0]),
    _operands(edges=[0]),
    _operands(vertices=[0, 3], edges=[1, 5], faces=[2]),
])
def test_star_is_idempotent(simplices):
    once = _star(simplices)

    assert all(np.array_equal(a, b) for a, b in zip(once, _star(once)))

@pytest.mark.parametrize("operator", [_closure, _star])
def test_closure_and_star_both_contain_their_input(operator):
    simplices = _operands(vertices=[0, 3], edges=[1, 5], faces=[2])

    result = operator(simplices)

    assert all(np.isin(np.unique(given), got).all()
               for given, got in zip(simplices, result))

def test_closure_of_the_star_is_a_complex():
    """St(S) is generally not a complex, but Cl(St(S)) is. Every edge of the
    result must have both endpoints present, and every face all three edges."""
    vertices, edges, faces = _closure(_star(_operands(vertices=[0])))

    assert np.isin(TETRA_EDGE_VERTEX_IDS[edges], vertices).all()
    assert np.isin(TETRA_FACE_EDGE_IDS[faces], edges).all()


### Generic helpers
def test_normalize_maps_the_span_onto_zero_one():
    assert ddgmath.normalize((0.0, 10.0), 2.5) == pytest.approx(0.25)
    assert ddgmath.normalize((-1.0, 1.0), 0.0) == pytest.approx(0.5)

def test_normalize_does_not_clamp():
    """Out-of-range results carry meaning: this is a cross-item comparator."""
    assert np.allclose(ddgmath.normalize((0.0, 10.0), np.array([-5.0, 15.0])),
                       [-0.5, 1.5])

def test_triangle_ratio_is_one_for_an_equilateral_triangle():
    assert np.allclose(ddgmath.compute_triangle_ratio(np.array([[2.0, 2.0, 2.0]])), 1.0)

def test_triangle_ratio_is_longest_over_shortest():
    assert np.allclose(ddgmath.compute_triangle_ratio(np.array([[1.0, 1.0, 2.0]])), 2.0)

def test_triangle_ratio_reports_zero_for_a_zero_length_edge():
    """Degenerate rather than infinite, matching :func:`compute_vector_values`."""
    with np.errstate(divide="raise", invalid="raise"):
        ratios = ddgmath.compute_triangle_ratio(np.array([[1.0, 0.0, 1.0]]))

    assert ratios[0] == 0.0

def test_triangle_jacobian_columns_are_the_two_edges_from_corner_zero():
    jacobians = ddgmath.compute_triangle_jacobian(TETRA_TRIANGLES)

    assert jacobians.shape == (4, 3, 2)
    assert np.allclose(jacobians[..., 0], TETRA_TRIANGLES[:, 1] - TETRA_TRIANGLES[:, 0])
    assert np.allclose(jacobians[..., 1], TETRA_TRIANGLES[:, 2] - TETRA_TRIANGLES[:, 0])
