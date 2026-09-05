"""Tests for the Polyscope application layer, without a viewer.

Everything here runs headless. Nothing calls ``ps.init`` or ``ps.show``, so the
tests cover the parts of the app layer that are ordinary Python: the operation
registry, the settings dataclasses, and the mesh bookkeeping. The two places
that must talk to Polyscope are reached with a monkeypatched stub.

The module-level ``app`` is global state, so every test that writes to it goes
through the ``clean_app`` fixture.
"""
import dataclasses

import numpy as np
import pytest

import interfaces.polyscope_app.ddg_poly as ddgpoly
from core.ddg_objects import Geometry

### Fixtures
@pytest.fixture(name="clean_app")
def fixture_clean_app():
    """Empty the loaded meshes for one test, then put the originals back."""
    state = ddgpoly.app.user_interface_state
    saved_meshes = dict(ddgpoly.app.meshes)
    saved_selection = state.selected_mesh

    ddgpoly.app.meshes.clear()
    state.selected_mesh = "<none>"
    yield ddgpoly.app

    ddgpoly.app.meshes.clear()
    ddgpoly.app.meshes.update(saved_meshes)
    state.selected_mesh = saved_selection

@pytest.fixture(name="headless_polyscope")
def fixture_headless_polyscope(monkeypatch):
    """Stub the two Polyscope calls that mesh removal makes.

    ``unload_mesh`` is pure bookkeeping apart from these, and the bookkeeping is
    what the tests are about.
    """
    removed = []
    monkeypatch.setattr(ddgpoly.ps, "has_surface_mesh", lambda name: True)
    monkeypatch.setattr(ddgpoly.ps, "remove_surface_mesh", removed.append)
    return removed

def _load_named(app, *names):
    """Put cheap tetrahedra into the app under the given names."""
    for name in names:
        app.meshes[name] = Geometry(None)
    app.user_interface_state.selected_mesh = names[0]


### The operation registry
def test_importing_the_module_registers_every_operation():
    """The buttons are generated from the registry, so registration happens at
    import time and before ``main`` runs."""
    assert set(ddgpoly.app.operations) == {
        "Compute Mesh Triangle Data",
        "Compute Mesh Dots vs FLOOR",
        "Compute Normal directions",
        "Compute Vertex Error",
    }

def test_every_registered_operation_is_callable():
    assert all(callable(fn) for fn in ddgpoly.app.operations.values())

def test_operation_returns_the_function_unchanged():
    """The decorator registers as a side effect; the function stays directly
    callable, which is what lets an operation be driven from a script."""
    def handler(mesh, ps_mesh):
        return mesh, ps_mesh

    decorated = ddgpoly.operation("test only: unchanged")(handler)

    assert decorated is handler
    del ddgpoly.app.operations["test only: unchanged"]

def test_operation_reusing_a_label_replaces_the_earlier_entry():
    label = "test only: replaced"
    ddgpoly.operation(label)(lambda mesh, ps_mesh: "first")
    ddgpoly.operation(label)(lambda mesh, ps_mesh: "second")

    assert ddgpoly.app.operations[label](None, None) == "second"
    del ddgpoly.app.operations[label]


### Settings dataclasses
def test_app_settings_are_frozen():
    """A runtime write to the build identity would be a bug, not a feature."""
    settings = ddgpoly.AppSettings()

    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.version = "9.9.9"

def test_app_settings_reject_an_empty_version():
    with pytest.raises(ValueError):
        ddgpoly.AppSettings(version="")

def test_polyscope_settings_are_frozen():
    settings = ddgpoly.PolyscopeSettings()

    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.max_framerate = 1

def test_user_interface_state_is_mutable():
    """This one is state, not a recipe, so it must stay writable."""
    state = ddgpoly.UserInterfaceState()
    state.debug = True

    assert state.debug is True

def test_reference_vectors_are_unit_length():
    """They are compared against face normals as ``cos(theta)``, so a
    non-unit entry would silently rescale every dot product."""
    vectors = ddgpoly.UserInterfaceState().reference_vectors

    assert np.allclose([np.linalg.norm(v) for v in vectors.values()], 1.0)

def test_the_floor_reference_the_gui_hardcodes_exists():
    """``_op_compute_dots`` indexes "FLOOR" directly. Until the reference
    becomes an argument, its absence is a KeyError at the button press."""
    assert "FLOOR" in ddgpoly.UserInterfaceState().reference_vectors


### AppState wiring
def test_each_app_state_gets_its_own_sub_objects():
    """Sub-objects are built with ``default_factory``. A bare default would be
    created once at class-definition time and shared by every instance."""
    first, second = ddgpoly.AppState(), ddgpoly.AppState()

    assert first.meshes is not second.meshes
    assert first.user_interface_state is not second.user_interface_state
    assert first.transforms is not second.transforms

def test_app_state_starts_empty():
    fresh = ddgpoly.AppState()

    assert fresh.meshes == {}
    assert fresh.generation == 0
    assert fresh.user_interface_state.selected_mesh == "<none>"


### retrieve_mesh
def test_retrieve_mesh_returns_a_none_triple_when_nothing_is_loaded(clean_app):
    """The three values are None together, so a caller may test any one."""
    assert ddgpoly.retrieve_mesh() == (None, None, None)

def test_retrieve_mesh_returns_a_none_triple_for_an_unknown_selection(clean_app):
    clean_app.user_interface_state.selected_mesh = "never loaded"

    assert ddgpoly.retrieve_mesh() == (None, None, None)


