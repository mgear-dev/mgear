import maya.cmds as cmds
import mgear.pymaya as pm
import maya.mel
import os
import sys

from mgear.core import string
from mgear.vendor.Qt import QtCore

# FBX wrapper section

# NOTE: pymel can use MEL commands directly
# for example:
#     pm.mel.FBXExport(f=path, s=True)
#
# But we will use this wrapper to ensure it will work if we remove pymel
# from mGear


# check if we have loaded the necessary plugins
if not pm.pluginInfo("fbxmaya", q=True, loaded=True):
    try:
        pm.loadPlugin("fbxmaya")
    except RuntimeError:
        pm.displayError("You need the fbxmaya.mll plugin!")


def _py_fbx(mel_cmd, *args, **kwargs):
    """Format python command to MEL

    NOTe: be carefull with the use of "" and '' for str

    Args:
        mel_cmd (str): Mel Command
        *args: Command Arguments
        **kwargs: KW arguments

    Returns:
        str: the result of the command execution
    """
    arg_string = ''
    kwargs_string = ''
    for a in args:
        if not isinstance(a, str):
            a = str(a)
        arg_string += ' {}'.format(a)

    for ka in kwargs.items():

        if ka[0] in ('q', 'query'):
            kwargs_string += ' -q'
        elif ka[0] in ('c', 'clear'):
            kwargs_string += ' -c'
        else:
            if isinstance(ka[1], str):
                argu = '{}'.format(string.normalize_path(ka[1]))
            else:
                argu = ka[1]

            if isinstance(argu, bool):
                if ka[1] is not None:
                    kwargs_string += ' -{} {}'.format(ka[0], str(argu).lower())
            elif isinstance(argu, int):
                kwargs_string += ' -{} {}'.format(ka[0], argu)
            else:
                kwargs_string += ' -{} "{}"'.format(ka[0], argu)

    mel_format_cmd = '{}{}{};'.format(mel_cmd, kwargs_string, arg_string)
    # print(mel_format_cmd)
    return maya.mel.eval(mel_format_cmd)


def FBXImport(*args, **kwargs):
    return _py_fbx("FBXImport", *args, **kwargs)


def FBXExport(*args, **kwargs):
    return _py_fbx("FBXExport", *args, **kwargs)


def FBXResetImport(*args, **kwargs):
    return _py_fbx("FBXResetImport", *args, **kwargs)


def FBXResetExport(*args, **kwargs):
    return _py_fbx("FBXResetExport", *args, **kwargs)


def FBXImportOCMerge(*args, **kwargs):
    return _py_fbx("FBXImportOCMerge", *args, **kwargs)


def FBXPushSettings(*args, **kwargs):
    return _py_fbx("FBXPushSettings", *args, **kwargs)


def FBXPopSettings(*args, **kwargs):
    return _py_fbx("FBXPopSettings", *args, **kwargs)


def FBXLoadImportPresetFile(*args, **kwargs):
    return _py_fbx("FBXLoadImportPresetFile", *args, **kwargs)


def FBXLoadExportPresetFile(*args, **kwargs):
    return _py_fbx("FBXLoadExportPresetFile", *args, **kwargs)


def FBXLoadMBImportPresetFile(*args, **kwargs):
    return _py_fbx("FBXLoadMBImportPresetFile", *args, **kwargs)


def FBXLoadMBExportPresetFile(*args, **kwargs):
    return _py_fbx("FBXLoadMBExportPresetFile", *args, **kwargs)


def FBXImportShowUI(*args, **kwargs):
    return _py_fbx("FBXImportShowUI", *args, **kwargs)


def FBXImportGenerateLog(*args, **kwargs):
    return _py_fbx("FBXImportGenerateLog", *args, **kwargs)


def FBXImportMode(*args, **kwargs):
    return _py_fbx("FBXImportMode", *args, **kwargs)


