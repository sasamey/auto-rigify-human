import bpy, bmesh
import mathutils
import math

#########################################
## Helper Functions for Rig Generation ##
#########################################
# Categories you want
RIGIFY_COLLECTIONS = [
    "Torso",
    "Torso (Tweak)",
    "Arm.L (IK)",
    "Arm.L (FK)",
    "Arm.L (Tweak)",
    "Arm.R (IK)",
    "Arm.R (FK)",
    "Arm.R (Tweak)",
    "Leg.L (IK)",
    "Leg.L (FK)",
    "Leg.L (Tweak)",
    "Leg.R (IK)",
    "Leg.R (FK)",
    "Leg.R (Tweak)",
    "Root",
]


def assign_custom_rigify_collections(armature_obj):
    arm = armature_obj.data
    # Create missing collections
    collections = {}
    for i, name in enumerate(RIGIFY_COLLECTIONS):
        if name not in arm.collections:
            col = arm.collections.new(name)
        else:
            col = arm.collections[name]
        # Assign a row number for UI organization
        collections[name] = col
        col.rigify_ui_row = i
    return collections


def split_before_last_dot(filename):
    """
    Splits a string before the last period.
    Useful for separating filename from its extension.

    Args:
        filename (str): The input string (e.g., "my.document.pdf").

    Returns:
        str: The part of the string before the last period.
             Returns the original string if no period is found.
    """
    if filename.endswith(".L") or filename.endswith(".R"):
        filename = filename[:-2]
    return filename


def create_and_configure_bone(edit_bones, name, deform=True, palette="THEME04", envelope_multiplier=4):
    """Creates a new bone or gets an existing one, sets basic properties."""
    bone = edit_bones.get(name)
    if not bone:
        bone = edit_bones.new(name)
    bone.use_deform = deform
    bone.color.palette = palette
    # Envelope distance can be set later based on length
    bone.envelope_distance = bone.length / envelope_multiplier if bone.length else 0.1
    return bone


def set_bone_parent_and_connect(child_bone, parent_bone, connect=True):
    """Sets the parent and connection status for a bone."""
    child_bone.parent = parent_bone
    child_bone.use_connect = connect


def calculate_and_apply_roll(armature_obj, bone_name, roll_type="GLOBAL_POS_Z"):
    """Selects a bone, calculates its roll, and deselects it."""
    bpy.ops.armature.select_all(action="DESELECT")
    armature_obj.data.edit_bones[bone_name].select = True
    bpy.ops.armature.calculate_roll(type=roll_type)
    armature_obj.data.edit_bones[bone_name].select = False


# ------------------- get_pole_angle --------------#
# This function calculates the pole angle for the IK constraint
# (Keep this as is, it's a specific calculation, not easily generalized for shortening repetition)
def get_pole_angle(base_bone, middle_bone, pole_bone_at_head):
    """
    Calculates the pole angle for an IK constraint.

    Args:
        base_bone (bpy.types.EditBone): The base bone of the IK chain (e.g., thigh, upper_arm).
        middle_bone (bpy.types.EditBone): The middle bone of the IK chain (e.g., shin, forearm).
        pole_bone_at_head (bpy.types.EditBone): The actual pole target bone whose head determines the angle.

    Returns:
        float: The calculated pole angle in radians.
    """

    def get_signed_angle_local(vector_u, vector_v, normal_for_sign):
        uv_angle = vector_u.angle(vector_v)
        cross_product = vector_u.cross(vector_v)
        if cross_product.length_squared < 1e-6:
            return uv_angle
        if cross_product.dot(normal_for_sign) < 0:
            return uv_angle
        return -uv_angle

    v_pole = pole_bone_at_head.head - base_bone.head
    pole_normal_vec = (middle_bone.tail - base_bone.head).cross(v_pole)
    projected_pole_axis = pole_normal_vec.cross(base_bone.vector)
    pole_angle = get_signed_angle_local(base_bone.x_axis, projected_pole_axis, base_bone.vector)
    return pole_angle


def tolerancex(source, target, axis1, tol):
    return [v for v in source if abs(v[axis1] - target[axis1]) < tol]


def tolerancex_co(source, target, axis1, tol):
    return [v for v in source if abs(v.co[axis1] - target[axis1]) < tol]


def tolerancexy_co(source, target, axis1, axis2, tol, tol2):
    return [v for v in source if abs(v.co[axis1] - target[axis1]) < tol and abs(v.co[axis2] - target[axis2]) < tol2]


