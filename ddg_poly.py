"""
ddg_poly handles the polyscope operations for the ddg app
ref: https://polyscope.run/py/basics/interactive_UIs_and_animation/#sample-custom-ui
"""
## Imports
import os
import sys
from dataclasses import dataclass, field
from pprint import pprint
import numpy as np
import polyscope as ps

import ddg_objects as ddg_obj
from ddg_objects import MeshObject
import ps_wrappers as imgui
import AuxFunctions as aux

## Consts
TIMED = ddg_obj.TIMED
MEMORY = ddg_obj.MEMORY
ERR = ddg_obj.ERR

class App():
    """
    App class to generate all app settings and store memory, enforce grammart and whatever else

    - app_settings: Contains configurations for app level utilization
    - ps_settings: Contains configurations for the polyscope initialization
    - opperations: Contains the button creation storage
    - meshes: Memory storage for the loaded meshes
    - transforms: Memory storage for a trasnform tree
    - ui_state: where we save all button , fields, checkboxes for the UI
    - reference_vectors: Convention of meaningful vectors I might want to store for use later
    - secondaty: another thing to track locations will use to check direction from some other vector
    """
    def __init__(self) -> None:
        self.app_settings = {
            "APP_NAME": "Discreate Differential Geometry Toolkit",
            "APP_VERSION": "0.0.1_beta",
            "APP_DEBUG": True,
        }
        self.ps_settings = { # Direct control of initialization settings for polyscope
            "PS_VERBOSITY": 5,
            "PS_BACKEND": "auto",
            "PS_MAX_FRAMERATE": 59,
            "PS_GIVE_FOCUS_ON_SHOW": True,
            "PS_UP_DIR": "z_up",
            "PS_SET_ALWAYS_REDRAW": True,
            "PS_SET_OPEN_IMGUI_WINDOW_FOR_USER_CALLBACK": True,
            }
        self.operations = {} # TODO: add subsections based on app menu
        self.meshes = {}
        self.transforms = {}
        self.ui_state = {
            "Auto Update": False,
            "Selected Name": "<none>",
            "Selected IDX": 0,
            "Save Mesh Name": "Default Mesh Name"
            }
        self.reference_vectors = {
            "UP": np.array([0.0,0.0,1.0]), # +Z-axis
            "DOWN": -1 * np.array([0.0,0.0,1.0]), # -Z-axis
            "RIGHT": np.array([1.0,0.0,0.0]), # +X-axis
            "LEFT": -1.0 * np.array([1.0,0.0,0.0]), # -X-axis
            "BACK": np.array([0.0,1.0,0.0]), # +Y-axis
            "FRONT": -1.0 * np.array([0.0,1.0,0.0]), # -Y-axis
            "FLOOR": np.array([0.0,0.0,1.0]), # Direction of the floor
            }
        self.secondary = { # Things that might be incidentally usefull but I have no better place to put
            "Source": np.array([4500.0,4500.0,4500.0]), # another thing to track locations will use to check direction from some other vector
            }

    def __repr__(self) -> str:
        return (f"App(meshes={len(self.meshes)}, "
                f"selected={self.ui_state['Selected Name']!r}, "
                f"operations={len(self.operations)}, "
                f"debug={self.app_settings['APP_DEBUG']})")








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
    version: str = "0.0.1_gamma"

    def __post_init__(self):
        if not self.version:
            raise ValueError("Version Must Be Set")

