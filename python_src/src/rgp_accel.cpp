/**
 * rgp_accel.cpp -- C++ acceleration for mGear Relative Guide Placement.
 *
 * Pure math -- zero Maya API dependency.
 *
 * Ports the following Python functions to C++:
 *   - getClosestNVerticesFromTransform -> find_n_closest_vertices
 *   - getMultiVertexReferenceMatrix -> build_multi_vertex_ref_matrix
 *   - getOrient -> Mat4::from_position_and_normal
 *   - getRepositionMatrix -> reposition_single_guide
 *   - getCentroidFromVertexNames -> compute_centroid
 */

#include "rgp_accel.h"

namespace rgp_accel {

// -------------------------------------------------------------------------
// Topology helpers
// -------------------------------------------------------------------------

void build_adjacency(
    int num_verts,
    const std::vector<int>& face_vert_counts,
    const std::vector<int>& face_vert_indices,
    std::vector<int>& neighbor_offsets,
    std::vector<int>& neighbor_indices_out)
{
    // Build per-vertex neighbor sets
    std::vector<std::unordered_set<int>> adj(num_verts);

    int idx = 0;
    for (int f = 0; f < static_cast<int>(face_vert_counts.size()); ++f) {
        int count = face_vert_counts[f];
        for (int i = 0; i < count; ++i) {
            int v0 = face_vert_indices[idx + i];
            int v1 = face_vert_indices[idx + (i + 1) % count];
            adj[v0].insert(v1);
            adj[v1].insert(v0);
        }
        idx += count;
    }

    // Flatten to CSR-like format
    neighbor_offsets.resize(num_verts + 1);
    neighbor_offsets[0] = 0;
    for (int v = 0; v < num_verts; ++v) {
        neighbor_offsets[v + 1] = neighbor_offsets[v] +
                                  static_cast<int>(adj[v].size());
    }

    neighbor_indices_out.resize(neighbor_offsets[num_verts]);
    for (int v = 0; v < num_verts; ++v) {
        int offset = neighbor_offsets[v];
        int i = 0;
        for (int n : adj[v]) {
            neighbor_indices_out[offset + i] = n;
            ++i;
        }
        // Sort for deterministic ordering
        std::sort(neighbor_indices_out.begin() + offset,
                  neighbor_indices_out.begin() + neighbor_offsets[v + 1]);
    }
}


void build_vert_faces(
    int num_verts,
    const std::vector<int>& face_vert_counts,
    const std::vector<int>& face_vert_indices,
    std::vector<int>& vert_face_offsets,
    std::vector<int>& vert_face_indices_out)
{
    // Count faces per vertex
    std::vector<int> counts(num_verts, 0);
    int idx = 0;
    for (int f = 0; f < static_cast<int>(face_vert_counts.size()); ++f) {
        for (int i = 0; i < face_vert_counts[f]; ++i) {
            counts[face_vert_indices[idx + i]]++;
        }
        idx += face_vert_counts[f];
    }

    // Build offsets
    vert_face_offsets.resize(num_verts + 1);
    vert_face_offsets[0] = 0;
    for (int v = 0; v < num_verts; ++v) {
        vert_face_offsets[v + 1] = vert_face_offsets[v] + counts[v];
    }

    // Fill face indices
    vert_face_indices_out.resize(vert_face_offsets[num_verts]);
    std::vector<int> write_pos(num_verts, 0);
    idx = 0;
    for (int f = 0; f < static_cast<int>(face_vert_counts.size()); ++f) {
        for (int i = 0; i < face_vert_counts[f]; ++i) {
            int v = face_vert_indices[idx + i];
            vert_face_indices_out[vert_face_offsets[v] + write_pos[v]] = f;
            write_pos[v]++;
        }
        idx += face_vert_counts[f];
    }
}


// -------------------------------------------------------------------------
// BFS flood-fill
// -------------------------------------------------------------------------

std::vector<int> find_n_closest_vertices(
    const std::vector<int>& seed_verts,
    const Vec3& ref_pos,
    const std::vector<double>& points,
    int count,
    const std::vector<int>& neighbor_offsets,
    const std::vector<int>& neighbor_indices)
{
    // BFS from seed vertices, collecting distance-sorted results
    std::unordered_set<int> visited(seed_verts.begin(), seed_verts.end());
    std::vector<int> frontier(seed_verts.begin(), seed_verts.end());

    // Collect (distance, vertex_id) pairs
    std::vector<std::pair<double, int>> collected;
    collected.reserve(count * 2);

    for (int vtx_id : frontier) {
        Vec3 vpos(points[vtx_id * 3], points[vtx_id * 3 + 1],
                  points[vtx_id * 3 + 2]);
        double d = distance(ref_pos, vpos);
        collected.push_back({d, vtx_id});
    }

    while (static_cast<int>(collected.size()) < count && !frontier.empty()) {
        std::vector<int> next_frontier;
        for (int vtx_id : frontier) {
            int start = neighbor_offsets[vtx_id];
            int end = neighbor_offsets[vtx_id + 1];
            for (int ni = start; ni < end; ++ni) {
                int n_id = neighbor_indices[ni];
                if (visited.find(n_id) == visited.end()) {
                    visited.insert(n_id);
                    next_frontier.push_back(n_id);
                    Vec3 vpos(points[n_id * 3], points[n_id * 3 + 1],
                              points[n_id * 3 + 2]);
                    double d = distance(ref_pos, vpos);
                    collected.push_back({d, n_id});
                }
            }
        }
        frontier = std::move(next_frontier);
    }

    // Sort by distance
    std::sort(collected.begin(), collected.end());

    // Return up to 'count' closest
    int result_count = std::min(count, static_cast<int>(collected.size()));
    std::vector<int> result(result_count);
    for (int i = 0; i < result_count; ++i) {
        result[i] = collected[i].second;
    }
    return result;
}


// -------------------------------------------------------------------------
// Multi-vertex reference matrix
// -------------------------------------------------------------------------

Vec3 compute_centroid(
    const std::vector<int>& vert_indices,
    const std::vector<double>& points)
{
    Vec3 centroid;
    for (int vi : vert_indices) {
        centroid.x += points[vi * 3];
        centroid.y += points[vi * 3 + 1];
        centroid.z += points[vi * 3 + 2];
    }
    double inv_count = 1.0 / static_cast<double>(vert_indices.size());
    centroid.x *= inv_count;
    centroid.y *= inv_count;
    centroid.z *= inv_count;
    return centroid;
}


Mat4 build_multi_vertex_ref_matrix(
    const std::vector<int>& vert_indices,
    const std::vector<double>& points,
    const std::vector<double>& face_normals,
    const std::vector<int>& vert_face_offsets,
    const std::vector<int>& vert_face_indices)
{
    // Compute centroid
    Vec3 centroid = compute_centroid(vert_indices, points);

    // Average face normals across all faces connected to all vertices
    Vec3 avg_normal;
    std::unordered_set<int> face_set;

    for (int vi : vert_indices) {
        int start = vert_face_offsets[vi];
        int end = vert_face_offsets[vi + 1];
        for (int fi = start; fi < end; ++fi) {
            int face_idx = vert_face_indices[fi];
            if (face_set.find(face_idx) == face_set.end()) {
                face_set.insert(face_idx);
                avg_normal.x += face_normals[face_idx * 3];
                avg_normal.y += face_normals[face_idx * 3 + 1];
                avg_normal.z += face_normals[face_idx * 3 + 2];
            }
        }
    }

    avg_normal = avg_normal.normalized();

    // Build 4x4 matrix from position and normal
    return Mat4::from_position_and_normal(centroid, avg_normal);
}


// -------------------------------------------------------------------------
// Single guide repositioning (C++ port of getRepositionMatrix)
// -------------------------------------------------------------------------

static Mat4 reposition_single_guide(
    const Mat4& node_matrix,
    const Mat4& orig_ref_matrix,
    const Mat4& mr_orig_ref_matrix,
    const std::vector<int>& vert_ids,
    const std::vector<int>& mr_vert_ids,
    int sample_count,
    const std::vector<double>& new_points)
{
    // Compute current centroids from new mesh positions
    Vec3 current_pos = compute_centroid(vert_ids, new_points);
    Vec3 mr_current_pos = compute_centroid(mr_vert_ids, new_points);

    // Distance between primary and mirror
    double current_length = distance(current_pos, mr_current_pos);

    // Original distances
    Vec3 orig_translate = orig_ref_matrix.translation();
    Vec3 mr_orig_translate = mr_orig_ref_matrix.translation();
    double orig_length = distance(orig_translate, mr_orig_translate);

    // Original center
    Vec3 orig_center = midpoint(orig_translate, mr_orig_translate);
    Mat4 orig_center_matrix;
    orig_center_matrix.set_translation(orig_center);

    // Current center
    Vec3 current_center = midpoint(current_pos, mr_current_pos);

    // Scale ratio
    double length_percentage = 1.0;
    if (current_length != 0.0 || orig_length != 0.0) {
        length_percentage = current_length / orig_length;
    }

    // Build reposition matrix
    Mat4 ref_position_matrix;
    ref_position_matrix.set_translation(current_center);

    // deltaMatrix = node_matrix * orig_center_matrix.inverse()
    Mat4 delta_matrix = node_matrix * orig_center_matrix.inverse();

    // deltaMatrix *= length_percentage
    // Python multiplies all 16 elements, but Maya's TransformationMatrix
    // normalizes by d[15] when decomposing, effectively undoing the scale
    // on translation and d[15]. We replicate that by scaling, then
    // normalizing (which fixes 3x3 + resets d[15]=1 + divides translation
    // by the pre-normalize d[15]).
    delta_matrix = delta_matrix * length_percentage;

    // Normalize scale (setMatrixScale) — also handles d[15] normalization
    delta_matrix.normalize_scale();

    // refPosition_matrix = deltaMatrix * refPosition_matrix
    Mat4 result = delta_matrix * ref_position_matrix;

    return result;
}


// -------------------------------------------------------------------------
// Batch operations
// -------------------------------------------------------------------------

RecordPrimaryResult record_primary(
    const std::vector<double>& guide_positions,
    const std::vector<double>& guide_matrices,
    const std::vector<int>& seed_vert_ids,
    const std::vector<int>& seed_offsets,
    int sample_count,
    const std::vector<double>& points,
    const std::vector<double>& face_normals,
    const std::vector<int>& face_vert_counts,
    const std::vector<int>& face_vert_indices,
    int num_verts,
    ProgressCB progress_cb)
{
    int guide_count = static_cast<int>(guide_positions.size()) / 3;

    // Pre-build topology
    std::vector<int> neighbor_offsets;
    std::vector<int> neighbor_indices;
    build_adjacency(num_verts, face_vert_counts, face_vert_indices,
                    neighbor_offsets, neighbor_indices);

    std::vector<int> vert_face_offsets;
    std::vector<int> vert_face_indices;
    build_vert_faces(num_verts, face_vert_counts, face_vert_indices,
                     vert_face_offsets, vert_face_indices);

    RecordPrimaryResult result;
    result.all_vert_ids.resize(guide_count * sample_count);
    result.all_ref_matrices.resize(guide_count * 16);
    result.all_mirror_positions.resize(guide_count * 3);

    for (int g = 0; g < guide_count; ++g) {
        // Guide position
        Vec3 gpos(guide_positions[g * 3],
                  guide_positions[g * 3 + 1],
                  guide_positions[g * 3 + 2]);

        // Get seed vertices for this guide (from Python's getClosestPoint)
        int seed_start = seed_offsets[g];
        int seed_end = seed_offsets[g + 1];
        std::vector<int> seeds(
            seed_vert_ids.begin() + seed_start,
            seed_vert_ids.begin() + seed_end);

        // BFS flood-fill to find N closest vertices
        std::vector<int> closest = find_n_closest_vertices(
            seeds, gpos, points, sample_count,
            neighbor_offsets, neighbor_indices);

        // Store vertex IDs
        for (int i = 0; i < sample_count; ++i) {
            if (i < static_cast<int>(closest.size())) {
                result.all_vert_ids[g * sample_count + i] = closest[i];
            } else {
                // Pad with last if BFS didn't find enough
                result.all_vert_ids[g * sample_count + i] =
                    closest.empty() ? 0 : closest.back();
            }
        }

        // Build reference matrix
        Mat4 ref_mat = build_multi_vertex_ref_matrix(
            closest, points, face_normals,
            vert_face_offsets, vert_face_indices);

        // Store reference matrix (flat 16)
        for (int i = 0; i < 16; ++i) {
            result.all_ref_matrices[g * 16 + i] = ref_mat.d[i];
        }

        // Compute mirror position: mm = ((ref_mat - guide_mat) * -1) + guide_mat
        // This mirrors the guide position through the reference matrix
        const double* gm = &guide_matrices[g * 16];
        Mat4 guide_mat;
        for (int i = 0; i < 16; ++i) guide_mat.d[i] = gm[i];

        Mat4 diff = ref_mat - guide_mat;
        Mat4 neg_diff = diff * -1.0;
        Mat4 mm = neg_diff + guide_mat;

        // Mirror position is row 3, columns 0-2
        result.all_mirror_positions[g * 3]     = mm.d[12];
        result.all_mirror_positions[g * 3 + 1] = mm.d[13];
        result.all_mirror_positions[g * 3 + 2] = mm.d[14];

        if (progress_cb) {
            progress_cb(g + 1, guide_count);
        }
    }

    return result;
}


RecordMirrorResult record_mirror(
    const std::vector<int>& seed_vert_ids,
    const std::vector<int>& seed_offsets,
    int sample_count,
    const std::vector<double>& points,
    const std::vector<double>& face_normals,
    const std::vector<int>& face_vert_counts,
    const std::vector<int>& face_vert_indices,
    int num_verts,
    const std::vector<double>& mirror_positions,
    ProgressCB progress_cb)
{
    int guide_count = static_cast<int>(seed_offsets.size()) - 1;

    // Pre-build topology (same mesh, reuse if possible but since we're
    // called separately, build here)
    std::vector<int> neighbor_offsets;
    std::vector<int> neighbor_indices;
    build_adjacency(num_verts, face_vert_counts, face_vert_indices,
                    neighbor_offsets, neighbor_indices);

    std::vector<int> vert_face_offsets;
    std::vector<int> vert_face_indices;
    build_vert_faces(num_verts, face_vert_counts, face_vert_indices,
                     vert_face_offsets, vert_face_indices);

    RecordMirrorResult result;
    result.all_vert_ids.resize(guide_count * sample_count);
    result.all_ref_matrices.resize(guide_count * 16);

    for (int g = 0; g < guide_count; ++g) {
        // Get seed vertices for this mirror position
        int seed_start = seed_offsets[g];
        int seed_end = seed_offsets[g + 1];
        std::vector<int> seeds(
            seed_vert_ids.begin() + seed_start,
            seed_vert_ids.begin() + seed_end);

        // Use the reflected guide position for distance sorting.
        // This matches the Python path which passes the exact mirror
        // world-space position to getClosestNVerticesFromTransform().
        Vec3 ref_pos(mirror_positions[g * 3],
                     mirror_positions[g * 3 + 1],
                     mirror_positions[g * 3 + 2]);

        // BFS flood-fill
        std::vector<int> closest = find_n_closest_vertices(
            seeds, ref_pos, points, sample_count,
            neighbor_offsets, neighbor_indices);

        // Store vertex IDs
        for (int i = 0; i < sample_count; ++i) {
            if (i < static_cast<int>(closest.size())) {
                result.all_vert_ids[g * sample_count + i] = closest[i];
            } else {
                result.all_vert_ids[g * sample_count + i] =
                    closest.empty() ? 0 : closest.back();
            }
        }

        // Build reference matrix
        Mat4 ref_mat = build_multi_vertex_ref_matrix(
            closest, points, face_normals,
            vert_face_offsets, vert_face_indices);

        // Store reference matrix
        for (int i = 0; i < 16; ++i) {
            result.all_ref_matrices[g * 16 + i] = ref_mat.d[i];
        }

        if (progress_cb) {
            progress_cb(g + 1, guide_count);
        }
    }

    return result;
}


std::vector<double> reposition_all_guides(
    const std::vector<double>& node_matrices,
    const std::vector<double>& ref_matrices,
    const std::vector<double>& mr_ref_matrices,
    const std::vector<int>& vert_ids,
    const std::vector<int>& mr_vert_ids,
    int sample_count,
    const std::vector<double>& new_points,
    ProgressCB progress_cb)
{
    int guide_count = static_cast<int>(node_matrices.size()) / 16;

    std::vector<double> results(guide_count * 16);

    for (int g = 0; g < guide_count; ++g) {
        // Unpack matrices
        Mat4 node_mat;
        Mat4 ref_mat;
        Mat4 mr_ref_mat;
        for (int i = 0; i < 16; ++i) {
            node_mat.d[i] = node_matrices[g * 16 + i];
            ref_mat.d[i] = ref_matrices[g * 16 + i];
            mr_ref_mat.d[i] = mr_ref_matrices[g * 16 + i];
        }

        // Extract vertex indices for this guide
        std::vector<int> guide_verts(
            vert_ids.begin() + g * sample_count,
            vert_ids.begin() + (g + 1) * sample_count);
        std::vector<int> guide_mr_verts(
            mr_vert_ids.begin() + g * sample_count,
            mr_vert_ids.begin() + (g + 1) * sample_count);

        // Reposition
        Mat4 repo_mat = reposition_single_guide(
            node_mat, ref_mat, mr_ref_mat,
            guide_verts, guide_mr_verts,
            sample_count, new_points);

        // Store result
        for (int i = 0; i < 16; ++i) {
            results[g * 16 + i] = repo_mat.d[i];
        }

        if (progress_cb) {
            progress_cb(g + 1, guide_count);
        }
    }

    return results;
}

}  // namespace rgp_accel
