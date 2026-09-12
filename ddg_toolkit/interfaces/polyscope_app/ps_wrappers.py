# Plyscope function wrappers
"""
Custom Polyscope wrappers for ease of sue and limiting linter/lance errors messages
ref: https://polyscope.run/py/basics/interactive_UIs_and_animation/#sample-custom-ui
"""

from collections.abc import Sequence

from polyscope import imgui
#from polyscope import implot

def button(label: str, button_size: tuple[float, float] = (0.0, 0.0),) -> bool:
    """"Wwrapper for ps.imgui.Button()
    """
    return imgui.Button(label, button_size)

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
    
    imgui.functionA | imgui.sameline | imgui.functionB

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

def slider_float(value: float,
                 v_min: float = -100,
                 v_max: float = 100,
                 str_format: str = '%.3f', 
                 label:str = "Default Slider",
                 flags:int = 0) -> tuple[bool, float]:
    """
    Wrapper for ps.imgui.SliderFloat
    """

    return imgui.SliderFloat(label, value, v_min, v_max, str_format, flags)

def input_float(
        label: str = "Default Input Float",
        value: float = 0.0,
        step: float = 0.0,
        step_fast: float = 0.0,
        string_format: str = '%.3f',
        flags: int = 0,)-> tuple[bool, float]:
    """
    Wrapper for ps.imgui.Inputfloat
    """
    return imgui.InputFloat(label, value, step, step_fast, string_format, flags)
