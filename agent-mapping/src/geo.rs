use serde::{Deserialize, Serialize};

use crate::UnitFixedPoint;
use crate::ZValue;

/// A UTM coordinate pair, without zone info.
#[derive(Debug, Copy, Clone, Serialize, Deserialize)]
pub struct UTMCoordinates {
    pub x: f64,
    pub y: f64,
}

impl UTMCoordinates {
    pub fn new(x: f64, y: f64) -> UTMCoordinates {
        UTMCoordinates { x, y }
    }

    /// Compute the square of the Euclidean distance between this point and
    /// another.
    #[inline]
    pub fn distance(self, other: UTMCoordinates) -> f64 {
        (self.x - other.x).hypot(self.y - other.y)
    }

    /// Compute the square of the Euclidean distance between this point and
    /// another.
    ///
    /// This might be faster than computing the actual distance, and still
    /// preserves nearest-neighbors.
    #[inline]
    pub fn squared_dist(self, other: UTMCoordinates) -> f64 {
        (self.x - other.x).powi(2) + (self.y - other.y).powi(2)
    }

    /// Convert this point into a `UnitFixedPoint` coordinate pair, based on a
    /// containing `Region`.
    ///
    /// The coordinates within this point are rescaled so that they lie within
    /// the range [0, 1], where coordinates `(0, 0)` represent the southwest
    /// corner of the region and coordinates `(1, 1)` represent the northeast
    /// corner.
    ///
    /// Returns `None` if this point falls outside of the given `region`.
    pub fn normalize(self, region: &Region) -> Option<(UnitFixedPoint, UnitFixedPoint)> {
        let x = (self.x - region.west) / (region.east - region.west);
        let y = (self.y - region.south) / (region.north - region.south);

        if x < 0.0 || x > 1.0 || y < 0.0 || y > 1.0 {
            None
        } else {
            Some((x.into(), y.into()))
        }
    }

    /// Convert this point into a Z-value by first rescaling each coordinate
    /// such that it falls within the range `[0, 1]` (see `normalize()`), then
    /// interleaving the fixed-point representation of the scaled coordinate
    /// values.
    pub fn z_value(self, region: &Region) -> Option<ZValue> {
        self.normalize(region).map(|p| p.into())
    }
}

impl From<(f64, f64)> for UTMCoordinates {
    fn from(tup: (f64, f64)) -> UTMCoordinates {
        UTMCoordinates { x: tup.0, y: tup.1 }
    }
}

impl From<UTMCoordinates> for (f64, f64) {
    fn from(coords: UTMCoordinates) -> Self {
        (coords.x, coords.y)
    }
}

/// Represents a rectangular geographical region, with bounds specified in UTM
/// coordinates.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Region {
    pub east: f64,
    pub west: f64,
    pub north: f64,
    pub south: f64,
}

impl Region {
    /// Creates a new Region.
    pub const fn new(east: f64, west: f64, north: f64, south: f64) -> Region {
        Region {
            east,
            west,
            north,
            south,
        }
    }

    /// Creates a new Region from two coordinate pairs.
    pub fn from_points(northeast: UTMCoordinates, southwest: UTMCoordinates) -> Region {
        Region {
            east: northeast.x,
            north: northeast.y,
            west: southwest.x,
            south: southwest.y,
        }
    }

    /// Tests if a coordinate pair lies within this Region.
    pub fn contains(&self, p: UTMCoordinates) -> bool {
        !((p.x < self.west) || (p.x > self.east) || (p.y < self.south) || (p.y > self.north))
    }

    /// Test if two Regions intersect.
    pub fn intersects(&self, other: &Region) -> bool {
        (self.west < other.east)
            && (self.east > other.west)
            && (self.south < other.north)
            && (self.north > other.south)
    }

    /// Get the center of this region.
    pub fn center(&self) -> UTMCoordinates {
        UTMCoordinates {
            x: (self.east + self.west) / 2.0,
            y: (self.north + self.south) / 2.0,
        }
    }

    /// Gets the southwest corner of this Region.
    pub fn southwest(&self) -> UTMCoordinates {
        UTMCoordinates {
            y: self.south,
            x: self.west,
        }
    }

    /// Gets the southeast corner of this Region.
    pub fn southeast(&self) -> UTMCoordinates {
        UTMCoordinates {
            y: self.south,
            x: self.east,
        }
    }

    /// Gets the northwest corner of this Region.
    pub fn northwest(&self) -> UTMCoordinates {
        UTMCoordinates {
            y: self.north,
            x: self.west,
        }
    }

    /// Gets the northeast corner of this Region.
    pub fn northeast(&self) -> UTMCoordinates {
        UTMCoordinates {
            y: self.north,
            x: self.east,
        }
    }
}
