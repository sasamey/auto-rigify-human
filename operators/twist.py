
import bpy

# ---------------------- twist bones -------------------------------
class GenerateTwistUpper(bpy.types.Operator):

    bl_idname = "fg.up_twist_armleg"
    bl_label = "Genx twist arm/leg"
    bl_description = "Choose upperarm or thigh bone\nGenerate twist bones for thigh or upperarm fix\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.context.object.pose.use_mirror_x = False
        bpy.context.object.data.pose_position = "REST"

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.object.data.use_mirror_x = False
        edit_bones = context.object.data.edit_bones
        activebone = context.active_bone  # context.object.data.edit_bones.active
        ac = edit_bones.get(activebone.name)
        ac.use_deform = False
        if not ac:
            self.report({"ERROR"}, "No active bone selected")
            return {"CANCELLED"}

        bones = [bn.name for bn in edit_bones]
        twist_count = 4
        acvector = ac.tail - ac.head
        twist_length = acvector.length / twist_count
        acvector.normalize()

        twist_bones = []
        for i in range(twist_count):
            twistbonename = "twist_" + str(i + 1) + ac.name
            if not twistbonename in bones:
                twistbone = edit_bones.new(name=twistbonename)
            else:
                twistbone = edit_bones[twistbonename]
            twist_bones.append(twistbone)

            twistbone.head = ac.head + acvector * twist_length * i
            twistbone.tail = ac.head + acvector * twist_length * (i + 1)
            twistbone.parent = ac
            twistbone.roll = ac.roll
            twistbone.use_deform = True

        bpy.ops.object.mode_set(mode="POSE")
        influences = [0.1, 0.33, 0.66, 1.0]
        for i, bone in enumerate(twist_bones):
            twistpbone = context.object.pose.bones[bone.name]
            twistpbone.bone.use_deform = True
            for con in twistpbone.constraints:
                if con.type == "COPY_ROTATION" or con.type == "DAMPED_TRACK" or con.type == "COPY_LOCATION":
                    twistpbone.constraints.remove(con)

            # copy location constraint

            cons1 = twistpbone.constraints.new(type="COPY_LOCATION")
            cons1.name = "Copy Loc " + bone.name[:7]
            cons1.target = context.object
            if i == 0:
                cons1.subtarget = activebone.name
                cons1.head_tail = 0
            else:
                cons1.subtarget = twist_bones[i - 1].name
                cons1.head_tail = 1
            cons1.use_offset = False

            # copy rotation constraint
            cons3 = twistpbone.constraints.new(type="COPY_ROTATION")
            cons3.name = "Copy Rot " + bone.name[:7]
            cons3.target = context.object
            cons3.subtarget = activebone.name
            cons3.use_x = True
            cons3.use_y = True
            cons3.use_z = True
            cons3.influence = influences[i]
            cons3.target_space = "LOCAL_WITH_PARENT"
            cons3.owner_space = "LOCAL"

            # create a damped track constraint for each twist bone
            cons2 = twistpbone.constraints.new(type="DAMPED_TRACK")
            cons2.name = "Dampd Trck " + bone.name[:7]
            cons2.target = context.object
            cons2.subtarget = activebone.name
            cons2.head_tail = 1

        bpy.context.object.data.pose_position = "POSE"
        return {"FINISHED"}


class GenerateTwistDown(bpy.types.Operator):
    bl_idname = "fg.down_twist_armleg"
    bl_label = "Genx arm/leg"
    bl_description = "Generate twist bones for hand or foot fix\nChoose forearm or shin\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.context.object.pose.use_mirror_x = False
        bpy.context.object.data.pose_position = "REST"

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.object.data.use_mirror_x = False
        edit_bones = context.object.data.edit_bones
        activebone = context.active_bone
        ac = edit_bones.get(activebone.name)
        ac.use_deform = False
        if not ac:
            self.report({"ERROR"}, "No active bone selected")
            return {"CANCELLED"}

        bones = [bn.name for bn in edit_bones]
        twist_count = 4
        influences = [0.1, 0.33, 0.66, 1.0]
        acvector = ac.tail - ac.head
        twist_length = acvector.length / twist_count
        acvector.normalize()
        twist_bones = []
        for i in range(twist_count):
            twistbonename = "twist_" + str(i + 1) + ac.name
            if not twistbonename in bones:
                twistbone = edit_bones.new(name=twistbonename)
            else:
                twistbone = edit_bones[twistbonename]
            twist_bones.append(twistbone)

            twistbone.head = ac.head + acvector * twist_length * i
            twistbone.tail = ac.head + acvector * twist_length * (i + 1)
            twistbone.parent = ac
            twistbone.roll = ac.roll
            twistbone.use_deform = True
        twist_bones = [context.object.pose.bones[b.name] for b in twist_bones]
        bpy.ops.object.mode_set(mode="POSE")

      
        handbone = context.scene.bone_enum
        print("handbone: ", handbone)
        if handbone == "":
            self.report({"ERROR"}, "No hand bone selected")
            return {"CANCELLED"}
        if handbone not in bones:
            self.report({"ERROR"}, "No hand bone in bones")
            return {"CANCELLED"}

        for i, bone in enumerate(twist_bones):
            twistpbone = context.object.pose.bones[bone.name]
            twistpbone.bone.use_deform = True
            for con in twistpbone.constraints:
                if con.type == "COPY_ROTATION" or con.type == "DAMPED_TRACK":
                    twistpbone.constraints.remove(con)

            # copy rotation constraint
            cons3 = twistpbone.constraints.new(type="COPY_ROTATION")
            cons3.name = "Copy Rot " + bone.name[:7]
            cons3.target = context.object
            cons3.subtarget = handbone
            cons3.use_x = True
            cons3.use_y = True
            cons3.use_z = True
            cons3.target_space = "LOCAL_WITH_PARENT"
            cons3.owner_space = "LOCAL"
            cons3.influence = influences[i]

            # create a damped track constraint for each twist bone
            cons2 = twistpbone.constraints.new(type="DAMPED_TRACK")
            cons2.name = "Dampd Trck " + bone.name[:7]
            cons2.target = context.object
            cons2.subtarget = handbone
            cons2.head_tail = 0

        bpy.context.object.data.pose_position = "POSE"
        return {"FINISHED"}


# ------------------ register -------------------#
classes = [GenerateTwistUpper, GenerateTwistDown]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
