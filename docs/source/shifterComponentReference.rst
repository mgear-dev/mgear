.. _shifter-component-reference:

Shifter Component Reference
###########################

Shifter comes with over 40 components you can build your rig from. This section covers the functionality and settings of each one in detail.

Guide Settings
==============

Main Settings
=============

Settings shared by all components.

* **Name**: The base name of the component, all the parts of the component get renmaed.
* **Side**: Which side the component is on; Left, Right or Center
* **Component Index**: WIP
* **Connector**: WIP

Joint Connection Settings
-------------------------

* **Use Joint Index**: WIP
* **Parent Joint Index**: WIP

Channel Host Settings
---------------------

* **Host**: The guide that stores the extra attributes for this component, such as IK/FK blendering and more. This will generally be a control_01 component.

Custom Ctonrollers Group
------------------------

WIP

----------------------------------------------------------------------------------------------------------------

Shifter Components
==================

arm_2jnt_01
-----------

Two bone arm setup with:

* **IK/FK blending** for switching between animating with IK or FK
* **Roll** attribute that lets you adjust the elbow direction, without moving the pole vector
* **Twist joints** for better deformations around the shoulder and wrist joints
* **Armpit roll** to manually adjust the twist joints around the shoulder joint
* **Scale** of the entire arm
* **Stretching** so the arm can elongate when the IK control is too far away to reach, including a maximum stretch limit
* **Sliding** of the elbow, which elongates the upper arm while shortening the lower arm, or vice versa
* **Softness** to prevent popping when the IK arm is stretched out straight
* **Reverse** to make the arm bend in the opposite direction when using IK
* **Roundness** for rubber hose style animation
* **Volume** preservation during stretching
* **Elbow** controller for accurately positioning the elbow, for instance when a character is resting her elbows on a table
* **Space switchers** for the IK, Up Vector and Elbow controllers that controls which space they follow

This is the default arm comoponent used by the biped template rig.

Guide Positioning
+++++++++++++++++

WIP

Compoent Settings
+++++++++++++++++

TODO! Should this be tools tips in the interface itself.

* **IK/FK Blender**: Default 

Source
++++++

Link to Module (how)

arm_2jnt_02
-----------
WIP

arm_2jnt_03
-----------
WIP

arm_2jnt_04
-----------
WIP

arm_2jnt_freeTangents_01
------------------------
WIP

arm_ms_2jnt_01
--------------
WIP

brow_01
-------
Brow rig from a path along the brow on the mesh, one side per component. It
builds the same rig as Brow Rigger 3.0 (Rigbits > Facial Rigger 3.0): a whole
brow control, main and tangent controls, optional secondary controls,
squeeze, the optional slide surface and an optional topological autoskin.

**Guide**

* **root**: near the middle of the brow.
* **aim**: in front of it. Root to aim is the front direction, and the aim
  depth is the distance of the controls.

The side is the component side; right side controls mirror the left ones.

**Settings**: the brow path, the controls, squeeze, the slide surface,
joints and autoskin, as in Brow Rigger 3.0. **Check Detection** selects the
inner end found from the path. **Import Config** and **Export Config** read
and write the Brow Rigger ``.brows`` files. A center brow shows **Left Brow**
and **Right Brow**: the roots of the left and right ``brow_01`` guides its
ends follow.

**Notes**

* The mesh, and the slide surface when set, must be in the scene when the
  rig builds.
* Duplicate Symmetrical mirrors the locators and the path on the mesh.

cable_01
--------
WIP

chain_01
--------
WIP

chain_FK_spline_01
------------------
WIP

chain_FK_spline_02
------------------
WIP

chain_FK_spline_variable_IK_01
------------------------------
WIP

chain_IK_spline_variable_FK_01
------------------------------
WIP

chain_IK_spline_variable_FK_stack_01
------------------------------------
WIP

chain_net_01
------------
WIP

chain_spring_01
---------------
WIP

chain_spring_gravity_02
-----------------------
FK chain with spring and gravity on each segment. It can be scaled, stacked
with the other stack chains, and has optional tweak controls.

**Guide**

* **root**: start of the chain.
* **#_loc**: one locator for each segment end. The last one is the chain tip.
* **blade**: orientation of the chain.

**Settings**

* **Mirror Behaviour L and R**: on the R side, the controls are mirrored, so
  the same values give a mirrored pose on L and R.
* **Extra Tweak**: a tweak control on each segment, after the spring. The
  tweak control drives the joint. The **Tweak Vis** attribute shows them.
* **Tweak End**: a control and a joint at the chain tip, following the last
  spring segment. Components parented to the tip locator follow it.
* **Master Local / Master Global**: master chain followed by this chain.
  Select the master guide root and click the pick button. Click with nothing
  selected to clear it. The local master adds its motion in the segment
  space, the global master in world aligned space. The **Local Blend** and
  **World Blend** attributes blend the master motion.
* **Connection Offset**: master segment of the first segment of this chain.
  Segments past the master end use its last segment.

Compatible masters: ``chain_spring_gravity_02``, ``chain_stack_01``,
``lite_chain_stack_01``, ``lite_chain_stack_02`` and
``chain_spring_lite_stack_master_01``. The master needs at least as many
segments as this chain.

**Stack**

