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

Space Manager
=============

Create and manage space switches for rig controls. Space switches allow controls to follow different parent spaces (world, local, custom targets).

.. image:: images/rigbits/spaceManager.png
    :align: center
    :scale: 80%

**Constraint Types:**

* **Parent** - Full transform constraint (position, rotation, scale)
* **Point** - Position only constraint
* **Orient** - Rotation only constraint
* **Scale** - Scale only constraint

**Menu Types:**

* **Enumerated** - Dropdown attribute for discrete space selection
* **Float** - Blend attribute for smooth space interpolation

**Workflow:**

1. Select the control that needs space switching
2. Add target spaces (objects to follow)
3. Choose constraint type and menu type
4. Create the space switch

**Import/Export:**

Space configurations can be saved and loaded as .smd files for reuse across rigs.

Space Jumper
============

Create a local reference space from another space in the hierarchy. This creates a non-cyclic space relationship using matrix math.

**Usage:**

1. Select the reference space (parent transform)
2. Select the jump space (child space to reference)
3. Run Space Jumper

The tool creates ``_SPACE_`` and ``_JUMP_`` transforms connected via ``gear_mulmatrix_op`` for clean space relationships.

Interpolate Transform
=====================

Create a transform that blends between two objects using matrix interpolation.

.. image:: images/rigbits/interpolated_transform.png
    :align: center
    :scale: 80%

**Usage:**

1. Select the first object (A)
2. Select the second object (B)
3. Run Interpolate Transform

Creates a new transform with ``_INTER_`` naming that interpolates 50% between both objects. Uses ``gear_intmatrix_op`` for smooth matrix-based blending.

Connect Local SRT
=================

Connect Scale, Rotation, and/or Translation attributes between objects.

.. image:: images/rigbits/connect_local_SRT_menu.png
    :align: center
    :scale: 80%

**Options:**

* **Connect SRT** - Connect all three (Scale, Rotation, Translation)
* **Connect S** - Scale only
* **Connect R** - Rotation only
* **Connect T** - Translation only

**Usage:**

1. Select the source object (first)
2. Select target objects
3. Choose which attributes to connect

Channel Wrangler
================

Move or proxy channels between nodes with a visual table interface.

.. image:: images/rigbits/channel_wrangler.png
    :align: center
    :scale: 80%

**Operation Modes:**

* **Move Channel** - Physically move the channel from source to target
* **Proxy Channel** - Create a proxy attribute that mirrors the source

**Move Policies:**

* **merge** - Merge with existing channels
* **index** - Match by channel index
* **fullName** - Match by full attribute name

**Proxy Policies:**

* **index** - Match by channel index
* **fullName** - Match by full attribute name

**UI Features:**

* Visual table with Index, Channel, Source, Target, Operation columns
* Channel and Target line edits with picker buttons
* Set Multi-Channel and Set Multi-Target for batch operations
* Import/Export configurations as .cwc JSON files

Eye Rigger
==========

Automatic eyelid rigging tools. Two versions are available:

Eye Rigger 2.1
--------------

The updated eye rigger with simplified options and improved workflow.

.. image:: images/rigbits/eyeRigger2.1.png
    :align: center
    :scale: 80%

**Key Features:**

* Automatic upper/lower eyelid rigging from edge loops
* Multiple joint distribution options (every N vertex, fixed count, from center)
* Simplified mode for lighter rigs
* Customizable control size
* Auto-skin with topological propagation
* Vertical/Horizontal tracking attributes
* Blink height offset parameter

**Workflow:**

1. Select the eye mesh
2. Pick the eyelid edge loop
3. Set corner vertices (automatic or manual)
4. Configure joint distribution settings
5. Set naming prefix
6. Build the rig

**Parameters:**

* **Edge Loop** - The eyelid edge loop to rig
* **Corner Vertices** - Inner and outer corner vertex selection
* **Prefix** - Naming prefix for created nodes
* **Offset** - Surface offset distance (default 0.05)
* **Rigid/Falloff Loops** - Control density settings
* **Head Joint** - Reference joint for parenting
* **Do Skin** - Enable automatic skinning
* **Simplified** - Create simplified rig version

Eye Rigger (Legacy)
-------------------

The original eye rigger for backward compatibility.

