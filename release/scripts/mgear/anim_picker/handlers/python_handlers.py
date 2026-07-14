import mgear


def safe_code_exec(cmd, env=None):
    """Safely execute code in new namespace with specified dictionary"""
    if env is None:
        env = {}
    try:
        exec(cmd, env)
    except Exception as e:
        mgear.log(
            "anim_picker: custom action failed: {}".format(e),
            mgear.sev_error,
        )
