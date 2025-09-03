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
