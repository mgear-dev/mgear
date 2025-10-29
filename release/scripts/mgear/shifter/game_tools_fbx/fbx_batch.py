"""
FBX Batch

Is used to handle tasks that used to be performed by the FBX API.
As the FBX API was an extra module that needed to be downloaded and installed,
it was decided that it would be more beneficial to the user to utilise
Maya Batch to perform the same tasks on the exported FBX file.

Process
-------
1. Shift FBX Exporter, exports the "master" fbx. This will be exported directly from
   the active scene, and should not impact the users scene data in any way.
2. Depending on what options/partitions where active, a variaty of batch tasks will be
   initialised, and perform alterations on the master fbx, and then generate a new FBX
   before ending the batch task.

Tasks / Conditions
------------------
- Removing namespaces.
- Clean up any lingering DAG nodes that are not needed.
- Partition Skeleton + Geometry.
- Exports each partition as an FBX.

Note
----
- Print logs are being used by the partition subprocess thread to detect progress.
"""
import os
import traceback
from collections import OrderedDict

import maya.cmds as cmds
import maya.api.OpenMaya as om
import mgear.pymaya as pm

from mgear.core import pyFBX as pfbx
import mgear.shifter.game_tools_disconnect as gtDisc

def perform_fbx_condition(
        remove_namespace,
        scene_clean,
        master_ma_path,
        root_joint,
        root_geos,
        skinning=True,
        blendshapes=True,
        partitions=True,
        export_data=None):
    """
    Performs the FBX file conditioning and partition exports.

    This is called by a MayaBatch process.
    """
    print("--------------------------")
    print(" PERFORM FBX CONDITIONING")
    print("  remove namespace:{}".format(remove_namespace))
    print("  clean scene:{}".format(scene_clean))
    print("  .ma path : {}".format(master_ma_path))
    print("--------------------------")

    # Load the master .ma file and force the scene to load it
    cmds.file(master_ma_path, open=True, force=True)

    # formats the output location from the master fbx path.
    output_dir = os.path.dirname(master_ma_path)
    fbx_file = export_data.get("file_name", "")
    if not fbx_file.endswith(".fbx"):
            fbx_file = "{}.fbx".format(fbx_file)

    print("  Output location: {}".format(output_dir))
    print("  FBX file: {}".format(fbx_file))

    # Removes all namespaces from any DG or DAG object.
    if remove_namespace:
        print("Removing Namespace..")
        export_data = _clean_namespaces(export_data)

        # updates root joint name if namespace is found
        root_joint = root_joint.split(":")[-1]
        for i in range(len(root_geos)):
            root_geos[i] = root_geos[i].split(":")[-1]

    if scene_clean:
        print("Cleaning Scene..")

        _partitions = export_data.get("partitions", dict())

        # Performs the same code that "Delete Rig + Keep Joints" does
        gtDisc.disconnect_joints()
        for rig_root in gtDisc.get_rig_root_from_set():
            rig_name = rig_root.name()
            jnt_org = rig_root.jnt_vis.listConnections(type="transform")[0]
            joints = jnt_org.getChildren()
            if joints:
                if cmds.listRelatives(joints, parent=True):
                    pm.parent(joints, world=True)

            # Updates all the geometry root paths, as they may have changed when geo
            # root was moved to world, depending on the structure of the rig.
            for geo_index in reversed(range(len(root_geos))):
                geo_root = root_geos[geo_index]
                geo_long_names = cmds.ls(geo_root, long=True)
                if len(geo_long_names) is not 1:
                    print("Too many {} found".format(geo_root))
                    return False
                geo_long_name = geo_long_names[0]
                if cmds.listRelatives(geo_root, parent=True):
                    output = pm.parent(geo_root, world=True)
                else:
                    output = cmds.ls(geo_root, long=False)
                root_geos[geo_index] = output[0]

                # The geo roots are moved to be under the 'World', in doing so we need to
                # update each geometry object stored in a partition.
                for partition_name, data in _partitions.items():
                    geo_list = data.get("skeletal_meshes", None)
                    filtered_array = [entry.replace(geo_long_name, "|"+geo_root) for entry in geo_list]
                    data["skeletal_meshes"] = filtered_array
                    _partitions[partition_name] = data

            export_data["partitions"] = _partitions

            pm.delete(rig_root.rigGroups.listConnections(type="objectSet"))
            pm.delete(pm.ls(type="mgear_matrixConstraint"))
            pm.delete(rig_root)

    if not skinning:
        print("Removing Skinning..")
        # Remove skinning from geometry
        _delete_bind_poses()

    if not blendshapes:
        # Remove blendshapes from geometry
        print("Removing Blendshapes..")
        _delete_blendshapes()

    # Save out conditioned file, as this will be used by other partition processes
    # Conditioned file, is the file that stores the rig which has already had data
    # update for the export process.
    print("Save Conditioned Scene...")
    print("    Path: {}".format(master_ma_path))
    cmds.file(save=True, force=True, type="mayaAscii")

    status = False

    if not partitions:
        # Exports the conditioned FBX
        master_fbx_path = os.path.join(output_dir, fbx_file)
        print("Exporting FBX...")
        print("    Path: {}".format(master_fbx_path))
        cmds.select(clear=True)
        cmds.select([root_joint] + root_geos)
        pfbx.FBXExport(f=master_fbx_path, s=True)
        status = True

    if partitions and export_data is not None:
        print("[Partitions]")
        print("   Preparing scene for Partition creation..")
        status = _export_skeletal_mesh_partitions([root_joint], export_data, master_ma_path)

    # Delete temporary conditioned .ma file
    print("[Clean up]")
    cmds.file(new=True, force=True)
    if os.path.exists(master_ma_path):
        print("   [Removing File] {}".format(master_ma_path))
        os.remove(master_ma_path)
    else:
        print("   Cleaned up conditioned file...")
        print("      Deleted - {}".format(master_ma_path))

    return status