def FBXImportMergeBackNullPivots(*args, **kwargs):
    return _py_fbx("FBXImportMergeBackNullPivots", *args, **kwargs)


def FBXImportConvertDeformingNullsToJoint(*args, **kwargs):
    return _py_fbx("FBXImportConvertDeformingNullsToJoint", *args, **kwargs)


def FBXImportHardEdges(*args, **kwargs):
    return _py_fbx("FBXImportHardEdges", *args, **kwargs)


def FBXImportUnlockNormals(*args, **kwargs):
    return _py_fbx("FBXImportUnlockNormals", *args, **kwargs)


def FBXImportProtectDrivenKeys(*args, **kwargs):
    return _py_fbx("FBXImportProtectDrivenKeys", *args, **kwargs)


def FBXImportMergeAnimationLayers(*args, **kwargs):
    return _py_fbx("FBXImportMergeAnimationLayers", *args, **kwargs)


def FBXImportResamplingRateSource(*args, **kwargs):
    return _py_fbx("FBXImportResamplingRateSource", *args, **kwargs)


def FBXImportSetMayaFrameRate(*args, **kwargs):
    return _py_fbx("FBXImportSetMayaFrameRate", *args, **kwargs)


def FBXImportQuaternion(*args, **kwargs):
    return _py_fbx("FBXImportQuaternion", *args, **kwargs)


def FBXImportSetLockedAttribute(*args, **kwargs):
    return _py_fbx("FBXImportSetLockedAttribute", *args, **kwargs)


def FBXImportSetTake(*args, **kwargs):
    return _py_fbx("FBXImportSetTake", *args, **kwargs)


def FBXImportAxisConversionEnable(*args, **kwargs):
    return _py_fbx("FBXImportAxisConversionEnable", *args, **kwargs)


def FBXImportScaleFactor(*args, **kwargs):
    return _py_fbx("FBXImportScaleFactor", *args, **kwargs)


def FBXImportUpAxis(*args, **kwargs):
    return _py_fbx("FBXImportUpAxis", *args, **kwargs)


def FBXImportAutoAxisEnable(*args, **kwargs):
    return _py_fbx("FBXImportAutoAxisEnable", *args, **kwargs)


def FBXImportForcedFileAxis(*args, **kwargs):
    return _py_fbx("FBXImportForcedFileAxis", *args, **kwargs)


def FBXImportCacheFile(*args, **kwargs):
    return _py_fbx("FBXImportCacheFile", *args, **kwargs)


def FBXImportSkins(*args, **kwargs):
    return _py_fbx("FBXImportSkins", *args, **kwargs)


def FBXImportShapes(*args, **kwargs):
    return _py_fbx("FBXImportShapes", *args, **kwargs)


def FBXImportCameras(*args, **kwargs):
    return _py_fbx("FBXImportCameras", *args, **kwargs)


def FBXImportLights(*args, **kwargs):
    return _py_fbx("FBXImportLights", *args, **kwargs)


def FBXImportAudio(*args, **kwargs):
    return _py_fbx("FBXImportAudio", *args, **kwargs)


def FBXImportFillTimeline(*args, **kwargs):
    return _py_fbx("FBXImportFillTimeline", *args, **kwargs)


def FBXImportConstraints(*args, **kwargs):
    return _py_fbx("FBXImportConstraints", *args, **kwargs)


def FBXImportSkeletonDefinitionsAs(*args, **kwargs):
    return _py_fbx("FBXImportSkeletonDefinitionsAs", *args, **kwargs)


def FBXExportShowUI(*args, **kwargs):
    return _py_fbx("FBXExportShowUI", *args, **kwargs)


def FBXExportGenerateLog(*args, **kwargs):
    return _py_fbx("FBXExportGenerateLog", *args, **kwargs)


def FBXExportFileVersion(*args, **kwargs):
    return _py_fbx("FBXExportFileVersion", *args, **kwargs)


