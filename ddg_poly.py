"""
ddg_poly handles the polyscope operations for the ddg app
ref: https://polyscope.run/py/basics/interactive_UIs_and_animation/#sample-custom-ui
"""
## Imports
import os
import sys
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

# TODO: Make app_state a data class to enforce
""" app_state = {
        "App Settings": {# Direct control of initialization settings for polyscope
            "APP_NAME": "Discreate Differential Geometry Toolkit",
            "APP_VERSION": "0.0.1_beta",
            "APP_DEBUG": True,
            "PS_VERBOSITY": 5,
            "PS_BACKEND": "auto",
            "PS_MAX_FRAMERATE": 59,
            "PS_GIVE_FOCUS_ON_SHOW": True,
            "PS_UP_DIR": "z_up",
            "PS_SET_ALWAYS_REDRAW": True,
            "PS_SET_OPEN_IMGUI_WINDOW_FOR_USER_CALLBACK": True,
            },
        ## UI Operations
        "Operations": {},
        ## Global store of meshes in case we want to acumulate
        "Meshes": {}, # [Proposal] Meshes = {"Name 1": {"MeshObject": MeshObject, "Transforms":{"Parent": Some Object, "Childs": {{"Name1":OBJ, ....}} }} }
        "Transforms": {}, # Global store of transforms, these are meaningful external (not object related transfomrs)
        "UI State": {
            "Auto Update": False,
            "Selected IDX": 0,
            "Save Mesh Name": "Default Mesh Name"
        },
        "Reference Vectors": {
            "UP": np.array([0.0,0.0,1.0]), # +Z-axis
            "DOWN": -1 * np.array([0.0,0.0,1.0]), # -Z-axis
            "RIGHT": np.array([1.0,0.0,0.0]), # +X-axis
            "LEFT": -1.0 * np.array([1.0,0.0,0.0]), # -X-axis
            "BACK": np.array([0.0,1.0,0.0]), # +Y-axis
            "FRONT": -1.0 * np.array([0.0,1.0,0.0]), # -Y-axis
            "FLOOR": np.array([0.0,0.0,1.0]), # Direction of the floor
        },
        "Secondary Objects":{ # things that might be incidentally usefull
            "Source": np.array([4500.0,4500.0,4500.0]), # another thing to track locations will use to check direction from some other vector
        }
    } """

