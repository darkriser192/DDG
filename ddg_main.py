"""
Here goes a docstring
"""
### Imports
import sys
from pprint import pprint

### Custom Imports
# import ddg_objects as ddg_o
import ddg_poly as ddg_p
import AuxFunctions as aux

### Consts
CLEAR = True

### Main Function
@aux.timed(False)
@aux.memory(True)
def main(pre_load = None):
    """
    Main function separated for time socping and others
    """
    ## Clear the screen or perform any necessary initialization
    if CLEAR:
        aux.clear_terminal()

    app_state = ddg_p.polyscope_app_init(pre_load = pre_load)

    return app_state

### Main File ###
if __name__ == "__main__":
    pprint("File self entry point start")
    # Does this even make sense? No, but i will figure this part out later...
    try:
        DEFAULT_MESH = "D:\\DDG\\rabbit-low-poly.stl"
        meshes = main(pre_load = DEFAULT_MESH)
        print(meshes)
    except Exception as e:
        print(f"Main exited with unhandled exception:\n {e}")
        sys.exit()
    print("File self entry point end")
