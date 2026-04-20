"""混合形状传输 - 配置 I/O 和执行包装器。

处理保存/加载 .bst 配置文件，并提供
从配置运行 transfer_blendshapes 的便捷包装器。
"""

import datetime
import getpass
import json

from maya import cmds

from mgear.core import blendshape


# Config file extension
BST_EXT = ".bst"


def export_config(
    filepath, target, sources, bs_node_name=None,
    reconnect=True, metadata=None,
):
    """将混合形状传输配置保存到磁盘。

    参数：
        filepath (str): 保存 .bst JSON 文件的路径。
        target (str): 目标网格名称。
        sources (list): 源网格名称列表。
        bs_node_name (str, 可选): BlendShape 节点名称。
        reconnect (bool, 可选): 重新连接标志。
        metadata (dict, 可选): 额外的元数据字段
            （名称、描述、标签）。

    返回：
        bool: 成功时返回 True。
    """
    meta = metadata or {}
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    config = {
        "version": 1,
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "author": meta.get("author", getpass.getuser()),
        "date": now,
        "tags": meta.get("tags", []),
        "target_mesh": target,
        "source_meshes": list(sources),
        "bs_node_name": bs_node_name or "",
        "reconnect": reconnect,
    }

    try:
        with open(filepath, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except (IOError, OSError) as e:
        cmds.warning(
            "导出配置失败：{}".format(e)
        )
        return False


def import_config(filepath):
    """从磁盘加载混合形状传输配置。

    参数：
        filepath (str): .bst JSON 文件的路径。

    返回：
        dict: 配置字典，失败时返回 None。
    """
    try:
        with open(filepath, "r") as f:
            config = json.load(f)
        return config
    except (IOError, ValueError, OSError) as e:
        cmds.warning(
            "导入配置失败：{}".format(e)
        )
        return None


def run_from_config(config):
    """从配置字典执行混合形状传输。

    参数：
        config (dict): 包含 ``target_mesh``、``source_meshes`` 以及可选的
            ``bs_node_name`` 和 ``reconnect`` 的配置。

    返回：
        str: 创建的 blendShape 节点名称，或 None。
    """
    target = config.get("target_mesh")
    sources = config.get("source_meshes", [])

    if not target or not sources:
        cmds.warning(
            "配置必须包含 target_mesh 和 source_meshes"
        )
        return None

    bs_name = config.get("bs_node_name") or None
    reconnect = config.get("reconnect", True)

    return blendshape.transfer_blendshapes(
        sources=sources,
        target=target,
        bs_node_name=bs_name,
        reconnect=reconnect,
    )
