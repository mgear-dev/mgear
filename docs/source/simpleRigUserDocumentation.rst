Simple Rig User Documentation
#############################

Simple Rig is a lightweight rigging system for quickly setting up prop and
secondary-asset rigs. It is built around a custom-pivot control that drives one
or more objects, and can be arranged into a full hierarchy of parent/child
controls. A finished Simple Rig can be exported to JSON and converted into a
full Shifter rig when needed.

`Simple Rig 2.0 Intro <https://youtu.be/SEtVdJ4UiyQ/>`_

.. image:: images/simplerig/simplerig_GUI.png
    :align: center
    :scale: 95%


Overview
--------

Typical workflow:

1. **Create Root** — initialize the rig for your scene (world / global / local master controls).
2. **Create CTL** — select geometry or transforms and add a control that drives them.
3. **Edit** — re-parent controls, add or remove driven objects, move pivots.
4. **Auto Rig** — (optional) batch-create controls from groups matching a suffix.
5. **Export / Import Config** — save the setup as a ``.srig`` JSON file for reuse.
6. **Convert to Shifter Rig** — promote the Simple Rig to a full Shifter rig with joints and auto-skinning when the asset needs it.

Every Simple Rig control stores its pivot, shape, color, driven list and parent
relationship on the control node itself, so a scene can be inspected,
exported, imported or converted at any time.


Rig Tab
-------

.. image:: images/simplerig/simplerig_GUI.png
    :align: center
    :scale: 95%

**Create Root**

Initializes a Simple Rig in the current scene. Creates a ``rig`` transform
with ``world_ctl``, ``global_C0_ctl`` and ``local_C0_ctl`` master controls
above any geometry you have selected. Use the **Extra Config** tab first if
you want to change the root name, master-control size, shape, or disable the
world control.

Only one Simple Rig root is allowed per scene.

**Create Control**

Select one or more objects (meshes, NURBS surfaces, or transforms) and press
**Create CTL** to add a control that drives them.

* **Name** — base name of the new control. The final name follows the
  ``name_<side><index>_ctl`` convention (for example ``donuts_C0_ctl``).
* **Side Label** — ``Center``, ``Left`` or ``Right``.
* **Position** — where the pivot will be placed:

  * ``Center of Geometry`` — bounding-box center of the selected objects.
  * ``Base of Geometry`` — lowest Y point of the bounding box (useful for
    props that sit on the ground).
  * ``World Center`` — scene origin.

* **Ctl Shape** — ``Circle`` or ``Cube``.

The first object in the selection determines where the control is parented:
if it is another Simple Rig control, the new control becomes its child;
otherwise it is parented under the nearest master control.

**Edit**

Edit operations act on the currently selected Simple Rig control.

* **Pivot**

  * **Edit Pivot** — enter pivot-edit mode on the selected control. The
    control shape is unlocked so it can be translated/rotated to a new
    pivot location.
  * **Set Pivot** — commit the new pivot. The control returns to its neutral
    state at the new position.
  * **Re-Parent Pivot** — re-parent the selected control under another
    control. Select the child control first, then shift-select the new
    parent, and press this button.

* **Elements**

  * **+** — add the selected objects to the control's driven list.
  * **-** — remove the selected objects from the control's driven list.
  * **Select Affected** — select every object currently driven by the
    control.

**Auto Rig**

Quickly build a rig from groups that follow a naming convention.

.. image:: images/simplerig/simplerig_auto.png
    :align: center
    :scale: 95%

* **Suffix Rule** — any group whose name ends with this suffix
  (default ``geoRoot``) will receive an auto-generated control.
* **Auto Build** — scans the scene, creates the Simple Rig root if needed,
  and adds one control per matching group. Useful for kitbash scenes or
  pre-organized asset files.

The **Auto** menu (menu bar) exposes the same ``Auto Build`` action.


Extra Config Tab
----------------

Settings that affect **Create Root** and **Auto Build**. Adjust these before
creating the rig.

.. image:: images/simplerig/simplerig_extra.png
    :align: center
    :scale: 95%

**Root**

* **Root Name** — name of the rig transform (default ``root``).

**Main Controls (World, Local, Global)**

* **Main controls in World Center** — when enabled, master controls are
  placed at the scene origin. When disabled, they are sized and positioned
  around the current selection.
* **Use fix size** — override the auto-computed size with **Fix Size**.
* **Fix Size** — explicit size for the master controls.
* **Local/Global Ctl Shape** — ``Square`` or ``Circle``.
* **Create World Ctl** — toggle creation of the top-level world control. If
  disabled, the hierarchy starts at ``global_C0_ctl``.
* **World Ctl Shape** — ``Circle`` or ``Sphere``.

**Custom Sets**

* **Extra CTL Sets** — comma-separated list of extra Maya sets that every
  new control will be added to. Supports nested sets using a dot notation,
  e.g. ``animSets.basic`` will add the control to ``basic`` under
  ``animSets``.


Menu Bar
--------

File
~~~~

.. image:: images/simplerig/simplerig_file.png
    :align: center
    :scale: 95%

* **Export Config** — save the current Simple Rig configuration to a
  ``.srig`` JSON file. The file contains every control's name, pivot,
  shape, color, parent and driven list.
* **Import Config** — load a ``.srig`` file and rebuild the rig on the
  current scene geometry. Useful for reusing a rig setup across asset
  versions.

Convert
~~~~~~~

.. image:: images/simplerig/simplerig_convert.png
    :align: center
    :scale: 95%

* **Create Shifter Guide** — extract the Simple Rig configuration as a
  Shifter guide (one ``control_01`` component per Simple Rig control).
  The original Simple Rig is left intact, so you can keep iterating on it.
* **Convert to Shifter Rig** — full pipeline: build the Shifter guide,
  delete the Simple Rig, build the Shifter rig, and auto-skin every driven
  object to the matching joint.

.. note::

    Auto-skinning walks the subtree under each driven object and binds every
    mesh or NURBS surface it finds to the corresponding joint. When a deeper
    control claims a sub-group, the walk stops there and that sub-geometry
    is bound to the deeper joint instead. This means a control attached to
    a plain transform still gets its geometry skinned, and nested controls
    keep their own sub-geometry.

Delete
~~~~~~

.. image:: images/simplerig/simplerig_delete.png
    :align: center
    :scale: 95%

* **Delete Pivot** — delete the selected Simple Rig control. Its driven
  objects are reparented under the removed control's parent.
* **Delete Rig** — remove the entire Simple Rig from the scene. Geometry
  is reparented out of the rig first so it is not deleted.

Auto
~~~~

* **Auto Build** — same as the **Auto Build** button on the Rig tab (see
  above).


Tips and notes
--------------

* **Selection order matters** when creating a control. The first selected
  object is used for pivot computation and for parenting.
* **Pivot edit** must be committed with **Set Pivot** before exporting a
  config or converting to Shifter — a control in pivot-edit mode cannot be
  collected.
* **World Ctl** is optional but recommended. If you plan to convert to
  Shifter, the world control becomes the rig's world component.
* **Convert to Shifter Rig is destructive** — the Simple Rig is deleted
  after the Shifter rig is built. Save or export your config first if you
  want to keep iterating on the Simple Rig.
* **Driven lists** can contain transforms as well as shapes. When
  converting to Shifter, the auto-skin pass only binds skinnable shapes
  (mesh, NURBS surface, NURBS curve); other transforms are still driven
  through the joint hierarchy.