class App():
    """
    App class to generate all app settings and store memory, enforce grammart and whatever else

    - ps_settings: Contains all configurations for the polyscope initialization
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
        self.operations = {} # TODO: add subsections based on app state
        self.meshes = {}
        self.transforms = {}
        self.ui_state = {
            "Auto Update": False,
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
    if default_app.ps_settings["APP_DEBUG"]:
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

        if app_state["App Settings"]["APP_DEBUG"]:
            print(f"Loaded a mesh: {name}")
            m = app_state["Meshes"][app_state["UI State"]["Selected Name"]]
            g = m.vertex_vertex_adjacency
            print(f"verts={m.NumVerts}  faces={m.NumFaces}")
            print(f"vertex adjacency (sparse): shape {g.shape}, nnz {g.nnz}, {g.data.nbytes/1e6:.1f} MB")
            attributes = vars(m) # TODO : Change to a  method call later
            print("These are the attributes ", attributes)
            for attr in attributes:
                o = getattr(m, attr, None)
                if hasattr(o, "nbytes"):
                    assert o is not None
                    print(f"  {attr}: {o.nbytes/1e6:.1f} MB")
                elif hasattr(o, "data"):
                    assert o is not None
                    print(f"  {attr}: {o.data.nbytes/1e6:.1f} MB (sparse nnz)")
                else:
                    print(f"  {attr}: {type(o).__name__}")
            print(f"  trimesh vertices: {m.Geometry.vertices.nbytes/1e6:.1f} MB, faces: {m.Geometry.faces.nbytes/1e6:.1f} MB")
    else:
        print("No mesh selected")

@aux.timed(True)
@aux.memory(True)
def retrieve_mesh():
    """
    Fucntion to speed up the operations to retrieve a mesh from the appstate
    """
    name = app_state["UI State"]["Selected Name"]
    mesh = app_state["Meshes"].get(name)
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

    index = list(app_state["Meshes"]).index(name)
    app_state["Meshes"].pop(name, None)

    remaining = list(app_state["Meshes"])
    if remaining:
        app_state["UI State"]["Selected Name"] = remaining[min(index, len(remaining) - 1)]
    else:
        app_state["UI State"]["Selected Name"] = "<none>"

@aux.timed(True)
@aux.memory(True)
def save_mesh(new_name: str):
    """
    Function to save a mesh to stl
    """
    name = app_state["UI State"]["Selected Name"]
    mesh = app_state["Meshes"].get(name)
    assert isinstance(mesh,MeshObject)
    mesh.Geometry.export(new_name + ".stl")

@operation("Compute Mesh Triangle Data")
def _op_compute_triangle_data(mesh, ps_mesh):
    if app_state["App Settings"]["APP_DEBUG"]:
        print(f"Computing Mesh Triangle Data on {app_state['UI State']['Selected Name']}")
    assert isinstance(mesh, MeshObject)
    assert isinstance(ps_mesh, ps.SurfaceMesh)
    mesh.compute_mesh_facet_values()
    assert mesh.FacetAreas is not None
    ps_mesh.add_scalar_quantity("area",
                                defined_on='faces',
                                values=mesh.FacetAreas, # type: ignore
                                vminmax=(0.0, mesh.FacetAreas.max()))
    ps_mesh.add_scalar_quantity("height",
                                defined_on='vertices',
                                values= mesh.Geometry.vertices[:, 2],
                                vminmax= (mesh.Geometry.vertices[:, 2].min(),
                                          mesh.Geometry.vertices[:, 2].max()))

@operation("Compute Mesh Dots vs FLOOR")
def _op_compute_dots(mesh, ps_mesh):
    if app_state["App Settings"]["APP_DEBUG"]:
        print(f"Computing Facet Dot Data on {app_state['UI State']['Selected Name']}")
    assert isinstance(mesh, MeshObject)
    assert isinstance(ps_mesh, ps.SurfaceMesh)
    mesh.compute_mesh_facet_direction(reference=app_state["Reference Vectors"]["FLOOR"])
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
    if app_state["App Settings"]["APP_DEBUG"]:
        print(f"Showing normal directions on {app_state['UI State']['Selected Name']}")
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
    if app_state["App Settings"]["APP_DEBUG"]:
        print(f"Computing vertex error on {app_state['UI State']['Selected Name']} mesh")
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
    changed, app_state["App Settings"]["APP_DEBUG"] = imgui.checkbox(app_state["App Settings"]["APP_DEBUG"],
                                                               "Debug Mode")
    if changed:
        print(f"App changed to {app_state["App Settings"]["APP_DEBUG"]}")
        if not app_state["App Settings"]["APP_DEBUG"]:
            ps.set_verbosity(0)
        else:
            ps.set_verbosity(app_state["App Settings"]["PS_VERBOSITY"])

    imgui.separator()

    # Load / Unload Mesh
    if imgui.button("Load Mesh"):
        try:
            load_mesh()
        except Exception as e:
            print("failed to load mesh as:")
            print(e)
    imgui.same_line()
    if imgui.button(f"Unload {app_state['UI State']['Selected Name']} mesh"):
        name, mesh, ps_mesh = retrieve_mesh()
        unload_mesh(name, mesh)
        ps.reset_camera_to_home_view()

    # Controls selected mesh # TODO: Evaluate if this is the most effective way to operate this step
    mesh_names = list(app_state["Meshes"].keys())
    if mesh_names:
        selected = app_state["UI State"]["Selected Name"]
        index = mesh_names.index(selected) if selected in mesh_names else 0
        changed, index = imgui.combo("Working Mesh", index, mesh_names)
        if changed:
            app_state["UI State"]["Selected Name"] = mesh_names[index]
        ## Save a mesh
        _, app_state["UI State"]["Save Mesh Name"] = imgui.input_text(app_state["UI State"]["Save Mesh Name"], label = "New Mesh Name")
        if imgui.button("Save Mesh"):
            save_mesh(app_state["UI State"]["Save Mesh Name"])
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
    app_settings = default_app.ps_settings
    try:
        ps.init(backend = app_settings["PS_BACKEND"])
        ps.set_program_name(f"{app_settings["APP_NAME"]}. Version: {app_settings["APP_VERSION"]}")
        ps.set_verbosity(app_settings["PS_VERBOSITY"])
        ps.set_max_fps(app_settings["PS_MAX_FRAMERATE"])
        ps.set_give_focus_on_show(app_settings["PS_GIVE_FOCUS_ON_SHOW"])
        ps.set_up_dir(app_settings["PS_UP_DIR"])
        ps.set_always_redraw(app_settings["PS_SET_ALWAYS_REDRAW"])
        ps.set_open_imgui_window_for_user_callback(app_settings["PS_SET_OPEN_IMGUI_WINDOW_FOR_USER_CALLBACK"])

        if app_state["App Settings"]["APP_DEBUG"]:
            print(f"Polyscope Initialized Correctly with settings: \n {app_settings}")

    except Exception as e:
        print(f"Polyscope Could Not Initialized Correctly:\n {e}")
        sys.exit()

    if pre_load is not None:
        load_mesh(pre_load)

    ps.set_user_callback(callback)

    ps.show()

    return app_state