@dataclass(frozen = False)
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
    backend: str = "auto"
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
    debug: bool = True
    auto_update: bool = True
    selected_mesh: str = "<none>"
    selected_idx: int = 0
    save_mesh_name: str = "Default Mesh Name"
    # working_directory: str =  #TODO: how do i get the local running folder? or set up one. This is a question Matthias always asks
    reference_vectors: dict = field(default_factory = lambda:{ # Not Frozen so we can mutate this dictionary later
        "UP": np.array([0.0,0.0,1.0]), # +Z-axis
        "DOWN": -1 * np.array([0.0,0.0,1.0]), # -Z-axis
        "RIGHT": np.array([1.0,0.0,0.0]), # +X-axis
        "LEFT": -1.0 * np.array([1.0,0.0,0.0]), # -X-axis
        "BACK": np.array([0.0,1.0,0.0]), # +Y-axis
        "FRONT": -1.0 * np.array([0.0,1.0,0.0]), # -Y-axis
        "FLOOR": np.array([0.0,0.0,1.0]), # Direction of the floor
        })
    secondary:dict = field(default_factory = lambda:{ # Used to store random things. but the goal is to move these into other fields or turn this into a usefull field
        "Source": np.array([4500.0,4500.0,4500.0]), # another thing to track locations will use to check direction from some other vector
        })

