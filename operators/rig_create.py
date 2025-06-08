import bpy, bmesh
import mathutils
import math


# ------------------- get_pole_angle --------------#
# This function calculates the pole angle for the IK constraint


# The pole angle is the angle between the base bone's x-axis and the projected pole axis on the base bone's plane
def get_pole_angle(base, middle, pole):
    def get_signed_angle(vector_u, vector_v, normal):

        uv_angle = vector_u.angle(vector_v)

        if vector_u.cross(vector_v) == mathutils.Vector((0, 0, 0)):
            return uv_angle

        if vector_u.cross(vector_v).angle(normal) < 1:
            return -uv_angle

        return uv_angle

    pole_location = pole.head

    pole_normal = (middle.tail - base.head).cross(pole_location - base.head)
    projected_pole_axis = pole_normal.cross(base.vector)

    pole_angle = get_signed_angle(base.x_axis, projected_pole_axis, base.vector)

    return pole_angle


def tolerancex(source, target, axis1, tol):
    return [v for v in source if abs(v[axis1] - target[axis1]) < tol]


def tolerancex_co(source, target, axis1, tol):
    return [v for v in source if abs(v.co[axis1] - target[axis1]) < tol]


def tolerancexy_co(source, target, axis1, axis2, tol, tol2):
    return [v for v in source if abs(v.co[axis1] - target[axis1]) < tol and abs(v.co[axis2] - target[axis2]) < tol2]


