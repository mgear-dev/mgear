#pragma once
/**
 * rgp_accel.h -- C++ acceleration for mGear Relative Guide Placement.
 *
 * Provides:
 *   - Vec3:  trivial 3-vector helper
 *   - Mat4:  row-major double[16] 4x4 matrix
 *   - Mesh topology helpers (adjacency, BFS flood-fill)
 *   - Multi-vertex reference matrix construction
 *   - Guide recording (primary + mirror) and repositioning
 *
 * Pure math -- zero Maya API dependency.
 */

#include <vector>
#include <cmath>
#include <algorithm>
#include <functional>
#include <cstring>
#include <numeric>
#include <cstdio>
#include <queue>
#include <unordered_set>

namespace rgp_accel {

// -------------------------------------------------------------------------
// Progress callback type
// -------------------------------------------------------------------------
using ProgressCB = std::function<void(int current, int total)>;

// -------------------------------------------------------------------------
// Vec3
// -------------------------------------------------------------------------

struct Vec3 {
    double x, y, z;

    Vec3() : x(0), y(0), z(0) {}
    Vec3(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}

    Vec3 operator+(const Vec3& o) const { return {x + o.x, y + o.y, z + o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x - o.x, y - o.y, z - o.z}; }
    Vec3 operator*(double s) const { return {x * s, y * s, z * s}; }
    Vec3& operator+=(const Vec3& o) { x += o.x; y += o.y; z += o.z; return *this; }
    Vec3 operator-() const { return {-x, -y, -z}; }

    double dot(const Vec3& o) const { return x * o.x + y * o.y + z * o.z; }
    Vec3 cross(const Vec3& o) const {
        return {y * o.z - z * o.y,
                z * o.x - x * o.z,
                x * o.y - y * o.x};
    }
    double length() const { return std::sqrt(x * x + y * y + z * z); }
    double length_sq() const { return x * x + y * y + z * z; }
    Vec3 normalized() const {
        double len = length();
        if (len < 1e-30) return {0, 0, 0};
        double inv = 1.0 / len;
        return {x * inv, y * inv, z * inv};
    }

    double operator[](int i) const {
        if (i == 0) return x;
        if (i == 1) return y;
        return z;
    }
};

inline Vec3 lerp(const Vec3& a, const Vec3& b, double t) {
    return {a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
            a.z + (b.z - a.z) * t};
}

// -------------------------------------------------------------------------
// Mat4  --  row-major double[16]
// -------------------------------------------------------------------------

struct Mat4 {
    double d[16];

    Mat4() : d{1, 0, 0, 0,
               0, 1, 0, 0,
               0, 0, 1, 0,
               0, 0, 0, 1} {}  // identity

    static Mat4 zero() {
        Mat4 m;
        std::memset(m.d, 0, sizeof(m.d));
        return m;
    }

    double& operator()(int r, int c) { return d[r * 4 + c]; }
    double operator()(int r, int c) const { return d[r * 4 + c]; }

    // Extract translation (row 3, columns 0-2)
    Vec3 translation() const { return {d[12], d[13], d[14]}; }

    // Set translation (row 3, columns 0-2)
    void set_translation(const Vec3& t) {
        d[12] = t.x; d[13] = t.y; d[14] = t.z;
    }

    // Extract a row as Vec3 (first 3 elements)
    Vec3 row3(int r) const {
        return {d[r * 4 + 0], d[r * 4 + 1], d[r * 4 + 2]};
    }

    // Mat4 * Mat4
    Mat4 operator*(const Mat4& o) const {
        Mat4 m = Mat4::zero();
        for (int r = 0; r < 4; ++r)
            for (int c = 0; c < 4; ++c)
                for (int k = 0; k < 4; ++k)
                    m.d[r * 4 + c] += d[r * 4 + k] * o.d[k * 4 + c];
        return m;
    }

    // Mat4 * scalar
    Mat4 operator*(double s) const {
        Mat4 m;
        for (int i = 0; i < 16; ++i)
            m.d[i] = d[i] * s;
        return m;
    }