def _export_skeletal_mesh_partitions(jnt_roots, export_data, scene_path):
    """
    Exports the individual partition hierarchies that have been specified.

    For each Partition, the conditioned .ma file will be loaded and have 
    alterations performed to it.

    """
    print("   Correlating Mesh to joints...")

    file_path = export_data.get("file_path", "")
    file_name = export_data.get("file_name", "")

    partitions = export_data.get("partitions", dict())
    if not partitions:
        cmds.warning("  Partitions not defined!")
        return False

    cull_joints = export_data.get("cull_joints", False)

    # Collects all partition data, so it can be more easily accessed in the next stage
    # where mesh and skeleton data is deleted and exported.

    partitions_data = OrderedDict()
    for partition_name, data in partitions.items():

        print("     Partition: {} \t Data: {}".format(partition_name, data))

        # Skip partition if disabled
        enabled = data.get("enabled", False)
        if not enabled:
            continue

        meshes = data.get("skeletal_meshes", None)

        joint_hierarchy = OrderedDict()
        for mesh in meshes:
            # we retrieve all end joints from the influenced joints
            influences = cmds.skinCluster(mesh, query=True, influence=True)

            # Gets hierarchy from the root joint to the influence joints.
            for jnt_root in jnt_roots:
                joint_hierarchy.setdefault(jnt_root, list())

                for inf_jnt in influences:
                    jnt_hierarchy = _get_joint_list(jnt_root, inf_jnt)
                    for hierarchy_jnt in jnt_hierarchy:
                        if hierarchy_jnt not in joint_hierarchy[jnt_root]:
                            joint_hierarchy[jnt_root].append(hierarchy_jnt)

        partitions_data.setdefault(partition_name, dict())

        # the joint chain to export will be the shorter one between the root joint and the influences
        short_hierarchy = None
        for root_jnt, joint_hierarchy in joint_hierarchy.items():
            total_joints = len(joint_hierarchy)
            if total_joints <= 0:
                continue
            if short_hierarchy is None:
                short_hierarchy = joint_hierarchy
                partitions_data[partition_name]["root"] = root_jnt
            elif len(short_hierarchy) > len(joint_hierarchy):
                short_hierarchy = joint_hierarchy
                partitions_data[partition_name]["root"] = root_jnt
        if short_hierarchy is None:
            continue

        # we make sure we update the hierarchy to include all joints between the skeleton root joint and
        # the first joint of the found joint hierarchy
        root_jnt = _get_root_joint(short_hierarchy[0])
        if root_jnt not in short_hierarchy:
            parent_hierarchy = _get_joint_list(root_jnt, short_hierarchy[0])
            short_hierarchy = parent_hierarchy + short_hierarchy

        partitions_data[partition_name]["hierarchy"] = short_hierarchy

    print("   Modifying Hierarchy...")

    # - Loop over each Partition
    # - Load the master .ma file
    # - Perform removal of geometry, that is not relevent to the partition
    # - Perform removal of skeleton, that is not relevent to the partition
    # - Export an fbx
    for partition_name, partition_data in partitions_data.items():
        if not partition_data:
            print("   Partition {} contains no data.".format(partition_name))
            continue

        partition_meshes = partitions.get(partition_name).get("skeletal_meshes")
        partition_joints = partition_data.get("hierarchy", [])

        print("Open Conditioned Scene: {}".format(scene_path))
        # Loads the conditioned scene file, to perform partition actions on.
        cmds.file(scene_path, open=True, force=True, save=False)

        # Deletes meshes that are not included in the partition.
        all_meshes = _get_all_mesh_dag_objects()
        for mesh in all_meshes:
            if not mesh in partition_meshes:
                cmds.delete(mesh)

        # Delete joints that are not included in the partition
        if cull_joints:
            print("    Culling Joints...")
            all_joints = _get_all_joint_dag_objects()
            for jnt in reversed(all_joints):
                if not jnt in partition_joints:
                    cmds.delete(jnt)

        # Exporting fbx
        partition_file_name = file_name + "_" + partition_name + ".fbx"
        export_path = os.path.join(file_path, partition_file_name)

        print("Exporting FBX: {}".format(export_path))
        try:
            preset_path = export_data.get("preset_path", None)
            up_axis = export_data.get("up_axis", None)
            fbx_version = export_data.get("fbx_version", None)
            file_type = export_data.get("file_type", "binary").lower()
            # export settings config
            pfbx.FBXResetExport()
            # set configuration
            if preset_path is not None:
                # load FBX export preset file
                pfbx.FBXLoadExportPresetFile(f=preset_path)
            fbx_version_str = None
            if up_axis is not None:
                pfbx.FBXExportUpAxis(up_axis.lower())
            if fbx_version is not None:
                fbx_version_str = "{}00".format(
                    fbx_version.split("/")[0].replace(" ", "")
                )
                pfbx.FBXExportFileVersion(v=fbx_version_str)
            if file_type == "ascii":
                pfbx.FBXExportInAscii(v=True)

            cmds.select(clear=True)
            cmds.select(partition_joints + partition_meshes)
            pfbx.FBXExport(f=export_path, s=True)
        except Exception:
            cmds.error(
                "Something wrong happened while export Partition {}: {}".format(
                    partition_name,
                    traceback.format_exc()
                )
            )
            return False
    return True