# ------------------- generate rig  level 1         --------------#
# Generate rig bones position
# This operator generates the rig bones position based on the selected object and armature
class GenerateRig(bpy.types.Operator):
    bl_idname = "fg.generate_rig"
    bl_label = "Orient rig bones position"
    bl_description = "Generate rig bones position"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        print("\n\n\n*********************************** generating rig*********************************\n")
        mode = context.object.mode
        # if mode != "OBJECT" or mode != "EDIT" or mode != "POSE":
        #     mode = "OBJECT"

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        if not hasattr(context.scene, "my_object") or context.scene.my_object is None:
            self.report({"ERROR"}, "No object set in the scene")
            return {"CANCELLED"}
        if not hasattr(context.scene, "my_armature") or not context.scene.my_armature:
            self.report({"ERROR"}, "No armature set in the scene")
            return {"CANCELLED"}
        # 1. Human
        human = context.scene.my_object
        human.select_set(True)  # human.select
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if human.parent:
            human.parent.select_set(True)
            bpy.context.view_layer.objects.active = human
            bpy.ops.object.parent_clear(type="CLEAR")

        # bpy.context.view_layer.objects.active = human
        # 2. Dimensions of human
        tall = human.dimensions[2]
        tallunit = human.dimensions[2] / 57
        width = human.dimensions[0] / 2
        deep = human.dimensions[1]
        # center = tallunit * 28.5
        armlocz = tallunit * 47
        # 3. Axis vectors
        x_axis = mathutils.Vector((1, 0, 0))
        y_axis = mathutils.Vector((0, 1, 0))
        z_axis = mathutils.Vector((0, 0, 1))

        matrixworld = human.matrix_world
        masterco = [matrixworld @ v.co for v in human.data.vertices]
        orjin_median = sum(masterco, mathutils.Vector()) / len(masterco)

        maxx = max(masterco, key=lambda v: v.x)
        minx = min(masterco, key=lambda v: v.x)
        midx = (maxx.x + minx.x) / 2
        print("midx:", midx, "   tallunit:", tallunit, "\norjin_median: ", orjin_median)

        # human.location.x -= midx
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        mid_vers = [v for v in masterco if abs(v.x - midx) < tallunit * 2]
        leftside_vers = [v for v in human.data.vertices if v.co.x >= midx]

        maxz = max(mid_vers, key=lambda v: v.z)
        minz = min(masterco, key=lambda v: v.z)

        hair = [v.co for v in human.data.vertices if v.co.z >= maxz.z - tallunit * 2]
        headmid = sum(hair, mathutils.Vector()) / len(hair)
        uppest = maxz * 0.5 + headmid * 0.5 + mathutils.Vector((0, 0, tallunit * 0.6))

        hit, crotch, nor, idx = human.ray_cast(mathutils.Vector((midx, uppest.y, tallunit * 15)), z_axis)
        center = crotch.z + tallunit * 1.5
        print("\ncrotch: ", crotch, "\nuppest: ", uppest, "minz: ", minz)
        lower = [v for v in human.data.vertices if abs(v.co.z - crotch.z) < tallunit * 2]
        maxlower = max(lower, key=lambda v: v.co.x).co
        minlower = min(lower, key=lambda v: v.co.x).co
        print("maxlower: ", maxlower, "minlower: ", minlower)
        crotch2 = maxlower * 0.5 + minlower * 0.5

        butts = [v for v in leftside_vers if abs(v.co.z - center) < tallunit * 3]
        butty = max(butts, key=lambda v: v.co.y)
        butty.co.x = min(tallunit * 1.5 + midx, butty.co.x)

        forearmverts = [v for v in leftside_vers if v.co.x > width * 0.5 + midx and v.co.x < width * 0.9 + midx]
        print(f"center: {center:0.4f}", "crotch: ", crotch)

        # 4. Armature
        armatur = context.scene.my_armature
        armatur.select_set(True)  # armatur.select
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.context.view_layer.objects.active = armatur
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.object.data.pose_position = "REST"
        editbones = armatur.data.edit_bones
        bonenames = [bn.name for bn in editbones]

        # \\\\\\\\\\\\\\\\\\\\\\\\\\                 //////////////////////
        #  |||||||||||||||||||||||||     SPİNES      |||||||||||||||||||||
        # //////////////////////////                 \\\\\\\\\\\\\\\\\\\\\\
        print("\n........................----------------------spine------------------------------........................")
        bones = ["spine", "spine.001", "spine.002", "spine.003", "spine.004", "spine.005", "spine.006"]
        lengths = [4, 3, 6, 6.5, 1.5, 2, 5.5]
        ypos = [0, 0, -0.3, 0, 1.2, 0.5, 0.08]
        ys = []
        i = 0
        bell = []
        tallunit2 = (maxz.z - center) / sum(lengths)
        for bn in bones:
            if not bn in bonenames:
                editbones.new(bn)
            editbones[bn].head.x = midx
            editbones[bn].tail.x = midx

            # editbones[bn].head.y = 0
            editbones[bn].roll = 0
            editbones[bn].use_deform = True
            if i != 0:
                editbones[bn].use_connect = True
                editbones[bones[i]].parent = editbones[bones[i - 1]]
            editbones[bn].head.z = center

            editbones[bn].color.palette = "THEME04"

            if i == 4:
                neck_fix = True
                while neck_fix:
                    neck = human.ray_cast(editbones[bn].head, x_axis)
                    print("neck: ", neck[1], editbones[bn].head)
                    if neck[0] and neck[1].x < tallunit * 2 + midx:
                        editbones[bn].head.z -= tallunit * 0.25
                        neck_fix = True
                        center = editbones[bn].head.z
                    else:
                        neck_fix = False
            if i == 5:
                chinfix = True
                while chinfix:
                    chin = human.ray_cast(editbones[bn].head, -y_axis)
                    # print("\nchin: ", chin[1].y, editbones[bn].head.z)
                    while chin[1].y != 0:
                        chin[1].y -= 0.001
                        chin = human.ray_cast(chin[1], -y_axis)
                        # print("chin2: ", chin[1].y, editbones[bn].head.z)
                        if chin[1].y < maxz.y - tallunit * 4:
                            editbones[bn].head.z -= tallunit * 0.25
                            chin = human.ray_cast(editbones[bn].head, -y_axis)
                            chinfix = True
                            center = editbones[bn].head.z
                            # print("chin333: ", chin[1].y, editbones[bn].head.z)
                        else:
                            chinfix = False

            center += lengths[i] * tallunit
            print("center: ", center, i)
            editbones[bn].tail.z = center
            editbones[bn].head.y = ypos[i] * tallunit + maxz.y
            editbones[bn].tail.y = ypos[i] * tallunit + maxz.y

            tol = editbones[bn].head
            have_hit = True
            while have_hit:
                hit, maxy, nor, idx = human.ray_cast(tol, y_axis)
                if hit:
                    maxyspine = maxy
                    have_hit = True
                    tol = maxy + y_axis * 0.001
                else:
                    have_hit = False
            y = 0
            tol = editbones[bn].head
            while not have_hit:
                hit, miny, nor, idx = human.ray_cast(tol, -y_axis)
                if hit:
                    minyspine = miny
                    have_hit = False
                    tol = miny + -y_axis * 0.001
                    y += 1
                    # print("hit min: ",y, miny[1],bn)
                if not hit or y >= 2:
                    have_hit = True

            editbones[bn].head.y = maxyspine.y * 0.55 + minyspine.y * 0.45

            ys.append(editbones[bn].head.y)
            editbones[bn].envelope_distance = editbones[bn].length / 4

            i += 1
            # end of for loop
        editbones[bones[-1]].tail.z = uppest.z
        editbones[bones[-1]].head.y = uppest.y * 0.5 + ys[-2] * 0.5

        # --------------- check bell ---------------
        for i in range(10):
            belly = human.ray_cast(editbones[bones[1]].head + mathutils.Vector((0, 0, i * tallunit * 0.5)), x_axis)
            if belly[0]:
                bell.append(belly[1])
        bellz = min(bell, key=lambda v: v.x)
        editbones[bones[2]].head.z = bellz.z

        if "breast.L" in bonenames:
            editbones["breast.L"].head.x = editbones[bones[2]].head.x + tallunit * 2
            editbones["breast.L"].tail.x = editbones[bones[2]].head.x + tallunit * 2.5
            editbones["breast.L"].head.z = editbones[bones[3]].head.z + tallunit
            editbones["breast.L"].tail.z = editbones[bones[3]].head.z + tallunit
            editbones["breast.L"].head.y = editbones[bones[3]].head.y + tallunit * 2
            editbones["breast.L"].tail.y = editbones[bones[3]].head.y - tallunit * 2
            editbones["breast.L"].envelope_distance = editbones["breast.L"].length / 8
            editbones["breast.L"].color.palette = "THEME04"
            editbones["breast.L"].use_deform = True
            editbones["breast.L"].use_connect = False
            editbones["breast.L"].parent = editbones[bones[3]]
            editbones["breast.L"].roll = 0
            breast = [
                v.co
                for v in leftside_vers
                if abs(v.co.x - editbones[bones[3]].head.x - tallunit * 4.5) < tallunit * 1.5
                and v.co.z > editbones[bones[1]].tail.z + tallunit * 4
                and v.co.z < editbones[bones[4]].tail.z
            ]
            if len(breast) > 0:
                breasty = min(breast, key=lambda v: v.y)
                editbones["breast.L"].tail = breasty
                editbones["breast.L"].head.x = breasty.x - tallunit2
                editbones["breast.L"].head.y = editbones["breast.L"].tail.y + tallunit * 4
                editbones["breast.L"].head.z = editbones["breast.L"].tail.z + tallunit * 2
            bpy.ops.armature.select_all(action="DESELECT")
            editbones["breast.L"].select = True
            bpy.ops.armature.calculate_roll(type="GLOBAL_POS_Z")
            editbones["breast.L"].select = False

        # dick detecting...........
        dick = [
            v.co
            for v in leftside_vers
            if abs(v.co.x - editbones[bones[0]].head.x) < tallunit * 2 and abs(v.co.z - editbones[bones[0]].head.z) < tallunit * 3
        ]
        dick_y = min(dick, key=lambda v: v.y)
        if dick_y.y < editbones[bones[3]].head.y - tallunit * 6:
            print("\n......dick detected.....\n", dick_y.y, breasty.y)
        # breast detecting..........
        breastdeep = [
            v.co
            for v in leftside_vers
            if abs(v.co.x - editbones[bones[3]].head.x) < tallunit * 0.5 and abs(v.co.z - editbones[bones[3]].head.z) < tallunit * 2
        ]

        if len(breastdeep) > 0:
            breastdeepy = min(breastdeep, key=lambda v: v.y)
            if breastdeepy.y - breasty.y > tallunit * 0.6:
                print("\n......breast detected.....\n", breastdeepy.y, breasty.y, editbones[bones[3]].head)
        else:
            print("\n......no breast detected.....\n", dick_y.y, breasty.y)

        # \\\\\\\\\\\\\\\\\\\\\\\\\\                 //////////////////////
        #  |||||||||||||||||||||||||      ARMS       |||||||||||||||||||||
        # //////////////////////////                 \\\\\\\\\\\\\\\\\\\\\\
        print("\n........................----------------------arms---------------------------------........................")
        armcheck = True
        if armcheck:
            j = 0
            armlen = [5.5, 8.5, 8, 3]
            arms = ["shoulder.L", "upper_arm.L", "forearm.L", "hand.L"]
            armbones = []
            maxhandx = max(leftside_vers, key=lambda v: v.co.x)
            armlocx = midx
            for arm in arms:

                if not arm in bonenames:
                    editbones.new(arm)
                # if j>0:
                #     editbones[arm].parent = editbones[arms[j-1]]
                #     # editbones[arm].use_connect =True
                editbones[arm].head.z = armlocz
                editbones[arm].tail.z = armlocz

                editbones[arm].head.x = armlocx
                armlocx += armlen[j] * tallunit
                editbones[arm].tail.x = armlocx

                j += 1
                armbones.append(editbones[arm])
                editbones[arm].color.palette = "THEME05"
                editbones[arm].envelope_distance = editbones[arm].length / 4

            # --------- finding hand tail ----------------------------------
            print("finding palm  : hand tail.....")
            armbones[3].tail = maxhandx.co  # avrg  # hand tail

            # --------- shoulder from armpit ----->  a-pose vs t-pose------
            if width < tallunit * 24:
                a_pose = True
                t_pose = False
            else:
                t_pose = True
                a_pose = False
            if a_pose:
                print("\n............a_pose ---> armpit detecting.....")
                allv = [v for v in leftside_vers if v.co.x > tallunit + midx]
                piit = []
                for i in range(64):
                    armarmpit = [v for v in allv if v.co.x > width * 0.8 - i * tallunit * 0.15 + midx]
                    maxarmpitz = max(armarmpit, key=lambda v: v.co.z)
                    minarmpitz = human.ray_cast(maxarmpitz.co + -x_axis * 0.001, -x_axis)
                    piit.append(minarmpitz[1])
                    # print("apose: ", i, maxarmpitz.co, piit[-1], len(armarmpit))
                    if minarmpitz[1][0] < midx and len(piit) > 1:
                        break
                    else:
                        minarmpitz2 = human.ray_cast(minarmpitz[1] + -x_axis * 0.001, -x_axis)
                zz = piit[-2] * 0.5 + minarmpitz2[1] * 0.5
                zz[2] -= tallunit

                minarmpitz3 = human.ray_cast(zz, z_axis)
                minarmpitz4 = human.ray_cast(minarmpitz3[1] + z_axis * 0.0001, z_axis)
                # print("armpitz: ", minarmpitz3[1], minarmpitz4[1])
                armpit = minarmpitz3[1] * 0.5 + minarmpitz4[1] * 0.5
                # print("armpit: ", armpit, piit[-2], minarmpitz2[1], zz)
            if t_pose:
                print("\n...t_pose ---> armpit detecting.....")
                allv = [v for v in leftside_vers if v.co.x > tallunit + midx and v.co.z < editbones[bones[5]].head.z]
                piit = set()
                for i in range(64):
                    armarmpit = [v for v in allv if v.co.x > width * 0.8 - i * tallunit / 2 + midx]
                    if len(armarmpit) < 1:
                        break
                    maxarmpitz = max(armarmpit, key=lambda v: v.co.z)
                    minarmpitz = human.ray_cast(maxarmpitz.co + -z_axis * 0.0001, -z_axis)
                    piit.add(minarmpitz[1].freeze())
                    # print("tpose: ", i, minarmpitz[1], len(armarmpit), maxarmpitz.co)
                    minarmpitz3 = human.ray_cast(minarmpitz[1] + -z_axis * 0.001, -z_axis)
                    piit.add(minarmpitz3[1].freeze())
                    if minarmpitz3[1][2] > tallunit * 20:
                        break
                    armpit = minarmpitz[1] * 0.5 + maxarmpitz.co * 0.5
                    armpit.x -= tallunit * 0.5
            if armpit:
                armbones[1].head = armpit
                armbones[0].tail = armbones[1].head
                armbones[0].head.x = midx + tallunit2
                armbones[0].tail.z += tallunit * 0.5
                armbones[0].tail.x -= tallunit * 0.5
                armbones[0].head.z = armbones[1].head.z + tallunit * 0.5
                armbones[0].head.y = armbones[1].head.y - tallunit * 2
                armbones[0].tail.y = armbones[1].head.y + tallunit * 0.25

            # ------------finger dif-------angle of arm by x----------------------

            shouldervector = maxhandx.co - armbones[0].tail
            # if a_pose:
            #     tallunit=shouldervector.length / 22
            #     print("tallunit: ", tallunit)
            anglex = shouldervector.angle(x_axis)
            print(f"\narm angle::: {anglex:.2f}, {math.degrees(anglex):.2f}, {math.cos(anglex):.2f}")  # angle

            print("...\na_pose ---> finger checking.....")
            fingertwist = [v for v in leftside_vers if v.co.x > width * 0.7 + midx]
            if len(fingertwist) > 0:
                fingerextend = max(fingertwist, key=lambda v: v.co.z)
                fingerdif = maxhandx.co.x - fingerextend.co.x
                print("fingerdif: ", fingerdif)
                if fingerdif < tallunit * 12 * math.cos(anglex):
                    fingerdown = tallunit * 8.4 * math.cos(anglex) - fingerdif
                    print("fingerdown: ", fingerdown)

            # chest bone fix z #####################################
            if editbones[bones[3]].head.z - armbones[0].head.z > -tallunit:
                editbones[bones[3]].head.z = armbones[0].head.z - tallunit * 2

            # ********* finding wrist from hand tail -----------------------
            handhead = [v.co for v in leftside_vers if abs(v.co.x - maxhandx.co.x + 6 * width / 28 - fingerdown) < tallunit]
            if len(handhead) > 0:
                armbones[3].head = sum(handhead, mathutils.Vector()) / len(handhead)
                handrayup = human.ray_cast(armbones[3].head, z_axis)
                handraydown = human.ray_cast(armbones[3].head, -z_axis)
                armbones[3].head = handrayup[1] * 0.5 + handraydown[1] * 0.5
                hand_rayfront = human.ray_cast(armbones[3].head, -y_axis)
                hand_rayback = human.ray_cast(armbones[3].head, y_axis)
                armbones[3].head = hand_rayfront[1] * 0.5 + hand_rayback[1] * 0.5
                armbones[3].head.y += tallunit * 0.25
                armbones[3].length -= 4 * width / 29

            # --------- finding elbow -------------------------------------

            elbowdown = (maxhandx.co.x - armbones[0].tail.x) * 0.4
            elbowdown += armbones[0].tail.x
            if a_pose:
                elbowdown += fingerdown
                print("fingerextend: ", fingerextend.co, "elbowdown: ", elbowdown)

            midelbow = armbones[0].tail * 0.45 + editbones["hand.L"].head * 0.55
            # print("midelbow: ", midelbow)
            elbowvert = [v.co for v in leftside_vers if abs(v.co.x - elbowdown) < tallunit and abs(v.co.z - midelbow.z) < tallunit * 4]
            if len(elbowvert) > 0:
                elbowzmax = max(elbowvert, key=lambda v: v.z)
                elbowzmin = min(elbowvert, key=lambda v: v.z)
                elbowz = elbowzmax * 0.5 + elbowzmin * 0.5
                elbowxmaax = max(elbowvert, key=lambda v: v.x)
                elbowxmin = min(elbowvert, key=lambda v: v.x)
                elbowz.x = elbowxmaax.x * 0.5 + elbowxmin.x * 0.5
                elbowz.y += tallunit * 0.5
                editbones["upper_arm.L"].tail = elbowz

            for arm in arms:
                bpy.ops.armature.select_all(action="DESELECT")
                editbones[arm].select = True
                bpy.ops.armature.calculate_roll(type="GLOBAL_POS_Z")

        # \\\\\\\\\\\\\\\\\\\\\\\\\\                 //////////////////////
        #  |||||||||||||||||||||||||      LEGS       |||||||||||||||||||||
        # //////////////////////////                 \\\\\\\\\\\\\\\\\\\\\\
        print("\n........................----------------------legs---------------------------------..........................")
        tallunit = human.dimensions[2] / 57
        legs = ["thigh.L", "shin.L", "foot.L", "toe.L"]
        legsh = []
        bpy.ops.armature.select_all(action="DESELECT")
        for i, leg in enumerate(legs):
            legsh.append(editbones[leg])
            if not leg in bonenames:
                editbones.new(leg)
            editbones[leg].select = True
            editbones[leg].color.palette = "THEME11"
            editbones[leg].envelope_distance = editbones[leg].length / 4
            if i < 2:
                bpy.ops.armature.calculate_roll(type="GLOBAL_POS_Y")
            else:
                bpy.ops.armature.calculate_roll(type="GLOBAL_NEG_Z")
            editbones[leg].select = False

        # ------------------------thigh------
        legsh[0].head.y = editbones["spine"].head.y
        legsh[0].head.x = butty.co.x + tallunit * 1.25
        legsh[0].head.z = butty.co.z + tallunit * 0.7

        # ----------------- pelvis-----
        if "pelvis.L" in bonenames:
            editbones["pelvis.L"].head = editbones[bones[0]].head
            editbones["pelvis.L"].tail = legsh[0].head
            editbones["pelvis.L"].tail.z = editbones[bones[1]].head.z
            editbones["pelvis.L"].tail.y -= tallunit
            bpy.ops.armature.select_all(action="DESELECT")
            editbones["pelvis.L"].select = True
            editbones["pelvis.L"].color.palette = "THEME14"
            bpy.ops.armature.calculate_roll(type="GLOBAL_POS_Y")
            bpy.ops.armature.select_all(action="DESELECT")

        # ----------------ankle to "foot"----------------
        anklevert = [v for v in masterco if abs(v.z - tallunit * 3.5 - minz.z) < tallunit * 0.7 and v.x > midx]
        anklez = min(anklevert, key=lambda v: v.y)  # ankle height position
        # print("anklez: ", anklez)
        # anklez.y = anklez.y + tallunit * 1.5  # ankle
        anklez.x = max(anklevert, key=lambda v: v.x).x * 0.5 + min(anklevert, key=lambda v: v.x).x * 0.5  # ankle x
        # print("anklez x: ", max(anklevert, key=lambda v: v.x))
        anklez.z = min(anklevert, key=lambda v: v.x).z  # ankle z
        anklez.y = min(anklevert, key=lambda v: v.x).y * 0.4 + max(anklevert, key=lambda v: v.x).y * 0.6  # ankle y
        # print("anklez z: ", min(anklevert, key=lambda v: v.x))
        legsh[1].tail = anklez
        print("ankle: ", anklez)

        # -----------------foot---toe----heel---------
        toevert = [v for v in masterco if abs(v.z - tallunit - minz.z) < tallunit and v.x > midx]
        toey = min(toevert, key=lambda v: v.y)  # toe tip
        toverty = [v for v in toevert if abs(v.y - toey.y) < tallunit * 6]  # toe head area
        toey2 = sum(toverty, mathutils.Vector()) / len(toverty)  # toe head center
        legsh[2].tail = toey2  # foot tail = toe head
        footvector = toey2 - legsh[2].head
        footvector.z = 0
        legsh[3].tail = legsh[2].tail + footvector * 0.35  # toe tail
        print("toe position: ", legsh[3].tail)
        heelname = [i for i in bonenames if i.startswith("heel.") and i.endswith(".L")]
        if len(heelname) > 0:
            editbones[heelname[0]].head = editbones["foot.L"].head - mathutils.Vector((0, -tallunit, tallunit * 3))
            editbones[heelname[0]].tail = editbones["foot.L"].head - mathutils.Vector((-tallunit * 2, -tallunit, tallunit * 3))

        # -----------------knee----------------
        kneeverty = [v for v in leftside_vers if abs(v.co.z - (crotch.z - minz.z) * 0.6) <= tallunit]
        kneeys = [max(kneeverty, key=lambda v: v.co.y)]  # knee y
        # print("\nknee ::: ", len(kneeverty), "kneeys: ", kneeys[0].co)
        for i in range(6):
            kneeverty = [v for v in leftside_vers if abs(v.co.z - (crotch.z - minz.z) * 0.55 + i * tallunit * 0.5 - minz.z) <= tallunit * 0.25]
            if len(kneeverty) > 0:
                # kneeys[-1].select = True
                kneemaxy = max(kneeverty, key=lambda v: v.co.y)
                # print("kneeverty: ", len(kneeverty), "kneemaxy: ", kneemaxy.co, "i: ", i, -(crotch.z - minz.z) * 0.65 + i * tallunit * 0.5 - minz.z)
                kneeys.append(kneemaxy)
                if len(kneeys) > 1 and abs(kneeys[-1].co.y - kneeys[-2].co.y) > tallunit * 0.5:
                    # print("knee pop up", kneeys[-1].co)
                    kneeys.pop()

        if len(kneeys) > 0:
            kneey = min(kneeys, key=lambda v: v.co.y)
            print("kneeys: ", len(kneeys), "kneey: ", kneey.co)
            kneeray = human.ray_cast(kneey.co + mathutils.Vector((0, -tallunit * 0.1, 0)), -y_axis)
            if kneeray[0]:
                legsh[1].head = kneeray[1] * 0.6 + kneey.co * 0.4

                print("------------knee: ", kneeray[1], kneey.co)

        legsh[1].head.x = legsh[0].head.x * 0.5 + legsh[1].tail.x * 0.5

        # \\\\\\\\\\\\\\\\\\\\\\\\\\                 //////////////////////
        #  |||||||||||||||||||||||||     Symetrize   |||||||||||||||||||||
        # //////////////////////////                 \\\\\\\\\\\\\\\\\\\\\\

        if armatur.data.use_mirror_x:
            bpy.ops.object.mode_set(mode="OBJECT")
            armatur.location.x -= midx
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            print("\n-------------------symmetrize--------------------")
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.armature.select_all(action="SELECT")
            bpy.ops.armature.symmetrize(direction="POSITIVE_X")
            bpy.ops.object.mode_set(mode="OBJECT")
            armatur.location.x += midx
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        bpy.context.object.data.pose_position = "POSE"
        bpy.ops.object.mode_set(mode=mode)
        context.view_layer.update()

        self.report({"INFO"}, f"Rig created for armature: {armatur.name} ...................\n")
        return {"FINISHED"}

        # \\\\\\\\\\\\\\\\\\\\\\\\\\                 //////////////////////
        #  |||||||||||||||||||||||||        END      |||||||||||||||||||||
        # //////////////////////////                 \\\\\\\\\\\\\\\\\\\\\\
        # *******************************************************************


