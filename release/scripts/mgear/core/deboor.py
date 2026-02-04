"""De Boor algorithm for NURBS basis function evaluation.

This module provides functions for computing B-spline basis functions using
the de Boor algorithm, as well as utilities for generating knot vectors.

These functions are used for wire deformer to skin cluster conversion and
other NURBS-based weight computations.

Example:
    >>> from mgear.core import deboor
    >>> kv = deboor.get_open_uniform_kv(5, 3)  # 5 CVs, degree 3
    >>> weights = deboor.deboor(5, 3, 0.5, kv)
    >>> print(sum(weights))  # Should be 1.0
"""


def get_open_uniform_kv(n, d):
    """Generate an open uniform knot vector for NURBS.

    An open uniform knot vector has multiplicity (d+1) at both ends,
    ensuring the curve passes through the first and last control points.

    Args:
        n (int): The number of control points.
        d (int): The degree of the NURBS curve.

    Returns:
        list: The open uniform knot vector of length (n + d + 1).

    Raises:
        TypeError: If n or d are not integers.
        ValueError: If n is not greater than d.

    Example:
        >>> get_open_uniform_kv(5, 3)
        [0, 0, 0, 0, 0.5, 1, 1, 1, 1]
    """
    if not isinstance(n, int) or not isinstance(d, int):
        raise TypeError("Both 'n' and 'd' must be integers.")
    if n <= d:
        raise ValueError("'n' must be greater than 'd'.")

    start = [0] * (d + 1)
    middle = [(i - d) / float(n - d) for i in range(d + 1, n)]
    end = [1] * (d + 1)

    return start + middle + end


def get_periodic_uniform_kv(n, d):
    """Generate a periodic uniform knot vector for NURBS.

    A periodic knot vector allows for closed/looping curves with
    uniform parameterization.

    Args:
        n (int): The number of control points.
        d (int): The degree of the NURBS curve.

    Returns:
        list: The periodic uniform knot vector.

    Raises:
        TypeError: If n or d are not integers.
        ValueError: If n is not greater than d.
    """
    if not isinstance(n, int) or not isinstance(d, int):
        raise TypeError("Both 'n' and 'd' must be integers.")
    if n <= d:
        raise ValueError("'n' must be greater than 'd'.")

    step = 1.0 / (n + d)
    return (
        [-step * i for i in range(d, 0, -1)]
        + [step * i for i in range(n + d + 1)]
        + [step * i + 1 for i in range(1, d + 1)]
    )


def knot_vector(kv_type, cvs, d):
    """Generate a knot vector and optionally modify control vertices.

    For periodic curves, this function also duplicates control vertices
    at the boundaries to create the wraparound effect.

    Args:
        kv_type (str): The type of knot vector, either "open" or "periodic".
        cvs (list): The control vertices.
        d (int): The degree of the NURBS curve.

    Returns:
        tuple: A tuple of (knot_vector, control_vertices) where control_vertices
            may be modified for periodic curves.

    Raises:
        ValueError: If kv_type is not 'open' or 'periodic'.
        TypeError: If cvs is not a list or d is not an integer.
    """
    if kv_type not in {"open", "periodic"}:
        raise ValueError("Invalid kv_type. Must be 'open' or 'periodic'.")
    if not isinstance(cvs, list):
        raise TypeError("'cvs' must be a list.")
    if not isinstance(d, int):
        raise TypeError("'d' must be an integer.")

    cvs_copy = cvs[:]

    if kv_type == "open":
        kv = get_open_uniform_kv(len(cvs), d)
    else:
        kv = get_periodic_uniform_kv(len(cvs), d)
        for i in range(d):
            cvs_copy.insert(0, cvs[len(cvs) - i - 1])
            cvs_copy.append(cvs[i])

    return kv, cvs_copy


