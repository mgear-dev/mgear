import json
import os
import traceback

import maya.api.OpenMaya as om
import maya.cmds as cmds
import mgear.pymaya as pm

from mgear.shifter import io
from mgear.shifter import guide_manager

try:
    import pyblish.api
    import pyblish.util

    pyblish.api.register_host("maya")
    pyblish.api.register_gui("pyblish_lite")
    plugin_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "Pyblish_plugins"
    )
    pyblish.api.register_plugin_path(plugin_dir)

    PYBLISH_READY = True
    om.MGlobal.displayInfo("Successfully imported Pyblish.")
except:
    PYBLISH_READY = False
    om.MGlobal.displayWarning(
        "Could not setup Pyblish, disabling validator option."
    )


class RigBuilder(object):
    def __init__(self):
        self.results_dict = {}

    def run_validators(self):
        """Runs the Pyblish validators."""
        context = pyblish.util.collect()
        pyblish.util.validate(context)
        return context

    def build_results_dict(self, output_name, context):
        """Builds a nested dictionary containing Pyblish validator results for each rig.

        Args:
            output_name (str): name of the rig and its output file
            context: Pyblish context containing results data

        The dictionary is stored in self.results_dict with this structure:
            { rig_name: { check_name: { results } } }
        """
        self.results_dict[output_name] = {}
        results = context.data.get("results")

        for result in results:
            check_name = result.get("plugin").__name__
            instance = result.get("instance")
            success = result.get("success")
            error = result.get("error")
            self.results_dict[output_name][check_name] = {
                "instance": instance,
                "success": success,
                "error": error,
            }

    def format_report_header(self):
        """Creates the header for the validator report string."""
        header_string = "{:<10}{:<40}{:<80}".format(
            "Success", "Plug-in", "Instance"
        )
        header = "{}\n{}\n".format(header_string, "-" * 70)
        return header

    def generate_instance_report(self, output_name):
        """Appends the validator results of the specified rig to the report string.

        Args:
            output_name (str): name of the rig and its output file
        """
        result_string = (
            "{success:<10}{check_name:<40}{instance} - {output_name}"
        )
        error_string = "{:<10} > error: {:<80}"
        valid = True

        results = []
        checks_dict = self.results_dict.get(output_name)
        for check_name, check_data in checks_dict.items():
            results.append(
                result_string.format(
                    **check_data,
                    check_name=check_name,
                    output_name=output_name
                )
            )
            r_error = check_data.get("error")
            if r_error is not None:
                valid = False
                results.append(error_string.format("", str(r_error)))

        report_string = "\n".join(results)
        return valid, report_string

    def execute_build_logic(self, json_data, validate=True, passed_only=False):
        """
        Executes the rig building logic based on the provided JSON data.
        Optionally runs Pyblish validators on the builds.

        Args:
            json_data (str): A JSON string containing the necessary data
            validate (bool): Option to run Pyblish validators
            passed_only (bool): Option to publish only rigs that pass validation
        """
        if type(json_data) is str:
            data = json.loads(json_data)
        else:
            data = json_data

        data_rows = data.get("rows")
        if not data_rows:
            return
        for row in data_rows:
            # Continue with the logic only if file_path is provided
            file_path = row.get("file_path")
            if not file_path:
                return

            output_folder = data.get("output_folder")
            if not output_folder:
                output_folder = os.path.dirname(file_path)
            
            custom_output_path = row.get("custom_output_path")
            
            # if row has a custom path, override output folder with custom path
            if custom_output_path:
                print(f"custom output{custom_output_path}")
                output_folder = custom_output_path
                

            output_name = row.get("output_name")
            maya_file_name = "{}.ma".format(output_name)
            maya_file_path = os.path.join(output_folder, maya_file_name)

            pre_script_path = data.get("pre_script")
            if pre_script_path:
                io.import_guide_template(file_path)
                guide_root = cmds.ls("*.ismodel", objectsOnly=True, long=True)
                if guide_root:
                    guide_root = guide_root[0]
                    pm.displayInfo(
                        "Updating the guide with pre-script: {}".format(pre_script_path)
                    )
                    with open(pre_script_path, "r") as file:
                        try:
                            exec(file.read())
                        except Exception as e:
                            error_message = str(e)
                            full_traceback = traceback.format_exc()
                            pm.displayWarning(
                                "Update script failed, check error log"
                            )
                            pm.displayError(
                                "Exception message:", error_message
                            )
                            pm.displayError("Full traceback:", full_traceback)

                    pm.select(guide_root, r=True)
                    pm.displayInfo("Building rig '{}'...".format(output_name))
                    guide_manager.build_from_selection()
                    pm.delete(guide_root)
                else:
                    pm.displayWarning("Guide not found.")
            else:
                pm.displayInfo("Building rig '{}'...".format(output_name))
                io.build_from_file(file_path)

            post_script_path = data.get("post_script")
            
            if post_script_path:
                pm.displayInfo(
                        "Updating the guide with post-script: {}".format(post_script_path)
                    )
                with open(post_script_path, "r") as file:
                    try:
                        exec(file.read())
                    except Exception as e:
                        error_message = str(e)
                        full_traceback = traceback.format_exc()
                        pm.displayWarning(
                            "Update script failed, check error log"
                        )
                        pm.displayError(
                            "Exception message:", error_message
                        )
                        pm.displayError("Full traceback:", full_traceback)

            context = None
            save_build = True
            report_string = self.format_report_header()

            if PYBLISH_READY and validate:
                pm.displayInfo("Validating rig '{}'...\n".format(output_name))
                context = self.run_validators()
                self.build_results_dict(output_name, context)
                valid, report = self.generate_instance_report(output_name)

                report_string += "{}\n".format(report)
                if passed_only and not valid:
                    save_build = False
                    pm.displayInfo(
                        "Found errors, please fix and rebuild the rig."
                    )

                report_string += "{}\n".format(" -" * 35)

            cmds.file(rename=maya_file_path)
            cmds.file(save=save_build, type="mayaAscii")
            cmds.file(new=True, force=True)

        if validate:
            pm.displayInfo(report_string)

        return self.results_dict

    def build_from_file(self, file_path):
        json_data = self.load_config_data_from_file(file_path)
        self.execute_build_logic(json_data)

    @classmethod
    def write_config_data_to_file(cls, data_string):
        file_path = pm.fileDialog2(fileMode=0, fileFilter="*.srb")[0]
        if not file_path:
            return

        with open(file_path, "w") as fp:
            fp.write(data_string)

    @classmethod
    def load_config_data_from_file(cls, file_path=""):
        if not file_path:
            file_path = pm.fileDialog2(fileMode=1, fileFilter="*.srb")[0]

        if not file_path:
            return

        data = ""
        with open(file_path, "r") as fp:
            data = json.load(fp)

        return data
