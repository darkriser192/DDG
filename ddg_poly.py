"""Polyscope application layer for the DDG toolkit.

Owns everything the viewer needs: the :class:`AppState` container, the
``@operation`` button registry, mesh load/unload/save, and the per-frame
:func:`callback`. The mathematics lives in ``ddg_objects``, which imports
nothing from here -- the dependency runs one way only, so the math layer stays
testable without a GUI.

References
----------
https://polyscope.run/py/basics/interactive_UIs_and_animation/#sample-custom-ui
"""
## Imports
# import os
import sys
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any, Literal
import numpy as np
import polyscope as ps

import ddg_objects as ddg_obj
from ddg_objects import Geometry, FloatArray
import ps_wrappers as imgui
import AuxFunctions as aux

## Type Aliases
# What the @operation registry stores: every button handler takes the working
# mesh and its Polyscope twin, and reports through the viewer rather than a
# return value.
Operation = Callable[[Geometry, ps.SurfaceMesh], None]

## Consts
TIMED: bool = ddg_obj.TIMED
MEMORY: bool = ddg_obj.MEMORY
ERR: float = ddg_obj.ERR

@dataclass(frozen = True)
class AppSettings():
    """Immutable application identity, fixed at startup.

    Holds the values that name the build. Frozen deliberately: a runtime write
    to any of these would be a bug rather than a feature. Runtime toggles, such
    as debug mode, belong in :class:`UserInterfaceState` instead.

    Parameters
    ----------
    name : str
        Program name. Passed to ``ps.set_program_name`` during initialization.
    version : str
        Internal revision string, shown in the window title beside the name.

    Raises
    ------
    ValueError
        If ``version`` is empty.
    """
    name: str = "Discrete Differential Geometry Toolkit"
    version: str = "0.0.2"

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("Version Must Be Set")

@dataclass(frozen = True)
class PolyscopeSettings():
    """Polyscope initialization settings.

    One field per global Polyscope setter called in
    :func:`polyscope_app_init`. Frozen because these are applied once, at
    startup; see Notes for what that means at runtime.

    Parameters
    ----------
    verbosity : int
        Polyscope log verbosity for ``ps.set_verbosity``. 0 silences it.
    backend : str
        Rendering backend passed to ``ps.init``. ``"auto"`` selects a suitable
        one for the platform.
    max_framerate : int
        Redraw cap for ``ps.set_max_fps``.
    give_focus_on_show : bool
        Whether the window takes focus when ``ps.show()`` runs.
    up_dir : str
        Which axis points up, e.g. ``"z_up"``. Sets the navigation frame and
        the ground plane orientation.
    always_redraw : bool
        Redraw every frame instead of only when something changes. Costs GPU
        time; useful while the callback drives animation.
    open_imgui_window_for_user_callback : bool
        Wrap :func:`callback` in an ImGui window automatically. False means the
        callback must open its own window.

    Notes
    -----
    Frozen records intent, not enforcement: Polyscope reads these once, so
    mutating the dataclass after ``ps.init`` would not change the running
    viewer anyway. Settings that must respond at runtime -- verbosity when the
    debug checkbox flips -- are applied by calling the Polyscope setter
    directly, leaving this recipe untouched.
    """
    verbosity: int = 5
    backend: Literal["auto", "openGL3_glfw", "openGL3_egl", "openGL_mock"] = "auto"
    max_framerate: int = 59
    give_focus_on_show: bool = True
    up_dir: str = "z_up"
    always_redraw: bool = True
    open_imgui_window_for_user_callback:bool = True