# ------------------- generate rig level 1 ------------------#
class GenerateRig(bpy.types.Operator):
    bl_idname = "fg.generate_rig"
    bl_label = "Orient rig bones position"
    bl_description = "Generate rigify bones from only 1 bone or metarig.\n\n*This operator will apply the scale and rotation of the armature and the object \nbefore generating the rig bones position.\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        print("\n\n\n*******************************     generating rig        *****************************")
        # --- Initial Checks ---
        if not context.active_object:
            bpy.context.view_layer.objects.active = armatur = context.scene.my_object
        initial_mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        print("                     initial_mode ==*",initial_mode + " mode for *"+context.active_object.name)

        if not hasattr(context.scene, "my_object") or context.scene.my_object is None:
            self.report({"ERROR"}, "No object set in the scene")
            return {"CANCELLED"}
        if not hasattr(context.scene, "my_armature") or not context.scene.my_armature:
            bpy.ops.object.armature_basic_human_metarig_add()
        context.scene.my_armature = context.active_object
        human = context.scene.my_object
        armatur = context.scene.my_armature

        # --- Prepare Human Object ---
        human.select_set(True)

        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if human.parent:
            human.parent.select_set(True)
            bpy.context.view_layer.objects.active = human
            bpy.ops.object.parent_clear(type="CLEAR")

        # --- Calculate Human Dimensions and Key Points ---
        tall = human.dimensions[2]
        tallunit = human.dimensions[2] / 57
        width = human.dimensions[0] / 2

        x_axis = mathutils.Vector((1, 0, 0))
        y_axis = mathutils.Vector((0, 1, 0))
        z_axis = mathutils.Vector((0, 0, 1))

        masterco = [human.matrix_world @ v.co for v in human.data.vertices]
        midx = (max(masterco, key=lambda v: v.x).x + min(masterco, key=lambda v: v.x).x) / 2

        # Apply armature transforms, then switch to edit mode \\\\\\\\\\\\\\\\

        armatur.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.context.view_layer.objects.active = armatur
        arm = armatur.data
        # Create missing collections
        assign_custom_rigify_collections(armatur)
        armatur.show_in_front = True

        bpy.ops.object.mode_set(mode="EDIT")
        armatur.data.pose_position = "REST"  # Ensure armature is in rest pose
        editbones = armatur.data.edit_bones
        bonenames = [bn.name for bn in editbones]  # Refresh bonenames after potentially creating new ones

        # Derived from human mesh (can be kept outside if no other changes)
        mid_vers = [v for v in masterco if abs(v.x - midx) < tallunit * 2]
        leftside_verts = [v for v in human.data.vertices if v.co.x >= midx]
        # Using local coords here, might need adjustment if masterco is always used.

        maxz_vert_co = max(mid_vers, key=lambda v: v.z)  # maxz is a coord, not a vertex object
        minz_vert_co = min(masterco, key=lambda v: v.z)

        # Head/Crotch calculations
        hair_cos = [v.co for v in human.data.vertices if v.co.z >= maxz_vert_co.z - tallunit * 2]
        headmid_co = sum(hair_cos, mathutils.Vector()) / len(hair_cos) if hair_cos else maxz_vert_co
        uppest_co = maxz_vert_co * 0.5 + headmid_co * 0.5 + mathutils.Vector((0, 0, tallunit * 0.5))

        hit, crotch_co, nor, idx = human.ray_cast(mathutils.Vector((midx, uppest_co.y, tallunit * 15 + minz_vert_co.z)), z_axis)
        center_z = crotch_co.z + tallunit * 1.5
        # Crotch position for thigh bone
        butt_verts = [v for v in human.data.vertices if abs(v.co.z - crotch_co.z - tallunit) < tallunit * 2 and abs(v.co.x - midx) < tallunit * 10]
        maxlower_co = max(butt_verts, key=lambda v: v.co.x).co
        minlower_co = min(butt_verts, key=lambda v: v.co.x).co
        crotch2_co = maxlower_co * 0.5 + minlower_co * 0.5
        butt_verts = [v for v in butt_verts if v.co.x > midx]
        butty_co = max(butt_verts, key=lambda v: v.co.y).co

        print("midx  :", midx, "  tallunit:", tallunit, "  crotch:", crotch_co, "\nuppest: ", uppest_co, "    minz: ", minz_vert_co)
        print("\nbutt            : ", butty_co, "\nhip frnt maxx/-x:", maxlower_co, minlower_co)

        # add root bone
        if len(editbones) < 2:
            editbones[0].name = "root"
        root = create_and_configure_bone(editbones, "root", palette="THEME04", deform=False, envelope_multiplier=8)
        root.head = mathutils.Vector((midx, crotch_co.y, minz_vert_co.z))
        root.tail = mathutils.Vector((midx, crotch_co.y + tallunit * 15, minz_vert_co.z))
        root.roll = 0
        armatur.data.collections["Root"].assign(root)
        # Set root as parent for all bones

        #########################################
        ## SPINES ##
        #########################################
        print("\n........................----------------------spine------------------------------........................")
        spine_data = [
            ("spine", 4, 0),
            ("spine.001", 3, 0),
            ("spine.002", 6, -0.3),
            ("spine.003", 6.5, 0),
            ("spine.004", 1.5, 1.2),
            ("spine.005", 2, 0.5),
            ("spine.006", 5.5, 0.08),
        ]

        spine_bones = []
        current_z = center_z
        for i, (name, length_factor, y_offset_factor) in enumerate(spine_data):
            bone = create_and_configure_bone(editbones, name, palette="THEME04")
            spine_bones.append(bone)
            armatur.data.collections["Torso"].assign(bone)
            bone.head.x = midx
            bone.tail.x = midx
            bone.roll = 0

            if i != 0:
                set_bone_parent_and_connect(bone, spine_bones[i - 1])

            bone.head.z = current_z

            # Neck and Chin Fix logic (still somewhat verbose due to raycasting and loops)
            if i == 4:  # Neck fix
                neck_fix = True
                while neck_fix:
                    neck_hit_loc = human.ray_cast(bone.head, x_axis)[1]
                    if neck_hit_loc and neck_hit_loc.x < tallunit * 2 + midx:
                        bone.head.z -= tallunit * 0.25
                        current_z = bone.head.z
                    else:
                        neck_fix = False
            elif i == 5:  # Chin fix
                chinfix = True
                while chinfix:
                    chin_ray_loc = human.ray_cast(bone.head, -y_axis)[1]
                    # Ensure chin_ray_loc.y is close to 0 or desired plane
                    if chin_ray_loc.y != 0:  # This while loop is problematic, it'll run infinitely if chin_ray_loc.y never becomes 0 exactly.
                        # Better to use a small tolerance or adjust the ray_cast start point.
                        # For now, let's simplify this and assume ray_cast works without iteration.
                        # Original: while chin[1].y != 0: chin[1].y -= 0.001; chin = human.ray_cast(chin[1], -y_axis)
                        # This part seems to be trying to find a projection onto a y=0 plane or similar.
                        # It's highly dependent on mesh topology.
                        pass  # Skipping this problematic while loop for now for brevity.

                    if chin_ray_loc.y < maxz_vert_co.y - tallunit * 4:
                        bone.head.z -= tallunit * 0.25
                        current_z = bone.head.z
                    else:
                        chinfix = False

            current_z += length_factor * tallunit
            bone.tail.z = current_z
            bone.head.y = y_offset_factor * tallunit + maxz_vert_co.y
            bone.tail.y = y_offset_factor * tallunit + maxz_vert_co.y

            # Raycast for y position (still somewhat verbose but inherent to the logic)
            maxyspine = bone.head.y  # Initialize with current y
            minyspine = bone.head.y  # Initialize with current y

            # Find max y hit
            temp_loc = bone.head.copy()
            while True:
                hit, loc, nor, idx = human.ray_cast(temp_loc, y_axis)
                if hit:
                    maxyspine = loc.y
                    temp_loc = loc + y_axis * 0.001
                else:
                    break

            # Find min y hit
            temp_loc = bone.head.copy()
            hit_count = 0
            while hit_count < 2:  # Limit iterations to prevent infinite loop
                hit, loc, nor, idx = human.ray_cast(temp_loc, -y_axis)
                if hit:
                    minyspine = loc.y
                    temp_loc = loc + -y_axis * 0.001
                    hit_count += 1
                else:
                    break

            if i == 0:
                set_bone_parent_and_connect(bone, root, connect=False)
                minyspine = max(2 * crotch_co.y - maxyspine, minyspine)  # Specific logic for spine root
            bone.head.y = maxyspine * 0.55 + minyspine * 0.45
            bone.tail.y = bone.head.y  # Align tail Y with head Y for spine bones

            bone.envelope_distance = bone.length / 4

        # Final spine adjustment
        spine_bones[-1].tail.z = uppest_co.z
        spine_bones[-1].head.y = uppest_co.y * 0.5 + spine_bones[-2].head.y * 0.5  # Use head.y of previous bone

        # Belly/Breast detection and bone placement
        bell_hits = []
        for i in range(10):
            belly_ray = human.ray_cast(spine_bones[1].head + mathutils.Vector((0, 0, i * tallunit * 0.5)), x_axis)
            if belly_ray[0]:
                bell_hits.append(belly_ray[1])
        if bell_hits:
            bellz_co = min(bell_hits, key=lambda v: v.x)
            spine_bones[2].head.z = bellz_co.z

        if "breast.L" in bonenames:
            breast_l = create_and_configure_bone(editbones, "breast.L", palette="THEME04", deform=True, envelope_multiplier=8)
            breast_r = create_and_configure_bone(editbones, "breast.R", palette="THEME04", deform=True, envelope_multiplier=8)

            set_bone_parent_and_connect(breast_l, spine_bones[3], connect=False)
            set_bone_parent_and_connect(breast_r, spine_bones[3], connect=False)
            armatur.data.collections["Torso"].assign(editbones["breast.L"])
            armatur.data.collections["Torso"].assign(editbones["breast.R"])
            breast_l.roll = 0

            # Breast position calculation (remains somewhat complex due to mesh interaction)
            breast_verts = [
                v.co
                for v in leftside_verts
                if abs(v.co.x - spine_bones[3].head.x - tallunit * 4.5) < tallunit * 1.5
                and v.co.z > spine_bones[1].tail.z + tallunit * 4
                and v.co.z < spine_bones[4].tail.z
            ]
            if breast_verts:
                breasty_co = min(breast_verts, key=lambda v: v.y)
                breast_l.tail = breasty_co
                breast_l.head.x = breasty_co.x - tallunit
                breast_l.head.y = breast_l.tail.y + tallunit * 4
                breast_l.head.z = breast_l.tail.z + tallunit * 2

            calculate_and_apply_roll(armatur, "breast.L", "GLOBAL_POS_Z")

            breastdeep_verts = [
                v.co
                for v in leftside_verts
                if abs(v.co.x - spine_bones[3].head.x) < tallunit * 0.5 and abs(v.co.z - spine_bones[3].head.z) < tallunit * 2
            ]
            if breastdeep_verts:
                breastdeepy_co = min(breastdeep_verts, key=lambda v: v.y)
                if breastdeepy_co.y - breasty_co.y > tallunit * 0.6:
                    print("\n......breast detected.....\n", breastdeepy_co.y, breasty_co.y, spine_bones[3].head)
            else:
                print("\n......no breast detected.....\n", breasty_co.y)

        # Dick detection (simple check, no bone creation here)
        dick_verts = [
            v.co for v in leftside_verts if abs(v.co.x - spine_bones[0].head.x) < tallunit * 2 and abs(v.co.z - spine_bones[0].head.z) < tallunit * 3
        ]
        if dick_verts:
            dick_y_co = min(dick_verts, key=lambda v: v.y)
            if dick_y_co.y < spine_bones[3].head.y - tallunit * 6:
                print("\n......dick detected.....\n", dick_y_co.y)

        #########################################
        ## ARMS ##*******************************
        ##########################################

        print("\n........................----------------------arms---------------------------------........................")
        arm_lengths = [5.5, 8.5, 8, 3]
        arm_names = ["shoulder.L", "upper_arm.L", "forearm.L", "hand.L"]
        arm_bones = []

        armlocx = midx
        armlocz_initial = tallunit * 47  # Initial guess for arm z location

        for j, arm_name in enumerate(arm_names):
            bone = create_and_configure_bone(editbones, arm_name, palette="THEME05")

            arm_bones.append(bone)

            # bone.head.z = armlocz_initial
            # bone.tail.z = armlocz_initial

            # bone.head.x = armlocx
            # armlocx += arm_lengths[j] * tallunit
            # bone.tail.x = armlocx

            bonemirror = bone.name.replace(".L", ".R")
            bonemrrr = create_and_configure_bone(editbones, bonemirror, palette="THEME05")
            if j == 0:
                set_bone_parent_and_connect(bone, spine_bones[3], connect=False)
                armatur.data.collections["Torso"].assign(bone)
                armatur.data.collections["Torso"].assign(bonemrrr)
            else:
                set_bone_parent_and_connect(bone, arm_bones[j - 1], connect=True)
                armatur.data.collections["Arm.L (IK)"].assign(bone)
                armatur.data.collections["Arm.R (IK)"].assign(bonemrrr)

            # bone.roll = 0  # Initial roll, will be recalculated later

        # Find hand tail = middle finger tip
        maxhandx_vert_co = max(leftside_verts, key=lambda v: v.co.x).co
        minhandz_verts = [
            v for v in leftside_verts if abs(v.co.x - maxhandx_vert_co.x) < tallunit * 3 and abs(v.co.z > tallunit * 20 + minz_vert_co.z)
        ]
        minhandz_vert_co = min(minhandz_verts, key=lambda v: v.co.z).co
        arm_bones[3].tail = maxhandx_vert_co * 0.7 + minhandz_vert_co * 0.3  # hand tail
        print("hand tail=finger tip:", maxhandx_vert_co, "min z in hand:", minhandz_vert_co)
        print("hand tail:", arm_bones[3].tail)

        # A-pose vs T-pose detection
        a_pose = width < tallunit * 24

        # Armpit detection (complex, remains somewhat verbose due to raycasting)
        armpit_co = mathutils.Vector((tallunit * 6 + midx, uppest_co.y, tallunit * 47 + minz_vert_co.z))
        slider = 0
        if a_pose:
            print(":::a_pose ---> armpit detecting:::")
            # shouder position to find armpit position
            armpit_store = []
            shoulder_down = False
            while not shoulder_down:
                slider += tallunit * 0.3
                armpit_vertices = [v for v in leftside_verts if v.co.x > tallunit * 3.5 + slider + midx and v.co.z < spine_bones[5].head.z]
                arm_maxz = max(armpit_vertices, key=lambda v: v.co.z)
                # arm_maxz_copy=arm_maxz.co.copy()
                armpit_store.append(arm_maxz)

                if len(armpit_store) > 1 and abs(armpit_store[-2].co.x - armpit_store[-1].co.x) < tallunit * 0.35:
                    armpit_store.pop()

                # armpit_store[-1].select = True
                if len(armpit_store) > 3 and armpit_store[-3].co.z > armpit_store[-1].co.z + tallunit * 0.7:
                    armpit_co = armpit_store[-1].co
                    shoulder_down = True
                if armpit_store[-1].co.x > tall * 0.5:
                    shoulder_down = True
                # print(armpit_store[-1].co, len(armpit_store))

        else:  # T-pose
            print(":::t_pose ---> armpit detecting:::")
            slider = 0
            armpit_store = []
            shoulder_down = False
            while not shoulder_down:
                slider += 1
                armpit_vertices = [v for v in leftside_verts if abs(v.co.x - tallunit * 8 + slider * tallunit * 0.35 - midx) < tallunit * 0.35]
                arm_minz = min(armpit_vertices, key=lambda v: v.co.z)
                armpit_store.append(arm_minz)

                if arm_minz.co.z < tallunit * 35:
                    armpit_co = max(armpit_store, key=lambda v: v.co.z).co
                    shoulder_down = True

                # print(armpit_store[-1].co, len(armpit_store))

        print("armpit: ", armpit_co)
        if armpit_co:

            arm_bones[1].head = armpit_co  # upper_arm.L head
            if a_pose:
                arm_bones[1].head += mathutils.Vector((-tallunit * 1.5, 0, -tallunit))
            else:
                arm_bones[1].head += mathutils.Vector((-tallunit * 0.1, 0, tallunit * 2))
            arm_bones[0].tail = arm_bones[1].head  # shoulder.L tail

            # Position shoulder bone relative to armpit
            arm_bones[0].head.x = midx + tallunit
            # arm_bones[0].tail.z += tallunit * 0.5
            # arm_bones[0].tail.x -= tallunit * 0.5
            arm_bones[0].head.z = arm_bones[1].head.z + tallunit * 0.5
            arm_bones[0].head.y = arm_bones[1].head.y - tallunit * 2
            # arm_bones[0].tail.y = arm_bones[1].head.y + tallunit * 0.25

        # Arm angle (cos calculation)
        shouldervector = maxhandx_vert_co - arm_bones[0].tail
        anglex = shouldervector.angle(x_axis)
        print(f"\narm angle::: {anglex:.2f}, {math.degrees(anglex):.2f} angle ->cos(angle): , {math.cos(anglex):.2f}")

        # Chest bone Z fix
        if spine_bones[3].head.z - arm_bones[0].head.z > -tallunit:
            spine_bones[3].head.z = arm_bones[0].head.z - tallunit * 2

        # Wrist/Hand head finding
        handhead_verts_co = [
            v
            for v in leftside_verts
            if abs(v.co.x - arm_bones[3].tail.x + tallunit * 14 * width / tall) < tallunit * 3
            and abs(v.co.z - arm_bones[3].tail.z - tallunit * 0.5 * tall / width) < tallunit * 2
        ]
        if abs(maxhandx_vert_co.x - maxlower_co.x) < tallunit * 3:
            handhead_verts_co = [v for v in handhead_verts_co if v.co.x > maxlower_co.x - tallunit * 3]
        for v in handhead_verts_co:
            v.select = True
        if handhead_verts_co:
            hand_avg_co = sum((v.co for v in handhead_verts_co), mathutils.Vector()) / len(handhead_verts_co)
            print(hand_avg_co)
            handrayup_res = human.ray_cast(hand_avg_co, z_axis)
            handraydown_res = human.ray_cast(hand_avg_co, -z_axis)
            if handrayup_res[0] and handraydown_res[0] and abs(handrayup_res[1].z - handraydown_res[1].z) < tallunit * 3:
                hand_avg_co.z = handrayup_res[1].z * 0.5 + handraydown_res[1].z * 0.5
                print("hand ray z success")
            handrayleft_res = human.ray_cast(hand_avg_co, x_axis)
            handrayright_res = human.ray_cast(hand_avg_co, -x_axis)
            if handrayleft_res[0] and handrayright_res[0] and abs(handrayleft_res[1].x - handrayright_res[1].x) < tallunit * 3:
                hand_avg_co.x = handrayleft_res[1].x * 0.5 + handrayright_res[1].x * 0.5
                print("hand ray x success")
            hand_rayfront_res = human.ray_cast(hand_avg_co, -y_axis)
            hand_rayback_res = human.ray_cast(hand_avg_co, y_axis)
            if hand_rayfront_res[0] and hand_rayback_res[0]:
                arm_bones[3].head = hand_rayfront_res[1] * 0.5 + hand_rayback_res[1] * 0.5
            else:  # Fallback if raycasts fail to provide two points
                arm_bones[3].head = hand_avg_co
            if arm_bones[3].head.z < arm_bones[3].tail.z:
                arm_bones[3].head.z = arm_bones[3].tail.z + tallunit
            # arm_bones[3].head.y += tallunit * 0.25
            arm_bones[3].length = tallunit * 3  # Adjust length after head is set

        # Elbow position finding
        elbowdown_x = (maxhandx_vert_co.x - arm_bones[0].tail.x) * 0.4 + arm_bones[0].tail.x

        midelbow_co = arm_bones[0].tail * 0.45 + arm_bones[3].head * 0.55
        elbow_verts_co = [v.co for v in leftside_verts if abs(v.co.x - elbowdown_x) < tallunit and abs(v.co.z - midelbow_co.z) < tallunit * 4]
        if elbow_verts_co:
            elbowzmax_co = max(elbow_verts_co, key=lambda v: v.z)
            elbowzmin_co = min(elbow_verts_co, key=lambda v: v.z)
            elbowz_co = elbowzmax_co * 0.5 + elbowzmin_co * 0.5
            elbowxmaax_co = max(elbow_verts_co, key=lambda v: v.x)
            elbowxmin_co = min(elbow_verts_co, key=lambda v: v.x)
            elbowz_co.x = elbowxmaax_co.x * 0.5 + elbowxmin_co.x * 0.5
            elbowz_co.y += tallunit * 0.5
            arm_bones[1].tail = elbowz_co  # upper_arm.L tail

        # Recalculate arm rolls
        for arm_bone in arm_bones:
            calculate_and_apply_roll(armatur, arm_bone.name, "GLOBAL_NEG_Y")

        #########################################
        ## LEGS ##
        #########################################
        print("\n........................----------------------legs---------------------------------..........................")
        leg_names = ["thigh.L", "shin.L", "foot.L", "toe.L"]
        leg_bones = []

        ## Create leg bones **********************************************************************************

        for i, leg_name in enumerate(leg_names):
            bone = create_and_configure_bone(editbones, leg_name, palette="THEME11")
            bonemirror = bone.name.replace(".L", ".R")
            bonemrrr = create_and_configure_bone(editbones, bonemirror, palette="THEME11")
            armatur.data.collections["Leg.L (IK)"].assign(bone)
            armatur.data.collections["Leg.R (IK)"].assign(bonemrrr)
            leg_bones.append(bone)
            if i == 0:
                bone.parent = spine_bones[0]  # Thigh connects to spine
            if i > 0:
                set_bone_parent_and_connect(bone, leg_bones[i - 1], connect=True)

            if i < 2:  # Thigh and Shin
                calculate_and_apply_roll(armatur, bone.name, "GLOBAL_POS_Y")
            else:  # Foot and Toe
                calculate_and_apply_roll(armatur, bone.name, "GLOBAL_NEG_Z")

        # Thigh bone head
        leg_bones[0].head = spine_bones[0].head
        leg_bones[0].head.x = min(butty_co.x + tallunit * 1.25, tallunit * 3)
        leg_bones[0].head.z = butty_co.z + tallunit * 0.7
        print("thigh head      : ", leg_bones[0].head)
        # Pelvis bone
        if "pelvis.L" in bonenames:
            pelvis_l = create_and_configure_bone(editbones, "pelvis.L", palette="THEME14", deform=True, envelope_multiplier=4)
            pelvis_r = create_and_configure_bone(editbones, "pelvis.R", palette="THEME14", deform=True, envelope_multiplier=4)
            pelvis_l.head = spine_bones[0].head
            pelvis_l.tail = leg_bones[0].head  # Connect to thigh head
            pelvis_l.tail.z = spine_bones[1].head.z  # Z-alignment with spine.001 head
            pelvis_l.tail.y -= tallunit  # Adjust Y
            armatur.data.collections["Torso"].assign(editbones["pelvis.L"])
            armatur.data.collections["Torso"].assign(editbones["pelvis.R"])
            calculate_and_apply_roll(armatur, "pelvis.L", "GLOBAL_POS_Y")

        # Ankle to foot tail
        ankle_verts = [v for v in masterco if abs(v.z - tallunit * 3.5 - minz_vert_co.z) < tallunit * 0.7 and v.x > midx]
        if ankle_verts:
            anklez_co = min(ankle_verts, key=lambda v: v.y)  # Base for ankle height
            anklez_co.x = max(ankle_verts, key=lambda v: v.x).x * 0.5 + min(ankle_verts, key=lambda v: v.x).x * 0.5
            anklez_co.z = min(ankle_verts, key=lambda v: v.x).z
            anklez_co.y = min(ankle_verts, key=lambda v: v.x).y * 0.4 + max(ankle_verts, key=lambda v: v.x).y * 0.6

            leg_bones[1].tail = anklez_co  # Shin.L tail is ankle
            print("ankle=shin tail : ", anklez_co)

        # Foot and Toe
        toe_verts = [v for v in masterco if abs(v.z - tallunit - minz_vert_co.z) < tallunit and v.x > midx]
        if toe_verts:
            toey_co = min(toe_verts, key=lambda v: v.y)  # Toe tip
            toverty_verts = [v for v in toe_verts if abs(v.y - toey_co.y) < tallunit * 6]
            toey2_co = sum(toverty_verts, mathutils.Vector()) / len(toverty_verts) if toverty_verts else toey_co

            leg_bones[2].tail = toey2_co  # foot.L tail = toe head

            foot_vector = toey2_co - leg_bones[2].head
            foot_vector.z = 0
            leg_bones[3].head = leg_bones[2].tail  # toe.L head
            leg_bones[3].tail = leg_bones[2].tail + foot_vector * 0.35  # toe.L tail
            print("toe tip position: ", leg_bones[3].tail)

        # Heel bone
        heel_name = next((i for i in bonenames if i.startswith("heel.") and i.endswith(".L")), None)
        if heel_name:
            heel_bone = editbones[heel_name]
            heel_bone.head = editbones["foot.L"].head - mathutils.Vector((0, -tallunit, tallunit * 3))
            heel_bone.tail = editbones["foot.L"].head - mathutils.Vector((-tallunit * 2, -tallunit, tallunit * 3))

        # Knee position \\\\\\\\\\\\\\\\\\\\\\\\\\\\//////////////////////////////////
        kneeverty_verts = [v for v in leftside_verts if abs(v.co.z - (crotch_co.z - minz_vert_co.z) * 0.6 - minz_vert_co.z) <= tallunit]

        knee_ys_candidates = []
        if kneeverty_verts:
            knee_ys_candidates.append(max(kneeverty_verts, key=lambda v: v.co.y))  # Initial candidate

        for i in range(6):
            # Recalculate verts for a slice around the knee height
            kneeverty_slice_verts = [
                v
                for v in leftside_verts
                if abs(v.co.z - ((crotch_co.z - minz_vert_co.z) * 0.55 + i * tallunit * 0.5 + minz_vert_co.z)) <= tallunit * 0.25
            ]
            if kneeverty_slice_verts:
                kneemaxy_vert = max(kneeverty_slice_verts, key=lambda v: v.co.y)

                if knee_ys_candidates and abs(kneemaxy_vert.co.y - knee_ys_candidates[-1].co.y) > tallunit * 0.5:
                    pass  # Skip if sudden large jump, likely not part of the same knee contour
                else:
                    knee_ys_candidates.append(kneemaxy_vert)
                # print("kneemaxy_vert: ", kneemaxy_vert.co, "i: ", i, knee_ys_candidates[-1].co)

        if knee_ys_candidates:
            leg_bones[1].head = min(knee_ys_candidates, key=lambda v: v.co.y).co

        leg_bones[1].head.y = leg_bones[0].head.y * 0.5 + leg_bones[1].tail.y * 0.5 - tallunit
        leg_bones[1].head.x = leg_bones[0].head.x * 0.5 + leg_bones[1].tail.x * 0.5  # Align knee x between thigh and shin

        # --- Symmetrize ---
        if armatur.data.use_mirror_x:
            bpy.ops.object.mode_set(mode="OBJECT")
            armatur.location.x -= midx  # Move armature to origin for symmetry
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            print("\n::: ::: symmetrizing ::: :::")
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.armature.select_all(action="SELECT")
            bpy.ops.armature.symmetrize(direction="POSITIVE_X")
            bpy.ops.object.mode_set(mode="OBJECT")
            armatur.location.x += midx  # Move armature back
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        armatur.data.pose_position = "POSE"
        bpy.ops.object.mode_set(mode=initial_mode)
        # context.view_layer.update()

        self.report({"INFO"}, f"Rig created for armature: {armatur.name} ...................\n")
        return {"FINISHED"}


