"""Tests for the geometry container.

Covers what ``Geometry`` adds on top of ``core.ddg_math``: construction, the
self-healing dependency order of the ``compute_*`` methods, the adjacency
structures, and the trimesh oracle. The mathematics itself is tested in
``test_ddg_math`` against literal arrays.

Tests that need the sample mesh skip when it is absent, so the suite still runs
in a checkout without it.
"""
import pathlib

import numpy as np
import pytest
import trimesh

import ddg_toolkit.core.ddg_math as ddgmath
from ddg_toolkit.core.ddg_objects import Geometry

RABBIT = pathlib.Path(__file__).resolve().parent.parent / "meshes" / "rabbit-low-poly.stl"

requires_rabbit = pytest.mark.skipif(not RABBIT.exists(),
                                     reason=f"sample mesh not present: {RABBIT}")

# The tables recorded in the comments of ``Geometry.__init__``, repeated here so
# ``test_tetrahedron_tables_match_trimesh`` can hold them to account. The pure
# math tests use the same literals.
TETRA_EDGE_VERTEX_IDS = np.array([[0, 1], [0, 2], [1, 2], [0, 3], [1, 3], [2, 3]])
TETRA_FACE_EDGE_IDS = np.array([[1, 2, 0], [0, 4, 3], [3, 5, 1], [2, 5, 4]])

### Fixtures
@pytest.fixture(name="tetra")
def fixture_tetra():
    """A fresh built-in tetrahedron. Cheap, so it is rebuilt per test."""
    return Geometry(None)

@pytest.fixture(name="rabbit", scope="module")
def fixture_rabbit():
    """The sample mesh, loaded once for the whole module."""
    return Geometry(str(RABBIT))


### Construction
def test_default_construction_builds_the_test_tetrahedron(tetra):
    assert tetra.name == "Test Tetrahedron"
    assert tetra.path == "<none>"
    assert tetra.number_vertices == 4
    assert tetra.number_faces == 4

def test_construction_is_cheap(tetra):
    """Only the name, path, and counts are set. Everything geometric is lazy."""
    lazy = ["face_normals", "normal_magnitudes", "face_areas", "face_centers",
            "edge_magnitudes", "edge_directions", "vertex_defects",
            "corner_angles", "defect_ratio", "face_face_adjacency",
            "vertex_vertex_adjacency", "vertex_face_adjacency"]

    assert all(getattr(tetra, name) is None for name in lazy)
    assert tetra.face_dots == {}

def test_name_is_the_file_stem():
    """The stem doubles as the Polyscope structure key, so it must not carry
    the extension or the directory."""
    mesh = Geometry(str(RABBIT)) if RABBIT.exists() else None

    if mesh is None:
        pytest.skip("sample mesh not present")
    assert mesh.name == "rabbit-low-poly"

@pytest.mark.xfail(reason="Geometry.__init__ catches the load failure, prints it, "
                          "then fails on the unset trimesh_object with an "
                          "AttributeError that hides the real cause.")
def test_a_missing_file_raises_a_useful_error(tmp_path):
    """The message a user gets should name the file problem, not an
    attribute. Flip this to a plain test once __init__ re-raises."""
    with pytest.raises(ValueError):
        Geometry(str(tmp_path / "no_such_mesh.stl"))


### Reference tables
def test_tetrahedron_tables_match_trimesh(tetra):
    """Guards the literal tables that ``test_ddg_math`` is built on.

    ``Geometry.__init__`` records the edge and face tables in a comment, and
    the pure math tests hardcode them. If trimesh ever orders its
    ``edges_unique`` differently, this is the test that says so.
    """
    assert np.array_equal(tetra.trimesh_object.edges_unique, TETRA_EDGE_VERTEX_IDS)
    assert np.array_equal(tetra.trimesh_object.faces_unique_edges, TETRA_FACE_EDGE_IDS)


### compute_face_values
def test_compute_face_values_sets_every_face_quantity(tetra):
    tetra.compute_face_values()

    assert tetra.face_normals.shape == (4, 3)
    assert tetra.normal_magnitudes.shape == (4,)
    assert tetra.face_areas.shape == (4,)
    assert tetra.edge_magnitudes.shape == (4, 3)
    assert tetra.edge_directions.shape == (4, 3, 3)

