use std::cmp::Ordering;
use std::convert::AsRef;
use std::mem;

use crate::UTMCoordinates;

/// A node within a `UTMTree`.
///
/// `T` is type of the data to be stored within the tree; the stored elements are
/// keyed and spatially partitioned by the `UTMCoordinates` each element references
/// (via `AsRef`).
pub struct TreeNode<'a, T: AsRef<UTMCoordinates> + Sync> {
    data: &'a T,
    left: Option<Box<TreeNode<'a, T>>>,
    right: Option<Box<TreeNode<'a, T>>>,
}

impl<'a, T: AsRef<UTMCoordinates> + Sync> TreeNode<'a, T> {
    /// Create a boxed `TreeNode` containing the (approximate) median point of
    /// the given coordinates along the current axis, as well as its child nodes.
    /// This is a recursive operation.
    ///
    /// `y_axis` indicates whether the Y-axis (if true) or the X-axis (if false)
    /// is being split along at the current tree level.
    ///
    /// Although `refs` must be a `mut` slice, none of the elements (themselves)
    /// will be changed during tree creation, only reordered as part of partitioning.
    ///
    /// This operation is parallelized using Rayon.
    fn new(refs: &mut [&'a T], y_axis: bool) -> Option<Box<TreeNode<'a, T>>> {
        match refs.len() {
            0 => None,
            1 => Some(Box::new(TreeNode {
                data: refs[0],
                left: None,
                right: None,
            })),
            2 => {
                let mut parent = Box::new(TreeNode {
                    data: refs[0],
                    left: None,
                    right: None,
                });

                let child = Box::new(TreeNode {
                    data: refs[1],
                    left: None,
                    right: None,
                });

                if coords_lt(child.data.as_ref(), parent.data.as_ref(), y_axis) {
                    parent.left = Some(child);
                } else {
                    parent.right = Some(child);
                };

                Some(parent)
            }
            _ => {
                let (left, pivot, right) = partition(refs, |&e1, &e2| {
                    coords_cmp(e1.as_ref(), e2.as_ref(), y_axis)
                });

                let (left, right) = rayon::join(
                    || TreeNode::new(left, !y_axis),
                    || TreeNode::new(right, !y_axis),
                );

                Some(Box::new(TreeNode {
                    data: *pivot,
                    left,
                    right,
                }))
            }
        }
    }

    /// Perform an unparallelized recursive nearest-neighbors query.
    ///
    /// `best` will be overwritten with the `k = best.len()` nearest neighbors of
    /// the `query` point, along with corresponding _squared_ Euclidean distances.
    ///
    /// `y_axis` indicates whether the Y-axis (if true) or the X-axis (if false)
    /// is being split along at the current tree level.
    ///
    /// `max_dist` is a squared distance threshold for returned points; points
    /// further away than `max_dist` will not be returned in `best`.
    fn nearest_neighbors(
        &self,
        query: UTMCoordinates,
        best: &mut [(Option<&'a T>, f64)],
        y_axis: bool,
        max_dist: f64,
    ) {
        let left = coords_lt(&query, self.data.as_ref(), y_axis);

        // Downwards recursion (towards absolute nearest neighbor)
        if left {
            if let Some(c) = self.left.as_deref() {
                c.nearest_neighbors(query, best, !y_axis, max_dist);
            }
        } else {
            if let Some(c) = self.right.as_deref() {
                c.nearest_neighbors(query, best, !y_axis, max_dist);
            }
        }

        // Upwards traversal: attempt to insert this node into the current
        // nearest neighbors list
        let d = self.data.as_ref().squared_dist(query);
        if d < max_dist {
            let idx = best
                .binary_search_by(|&x| {
                    if x.1 <= d {
                        Ordering::Less
                    } else {
                        Ordering::Greater
                    }
                })
                .unwrap_err();

            if idx < best.len() {
                let mut t = (Some(self.data), d);
                for slot in &mut best[idx..] {
                    mem::swap(&mut t, slot);
                }
            }
        }

        // Check if there are better points on the other side
        if (left && self.right.is_some()) || (!left && self.left.is_some()) {
            let sep_dist = if y_axis {
                f64::powi(query.y - self.data.as_ref().y, 2)
            } else {
                f64::powi(query.x - self.data.as_ref().x, 2)
            };

            if sep_dist < max_dist && sep_dist <= best.last().unwrap().1 {
                // recurse into other child
                if left {
                    self.right
                        .as_deref()
                        .unwrap()
                        .nearest_neighbors(query, best, !y_axis, max_dist);
                } else {
                    self.left
                        .as_deref()
                        .unwrap()
                        .nearest_neighbors(query, best, !y_axis, max_dist);
                }
            }
        }
    }
}

/// A `k`-d tree structure, keyed by points represented as `UTMCoordinates`.
///
/// Given a set of data elements with associated geographical points, this data
/// structure can be used to efficiently search for the nearest element(s) to a
/// query point.
///
/// Each element/reference stored within the tree must be associated with
/// `UTMCoordinates` via `AsRef<UTMCoordinates>`. These coordinates will be
/// used to both construct the tree and perform nearest-neighbor lookups.
///
/// In addition, the initial construction of the tree will be performed in
/// parallel using Rayon, therefore the elements stored within the tree must be
/// `Sync`.
///
/// As with most keyed collections, it is a logic error for the `UTMCoordinates`
/// referenced by a stored element to change while it is in the tree; this is
/// normally only possible by interior mutability (`Cell` and the like) or unsafe
/// code.
pub struct UTMTree<'a, T: AsRef<UTMCoordinates> + Sync> {
    root: Option<Box<TreeNode<'a, T>>>,
}

impl<'a, T: AsRef<UTMCoordinates> + Sync> UTMTree<'a, T> {
    /// Create a new UTMTree referencing the given `data`.
    pub fn new(data: &'a [T]) -> UTMTree<'a, T> {
        let mut refs: Vec<&'a T> = data.iter().collect();
        let root = TreeNode::new(&mut refs, false);
        UTMTree { root }
    }

    /// Find the `k = out.len()` nearest stored points to the given `query`
    /// point.
    ///
    /// The results (returned in the `out` slice) consist of pairs of found
    /// neighbor points (if any) and the _squared_ Euclidean distances to those
    /// points.
    /// These neighbors will be returned in order of increasing distance.
    ///
    /// `max_dist` can be used as a filter for returned results: points in the
    /// tree that are further away than `max_dist` will not be returned as
    /// neighbor points.
    ///
    /// This method takes a mutable slice for output in order to allow for
    /// reusing allocations.
    pub fn nearest_neighbors(
        &self,
        query: UTMCoordinates,
        out: &mut [(Option<&'a T>, f64)],
        max_dist: f64,
    ) {
        for i in out.iter_mut() {
            *i = (None, f64::INFINITY);
        }

        if out.len() == 0 {
            return;
        }

        if let Some(root) = self.root.as_deref() {
            root.nearest_neighbors(query, out, false, max_dist.powi(2));
        }
    }

    /// Find the nearest stored data points to a query point, and collect them
    /// into a Vec.
    ///
    /// This works the same as `nearest_neighbors`, but returns results
    /// in a freshly-allocated Vec.
    ///
    /// The returned Vec will be additionally be trimmed such that it only
    /// contains found neighbors, though space for `k` returned elements must
    /// always be allocated up-front.
    pub fn collect_nearest(
        &self,
        query: UTMCoordinates,
        k: usize,
        max_dist: f64,
    ) -> Vec<(Option<&'a T>, f64)> {
        let mut out = Vec::new();

        out.resize(k, (None, f64::INFINITY));
        self.nearest_neighbors(query, &mut out, max_dist);
        out.retain(|nn| nn.0.is_some());

        out
    }
}

fn coords_cmp(a: &UTMCoordinates, b: &UTMCoordinates, y_axis: bool) -> Ordering {
    if y_axis {
        a.y.partial_cmp(&b.y).unwrap()
    } else {
        a.x.partial_cmp(&b.x).unwrap()
    }
}

fn coords_lt(a: &UTMCoordinates, b: &UTMCoordinates, y_axis: bool) -> bool {
    if y_axis {
        a.y.lt(&b.y)
    } else {
        a.x.lt(&b.x)
    }
}

/// Find the median value in an array and reorder it into separate partitions,
/// based on a comparison function.
///
/// This function returns:
///  - A subslice of `array` containing elements less than the median
///  - A reference to the median itself
///  - A subslice of `array` containing elements greater than or equal to the
///    median.
///
/// These subslices and references are non-overlapping.
fn partition<'a, T, F>(array: &'a mut [T], mut cmp: F) -> (&'a mut [T], &'a mut T, &'a mut [T])
where
    F: FnMut(&T, &T) -> Ordering,
{
    if array.len() == 0 {
        panic!("cannot partition arrays of size 0");
    } else if array.len() == 1 {
        return (&mut [], &mut array[0], &mut []);
    } else if array.len() == 2 {
        if cmp(&array[0], &array[1]) == Ordering::Greater {
            array.swap(0, 1);
        }

        let (pivot, lower) = array.split_last_mut().unwrap();
        return (lower, pivot, &mut []);
    }

    // Move median of three to last position:
    let hi = array.len() - 1;
    let mid = array.len() >> 1;

    if cmp(&array[mid], &array[0]) == Ordering::Less {
        array.swap(mid, 0);
    }

    if cmp(&array[hi], &array[0]) == Ordering::Less {
        array.swap(hi, 0);
    }

    if cmp(&array[mid], &array[hi]) == Ordering::Less {
        array.swap(hi, mid);
    }

    let (pivot, elems) = array.split_last_mut().unwrap();
    let mut i: usize = 0;
    let mut j: usize = elems.len();

    loop {
        while cmp(&elems[i], pivot) == Ordering::Less {
            i += 1;
        }

        loop {
            j -= 1;
            if cmp(&elems[j], pivot) != Ordering::Greater {
                break;
            }
        }

        if i >= j {
            let (lt, ge) = elems.split_at_mut(i);
            return (lt, pivot, ge);
        } else {
            elems.swap(i, j);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use quickcheck::TestResult;

    #[derive(Debug, Copy, Clone)]
    struct DummyPoint {
        pt: UTMCoordinates,
        offset: f64,
    }

    impl AsRef<UTMCoordinates> for DummyPoint {
        fn as_ref(&self) -> &UTMCoordinates {
            &self.pt
        }
    }

    #[quickcheck]
    fn quickcheck_knn_correctness(
        query: (f64, f64),
        offsets: Vec<(f64, f64)>,
        k: usize,
        max_dist: f64,
    ) -> TestResult {
        if k > offsets.len() {
            return TestResult::discard();
        }

        let query: UTMCoordinates = query.into();
        let mut cur_dist: f64 = 0.0;

        // generate points with increasing distance from query
        let points: Vec<DummyPoint> = offsets
            .into_iter()
            .map(move |(d, th)| {
                let d = d.abs();
                cur_dist += d;

                let (dx, dy) = th.sin_cos();
                let cur_pt =
                    UTMCoordinates::new(query.x + (dx * cur_dist), query.y + (dy * cur_dist));

                DummyPoint {
                    pt: cur_pt,
                    offset: d,
                }
            })
            .collect();

        if points.iter().any(|p| p.offset < 0.000001) {
            return TestResult::discard();
        }

        let tree = UTMTree::new(&points);
        let knn = tree.collect_nearest(query, k, max_dist);

        assert!(knn.len() <= k);
        for (i, p) in knn.iter().enumerate() {
            assert!(p.0.is_some(), "could not find nearest neighbor #{}", i);
        }

        // We want to test these properties:
        // - Nearest-neighbors should be returned in order of increasing distance
        // - Distances to all nearest-neighbors should be < max_dist
        // - All nearest-neighbors closer than max_dist should be returned.

        // Find the expected nearest-neighbor points using the naive method
        // as a comparison:
        let squared_max_dist = max_dist.powi(2);
        let expected: Vec<(&DummyPoint, f64)> = points
            .iter()
            .filter_map(|item| {
                let dist = item.pt.squared_dist(query);
                if dist < squared_max_dist {
                    Some((item, dist))
                } else {
                    None
                }
            })
            .take(k)
            .collect();

        assert_eq!(expected.len(), knn.len());

        let is_correct = knn.iter().zip(&expected).all(|((i1, d1), (i2, d2))| {
            let r1 = i1.unwrap() as *const DummyPoint;
            let r2 = *i2 as *const DummyPoint;

            let err = (*d1 - *d2).abs();
            (r1 == r2) && (err < 1e-5) && (d1 < &squared_max_dist)
        });

        TestResult::from_bool(is_correct)
    }

    #[quickcheck]
    fn quickcheck_partition_correctness(mut data: Vec<u64>) -> TestResult {
        if data.len() < 1 {
            return TestResult::discard();
        }

        let (lt, pivot, ge) = partition(&mut data, |x, y| x.cmp(y));

        let left_check = lt.iter().all(|i| i.lt(pivot));
        let right_check = ge.iter().all(|i| i.ge(pivot));

        TestResult::from_bool(left_check && right_check)
    }
}
