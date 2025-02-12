bl_info = {
    "name": "VRM-Spacing-Animation-Baking",
    "author": "ingenoire",
    "version": (2, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > VRM Bake",
    "description": "Adjusts spacing for VRM bones and provides animation baking tools.",
    "category": "Animation",
}

import bpy
import math
import mathutils

tracked_changes = {}
is_tracking = False  # Global flag to determine if we're recording

# List of bone pairs for dropdown menu
bone_pairs = [
    ("SHOULDER", "J_Bip_L_Shoulder", "J_Bip_R_Shoulder", "Shoulder", True),
    ("UPPER_ARM", "J_Bip_L_UpperArm", "J_Bip_R_UpperArm", "Upper Arm", True),
    ("LOWER_ARM", "J_Bip_L_LowerArm", "J_Bip_R_LowerArm", "Lower Arm", True),
    ("HANDS", "J_Bip_L_Hand", "J_Bip_R_Hand", "Hands", True),
    ("UPPER_LEG", "J_Bip_L_UpperLeg", "J_Bip_R_UpperLeg", "Upper Leg", True),
    ("LOWER_LEG", "J_Bip_L_LowerLeg", "J_Bip_R_LowerLeg", "Lower Leg", True),
    ("FEET", "J_Bip_L_Foot", "J_Bip_R_Foot", "Feet", True),
    ("TOES", "J_Bip_L_ToeBase", "J_Bip_R_ToeBase", "Tip of Feet / Toes", True),
    ("SPINE", "J_Bip_C_Spine", None, "Spine", False),
    ("CHEST", "J_Bip_C_Chest", None, "Chest", False),
    ("UPPER_CHEST", "J_Bip_C_UpperChest", None, "Upper Chest", False),
    ("NECK", "J_Bip_C_Neck", None, "Neck", False),
    ("HEAD", "J_Bip_C_Head", None, "Head", False)
]

# Add a toggle property for choosing spacing axis
bpy.types.Scene.spacing_axis = bpy.props.EnumProperty(
    name="Spacing Axis",
    description="Choose which axis to apply the spacing on",
    items=[
        ('SIDEWAYS', "Space Sideways (Z-Axis)", ""),
        ('FORWARD_BACKWARD', "Space Forward/Backward (Y-Axis)", ""),
        ('DEPTH', "Space Depth (X-Axis)", "")
    ],
    default='SIDEWAYS'
)

# Updated bone pair spacing function
def adjust_bone_pair_spacing(armature, bone_l_name, bone_r_name, space_value, affect_left, affect_right, axis):
    if not affect_left and not affect_right:
        return {'CANCELLED'}

    space_rad = math.radians(space_value)
    anim_data = armature.animation_data

    if anim_data is not None and anim_data.action is not None:
        for f in range(int(anim_data.action.frame_range[0]), int(anim_data.action.frame_range[1]) + 1):
            bpy.context.scene.frame_set(f)

            # Determine which axis to adjust
            if axis == 'SIDEWAYS':
                axis_index = 2  # Z-axis
            elif axis == 'FORWARD_BACKWARD':
                axis_index = 1  # Y-axis
            else:  # DEPTH - X-axis
                axis_index = 0

            if affect_left and bone_l_name in armature.pose.bones:
                bone_l = armature.pose.bones[bone_l_name]
                fcurve = anim_data.action.fcurves.find(data_path=f"pose.bones[\"{bone_l_name}\"].rotation_euler", index=axis_index)
                if fcurve and any(kp.co[0] == f for kp in fcurve.keyframe_points):
                    bone_l.rotation_euler[axis_index] += space_rad
                    bone_l.keyframe_insert(data_path="rotation_euler", index=axis_index)

            if affect_right and bone_r_name and bone_r_name in armature.pose.bones:
                bone_r = armature.pose.bones[bone_r_name]
                fcurve = anim_data.action.fcurves.find(data_path=f"pose.bones[\"{bone_r_name}\"].rotation_euler", index=axis_index)
                if fcurve and any(kp.co[0] == f for kp in fcurve.keyframe_points):
                    bone_r.rotation_euler[axis_index] -= space_rad
                    bone_r.keyframe_insert(data_path="rotation_euler", index=axis_index)

    return {'FINISHED'}

# Update the operator to include the axis parameter
class SpacingAdjusterOperator(bpy.types.Operator):
    bl_idname = "object.adjust_spacing"
    bl_label = "Adjust Spacing"
    bl_description = "Adjusts the spacing of the selected bones according to the value chosen above."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = context.object
        bone_pair_key = context.scene.selected_bone_pair
        space_value = context.scene.space_value_prop
        affect_left = context.scene.affect_left_prop
        affect_right = context.scene.affect_right_prop
        spacing_axis = context.scene.spacing_axis

        if not affect_left and not affect_right:
            self.report({'WARNING'}, "You must select at least one bone (Left or Right) to adjust.")
            return {'CANCELLED'}

        bone_pair = next((bp for bp in bone_pairs if bp[0] == bone_pair_key), None)
        if bone_pair:
            bone_l_name, bone_r_name = bone_pair[1], bone_pair[2]
            if bone_r_name is None:
                affect_right = False  # Ensure right bone isn't processed if None
            result = adjust_bone_pair_spacing(armature, bone_l_name, bone_r_name, space_value, affect_left, affect_right, spacing_axis)
            if result != {'FINISHED'}:
                return result
        else:
            self.report({'ERROR'}, "Invalid bone pair selected.")
            return {'CANCELLED'}

        return {'FINISHED'}

# ----------------------------- Animation Helper Functions -----------------------------

# Operator to select physics bones
class SelectPhysicsBonesOperator(bpy.types.Operator):
    bl_idname = "object.select_physics_bones"
    bl_label = "Select Physics Bones"
    bl_description = "This selects all the possible physics bones that could exist on your VRM model."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = context.object

        # Ensure we are in Pose Mode
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        # Deselect all bones first
        bpy.ops.pose.select_all(action='DESELECT')

        # List of patterns for bone names
        patterns = ["Hair", "Bust", "Skirt", "Sleeve", "Ear", "Tail"]

        # Iterate over all bones and select those matching the patterns
        for bone in armature.pose.bones:
            bone_name = bone.name
            if any(pattern in bone_name for pattern in patterns):
                bone.bone.select = True  # Select matching bones

        return {'FINISHED'}



# Operator to delete highlighted bones from animation
class DeleteHighlightedBonesOperator(bpy.types.Operator):
    bl_idname = "object.delete_highlighted_bones"
    bl_label = "Delete Highlighted Bones from Animation"
    bl_description = "This removes the physics bones from the current animation, which is often the case when retargeting animations to the VRM model."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = context.object
        anim_data = armature.animation_data

        if bpy.context.mode != 'POSE':
            self.report({'WARNING'}, "You must be in Pose Mode.")
            return {'CANCELLED'}

        if not armature.pose.bones:
            self.report({'WARNING'}, "No bones selected.")
            return {'CANCELLED'}

        if anim_data is None or anim_data.action is None:
            self.report({'WARNING'}, "No animation data found.")
            return {'CANCELLED'}

        selected_bones = [bone.name for bone in armature.pose.bones if bone.bone.select]

        if not selected_bones:
            self.report({'WARNING'}, "No bones selected.")
            return {'CANCELLED'}

        # Loop through selected bones and remove keyframes for all transformations
        for bone_name in selected_bones:
            fcurves = [fc for fc in anim_data.action.fcurves if fc.data_path.startswith(f'pose.bones["{bone_name}"]')]
            for fcurve in fcurves:
                anim_data.action.fcurves.remove(fcurve)

        return {'FINISHED'}


# Operator to toggle VRM Spring Bone Physics
class ToggleVRMSpringBonePhysicsOperator(bpy.types.Operator):
    bl_idname = "object.toggle_vrm_spring_bone_physics"
    bl_label = "Enable/Disable VRM Spring Bone Physics"
    bl_description = "Enable VRM Spring Bone Physics for baking; disable before creating looping animations."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Locate the Armature in the scene
        armature = None
        for obj in bpy.context.scene.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if armature is None:
            self.report({'ERROR'}, "No Armature object found in the scene.")
            return {'CANCELLED'}
        
        # Set the Armature as the active object and select it
        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        
        # Access the VRM Spring Bone settings
        try:
            # Toggle the spring bone physics status
            vrm_module = armature.data.vrm_addon_extension  # Placeholder for actual VRM property path
            enabled = not getattr(vrm_module.spring_bone1, 'enable_animation', False)
            vrm_module.spring_bone1.enable_animation = enabled
            
            # Update the scene property to reflect the toggle status
            context.scene.vrm_spring_bone_physics_enabled = enabled

            status = "enabled" if enabled else "disabled"
            self.report({'INFO'}, f"VRM Spring Bone Physics {status}.")

        except AttributeError:
            self.report({'ERROR'}, "VRM Spring Bone system not available.")
            return {'CANCELLED'}

        return {'FINISHED'}

    
class AdjustPlaybackAndBakeOperator(bpy.types.Operator):
    bl_idname = "object.adjust_playback_and_bake"
    bl_label = "Adjust Playback Range and Bake Animation"
    bl_description = "Bakes the hair physics into the animation and also changes the playback range of the scene to that of the animation. If you don't need a looping animation, this is the final step."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        armature = context.object

        # Ensure we're in Object Mode
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get the action
        anim_data = armature.animation_data
        if anim_data is None or anim_data.action is None:
            self.report({'ERROR'}, "No animation data found.")
            return {'CANCELLED'}

        action = anim_data.action

        # Adjust playback range's final frame to match the final frame of the current action
        final_frame = int(action.frame_range[1])
        scene.frame_end = final_frame

        # Bake Animation
        bpy.ops.object.mode_set(mode='POSE')  # Switch to Pose Mode
        bpy.ops.nla.bake(
            frame_start=1,
            frame_end=final_frame,
            bake_types={'POSE'},
            visual_keying=True,
            clear_constraints=False,
            use_current_action=True,
            only_selected=False
        )
        bpy.ops.object.mode_set(mode='OBJECT')  # Switch back to Object Mode

        self.report({'INFO'}, f"Playback range adjusted to frame {final_frame} and animation baked.")
        return {'FINISHED'}
    
# ----------------------------- Loopify Physics Operator -----------------------------
class LoopifyPhysicsOperator(bpy.types.Operator):
    bl_idname = "object.loopify_physics"
    bl_label = "Loopify Physics"
    bl_description = "Deletes the front or back of the animation's physics and inserts the opposite side's last or first frame of physics bones, making the animation loop seamlessly. The more frame easing there is, the more frames are deleted, at the cost of less precise physics for a longer portion of the animation. This is the final step for looping animations."
    bl_options = {'REGISTER', 'UNDO'}

    # Use the frame easing defined in the scene properties
    def execute(self, context):
        armature = context.object

        # Ensure we are in Pose Mode
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        # Get the action
        anim_data = armature.animation_data
        if anim_data is None or anim_data.action is None:
            self.report({'ERROR'}, "No animation data found.")
            return {'CANCELLED'}

        action = anim_data.action
        frame_range = action.frame_range
        start_frame = int(frame_range[0])
        end_frame = int(frame_range[1])

        # Get user input for frame selection and easing value from context
        frame_selection = context.scene.frame_selection
        frame_easing = context.scene.loopify_frame_easing  # Correctly fetching frame easing from the scene property

        # Determine the copy frame and delete frame range based on user selection
        if frame_selection == 'LAST_FRAME':
            copy_frame = end_frame
            delete_range_start = start_frame
            delete_range_end = start_frame + frame_easing - 1
            paste_frame = 0
        else:  # 'FIRST_FRAME'
            copy_frame = start_frame
            delete_range_start = end_frame - frame_easing + 1
            delete_range_end = end_frame
            paste_frame = end_frame + 1

        # Log debug information
        print(f"Action Frame Range: {start_frame} to {end_frame}")
        print(f"Frame Selection: {frame_selection}")
        print(f"Frame Easing: {frame_easing}")
        print(f"Copy Frame: {copy_frame}")
        print(f"Delete Range: {delete_range_start} to {delete_range_end}")
        print(f"Paste Frame: {paste_frame}")

        # Get selected bones
        selected_bones = [bone.name for bone in armature.pose.bones if bone.bone.select]
        if not selected_bones:
            self.report({'ERROR'}, "No bones selected.")
            return {'CANCELLED'}
        print(f"Selected Bones: {selected_bones}")

        # Helper function to get F-Curves for selected bones
        def get_selected_bone_fcurves():
            fcurves = []
            for fcurve in action.fcurves:
                if any(bone_name in fcurve.data_path for bone_name in selected_bones):
                    fcurves.append(fcurve)
            return fcurves

        fcurves = get_selected_bone_fcurves()

        # Collect keyframe data to copy
        keyframe_data = {}
        for fcurve in fcurves:
            keyframe_data[fcurve] = {}
            for keyframe in fcurve.keyframe_points:
                if keyframe.co[0] == copy_frame:
                    keyframe_data[fcurve][keyframe.co[0]] = keyframe.co[1]

        # Delete keyframes within the delete range
        for fcurve in fcurves:
            for frame in range(delete_range_start, delete_range_end + 1):
                keyframes_to_remove = [kf for kf in fcurve.keyframe_points if kf.co[0] == frame]
                for keyframe in keyframes_to_remove:
                    fcurve.keyframe_points.remove(keyframe)

        # Insert keyframes at the paste position
        for fcurve in fcurves:
            for frame, value in keyframe_data[fcurve].items():
                fcurve.keyframe_points.insert(paste_frame, value, options={'FAST'})

        # Re-delete the original delete range to clear any additional frames
        for fcurve in fcurves:
            for frame in range(delete_range_start, delete_range_end + 1):
                keyframes_to_remove = [kf for kf in fcurve.keyframe_points if kf.co[0] == frame]
                for keyframe in keyframes_to_remove:
                    fcurve.keyframe_points.remove(keyframe)

        return {'FINISHED'}

# ----------------------- Track Pose Changes -----------------------

def track_pose_changes(scene):
    """Tracks changes in Pose Mode for selected bones only when recording is active."""
    global tracked_changes, is_tracking

    if not is_tracking:
        return  # Stop tracking if not in recording mode

    armature = bpy.context.object
    if not armature or armature.type != 'ARMATURE':
        return

    try:
        for bone in armature.pose.bones:
            if not bone.bone.select:  # Only track selected bones
                continue

            bone_name = bone.name

            # Initialize tracking for the selected bone
            if bone_name not in tracked_changes:
                tracked_changes[bone_name] = {
                    "original_location": bone.location.copy(),
                    "original_rotation": bone.rotation_quaternion.copy() if bone.rotation_mode == 'QUATERNION' else bone.rotation_euler.to_quaternion(),
                    "original_scale": bone.scale.copy(),
                    "delta_location": mathutils.Vector((0, 0, 0)),
                    "delta_rotation": mathutils.Quaternion((1, 0, 0, 0)),  # Identity quaternion
                    "delta_scale": mathutils.Vector((0, 0, 0)),
                    "has_changes": False  # Flag to check if bone has changed
                }
                continue  # Skip computing deltas on the first frame

            # Compute deltas (change from original pose)
            original = tracked_changes[bone_name]

            delta_loc = bone.location - original["original_location"]
            
            # Convert Euler to Quaternion if needed
            current_rot = bone.rotation_quaternion if bone.rotation_mode == 'QUATERNION' else bone.rotation_euler.to_quaternion()
            # Invert the delta rotation to fix flipping
            delta_rot = current_rot.rotation_difference(original["original_rotation"]).inverted()

            delta_scale = bone.scale - original["original_scale"]

            # Store deltas only if there is meaningful change
            if delta_loc.length > 0.0001 or delta_rot.angle > 0.0001 or delta_scale.length > 0.0001:
                tracked_changes[bone_name]["delta_location"] = delta_loc
                tracked_changes[bone_name]["delta_rotation"] = delta_rot
                tracked_changes[bone_name]["delta_scale"] = delta_scale
                tracked_changes[bone_name]["has_changes"] = True

    except Exception as e:
        print(f"Error in pose tracking: {e}")


# ----------------------- Start Tracking -----------------------

class StartListeningOperator(bpy.types.Operator):
    """Starts tracking pose transformations for selected bones"""
    bl_idname = "pose.start_listening"
    bl_label = "Start Tracking Pose Changes"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global tracked_changes, is_tracking

        if bpy.context.object and bpy.context.object.type == 'ARMATURE':
            if bpy.context.mode != 'POSE':
                bpy.ops.object.mode_set(mode='POSE')
        else:
            self.report({'ERROR'}, "No active armature found.")
            return {'CANCELLED'}

        tracked_changes = {}  # Clear previous tracking
        is_tracking = True  # Activate tracking

        if track_pose_changes not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(track_pose_changes)

        context.scene.is_tracking_pose_changes = True
        self.report({'INFO'}, "Started tracking pose changes.")
        return {'FINISHED'}


class CancelTrackingOperator(bpy.types.Operator):
    """Cancels pose tracking and clears recorded changes"""
    bl_idname = "pose.cancel_tracking"
    bl_label = "Cancel Tracking"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global tracked_changes, is_tracking

        is_tracking = False
        tracked_changes.clear()  # Clear recorded data

        if track_pose_changes in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(track_pose_changes)

        context.scene.is_tracking_pose_changes = False
        self.report({'INFO'}, "Tracking canceled.")
        return {'FINISHED'}




# ----------------------- Apply Tracked Changes -----------------------

class ApplyTrackedChangesOperator(bpy.types.Operator):
    """Applies the recorded transformations to selected keyframes for selected bones."""
    bl_idname = "pose.apply_tracked_changes"
    bl_label = "Apply Tracked Changes"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        # Show popup message to guide the user
        self.report(
            {'INFO'},
            "Please select a range of frames in the timeline, adjust the necessary bones "
            "(translation, rotation, scaling), and then apply the changes."
        )
        return self.execute(context)

    def execute(self, context):
        global tracked_changes, is_tracking
        armature = bpy.context.object

        if not tracked_changes:
            self.report({'WARNING'}, "No changes tracked.")
            return {'CANCELLED'}

        if not armature or armature.type != 'ARMATURE' or not armature.animation_data or not armature.animation_data.action:
            self.report({'ERROR'}, "No active armature or animation data found.")
            return {'CANCELLED'}

        action = armature.animation_data.action
        selected_keyframes = get_selected_keyframes(action)

        if not selected_keyframes:
            self.report({'WARNING'}, "No keyframes selected.")
            return {'CANCELLED'}

        try:
            for frame in selected_keyframes:
                bpy.context.scene.frame_set(frame)  # Set the current frame

                for bone_name, changes in tracked_changes.items():
                    if not changes["has_changes"]:  # Skip unchanged bones
                        continue

                    if bone_name in armature.pose.bones:
                        bone = armature.pose.bones[bone_name]

                        # Apply stored deltas to the current bone state at the keyframe
                        bone.location += changes["delta_location"]
                        bone.keyframe_insert(data_path="location", frame=frame)

                        if bone.rotation_mode == 'QUATERNION':
                            bone.rotation_quaternion = bone.rotation_quaternion @ changes["delta_rotation"]
                            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                        else:
                            current_quat = bone.rotation_euler.to_quaternion()
                            new_quat = current_quat @ changes["delta_rotation"]
                            bone.rotation_euler = new_quat.to_euler(bone.rotation_mode)
                            bone.keyframe_insert(data_path="rotation_euler", frame=frame)

                        bone.scale += changes["delta_scale"]
                        bone.keyframe_insert(data_path="scale", frame=frame)

            # Rebake keyframes for proper interpolation
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='POSE')

        except Exception as e:
            print(f"Error applying tracked changes: {e}")

        # Clear tracked changes after applying
        tracked_changes.clear()
        is_tracking = False
        context.scene.is_tracking_pose_changes = False

        if track_pose_changes in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(track_pose_changes)

        self.report({'INFO'}, "Applied changes to selected keyframes.")
        return {'FINISHED'}