def deboor(n, d, t, kv, tol=0.000001):
    """Evaluate the basis functions using the de Boor algorithm.

    Computes the weights (basis function values) for each control point
    at parameter t. The weights sum to 1.0 and can be used for skinning
    or other NURBS-based computations.

    Args:
        n (int): Number of control points.
        d (int): Degree of the NURBS curve.
        t (float): The parameter value to evaluate (0.0 to 1.0).
        kv (list): The knot vector of length (n + d + 1).
        tol (float): Tolerance for floating-point comparison. Defaults to 1e-6.

    Returns:
        list: The weights of the basis functions for each control point.

    Raises:
        TypeError: If parameters have incorrect types.
        ValueError: If knot vector length is invalid or t is out of range.

    Example:
        >>> kv = get_open_uniform_kv(5, 3)
        >>> weights = deboor(5, 3, 0.5, kv)
        >>> # weights[i] gives the influence of control point i at parameter 0.5
    """
    if not isinstance(n, int) or not isinstance(d, int):
        raise TypeError("Both 'n' and 'd' must be integers.")
    if not isinstance(t, (float, int)):
        raise TypeError("'t' must be a float or int.")
    if not isinstance(kv, list):
        raise TypeError("'kv' must be a list.")
    if len(kv) != n + d + 1:
        raise ValueError("Invalid knot vector length.")
    if t < 0 or t > 1:
        raise ValueError("'t' must be in the range [0, 1].")

    # Handle boundary case at t = 1
    if t + tol > 1:
        return [0.0 if i != n - 1 else 1.0 for i in range(n)]

    # Initialize basis functions - set 1.0 for the span containing t
    weights = [1.0 if kv[i] <= t < kv[i + 1] else 0.0 for i in range(n + d)]

    basis_width = n + d - 1

    # Build up basis functions from degree 0 to degree d
    for degree in range(1, d + 1):
        for i in range(basis_width):
            # Skip if both adjacent weights are zero (optimization)
            if weights[i] == 0 and weights[i + 1] == 0:
                continue

            a_denom = kv[i + degree] - kv[i]
            b_denom = kv[i + degree + 1] - kv[i + 1]

            a = (t - kv[i]) * weights[i] / a_denom if a_denom != 0 else 0.0
            b = (
                (kv[i + degree + 1] - t) * weights[i + 1] / b_denom
                if b_denom != 0
                else 0.0
            )

            weights[i] = a + b

        basis_width -= 1

    return weights[:n]


def find_knot_span(n, p, u, knots):
    """Find the knot span index for parameter u using binary search.

    Given a parameter value u, find the index i such that
    knots[i] <= u < knots[i+1].

    Args:
        n (int): Number of control points minus 1 (highest index).
        p (int): Degree of the curve.
        u (float): Parameter value to find span for.
        knots (list): Knot vector.

    Returns:
        int: Knot span index.

    Note:
        This function is useful when working with Maya's knot vector format
        directly, as it handles non-uniform knot vectors.
    """
    # Bounds check
    if len(knots) < n + p + 2:
        return p

    if u >= knots[n + 1]:
        return n
    if u <= knots[p]:
        return p

    low = p
    high = n + 1
    mid = (low + high) // 2

    max_iterations = 100  # Prevent infinite loop
    iteration = 0

    while (u < knots[mid] or u >= knots[mid + 1]) and iteration < max_iterations:
        if u < knots[mid]:
            high = mid
        else:
            low = mid
        mid = (low + high) // 2
        iteration += 1

        # Safety check
        if mid >= len(knots) - 1:
            return n
        if mid < p:
            return p

    return mid


def basis_functions(span, u, p, knots):
    """Compute all non-zero B-spline basis functions at parameter u.

    Given a knot span and parameter value, computes the (p+1) non-zero
    basis functions using the Cox-de Boor recursion formula.

    Args:
        span (int): The knot span index (from find_knot_span).
        u (float): Parameter value.
        p (int): Degree of the curve.
        knots (list): Knot vector.

    Returns:
        list: Array of (p+1) basis function values N[0] through N[p].

    Note:
        The returned values correspond to control points
        (span-p) through (span), with N[i] being the weight for
        control point (span - p + i).
    """
    N = [0.0] * (p + 1)
    left = [0.0] * (p + 1)
    right = [0.0] * (p + 1)

    N[0] = 1.0

    # Bounds check
    knot_len = len(knots)

    for j in range(1, p + 1):
        # Check indices are valid
        left_idx = span + 1 - j
        right_idx = span + j

        if left_idx < 0 or right_idx >= knot_len:
            # Fall back to uniform distribution
            for i in range(p + 1):
                N[i] = 1.0 / (p + 1)
            return N

        left[j] = u - knots[left_idx]
        right[j] = knots[right_idx] - u
        saved = 0.0

        for r in range(j):
            denom = right[r + 1] + left[j - r]
            if abs(denom) < 1e-10:
                temp = 0.0
            else:
                temp = N[r] / denom
            N[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp

        N[j] = saved

    return N