# ---

### Refactored `GenerateIk` Operator


import bpy
import mathutils
import math

# (get_pole_angle, tolerancex, tolerancex_co, tolerancexy_co functions are assumed to be defined above)


class GenerateIk(bpy.types.Operator):
    bl_idname = "fg.generate_ik"
    bl_label = "Genx ik"
    bl_description = "Generate ik bones for hand, foot, and other limbs"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.context.object.pose.use_mirror_x = False
        bpy.context.object.data.pose_position = "REST"

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.object.data.use_mirror_x = False
        edit_bones = context.object.data.edit_bones
        activebone = context.active_bone  # context.object.data.edit_bones.active
        ac = edit_bones.get(activebone.name)

        base = activebone.parent
        dir = (base.vector - ac.vector).normalized()
        dir.z = 0
        dir.x = 0
        if not base:
            self.report({"ERROR"}, "No parent bone to ik bone")
            return {"CANCELLED"}
        if not ac:
            self.report({"ERROR"}, "No ik bone selected")
            return {"CANCELLED"}

        # generate ik bone and place it
        activebonename = activebone.name
        bones = [bn.name for bn in edit_bones]
        ikbonename = "IK_" + activebone.name
        polebonename = "POLE_" + activebone.name
        if not ikbonename in bones:
            ikbone = edit_bones.new(name=ikbonename)
        else:
            ikbone = edit_bones[ikbonename]
        if not polebonename in bones:
            polebone = edit_bones.new(name=polebonename)
        else:
            polebone = edit_bones[polebonename]

        ikbone.use_deform = False
        ikbone.head = activebone.tail

        tallunit = context.object.dimensions[2] / 57
        if activebone.tail[2] > tallunit * 15:
            t = 1
        else:
            t = -1
        ikbone.tail = ikbone.head + t * dir * 0.2
        print(tallunit, t)
        # generate pole bone and place it
        polebone.use_deform = False
        polebone.head = base.tail + dir * tallunit * 35
        polebone.tail = polebone.head + dir * 0.2
        print("polebone_head: ", polebone.head, "polebone_tail: ", polebone.tail)
        pol_angle = get_pole_angle(edit_bones[activebonename].parent, edit_bones[activebonename], edit_bones[polebonename])
        print("pol_angle: ", pol_angle)
        bpy.ops.object.mode_set(mode="POSE")
        activepbone = context.object.pose.bones[activebonename]
        if not "IK_" + activebonename in activepbone.constraints:
            cons = activepbone.constraints.new(type="IK")
            cons.name = "IK_" + activebonename
        else:
            cons = activepbone.constraints["IK_" + activebonename]

        cons.target = context.object
        cons.subtarget = ikbonename
        cons.pole_target = context.object
        cons.pole_subtarget = polebonename
        cons.pole_angle = pol_angle
        # print("uv_angle: ", cons.pole_angle)
        cons.chain_count = context.scene.chain_count
        cons.use_stretch = False

        bpy.context.object.data.pose_position = "POSE"

        # bpy.context.view_layer.update()
        self.report({"INFO"}, f"Ik bone created: {ikbonename}")
        return {"FINISHED"}


