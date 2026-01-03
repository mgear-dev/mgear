Rigbits User Documentation
###########################

Rigging tools

.. image:: images/rigbits/menu.png
    :align: center
    :scale: 95%


Add NPO
===========

Add a transform as parent of each selected object in order to neutralize the local values to the reset position

.. figure:: images/rigbits/npo_before.png
    :align: center
    :scale: 95%

    The tranlate X and Y have some values

.. figure:: images/rigbits/npo_after.png
    :align: center
    :scale: 95%

    All the local transform values are reset


Gimmick Joints
==============

Joint helper tools.

Add Joint
---------------------

Add a deformer joint to each selected object.

This command will try to add the joint to "rig_deformers_grp" or create it if doesn't exist.
Also will parent the joint under "jnt_org" if exist. If doesn't exist will parent the joint under the corresponding object.

Add Blended Joint
---------------------

Add a blended joint under a chain of joints. This joint will rotat 50% between 2 joints.

.. image:: images/rigbits/gimmick_joints.png
    :align: center
    :scale: 95%

Add Support Joint
---------------------

Support joint are created under a blended joint and are design to help with deformation. Typically this kind of joints will also be driven by a SDK or similar.


Replace Shape
==============

Replace the shape of one object shape with another

.. image:: images/rigbits/gif/replace_shape.gif
    :align: center
    :scale: 95%


Match All Transform
===================

Align one object to another object using the world Matrix reference.


Match Pos with BBox
===================

Center the position of an object in the center of the bounding box of an object.


Align Ref Axis
==============

Create a reference locator axis based on a point selection. This command needs at less 3 points.

.. image:: images/rigbits/gif/Align_ref_axis.gif
    :align: center
    :scale: 95%

.. Tip::

	Very useful to find rotation axis in mechanical rigs if the transformations of the mesh have been freeze.


CTL as Parent
==============

Create a control of the selected shape as parent of each selected object.


Ctl as Child
==============

Create a control of the selected shape as child of each selected object.


Duplicate Symmetrical
======================

Duplicate and mirror the selected object and his children. This is done by negating some axis scaling and inverting some of the values. This will provide a mirror behavior.
Also handle some renaming. i.e: from _L to _R

RBF Manager
===========

A tool to manage a number of RBF type nodes under a user defined setup(name)

**2.1 quick overview**

.. only:: html

   .. raw:: html

      <div style="max-width: 880px; margin: 2em auto;">
        <div style="position: relative; padding-bottom: 56.25%;
                    height: 0; overflow: hidden;">
          <iframe
              title="vimeo-player"
              src="https://player.vimeo.com/video/1115410441?h=cbaa109360"
              frameborder="0"
              allow="autoplay; fullscreen; picture-in-picture; clipboard-write;
                      encrypted-media; web-share"
              allowfullscreen
              style="position: absolute; top: 0; left: 0; width: 100%;
                     height: 100%;">
          </iframe>
        </div>
      </div>

.. only:: not html

   `Watch on Vimeo <https://vimeo.com/1115410441/cbaa109360?fl=pl&fe=sh>`_

**RBF Manager Tutorial**

.. only:: html

   .. raw:: html

      <div style="max-width: 880px; margin: 2em auto;">
        <div style="position: relative; padding-bottom: 56.25%;
                    height: 0; overflow: hidden;">
          <iframe
              title="vimeo-player"
              src="https://player.vimeo.com/video/1115410469?h=aae34545a5"
              frameborder="0"
              allow="autoplay; fullscreen; picture-in-picture; clipboard-write;
                      encrypted-media; web-share"
              allowfullscreen
              style="position: absolute; top: 0; left: 0; width: 100%;
                     height: 100%;">
          </iframe>
        </div>
      </div>

.. only:: not html

   `Watch on Vimeo <https://vimeo.com/1115410469/aae34545a5>`_



Steps -
    set Driver
    set Control for driver(optional, recommended)
    select attributes to driver RBF nodes
    Select Node to be driven in scene(Animation control, transform)
    Name newly created setup
    select attributes to be driven by the setup
    add any additional driven nodes
    position driver(via the control)
    position the driven node(s)
    select add pose

Add notes -
Please ensure the driver node is NOT in the same position more than once. This
will cause the RBFNode to fail while calculating. This can be fixed by deleting
any two poses with the same input values.

Edit Notes -
Edit a pose by selecting "pose #" in the table. (which recalls recorded pose)
reposition any controls involved in the setup
select "Edit Pose"

Delete notes -
select desired "pose #"
select "Delete Pose"

Mirror notes -
setups/Controls will succefully mirror if they have had their inverseAttrs
configured previously.

Space Jumper
==============

Interpolate Transform
=====================

Connect Local SRT
=================


Spring
======

Rope
====

Channel Wrangler
================

Eye Rigger
==========

