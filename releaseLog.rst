Release Log
===========


5.2.0
------
**New Features**
	* Shifter: Blueprint Guide: New feature for defining standardized rig settings shared across multiple characters with per-section and per-component local override support. Includes Guide Explorer color coding for blueprint status visualization.
	* Shifter: Custom Steps UI 2.0: Complete overhaul with drag and drop support, collapsible sections, custom step groups, config IO to JSON, multi-selection support, and improved visual styling #113
	* Shifter: Guide Explorer: New interface for exploring guides #592
	* Shifter: Guide Tools: Initial implementation #588
	* Utilbits: xPlorer: New tool with multi-selection, visibility toggle, attribute editor, search functionality, and arrow navigation #602
	* Rigbits: Eye Rigger 2.1: Simplified options and miscellaneous improvements #579
	* Mocap Tools: HumanIK Mapper: Batch Bake to Timeline button #590

**Enhancements**
	* Core: Icon: Adding Gear and mGear logo curve icons, update control_01 components
	* Core: Utils: Added undo off decorator for performance optimization
	* Shifter: Build speed optimization
	* Shifter: Guide traversal support in core dag and component guide #584
	* Shifter: Improving custom steps implementation and new method to run Sub-custom_Steps #601
	* Shifter: Adding Duplicate Symmetry Status flag for postDraw method logic
	* Shifter: Component creation and rename methods wrapped with single-undo decorator #589
	* Shifter: Update Shifter templates menu with better description for UE templates
	* Shifter: Update mannequin templates to use only EPIC components #58
	* Shifter: lite_chain_01: Adding mirror behavior
	* Channel Master: Update UI logic for slider sync behaviour #539 #593
	* RBF Manager: Added option to use custom names on RBF setups #595
	* RBF Manager: Better naming checker and logic when custom name is cancelled #595
	* SDK Manager: Misc fixes and UI updates #587
	* PyMaya: node.addAttr return attr correctly
	* PyMaya: Attr: added getRange() method
	* PyMaya: Node: refactor sets members method to support Pymel like flatten flag query
	* Core: Applyop: create_proximity_constraint now returns pyNode not string
	* Utilbits: Update menu and adding random colors tool #602
	* Allow underscores in rig_name property #558
	* Quick function for setting and updating mGear component types #559

**Bug Fix**
	* Core: upv_visualizer: replace floatMath by multiplyDivide (floatMath node from lookDev toolkit not always loaded) #567
	* Rigbits: Fix alignToPointsLoop
	* Rigbits: Lip rigger autoSkin not working #533 #562
	* Rigbits: Fix create_proximity_tweak
	* Rigbits: Eye Rigger 2.1: add kwargs for old version config compatibility #579
	* Shifter: Fix "Show Settings After Create New Component" checkbox being ignored in PySide6 #583
	* Shifter: Fix broken error handling when opening Guide Manager #569
	* Shifter: custom_step.py: fix dup method
	* Shifter: Skeletal and Geometry root validation added #573
	* SDK Manager: Fix issue with unitConversion nodes #587
	* SDK Manager: Fix driver_attr_drop_down #587
	* SDK Manager: sdk_io fix copySDKsNode #587
	* PyMaya: Fix node.py listAttr
	* RBF Manager: When driver is used to drive several setups, multiple poses added creating decomposition error on the solver #595
	* Core: PickWalk: fix pickwalk up and down for non controls
	* Ghost Slider Function erroring out (PyMaya compatibility) #513
	* Knee Auto Thickness: Changes rotate order value on readerB to improve stability #529 #564
	* Fix an error when generating diamond icon with pos offset #561
	* SimpleRig: Fix issue with relatives reversed order at generation time
	* Fix type hints #586
	* FIX: adding stateChanged connection to import skin checkbox in guide settings #440

**Solvers**
	* Fix memory leak in rollSplineKine: replace dynamic MQuaternion array with local vars #572

**ueGear**
	* UE 5.6 - Metahuman DDC export has new joint naming #536 #568
	* Remote Control ObjectPath defaults to 5.5+
	* Fix update camera "FBX export" error

5.1.0
------
**Enhancements**
	* Core: Anim_utils: allow ParentSpaceTransfer to be executed outside anim_picker #552
	* Rigbits: RBF Manager v2.0: new solver and misc updates #429 #514
	* Shifter: EPIC_control_01: add backwards_ref_jnt setting #523
	* Shifter: Improve IK/FK matching in arms and leg to support arbitrary length for FK sections and match with IK configuration #501


**Bug Fix**
	* Core: Right click dag menu fails to populate in all controls types #526
	* Core: SKIN IO: Rounding issue with 10+ influences #538
	* Rigbits: RBF Manager not working correctly with new weightDriver kernel. #514
	* Shifter: Behavior on EPIC_spine_02 : controls are rotating in wrong axis when moving IK #510
	* Shifter: Color settings aren’t working #511
	* Shifter: Core: CustomPickwalk faling if not controls #524
	* Shifter: EPIC_spine_02 : (UI bug) slider "Lock Orient Chest" and spin box aren't synced #516
	* Shifter: Orientation control and joints issue with chain_02 #509
	* Shifter: Rig not deleted when using confirmPop=False in delete_rig_keep_joints() #527
	* Shifter: The "Draw Component" in the right-click menu of the Shifter Guide Manager was incorrect when no component was selected. #528


**Deprecated**
	* IMPORTANT: Dropping support for Maya 2020 and older Maya versions.
	* IMPORTANT: Remove original weightDriver from SHAPES, been replaced by the mgearWeightDriver fork version. We can still use it on the weight driver but we need to install it separately

**ueGear 1.0.4**
	* Fixed remote control issue for UE 5.4+
	* Improved Control Rig build times

5.0.7
------
**Enhancements**
 	* Adding Maya 2026 OSX solvers (Note: RBF weightDriver not yet available in OSX)
 	* Flex: Add description in buttons for usage clarity #498
 	* Shifter: Chain_net_01: blend ui host is using the first FK control #504
 	* Shifter: Expose ctl name in shoulder components  #505
 	* Shifter:Data Centric folder creator, add support for "," separation on asset section #497