.. image:: images/rigbits/eye_rigger.png
    :align: center
    :scale: 80%

Similar functionality to version 2.1 with the original parameter set including blink height percentage control.

Lips Rigger
===========

Automatic lip rigging from edge loops.

.. image:: images/rigbits/lips_rigger.png
    :align: center
    :scale: 80%

**Key Features:**

* Lip edge loop setup for upper and lower lips
* Central vertex selection for proper topology handling
* Thickness parameter for offset control
* Rigidity and falloff density settings
* Head and jaw joint references
* Automatic shape and control creation

**Workflow:**

1. Select the lip edge loop
2. Set the upper central vertex
3. Set the lower central vertex
4. Configure thickness and density settings
5. Set head and jaw joint references
6. Build the rig

**Parameters:**

* **Edge Loop** - The lip edge loop
* **Up Vertex** - Upper central vertex
* **Low Vertex** - Lower central vertex
* **Thickness** - Offset amount (default 0.3)
* **Rigid Loops** - Rigidity density (default 5)
* **Falloff Loops** - Falloff density (default 8)
* **Head Joint** - Head reference joint
* **Jaw Joint** - Jaw reference joint

Proxy Geo
=========

Create proxy geometry for joints with multiple creation modes.

.. image:: images/rigbits/ProxyGeo.png
    :align: center
    :scale: 80%

**Creation Modes:**

* **Proxy to Next** - Extends geometry toward the next joint in chain
* **Proxy Centered** - Creates geometry centered at joint position
* **Proxy to Children** - Aims geometry at child joints

**Shape Types:**

* **Capsule** - Rounded cylinder shape
* **Box** - Rectangular box shape

**Build Modes:**

* **Add** - Add new proxy geometry
* **Replace** - Replace existing proxy geometry

**Features:**

* Duplicate and Mirror existing proxies
* Combine multiple proxies into single mesh
* Export/Import proxy configurations as .pxy files
* Automatic axis alignment
* Build Tip Joint option for end joints

**Proxy Attributes:**

Created proxies have custom attributes for identification and configuration:

* ``isProxy`` - Boolean marker
* ``proxy_shape`` - "capsule" or "box"
* ``proxy_axis`` - Axis alignment
* ``side`` / ``length`` - Dimension attributes

Proxy Slicer
============

Create proxy geometry by analyzing skin cluster weights and splitting the mesh per joint influence. Uses OpenMaya2 for fast batch weight queries.

**How it works:**

1. Batch-queries all skinCluster weights via OpenMaya2 (single API call)
2. Groups faces by their dominant joint influence
3. Creates separate proxy meshes per joint
4. Names proxies as ``JointName_Proxy``
5. Handles locked transforms from skinned meshes (unlocks for operations, re-locks after parenting)

**Usage:**

Select one or more skinned meshes and run Proxy Slicer. The system automatically creates proxy geometry based on skin weights, with each proxy representing the area most influenced by that joint. Multiple meshes are processed in sequence.

Works with meshes that have additional deformers after the skinCluster (softMod, cluster, etc.) since it searches the full deformation history.

Proxy Slicer Parenting
======================

Same as Proxy Slicer but parents the created proxies directly under their influence joints instead of grouping them separately.

**Difference from Proxy Slicer:**

* **Proxy Slicer** - Creates a ProxyGeo group with matrix constraints to influence joints
* **Proxy Slicer Parenting** - Parents proxies directly under influence joints, re-locks transform attributes

**Python API:**

.. code-block:: python

    from mgear.rigbits import proxySlicer

    # Slice a single mesh (world-space mode with matrix constraints)
    proxySlicer.slice(parent=False, oSel="body_geo")

    # Slice with direct parenting under influence joints
    proxySlicer.slice(parent=True, oSel="body_geo")

    # Slice multiple meshes
    proxySlicer.slice(oSel=["body_geo", "head_geo", "hands_geo"])

    # Slice current selection (supports multi-select)
    proxySlicer.slice()

    # Slice current selection with parenting
    proxySlicer.slice(parent=True)

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

Wire to Skinning
================

A tool for creating wire deformers and converting them to skin clusters using the de Boor algorithm for NURBS-based weight computation.

.. image:: images/rigbits/wire_to_skinning/wire_to_skinning_UI.png
    :align: center
    :scale: 80%