# ----------------------- Utility Function -----------------------

def get_selected_keyframes(action):
    """Returns a sorted list of selected keyframes"""
    selected_frames = set()
    for fcurve in action.fcurves:
        for keyframe in fcurve.keyframe_points:
            if keyframe.select_control_point:
                selected_frames.add(int(keyframe.co.x))
    return sorted(selected_frames)




class SpacingPanel(bpy.types.Panel):
    bl_label = "VRM Space Anime Baking"
    bl_idname = "OBJECT_PT_spacing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VRM Space Anime Baking'

    def draw(self, context):
        layout = self.layout

        # ------------------- Spacing Section -------------------
        layout.label(text="Bone Spacing Adjuster", icon='ARMATURE_DATA')

        row = layout.row(align=True)
        row.prop(context.scene, 'selected_bone_pair', text="Bone Pair")
        row = layout.row(align=True)
        row.prop(context.scene, 'affect_left_prop', text="Affect Left", icon='TRIA_LEFT')
        row.prop(context.scene, 'affect_right_prop', text="Affect Right", icon='TRIA_RIGHT')

        layout.prop(context.scene, 'space_value_prop', text="Spacing Value", icon='ARROW_LEFTRIGHT')

        # Add the new axis toggle
        layout.prop(context.scene, 'spacing_axis', text="Spacing Axis")

        layout.operator("object.adjust_spacing", text="Adjust Spacing", icon='MODIFIER')

        layout.separator(factor=0.5)
        
        is_tracking = context.scene.is_tracking_pose_changes

        layout.label(text="Track & Apply Pose Changes", icon='ARMATURE_DATA')

        if not is_tracking:
            layout.operator("pose.start_listening", text="Start Tracking", icon='TRACKING')
        else:
            layout.operator("pose.cancel_tracking", text="Cancel Tracking", icon='CANCEL')
            layout.label(text="Tracking in Progress...", icon='TIME')
            # Show "Apply Changes" button only when tracking is active
            layout.operator("pose.apply_tracked_changes", text="Apply Changes", icon='KEY_HLT')

        # ------------------- Animation Helper Section -------------------
        layout.label(text="Animation Helper", icon='ANIM')

        row = layout.row(align=True)
        row.operator("object.select_physics_bones", text="Select Physics Bones", icon='BONE_DATA')
        row.operator("object.delete_highlighted_bones", text="Delete Highlighted Bones", icon='TRASH')

        # Toggle button for VRM spring bone physics with status indicator
        layout.separator(factor=0.5)
        is_enabled = context.scene.vrm_spring_bone_physics_enabled
        icon = 'CHECKBOX_HLT' if is_enabled else 'CHECKBOX_DEHLT'
        status_text = "VRM Spring Bone Physics ON" if is_enabled else "VRM Spring Bone Physics OFF"
        layout.operator("object.toggle_vrm_spring_bone_physics", text=status_text, icon=icon)

        layout.separator(factor=0.5)

        # Adjust Playback and Bake
        layout.operator("object.adjust_playback_and_bake", text="Adjust Playback & Bake", icon='RENDER_ANIMATION')

        # Loopify Physics
        layout.separator(factor=0.5)
        layout.prop(context.scene, "frame_selection", text="Frame Selection", icon='TIME')
        layout.prop(context.scene, "loopify_frame_easing", text="Frame Easing", icon='IPO_ELASTIC')
        layout.operator("object.loopify_physics", text="Loopify Physics", icon='CON_FOLLOWPATH')

