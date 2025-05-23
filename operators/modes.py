import bpy



# ------------------modes-------------------#
class Weightpaintmode(bpy.types.Operator):
    bl_idname = "fg.wpaintmode"
    bl_label = "weight paint mode"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        human = context.scene.my_object
        armatur = context.scene.my_armature
        human.select_set(True)
        armatur.select_set(True)
        bpy.context.view_layer.objects.active = human
        bpy.ops.paint.weight_paint_toggle()

        return {"FINISHED"}


class Posemode(bpy.types.Operator):
    bl_idname = "fg.posemode"
    bl_label = "toggle pose mode"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armatur = context.scene.my_armature
        armatur.select_set(True)
        bpy.context.view_layer.objects.active = armatur
        bpy.ops.object.posemode_toggle()

        return {"FINISHED"}

classes = [Weightpaintmode, Posemode]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)   

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()