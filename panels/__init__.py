import bpy


from . import Fg_Panel


modules = [Fg_Panel]


def register():

    for module in modules:
        module.register()

def unregister():

    for module in modules:
        module.unregister()

if __name__ == "__main__":
    register()