@dataclass(frozen = False)
class UserInterfaceState():
    """Mutable session state driven by the GUI widgets.

    Everything the user can change while the app runs: toggles, the current
    selection, and text fields. Deliberately not frozen -- this is state, not a
    recipe. Contrast :class:`AppSettings`, which is fixed at startup.

    Parameters
    ----------
    debug : bool
        Debug mode, driven by the "Debug Mode" checkbox. Gates the diagnostic
        prints and selects the Polyscope verbosity to restore.
    auto_update : bool
        Reserved: re-run the active operations when the selection changes.
        Nothing reads it yet.
    selected_mesh : str
        Name of the working mesh, chosen in the "Working Mesh" combo. Keys into
        ``AppState.meshes``. ``"<none>"`` when nothing is loaded.
    selected_idx : int
        Index of the working mesh in the combo. Derived each frame from
        ``selected_mesh``; kept only because the widget needs an integer.
    save_mesh_name : str
        Contents of the export filename field, used by :func:`save_mesh`.
    reference_vectors : dict
        Name -> unit vector, shape (3,). The palette a user picks a reference
        direction from, e.g. ``"FLOOR"``. Seeded with the six axes but
        user-extensible, so it lives here rather than on :class:`AppState`.
    secondary : dict
        Scratch storage for values with no better home yet, including one-off
        derived results such as face clusters. Intended to shrink as its
        contents find real fields.

    Notes
    -----
    Because ``reference_vectors`` is user-editable, an operation must not index
    a hardcoded key into it -- a renamed or deleted entry would raise
    ``KeyError``. Operations should receive the selected vector as an argument;
    :meth:`Geometry.compute_mesh_facet_direction` already takes ``(name,
    reference)`` for this.
    """
    debug: bool = False
    auto_update: bool = True
    selected_mesh: str = "<none>"
    selected_idx: int = 0
    save_mesh_name: str = "Default Mesh Name"
    # working_directory: str =  #TODO: how do i get the local running folder? or set up one. This is a question Matthias always asks
    reference_vectors: dict[str, FloatArray] = field(default_factory = lambda:{ # Not Frozen so we can mutate this dictionary later
        "UP": np.array([0.0,0.0,1.0]), # +Z-axis
        "DOWN": -1 * np.array([0.0,0.0,1.0]), # -Z-axis
        "RIGHT": np.array([1.0,0.0,0.0]), # +X-axis
        "LEFT": -1.0 * np.array([1.0,0.0,0.0]), # -X-axis
        "BACK": np.array([0.0,1.0,0.0]), # +Y-axis
        "FRONT": -1.0 * np.array([0.0,1.0,0.0]), # -Y-axis
        "FLOOR": np.array([0.0,0.0,1.0]), # Direction of the floor
        })
    secondary:dict[str, Any] = field(default_factory = lambda:{ # Used to store random things. but the goal is to move these into other fields or turn this into a usefull field
        "Source": np.array([4500.0,4500.0,4500.0]), # another thing to track locations will use to check direction from some other vector
        })
    vertex_edge_face: tuple[int,int,int] = (0,0,0)

@dataclass
class AppState():
    """Single container for all state owned by the Polyscope app layer.

    One module-level instance, ``app``, is the single source of truth for the
    GUI layer; the math layer in ``ddg_objects`` knows nothing about it.

    Grouping rule: a **dataclass** when the field names are written as literals
    in source, so Pylance can check them; a **dict** when the keys arrive as
    data -- mesh names, operation labels, user-named vectors.

    Parameters
    ----------
    app_settings : AppSettings
        Immutable application identity. Fixed at startup.
    polyscope_settings : PolyscopeSettings
        Polyscope initialization recipe. Applied once by
        :func:`polyscope_app_init`.
    user_interface_state : UserInterfaceState
        Mutable session state driven by the GUI widgets.
    meshes : dict
        Mesh name -> mesh object. The loaded document. Keys match the Polyscope
        structure names, so ``ps.get_surface_mesh(name)`` resolves.
    operations : dict
        Button label -> function, filled at import time by the
        :func:`operation` decorator. A registry of what the app can do, not a
        GUI concern -- the buttons are one way to invoke it.
    transforms : dict
        External transforms, not owned by any single mesh.
    generation : int
        Counter bumped whenever loaded geometry changes. Lets a derived
        quantity be checked for staleness against the geometry it came from.

    Notes
    -----
    These four live here rather than in :class:`UserInterfaceState` by one
    test: *what survives if the GUI is removed and the app is driven from a
    script?* Meshes, transforms, and capabilities survive; the current
    selection and the text fields do not.

    Sub-objects must be supplied with ``default_factory``, not as bare
    defaults. A bare default is built once at class-definition time and shared
    by every instance; Python rejects it outright for anything unhashable,
    which includes any non-frozen dataclass.
    """
    app_settings: AppSettings = field(default_factory=AppSettings)
    polyscope_settings: PolyscopeSettings = field(default_factory=PolyscopeSettings)
    user_interface_state: UserInterfaceState = field(default_factory=UserInterfaceState)

    meshes: dict[str, Geometry] = field(default_factory=dict)
    operations: dict[str, Operation] = field(default_factory=dict)
    transforms: dict[str, Any] = field(default_factory=dict)

    generation: int = 0

    def __repr__(self) -> str:
        string = (
            f"App Setings: \n -{vars(self.app_settings)}\n"
            f"Polyscope Settings: \n -{vars(self.polyscope_settings)}\n"
        )
        return string