def FBXExportApplyConstantKeyReducer(*args, **kwargs):
    return _py_fbx("FBXExportApplyConstantKeyReducer", *args, **kwargs)


def FBXExportQuaternion(*args, **kwargs):
    return _py_fbx("FBXExportQuaternion", *args, **kwargs)


def FBXExportSkins(*args, **kwargs):
    return _py_fbx("FBXExportSkins", *args, **kwargs)


def FBXExportShapes(*args, **kwargs):
    return _py_fbx("FBXExportShapes", *args, **kwargs)


def FBXExportShapeAttributes(*args, **kwargs):
    return _py_fbx("FBXExportShapeAttributes", *args, **kwargs)


def FBXExportShapeAttributeValues(*args, **kwargs):
    return _py_fbx("FBXExportShapeAttributeValues", *args, **kwargs)


def FBXExportCameras(*args, **kwargs):
    return _py_fbx("FBXExportCameras", *args, **kwargs)


def FBXExportLights(*args, **kwargs):
    return _py_fbx("FBXExportLights", *args, **kwargs)


def FBXExportAudio(*args, **kwargs):
    return _py_fbx("FBXExportAudio", *args, **kwargs)


def FBXExportInstances(*args, **kwargs):
    return _py_fbx("FBXExportInstances", *args, **kwargs)


def FBXExportReferencedContainersContent(*args, **kwargs):
    return _py_fbx("FBXExportReferencedContainersContent", *args, **kwargs)


def FBXExportReferencedAssetsContent(*args, **kwargs):
    return _py_fbx("FBXExportReferencedAssetsContent", *args, **kwargs)


def FBXExportBakeComplexStart(*args, **kwargs):
    return _py_fbx("FBXExportBakeComplexStart", *args, **kwargs)


def FBXExportBakeComplexEnd(*args, **kwargs):
    return _py_fbx("FBXExportBakeComplexEnd", *args, **kwargs)


def FBXExportBakeComplexStep(*args, **kwargs):
    return _py_fbx("FBXExportBakeComplexStep", *args, **kwargs)


def FBXExportEmbeddedTextures(*args, **kwargs):
    return _py_fbx("FBXExportEmbeddedTextures", *args, **kwargs)


def FBXExportConvert2Tif(*args, **kwargs):
    return _py_fbx("FBXExportConvert2Tif", *args, **kwargs)


def FBXExportInAscii(*args, **kwargs):
    return _py_fbx("FBXExportInAscii", *args, **kwargs)


def FBXExportBakeComplexAnimation(*args, **kwargs):
    return _py_fbx("FBXExportBakeComplexAnimation", *args, **kwargs)


def FBXExportBakeResampleAnimation(*args, **kwargs):
    return _py_fbx("FBXExportBakeResampleAnimation", *args, **kwargs)


def FBXExportUseSceneName(*args, **kwargs):
    return _py_fbx("FBXExportUseSceneName", *args, **kwargs)


def FBXExportAnimationOnly(*args, **kwargs):
    return _py_fbx("FBXExportAnimationOnly", *args, **kwargs)


def FBXExportSplitAnimationIntoTakes(*args, **kwargs):
    return _py_fbx("FBXExportSplitAnimationIntoTakes", *args, **kwargs)


def FBXExportDeleteOriginalTakeOnSplitAnimation(*args, **kwargs):
    return _py_fbx(
        "FBXExportDeleteOriginalTakeOnSplitAnimation", *args, **kwargs
    )


def FBXExportHardEdges(*args, **kwargs):
    return _py_fbx("FBXExportHardEdges", *args, **kwargs)


def FBXExportTangents(*args, **kwargs):
    return _py_fbx("FBXExportTangents", *args, **kwargs)


def FBXExportSmoothMesh(*args, **kwargs):
    return _py_fbx("FBXExportSmoothMesh", *args, **kwargs)