**Bug Fix**
	* Anim_picker: update metahuman picker
	* Animbits: HumanIK Mapper Bake not working  #507
	* Core: Anim_utils: Range Switch doesn't work for switching FK to IK overtime #488
	* Core: Anim_Utils: remove getIKPoleVectorMatrices method. We will fall back to the mth node matching. #488
	* Core: node.py createMultMatrixNode check if args are str and convert to PyNode
	* PyMaya: cmd: Update listRelatives to return the shape of the geometry as parent of MeshEdge, MeshVertex, or MeshFace types # 263
	* PyMaya: dag Node shortName now returns shortName. before was returning partilaPathName that can contain more than one "|" separator. #263
	* PyMaya: Node child method implemented. #496
	* Rigbits: Eye Rigger 2.0, Facial Rigger - no attribute ‘longName’. Adding longName method to MeshFace #506 #263
	* Shifter Component Chain_02 rotation issue #478
	* Shifter: EPIC leg 3jnt_01 Stretch broken when Full3bonesIK is 0  #479
	* Shifter: IKFK match issues with split wrist build in EPIC_arm_02 and arm_2jnt_freeTangent_01 #491
	* Shifter: Plebes Constrain to Rig not working  #502

**Deprecated**
	* Shifter: Remove MS components #503


5.0.6
------
**Enhancements**
	* PyMaya: Shifter: Collecting data only when will be stored. Removed the flush undo. Now we can undo rig builds. pymaya: Python wrapper for mGear #263
	* Shifter: Adding new Shifter Templates + fix bug on EPIC_met_01 when no control added #306
	* Shifter: Allow to connect to a non reset rotation joints.  #480
	* Shifter: Data collector is production ready. Removed "Experimental" in UI #383
	* Adding Maya 2026 windows solvers and Weightdriver

**Bug Fix**
	* Adjust ihi Behavior Based on Mode Type Instead of Step Type #472
	* After setting up RBF, the RBF Manager2 window does not open again.  #471
	* Anim_utils: IK/FK match set key automatically if any related control has already key. Previous fix was for ikFkMatch_with_namespace2, this fix is fro ikFkMatch_with_namespace #445
	* Core: Anim_utils: space switch and range switch doesn't support rotation pivot offset  #487
	* Core: Dagmenu: add neck ik control map for __switch_parent_callback #487
	* CORE: Maya 2026 support to new addDoubleLinear node naming
	* EPIC chain IK_FK_01 filing building using mode FK/IK.  #466
	* EPIC_meta: fix control Relative relations
	* Fixed missing "size" on Guide file builds #486
	* Fixed rotation pymel bug, replaced all pymel commands
	* PyMaya: fix error catch when name clashing in the guides #263
	* PyMaya: fix SoftTweak error catching #263
	* Rigbits: ProxySlice: Refactor to maya cmds. fixes #469
	* Shifter Component 3jnt legs. Change component internal joint visibility to avoid hiding child components #483
	* Shifter: Collect data fix WIP. Related with the new Pymaya wrapper and MVector parsing #263
	* Shifter: Quadruped leg IK/FK offset bug, IK/FK match menu and misc IK/FK matching .Update EPIC_3jnt_leg and Classic 3_jnt_leg fixes #445
	* Skin import issue (skinned NURBS curve) fixes #477
	* UI_Slider_01 component fails during installation. fixes #464
	* When using anim_utils.IkFkTransfer.execute(), only baking to FK works correctly ( includes possible fix ) fixes #406


5.0.5
------
**Bug Fix**
	* PyMaya: attr add index method #263
	* Anim_utils: IK/FK fix error when not keyframes #445
	* PyMaya: implementing pm.select() to support nested lists > This mimics pymel select() and fixed issue with custom pickwalk #263
	* Anim_utils: update get_ik_conntorls_by_role #445
	* Core: Transform: getTransformLookingAt add support for -x-y axis config
	* PyMaya: cmd listrelatives parent return empty list if none. Before was returning a list with an empty string like [""] now returns [] #263


5.0.4
------
**Bug Fix**
	* Anim_utils: IK/FK matching and Range Transfer misc Fixes and enhancements #445
	* PyMaya: PyMaya Node return implicit longName #263

5.0.3
------

**Enhancements**
	* Core: Skin IO: review logic to increase performance #456
	* PyMaya: cmd update lazy import
	* PyMaya: New List relatives implementation using api.OpenMaya #452
	* PyMaya: Node get parent and list relatives update #452
	* PyMaya: Node.attr: improve implementation to support compound attrs and indexed attrs #459
	* PyMaya: optimize _obj_to_name and _name_to_obj #263
	* SimpleRig: clean up  #452
	* Vendor plugin: Update SHAPES weightdriver plugin to the latest kernel version: from Maya 2020 to 2025

**Bug Fix**
	* Core: anim_utils: Fix support for _switch space naming. for IK/FK match range #445
	* Shifter: Delete Rig + Keep Joints functionality fails fixes #457
	* Shifter: Pyside6 update: fix component settings import #409


5.0.2
------
**Bug Fix**
	* Shifter: Handle name clashing when parsing the guide to determine the parent component #454
	* Core: Vector: Fix calculate pole vector #455



5.0.1
------
**New Features**
	* New animpicker template for Metahuman (Emilio Serrano Contribution)
	* Shiter component: chain_spring_gravity_01 (Emilio Serrano Contribution)

**Enhancements**
	* AnimPicker: Add function to re-order tabs in edit mode#419
	* Core: dagmenu.py enhancement. Reset to bindpose, reset all SRT #224
	* Crank: add support to use existing blendshapes nodes or creating nodes in foc #416
	* Removed Pymel dependency and new wrapper called pymaya (Big thanks to Kim Sol for all the hard work on the wrapper!!)
	* SDK IO adding support to blendshape nodes #434
	* Shifter: adding Edit button on message window when custom step fails #450
	* Spring Manager: Only keyframe relevant attributes Rotate and translate.  #420

**Bug Fix**
	* Anim Picker: Lost any tabs that haven't been converted to nurbs when you switch back to picker data. #323
	* anim_picker: Reading data file which uses ANIM_PICKER_PATH token is not working #210
	* Metahuman template MISC bugs #426
	* RBF manager uses f-strings which breaks compatibility with Maya 2020 #417
	* RBF Manager: Mirror pose not working correctly #424
	* Shifter foot: Toes do not scale together with the fk foot #320
	* Shifter: Error using custom_step duplicate function #213

**Removed Tools**
	* Rigbits: PostSpring
	* Rigbits: RBF manager v1
	* Rigbits: Rope tool
	* Synoptic picker


4.2.4
------

**Enhancements**
	* Shifter: Update data collector #383
	* Shifter: New joint structure options: World oriented #384
	* Crank: New functions and Crank channel box #386
	* Shifter: Rig Builder: IO for configurations and option to run from script #388
	* Shifter: Data Centric folder structure creator #390


**Bug Fix**
	* Crank: new targets are not keeping Edit on by default #386

4.2.2
------
**Bug Fix**
	* Shifter: Fix joint radius value retrieval from guide option #367

4.2.1
------
**New Features**
	* Added the new module chain_02