    // Mat4 + Mat4
    Mat4 operator+(const Mat4& o) const {
        Mat4 m;
        for (int i = 0; i < 16; ++i)
            m.d[i] = d[i] + o.d[i];
        return m;
    }

    // Mat4 - Mat4
    Mat4 operator-(const Mat4& o) const {
        Mat4 m;
        for (int i = 0; i < 16; ++i)
            m.d[i] = d[i] - o.d[i];
        return m;
    }

    // 4x4 inverse using cofactor expansion
    Mat4 inverse() const {
        Mat4 inv;
        const double* m = d;

        inv.d[0] = m[5]*m[10]*m[15] - m[5]*m[11]*m[14] - m[9]*m[6]*m[15] +
                   m[9]*m[7]*m[14] + m[13]*m[6]*m[11] - m[13]*m[7]*m[10];
        inv.d[4] = -m[4]*m[10]*m[15] + m[4]*m[11]*m[14] + m[8]*m[6]*m[15] -
                   m[8]*m[7]*m[14] - m[12]*m[6]*m[11] + m[12]*m[7]*m[10];
        inv.d[8] = m[4]*m[9]*m[15] - m[4]*m[11]*m[13] - m[8]*m[5]*m[15] +
                   m[8]*m[7]*m[13] + m[12]*m[5]*m[11] - m[12]*m[7]*m[9];
        inv.d[12] = -m[4]*m[9]*m[14] + m[4]*m[10]*m[13] + m[8]*m[5]*m[14] -
                    m[8]*m[6]*m[13] - m[12]*m[5]*m[10] + m[12]*m[6]*m[9];

        double det = m[0]*inv.d[0] + m[1]*inv.d[4] + m[2]*inv.d[8] + m[3]*inv.d[12];
        if (std::abs(det) < 1e-30) {
            return Mat4();  // identity fallback
        }
        double inv_det = 1.0 / det;

        inv.d[1] = -m[1]*m[10]*m[15] + m[1]*m[11]*m[14] + m[9]*m[2]*m[15] -
                   m[9]*m[3]*m[14] - m[13]*m[2]*m[11] + m[13]*m[3]*m[10];
        inv.d[5] = m[0]*m[10]*m[15] - m[0]*m[11]*m[14] - m[8]*m[2]*m[15] +
                   m[8]*m[3]*m[14] + m[12]*m[2]*m[11] - m[12]*m[3]*m[10];
        inv.d[9] = -m[0]*m[9]*m[15] + m[0]*m[11]*m[13] + m[8]*m[1]*m[15] -
                   m[8]*m[3]*m[13] - m[12]*m[1]*m[11] + m[12]*m[3]*m[9];
        inv.d[13] = m[0]*m[9]*m[14] - m[0]*m[10]*m[13] - m[8]*m[1]*m[14] +
                    m[8]*m[2]*m[13] + m[12]*m[1]*m[10] - m[12]*m[2]*m[9];

        inv.d[2] = m[1]*m[6]*m[15] - m[1]*m[7]*m[14] - m[5]*m[2]*m[15] +
                   m[5]*m[3]*m[14] + m[13]*m[2]*m[7] - m[13]*m[3]*m[6];
        inv.d[6] = -m[0]*m[6]*m[15] + m[0]*m[7]*m[14] + m[4]*m[2]*m[15] -
                   m[4]*m[3]*m[14] - m[12]*m[2]*m[7] + m[12]*m[3]*m[6];
        inv.d[10] = m[0]*m[5]*m[15] - m[0]*m[7]*m[13] - m[4]*m[1]*m[15] +
                    m[4]*m[3]*m[13] + m[12]*m[1]*m[7] - m[12]*m[3]*m[5];
        inv.d[14] = -m[0]*m[5]*m[14] + m[0]*m[6]*m[13] + m[4]*m[1]*m[14] -
                    m[4]*m[2]*m[13] - m[12]*m[1]*m[6] + m[12]*m[2]*m[5];

        inv.d[3] = -m[1]*m[6]*m[11] + m[1]*m[7]*m[10] + m[5]*m[2]*m[11] -
                   m[5]*m[3]*m[10] - m[9]*m[2]*m[7] + m[9]*m[3]*m[6];
        inv.d[7] = m[0]*m[6]*m[11] - m[0]*m[7]*m[10] - m[4]*m[2]*m[11] +
                   m[4]*m[3]*m[10] + m[8]*m[2]*m[7] - m[8]*m[3]*m[6];
        inv.d[11] = -m[0]*m[5]*m[11] + m[0]*m[7]*m[9] + m[4]*m[1]*m[11] -
                    m[4]*m[3]*m[9] - m[8]*m[1]*m[7] + m[8]*m[3]*m[5];
        inv.d[15] = m[0]*m[5]*m[10] - m[0]*m[6]*m[9] - m[4]*m[1]*m[10] +
                    m[4]*m[2]*m[9] + m[8]*m[1]*m[6] - m[8]*m[2]*m[5];

        for (int i = 0; i < 16; ++i)
            inv.d[i] *= inv_det;

        return inv;
    }

