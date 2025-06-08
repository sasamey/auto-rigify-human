import bpy


def visible_mesh_poll(self, object):
    return object.type == "MESH" and object.visible_get()


def visible_armature_poll(self, object):
    return object.type == "ARMATURE" and object.visible_get()


# 🧠 Enum generator callback
def get_bone_items(self, context):
    # pose mode
    obj = context.object
    if not obj or obj.type != "ARMATURE":
        return [("", "Not an armature", "")]

    objbone = context.active_pose_bone
    bones = obj.pose.bones

    if not objbone or not bones:
        return [("", "No bone selected", "")]

    objbones = []
    for bone in bones:
        head = bone.bone.head_local
        tail = objbone.bone.tail_local
        if abs(head.x - tail.x) < 0.01 and abs(head.y - tail.y) < 0.01 and abs(head.z - tail.z) < 0.01:
            objbones.append(bone)

    if not objbones:
        return [("", "No child bone found", "")]
    return [(bone.name, bone.name, "") for bone in objbones]


class VIEW3D_PT_Selecting(bpy.types.Panel):
    "1"

    bl_label = "Select object & armature first"
    bl_idname = "VIEW3D_PT_Selecting"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Fg"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # visible_meshes = [obj for obj in context.scene.objects if obj.type == "MESH" and obj.visible_get()]
        # # if visible_meshes:
        # #     scene.my_object = visible_meshes[0]
        ob = scene.my_object
        # if ob is None:
        #     ob = visible_meshes[0] if visible_meshes else None
        #     # scene.my_object = ob
        # print("ob", ob,visible_meshes[0] if visible_meshes else None)
        armature = scene.my_armature
        if ob and armature:
            self.bl_label = armature.name.split("_")[0].title() + " vs " + ob.name.split("_")[0].title()

        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row()
        row.alignment = "CENTER"
        row.operator("script.reload", icon="FILE_REFRESH")
        row.separator()

        row = layout.row()
        row.alignment = "LEFT"
        row.label(text="Object:")
        row.prop(scene, "my_object", text="")

        row = layout.row()
        row.alignment = "LEFT"
        row.label(text="Armature:")
        row.prop(scene, "my_armature", text="")
        row.separator()
        layout.separator()


class VIEW3D_PT_Rig_Orienting(bpy.types.Panel):
    "2"

    bl_label = " ...  Auto Rig & Parent   ..."
    bl_idname = "VIEW3D_PT_Rig_Orienting"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Fg"
    # bl_options = {"HIDE_HEADER"}

    def draw(self, context):

        layout = self.layout
        bone = context.active_bone
        bname = bone.name if bone else "?"

        # if bone:
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("fg.generate_rig", text=f"Generate RIG", icon="CONSTRAINT_BONE")
        row.operator("fg.autoparent", text="auto parent", icon="RIGHTARROW_THIN")
        layout.separator()

        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="::: Auto ik ::: ")
        row = layout.row(align=True)
        row.operator("fg.generate_ik", text="Generator ik for " + bname, icon="CON_KINEMATIC")
        col.enabled = True 
        col = row.column(align=True)
        col.scale_x = 0.5
        col.prop(scene, "chain_count")
        col.enabled = False
        layout.separator()

        row = layout.row()
        row.alignment = "CENTER"
        row.label(text=" ::: Snap ::: ")
        row = layout.row(align=True)
        row.operator("fg.ikorfksnap", text="IK or FK", icon="SNAP_ON")
        layout.separator()


class VIEW3D_PT_Smart_Modes(bpy.types.Panel):
    "3"

    bl_label = "Modes"
    bl_idname = "VIEW3D_PT_Smart_Modes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Fg"

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        # layout.use_property_decorate = False

        self.bl_label = "MODE:   ***   " + context.mode.title() + "   ***  "
        obj=context.selected_editable_objects
        
        row = layout.row(align=True)
        if context.mode != "OBJECT":
                row.operator("object.mode_set", text="Object Mode", icon="OBJECT_DATA").mode = "OBJECT"
        if context.mode != "EDIT_ARMATURE" and context.mode != "EDIT_MESH":
            row.operator("object.mode_set", text="Edit Mode", icon="EDITMODE_HLT").mode = "EDIT"

        # if obj:     
        if context.mode != "POSE":
            row.operator("fg.posemode", text="pose mode", icon="POSE_HLT")
        if context.mode != "PAINT_WEIGHT":
            row.operator("fg.wpaintmode", text="weight paint", icon="BRUSH_DATA")
    # row.separator()
        layout.separator()


class VIEW3D_PT_Twist_Fix(bpy.types.Panel):
    "4"

    bl_label = "Twist bones"
    bl_idname = "VIEW3D_PT_Twist_Fix"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Fg"
    # bl_options = {"HIDE_HEADER"}
    # bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        bone = context.active_bone
        if bone:
            scene = context.scene

            row = layout.row()
            # row.alignment = "CENTER"

            row.operator("fg.down_twist_armleg", text="twist down")
            row.prop(scene, "bone_enum", text="")
            row.label(text="", icon="VIEW_PAN")

            row = layout.row()
            row.operator("fg.up_twist_armleg", text="twist up")
            row.prop(context.active_bone, "name", text="", icon_only=True)
            # row.label(text="", icon="GIZMO")

            # layout.separator()
            # row.label(text=context.active_bone.parent.name if context.active_bone.parent else "--> No Parent")

            row = layout.row()


# Custom poll function to allow only visible mesh objects
def visible_mesh_poll(self, object):
    return object.type == "MESH" and object.visible_get()


def visible_armature_poll(self, object):
    return object.type == "ARMATURE" and object.visible_get()


# 🔁 Register
classes = [VIEW3D_PT_Selecting, VIEW3D_PT_Rig_Orienting, VIEW3D_PT_Smart_Modes, VIEW3D_PT_Twist_Fix]

props = [
    ("bone_enum", bpy.props.EnumProperty(name="Child Bone", description="Choose hand or foot bone to fix twist", items=get_bone_items)),
    (
        "my_object",
        bpy.props.PointerProperty(name="Object", type=bpy.types.Object, poll=visible_mesh_poll, description="Select an Object"),
    ),
    (
        "my_armature",
        bpy.props.PointerProperty(name="Armature", type=bpy.types.Object, poll=visible_armature_poll, description="Select an Armature"),
    ),
    ("chain_count", bpy.props.IntProperty(name="", default=2, min=1, max=10, description="Number of bones in the chain")),
]


def register():

    for prop in props:
        setattr(bpy.types.Scene, prop[0], prop[1])

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for prop in props:
        delattr(bpy.types.Scene, prop[0])

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