**Enhancements**
	* arm_2jnt_free_tangents_01 Align wrist to world orientation option #373
	* EPIC Arm and leg 02: added T reset pose option #359
	* Human Ik Mapper - Batch bake #374
	* Rig Builder: Added Pyblish validator and pre script to update guides #365
	* Shifter: Unlock visibility on rig top node. New guide settings: Joint size and guide vis after build #367


4.2.0
------
**New Features**
	* ueGear: 0.5 Beta
	* Shifter Game Tools: FBX exporter #117
	* Shifter: FBX exporter Intergration with Unreal #309
	* RBF Manager 2.0: Miscellaneous Improvements #324
	* Shifter: Rig Builder #115
	* Mocap Tool: HumanIK mapper tool #348

**Enhancements**
	* Animbits: Spring Manager misc bugs and updates #317 #349
	* Shifter: Add load from selection option in the template explorer #313
	* Core: Curve module update #319
	* chain_FK_spline_02 and control_01: add support for leaf joints #332
	* Shifter: Squash_01 add scale multipliers #33
	* Shifter: Add Match guide to joint hierarchy command #350

**Bug Fix**
	* Shifter: Not context menu with ghost controls #251
	* Shifter Component bug fix: chain_IK_spline_variable_FK_stack_01 #326 # 325
	* Made a metadata for rotateOrder #343 #328
	* Shifter: Replace self.__class__ in all components to avoid recursion error #362


4.1.2
------
**New Features**
	* Animbits: Spring Manager #266

**Enhancements**
	* shifter: Right click menu add space swich range like synoptic #206


4.1.1
------
**Enhancements**
	* EPIC_leg_3jnt_01 add support for 0 division on sections #273
	* Add a dagmenu to reset all controllers on viewport menu #286

**Bug Fix**
	* Fixed Error while mgear menu generation on startup #265 #267
	* Rigbits: Fixed a bug related to the Mirror Control Shape tool. reported by remicc #252 #174
	* Rigbits: Fixed a bug that can't open a fileDialog to import/export a SDK file throughout the GUI. #250
	* Shifter: Control_01 and other simple components wrong naming with some custom name rules. #268
	* Core: getTransformLookingAt fix axis calculation for -zx and -xy #296
	* Channel wrangler move bool channels #217
	* SoftTweak tool doesn't keep the right order of the softmod when re-import from .smt #262

4.1.0
------
**New Features**
	* Animbits: Space Recorder
	* chain_variable_IK #193
	* EPIC components improvements: arm 2.0 + leg 2.0 + leaf joint in all components + Misc Improvements #195
	* EPIC Meta_01 component #236
	* EPIC neck and spine component v2 using splineIK solver #228
	* EPIC_chain_IKFK_01 #192
	* EPIC_layered_control_01 #226
	* Misc: Smart export hotkey #180
	* Rigbits: PROXY GEO #196
	* Rigbits: Space Manager #152
	* Rigbits: Tweaks support for proximity pin #230
	* Shifter EPIC quadruped leg component #116
	* Shifter: embed guide information in rig #248
	* Shifter: Right click context menu for guides #187
	* Solvers: Add spring node gravity and simple collision #94

**Enhancements**
	* Added info for the user if (un)installation fails. #247
	* Channel Master: New features #74
	* Core: Added lineWidth of curves with collect_curve_data on curve.py #148 #151
	* Core: attributes: add vector 3 attr method #156
	* Core: deformer module + rigbits adding connect with morph #233
	* Drag and drop support for more mGear's serialized formats #179
	* EPIC Components adding support for custom name description #239
	* Epic templates: Change IK reference hand and foot space to follow arm and legs #141
	* Maya 2024 compatible.
	* Metahuman template detach command + review leaf joints connection/disconnection #52
	* Misc: Minimize code in userSetup.py #93
	* Rigbits: Eye rigger 2 fixed number of joints #249
	* Rigbits: IO Dialog use latest open folder
	* Rigbits: Mirror Controls add extra attributes #200
	* Rigbits: Misc improvements #129
	* Rigbits: Move existing blendshape node to the front of chain #128
	* Rigbits: RBF Manager, update SHAPES new node compatibility #244
	* Rigbits: Tweaks optional control shape argument
	* Shifter 3_jnt_leg Component: Tweak ctl by joint and MISC improvements #138
	* Shifter Guide x ray curve in 2022 and new Maya versions #209
	* Shifter: add rig_geo_grp set #137
	* Shifter: addCtl add to controller set is now optional
	* Shifter: better settings for CTL description #191
	* Shifter: build from selection should try to autoselect the guide if nothing is selected #170
	* Shifter: Build from selection without selecting guide #131
	* Shifter: Collect data options update #157
	* Shifter: Commands to manage joints connections and delete rig #169
	* Shifter: ConnectRef method update #159
	* Shifter: custom step UI misc improvements #241
	* Shifter: Data collector: collect ctl shapes #132
	* Shifter: Data Collector: Track joint solvers inputs #127
	* Shifter: Extract controls should filter if is ctl #185
	* Shifter: hide node inputs for controls #204
	* Shifter: Improve IK/FK matching for legs + foot #92
	* Shifter: Joint tagging to track guide locators relation #112
	* Shifter: optinal controls orientation #163
	* Shifter: Option to create joint_org directly on scene root #104
	* Shifter: Resizeable log window #133
	* SimpleRig: lock _npo #215
	* Update dagmenu.py #216



**Bug Fix**
	* Adding in deregister for springGravity node #153
	* anim_utils uses dict.iteritems() and errors in Python 3 #203
	* Animbits: SoftTweak support for Maya 2022+
	* attribute.py returns None and fails, if all channels are hidden #175
	* Build from guide template file incompatible with EPIC components #238
	* Core utils: viewport_off decorator fails in certain enviroment #190
	* Core: findComponentChildren3 will fail if there is no children #171
	* cvwrap missing print brackets for python 3 #84
	* drag_n_drop_install script bug #154
	* Epic components: Intermediate transforms in joint structure #142
	* EPIC leg 02 wrong IK orientation in R side when Z-up #255
	* Epic Mannequin Template several problems and bugs #242
	* EPIC_legs flip/twist issue and EPIC_arm tangent scale not 0.0 #99
	* Export weight maps broken in 2022+
	* Game Tools Export: Set index is incorrect, re-connect fails #231
	* IKFK match offset in biped template #122
	* leg_3jnt_01 module breaks when rotated to be Z-up #161
	* Metahuman driver neck bones not driven by mGear EPIC Metahuman rig #232
	* Metahunam template right hand fingers bad orientation #173
	* mgear menu disappearing issue #254
	* mgear viewport menu: Range Switch + missing space switch options #178
	* RBF Manager: import errors when 'drivenControlName' is null #149
	* RBFManager: check if drivenControlName is valid before testing scene #150
	* RBFManager: fix mirroring and add manual entry feature #155
	* RBFManager: Mirror ctl action not working #211
	* Rigbits: Bake spring menu command not working #83
	* Rigbits: Bake Spring nodes #177
	* Rigbits: blendshape module issue with 2.7 *args unpacking #160
	* Rigbits: RBF fix sorted() call #125
	* Rigbits: RBF manager failing to update the UI #124
	* Rigbits: SDK IO: Fixed tangents are not supported by setKeyframe #164
	* Rigbits: SDK manager reload python3 error #245
	* Shifter : connectRef handle negates scaled axis references
	* Shifter naming issue #225
	* Shifter naming rule issue: If the {index} is removed #221
	* Shifter: control_01 is missing ctl role. #167
	* Shifter: Delete rig keep joints fails if no joints #186
	* Shifter: fix ik/fk transition upv_ctrl #229
	* Shifter: Leaf joints not created if connect to existing joints active #183
	* Shifter: Rebuild rig on existing joints crash if joints has guide_relatives already created #165
	* Shifter: upvector space bad index issue affecting several components #198
	* Synoptic tabs list missing in guide configuration #256




