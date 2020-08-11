use serde::{Deserialize, Serialize};
use std::convert::{AsMut, AsRef};

use super::{Region, UTMCoordinates};

/// A (simplified) representation of a building's footprint, containing the area
/// and centroid coordinates for the original footprint, as well as the bounding
/// box of the footprint.
#[derive(Debug, Clone, Serialize)]
pub struct Building {
    id: u32,
    area: f64,
    centroid: UTMCoordinates,
    bbox: Region,
}

impl Building {
    pub fn id(&self) -> u32 {
        self.id
    }

    pub fn area(&self) -> f64 {
        self.area
    }

    pub fn centroid(&self) -> UTMCoordinates {
        self.centroid
    }

    /// Get the bounding box for this building.
    pub fn bbox(&self) -> &Region {
        &self.bbox
    }
}

impl AsRef<UTMCoordinates> for Building {
    fn as_ref(&self) -> &UTMCoordinates {
        &self.centroid
    }
}

impl AsRef<u32> for Building {
    fn as_ref(&self) -> &u32 {
        &self.id
    }
}

impl AsMut<u32> for Building {
    fn as_mut(&mut self) -> &mut u32 {
        &mut self.id
    }
}

impl From<Building> for u32 {
    fn from(bldg: Building) -> u32 {
        bldg.id
    }
}

/// A record describing a `Building`, as produced by our preprocessing scripts.
#[derive(Debug, Deserialize)]
pub struct BuildingRecord {
    id: u32,
    center_x: f64,
    center_y: f64,
    area: f64,
    bbox_east: f64,
    bbox_west: f64,
    bbox_north: f64,
    bbox_south: f64,
}

impl From<BuildingRecord> for Building {
    fn from(record: BuildingRecord) -> Building {
        Building {
            id: record.id,
            area: record.area,
            centroid: UTMCoordinates::new(record.center_x, record.center_y),
            bbox: Region::new(
                record.bbox_east,
                record.bbox_west,
                record.bbox_north,
                record.bbox_south,
            ),
        }
    }
}

impl From<&'_ BuildingRecord> for Building {
    fn from(record: &'_ BuildingRecord) -> Building {
        Building {
            id: record.id,
            area: record.area,
            centroid: UTMCoordinates::new(record.center_x, record.center_y),
            bbox: Region::new(
                record.bbox_east,
                record.bbox_west,
                record.bbox_north,
                record.bbox_south,
            ),
        }
    }
}
