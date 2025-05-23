import bpy


from . import rig_create, modes, ikfksnap,twist


modules = [rig_create, modes, ikfksnap, twist]


def register():

    for module in modules:
        module.register()


def unregister():

    for module in modules:
        module.unregister()


if __name__ == "__main__":
    register()