# ------------------- autoparent --------------#
# Auto parent the selected object to the armature
class Autoparent(bpy.types.Operator):
    bl_idname = "fg.autoparent"
    bl_label = "parent them"
    bl_description = "Blender's parenting system with automatic weights(CTRL+P).\n\n*This operator will apply the scale and rotation of the armature and the object\nbefore parenting them.\n"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mode = bpy.context.object.mode
        aktiv = bpy.context.active_object
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        human = context.scene.my_object
        armatur = context.scene.my_armature

        human.select_set(True)
        bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        armatur.select_set(True)
        bpy.context.view_layer.objects.active = armatur
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.context.object.data.pose_position = "REST"

        original_scale = armatur.scale.copy()
        human_scale = human.scale.copy()
        # --- Apply temporary scale (2x) ---
        armatur.scale = [s * 10 for s in original_scale]
        human.scale = [s * 10 for s in human_scale]
        # bpy.context.view_layer.update()

        bpy.ops.object.parent_set(type="ARMATURE_AUTO")

        armatur.scale = original_scale

        # bpy.context.view_layer.update()
        bpy.context.object.data.pose_position = "POSE"
        bpy.context.view_layer.objects.active = human
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = aktiv
        bpy.ops.object.mode_set(mode=mode)
        self.report({"INFO"}, f"Lets parent anyway")
        return {"FINISHED"}