### unload_mesh
def test_unload_removes_the_mesh_from_the_app(clean_app, headless_polyscope):
    _load_named(clean_app, "alpha", "beta")

    ddgpoly.unload_mesh("alpha", clean_app.meshes["alpha"])

    assert "alpha" not in clean_app.meshes
    assert headless_polyscope == ["alpha"], "must also deregister from the viewer"

def test_unload_selects_the_mesh_that_inherits_the_position(clean_app, headless_polyscope):
    _load_named(clean_app, "alpha", "beta", "gamma")

    ddgpoly.unload_mesh("beta", clean_app.meshes["beta"])

    assert clean_app.user_interface_state.selected_mesh == "gamma"

def test_unload_of_the_last_entry_falls_back_to_the_new_last(clean_app, headless_polyscope):
    _load_named(clean_app, "alpha", "beta", "gamma")

    ddgpoly.unload_mesh("gamma", clean_app.meshes["gamma"])

    assert clean_app.user_interface_state.selected_mesh == "beta"

def test_unloading_everything_leaves_no_selection(clean_app, headless_polyscope):
    _load_named(clean_app, "alpha")

    ddgpoly.unload_mesh("alpha", clean_app.meshes["alpha"])

    assert clean_app.meshes == {}
    assert clean_app.user_interface_state.selected_mesh == "<none>"

def test_unloading_nothing_is_a_no_op(clean_app, headless_polyscope, capsys):
    ddgpoly.unload_mesh(None, None)

    assert "No mesh to unload" in capsys.readouterr().out
    assert headless_polyscope == []


### Operations against a real mesh, with a recording stub for the viewer
class RecordingSurfaceMesh:
    """Stands in for ``ps.SurfaceMesh``, recording what an operation displays.

    An operation both mutates the mesh and draws to Polyscope. Until those are
    split, this is how the drawing half gets tested without a GPU.
    """

    def __init__(self):
        self.quantities = {}

    def add_scalar_quantity(self, name, values, defined_on=None, vminmax=None):
        self.quantities[name] = ("scalar", defined_on, np.asarray(values))

    def add_vector_quantity(self, name, values, defined_on=None):
        self.quantities[name] = ("vector", defined_on, np.asarray(values))

    def add_color_quantity(self, name, values, defined_on=None):
        self.quantities[name] = ("color", defined_on, np.asarray(values))

@pytest.fixture(name="tetra_and_viewer")
def fixture_tetra_and_viewer():
    return Geometry(None), RecordingSurfaceMesh()

def test_triangle_data_operation_displays_area_and_height(tetra_and_viewer):
    mesh, viewer = tetra_and_viewer

    ddgpoly.app.operations["Compute Mesh Triangle Data"](mesh, viewer)

    assert viewer.quantities["Face Area"][1] == "faces"
    assert viewer.quantities["Height"][1] == "vertices"
    assert np.allclose(viewer.quantities["Face Area"][2], mesh.face_areas)

def test_normals_operation_encodes_colours_in_the_unit_range(tetra_and_viewer):
    """The mapping is (n + 1) / 2, so every channel must land inside [0, 1]."""
    mesh, viewer = tetra_and_viewer

    ddgpoly.app.operations["Compute Normal directions"](mesh, viewer)

    _, defined_on, colours = viewer.quantities["Normal directions"]

    assert defined_on == "faces"
    assert colours.min() >= 0.0 and colours.max() <= 1.0

def test_curvature_operation_displays_the_defect_and_the_ratio(tetra_and_viewer):
    mesh, viewer = tetra_and_viewer

    ddgpoly.app.operations["Compute Vertex Error"](mesh, viewer)

    assert np.allclose(viewer.quantities["Vertex Defect"][2], mesh.vertex_defects)
    assert np.allclose(viewer.quantities["Gausian Curvature"][2], mesh.defect_ratio)

def test_dots_operation_uses_the_floor_reference(tetra_and_viewer):
    mesh, viewer = tetra_and_viewer

    ddgpoly.app.operations["Compute Mesh Dots vs FLOOR"](mesh, viewer)

    assert "DOT wrt Floor" in viewer.quantities
    assert "Angles wrt Floor" in viewer.quantities
    assert np.allclose(viewer.quantities["DOT wrt Floor"][2], mesh.face_normals[:, 2])

@pytest.mark.parametrize("label", ["Compute Mesh Triangle Data",
                                   "Compute Mesh Dots vs FLOOR",
                                   "Compute Normal directions",
                                   "Compute Vertex Error"])
def test_operations_can_be_invoked_in_any_order(label, tetra_and_viewer):
    """Each operation computes its own prerequisites, so a button works no
    matter which one the user pressed first."""
    mesh, viewer = tetra_and_viewer

    ddgpoly.app.operations[label](mesh, viewer)

    assert viewer.quantities, f"{label} displayed nothing"

@pytest.mark.parametrize("label", ["Compute Mesh Triangle Data",
                                   "Compute Vertex Error"])
def test_operations_are_idempotent(label, tetra_and_viewer):
    """Pressing a button twice is documented as harmless."""
    mesh, viewer = tetra_and_viewer

    ddgpoly.app.operations[label](mesh, viewer)
    first = {k: v[2].copy() for k, v in viewer.quantities.items()}
    ddgpoly.app.operations[label](mesh, viewer)

    assert all(np.allclose(first[k], viewer.quantities[k][2]) for k in first)