app = AppState()

def operation(label: str) -> Callable[[Operation], Operation]:
    """Register a function as a button in the operations panel.

    Decorator factory. The decorated function is stored in ``app.operations``
    under ``label`` and returned unchanged, so it stays directly callable.
    :func:`callback` walks the registry each frame and draws one button per
    entry, which means adding a button is one decorated function and no edit
    to the callback.

    Parameters
    ----------
    label : str
        Button text, and the registry key. Reusing a label replaces the
        earlier entry.

    Returns
    -------
    deco : callable
        Decorator taking ``fn(mesh, ps_mesh)`` and returning it unchanged.

    Side Effects
    ------------
    Writes into the module-level ``app.operations`` at import time, so every
    operation is registered before ``main`` runs.

    Examples
    --------
    >>> @operation("Compute Areas")
    ... def _op_areas(mesh, ps_mesh):
    ...     mesh.compute_mesh_facet_values()
    """
    def deco(fn: Operation) -> Operation:
        app.operations[label] = fn
        return fn
    return deco

@aux.timed(TIMED)
@aux.memory(MEMORY)
def load_mesh(file_path: str | None = None) -> None:
    """Load a mesh from disk and register it with Polyscope.

    Builds a :class:`Geometry`, stores it in ``app.meshes`` keyed by the file
    stem, makes it the working mesh, and registers a Polyscope surface mesh
    under the same name -- the shared key is what lets :func:`retrieve_mesh`
    pair the two later.

    Parameters
    ----------
    file_path : str, optional
        Path to any mesh file ``trimesh`` can read. When None, opens a file
        dialog via :func:`AuxFunctions.read_file`; a cancelled dialog returns
        None and the function reports "No mesh selected" without loading.

    Side Effects
    ------------
    Writes ``app.meshes`` and ``app.user_interface_state``, registers a
    Polyscope structure with back-face culling, and resets the camera. Prints
    a per-attribute memory breakdown when debug is on.

    Notes
    -----
    Loading a file whose stem is already present overwrites both the entry in
    ``app.meshes`` and the Polyscope structure, discarding any scalar
    quantities previously attached to it.
    """
    if app.user_interface_state.debug:
        print("Loading a mesh")

    ## Open a window and retrieve a file path, use it to load into a mesh object
    if file_path is None:
        file_path = aux.read_file()

    if file_path is not None:
        mesh_object = Geometry(
            file_path = file_path,
            )
        name = mesh_object.name
        app.meshes[name] = mesh_object
        app.user_interface_state.selected_mesh = name
        app.user_interface_state.selected_idx = len(app.meshes) - 1

        ps_mesh = ps.register_surface_mesh(mesh_object.name,
                                           mesh_object.trimesh_object.vertices,
                                           mesh_object.trimesh_object.faces)

        ps_mesh.set_back_face_policy('cull') # TODO: Default all to "cull" might change later

        ps.reset_camera_to_home_view()

        if app.user_interface_state.debug:
            print(f"Loaded a mesh: {name}")
            g = mesh_object.vertex_vertex_adjacency
            print(f"verts={mesh_object.number_vertices}  faces={mesh_object.number_faces}")
            if g is not None:
                print(f"vertex adjacency (sparse): shape {g.shape}, nnz {g.nnz}, {g.data.nbytes/1e6:.1f} MB")
            else:
                print("No Adjacency computed")
            attributes = vars(mesh_object) # TODO : Change to a  method call later
            print("These are the attributes ", attributes)
            for attr in attributes:
                o = getattr(mesh_object, attr, None)
                if hasattr(o, "nbytes"):
                    assert o is not None
                    print(f"  {attr}: {o.nbytes/1e6:.1f} MB")
                elif hasattr(o, "data"):
                    assert o is not None
                    print(f"  {attr}: {o.data.nbytes/1e6:.1f} MB (sparse nnz)")
                else:
                    print(f"  {attr}: {type(o).__name__}")
            print(f"- Vertices: {mesh_object.trimesh_object.vertices.nbytes/1e6:.1f} MB,"
                  f"- Faces: {mesh_object.trimesh_object.faces.nbytes/1e6:.1f} MB")
    else:
        print("No mesh selected")