def _delete_blendshapes():
    """
    Deletes all blendshape objects in the scene.
    """
    blendshape_mobjs = _find_dg_nodes_by_type(om.MFn.kBlendShape)

    dg_mod = om.MDGModifier()
    for mobj in blendshape_mobjs:
        print("   - {}".format(om.MFnDependencyNode(mobj).name()))
        dg_mod.deleteNode(mobj)

    dg_mod.doIt()


def _find_geometry_dag_objects(parent_object_name):
    selection_list = om.MSelectionList()

    try:
        # Add the parent object to the selection list
        selection_list.add(parent_object_name)

        # Get the MDagPath of the parent object
        parent_dag_path = om.MDagPath()
        parent_dag_path = selection_list.getDagPath(0)

        # Iterate through child objects
        child_count = parent_dag_path.childCount()
        geometry_objects = []

        for i in range(child_count):
            child_obj = parent_dag_path.child(i)
            child_dag_node = om.MFnDagNode(child_obj)
            child_dag_path = child_dag_node.getPath()

            # Check if the child is a geometry node
            if (child_dag_path.hasFn(om.MFn.kMesh) or child_dag_path.hasFn(
                    om.MFn.kNurbsSurface)) and child_dag_path.hasFn(om.MFn.kTransform):
                geometry_objects.append(child_dag_path.fullPathName())

            # Recursive call to find geometry objects under the child
            geometry_objects.extend(_find_geometry_dag_objects(child_dag_path.fullPathName()))

        return geometry_objects

    except Exception as e:
        print("Error: {}".format(e))
        return []


def _delete_bind_poses():
    """
    Removes all skin clusters and bind poses nodes from the scene.
    """
    bind_poses_mobjs = _find_dg_nodes_by_type(om.MFn.kDagPose)
    skin_cluster = _find_dg_nodes_by_type(om.MFn.kSkinClusterFilter)

    dg_mod = om.MDGModifier()
    for mobj in bind_poses_mobjs + skin_cluster:
        print("   - {}".format(om.MFnDependencyNode(mobj).name()))
        dg_mod.deleteNode(mobj)

    dg_mod.doIt()


