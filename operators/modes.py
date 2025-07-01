import bpy


# ------------------modes-------------------#
class Weightpaintmode(bpy.types.Operator):
    bl_idname = "fg.wpaintmode"
    bl_label = "weight paint mode"
    bl_description = "Automatically selects the armature and object\n and switches to weight paint mode\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        human = context.scene.my_object
        armatur = context.scene.my_armature
        armatur.select_set(True)
        human.select_set(True)
        bpy.context.view_layer.objects.active = human
        bpy.ops.object.mode_set(mode="WEIGHT_PAINT")

        return {"FINISHED"}


class Posemode(bpy.types.Operator):
    bl_idname = "fg.posemode"
    bl_label = "toggle pose mode"
    bl_description = "Automatically selects the armature and object\n and switches to pose mode\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armatur = context.scene.my_armature
        armatur.select_set(True)
        bpy.context.view_layer.objects.active = armatur
        bpy.ops.object.posemode_toggle()

        return {"FINISHED"}


class HumanEditmode(bpy.types.Operator):
    bl_idname = "fg.humaneditmode"
    bl_label = "toggle human edit mode"
    bl_description = "Automatically switches to edit mode for human\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armatur = context.scene.my_object
        armatur.select_set(True)
        bpy.context.view_layer.objects.active = armatur
        bpy.ops.object.editmode_toggle()

        return {"FINISHED"}


class BoneEditmode(bpy.types.Operator):
    bl_idname = "fg.boneditmode"
    bl_label = "toggle bone edit mode"
    bl_description = "Automatically switches to edit mode for bones\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armatur = context.scene.my_armature
        armatur.select_set(True)
        bpy.context.view_layer.objects.active = armatur
        bpy.ops.object.editmode_toggle()

        return {"FINISHED"}


classes = [Weightpaintmode, Posemode, HumanEditmode, BoneEditmode]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