# Generate ik bones for arm or leg
class GenerateIk(bpy.types.Operator):
    bl_idname = "fg.generate_ik"
    bl_label = "Genx ik"
    bl_description = "Generate ik bones for arm or leg"
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
        dir = (ac.vector - base.vector).normalized()
        # dir.z = 0
        # dir.x = 0
        if not base:
            self.report({"ERROR"}, "No parent bone to ik bone")
            return {"CANCELLED"}
        if not ac:
            self.report({"ERROR"}, "No ik bone selected")
            return {"CANCELLED"}

        # generate ik bone and place it
        activebonename = activebone.name
        bones = [bn.name for bn in edit_bones]
        ikbonename = "ik_" + activebone.name
        polebonename = "pole_" + activebone.name
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
        if activebone.tail[2] > 0.66:
            t = 1
        else:
            t = -1
        ikbone.tail = ikbone.head + t * dir * 0.1

        # generate pole bone and place it
        polebone.use_deform = False
        polebone.head = base.tail + dir * ac.length * -3
        polebone.tail = polebone.head + dir * 0.1
        pol_angle = get_pole_angle(edit_bones[activebonename].parent, edit_bones[activebonename], edit_bones[polebonename])

        bpy.ops.object.mode_set(mode="POSE")
        activepbone = context.object.pose.bones[activebonename]
        if not "ik_" + activebonename in activepbone.constraints:
            cons = activepbone.constraints.new(type="IK")
            cons.name = "ik_" + activebonename
        else:
            cons = activepbone.constraints["ik_" + activebonename]

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