def _find_dg_nodes_by_type(node_type):
    """
    returns a list of MObjects, that match the node type
    """
    dagpose_nodes = []

    # Create an iterator to traverse all dependency nodes
    dep_iter = om.MItDependencyNodes()

    while not dep_iter.isDone():
        current_node = dep_iter.thisNode()

        # Check if the node is a DAG Pose node
        if current_node.hasFn(node_type):
            dagpose_nodes.append(current_node)

        dep_iter.next()

    return dagpose_nodes


def _cleanup_stale_dag_hierarchies(ignore_objects):
    """
    Deletes any dag objects that are not geo or skeleton roots, under the scene root.
    """
    IGNORED_OBJECTS = ['|persp', '|top', '|front', '|side']
    obj_names = _get_dag_objects_under_scene_root()

    for i_o in IGNORED_OBJECTS:
        obj_names.remove(i_o)

    for i_o in ignore_objects:
        pipped_io = "|" + i_o
        try:
            obj_names.remove(pipped_io)
        except:
            print("  skipped {}".format(pipped_io))

    # Delete left over object hierarchies
    dag_mod = om.MDagModifier()

    for name in obj_names:
        temp_sel = om.MSelectionList()
        temp_sel.add(name)

        if temp_sel.length() != 1:
            continue

        dag_path = temp_sel.getDagPath(0)
        dag_node = om.MFnDagNode(dag_path)
        dag_mod.deleteNode(dag_node.object())
        dag_mod.doIt()


def _parent_to_root(name):
    """
    As Maya's parent command can cause failures if you try and parent the object to 
    the same object it is already parented to. We check the parent, and only if it
    it not the world do we reparent the object.
    """
    temp_sel = om.MSelectionList()
    temp_sel.add(name)

    if temp_sel.length() != 1:
        return

    dag_path = temp_sel.getDagPath(0)
    dag_node = om.MFnDagNode(dag_path)
    parent_obj = dag_node.parent(0)
    parent_name = om.MFnDependencyNode(parent_obj).name()

    if parent_name == "world":
        return

    cmds.parent(name, world=True)

    temp_sel.clear()
    print("  Moved {} to scene root.".format(name))


def _get_dag_objects_under_scene_root():
    """
    Gets a list of all dag objects that direct children of the scene root.
    """
    # Create an MItDag iterator starting from the root of the scene
    dag_iter = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kInvalid)

    dag_objects = []

    while not dag_iter.isDone():
        current_dag_path = dag_iter.getPath()

        # Check if the current DAG path is under the scene root
        if current_dag_path.length() == 1:
            dag_objects.append(current_dag_path.fullPathName())

        # Move to the next DAG object
        dag_iter.next()

    return dag_objects


def _clean_namespaces(export_data):
    """
    Gets all available namespaces in scene.
    Checks each for objects that have it assigned.
    Removes the namespace from the object.
    """
    namespaces = _get_scene_namespaces()

    # Sort namespaces by longest nested first
    namespaces = sorted(namespaces, key=_count_namespaces, reverse=True)

    for namespace in namespaces:
        print("  - {}".format(namespace))
        child_namespaces = om.MNamespace.getNamespaces(namespace, True)

        for chld_ns in child_namespaces:
            m_objs = om.MNamespace.getNamespaceObjects(chld_ns)
            for m_obj in m_objs:
                _remove_namespace(m_obj)

        m_objs = om.MNamespace.getNamespaceObjects(namespace)
        for m_obj in m_objs:
            _remove_namespace(m_obj)

    filtered_export_data = _clean_export_namespaces(export_data)
    return filtered_export_data

def _clean_export_namespaces(export_data):
    """
    Looks at all the joints and mesh data in the export data and removes
    any namespaces that exists.
    """
    
    for key in export_data.keys():

        # ignore filepath, as it contains ':', which will break the path
        if key == "file_path" or key == "color":
            continue

        value = export_data[key]
        if isinstance(value, list):
            for i in range(len(value)):
                value[i] = _trim_namespace_from_name(value[i])
        elif isinstance(value, dict):
            value = _clean_export_namespaces(value)
        elif isinstance(value, str):
            value = _trim_namespace_from_name(value)

        export_data[key] = value

    return export_data

def _count_namespaces(name):
    # Custom function to count the number of ":" in a name
    return name.count(':')