def FBXExportSmoothingGroups(*args, **kwargs):
    return _py_fbx("FBXExportSmoothingGroups", *args, **kwargs)


def FBXExportFinestSubdivLevel(*args, **kwargs):
    return _py_fbx("FBXExportFinestSubdivLevel", *args, **kwargs)


def FBXExportInputConnections(*args, **kwargs):
    return _py_fbx("FBXExportInputConnections", *args, **kwargs)


def FBXExportIncludeChildren(*args, **kwargs):
    return _py_fbx("FBXExportIncludeChildren", *args, **kwargs)


def FBXExportConstraints(*args, **kwargs):
    return _py_fbx("FBXExportConstraints", *args, **kwargs)


def FBXExportSkeletonDefinitions(*args, **kwargs):
    return _py_fbx("FBXExportSkeletonDefinitions", *args, **kwargs)


def FBXExportCacheFile(*args, **kwargs):
    return _py_fbx("FBXExportCacheFile", *args, **kwargs)


def FBXExportQuickSelectSetAsCache(*args, **kwargs):
    return _py_fbx("FBXExportQuickSelectSetAsCache", *args, **kwargs)


def FBXExportTriangulate(*args, **kwargs):
    return _py_fbx("FBXExportTriangulate", *args, **kwargs)


def FBXExportColladaTriangulate(*args, **kwargs):
    return _py_fbx("FBXExportColladaTriangulate", *args, **kwargs)


def FBXExportColladaSingleMatrix(*args, **kwargs):
    return _py_fbx("FBXExportColladaSingleMatrix", *args, **kwargs)


def FBXExportColladaFrameRate(*args, **kwargs):
    return _py_fbx("FBXExportColladaFrameRate", *args, **kwargs)


def FBXResamplingRate(*args, **kwargs):
    return _py_fbx("FBXResamplingRate", *args, **kwargs)


def FBXRead(*args, **kwargs):
    return _py_fbx("FBXRead", *args, **kwargs)


def FBXClose(*args, **kwargs):
    return _py_fbx("FBXClose", *args, **kwargs)


def FBXGetTakeCount(*args, **kwargs):
    return _py_fbx("FBXGetTakeCount", *args, **kwargs)


def FBXGetTakeIndex(*args, **kwargs):
    return _py_fbx("FBXGetTakeIndex", *args, **kwargs)


def FBXGetTakeName(*args, **kwargs):
    return _py_fbx("FBXGetTakeName", *args, **kwargs)


def FBXGetTakeComment(*args, **kwargs):
    return _py_fbx("FBXGetTakeComment", *args, **kwargs)


def FBXGetTakeLocalTimeSpan(*args, **kwargs):
    return _py_fbx("FBXGetTakeLocalTimeSpan", *args, **kwargs)


def FBXGetTakeReferenceTimeSpan(*args, **kwargs):
    return _py_fbx("FBXGetTakeReferenceTimeSpan", *args, **kwargs)


def FBXImportConvertUnitString(*args, **kwargs):
    return _py_fbx("FBXImportConvertUnitString", *args, **kwargs)


def FBXExportConvertUnitString(*args, **kwargs):
    return _py_fbx("FBXExportConvertUnitString", *args, **kwargs)


def FBXExportAxisConversionMethod(*args, **kwargs):
    return _py_fbx("FBXExportAxisConversionMethod", *args, **kwargs)


def FBXExportUpAxis(*args, **kwargs):
    return _py_fbx("FBXExportUpAxis", *args, **kwargs)


def FBXExportScaleFactor(*args, **kwargs):
    return _py_fbx("FBXExportScaleFactor", *args, **kwargs)


def FBXProperties(*args, **kwargs):
    return _py_fbx("FBXProperties", *args, **kwargs)


def FBXProperty(*args, **kwargs):
    pm.displayWarning("This command is not yet supported in the wrapper")
    return