def test_face_values_agree_with_trimesh(tetra):
    tetra.compute_face_values()

    assert np.allclose(tetra.face_areas, tetra.trimesh_object.area_faces)
    assert np.allclose(tetra.face_normals, tetra.trimesh_object.face_normals)

def test_face_centers_stays_unset(tetra):
    """Documented behaviour: no method sets it yet. Delete this test when one does."""
    tetra.compute_face_values()

    assert tetra.face_centers is None


### Order independence
# Every compute_* method is documented as self-healing its own prerequisites,
# so the GUI buttons can be pressed in any order. These tests call each method
# on a *fresh* object, with nothing computed beforehand.
def test_vertex_defects_computes_its_own_prerequisites(tetra):
    tetra.compute_vertex_defects()

    assert tetra.vertex_defects is not None
    assert tetra.edge_directions is not None, "should have back-filled the face values"

def test_face_direction_computes_its_own_prerequisites(tetra):
    tetra.compute_face_direction(name="UP")

    assert tetra.face_normals is not None
    assert "UP" in tetra.face_dots

def test_computing_twice_is_harmless(tetra):
    tetra.compute_vertex_defects()
    first = tetra.vertex_defects.copy()
    tetra.compute_vertex_defects()

    assert np.array_equal(first, tetra.vertex_defects)


### compute_face_direction
def test_face_direction_defaults_to_the_up_axis(tetra):
    tetra.compute_face_direction(name="FLOOR")

    dots = tetra.face_dots["FLOOR"]["dots"]

    assert np.allclose(dots, tetra.face_normals[:, 2])

def test_face_direction_keeps_one_entry_per_reference(tetra):
    """Results for several reference directions must coexist."""
    tetra.compute_face_direction(name="UP", reference=np.array([0.0, 0.0, 1.0]))
    tetra.compute_face_direction(name="RIGHT", reference=np.array([1.0, 0.0, 0.0]))

    assert set(tetra.face_dots) == {"UP", "RIGHT"}
    assert not np.allclose(tetra.face_dots["UP"]["dots"],
                           tetra.face_dots["RIGHT"]["dots"])

def test_face_direction_can_skip_the_angle(tetra):
    tetra.compute_face_direction(name="UP", angle=False)

    assert tetra.face_dots["UP"]["angles"] is None

def test_face_direction_reusing_a_key_overwrites_it(tetra):
    tetra.compute_face_direction(name="REF", reference=np.array([0.0, 0.0, 1.0]))
    tetra.compute_face_direction(name="REF", reference=np.array([1.0, 0.0, 0.0]))

    assert len(tetra.face_dots) == 1
    assert np.allclose(tetra.face_dots["REF"]["dots"], tetra.face_normals[:, 0])


### The trimesh oracle
def test_vertex_defects_agree_with_trimesh(tetra):
    """The assert inside compute_vertex_defects is the permanent oracle. This
    test states the same claim from outside, so a failure reads as a test
    failure rather than as an assertion escaping the library."""
    tetra.compute_vertex_defects()

    assert np.allclose(tetra.vertex_defects, tetra.trimesh_object.vertex_defects)

def test_vertex_defects_satisfy_gauss_bonnet(tetra):
    tetra.compute_vertex_defects()

    assert tetra.vertex_defects.sum() == pytest.approx(2 * np.pi * 2)

def test_defect_ratio_is_the_defect_over_a_full_turn(tetra):
    tetra.compute_vertex_defects()

    assert np.allclose(tetra.defect_ratio, tetra.vertex_defects / (2 * np.pi))


### compute_adjacency
def test_adjacency_sets_all_three_structures(tetra):
    tetra.compute_adjacency()

    assert tetra.face_face_adjacency.shape == (4, 4)
    assert tetra.vertex_vertex_adjacency.shape == (4, 4)
    assert tetra.vertex_face_adjacency is not None

def test_adjacency_matrices_are_symmetric(tetra):
    tetra.compute_adjacency()

    for matrix in (tetra.face_face_adjacency, tetra.vertex_vertex_adjacency):
        assert (matrix != matrix.T).nnz == 0

def test_adjacency_holds_connectivity_not_weights(tetra):
    """Every stored entry is 1.0 by design."""
    tetra.compute_adjacency()

    assert np.all(tetra.vertex_vertex_adjacency.data == 1.0)
    assert np.all(tetra.face_face_adjacency.data == 1.0)

