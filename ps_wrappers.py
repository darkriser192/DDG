# Plyscope function wrappers
"""
Custom Polyscope wrappers for ease of sue and limiting linter/lance errors messages
ref: https://polyscope.run/py/basics/interactive_UIs_and_animation/#sample-custom-ui
"""

from collections.abc import Sequence

from polyscope import imgui
from polyscope import implot

def button(label: str) -> bool:
    """"
    wrapper for ps.imgui.Button()
    """
    return imgui.Button(label)

def separator() -> None:
    """
    wrapper for ps.imgui.Separator
    """
    return imgui.Separator()

def combo(a: str, b: int, c: Sequence[str]) -> tuple[bool, int]:
    """
    wrapper for ps.imgui.Separator
    # TODO: Need to improve documentation of this item
    """
    return imgui.Combo(a,b,c)

def same_line() -> None:
    """
    wrapper for ps.imgui.SameLine()
    """
    return imgui.SameLine()

def checkbox(value: bool, name: str = "Default Name") -> tuple[bool, bool]:
    """
    wrapper for ps.imgui.Checkbox()
    """
    return imgui.Checkbox(name,value)

def input_text(variable: str, label: str = "Default Text") -> tuple[bool, str]:
    """
    wrapper for ps.imgui.InputText()
    """
    return imgui.InputText(label, variable)

def input_int(variable: int, label: str = "Default Text") -> tuple[bool, int]:
    """
    wrapper for ps.imgui.InputInt()
    """
    return imgui.InputInt(label, variable)

def input_int3(variable: Sequence[int],
               label: str = "Default Text") -> tuple[bool, tuple[int, int, int]]:
    """
    wrapper for ps.imgui.InputInt3()
    """
    return imgui.InputInt3(label, variable)

def some_function() -> int:
    """
    to use later
    """
    return 0