@aux.timed(True)
@aux.memory(True)
def retrieve_mesh() -> tuple[str, Geometry, ps.SurfaceMesh] | tuple[None, None, None]:
    """Fetch the working mesh together with its Polyscope counterpart.

    Returns
    -------
    name : str or None
        Name of the working mesh, or None when nothing is selected.
    mesh : Geometry or None
        The stored geometry, or None.
    ps_mesh : polyscope.SurfaceMesh or None
        The registered Polyscope structure, or None.

    Notes
    -----
    The three values are None together, so a caller may test any one of them.
    The return type says so as a union of two whole tuples rather than three
    independent ``| None`` slots, so a checker narrows all three at once from a
    single test. Returning the name alongside saves callers a second lookup
    when they need it for a label or a message.
    """
    name = app.user_interface_state.selected_mesh
    mesh = app.meshes.get(name)
    if mesh is None:
        return None, None, None

    assert isinstance(mesh, Geometry)

    return name, mesh, ps.get_surface_mesh(name)

@aux.timed(True)
@aux.memory(True)
def unload_mesh(name: str | None, mesh: Geometry | None) -> None:
    """Remove a mesh from Polyscope and from the app state.

    Picks a replacement afterwards so the working mesh stays valid: the entry
    that inherits the removed one's position, or the last remaining entry when
    the removed one was at the end.

    Parameters
    ----------
    name : str
        Mesh name. Serves as both the Polyscope structure name and the key
        into ``app.meshes``.
    mesh : Geometry or None
        The mesh itself. Only tested against None; the removal works entirely
        from ``name``.

    Side Effects
    ------------
    Removes the Polyscope structure, pops the entry from ``app.meshes``, and
    rewrites ``selected_mesh`` -- to ``"<none>"`` when nothing remains.
    """
    if mesh is None:
        print("No mesh to unload")
        return

    if ps.has_surface_mesh(name):
        ps.remove_surface_mesh(name)

    index = list(app.meshes).index(name)
    app.meshes.pop(name, None)

    remaining = list(app.meshes)
    if remaining:
        app.user_interface_state.selected_mesh = remaining[min(index, len(remaining) - 1)]
    else:
        app.user_interface_state.selected_mesh = "<none>"

@aux.timed(True)
@aux.memory(True)
def save_mesh(new_name: str) -> None:
    """Export the working mesh to an STL file.

    Parameters
    ----------
    new_name : str
        Filename stem. ``".stl"`` is appended, and the file is written
        relative to the current working directory.

    Raises
    ------
    KeyError
        If no mesh is selected. The call site in :func:`callback` is guarded
        by a non-empty mesh list, so this only fires if called directly.

    Side Effects
    ------------
    Writes a file, overwriting any existing one without warning.
    """
    name = app.user_interface_state.selected_mesh
    mesh = app.meshes[name]
    mesh.trimesh_object.export(new_name + ".stl")

