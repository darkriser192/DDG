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

    return app_state["Meshes"]

### Main File ###
if __name__ == "__main__":
    pprint("File self entry point start")
    # Does this even make sense? No, but i will figure this part out later...
    try:
        meshes = main('.\\rabbit-low-poly.stl')
        print(meshes)
    except Exception as e:
        pprint(f"Main could not start correctly:\n {e}")
        sys.exit()
    pprint("File self entry point end")