    /**
     * Extract XYZ euler angles (radians) from the upper-left 3x3 of a
     * row-major 4x4 matrix. Matches Maya's MEulerRotation::kXYZ order.
     *
     * Maya uses ROW-VECTOR convention: v' = v * M, and for XYZ rotation
     * order the combined matrix is M = Rx * Ry * Rz (applied left-to-right
     * as the vector multiplies from the left):
     *
     *   m(0,0) = cy*cz                m(0,1) = cy*sz                m(0,2) = -sy
     *   m(1,0) = sx*sy*cz - cx*sz     m(1,1) = sx*sy*sz + cx*cz    m(1,2) = sx*cy
     *   m(2,0) = cx*sy*cz + sx*sz     m(2,1) = cx*sy*sz - sx*cz    m(2,2) = cx*cy
     *
     * Extraction:
     *   y = asin(-m(0,2))
     *   x = atan2(m(1,2), m(2,2))
     *   z = atan2(m(0,1), m(0,0))
     */
    static Vec3 euler_from_matrix_xyz(const Mat4& m) {
        double neg_sy = m.d[2];  // m(0,2) = -sin(y)
        // Clamp to [-1, 1] to avoid NaN from asin
        if (neg_sy > 1.0) neg_sy = 1.0;
        if (neg_sy < -1.0) neg_sy = -1.0;
        double y = std::asin(-neg_sy);

        double cy = std::cos(y);
        double x, z;
        if (std::abs(cy) > 1e-10) {
            x = std::atan2(m.d[6], m.d[10]);   // m(1,2), m(2,2)
            z = std::atan2(m.d[1], m.d[0]);    // m(0,1), m(0,0)
        } else {
            // Gimbal lock
            x = std::atan2(-m.d[9], m.d[5]);   // -m(2,1), m(1,1)
            z = 0.0;
        }
        return {x, y, z};
    }

    /**
     * Build a rotation matrix from XYZ euler angles (radians).
     *
     * Maya uses ROW-VECTOR convention: v' = v * M. For XYZ rotation
     * order the combined matrix is M = Rx * Ry * Rz, stored row-major:
     *
     *   m(0,0) = cy*cz                m(0,1) = cy*sz                m(0,2) = -sy
     *   m(1,0) = sx*sy*cz - cx*sz     m(1,1) = sx*sy*sz + cx*cz    m(1,2) = sx*cy
     *   m(2,0) = cx*sy*cz + sx*sz     m(2,1) = cx*sy*sz - sx*cz    m(2,2) = cx*cy
     */
    static Mat4 mat4_from_euler_xyz(const Vec3& euler) {
        double cx = std::cos(euler.x), sx = std::sin(euler.x);
        double cy = std::cos(euler.y), sy = std::sin(euler.y);
        double cz = std::cos(euler.z), sz = std::sin(euler.z);

        Mat4 m;
        m.d[0]  = cy * cz;
        m.d[1]  = cy * sz;
        m.d[2]  = -sy;
        m.d[3]  = 0;

        m.d[4]  = sx * sy * cz - cx * sz;
        m.d[5]  = sx * sy * sz + cx * cz;
        m.d[6]  = sx * cy;
        m.d[7]  = 0;

        m.d[8]  = cx * sy * cz + sx * sz;
        m.d[9]  = cx * sy * sz - sx * cz;
        m.d[10] = cx * cy;
        m.d[11] = 0;

        m.d[12] = 0;
        m.d[13] = 0;
        m.d[14] = 0;
        m.d[15] = 1;
        return m;
    }