Overview
--------

Wire to Skinning provides a workflow for:

1. **Creating wire deformers** from edge loops or joints
2. **Converting wire deformers to skin clusters** with precise B-spline weight distribution
3. **Export/Import configurations** for reusable wire setups

This tool is particularly useful for facial rigging, secondary deformation, and any setup requiring smooth, NURBS-based weight falloff.

.. Tip::

    Wire deformers are excellent for quick deformation tests. Use this tool to convert your wire setup to production-ready skin clusters once you're happy with the result.

Create Wire Section
-------------------

The top section allows creating wire deformers using two methods:

**Edge Loop Mode:**

* Select edges from the mesh to define the wire curve path
* Specify the number of CVs for the curve (more CVs = more joints/control)
* The curve is rebuilt to match the target CV count

**Joint Mode:**

* Select existing joints to define the wire curve
* The curve CVs are connected to joints via ``mgear_curveCns`` deformer
* Moving joints automatically updates the wire curve
* Joint ordering options: Selection order, Hierarchy, or Position X

**Common Parameters:**

* **Mesh** - Target mesh for the wire deformer
* **Wire Name** - Base name for the created wire deformer
* **Dropoff** - Wire influence falloff distance

Existing Wires Section
----------------------

Displays all wire deformers currently affecting the selected mesh.

* **Refresh** - Update the wire list
* **Select** - Select the wire deformer in Maya
* **Remove** - Delete the wire deformer and its curves

Convert to Skin Section
-----------------------

Converts wire deformers to skin clusters using the de Boor algorithm for B-spline basis function evaluation.

**Wire Selection:**

* **All Wires** - Convert all wire deformers on the mesh
* **Selected Wire** - Convert only the selected wire from the dropdown

**Joint Options:**

* **Auto-create joints** - Create joints at each curve CV position

  * **Prefix** - Naming prefix for auto-created joints
  * **Parent Joint** - Optional parent for the joint chain

* **Custom joints** - Use manually specified joints (must match CV count)

**Conversion Parameters:**

* **Static Joint** - Joint for vertices outside wire influence (default: ``static_jnt``)
* **Delete Wire** - Remove the wire deformer after conversion

**How Conversion Works:**

1. For each vertex, finds the closest point on the wire curve
2. Computes B-spline basis functions at that parameter using de Boor's algorithm
3. Distributes weights across nearby joints based on curve continuity
4. Blends with existing skin weights or assigns to static joint for unaffected areas

.. Tip::

    When converting a wire created from joints, the tool automatically uses those connected joints for skinning - no need to manually specify them.

Configuration Export/Import
---------------------------

Save and load wire configurations for reuse across scenes or characters.

**File Menu:**

* **Export Configuration** - Save wire setup to a ``.wts`` file
* **Import Configuration** - Load wire setup from a ``.wts`` file

**Exported Data:**

* Wire deformer settings (dropoff, scale, envelope)
* Curve CV positions
* Connected joint names (for joint-mode wires)
* Conversion settings

**Import Behavior:**

* Recreates wire deformers from saved curve data
* For joint-connected wires, automatically reconnects to existing joints
* Falls back to static curves if referenced joints don't exist

.. Tip::

    Enable mGear file drop (mGear > Utilities > Enable mGear file drop) to import ``.wts`` files by dragging them into Maya's viewport.

Scripting Access
----------------

The tool's core functions are available for scripting:

.. code-block:: python

    from mgear.rigbits import wire_to_skinning

    # Show the UI
    wire_to_skinning.show()

    # Create wire from edges
    positions = wire_to_skinning.get_edges_positions(edges)
    curve = wire_to_skinning.create_curve_from_positions(positions, num_cvs=8)
    wire = wire_to_skinning.create_wire_deformer(mesh, curve, dropoff_distance=5.0)

    # Create wire from joints
    wire, curve, curvecns = wire_to_skinning.create_wire_from_joints(
        mesh, joints, dropoff_distance=5.0, name="lip_wire"
    )

    # Convert wire to skin
    curve_info = wire_to_skinning.get_curve_info(curve)
    wire_info = wire_to_skinning.get_wire_deformer_info(wire)
    weights, uses_static = wire_to_skinning.compute_skin_weights_deboor(
        mesh, curve_info, wire_info, wire_deformer=wire
    )
    joints = wire_to_skinning.create_joints_at_cvs(curve_info, prefix="lip")
    skin = wire_to_skinning.create_skin_cluster(mesh, joints, weights)

    # Export/Import configuration
    wire_to_skinning.export_configuration(mesh, "/path/to/config.wts")
    wire_to_skinning.import_configuration("/path/to/config.wts", target_mesh=mesh)

