/**
 * bindings.cpp -- pybind11 bindings for rgp_accel.
 *
 * Exposes functions to Python:
 *   - record_primary(...)        -> dict with vert_ids, ref_matrices, mirror_positions
 *   - record_mirror(...)         -> dict with vert_ids, ref_matrices
 *   - reposition_all_guides(...) -> list[float] (flat guide_count * 16)
 *
 * The GIL is released during heavy computation and re-acquired only when
 * calling the Python progress callback.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "rgp_accel.h"

namespace py = pybind11;


/**
 * Wrap a Python callable as a C++ ProgressCB that re-acquires the GIL
 * for each callback invocation.
 */
static rgp_accel::ProgressCB wrap_progress(py::object py_cb) {
    if (py_cb.is_none()) {
        return nullptr;
    }
    // Copy the py::object into the lambda (ref-counted)
    return [py_cb](int current, int total) {
        py::gil_scoped_acquire acquire;
        py_cb(current, total);
    };
}


PYBIND11_MODULE(_rgp_accel_cpp, m) {
    m.doc() = "C++ acceleration for mGear Relative Guide Placement "
              "(BFS flood-fill, centroid, reference matrix, repositioning)";

    // -----------------------------------------------------------------
    // record_primary
    // -----------------------------------------------------------------
    m.def("record_primary",
        [](const std::vector<double>& guide_positions,
           const std::vector<double>& guide_matrices,
           const std::vector<int>& seed_vert_ids,
           const std::vector<int>& seed_offsets,
           int sample_count,
           const std::vector<double>& points,
           const std::vector<double>& face_normals,
           const std::vector<int>& face_vert_counts,
           const std::vector<int>& face_vert_indices,
           int num_verts,
           py::object progress_cb) -> py::dict
        {
            auto cb = wrap_progress(progress_cb);

            rgp_accel::RecordPrimaryResult result;
            {
                // Release the GIL for heavy computation
                py::gil_scoped_release release;

                result = rgp_accel::record_primary(
                    guide_positions, guide_matrices,
                    seed_vert_ids, seed_offsets,
                    sample_count,
                    points, face_normals,
                    face_vert_counts, face_vert_indices,
                    num_verts, cb);
            }

            py::dict d;
            d["vert_ids"] = std::move(result.all_vert_ids);
            d["ref_matrices"] = std::move(result.all_ref_matrices);
            d["mirror_positions"] = std::move(result.all_mirror_positions);
            return d;
        },
        py::arg("guide_positions"),
        py::arg("guide_matrices"),
        py::arg("seed_vert_ids"),
        py::arg("seed_offsets"),
        py::arg("sample_count"),
        py::arg("points"),
        py::arg("face_normals"),
        py::arg("face_vert_counts"),
        py::arg("face_vert_indices"),
        py::arg("num_verts"),
        py::arg("progress_cb") = py::none(),
        "Record primary side for all guides (batch).\n\n"
        "Performs BFS flood-fill + reference matrix construction for\n"
        "each guide position. Returns dict with:\n"
        "  vert_ids: flat list of guide_count * sample_count ints\n"
        "  ref_matrices: flat list of guide_count * 16 doubles\n"
        "  mirror_positions: flat list of guide_count * 3 doubles"
    );

    // -----------------------------------------------------------------
    // record_mirror
    // -----------------------------------------------------------------
    m.def("record_mirror",
        [](const std::vector<int>& seed_vert_ids,
           const std::vector<int>& seed_offsets,
           int sample_count,
           const std::vector<double>& points,
           const std::vector<double>& face_normals,
           const std::vector<int>& face_vert_counts,
           const std::vector<int>& face_vert_indices,
           int num_verts,
           const std::vector<double>& mirror_positions,
           py::object progress_cb) -> py::dict
        {
            auto cb = wrap_progress(progress_cb);

            rgp_accel::RecordMirrorResult result;
            {
                py::gil_scoped_release release;

                result = rgp_accel::record_mirror(
                    seed_vert_ids, seed_offsets,
                    sample_count,
                    points, face_normals,
                    face_vert_counts, face_vert_indices,
                    num_verts, mirror_positions, cb);
            }

            py::dict d;
            d["vert_ids"] = std::move(result.all_vert_ids);
            d["ref_matrices"] = std::move(result.all_ref_matrices);
            return d;
        },
        py::arg("seed_vert_ids"),
        py::arg("seed_offsets"),
        py::arg("sample_count"),
        py::arg("points"),
        py::arg("face_normals"),
        py::arg("face_vert_counts"),
        py::arg("face_vert_indices"),
        py::arg("num_verts"),
        py::arg("mirror_positions"),
        py::arg("progress_cb") = py::none(),
        "Record mirror side for all guides (batch).\n\n"
        "Performs BFS flood-fill + reference matrix construction for\n"
        "each mirror position. Uses mirror_positions (reflected guide\n"
        "world positions) as the distance reference for vertex sorting,\n"
        "matching the Python path behavior.\n\n"
        "Returns dict with:\n"
        "  vert_ids: flat list of guide_count * sample_count ints\n"
        "  ref_matrices: flat list of guide_count * 16 doubles"
    );

    // -----------------------------------------------------------------
    // reposition_all_guides
    // -----------------------------------------------------------------
    m.def("reposition_all_guides",
        [](const std::vector<double>& node_matrices,
           const std::vector<double>& ref_matrices,
           const std::vector<double>& mr_ref_matrices,
           const std::vector<int>& vert_ids,
           const std::vector<int>& mr_vert_ids,
           int sample_count,
           const std::vector<double>& new_points,
           py::object progress_cb) -> std::vector<double>
        {
            auto cb = wrap_progress(progress_cb);

            py::gil_scoped_release release;

            return rgp_accel::reposition_all_guides(
                node_matrices, ref_matrices, mr_ref_matrices,
                vert_ids, mr_vert_ids,
                sample_count, new_points, cb);
        },
        py::arg("node_matrices"),
        py::arg("ref_matrices"),
        py::arg("mr_ref_matrices"),
        py::arg("vert_ids"),
        py::arg("mr_vert_ids"),
        py::arg("sample_count"),
        py::arg("new_points"),
        py::arg("progress_cb") = py::none(),
        "Reposition all guides given stored data and new mesh.\n\n"
        "Computes delta matrix * scale ratio * new center for each guide.\n"
        "Returns flat list of guide_count * 16 doubles (row-major matrices)."
    );
}
