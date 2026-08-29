# Plyscope function wrappers
"""
Custom Polyscope wrappers for ease of sue and limiting linter/lance errors messages
ref: https://polyscope.run/py/basics/interactive_UIs_and_animation/#sample-custom-ui
"""

from polyscope import imgui
from polyscope import implot

def button(label):
    """"
    wrapper for ps.imgui.Button()
    """
    return imgui.Button(label)

def separator():
    """
    wrapper for ps.imgui.Separator
    """
    return imgui.Separator()

def combo(a,b,c):
    """
    wrapper for ps.imgui.Separator
    # TODO: Need to improve documentation of this item
    """
    return imgui.Combo(a,b,c)

def same_line():
    """
    wrapper for ps.imgui.SameLine()
    """
    return imgui.SameLine()

def checkbox(value, name: str = "Default Name"):
    """
    wrapper for ps.imgui.Checkbox()
    """
    return imgui.Checkbox(name,value)

def input_text(variable, label: str = "Default Text"):
    """
    wrapper for ps.imgui.InputText()
    """
    return imgui.InputText(label, variable)

def input_int(variable, label: str = "Default Text"):
    """
    wrapper for ps.imgui.InputInt()
    """
    return imgui.InputInt(label, variable)

def input_int3(variable, label: str = "Default Text"):
    """
    wrapper for ps.imgui.InputInt3()
    """
    return imgui.InputInt3(label, variable)

def some_function():
    """
    to use later
    """
    return 0