    /**
     * Build a 4x4 matrix from a position and a normal direction.
     *
     * Replicates the Python getOrient() + setRotation() + setTranslation()
     * pipeline EXACTLY:
     *   1. Build raw matrix: row0=normal, row1=[0,1,0], row2=normal x [0,1,0]
     *      (no normalization, no orthogonalization — matches Python)
     *   2. Extract XYZ euler angles (matches Maya's MTransformationMatrix)
     *   3. Rebuild clean rotation from euler angles
     *   4. Set translation
     *
     * The euler round-trip "cleans up" the non-orthogonal input, exactly
     * as Maya does when getOrient returns euler angles and setRotation
     * rebuilds the matrix.
     */
    static Mat4 from_position_and_normal(const Vec3& pos, const Vec3& normal) {
        // Do NOT normalize normal — match Python which passes avg_normal
        // (already normalized at the Python call site via .normalize())
        Vec3 n = normal;
        Vec3 tangent = {0, 1, 0};
        // Raw cross product — do NOT normalize (matches Python getOrient)
        Vec3 cross = {
            n.y * tangent.z - n.z * tangent.y,
            n.z * tangent.x - n.x * tangent.z,
            n.x * tangent.y - n.y * tangent.x
        };

        // Build raw (potentially non-orthogonal) matrix:
        // row0 = normal, row1 = tangent, row2 = cross
        // This matches: tMatrix = normal + [0] + tangent + [0] + cross + [0,0,0,0,1]
        Mat4 raw = Mat4::zero();
        raw.d[0]  = n.x;       raw.d[1]  = n.y;       raw.d[2]  = n.z;
        raw.d[4]  = tangent.x; raw.d[5]  = tangent.y; raw.d[6]  = tangent.z;
        raw.d[8]  = cross.x;   raw.d[9]  = cross.y;   raw.d[10] = cross.z;
        raw.d[15] = 1.0;

        // Euler round-trip: extract XYZ euler from raw, rebuild clean rotation
        // This matches Maya's: MTransformationMatrix(raw).eulerRotation()
        // then TransformationMatrix().setRotation(euler)
        Vec3 euler = euler_from_matrix_xyz(raw);
        Mat4 result = mat4_from_euler_xyz(euler);
        result.set_translation(pos);
        return result;
    }