**Core Module Functions:**

The underlying functions are also available in ``mgear.core`` modules:

* ``mgear.core.curve.getCurveInfo()`` - Get curve CVs, degree, knots
* ``mgear.core.deformer.createWireDeformer()`` - Create wire deformer
* ``mgear.core.deformer.getWireDeformerInfo()`` - Get wire deformer attributes
* ``mgear.core.deformer.getWireWeightMap()`` - Get per-vertex wire weights
* ``mgear.core.deformer.getMeshWireDeformers()`` - Find wire deformers on mesh
* ``mgear.core.skin.getCompleteWeights()`` - Get skin weights by vertex

.. _evaluation-partition:

Evaluation Partition
====================

The Evaluation Partition tool splits a mesh into polygon group partitions to optimize Maya's parallel evaluation. By dividing a dense mesh into independent sub-meshes, each partition can be evaluated in parallel, improving playback performance for complex character rigs.

Access from the menu: **mGear > Rigbits > Evaluation Partition**

.. image:: images/rigbits/evaluation_partition_ui.png
    :align: center

Overview
--------

The tool works by defining polygon groups on a source mesh and then executing an 8-step pipeline that creates independent partition meshes with all deformers transferred.

.. image:: images/rigbits/evaluation_partition_sample.png
    :align: center

Polygon Groups
--------------

Define which faces belong to each partition using the Polygon Groups section.

- **Default Group**: Contains all faces not assigned to other groups
- **Add Group from Selection**: Select faces in the viewport and click to create a new group
- **Add/Remove faces**: Use the ``+`` and ``-`` buttons on each group to add or remove selected faces
- **Select**: Click to select the group's faces in the viewport
- **Color coding**: Each group displays with a unique color shader for visual reference

Pipeline Steps
--------------

When you click **Execute Partition**, the tool runs an 8-step pipeline:

1. **Split Polygon Groups**: Creates independent meshes from each polygon group
2. **Transfer Blendshapes**: Captures blendshape targets via wrap-based baking, including in-between targets
3. **Clean Unused BS Targets**: Removes targets with zero delta on each partition
4. **Reconnect BS Inputs**: Replicates weight driver connections. For combo targets (multiply networks from SHAPES or similar), builds independent multiply chains per partition
5. **Copy Skin Clusters**: Transfers skin weights from source to each partition
6. **Remove Unused Influences**: Cleans influences with zero weight on each partition
7. **Copy Skin Configuration**: Copies skinCluster settings (skinningMethod, normalizeWeights, dqsScale connections, prebind matrices). Reproduces localized skinCluster connections (``mgear_mulMatrix``) if the source uses ``localize_skin_clusters``
8. **Proximity Wrap Proxy**: Creates a proxy mesh with proximity wrap for any remaining deformation

Visibility Controls
-------------------

Per-partition visibility attributes are created on the partitions root group node, allowing individual partitions and the proxy geometry to be toggled on and off.

Configuration
-------------

Save and load partition configurations using the **File** menu.

- **Export Configuration**: Save polygon groups and settings to a ``.evp`` file
- **Import Configuration**: Load a previously saved ``.evp`` file

Scripting Access
----------------

Launch the UI:

.. code-block:: python

    from mgear.rigbits import evaluation_partition
    evaluation_partition.show()

Run from a ``.evp`` configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``execute_from_file`` is the main entry point for pipeline automation and scripting. It loads a ``.evp`` file, creates a ``PolygonGroupManager``, and assigns the partition shaders to the mesh. It does **not** run the 8-step pipeline by itself — it only prepares the manager so you can inspect it, modify it, or feed it to the pipeline.

