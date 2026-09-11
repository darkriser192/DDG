"""
Application entry point and imperative shell for the DDG toolkit.

This module owns the Polyscope application layer: initialization, UI state,
object registration, and orchestration of operations across the semantic
object layer and the DDG functional/math core.

The application layer interprets and coordinates mathematical objects rather
than defining their mathematics. Semantic objects provide the domain-level
contracts and relationships between representations and derived objects,
while ddg_objects remains independent of the application layer.

                         APP STATE
                             │
                    ┌────────┴────────┐
                    │                 │
              Imperative Shell        │
                    │                 │
        ┌───────────┼───────────┐     │
        ▼           ▼           ▼     ▼
    UI State    Object Registry   Initialization
                                   Protocol
                    │
                    ▼
             SEMANTIC OBJECTS
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     Mesh        Support       Lattice
       │            │            │
       └────────────┼────────────┘
                    │
        Relationships / Contracts
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    DDG Objects          Representations
 Functional / Math       Geometry / SDF /...
       Core                   │
          │                   │
          └─────────┬─────────┘
                    ▼
             Computational Core
            Numpy / scipy / ...
                    │
                    ▼
           ...Turtles all the
              way down ...

The dependency is intentionally one-way so that the DDG core can eventually
serve applications beyond this Python/Polyscope implementation.

References
----------
https://github.com/darkriser192/DDG

"""
### Imports
import sys
from importlib import metadata
from pprint import pprint

### Custom Imports
import interfaces.polyscope_app.ddg_poly as ddgpoly
import core.aux_functions as aux
### Consts
CLEAR: bool = False

### Main Function
@aux.timed(False)
@aux.memory(True)
def main(pre_load: str | None = None) -> ddgpoly.AppState:
    """
    Main function separated for time socping and others
    """
    ## Clear the screen or perform any necessary initialization
    if CLEAR:
        aux.clear_terminal()
        print(aux.python_version())
        for dist in metadata.distributions():
            print(f"{dist.metadata['Name']} == {dist.version}")

    app_state = ddgpoly.polyscope_app_init(pre_load = pre_load)

    return app_state

### Main File ###
if __name__ == "__main__":
    pprint("File self entry point start")
    # Does this even make sense? No, but i will figure this part out later...
    try:
        DEFAULT_MESH = ".\\meshes\\rabbit-low-poly.stl"
        meshes = main(pre_load = DEFAULT_MESH)
        print(meshes)
    except Exception as e:
        print(f"Main exited with unhandled exception:\n {e}")
        sys.exit()
    print("File self entry point end")