    /**
     * Set the scale of the matrix to 1,1,1 while preserving rotation
     * and translation. Matches mgear.core.transform.setMatrixScale()
     * which uses TransformationMatrix.setScale + setShear.
     *
     * Uses Gram-Schmidt orthogonalization on the upper-left 3x3 to
     * extract pure rotation, removing both scale and shear.
     *
     * Also handles the case where d[15] != 1 (e.g. after uniform scalar
     * multiplication of the whole matrix). Maya's TransformationMatrix
     * normalizes by d[15] during decomposition, so we replicate that
     * by dividing translation by d[15] before resetting it to 1.
     */
    void normalize_scale() {
        // If d[15] != 1 (from scalar multiplication of the whole matrix),
        // normalize translation by d[15] to match Maya's behavior.
        // Maya's MTransformationMatrix divides by d[15] on decomposition.
        if (std::abs(d[15]) > 1e-30 && std::abs(d[15] - 1.0) > 1e-15) {
            double inv_w = 1.0 / d[15];
            d[12] *= inv_w;
            d[13] *= inv_w;
            d[14] *= inv_w;
        }

        Vec3 r0 = row3(0);
        Vec3 r1 = row3(1);

        // Gram-Schmidt orthogonalization
        r0 = r0.normalized();
        r1 = (r1 - r0 * r1.dot(r0)).normalized();
        // r2 from cross product ensures right-handed orthonormal frame
        Vec3 r2 = r0.cross(r1);

        d[0] = r0.x; d[1] = r0.y; d[2] = r0.z;  d[3]  = 0;
        d[4] = r1.x; d[5] = r1.y; d[6] = r1.z;  d[7]  = 0;
        d[8] = r2.x; d[9] = r2.y; d[10] = r2.z; d[11] = 0;
        d[15] = 1.0;
    }

    /**
     * Set matrix position (translation row).
     * Matches mgear.core.transform.setMatrixPosition().
     */
    static Mat4 with_position(const Mat4& m, const Vec3& pos) {
        Mat4 result = m;
        result.d[12] = pos.x;
        result.d[13] = pos.y;
        result.d[14] = pos.z;
        return result;
    }
};

// -------------------------------------------------------------------------
// Topology helpers
// -------------------------------------------------------------------------

/**
 * Build vertex-to-vertex adjacency from face topology.
 *
 * face_vert_counts: number of vertices per face (F)
 * face_vert_indices: flat array of vertex indices (sum of counts)
 *
 * Returns: adjacency as two flat arrays:
 *   neighbor_offsets[v] = start index into neighbor_indices for vertex v
 *   neighbor_indices = flat array of neighbor vertex indices
 *   (size = neighbor_offsets.size() - 1 = num_verts + 1)
 */
void build_adjacency(
    int num_verts,
    const std::vector<int>& face_vert_counts,
    const std::vector<int>& face_vert_indices,
    std::vector<int>& neighbor_offsets,
    std::vector<int>& neighbor_indices_out);

/**
 * Build vertex-to-face adjacency from face topology.
 *
 * Returns: two flat arrays (CSR-like):
 *   vert_face_offsets[v] = start index for vertex v
 *   vert_face_indices = flat array of face indices
 */
void build_vert_faces(
    int num_verts,
    const std::vector<int>& face_vert_counts,
    const std::vector<int>& face_vert_indices,
    std::vector<int>& vert_face_offsets,
    std::vector<int>& vert_face_indices_out);

/**
 * BFS flood-fill from seed vertices, returning the N closest vertices
 * sorted by distance from a reference position.
 *
 * This is the C++ port of meshNavigation.getClosestNVerticesFromTransform().
 *
 * seed_verts: initial vertex indices to start BFS from (e.g. polygon verts)
 * ref_pos: reference position to measure distances from
 * points: flat N*3 vertex positions
 * count: number of closest vertices to return
 *
 * Returns: sorted vertex indices (closest first)
 */
std::vector<int> find_n_closest_vertices(
    const std::vector<int>& seed_verts,
    const Vec3& ref_pos,
    const std::vector<double>& points,
    int count,
    const std::vector<int>& neighbor_offsets,
    const std::vector<int>& neighbor_indices);

/**
 * Build a reference matrix from multiple vertex indices.
 * Computes centroid + averaged face normal -> 4x4 matrix.
 *
 * This is the C++ port of getMultiVertexReferenceMatrix().
 *
 * vert_indices: vertex indices to use
 * points: flat N*3 vertex positions
 * face_normals: flat F*3 face normals
 * vert_face_offsets / vert_face_indices: vertex-to-face adjacency
 *
 * Returns: 4x4 reference matrix (row-major, flat 16 doubles)
 */
Mat4 build_multi_vertex_ref_matrix(
    const std::vector<int>& vert_indices,
    const std::vector<double>& points,
    const std::vector<double>& face_normals,
    const std::vector<int>& vert_face_offsets,
    const std::vector<int>& vert_face_indices);

/**
 * Compute centroid from vertex indices.
 *
 * Returns: centroid position
 */
Vec3 compute_centroid(
    const std::vector<int>& vert_indices,
    const std::vector<double>& points);

/**
 * Compute the distance between two Vec3 points.
 */
inline double distance(const Vec3& a, const Vec3& b) {
    return (a - b).length();
}

/**
 * Linear interpolation between two Vec3 points (t=0.5).
 */
inline Vec3 midpoint(const Vec3& a, const Vec3& b) {
    return lerp(a, b, 0.5);
}

// -------------------------------------------------------------------------
// Batch operations exposed to Python
// -------------------------------------------------------------------------

/**
 * Result from recording primary side of all guides.
 *
 * For each guide:
 *   vert_ids: flat array of N vertex indices
 *   ref_matrix: 16-element flat matrix
 *   mirror_position: 3-element position (where to search for mirror verts)
 */
struct RecordPrimaryResult {
    // Per-guide results, all flat-packed
    // guide_count entries, each with sample_count vertex ids
    std::vector<int> all_vert_ids;           // guide_count * sample_count
    std::vector<double> all_ref_matrices;    // guide_count * 16
    std::vector<double> all_mirror_positions; // guide_count * 3
};

/**
 * Result from recording mirror side of all guides.
 */
struct RecordMirrorResult {
    std::vector<int> all_vert_ids;           // guide_count * sample_count
    std::vector<double> all_ref_matrices;    // guide_count * 16
};

/**
 * Record primary side: for each guide position, find N closest vertices,
 * build reference matrix, and compute mirror position.
 *
 * guide_positions: flat guide_count * 3 world positions
 * guide_matrices: flat guide_count * 16 world matrices
 * seed_vert_ids: flat guide_count * seed_count seed vertices per guide
 *                (from MFnMesh.getClosestPoint, done in Python)
 * seed_count: number of seed verts per guide (polygon vertex count)
 * seed_counts: per-guide seed vertex counts (variable polygon sizes)
 * seed_offsets: per-guide offsets into seed_vert_ids
 *
 * All mesh data (points, topology, normals) passed as flat arrays.
 */
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
    ProgressCB progress_cb = nullptr);