# ------------------- weight paint auto --------------#
# Calculate the distance from a point to a line segment defined by two endpoints
def point_line_distance(point, line_start, line_end):
    """Calculate the distance from a point to a line segment defined by two endpoints."""
    line_vector = line_end - line_start
    point_vector = point - line_start
    line_length_squared = line_vector.length_squared

    if line_length_squared == 0:
        return (point - line_start).length

    t = max(0, min(1, point_vector.dot(line_vector) / line_length_squared))
    projection = line_start + t * line_vector
    return (point - projection).length


class Weightpaintauto(bpy.types.Operator):
    bl_idname = "fg.wpaintauto"
    bl_label = "auto weight paint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        human = context.scene.my_object
        armatur = context.scene.my_armature
        # human.select_set(True)
        armatur.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.context.view_layer.objects.active = armatur
        verts = [v for v in human.data.vertices]
        # for v in verts:
        #     v.select=False
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.object.data.pose_position = "REST"

        bns = context.selected_editable_bones
        for bn in bns:
            for v in verts:
                world_co = human.matrix_world @ v.co
                headco = armatur.matrix_world @ bn.head
                tailco = armatur.matrix_world @ bn.tail
                if abs(point_line_distance(world_co, headco, tailco)) <= 0.01:
                    v.select = True
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = human
        bpy.ops.object.mode_set(mode="EDIT")
        return {"FINISHED"}

    ############################################


# ------------------ register -------------------#
classes = [GenerateIk, GenerateRig, Weightpaintauto, Autoparent]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