@operation("Compute Mesh Triangle Data")
def _op_compute_triangle_data(mesh: Geometry, ps_mesh: ps.SurfaceMesh) -> None:
    """Compute per-face geometry and display area and height.

    Side Effects
    ------------
    Populates the mesh facet values; adds "Facet Area" (faces) and "Height"
    (vertices) to the Polyscope structure.

    Notes
    -----
    Height is the raw Z coordinate, so it is only meaningful when ``up_dir``
    is ``"z_up"``. Area is floored at 0.0 rather than at its minimum, so the
    colour map reads as an absolute scale.
    """
    if app.user_interface_state.debug:
        print(f"Computing Mesh Triangle Data on {app.user_interface_state.selected_mesh}")

    mesh.compute_mesh_facet_values()
    # We know for a fact that mesh.facet_areas will never be 'none' after calling a compute_*() method
    assert mesh.facet_areas is not None

    ps_mesh.add_scalar_quantity("Facet Area",
                                defined_on= 'faces',
                                values= mesh.facet_areas,
                                vminmax= (0.0, mesh.facet_areas.max()))
    ps_mesh.add_scalar_quantity("Height",
                                defined_on= 'vertices',
                                values= mesh.trimesh_object.vertices[:, 2],
                                vminmax= (mesh.trimesh_object.vertices[:, 2].min(),
                                          mesh.trimesh_object.vertices[:, 2].max()))

@operation("Compute Mesh Dots vs FLOOR")
def _op_compute_dots(mesh: Geometry, ps_mesh: ps.SurfaceMesh) -> None:
    """Compare face normals against the FLOOR reference direction.

    Stores the result under a named key on the mesh, so results for several
    reference directions can coexist, and displays both the dot product and
    the angle in degrees.

    Side Effects
    ------------
    Writes ``mesh.facet_dots["wrt Floor"]``; adds "DOT wrt Floor" and
    "Angles wrt Floor" to the Polyscope structure, both defined on faces.

    Notes
    -----
    The reference is currently the hardcoded ``"FLOOR"`` key, which will raise
    ``KeyError`` once the user can rename or delete palette entries. The
    reference should become an argument passed from the selection; see
    :class:`UserInterfaceState`.
    """
    if app.user_interface_state.debug:
        print(f"Computing Facet Dot Data on {app.user_interface_state.selected_mesh}")

    reference_name = "wrt Floor"
    mesh.compute_mesh_facet_direction(name = reference_name,reference = app.user_interface_state.reference_vectors["FLOOR"])

    result = mesh.facet_dots[reference_name]
    dots = result["dots"]

    ps_mesh.add_scalar_quantity(f"DOT {reference_name}",
                                defined_on = 'faces',
                                values = dots,
                                vminmax = (dots.min(), dots.max()))

    if result["angles"] is not None:
        angles_in_degs = np.rad2deg(result["angles"])
        ps_mesh.add_scalar_quantity(f"Angles {reference_name}",
                                    defined_on = 'faces',
                                    values = angles_in_degs,
                                    vminmax = (angles_in_degs.min(),
                                               angles_in_degs.max()))

@operation("Compute normal directions")
def _op_compute_normals(mesh: Geometry, ps_mesh: ps.SurfaceMesh) -> None:
    """Display face normals as vectors and as RGB colours.

    Computes the facet values first if they are unset, so the button works
    regardless of the order the user clicks things in.

    Side Effects
    ------------
    May populate the mesh facet values; adds a "Normal direction" vector
    quantity and a "normal directions" colour quantity, both on faces.

    Notes
    -----
    The colour mapping is ``(n + 1) / 2``, which sends each component from
    [-1, 1] into [0, 1] -- the usual normal-map encoding. Opposing faces come
    out as complementary colours.
    """
    if app.user_interface_state.debug:
        print(f"Showing normal directions on {app.user_interface_state.selected_mesh}")

    if mesh.facet_normals is None:
        mesh.compute_mesh_facet_values()
    # Since we hace checked that is not None and if it is none we have computed them
    assert mesh.facet_normals is not None

    ps_mesh.add_vector_quantity(name="Normal direction",
                                values= mesh.facet_normals,
                                defined_on="faces")
    ps_mesh.add_color_quantity(name="normal directions",
                               defined_on="faces",
                               values=(mesh.facet_normals + 1.0) / 2.0)

