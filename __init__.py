bl_info = {
    "name": "FG Rig Tools",
    "author": "sasamey",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "category": "Rigging",
    "location": "View3D > Sidebar > Fg",
    "description": "Rigging utilities like bone orientation and Rigify tools.",
}

import sys
import importlib


from . import operators, panels


if "bpy" in locals():
    prefix = __package__ + "."
    for name, module in sys.modules.copy().items():
        if name.startswith(prefix):
            basename = name.removeprefix(prefix)
            globals()[basename] = importlib.reload(module)

import bpy

modules = [operators, panels]


def register():

    for module in modules:
        module.register()


def unregister():

    for module in modules:
        module.unregister()


if __name__ == "__main__":
    register()