4.0.9
------
**Enhancements**
	* Maya 2023 compatible. (OSX and Linux only mgear_solvers are available. WeightDriver and other C++ 3rd party plugins are not yet available)
	* Rigbits: Facial Rigger 2.0 BETA (Not yet exposed in menu)
	* Shifter Component: Expose Foot roll default value in the component settings
	* Shifter: addParamAnim exact name argument
	* Shifter: Build log options
	* Shifter: Extract controls keep color
	* Shifter: Shifter: Improve IK/FK matching for legs + foot
	* Shifter_EPIC_components: Joint name descriptions exposes in settings new tab

**Bug Fix**
	* Rigbits: Facial rigger had some issues with Py3
	* Shifter: component: chain_IK_spline_variable_FK_01 TypeError
	* Shifter: FK/FK Match on Metahuman Leg Broken
	* Shifter_EPIC_components: Epic_arm mirrored mid_ctr problem
	* Shifter_EPIC_components: EPIC_leg_01 (Right) is broken


4.0.7
------
**Enhancements**
	* Rigbits: Channel master external data support and various improvements
	* mGear_Core: New env var "MGEAR_PROJECT_NAME" to set the project name in mGear menu
	* Shifter: Pebles: Skin transfer and more templates
	* Shifter: Data collector option to store data on joint custom attr
	* mGear_Core: anim_utils: IK/FK match with keyframe only key the blend value on uiHost

**Bug Fix**
	* Shifter_components: 3jnt_leg:  joint flip issue fixed
	* Shifter_EPIC_componentsMetahuman template twist flip problem fixed
	* Logo missing from installer
	* Shifter_EPIC_componentsMetahuman template toes offset IK/FK
	* Shifter: custom step path fix for OSX
	* mGear_core: Python3 reloadModule error fix


4.0.3
------

**New Features**
	* Project is back to mono repository on Github
	* Python 3 Support and Maya 2022
	* Shifter: Auto-snap for metahuman biped Template
	* Shifter: connect to existing joint in the scene
	* Shifter: Data collector for IO with other DCCs (Experimental Feature)
	* Shifter: New components. Epic mannequin components, chain_ori_loc_01
	* Shifter: New/Updated biped template
	* Shifter: RGB color support for controls

**Enhancements**
	# Rigbits: Removed lagacy facial tools
	* Anim_picker: Edit picker shape using curves
	* mGear menu icons
	* Shifter Component: Meta_01 new option to define how joints are connected
	* Shifter: Added optional x-ray for controls on Maya 2022
	* Shifter: Control_01 leaf joint option (Creates a joint without the ctl)
	* Shifter: Guides blade new shape and color. Also new attribute to change the size
	* Shifter: Metahuman and Mannequin templates updated and new naming on controls
	* Shifter: Naming rule have separated side labels for controls and joints
	* Shifter: Naming rule support for index padding
	* Shifter: Updated pole vector FK/IK match

**Bug Fix**
	* General bug fixes in all modules, Python3 compatibility and Maya 2022. More info https://github.com/orgs/mgear-dev/projects/20


3.7.11
------