@operation("Compute Vertex Error")
def _op_compute_curvature(mesh: Geometry, ps_mesh: ps.SurfaceMesh) -> None:
    """Compute and display the per-vertex angle defect.

    The discrete Gaussian curvature: ``2*pi`` minus the corner angles meeting
    at each vertex.

    Side Effects
    ------------
    Populates ``mesh.vertex_defects`` and ``mesh.vertex_angles``; adds
    "Vertex Defect" to the Polyscope structure, defined on vertices.

    Raises
    ------
    AssertionError
        Propagated from :meth:`Geometry.compute_mesh_vertex_defect` when the
        result disagrees with the ``trimesh`` reference. That oracle is
        deliberate -- a failure here means the curvature code is wrong, not
        that the mesh is unusual.
    """
    if app.user_interface_state.debug:
        print(f"Computing vertex error on {app.user_interface_state.selected_mesh} mesh")
    mesh.compute_mesh_vertex_defect()
    # Since we just cumputed them, we know they are not none
    assert mesh.vertex_defects is not None
    ps_mesh.add_scalar_quantity("Vertex Defect",
                                defined_on = 'vertices',
                                values = mesh.vertex_defects,
                                vminmax = (mesh.vertex_defects.min(),
                                          mesh.vertex_defects.max()))

## Callback definition
@aux.timed(False)
@aux.memory(False)
def callback() -> None:
    """Draw the entire custom UI. Runs once per frame.

    Polyscope invokes this at roughly the frame rate, so it must stay cheap.
    Every widget is rebuilt from scratch on each call -- that is what
    immediate mode means -- and any real work belongs behind a button guard.

    Side Effects
    ------------
    Draws widgets and writes their values back into
    ``app.user_interface_state``. Button presses invoke :func:`load_mesh`,
    :func:`unload_mesh`, :func:`save_mesh`, or a registered operation.

    Notes
    -----
    The combo index is derived from ``selected_mesh`` every frame rather than
    stored, so loading or unloading a mesh cannot desynchronise the name from
    the index. Timing is disabled on this function deliberately: at frame rate
    it would flood the log.
    """
    # Debug mode On/Off
    changed_debug, app.user_interface_state.debug = imgui.checkbox(app.user_interface_state.debug,
                                                             "Debug Mode")
    if changed_debug:
        print(f"App changed to {app.user_interface_state.debug}")
        if not app.user_interface_state.debug:
            ps.set_verbosity(0)
        else:
            ps.set_verbosity(app.polyscope_settings.verbosity)

    imgui.separator()

    # Load / Unload Mesh
    if imgui.button("Load Mesh"):
        try:
            load_mesh()
        except Exception as e:
            print("failed to load mesh as:")
            print(e)
    imgui.same_line()
    if imgui.button(f"Unload {app.user_interface_state.selected_mesh} mesh"):
        name, mesh, ps_mesh = retrieve_mesh()
        unload_mesh(name, mesh)
        ps.reset_camera_to_home_view()
    imgui.same_line()
    if imgui.button(f"Print {app.user_interface_state.selected_mesh} memory"):
        #TODO: Needs to make mork, does not work at the moment
        print("Not implemented")

    # Controls selected mesh # TODO: Evaluate if this is the most effective way to operate this step
    mesh_names = list(app.meshes.keys())
    if mesh_names:
        selected = app.user_interface_state.selected_mesh
        index = mesh_names.index(selected) if selected in mesh_names else 0
        changed_working, index = imgui.combo("Working Mesh", index, mesh_names)
        if changed_working:
            app.user_interface_state.selected_mesh = mesh_names[index]
        ## Save a mesh
        changed_new_mesh_name, app.user_interface_state.save_mesh_name = imgui.input_text(
            app.user_interface_state.save_mesh_name,
            label = "New Mesh Name")
        if imgui.button("Save Mesh"):
            save_mesh(app.user_interface_state.save_mesh_name)
            print("save mesh")

    imgui.separator()

    # All @operation buttons render here
    for label, fn in app.operations.items():
        if imgui.button(label):
            name, mesh, ps_mesh = retrieve_mesh()
            # Both tested, not just `mesh`: unpacking the union return loses the
            # "None together" link, so a checker needs each name proved on its own.
            if mesh is not None and ps_mesh is not None:
                fn(mesh, ps_mesh)

    imgui.separator()

    # Do action on vertex id
    # TODO: Chance to Int3 and title line
    change_tuple, app.user_interface_state.vertex_edge_face = imgui.input_int3(app.user_interface_state.vertex_edge_face, "Vert, Edge, Face")

    if imgui.button("Compute vertex's star"):
        name, mesh, ps_mesh = retrieve_mesh()
        
        mesh.geometry_star(coordinates = app.user_interface_state.vertex_edge_face)