Lips Rigger
===========

Proxy Slicer
============

Proxy Slicer Parenting
======================

SDK Manager
===========

The SDK Manager is a tool for creating and managing Set Driven Keys (SDKs) in mGear rigs. It provides a streamlined workflow for setting up SDK-based facial rigs and corrective shapes using joints.

.. image:: images/rigbits/sdk_manager/SDK_manager_UI.png
    :align: center
    :scale: 80%

Overview
--------

The SDK Manager workflow is based on Judd Simantov's facial rigging techniques, using joints and SDKs to create facial shapes with the control of joints and weighting rather than blendshapes.

**Advantages:**

* Same results as blendshape-based face rigs with extreme control over every shape
* Expose tweak controls for every joint to animators
* Fits into the rebuild workflow - pivots and controllers can be altered without destroying rig work
* Export/import weight maps, guides, and SDKs between characters
* Can add blendshapes on top for further deformation

SDK Tab
-------

The main SDK tab provides the core functionality for setting driven keys.

**Driver Section:**

* Click the **Driver** button with a control selected to set it as the driver
* Choose the **Driver Attribute** from the dropdown to select which attribute drives the SDKs
* Enable **Show Only Connected Driver Attributes** to filter the dropdown to attributes that already have SDKs

**Key Channels:**

Select which channels to key on the driven controls:

* **Translate** - with individual X, Y, Z checkboxes
* **Rotate** - with individual X, Y, Z checkboxes
* **Scale** - with individual X, Y, Z checkboxes

This allows you to key only specific axes (e.g., only Translate Y and Rotate Z) rather than all channels.

**Driven Section:**

* Click **Add Selected Joints To Driven** to add SDK controls to the driven list
* Select items in the list and click **Set Driven Key** to create SDKs at current values
* Use the navigation buttons (<<, <, |, >, >>) to jump between existing key values
* Use the **Driver Val** slider and spin box to scrub the driver value
* The -1, -0.5, 0, +0.5, +1 buttons provide quick value adjustments

**Save Slots:**

The five save slot buttons allow you to store and recall SDK control positions:

* Click with controls selected to save their current values
* Click again to restore saved values
* Ctrl+Click to clear the slot

Right-Click Menu
----------------

Right-click on items in the driven list for additional options:

.. image:: images/rigbits/sdk_manager/Rightclick_menu.png
    :align: center
    :scale: 80%

* **Select SDK Ctl** - Select the SDK control in the viewport
* **Select Anim Ctl** - Select the animation tweak control
* **Select Joint** - Select the driven joint
* **Select SDKs** - Select all SDK animation curves
* **Select Tx/Ty/Tz/Rx/Ry/Rz Curves** - Select specific channel curves
* **Apply Control Offset to Selected** - Match driven controls to driver position
* **Delete All Keys at current Value** - Remove keys at the current driver value
* **Delete All SDKs** - Remove all SDKs from selected items
* **Remove From Driven** - Remove items from the driven list

Controls Tab
------------

The Controls tab provides tools for setting transform limits on SDK controls.

.. image:: images/rigbits/sdk_manager/control_limits_tab.png
    :align: center
    :scale: 80%

* **Lock/Unlock Limits** - Toggle transform limits on X, Y, Z axes
* **Set Upper Limits** - Set upper limit from current position
* **Set Lower Limits** - Set lower limit from current position

Mirror Tab
----------

The Mirror tab allows mirroring SDKs between left and right controls.

.. image:: images/rigbits/sdk_manager/mirror_tab.png
    :align: center
    :scale: 80%

* Select driver controls and click **Mirror SDK's From Selected Ctls X+ To X-** to copy SDKs to the opposite side

Menu Bar
--------

**File Menu:**

* **Export SDK's** - Export all SDKs to a JSON file
* **Import SDK's** - Import SDKs from a JSON file

**Select Menu:**

* **Select All SDK Ctls** - Select all SDK controls in the scene
* **Select All Anim Ctls** - Select all animation tweak controls
* **Select All SDK Jnts** - Select all SDK-driven joints
* **Select All SDK Nodes** - Select all SDK animation curve nodes

**Tools Menu:**

* **Toggle Infinity** - Toggle pre/post infinity on SDK curves
* **Set Tangent Type** - Set in/out tangent types (Auto, Spline, Flat, Linear, Plateau, Stepped)
* **Auto Set/Remove Limits** - Batch limit operations on selected controls
* **Rescale Driver range to fit Driven** - Adjust driver range
* **Lock/Unlock Animation/SDK Ctls** - Lock or unlock control channels
* **Prune SDKs with no input/output** - Clean up orphaned SDK nodes

**Reset Menu:**

* **Reset All Ctls** - Reset all controls to default
* **Reset SDK Ctls** - Reset only SDK controls
* **Reset Anim Tweaks** - Reset only animation tweak controls