# ----------------------------- Register/Unregister Functions -----------------------------

def register():
    bpy.utils.register_class(SpacingAdjusterOperator)
    bpy.utils.register_class(SelectPhysicsBonesOperator)
    bpy.utils.register_class(DeleteHighlightedBonesOperator)
    bpy.utils.register_class(SpacingPanel)
    bpy.utils.register_class(AdjustPlaybackAndBakeOperator)
    bpy.utils.register_class(ToggleVRMSpringBonePhysicsOperator)
    bpy.utils.register_class(LoopifyPhysicsOperator)
    
    bpy.utils.register_class(StartListeningOperator)
    bpy.utils.register_class(CancelTrackingOperator)
    bpy.utils.register_class(ApplyTrackedChangesOperator)

    bpy.types.Scene.is_tracking_pose_changes = bpy.props.BoolProperty(
        name="Is Tracking Pose Changes",
        description="Indicates if pose tracking is active",
        default=False
    )

    bpy.types.Scene.selected_bone_pair = bpy.props.EnumProperty(
        name="Bone Pair",
        description="Select the bone pair to adjust",
        items=[(bp[0], bp[3], "") for bp in bone_pairs],
        default='SHOULDER'
    )

    bpy.types.Scene.affect_left_prop = bpy.props.BoolProperty(
        name="Affect Left",
        description="Affect the left bone",
        default=True
    )
    bpy.types.Scene.affect_right_prop = bpy.props.BoolProperty(
        name="Affect Right",
        description="Affect the right bone",
        default=True
    )
    bpy.types.Scene.space_value_prop = bpy.props.FloatProperty(
        name="Spacing Value",
        description="Spacing value in degrees",
        default=5.0,
        min=-20.0,
        max=20.0
    )
    bpy.types.Scene.spacing_axis = bpy.props.EnumProperty(
        name="Spacing Axis",
        description="Choose which axis to apply the spacing on",
        items=[
            ('SIDEWAYS', "Space Sideways (Z-Axis)", ""),
            ('FORWARD_BACKWARD', "Space Forward/Backward (Y-Axis)", ""),
            ('DEPTH', "Space Depth (X-Axis)", "")
        ],
        default='SIDEWAYS'
    )

    bpy.types.Scene.frame_selection = bpy.props.EnumProperty(
        name="Frame Selection",
        description="Choose the frame to base the loop from",
        items=[('LAST_FRAME', "Last Frame (Recommended)", ""),
               ('FIRST_FRAME', "First Frame", "")],
        default='LAST_FRAME'
    )

    bpy.types.Scene.loopify_frame_easing = bpy.props.IntProperty(
        name="Frame Easing from Loop",
        description="Number of frames to ease out physics when looping",
        default=4
    )

    bpy.types.Scene.vrm_spring_bone_physics_enabled = bpy.props.BoolProperty(
        name="VRM Spring Bone Physics",
        description="Toggle VRM Spring Bone Physics ON/OFF",
        default=False
    )


def unregister():
    bpy.utils.unregister_class(SpacingAdjusterOperator)
    bpy.utils.unregister_class(SelectPhysicsBonesOperator)
    bpy.utils.unregister_class(DeleteHighlightedBonesOperator)
    bpy.utils.unregister_class(SpacingPanel)
    bpy.utils.unregister_class(AdjustPlaybackAndBakeOperator)
    bpy.utils.unregister_class(ToggleVRMSpringBonePhysicsOperator)
    bpy.utils.unregister_class(LoopifyPhysicsOperator)
    
    bpy.utils.unregister_class(StartListeningOperator)
    bpy.utils.unregister_class(CancelTrackingOperator)
    bpy.utils.unregister_class(ApplyTrackedChangesOperator)

    del bpy.types.Scene.is_tracking_pose_changes

    del bpy.types.Scene.selected_bone_pair
    del bpy.types.Scene.affect_left_prop
    del bpy.types.Scene.affect_right_prop
    del bpy.types.Scene.space_value_prop
    del bpy.types.Scene.spacing_axis
    del bpy.types.Scene.frame_selection
    del bpy.types.Scene.loopify_frame_easing
    del bpy.types.Scene.vrm_spring_bone_physics_enabled


if __name__ == "__main__":
    register()