The chain is also a master of ``chain_stack_01``, ``lite_chain_stack_01``,
``lite_chain_stack_02`` and other ``chain_spring_gravity_02`` chains. The
slave chains follow the FK controls after the spring. The twist, wide and
depth channels of a master pass through to its slaves.

The local stack connection uses the segment orientation of
``chain_stack_01`` and ``lite_chain_stack``, so the master and slave chains
bend the same way, through **Master Local** and **Master Global**.

**Anim attributes**

* **Spring chain intensity**: 0 is the FK pose, 1 the full spring.
* **damping**, **stiffness**, **gravity**, **gravity_directionY**,
  **useGround** and **collide_softness**: spring settings for each segment.

**Scale**

The rig holds under global scale: the controls, the spring and the joints
scale together. Gravity is in world units and doesn't change with the scale.

chain_stack_01
--------------
WIP

chain_whip_01
-------------
WIP

control_01
----------
WIP

eye_01
------
WIP

eyelid_01
---------
Eyelid rig from an eyelid loop on the mesh. It builds the same rig as Eye
Rigger 3.0 (Rigbits > Facial Rigger 3.0): blink controls, eyelid controls,
eye tracking, one joint per loop vertex and an optional topological autoskin.

**Guide**

* **root**: the eye center.
* **aim**: in front of the eye. Root to aim is the eye direction, and the aim
  depth in front of the eyelid is the distance of the eyelid controls. Tilted
  and side facing eyes need no extra setting.

The side is the component side; right side controls mirror the left ones.

**Settings**: the eyelid loop (vertex loop by default, or edge loop), custom
corners, control size, tracking, joint distribution and autoskin, as in Eye
Rigger 3.0. **Import Config** and **Export Config** read and write the Eye
Rigger ``.eyes`` files. **Snap Root to Eyeball** moves the root to the eyeball
center.

**Connectors**

* **standard**: the component makes its own eye aim control.
* **eye_01**, **MCS_eye_01**: picked when the guide is drawn under an eye
  component. The eyelids follow the eye aim and sit under the eye's eyeOver
  control, so they don't spin with the eye.

**Notes**

* The mesh with the eyelid loop must be in the scene when the rig builds, for
  example imported by a pre custom step.
* Duplicate Symmetrical mirrors the locators and the loop on the mesh. Loop
  vertices without a mirror keep the source value, with a warning.
* The autoskin (off by default) blends the eyelid joints with the parent
  component joint.

foot_bk_01
----------
WIP

hydraulic_01
------------
WIP

leg_2jnt_01
-----------
WIP

leg_2jnt_02
-----------
WIP

leg_2jnt_freeTangents_01
------------------------
WIP

leg_3jnt_01
-----------
WIP

leg_ms_2jnt_01
--------------
WIP

lite_chain_01
-------------
WIP

lite_chain_stack_01
-------------------
WIP

lips_01
-------
Lips rig from the loop between the lips on the mesh. It builds the same rig
as Lips Rigger 3.0 (Rigbits > Facial Rigger 3.0): corner, center and
in-between controls, jaw follow, zipper, lip roll, optional squash and
stretch, one joint per loop
vertex and an optional topological autoskin.

**Guide**

* **root**: the mouth center, between the lips.
* **aim**: in front of the mouth. Root to aim is the mouth front direction,
  and the aim depth in front of the lips is the distance of the controls.
* **lip**: in the middle of the upper or lower lip, where the joints sit.
  The root to lip distance is the lips thickness.

The component is usually center side; the left and right controls are named
with ``_L_`` and ``_R_`` (``lips_C0_corner_L_ctl``) so the mirror tools pair
them.

**Settings**: the lips loop (vertex loop by default, or edge loop), Invert
Upper/Lower, rope points, controls, zipper and roll options, joint
distribution and autoskin, as in Lips Rigger 3.0. **Check Detection** selects
the upper lip found from the loop. **Import Config** and **Export Config**
read and write the Lips Rigger ``.lips`` files.

**Connectors**

* **standard**: the upper lip follows the guide parent, the lower lip the
  guide element set in **Jaw Reference** (the parent when empty). The Jaw
  Reference setting only shows with this connector.
* **mouth_01**, **mouth_02**, **MCS_mouth_01**, **MCS_mouth_03**: picked when
  the guide is drawn under a mouth component. The lips go under the mouth
  root, the upper lip follows the mouth ``lipup`` control and the lower lip
  its ``liplow`` control.

**Notes**

* The mesh with the lips loop must be in the scene when the rig builds, for
  example imported by a pre custom step.
* ``secondaryVis`` on the UI host hides the in-between controls.
* The autoskin (off by default) blends the lip joints with the strongest
  existing influence of each vertex, or skins to the parent component joint
  when the mesh has no skin yet.

meta_01
-------
WIP

mouth_01
--------
WIP

mouth_02
--------
WIP

neck_ik_01
----------
WIP

sdk_control_01
--------------
WIP

shoulder_01
-----------
WIP

shoulder_02
-----------
WIP

shoulder_ms_01
--------------
WIP

spine_FK_01
-----------
WIP

spine_S_shape_01
----------------
WIP

spine_ik_01
-----------
WIP

spine_ik_02
-----------
WIP

squash4Sides_01
---------------
WIP

squash_01
---------
WIP

tangent_spline_01
-----------------
WIP

ui_container_01
---------------
WIP

ui_slider_01
------------
WIP