/**
 * Record mirror side: for each mirror seed, find N closest vertices
 * and build reference matrix.
 *
 * Same signature pattern as record_primary but for mirror positions.
 */
RecordMirrorResult record_mirror(
    const std::vector<int>& seed_vert_ids,
    const std::vector<int>& seed_offsets,
    int sample_count,
    const std::vector<double>& points,
    const std::vector<double>& face_normals,
    const std::vector<int>& face_vert_counts,
    const std::vector<int>& face_vert_indices,
    int num_verts,
    ProgressCB progress_cb = nullptr);

/**
 * Reposition all guides given stored data and new mesh.
 *
 * For each guide, computes the delta matrix and applies scale
 * compensation, matching the Python getRepositionMatrix() logic.
 *
 * node_matrices: flat guide_count * 16 original guide world matrices
 * ref_matrices: flat guide_count * 16 original reference matrices
 * mr_ref_matrices: flat guide_count * 16 original mirror reference matrices
 * vert_ids: flat guide_count * sample_count primary vertex indices
 * mr_vert_ids: flat guide_count * sample_count mirror vertex indices
 * new_points: flat N*3 new mesh vertex positions
 *
 * Returns: flat guide_count * 16 new world matrices for each guide
 */
std::vector<double> reposition_all_guides(
    const std::vector<double>& node_matrices,
    const std::vector<double>& ref_matrices,
    const std::vector<double>& mr_ref_matrices,
    const std::vector<int>& vert_ids,
    const std::vector<int>& mr_vert_ids,
    int sample_count,
    const std::vector<double>& new_points,
    ProgressCB progress_cb = nullptr);

}  // namespace rgp_accel
