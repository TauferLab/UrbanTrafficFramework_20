#[cfg(test)]
extern crate quickcheck;

#[cfg(test)]
#[macro_use(quickcheck)]
extern crate quickcheck_macros;

pub mod buildings;
pub mod geo;
pub mod kd_tree;
pub mod loader;
pub mod quadtree;
mod unit_fixed;
pub mod vehicle_sim;
mod z_order;

pub use buildings::{Building, BuildingRecord};
pub use geo::{Region, UTMCoordinates};
pub use kd_tree::UTMTree;
pub use loader::{load_agents, load_buildings};
use unit_fixed::UnitFixedPoint;
pub use vehicle_sim::{parse_timestamp, Agent, AgentRecord};
use z_order::ZValue;