def _trim_namespace_from_name(name):

    split_long_name = name.split("|")
    for i in range(len(split_long_name)):
        meta_name = split_long_name[i]
        if meta_name == "":
            continue
        if meta_name.find(":") >= 0:
            split_long_name[i] = meta_name.split(":")[-1]
    name = "|".join(split_long_name)
    return name

def _remove_namespace(mobj):
    """
    Removes the namesspace that is currently assigned to the asset
    """
    dg = om.MFnDependencyNode(mobj)
    name = dg.name()
    dg.setName(name[len(dg.namespace):])


def _get_scene_namespaces():
    """
    Gets all namespaces in the scene.
    """
    IGNORED_NAMESPACES = [":UI", ":shared", ":root"]
    spaces = om.MNamespace.getNamespaces(recurse=True)
    for ignored in IGNORED_NAMESPACES:
        if ignored in spaces:
            spaces.remove(ignored)

    return spaces


def _import_fbx(file_path):
    try:
        # Import FBX file
        name = cmds.file(file_path, i=True, type="FBX", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False,
                         namespace=":")

        print("FBX file imported successfully.")
        return name

    except Exception as e:
        print("Error importing FBX file:", e)
        return


def _get_joint_list(start_joint, end_joint):
    """Returns a list of joints between and including given start and end joint

    Args:
            start_joint str: start joint of joint list
            end_joint str end joint of joint list

    Returns:
            list[str]: joint list
    """

    sel_list = om.MSelectionList()

    # Tries to convert the start_joint into the full path
    try:
        sel_list.add(start_joint)
        dag_path = sel_list.getDagPath(0)
        full_path = dag_path.fullPathName()
        if start_joint != full_path:
            start_joint = full_path
        sel_list.clear()
    except:
        print("[Error] Start joint {}, could not be found".format(start_joint))
        return []

    # Tries to convert the end_joint into the full path
    try:
        sel_list.add(end_joint)
        dag_path = sel_list.getDagPath(0)
        full_end_joint = dag_path.fullPathName()
        if end_joint != full_end_joint:
            end_joint = full_end_joint
    except:
        print("[Error] End joint {}, could not be found".format(end_joint))
        return []

    if start_joint == end_joint:
        return [start_joint]

    # check hierarchy
    descendant_list = cmds.ls(
        cmds.listRelatives(start_joint, ad=True, fullPath=True),
        long=True,
        type="joint",
    )

    # if the end joint does not exist in the hierarch as the start joint, return
    if not descendant_list.count(end_joint):
        return list()

    joint_list = [end_joint]

    while joint_list[-1] != start_joint:
        parent_jnt = cmds.listRelatives(joint_list[-1], p=True, pa=True, fullPath=True)
        if not parent_jnt:
            raise Exception(
                'Found root joint while searching for start joint "{}"'.format(
                    start_joint
                )
            )
        joint_list.append(parent_jnt[0])

    joint_list.reverse()

    return joint_list


def _get_root_joint(start_joint):
    """
    Recursively traverses up the hierarchy until finding the first object that does not have a parent.

    :param str node_name: node name to get root of.
    :param str node_type: node type for the root node.
    :return: found root node.
    :rtype: str
    """

    parent = cmds.listRelatives(start_joint, parent=True, type="joint")
    parent = parent[0] if parent else None

    return _get_root_joint(parent) if parent else start_joint


def _get_all_mesh_dag_objects():
    """
    Gets all mesh dag objects in scene.

    Only returns DAG object and not the shape node.

    returns list of full path names
    """
    mesh_objects = []

    dag_iter = om.MItDag(om.MItDag.kBreadthFirst)

    while not dag_iter.isDone():
        current_dag_path = dag_iter.getPath()

        # Check if the current object has a mesh function set
        if current_dag_path.hasFn(om.MFn.kMesh):
            if current_dag_path.hasFn(om.MFn.kTransform):
                mesh_objects.append(current_dag_path.fullPathName())

        dag_iter.next()

    return mesh_objects


def _get_all_joint_dag_objects():
    """
    Gets all mesh dag objects in scene.

    Only returns DAG object and not the shape node.
    """
    mesh_objects = []

    dag_iter = om.MItDag(om.MItDag.kBreadthFirst)

    while not dag_iter.isDone():
        current_dag_path = dag_iter.getPath()

        # Check if the current object has a mesh function set
        if current_dag_path.hasFn(om.MFn.kJoint):
            if current_dag_path.hasFn(om.MFn.kTransform):
                mesh_objects.append(current_dag_path.fullPathName())

        dag_iter.next()

    return mesh_objects