## Initialize Polyscope, has fallback
def polyscope_app_init(pre_load: str | None = None, default_app: AppState = app) -> AppState:
    """Initialize Polyscope, install the callback, and run the viewer.

    Applies every field of ``polyscope_settings``, optionally pre-loads a
    mesh, then blocks in ``ps.show()`` until the window closes.

    Parameters
    ----------
    pre_load : str, optional
        Mesh file to load before the window opens. Saves a dialog round-trip
        when restarting repeatedly during development.
    default_app : AppState, optional
        State container to initialize from. Defaults to the module-level
        ``app``. See Notes.

    Returns
    -------
    default_app : AppState
        The same container, returned after the session ends so a caller can
        inspect what was loaded.

    Raises
    ------
    SystemExit
        If Polyscope fails to initialize.

    Notes
    -----
    ``default_app`` is read only here. Every other function in this module --
    :func:`load_mesh`, :func:`callback`, and the operations -- reads the
    module-level ``app`` directly, so passing a different instance would apply
    that instance's settings while the rest of the app kept using the global
    one. Treat the parameter as unfinished rather than as working injection.
    """
    try:
        ps.init(default_app.polyscope_settings.backend)
        ps.set_program_name(f"{default_app.app_settings.name}. Version: {default_app.app_settings.version}")
        ps.set_verbosity(default_app.polyscope_settings.verbosity)
        ps.set_max_fps(default_app.polyscope_settings.max_framerate)
        ps.set_give_focus_on_show(default_app.polyscope_settings.give_focus_on_show)
        ps.set_up_dir(default_app.polyscope_settings.up_dir)
        ps.set_always_redraw(default_app.polyscope_settings.always_redraw)
        ps.set_open_imgui_window_for_user_callback(default_app.polyscope_settings.open_imgui_window_for_user_callback)

        if default_app.user_interface_state.debug:
            print(f"Polyscope Initialized Correctly with settings:\n"
                  f"\n-{default_app.app_settings}\n"
                  f"\n-{default_app.polyscope_settings}\n")

    except Exception as e:
        print(f"Polyscope Could Not Initialized Correctly:\n {e}")
        sys.exit()

    if pre_load is not None:
        load_mesh(pre_load)

    try:
        ps.set_user_callback(callback)
    except Exception as e:
        raise Exception(f"Failed to construct GUI. Polyscope returned: {e}") from e

    ps.show()

    return default_app

# Local testing
if __name__ == "__main__":
    print("Local excecution protyping and testing")

    returns = polyscope_app_init()

    print(returns)

    print("End local excecution prototype and testing")
