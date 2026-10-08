"""Find and match Maya nodes by name across namespaces and DAG paths.

Generic helpers used by IO tools (skin, curves, anim...) to resolve
exported node names against the current scene, and to propose matches
for missing nodes. Matchers are pure Python and return ``{source: target}``
proposals; callers decide how to combine or apply them.
"""

import difflib
import re

from maya import cmds

from mgear.core import string


def strip_namespace_path(path):
    """Remove the namespace from every segment of a DAG path.

    Args:
        path (str): Node name or DAG path, e.g. ``|a:grp|a:b:body``.

    Returns:
        str: The path without namespaces, e.g. ``|grp|body``.
    """
    return "|".join(seg.split(":")[-1] for seg in path.split("|"))


def short_name(path):
    """Return the namespace-stripped leaf name of a DAG path.

    Args:
        path (str): Node name or DAG path.

    Returns:
        str: The leaf name without namespace.
    """
    return strip_namespace_path(path).split("|")[-1]


def _ls(patterns, node_type=None, recursive=False):
    """List unique long names matching the patterns, ignoring bad patterns.

    Args:
        patterns (list): Name patterns for ``cmds.ls``.
        node_type (str, optional): Node type filter.
        recursive (bool, optional): Search in all namespaces.

    Returns:
        list: Unique full DAG paths (or node names for DG nodes).
    """
    kwargs = {"long": True}
    if node_type:
        kwargs["type"] = node_type
    if recursive:
        kwargs["recursive"] = True
    try:
        found = cmds.ls(*patterns, **kwargs) or []
    except (RuntimeError, ValueError):
        return []
    return list(dict.fromkeys(found))


def filter_by_path_suffix(paths, suffix):
    """Keep the paths whose namespace-stripped segments end with the suffix.

    Args:
        paths (list): Full DAG paths.
        suffix (str): Namespace-stripped partial or full path.

    Returns:
        list: The matching paths.
    """
    suffix_parts = [p for p in suffix.split("|") if p]
    if not suffix_parts:
        return list(paths)
    count = len(suffix_parts)
    return [
        p
        for p in paths
        if [s for s in strip_namespace_path(p).split("|") if s][-count:] == suffix_parts
    ]


def find_node_candidates(name, long_name=None, node_type=None, namespace=None):
    """Find the scene nodes that match an exported node name.

    The lookup stops at the first step that finds exactly one node:

    1. ``namespace`` remap of the stripped short name (if given).
    2. Exact name.
    3. ``long_name`` (or ``name`` if it is a partial path), namespaces
       stripped, matched as a path suffix.
    4. Stripped short name in any namespace.

    Args:
        name (str): Exported node name, may include namespace or path.
        long_name (str, optional): Exported full DAG path, used to
            disambiguate clashing short names.
        node_type (str, optional): Only return nodes of this type.
        namespace (str, optional): Force this namespace, e.g. ``"char:"``.
            Use ``""`` for the root namespace.

    Returns:
        list: Full paths. One item if resolved, several if ambiguous,
            empty if nothing matches.
    """
    leaf = short_name(name)

    if namespace is not None:
        ns = namespace.strip(":")
        target = "{}:{}".format(ns, leaf) if ns else leaf
        hits = _ls([target], node_type)
        if hits:
            return hits

    hits = _ls([name], node_type)
    if len(hits) == 1:
        return hits

    pool = _ls([leaf], node_type, recursive=True)
    if len(pool) <= 1:
        return pool

    suffix = long_name or (name if "|" in name else None)
    if suffix:
        matched = filter_by_path_suffix(pool, strip_namespace_path(suffix))
        if matched:
            return matched

    return pool


def group_by_short_name(paths):
    """Group node names or paths by namespace-stripped short name.

    Args:
        paths (list): Node names or DAG paths.

    Returns:
        dict: ``{short name: [paths]}``
    """
    index = {}
    for path in paths:
        index.setdefault(short_name(path), []).append(path)
    return index


def _unique_by_name(targets):
    """Index targets by namespace-stripped short name, dropping duplicates.

    Args:
        targets (list): Target node names or paths.

    Returns:
        dict: ``{short_name: target}`` for short names that are unique.
    """
    return {
        key: paths[0]
        for key, paths in group_by_short_name(targets).items()
        if len(paths) == 1
    }