def FBXExportUseTmpFilePeripheral(*args, **kwargs):
    return _py_fbx("FBXExportUseTmpFilePeripheral", *args, **kwargs)


def FBXUICallBack(*args, **kwargs):
    return _py_fbx("FBXUICallBack", *args, **kwargs)


def FBXUIShowOptions(*args, **kwargs):
    return _py_fbx("FBXUIShowOptions", *args, **kwargs)


# Helper functions


def get_fbx_versions():
    """Get available FBX version list

    Returns:
        list: String names of the available fbx versions
    """

    return pm.mel.eval("FBXExportFileVersion -uivl;")


def get_fbx_export_presets():
    """Returns all available FBX export preset files

    Returns:
        list: String paths of the available fbx export preset files
    """

    paths_to_check = list()
    export_preset_files = list()

    # retrieve templates located in Maya installation folder
    default_path = os.environ.get('MAYA_LOCATION', None)
    if default_path and os.path.isdir(default_path):
        default_path = os.path.join(default_path, 'plug-ins', 'fbx', 'plug-ins', 'FBX', 'Presets', 'export')
        if os.path.isdir(default_path):
            paths_to_check.append(default_path)

    # retrieve user templates
    if cmds.pluginInfo('fbxmaya.mll', loaded=True, query=True):
        fbx_plugin_version = cmds.pluginInfo('fbxmaya.mll', version=True, query=True)
        user_path = os.path.join(pm.mel.eval('internalVar -userAppDir'), 'FBX', 'Presets', fbx_plugin_version, 'export')
        if user_path and os.path.isdir(user_path):
            paths_to_check.append(user_path)

    if not paths_to_check:
        return export_preset_files

    for path_to_check in paths_to_check:
        for file_name in os.listdir(path_to_check):
            _, file_extension = os.path.splitext(file_name)
            if not file_extension or file_extension != '.fbxexportpreset':
                continue
            export_preset_files.append(string.normalize_path(os.path.join(path_to_check, file_name)))

    return export_preset_files


def get_fbx_import_presets():
    """Returns all available FBX export preset files

    Returns:
        list: String paths of the available fbx export preset files
    """

    paths_to_check = list()
    import_preset_files = list()

    # retrieve templates located in Maya installation folder
    default_path = os.environ.get('MAYA_LOCATION', None)
    if default_path and os.path.isdir(default_path):
        default_path = os.path.join(default_path, 'plug-ins', 'fbx', 'plug-ins', 'FBX', 'Presets', 'import')
        if os.path.isdir(default_path):
            paths_to_check.append(default_path)

    # retrieve user templates
    if cmds.pluginInfo('fbxmaya.mll', loaded=True, query=True):
        fbx_plugin_version = cmds.pluginInfo('fbxmaya.mll', version=True, query=True)
        user_path = os.path.join(pm.mel.eval('internalVar -userAppDir'), 'FBX', 'Presets', fbx_plugin_version, 'import')
        if user_path and os.path.isdir(user_path):
            paths_to_check.append(user_path)

    if not paths_to_check:
        return

    for path_to_check in paths_to_check:
        for file_name in os.listdir(path_to_check):
            _, file_extension = os.path.splitext(file_name)
            if not file_extension or file_extension != '.fbximportpreset':
                continue
            import_preset_files.append(string.normalize_path(os.path.join(path_to_check, file_name)))

    return import_preset_files


# SNIPPETS
# docs https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2023/ENU/Maya-DataExchange/files/GUID-F48E3B78-3E56-4869-9914-CE0FAB6E3116-htm.html

# query and format all fbxmaya commands

"""
import mgear.pymaya as pm
cds = pm.pluginInfo( 'fbxmaya.mll', query=True, command=True )


final_str = ""
for c in cds:
    fun = r'''

def {0}(*args, **kwargs):
    return _py_fbx("{0}", *args, **kwargs)
'''.format(c)
    final_str += fun
print(final_str)
"""