.. code-block:: python

    from mgear.rigbits import evaluation_partition as evp

    # Load the config and build the manager (shaders are created and assigned)
    manager = evp.core.execute_from_file("D:/configs/character_body.evp")

    # Optional: override the mesh stored in the config
    # manager = evp.core.execute_from_file(
    #     "D:/configs/character_body.evp",
    #     mesh="body_geo",
    # )

**Returns:** a ``PolygonGroupManager`` instance, or ``None`` if loading failed.

The manager holds the in-memory state reconstructed from the ``.evp`` file:

* ``manager.mesh`` — target mesh (long name)
* ``manager.groups`` — list of ``PolygonGroup`` objects, each with ``name``, ``color``, ``face_indices``, ``shader_node``, and ``shading_group``

This is useful for:

1. **Feeding the pipeline.** Every step function takes a manager as input. ``execute_from_file`` is the scripted way to get one without opening the UI.
2. **Previewing / QC.** Shaders are already assigned, so you can visually verify the partition in the viewport before executing the split.
3. **Inspecting or tweaking groups in code.** Iterate ``manager.groups`` to validate face counts, rename, recolor, or adjust face assignments (``add_faces_to_group``, ``remove_faces_from_group``, ``update_group_color``, ``rename_group``) before running the pipeline.
4. **Running a subset of steps** on the same manager (e.g. only split + skin copy, skipping blendshapes).

Run the full 8-step pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The typical scripted flow is: load the config, then hand the manager to ``execute_full_pipeline``.

.. code-block:: python

    from mgear.rigbits import evaluation_partition as evp

    manager = evp.core.execute_from_file("D:/configs/character_body.evp")

    # Optional: inspect or modify the manager here
    # for group in manager.groups:
    #     print(group.name, len(group.face_indices))

    grp, partitions, proxy = evp.core.execute_full_pipeline(manager)

Run individual pipeline steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you only need a subset of the pipeline, call the step functions directly on the manager. Step 1 (``split_polygon_groups``) must run first because it produces the partition meshes that every later step operates on.

.. code-block:: python

    from mgear.rigbits import evaluation_partition as evp

    manager = evp.core.execute_from_file("D:/configs/character_body.evp")

    # Step 1 — split the source mesh into partition meshes
    grp, partitions = evp.core.split_polygon_groups(manager)

    source = manager.mesh

    # Step 2 — transfer blendshapes
    evp.core.transfer_blendshapes(source, partitions)

    # Step 3 — clean unused BS targets
    evp.core.clean_unused_bs_targets(partitions)

    # Step 4 — reconnect BS input connections
    evp.core.reconnect_bs_inputs(source, partitions)

    # Step 5 — copy skin clusters
    evp.core.copy_skin_clusters(source, partitions)

    # Step 6 — remove unused influences
    evp.core.remove_unused_influences(partitions)

    # Step 7 — copy skin configuration and reproduce localization
    evp.core.copy_skin_configuration(source, partitions)
    evp.core.reproduce_skin_localization(source, partitions)

    # Step 8 — create the proximity wrap proxy
    proxy = evp.core.create_proximity_wrap_proxy(source, partitions, grp, manager)

``.evp`` configuration format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As of schema **v2.0**, ``.evp`` files store the target mesh as a **short name** rather than a full DAG path. This makes configurations portable across scenes, namespaces, and rig reorganizations — the tool resolves the short name to the actual node in the current scene at load time.

Backwards compatibility:

* Existing v1.0 ``.evp`` files (which store the long path) still load. If the stored long path still resolves, it is used verbatim; otherwise the tool falls back to a short-name lookup using the ``mesh_short_name`` field.
* Re-saving a v1.0 file writes it out as v2.0 automatically.

Ambiguity:

* If the short name in a config matches **more than one** mesh transform in the current scene, ``apply_configuration`` raises ``RuntimeError`` listing every match. Rename the conflicting nodes, or pass ``mesh=`` explicitly to disambiguate:

  .. code-block:: python

      manager = evp.core.execute_from_file(
          "D:/configs/character_body.evp",
          mesh="|rig|geo|body",   # explicit long path wins
      )

.. _blendshape-transfer:

Blendshape Setup Transfer
=========================

The Blendshape Setup Transfer tool transfers blendshape targets from one or more source meshes into a single blendShape node on a target mesh. It supports combo multiply networks, in-between targets, and preserves all alias names.