def _match_by_rename(sources, targets, rename):
    """Propose matches by renaming each source and looking up the result.

    Args:
        sources (list): Source names to match.
        targets (list): Candidate target names or paths.
        rename (callable): Takes a namespace-stripped short name and
            returns the expected target short name.

    Returns:
        dict: ``{source: target}`` for sources with exactly one match.
    """
    index = _unique_by_name(targets)
    result = {}
    for source in sources:
        target = index.get(rename(short_name(source)))
        if target is not None:
            result[source] = target
    return result


def match_by_pattern(sources, targets, search, replace, regex=False):
    """Propose matches by applying a search/replace to source names.

    Args:
        sources (list): Source names to match.
        targets (list): Candidate target names or paths.
        search (str): Text or regex pattern to search for.
        replace (str): Replacement text.
        regex (bool, optional): Treat ``search`` as a regular expression.

    Returns:
        dict: ``{source: target}`` for sources with exactly one match.
    """
    if regex:
        pattern = re.compile(search)
        return _match_by_rename(
            sources, targets, lambda name: pattern.sub(replace, name)
        )
    return _match_by_rename(
        sources, targets, lambda name: name.replace(search, replace)
    )


def match_by_prefix(sources, targets, strip="", add=""):
    """Propose matches by stripping and/or adding a name prefix.

    Args:
        sources (list): Source names to match.
        targets (list): Candidate target names or paths.
        strip (str, optional): Prefix removed from source names.
        add (str, optional): Prefix added to source names.

    Returns:
        dict: ``{source: target}`` for sources with exactly one match.
    """
    search = "^" + re.escape(strip)
    return match_by_pattern(sources, targets, search, add, regex=True)


def match_by_side_swap(sources, targets):
    """Propose matches by swapping L/R side tokens in source names.

    Uses the mGear mirror naming rules, see ``string.convertRLName``.

    Args:
        sources (list): Source names to match.
        targets (list): Candidate target names or paths.

    Returns:
        dict: ``{source: target}`` for sources with exactly one match.
    """
    return _match_by_rename(sources, targets, string.convertRLName)


def match_by_similarity(sources, targets, cutoff=0.8):
    """Propose the most similar target name for each source.

    Args:
        sources (list): Source names to match.
        targets (list): Candidate target names or paths.
        cutoff (float, optional): Minimum similarity ratio, 0 to 1.

    Returns:
        dict: ``{source: target}`` for sources with a match over the cutoff.
    """
    index = _unique_by_name(targets)
    names = list(index)
    result = {}
    for source in sources:
        close = difflib.get_close_matches(short_name(source), names, n=1, cutoff=cutoff)
        if close:
            result[source] = index[close[0]]
    return result


def similar_names(name, targets, count=5, cutoff=0.6):
    """Return the targets whose short name is most similar to a name.

    Args:
        name (str): Name to compare, may include namespace or path.
        targets (list): Candidate target names or paths.
        count (int, optional): Maximum number of results.
        cutoff (float, optional): Minimum similarity ratio, 0 to 1.

    Returns:
        list: Targets, most similar first. Targets sharing a short name
            are all included.
    """
    index = group_by_short_name(targets)
    close = difflib.get_close_matches(
        short_name(name), list(index), n=count, cutoff=cutoff
    )
    return [target for key in close for target in index[key]][:count]


def match_by_position(source_positions, target_positions, tolerance=0.01):
    """Propose the nearest target for each source by world position.

    Args:
        source_positions (dict): ``{source: (x, y, z)}``.
        target_positions (dict): ``{target: (x, y, z)}``.
        tolerance (float, optional): Maximum distance in world units.

    Returns:
        dict: ``{source: target}`` for sources with a target in tolerance.
    """
    max_dist_sq = tolerance * tolerance
    result = {}
    for source, src_pos in source_positions.items():
        if not src_pos:
            continue
        best = None
        best_dist_sq = max_dist_sq
        sx, sy, sz = src_pos
        for target, (tx, ty, tz) in target_positions.items():
            dist_sq = (sx - tx) ** 2 + (sy - ty) ** 2 + (sz - tz) ** 2
            if dist_sq <= best_dist_sq:
                best = target
                best_dist_sq = dist_sq
        if best is not None:
            result[source] = best
    return result
