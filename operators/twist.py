import bpy


# ---------------------- twist bones -------------------------------
class GenerateTwistUpper(bpy.types.Operator):

    bl_idname = "fg.up_twist_armleg"
    bl_label = "Genx twist arm/leg"
    bl_description = "*First choose a upperarm or thigh bone\nGenerate twist bones for thigh or upperarm fix\n"
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

        bonenames = [bn.name for bn in edit_bones]
        twist_count = 4
        influences = [0.1, 0.33, 0.66, 1.0]
        acvector = ac.tail - ac.head
        twist_length = acvector.length / twist_count
        acvector.normalize()

        twist_bones = []
        for i in range(twist_count):
            twistbonename = "twist_" + str(i + 1) + ac.name
            if not twistbonename in bonenames:
                twistbone = edit_bones.new(name=twistbonename)
            else:
                twistbone = edit_bones[twistbonename]
            twist_bones.append(twistbone)

            twistbone.head = ac.head + acvector * twist_length * i
            twistbone.tail = ac.head + acvector * twist_length * (i + 1)
            twistbone.parent = ac
            twistbone.roll = ac.roll
            twistbone.use_deform = True

        # Convert to pose bones
        twist_bones = [context.object.pose.bones[b.name] for b in twist_bones if b.name in context.object.pose.bones]
        bpy.ops.object.mode_set(mode="POSE")

       

        # Set up constraints for twist bones
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
        bpy.ops.fg.autoparent()
        bpy.context.object.data.pose_position = "POSE"
        return {"FINISHED"}


class GenerateTwistDown(bpy.types.Operator):
    bl_idname = "fg.down_twist_armleg"
    bl_label = "Genx arm/leg"
    bl_description = "Generate twist bones for hand or foot fix\n*First choose a forearm or shin bone\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({"ERROR"}, "No armature object selected")
            return {"CANCELLED"}

        # Switch to edit mode and disable mirroring
        obj.pose.use_mirror_x = False
        obj.data.pose_position = "REST"
        bpy.ops.object.mode_set(mode="EDIT")
        obj.data.use_mirror_x = False

        # Get active bone
        active_bone = context.active_bone
        if not active_bone:
            self.report({"ERROR"}, "No active bone selected")
            return {"CANCELLED"}

        ac = obj.data.edit_bones.get(active_bone.name)
        if not ac:
            self.report({"ERROR"}, "Active bone not found in edit bones")
            return {"CANCELLED"}
        ac.use_deform = False

        # Constants for twist bones
        twist_count = 4
        influences = [0.1, 0.33, 0.66, 1.0]
        ac_vector = (ac.tail - ac.head).normalized()
        twist_length = (ac.tail - ac.head).length / twist_count

        # Create or update twist bones
        twist_bones = []
        for i in range(twist_count):
            twist_bone_name = f"twist_{i + 1}_{ac.name}"
            twist_bone = obj.data.edit_bones.get(twist_bone_name) or obj.data.edit_bones.new(name=twist_bone_name)
            twist_bones.append(twist_bone)

            # Position and parent the twist bone
            twist_bone.head = ac.head + ac_vector * twist_length * i
            twist_bone.tail = ac.head + ac_vector * twist_length * (i + 1)
            twist_bone.parent = ac
            twist_bone.roll = ac.roll
            twist_bone.use_deform = True

        # Switch to pose mode for constraints
        bpy.ops.object.mode_set(mode="POSE")

        # Validate hand bone selection
        hand_bone = context.scene.bone_enum
        if not hand_bone or hand_bone not in obj.pose.bones:
            self.report({"ERROR"}, "No valid hand bone selected")
            return {"CANCELLED"}

        # Apply constraints to twist bones
        for i, bone in enumerate(twist_bones):
            # Sanitize bone name
            sanitized_name = bone.name.encode('utf-8', errors='ignore').decode('utf-8')
            pose_bone = obj.pose.bones.get(sanitized_name)

            # Clear existing constraints
            for constraint in pose_bone.constraints:
                if constraint.type in {"COPY_ROTATION", "DAMPED_TRACK"}:
                    pose_bone.constraints.remove(constraint)

            # Add 'copy rotation' constraint
            copy_rot = pose_bone.constraints.new(type="COPY_ROTATION")
            copy_rot.name = f"Copy Rot {bone.name[:7]}"
            copy_rot.target = obj
            copy_rot.subtarget = hand_bone
            copy_rot.use_x = copy_rot.use_y = copy_rot.use_z = True
            copy_rot.target_space = "LOCAL_WITH_PARENT"
            copy_rot.owner_space = "LOCAL"
            copy_rot.influence = influences[i]

            # Add 'damped track' constraint
            damped_track = pose_bone.constraints.new(type="DAMPED_TRACK")
            damped_track.name = f"Dampd Trck {bone.name[:7]}"
            damped_track.target = obj
            damped_track.subtarget = hand_bone
            damped_track.head_tail = 0

        # Run auto-parenting and update pose position
        bpy.ops.fg.autoparent()
        obj.data.pose_position = "POSE"
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