def test_vertex_adjacency_has_two_entries_per_unique_edge(tetra):
    """Built from edges_unique, stacked in both orders."""
    tetra.compute_adjacency()

    assert tetra.vertex_vertex_adjacency.nnz == 2 * len(tetra.trimesh_object.edges_unique)

def test_every_tetrahedron_element_touches_every_other(tetra):
    """In a tetrahedron each vertex neighbours the other three, and so does
    each face. A stray self-loop on the diagonal would break this."""
    tetra.compute_adjacency()

    assert np.array_equal(tetra.vertex_vertex_adjacency.toarray(),
                          1.0 - np.eye(4))
    assert np.array_equal(tetra.face_face_adjacency.toarray(),
                          1.0 - np.eye(4))


### Reporting
def test_memory_report_measures_arrays_and_skips_scalars(tetra):
    tetra.compute_face_values()

    report = tetra.memory_report()

    assert report["face_normals"] > 0.0
    assert report["name"] is None, "a string has no measurable buffer"
    assert report["face_centers"] is None, "unset attributes report None"

def test_memory_report_includes_the_underlying_trimesh_buffers(tetra):
    report = tetra.memory_report()

    assert report["trimesh.vertices"] > 0.0
    assert report["trimesh.faces"] > 0.0

def test_repr_names_the_mesh_and_its_counts(tetra):
    text = repr(tetra)

    assert "Test Tetrahedron" in text
    assert "V = 4" in text
    assert "F = 4" in text


### The sample mesh
@requires_rabbit
def test_rabbit_loads_as_a_single_watertight_mesh(rabbit):
    assert isinstance(rabbit.trimesh_object, trimesh.Trimesh)
    assert rabbit.trimesh_object.is_watertight

@requires_rabbit
def test_rabbit_curvature_agrees_with_trimesh(rabbit):
    """The tolerance in compute_vertex_defects is 1e-8 and the measured
    disagreement is around 5e-14, so this also guards that margin."""
    rabbit.compute_vertex_defects()

    assert np.abs(rabbit.vertex_defects
                  - rabbit.trimesh_object.vertex_defects).max() < 1e-12

@requires_rabbit
def test_rabbit_satisfies_gauss_bonnet(rabbit):
    """135k vertices of accumulated floating point still land on chi = 2."""
    rabbit.compute_vertex_defects()

    total_turns = rabbit.vertex_defects.sum() / (2 * np.pi)

    assert total_turns == pytest.approx(rabbit.trimesh_object.euler_number, abs=1e-8)


### Combinatorial operators against a real closed surface
@requires_rabbit
@pytest.mark.parametrize("vertex_id", [0, 1, 1000, 50_000, 135_219])
def test_link_of_an_interior_vertex_is_a_closed_cycle(rabbit, vertex_id):
    """On a closed manifold the link of a vertex is its one-ring boundary: a
    cycle, so it holds as many edges as vertices, and no faces."""
    edge_vertex_ids = np.asarray(rabbit.trimesh_object.edges_unique, dtype=np.int64)
    face_edge_ids = np.asarray(rabbit.trimesh_object.faces_unique_edges, dtype=np.int64)
    empty = np.array([], dtype=np.int64)

    vertices, edges, faces = ddgmath.reference_simplex_link(
        edge_vertex_ids, face_edge_ids, (np.array([vertex_id]), empty, empty))

    assert len(faces) == 0
    assert len(vertices) == len(edges)
    assert vertex_id not in vertices, "the link must exclude its own simplex"

@requires_rabbit
def test_star_of_a_vertex_holds_its_incident_faces(rabbit):
    """Cross-check against trimesh's own vertex_faces table."""
    edge_vertex_ids = np.asarray(rabbit.trimesh_object.edges_unique, dtype=np.int64)
    face_edge_ids = np.asarray(rabbit.trimesh_object.faces_unique_edges, dtype=np.int64)
    empty = np.array([], dtype=np.int64)

    _, _, faces = ddgmath.reference_simplex_star(
        edge_vertex_ids, face_edge_ids, (np.array([7]), empty, empty))

    incident = rabbit.trimesh_object.vertex_faces[7]
    expected = np.unique(incident[incident >= 0])

    assert np.array_equal(faces, expected)