Access from the menu: **mGear > Rigbits > Blendshape Setup Transfer**

.. image:: images/rigbits/Blendshape_setup_transfer.png
    :align: center

Features
--------

**Multi-Source Transfer**

Transfer blendshape targets from multiple source meshes simultaneously. All targets are stacked into a single blendShape node on the target mesh with unique alias names. Name collisions are resolved by prefixing the source mesh name.

**Combo Network Rebuild**

For targets driven by SHAPES combo connections (multiply networks using ``multDL`` or ``multDoubleLinear`` nodes), the tool rebuilds an independent multiply chain on the target blendShape. The source combo network is never modified.

**Zero-Delta Cleanup**

Targets that produce no visible deformation on the target mesh are automatically detected and skipped during transfer, keeping the result clean.

**Connection Reconnection**

Simple weight drivers (animCurves, weightDrivers, etc.) are connected from the source to the corresponding target weight. Combo networks are rebuilt from scratch using the target's own weights as inputs.

Usage
-----

1. Set the **Target Mesh** using the ``<<`` button to load from selection
2. Add one or more **Source Meshes** using **Add from Selection**
3. Optionally set a custom **BS Node Name**
4. Enable or disable **Reconnect connections**
5. Click **Execute Transfer**

Configuration
-------------

Save and load transfer configurations using the **File** menu.

- **Export Config**: Save target, sources, and options to a ``.bst`` file
- **Import Config**: Load a previously saved ``.bst`` file and populate the UI

Scripting Access
----------------

.. code-block:: python

    from mgear.core import blendshape

    # Transfer from multiple sources to a target
    result = blendshape.transfer_blendshapes(
        sources=["source_head", "source_jaw"],
        target="target_body",
        bs_node_name="body_BS",
        reconnect=True,
    )

    # Run from a saved config file
    from mgear.rigbits.blendshape_transfer import core
    config = core.import_config("/path/to/config.bst")
    core.run_from_config(config)


SDK Creator
===========

Reads keyframed poses from the timeline and creates **Set Driven Key** setups. It converts animation data into SDK transform nodes with animCurve graphs driven by attributes on a UIHost control.

.. image:: images/rigbits/SDK_Creator_UI.png
    :align: center
    :scale: 80%

Workflow
--------

1. Select a **UIHost** control (the node that will hold the driver attributes)
2. Add the **controls** that have keyframed poses on the timeline
3. Click **Detect Poses** to read keyframes — the tool finds all keyed frames and lists them with editable pose names
4. Adjust the **Min/Max** range for the driver attributes (default 0–1)
5. Click **Apply** to generate the SDK setup

The tool creates:

- An ``_sdk`` transform above each control (like an NPO but for SDK offsets)
- A driver attribute per pose on the UIHost control
- ``animCurve`` and ``blendWeighted`` nodes connecting the poses to control channels

Mirror
------

The **Mirror** tab creates a symmetrical copy of the SDK setup by applying search/replace naming and optional channel negation.

.. image:: images/rigbits/SDK_creator_Mirror.png
    :align: center
    :scale: 80%

- **Search/Replace**: Renames controls and UIHost (e.g. ``_L`` → ``_R``)
- **Negate Channels**: Flips the specified transform channels (tx, ty, tz, rx, ry, rz, sx, sy, sz) to achieve mirror behavior

Configuration
-------------

Save and load SDK setups using the **File** menu.

- **Export Config**: Save the SDK setup to a ``.sdkc`` file
- **Export Mirror Config**: Export a mirrored version directly
- **Import Config**: Load a ``.sdkc`` file into the UI
- **Apply from File**: Apply an SDK setup directly from a file without loading the UI

The **Edit** menu provides **Delete SDK Setup from Controls** to cleanly remove SDK transforms and orphaned driver attributes.

Scripting Access
----------------

.. code-block:: python

    from mgear.rigbits.sdk_creator import core

    # Apply from a saved config file
    core.apply_from_file("/path/to/config.sdkc")

    # Mirror an existing config
    config = core.import_config("/path/to/config.sdkc")
    mirrored = core.mirror_config(
        config, search="_L", replace="_R",
        negate_channels=["tx", "rz", "ry"],
    )
    core.apply_from_config(mirrored)