@dataclass
class AppState():
    """Single container for all state owned by the Polyscope app layer.

    The replacement for :class:`App`. One instance, ``default_app``, is the
    single source of truth for the GUI layer; the math layer in
    ``ddg_objects`` knows nothing about it.

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
    app_settings: AppSettings = field(default=AppSettings())
    polyscope_settings: PolyscopeSettings = field(default_factory=PolyscopeSettings)
    user_interface_state: UserInterfaceState = field(default_factory=UserInterfaceState)

    meshes: dict = field(default_factory=dict)
    operations: dict = field(default_factory=dict)
    transforms: dict = field(default_factory=dict)

    generation: int = 0

    def __repr__(self) -> str:
        string = (
            f"App Setings: \n -{vars(self.app_settings)}\n"
            f"Polyscope Settings: \n -{vars(self.polyscope_settings)}\n"
        )
        return string

default_app = App()

def operation(label):
    """
    Button generation automation function, decorator / wrapper
    """
    def deco(fn):
        default_app.operations[label] = fn
        return fn
    return deco

@aux.timed(TIMED)
@aux.memory(MEMORY)
def load_mesh(file_path = None):
    """
    Takes a filepath and loads it to memory
    """
    if default_app.app_settings["APP_DEBUG"]:
        print("Loading a mesh")

    ## Open a window and retrieve a file path, use it to load into a mesh object
    if file_path is None:
        file_path = aux.read_file()

    if file_path is not None:
        name = os.path.basename(file_path)
        mesh_object = MeshObject(FilePath = file_path,
                                 Name = name)
        default_app.meshes[name] = mesh_object
        default_app.ui_state["Selected Name"] = name
        default_app.ui_state["Selected IDX"] = len(default_app.meshes) - 1

        ps_mesh = ps.register_surface_mesh(mesh_object.Name,
                                           mesh_object.Geometry.vertices,
                                           mesh_object.Geometry.faces)

        ps_mesh.set_back_face_policy('cull')

        ps.reset_camera_to_home_view()

        if default_app.app_settings["APP_DEBUG"]:
            print(f"Loaded a mesh: {name}")
            g = mesh_object.vertex_vertex_adjacency
            print(f"verts={mesh_object.NumVerts}  faces={mesh_object.NumFaces}")
            print(f"vertex adjacency (sparse): shape {g.shape}, nnz {g.nnz}, {g.data.nbytes/1e6:.1f} MB")
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
            print(f"  trimesh vertices: {mesh_object.Geometry.vertices.nbytes/1e6:.1f} MB, faces: {mesh_object.Geometry.faces.nbytes/1e6:.1f} MB")
    else:
        print("No mesh selected")

@aux.timed(True)
@aux.memory(True)
def retrieve_mesh():
    """
    Fucntion to speed up the operations to retrieve a mesh from the appstate
    """
    name = default_app.ui_state["Selected Name"] # app_state["UI State"]["Selected Name"]
    mesh = default_app.meshes.get(name) # app_state["Meshes"].get(name)
    if mesh is None:
        return None, None, None
    return name, mesh, ps.get_surface_mesh(name)

@aux.timed(True)
@aux.memory(True)
def unload_mesh(name, mesh):
    """
    Unload the selected mesh from Polyscope and from app_state.
    """
    if mesh is None:
        return

    if ps.has_surface_mesh(name):
        ps.remove_surface_mesh(name)

    index = list(default_app.meshes).index(name)
    default_app.meshes.pop(name, None)

    remaining = list(default_app.meshes)
    if remaining:
        default_app.ui_state["Selected Name"] = remaining[min(index, len(remaining) - 1)]
    else:
        default_app.ui_state["Selected Name"] = "<none>"

@aux.timed(True)
@aux.memory(True)
def save_mesh(new_name: str):
    """
    Function to save a mesh to stl
    """
    name = default_app.ui_state["Selected Name"]
    mesh = default_app.meshes.get(name)
    assert isinstance(mesh,MeshObject)
    mesh.Geometry.export(new_name + ".stl")

@operation("Compute Mesh Triangle Data")
def _op_compute_triangle_data(mesh, ps_mesh):
    if default_app.app_settings["APP_DEBUG"]:
        print(f"Computing Mesh Triangle Data on {default_app.ui_state['Selected Name']}")
    assert isinstance(mesh, MeshObject)
    assert isinstance(ps_mesh, ps.SurfaceMesh)
    mesh.compute_mesh_facet_values()
    assert mesh.FacetAreas is not None
    ps_mesh.add_scalar_quantity("area",
                                defined_on= 'faces',
                                values= mesh.FacetAreas, # type: ignore
                                vminmax= (0.0, mesh.FacetAreas.max()))
    ps_mesh.add_scalar_quantity("height",
                                defined_on= 'vertices',
                                values= mesh.Geometry.vertices[:, 2],
                                vminmax= (mesh.Geometry.vertices[:, 2].min(),
                                          mesh.Geometry.vertices[:, 2].max()))

@operation("Compute Mesh Dots vs FLOOR")
def _op_compute_dots(mesh, ps_mesh):
    if default_app.app_settings["APP_DEBUG"]:
        print(f"Computing Facet Dot Data on {default_app.ui_state['Selected Name']}")
    assert isinstance(mesh, MeshObject)
    assert isinstance(ps_mesh, ps.SurfaceMesh)
    mesh.compute_mesh_facet_direction(reference = default_app.reference_vectors["FLOOR"])
    assert mesh.FacetDots is not None
    ps_mesh.add_scalar_quantity("DOT",
                                defined_on='faces',
                                values=mesh.FacetDots, # type: ignore
                                vminmax=(mesh.FacetDots.min(), mesh.FacetDots.max()))
    if mesh.Angles is not None:
        ps_mesh.add_scalar_quantity("Angle",
                                    defined_on='faces',
                                    values=np.rad2deg(mesh.Angles),
                                    vminmax=(np.rad2deg(mesh.Angles).min(),
                                             np.rad2deg(mesh.Angles).max()))

@operation("Compute normal directions")
def _op_show_normals(mesh, ps_mesh):
    if default_app.app_settings["APP_DEBUG"]:
        print(f"Showing normal directions on {default_app.ui_state['Selected Name']}")
    assert isinstance(mesh, MeshObject)
    assert isinstance(ps_mesh, ps.SurfaceMesh)

    if mesh.FacetNormals is None:
        mesh.compute_mesh_facet_values()

    assert mesh.FacetNormals is not None

    ps_mesh.add_vector_quantity(name="Normal direction",
                                values= mesh.FacetNormals,
                                defined_on="faces")
    ps_mesh.add_color_quantity(name="normal directions",
                               defined_on="faces",
                               values=( mesh.FacetNormals + 1.0) / 2.0)

@operation("Compute Vertex Error")
def _op_compute_curvature(mesh,ps_mesh):
    if default_app.app_settings["APP_DEBUG"]:
        print(f"Computing vertex error on {default_app.ui_state["Selected Name"]} mesh")
    assert isinstance(mesh, MeshObject)
    assert isinstance(ps_mesh, ps.SurfaceMesh)
    mesh.compute_mesh_vertex_defect()
    assert mesh.vertex_defect is not None
    ps_mesh.add_scalar_quantity("vertex Defect",
                                defined_on = 'vertices',
                                values = mesh.vertex_defect,
                                vminmax= (mesh.vertex_defect.min(),
                                          mesh.vertex_defect.max()))

## Callback definition
@aux.timed(False)
@aux.memory(False)
def callback():
    """
    Constructs all the polyscope buttons
    """
    # Debug mode On/Off
    changed, default_app.app_settings["APP_DEBUG"] = imgui.checkbox(default_app.app_settings["APP_DEBUG"],
                                                                    "Debug Mode")
    if changed:
        print(f"App changed to {default_app.app_settings["APP_DEBUG"]}")
        if not default_app.app_settings["APP_DEBUG"]:
            ps.set_verbosity(0)
        else:
            ps.set_verbosity(default_app.ps_settings["PS_VERBOSITY"])

    imgui.separator()

    # Load / Unload Mesh
    if imgui.button("Load Mesh"):
        try:
            load_mesh()
        except Exception as e:
            print("failed to load mesh as:")
            print(e)
    imgui.same_line()
    if imgui.button(f"Unload {default_app.ui_state['Selected Name']} mesh"):
        name, mesh, ps_mesh = retrieve_mesh()
        unload_mesh(name, mesh)
        ps.reset_camera_to_home_view()

    # Controls selected mesh # TODO: Evaluate if this is the most effective way to operate this step
    mesh_names = list(default_app.meshes.keys())
    if mesh_names:
        selected = default_app.ui_state["Selected Name"]
        index = mesh_names.index(selected) if selected in mesh_names else 0
        changed, index = imgui.combo("Working Mesh", index, mesh_names)
        if changed:
            default_app.ui_state["Selected Name"] = mesh_names[index]
        ## Save a mesh
        _, default_app.ui_state["Save Mesh Name"] = imgui.input_text(default_app.ui_state["Save Mesh Name"], label = "New Mesh Name")
        if imgui.button("Save Mesh"):
            save_mesh(default_app.ui_state["Save Mesh Name"])
            print("save mesh")

    imgui.separator()

    # All @operation buttons render here
    for label, fn in default_app.operations.items():
        if imgui.button(label):
            name, mesh, ps_mesh = retrieve_mesh()
            if mesh is not None:
                fn(mesh, ps_mesh)

    imgui.separator()

## Initialize Polyscope, has fallback
def polyscope_app_init(pre_load = None):
    """
    controls the initialization of polyscope for ddg main
    """

    try:
        ps.init(backend = default_app.ps_settings["PS_BACKEND"])
        ps.set_program_name(f"{default_app.app_settings["APP_NAME"]}. Version: {default_app.app_settings["APP_VERSION"]}")
        ps.set_verbosity(default_app.ps_settings["PS_VERBOSITY"])
        ps.set_max_fps(default_app.ps_settings["PS_MAX_FRAMERATE"])
        ps.set_give_focus_on_show(default_app.ps_settings["PS_GIVE_FOCUS_ON_SHOW"])
        ps.set_up_dir(default_app.ps_settings["PS_UP_DIR"])
        ps.set_always_redraw(default_app.ps_settings["PS_SET_ALWAYS_REDRAW"])
        ps.set_open_imgui_window_for_user_callback(default_app.ps_settings["PS_SET_OPEN_IMGUI_WINDOW_FOR_USER_CALLBACK"])

        if default_app.app_settings["APP_DEBUG"]:
            pprint(f"Polyscope Initialized Correctly with settings: \n {default_app.app_settings}")

    except Exception as e:
        print(f"Polyscope Could Not Initialized Correctly:\n {e}")
        sys.exit()

    if pre_load is not None:
        load_mesh(pre_load)

    ps.set_user_callback(callback)

    ps.show()

    return default_app


if __name__ == "__main__":
    print("Local excecution protyping and testing")

    returns = polyscope_app_init()

    print(returns)

    print("End local excecution prototype and testing")
