import bpy
from bpy.types import Operator
from mathutils import Matrix


class IKFKSnap(Operator):
    """Snap FK to IK or IK to FK"""

    bl_idname = "fg.ikorfksnap"
    bl_label = "IK/FK Snap"
    bl_description = "IK or FK Snap"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        print("---------------------IK/FK Snap------------------------")
        # bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.mode_set(mode="POSE")
        armature = context.active_object
        ac = context.active_pose_bone
        if armature is None or armature.type != "ARMATURE":
            self.report({"WARNING"}, "No armature selected")
            return {"CANCELLED"}
        pb = armature.pose.bones
        ik_bones = []
        # Get all bones with IK constraints
        i = 0
        for b in pb:
            for constraint in b.constraints:
                if constraint.type == "IK":
                    if constraint.subtarget != "":
                        ik_bones.append([b])  #  1 shin
                        ik_bones[i].append(b.parent)  #  2 thigh

                        iktargt = constraint.subtarget
                        ik_bones[i].append(pb[iktargt])  # 3 ik ctrl bone
                        for c in pb[iktargt].children:
                            ik_bones[i].append(c)  # 4 foot
                        for c in b.children:
                            ik_bones[i].append(c)  # 4 foot

                        pole_target = constraint.pole_subtarget
                        if pole_target != "":
                            ik_bones[i].append(pb[pole_target])  # 5 pole target bone
                            # for c in pb[pole_target].children:
                            #     ik_bones[i].append(c)  # 5+ pole target bone child
                        i += 1
        # print("IK bones: ", ik_bones[1])
        for i, b in enumerate(ik_bones):
            for c in b:
                if c == ac:
                    ac = b[0]
                    ikbones = b
                    break
        if ac == None:
            self.report({"WARNING"}, "No IK constraint found")
            return {"CANCELLED"}
        # print("IK bones: ", ikbones)
        frame = context.scene.frame_current
        copymatrx = [b.matrix.copy() for b in ikbones]

        for i, b in enumerate(ikbones):
            b.matrix = copymatrx[i]
            context.view_layer.update()
            b.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            b.keyframe_insert(data_path="location", frame=frame)

        for con in ac.constraints:
            if con.type == "IK":
                con.keyframe_insert(data_path="influence", frame=frame)
                if con.influence < 1:
                    IK_relative_to_Fk = ikbones[0].bone.matrix_local.inverted() @ ikbones[2].bone.matrix_local
                    ikbones[2].matrix = ikbones[0].matrix @ IK_relative_to_Fk
                    # bpy.context.view_layer.update()

                    PV_normal = ((ikbones[0].vector + ikbones[1].vector*-1)).normalized()
                    PV_matrix_loc = ikbones[0].matrix.to_translation() + (PV_normal * ac.length*-3)
                    PV_matrix = Matrix.LocRotScale(PV_matrix_loc, ikbones[4].matrix.to_quaternion(), None)
                    ikbones[4].matrix = PV_matrix
                    # bpy.context.view_layer.update()

                    ikbones[2].keyframe_insert(data_path="location", frame=frame)
                    ikbones[2].keyframe_insert(data_path="rotation_quaternion", frame=frame)
                    # ikbones[2].keyframe_insert(data_path="rotation_euler", frame=frame)

        # bpy.ops.object.mode_set(mode="OBJECT")
        # bpy.ops.object.mode_set(mode="POSE")

        bpy.context.view_layer.update()
        return {"FINISHED"}


classes = [IKFKSnap]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