**Enhancements**
	* mgear_dist: New drag and drop installer [mgear_dist#62]
	* Shifter: Extending the CustomShifterStep base class functionality. [shifter#109]
	* mGear_core: Added meshNavigation.edgeLoopBetweenVertices [mgear_core#77]
	* mGear_core: Added create raycast node function in applyop.py [mgear_core#90]

**Bug Fix**
	* Shifter: Error when joint name start with number [shifter#111]
	* mGear_core: Bad IKRot rol reference anim_utils.py [shifter#82]
	* mGear_core: Remove compile PyQt ui menu command for Maya 2022 compatibility [shifter#81]
	* mGear_core: Knots saved in json file and read if they exist [shifter#76]
	* Rigbits: Fix missing import in menu.py [rigbits#68]
	* Rigbits: rbf manager, import error catch and cleanup [rigbits#73]
	* Rigbits: Fix eyebrow joint orientation [rigbits#72]
	* Shifter_EPIC_components: Improve joint placement precision on arm, leg and spine. [shifter_epic_components#20]
	* Shifter_EPIC_components: Fixed relation dict value of "knee" in EPIC_leg_01 which causes building failure in certain cases. [shifter_epic_components#19]


3.7.8
-----
**New Features**
	* CFXbits: Xgen IGS boost: New tool to create curve based grooming with xgen interactive grooming splines [cfxbits#1]
	* mGear solvers: New matrixConstraint node [mgear_solvers#5]
	* mGear_core: Add support for drag n drop of mGear filetypes, .sgt [mgear_core#79]
	* mGear_core: Deformer weight IO module [mgear_core#75]
	* mgear_dist: Drag and Drop easy installer  [mgear_dist#56]
	* Shifter: Configurable naming template. [shifter#83]
	* Shifter: Joint orientation options. [shifter#73]
	* Shifter: Plebes (a tool for rigging character generator characters with mGear). [shifter#96]
	* Shifter_EPIC_components: New set of componets specially design for Unreal engine and Games in general.

**Enhancements**
	* mGear_core: General update to add CFXbits required functions [mgear_core#63]
	* mGear_core: Skinning mismatch vertex warning should include the name of the object [mgear_core#63]
	* Shifter: Add support for #_blade in chain coponents. [shifter#107]
	* Shifter: Attributes naming using component short name(instance Name) not component type name. [shifter#95]
	* Shifter: IO return shifter rig object for NXT tools integration. [shifter#94]
	* simpleRig: Improve automatic hierarchy creation [simpleRig#8]

**Bug Fix**
	* Anim Picker: Create picker improvements [anim_picker#21]
	* Anim Picker: Duplicate behavior creates instances [anim_picker#24]
	* Anim Picker: Duplicating pickers, spacing issue [anim_picker#22]
	* Anim Picker: Fail gracefully when space switch controls are not found [anim_picker#33]
	* Anim Picker: save overlay offset when change windows size [anim_picker#19]
	* Anim Picker: UI buttons hidden in OSX [anim_picker#34]
	* Animbits: Channel Master: Channel Master: Sync with Graph editor. [animbits#54]
	* Animbits: Channel Master: sync selected channels in graph editor. [animbits#55]
	* mGear solvers: added in the clamp values for the squash and stretch node [mgear_solvers#6]
	* mGear_core: anim_utils: improve IK FK match pole vector calculation [mgear_core#65]
	* mGear_core: Attribute module new functions: Make it work with control custom names [mgear_core#62]
	* mGear_core: Mirro/flip pose not working with custom names [mgear_core#71]
	* mGear_core: Mirror/flip pose fail [mgear_core#70]
	* mGear_core: QApplication instance dont have widgetAt method on Maya 2020 [mgear_core#66]
	* mGear_core: shifter_classic_components repeatedly added to sys.path  [mgear_core#69]
	* mGear_core: Stripe pipes from skinCluster names [mgear_core#64]
	* mgear_dist: Incorrect grammar in UI [mgear_dist#26]
	* mgear_dist: update menus to str command [mgear_dist#53]
	* Rigbits: Add attr ctrl tweaks  [rigbits#60]
	* Rigbits: Add control and tweaks module controls need to create "isCtrl" control tag  [rigbits#50]
	* Rigbits: Facial rigger is compatible with Shifter's game tools [rigbits#37]
	* Rigbits: Mirror controls required target shape to exist  [rigbits#56]
	* Rigbits: RBF manager mirror with custom names  [rigbits#63]
	* Shifter: Game tools fix connection issue with new matrix constraint node. [shifter#108]
	* Shifter: Game tools is not disconnecting all the connections between rig and model. [shifter#68]
	* Shifter: Guide component scale inconsistency at creation time. [shifter#97]
	* Shifter: replaces backslashes with forward slashes for Mac OS. [shifter#101]
	* Shifter: Set by default Force uniform scaling to ON. [shifter#79]
	* Shifter_classic_components: Change on Shifter leg_2jnt_tangent component settings UI [shifter_classic_components#81]
	* Shifter_classic_components: Control_01 component space switching with mgear viewport menu [shifter_classic_components#82]
	* Shifter_classic_components: Fix for issue "Menu: Ctrl+Shift results in broken shelf items" [shifter_classic_components#87]

**WARNING**
	* mgear_dist: dropping support for Maya 2017 and older [mgear_dist#60]



3.6.0
-----
**New Features**
	* Shifter_classic_components: chain_spring_lite_stack_master_01: New component [shifter_classic_components#79]

**Enhancements**
	* Anim Picker: Add create picker menu items based on selection [anim_picker#18]
	* Anim Picker: Make select controls display more noticeable [anim_picker#16]
	* Animbits: Channel Master: Add channels from any section in ChannelBox. [animbits#50]
	* Animbits: Channel Master: Auto color options. [animbits#51]
	* Animbits: Channel Master: option to configure channel order. [animbits#37]
	* Animbits: Channel Master: Turn off real time update on scrubbing. [animbits#51]
	* Animbits: Channel Master: Use selected channels for copy/paste keyframes. [animbits#52]
	* Animbits: softTweak: add surface fallof option [animbits#53]
	* mGear_core: attribute module new functions: get_selected_channels_full_path + collect_attrs [mgear_core#56]
	* Shifter: Add Joint Names parameter for customizing joint names in guide settings. [shifter#85]
	* Shifter_classic_components: lite_chain_stack_02 component: add blend option to turn off the connection [shifter_classic_components#78]

**Bug Fix**
	* Animbits: Channel Master: Blendshape node channels bug. [animbits#49]
	* Shifter: Importing old guides with missing parameters error. [shifter#69]

3.5.1
-----
**Bug Fix**
	* mGear_core: When copy skin, match the skinningMethod as well [mgear_core#55]
	* Rigbits: RBF Manager mirror bug with Flex Add_attribute [rigbits#54]

3.5.0
-----
**New Features**
	* Animbits: Channel Master [animbits#14]
	* Shifter: Auto Fit Guide (Beta preview). [shifter#82]

**Enhancements**
	* Anim Picker: Make select controls display more noticeable [anim_picker#16]

**Bug Fix**
	* Anim Picker: CentOS and windows Maya 2019/2020 TypeErrorr [anim_picker#15]
	* mGear_core: dagmenu error when parent switch with keys on and rig with namespace [mgear_core#53]
	* mGear_core: Fix loop crash when quering tag childrens [mgear_core#52]
	* mGear_core: Fixed path handling in exportSkinPack if it is called with arguments. [mgear_core#37]
	* mGear_core: getRootNode doesn't find the root correctly [mgear_core#51]
	* mGear_core: Mirror function causes tag attributes to mirror their content [mgear_core#47]
	* mGear_core: Parent switch dag menu not working when root node is parented under a non referenced heararchy. [mgear_core#48]

3.4.0
-----
**New Features**
	* Anim Picker: New Animation Picker [anim_picker#2]
	* mGear_core: mGear viewport menu [mgear_core#38]
	* Rigbits: SDK Manager [rigbits#42]
	* Shifter_classic_components: SDK manager special component [shifter_classic_components#75]

3.3.1
-----
**Bug Fix**
	* Rigbits: Facial rigger tools QT aligment argument [rigbits#44]

3.3.0
-----
**New Features**
	* Shifter_classic_components: Cable component [shifter_classic_components#73]
	* Shifter_classic_components: UI_slider and UI_container component [shifter_classic_components#66]
	* Rigbits: New eyebrow Rigger [rigbits#40]

**Enhancements**
	* Shifter_classic_components: Control_01: Expose more space switch options [shifter_classic_components#7]

3.2.1
-----
**Enhancements**
	* Shifter_classic_components:  arm_2jnt_04: wrist align and plane normal [shifter_classic_components#58] [shifter_classic_components#59]
	* Shifter_classic_components:  S_Spine change the relative connections  [shifter_classic_components#67]
	* mGear_core: Added 2D guide root for Shifter components [mgear_core#36]
	* Shifter: Build log window clears instead of reopening. [shifter#74]

**Bug Fix**
	* Shifter: Fixed a guide renaming issue. [shifter#71]
	* Shifter: Renamed Connexion to Connection in some places.. [shifter#75]
	* Shifter: Renaming components will fail if the names are not unique. [shifter#70]
	* Shifter_classic_components: foot_bk_01 component roll_ctrl issue [shifter_classic_components#68]
	* Shifter_classic_components: Visual axis reference for control_01 and arm_2jnt_04 is not scaling correctly  [shifter_classic_components#57]
	* Shifter_classic_components: Fixes building of chain_01 when set to IK only  [shifter_classic_components#65]
	* Shifter_classic_components:  spine_S_shape rename bug  [shifter_classic_components#50]
	* mGear_core: dag.findComponentChildren2 fails after a rig was built. [mgear_core#32] [mgear_core#35]
	* mGear_core: QDragListView ignores drop event on self  [mgear_core#34][mgear_core#33]

3.2.0
-----
**New Features**
	* Animbits: Animation GPU cache manager [animbits#11]
	* Rigbits: New Facial Rigger  [rigbits#28][rigbits#27][rigbits#64][rigbits#33][rigbits#32]
	* Shifter_classic_components: new arm and leg with elbow and knee thickness control [shifter_classic_components#55]
	* Shifter_classic_components: New component arm_2jnt_03 with align wrist with guide option [shifter_classic_components#53]
	* Shifter_classic_components: New component mouth_02 [shifter_classic_components#51]

**Enhancements**
	* Rigbits: Mirror Controls Shape Tool [rigbits#25]
	* Rigbits: RBF manager updated with support for non-control objects  [rigbits#31]
	* Shifter_classic_components: control_01, arm_2jnt_04 add orientation visual feedback [shifter_classic_components#54]

3.1.1
-----
**New Features**
	* shifter_classic_components: New Component: chain_IK_with_variable FK and stack connection [shifter_classic_components#43]
	* shifter_classic_components: New Component: chain_net_01 [shifter_classic_components#42]
	* shifter_classic_components: new component: Lite chain stack [shifter_classic_components#40]

**Enhancements**
	* mgear_core:implemented filesize compression for jSkin and gSkin (pull request #28)
	* Rigbits: Update tweakers modules [rigbits#18]
	* Shifter: add optional uihost argument on addAnimParam and addAnimEnumParam [shifter#60]
	* Shifter: avoid negative scaling in joints [shifter#59]
	* Shifter: inspect settings open tap option [shifter#62]
	* Shifter: Shared custom step fix color feedback and hover information [shifter#57]
	* shifter_classic_components: chain_net_01: improve pickwalk [shifter_classic_components#47]
	* shifter_classic_components: Chains with stack connection should have connection offset options [shifter_classic_components#46]
	* shifter_classic_components: Review channel hosts for stack connection chains [shifter_classic_components#44]
	* simpleRig: handle geometry selection option when convert to shifter rig [simpleRig#6]
	* Synoptic: Fix refresh needed on togglButtons and on visibility/control tabs [synoptic#13]

**Bug Fix**
	* mgear_core: attribute module log error wrong flags [mgear_core#29]
	* shifter_classic_components: chain FK with variable IK the extreme controls should not be on 0 or 1.0 of the path [shifter_classic_components#45]

3.0.5
-----
**Bug Fix**
	* mGear_core: Attribute: moveChannel doesn't support float attr [mgear_core#27]
	* mGear_core: Callback manager: UserTimeChangedManager change condition state to playingBackAuto [mgear_core#28]
	* Rigbits: Eye rigger and Lips Rigger bad naming in rig curves [rigbits#21]
	* Shifter: Export guide to template (.sgt) will break component parent references if name is not unique [shifter#58]


3.0.4
-----
**Bug Fix**
	* Synoptic: Fix refresh needed on togglButtons and on visibility/control tabs [synoptic#13]
	* mGear_core: Node: controller_tag_connect fail if ctl parent doesn't have tag [mgear_core#24]
	* Shifter_classic_components: Eye component update structure [shifter_classic_components#39]
	* Shifter_classic_components: Spine FK: fisrt joint moving with IK chest control [shifter_classic_components#38]
	* Shifter: custom step template still have old name import [shifter#56]
	* Rigbits: hotkey creation command has bad imports [rigbits#19]
	* Shifter: serialized guide with none parent components issue [shifter#55]
	* Rigbits: Ghost control creator and Tweaks should handle ctrl Tag and custom pickwalk [rigbits#20]

3.0.3
-----
**New Features**
	* Flex: Flex is the mGear models (geometry) update tool inside rigs.
	* Shifter: Build Rig from file [shifter#20]
	* Shifter: Game Tools,  for decouple deform and control rig [shifter#6]
	* Shifter: Guide Relative placement [shifter#14]
	* Shifter: Guide serialization to json
	* Shifter: New Guide manager
	* Shifter: Serialized Diff Tool
	* Shifter: Serialized Guide Explorer
	* Shifter_classic_components: New Component: Chain FK spline with variable IK controls [shifter_classic_components#26]
	* Shifter_classic_components: New Component: Chain IK spline with variable FK controls [shifter_classic_components#30]
	* Shifter_classic_components: New Component: Chain Stack [shifter_classic_components#32]
	* Shifter_classic_components: New Component: shoulder_02 [shifter_classic_components#25]
	* Shifter_classic_components: New Component: Spine FK [shifter_classic_components#31]
	* Shifter_classic_components: New Component: Tangent_spline_01 [shifter_classic_components#28]
	* Shifter_classic_components: New Component: Whip chain [shifter_classic_components#27]


**Enhancements**
	* Animbits: softTweak: make UI dockable [animbits#8]
	* Crank: Make UI dockable [crank#3]
	* Crank: Shot Sculpting tool, General update initial Goals [crank#1]
	* mGear_core: attribute: FCurveParamDef should store the samples from getFCurveValues [mgear_core#12]
	* mGear_core: attribute: ParamDef: Dict serialisation [mgear_core#11]
	* mGear_core: pyQt: showDialog option to make windows dockable [mgear_core#6]
	* mGear_core: Skin module: Review it and update use Json and pickle [mgear_core#20] [mgear_core#23]
	* Shifter: Custom step list. Visual cue for shared custom step [shifter#51]
	* Shifter: FCurveParamDef should store the samples from getFCurveValues in value of paramDef [shifter#26]
	* Shifter: update menu with new functionalities [shifter#37]
	* Shifter: Update modal position menu to QT modern version [shifter#46]
	* Shifter_classic_components: add new upv roll control to arm_2jnt  [shifter_classic_components#36]
	* Shifter_classic_components: Add UniScale option for games compatible  [shifter_classic_components#9]
	* Shifter_classic_components: arm_2jnt_01 and leg_2jnt_01: Make optional the extra support joint in the articulations [shifter_classic_components#3]

**API Changes**
	* mgear_dist: Modularisation of mgear [mgear_dist#11]

**Bug Fix**
	* mGear_core: Attribute: channelWrangler apply config from script fails due to attributeError [mgear_core#21]
	* mGear_core: curve: create_curve_from_data_by_name should not take the name from the first shape [mgear_core#17]
	* mGear_core: curve: importing curve while rebuild hierarchy will fail if the parent object don't have unique name [mgear_core#18]
	* Rigbits: Duplicate symmetry bad import string [Rigbits#13]
	* Rigbits: Replace Shape Command doesn't handle if the target object have input connections in the shape [Rigbits#12]
	* Shifter: Component connector: standard fallback [shifter#27]
	* Shifter: Component space references: add checker for space references names [shifter#16]
	* SimpleRig: re-import configuration dont link unselectable geometry [simpleRig#1]


2.6.1
-----
**New Features**
	* Animbits: Crank shot sculpt  [mgear#233]
	* Rigbits: RBF Manager: support for non-control objects  [mgear#228]

2.5.24
------
**New Features**
	* mGear: IO curves [mgear#76]
	* Rigbits: RBF Manager [mgear#183]
	* Rigbits: set driven key module [mgear#160]
	* Simple Rig: 2.0 [mgear#163]
	* Synoptic: Control lister Tab [mgear#99]
	* Synoptic: geometry visibility manager Tab [mgear#130]
	* Synoptic: Spine IK <--> FK animation transfer [mgear#169]

**Enhancements**
	* Animbits: SoftTweak tool update [mgear#167]
	* mGear: skin: copy skin [mgear#168]
	* Shifter: chain_FK_spline_01: keep length multiplayer channel [mgear#199]
	* Shifter: chain_FK_spline_02: add extra Tweak option [mgear#202]
	* Shifter: component ctrlGrp should be inherit from parent component [mgear#181]
	* Shifter: Component Lite chain and chain FK spline mirror auto pose configuration if override negate axis direction in R [mgear#198]
	* Shifter: Component Lite chain and chain FK spline mirror auto pose configuration if override negate axis direction in R [mgear#198]
	* Shifter: Control_01: lock sizeRef axis [mgear#156]
	* Shifter: Custom Step List: Highlight Background quicksearch [mgear#203]
	* Shifter: Lock joint channels if "separated joint structure" is unchek [mgear#182]
	* Shifter: Make not keyable the joints channel if jnt_org is checked [mgear#188]
	* Shifter: neck_ik: add option to orient IK to world space [mgear#159]
	* Shifter: Partial build skip custom steps [mgear#154]
	* Shifter: spine_S_Shape: add option to orient IK to world space [mgear#164]
	* Shifter: Turn on/off custom steps [mgear#189]

**Bug Fix**
	* mGear:  curve.addCnsCurve: modify the center list in some situations [mgear#172]
	* Rigbits: Blended Gimmick joints bad naming with multy selection [mgear#153]
	* Shifter: 3jnt leg roundness att for knee and ankle [mgear#144]
	* Shifter: add_controller_tag. Fail on Maya old versions [mgear#187]
	* Shifter: Component: spine_IK_02: Last FK control don't have correct attr [mgear#161]
	* Shifter: Controller tag lost if export selection the rig [mgear#175]
	* Shifter: Joint connection: Maya evaluation Bug [mgear#210]
	* Shifter: leg_2jnt and leg _2jnt_freetangents not taking max stretch default setting [mgear#162]
	* Shifter: Spine S Shape: bad build with offset on fk controls [mgear#146]
	* Simple Rig: BBox computation fails with lights [mgear#212]
	* Synoptic: IK/FK transfer doesn't save keyframes on blend channel [mgear#180]
	* Synoptic: IK<->FK transfer strange refresh [mgear#173]

**Known Issues**
	* Shifter: Undo Build from selection crash maya. Now flush Undo to avoid possible crash [mgear#74]


2.4.2
-----
**Bug Fix**
	* Animbits: SoftTweak root lost relative position to parent [mgear#143]

2.4.1
-----
**Bug Fix**
	* Shifter: Rotation inverted on joints with negative scale [mgear#142]

2.4.0
-----
**New Features**
	* Animbits: SoftTweaks tool [mgear#133]
	* LINUX: Maya 2018 solvers
	* Rigbits: Eye rigger tool [mgear#127]
	* Rigbits: Lips Rigger tool [mgear#128]
	* Shifter: New Component: Chain FK spline Component [mgear#104]
	* Shifter: New Component: Lite FK chain [mgear#115]
	* Shifter: New Component: Spine_S_shape [mgear#96]

**Enhancements**
	* Shifter: Add alias names for space references [mgear#110]
	* Shifter: Add visual crv connection for the upVector controls [mgear#124]
	* Shifter: arm and leg 2jnt: add optional controls x Joint [mgear#114]
	* Shifter: chain_FK_spline: add option to control visibility of controls [mgear#136]
	* Shifter: Hide controls on Playback rig setting [mgear#131]
	* Shifter: Improve parallel evaluation [mgear#123]
	* Shifter: Lite_chain and Chain_FK_spline. Option to override side negation [mgear#139]
	* Shifter: Neck_ik_01: add option to have only IK space reference [mgear#132]
	* Shifter: Review rollspline solver precision values [mgear#138]
	* Shifter: Set all controls shape to d1 curves [mgear#118]
	* Shifter: Set to False the default use of uniscale in joints [mgear#117]
	* Shifter: Update component with Proxy attributes [mgear#111]

**Bug Fix**
	* Shifter: Bindpose bug with custom controllers grp [mgear#134]
	* Shifter: Component addJnt error if negative scaling [mgear#141]
	* Shifter: Extracted controls doesn't clean shape name [mgear#135]
	* Shifter: leg_2jnt_01 maxStretch setting is lost at build time [mgear#140]
	* Shifter: Maya 2018.2 flip in leg_2jnt_01 component [mgear#125]

2.3.0
-----
**Enhancements**
	* mGear: Attribute: addAttribute not setting default attribute value. [mgear#84]
	* mGear: Attribute: update with lock and unlock attribute functions [mgear#83]
	* mGear: PEP8 Style Refactor [mgear#100]
	* mGear: Refactor all exception handling [mgear#88]
	* mGear: Vendoring QT [mgear#89]
	* Shifter: Build command review and log popup window [mgear#73]
	* Shifter: Change Global_C0_ctl to World_ctl [mgear#66]
	* Shifter: Control_01: Add option to have mirror behaviour [mgear#68]
	* Shifter: Improve rig build speed [mgear#65]
	* Shifter: Leg_2jnts_freeTangents_01:no ikFoot in upvref attribute [mgear#62]
	* Shifter: Reload components in custom path [mgear#78]
	* Shifter: Update guide structure in pre custom step [mgear#101]
	* Simple Rig: Update functionality revision  [mgear#71]
	* Synoptic: spring bake util [mgear#61]

**Bug Fix**
	* Rigbits: createCTL function issue [mgear#59]
	* Rigbits: export skin pack error with crvs [mgear#56]
	* Rigbits: skin: There is a case in exportSkin function breaks the existing file [mgear#58]
	* Shifter: 3 joint leg: soft Ik range min in graph editor [mgear#82]
	* Shifter: arm_2jnt_freeTangents_01 no attribute 'rollRef' [mgear#63]
	* Shifter: Arms auto upvector and shoulder space jump [mgear#85]
	* Shifter: Chain_spring_01: pop if manipulate FK ctl after Bake [mgear#75]
	* Shifter: Connect Ctl_vis [mgear#103]
	* Shifter: Control_01: rotation axis is missing Y lock [mgear#74]
	* Shifter: Japanese Ascii [mgear#79]
	* Shifter: Spring chain: lock control parent and bake spring bug [mgear#67]
	* Shifter: Synoptic: IK/FK Match with arm_ms_2jnt_01 [mgear#80]

**Known Issues**
	* Shifter: Undo Build from selection crash maya [mgear#74]

2.2.4
-----
**Enhancements**
	* Shifter: Global scale and size of controllers. [mgear#50]

2.2.3
-----
**Enhancements**
	* Shifter: Custom Steps: Added Stop Build and Try again option if step fail.[mgear#43]

**Bug Fix**
	* Synoptic: Match IK/FK with split ctl for trans and rot [mgear#54]

2.2.2
-----
**Enhancements**
	* Shifter: Components: Legs: Mirror axis behavior on upv and mid ctl [mgear#47]
	* Shifter: Componets: Arms: IK ctl mirror behaviour [mgear#48]
	* Shifter: arm roll new reference connector [mgear#53]

**Bug Fix**
	* Shifter: component UI min division hang. Check all components [mgear#42]
	* Shifter: quadruped rig not being created in 2018 [ mgear#44]
	* Shifter: Close settings Exception on Maya 2018: Note: This is a workaround. The issue comes from Maya 2018 [mgear#49]

2.2.1
-----
**Bug Fix**
	* Shifter: Component: Hydraulic: Fix bad reference connector
	* Docs: Text error fix
	* Shifter: Text error fix

2.2.0
-----
**New Features**
	* Maya 2018 compatible
	* Simple autorig This a new rigging sytem for basic props.
	* Channel Wrangler: Channel manager with export import options.

**Enhancements**
	* Synoptic: key/select all for custom widgets
	* Skin IO: IO skin for curves & nurbs
	* Skin IO: Now can export with Skin Packs. Every object will be in a separated file.
	* Shifter: custom Sets: Now is possible to add custom sets to shifter components
	* Shifter: Now all the controls are Tag as a control (> Maya 2016.5)
	* Shifter: Custom Rig controls navigation
	* Shifter: Custom steps IO to JSON file.
	* Shifter: Componente: Chain_01: Non uniform scaling for FK controls
	* Shifter: Now the controls have unchecked historical interest from ctl shapes for cleaner channel box
	* Rigbits: Now replace shape support multiple shapes
	* mGear: Menu updated with about info and useful links
	* mGear: Added support for RGB color on icons/Controls

**Bug Fix**
	* Shifter: component: freetangent arm and leg: Fixed joint offset in the extremes
	* General: Fixed bad parenting for PySide dialogs.


2.1.1
-----
**New Features**
	* mGear solvers: New vertex position node.  This node gets the vertex position in worldspace.
	* Rigbits: New rigging commont library with toos and functions to help the rigging system. This library is meant to be use with custom steps or other rigging tools.
	* Shifter: Components: New  Components from Miles Cheng "arm_ms_2jnt_01", "shoulder_ms_2jnt_01" and "leg_ms_2jnt_01"
	* Shifter: Components: New enviroment variable: MGEAR_SHIFTER_COMPONENT_PATH (only project components)
	* Shifter: Custom Step: New enviroment variable: MGEAR_SHIFTER_CUSTOMSTEP_PATH to stablish relative paths for the custom steps data.
	* Shifter: New Channel naming options

**Improvements**
	* Improved error logging for custom steps and Synoptic.
	* Shifter: Clean up jnt_org empty groups after rig build.
	* Shifter: Components: Updated neck with optiona tangent controls.
	* Shifter: Components: Arm have a new option to separate the IK controls in rotation and translation control
	* Shifter: Components: Control extraction name buffer to avoid name clashing for ctl extraction on guides
	* Shifter: Components: Pin elbow/knee
	* Shifter: Components: Spine updated: Autobend optional control and optional mid tangent control
	* Shifter: Components: Arms mid ctl and upv with optinal mirror behaviour.
	* Shifter: Custom step using class implementation
	* Shifter: Track information (rig Asset, components used version and mGear version)
	* Synoptic: General visual and structure improvement. Big Thanks to Yamahigashi-san.
	* Synoptic: IK/FK animation transfer
	* Shifter: Updated biped guide
	* Shifter: Updated Quadruped guide

**Bug Fix**
	* Bad layout on setting windows with HDPI displays.
	* Shifter: Components: General clean up and bug fixing (Please check github commint for more info).
	* Issue mgear#9  leg_3jnt: Flip offset rz double connection
	* Issue mgear#13  Chain_01 IK refs not being connected

2.0
---
**New Features**
	* Custom enviroment variables for synoptic: MGEAR_SYNOPTIC_PATH
	* cvWrap deformer included.
	* Gimmick joints basic tools
	* Mocap HumanIK mapping tool for standard Shifter biped
	* New Component settings view.
	* New Documentation
	* New licensing under MIT license terms.
	* Pre and Post custom Steps.
	* Shifter: Modular rigging sytem rebranded.
	* Shifter: Quadrupeds template and new leg component for 3 bones legs.
	* Shifter: Single Hierarchy Joint connexion
	* Shifter: Update Guides Command.
	* Synoptic view Updated.

**Inprovements**
	* Component guides will snap to parent position at creation time.
	* Duplicate symmetry can find partial chain names. Is not needed to duplicate from the top root of the branch.
	* Groups and dag pose connected to rig base node. This will avoid lost elements if we export selection.
	* Guide Blades have new attr to control the  roll offset
	* mGear version and other useful information in guide root.
	* Newly created guide components automatic update of the side and uiHost from the parent attributes.
	* Shifter componets full review and functions unified.





