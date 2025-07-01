import bpy


# 🔁 Reusable poll functions
def visible_mesh_poll(self, obj):
    return obj.type == "MESH" and obj.visible_get()


def visible_armature_poll(self, obj):
    return obj.type == "ARMATURE" and obj.visible_get()


# 🧠 Bone enum callback
def get_bone_items(self, context):
    obj = context.object
    if not obj or obj.type != "ARMATURE":
        return [("", "Not an armature", "")]
    objbone = context.active_pose_bone
    if not objbone or not obj.pose.bones:
        return [("", "No bone selected", "")]
    matches = [bone for bone in obj.pose.bones if (bone.bone.head_local - objbone.bone.tail_local).length < 0.01]
    return [(b.name, b.name, "") for b in matches] or [("", "No child bone found", "")]


# 🔧 Base panel class
class FG_BasePanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Fg"


# Panels
class VIEW3D_PT_Selecting(FG_BasePanel, bpy.types.Panel):
    bl_label = "Select object & armature first"
    bl_idname = "VIEW3D_PT_Selecting"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        ob, armature = scene.my_object, scene.my_armature

        if ob and armature:
            self.bl_label = f"::: {armature.name.split('_')[0].title()} vs {ob.name.split('_')[0].title()} :::"

        layout.row().operator("script.reload", icon="FILE_REFRESH")
        layout.row(align=True).prop(scene, "my_object")
        layout.row(align=True).prop(scene, "my_armature")
        layout.separator()


class VIEW3D_PT_Rig_Orienting(FG_BasePanel, bpy.types.Panel):
    bl_label = "::: Auto Rig & Parent :::"
    bl_idname = "VIEW3D_PT_Rig_Orienting"

    def draw(self, context):
        layout = self.layout
        armature = context.scene.my_armature
        bone = context.active_bone

        layout.use_property_decorate = False
        row = layout.row(align=True)
        row.operator("fg.generate_rig", text="Generate RIG", icon="CONSTRAINT_BONE")
        row.scale_x = 0.25
        row.prop(armature.data, "use_mirror_x", text="X", icon="MOD_MIRROR")
        layout.row(align=True).operator("fg.autoparent", text="Auto Parent", icon="RIGHTARROW_THIN")
        layout.separator()


class VIEW3D_PT_IK_Fix(FG_BasePanel, bpy.types.Panel):
    bl_label = "::: Generate IK and Pole Bones :::"
    bl_idname = "VIEW3D_PT_IK_Fix"

    def draw(self, context):
        layout = self.layout
        bone = context.active_bone
        armature = context.scene.my_armature

        if bone:
            row = layout.row(align=True)
            row.operator("fg.generate_ik", text=f"IK for {bone.name}", icon="CON_KINEMATIC")
            row.scale_x = 0.25
            row.prop(armature.data, "use_mirror_x", text="X", icon="MOD_MIRROR")
            layout.separator()


class VIEW3D_PT_Twist_Fix(FG_BasePanel, bpy.types.Panel):
    bl_label = "::: Generate Twist Bones :::"
    bl_idname = "VIEW3D_PT_Twist_Fix"
    bl_parent_id = "VIEW3D_PT_IK_Fix"

    def draw(self, context):
        layout = self.layout
        bone = context.active_bone
        scene = context.scene

        if bone:
            row = layout.row(align=True)
            row.operator("fg.down_twist_armleg", text="Hand Fix", icon="VIEW_PAN")
            row.prop(scene, "bone_enum", text="")
            row.scale_x = 0.5

            row = layout.row()
            row.operator("fg.up_twist_armleg", text="Arm Fix", icon="MOD_ARMATURE")
            row.prop(bone, "name", text="")
            row.scale_x = 0.5


class VIEW3D_PT_Smart_Modes(FG_BasePanel, bpy.types.Panel):
    bl_label = ""
    bl_idname = "VIEW3D_PT_Smart_Modes"

    def draw(self, context):
        layout = self.layout
        mode = context.mode
        self.bl_label = f"{mode.title()} mode :::" if mode else ":::...MODE...:::"
        obj = context.object

        row = layout.row(align=True)
        if mode != "OBJECT":
            row.operator("object.mode_set", text="Object Mode").mode = "OBJECT"
        if mode != "EDIT_MESH":
            row.operator("fg.humaneditmode", text="Edit Human")
        if mode != "EDIT_ARMATURE":
            row.operator("fg.boneditmode", text="Edit Bones")
        # layout.separator()

        row = layout.column(align=True)
        row=row.row(align=True)
        if mode != "POSE":
            row.operator("fg.posemode", text="Pose Mode", icon="POSE_HLT")
        if mode != "PAINT_WEIGHT":
            row.operator("fg.wpaintmode", text="Weight Paint", icon="BRUSH_DATA")


class VIEW3D_PT_bone_collection_toggle(FG_BasePanel, bpy.types.Panel):
    bl_label = ""
    bl_idname = "VIEW3D_PT_bone_collection_toggle"
    bl_parent_id = "VIEW3D_PT_Smart_Modes"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        armature = scene.my_armature
        if armature:
            layout.label(text=f"{armature.name.split('_')[0].title()} Collections", icon="GROUP_BONE")
        else:
            layout.label(text="No Armature Selected", icon="ERROR")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        ob, armature = scene.my_object, scene.my_armature
        # layout.use_property_decorate = False
        col = layout.column()
        sq = 0
        for bc in armature.data.collections_all:
            if sq % 2 == 0:
                row = layout.row(align=True)
            sq += 1
            row.prop(bc, "is_visible", text=bc.name, toggle=True)


class VIEW3D_PT_Snap_Fix(FG_BasePanel, bpy.types.Panel):
    bl_label = "::: Snap :::"
    bl_idname = "VIEW3D_PT_Snap_Fix"
    bl_parent_id = "VIEW3D_PT_IK_Fix"

    def draw(self, context):
        if context.mode == "POSE":
            row = self.layout.row(align=True)
            row.alignment = "CENTER"
            row.operator("fg.ikorfksnap", text="IK or FK", icon="SNAP_ON")


# 🔧 Register
classes = [
    VIEW3D_PT_Selecting,
    VIEW3D_PT_Rig_Orienting,
    VIEW3D_PT_IK_Fix,
    VIEW3D_PT_Twist_Fix,
    VIEW3D_PT_Snap_Fix,
    VIEW3D_PT_Smart_Modes,
    VIEW3D_PT_bone_collection_toggle,
]

props = {
    "bone_enum": bpy.props.EnumProperty(name="Child Bone", items=get_bone_items, description="Choose hand or foot bone"),
    "my_object": bpy.props.PointerProperty(name="Human", type=bpy.types.Object, poll=visible_mesh_poll),
    "my_armature": bpy.props.PointerProperty(name="Metarig", type=bpy.types.Object, poll=visible_armature_poll),
    "chain_count": bpy.props.IntProperty(name="", default=2, min=1, max=10, description="Chain Bone Count"),
}


def register():
    for k, v in props.items():
        setattr(bpy.types.Scene, k, v)
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for k in props:
        delattr(bpy.types.Scene, k)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
