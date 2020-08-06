use csv::StringRecord;
use rayon::prelude::*;
use serde::de::DeserializeOwned;
use std::convert::AsRef;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;
use std::sync::Arc;

use crate::{Agent, AgentRecord, Building, BuildingRecord};

/// Load records out of a CSV file and deserialize them in parallel.
pub fn load<T: DeserializeOwned + Send, P: AsRef<Path>>(
    fname: P,
) -> impl ParallelIterator<Item = T> {
    let f = File::open(fname).expect("could not open file");
    let buf = BufReader::new(f);
    let mut reader = csv::Reader::from_reader(buf);
    let header = Arc::new(reader.headers().expect("could not read header row").clone());

    reader
        .into_records()
        .par_bridge()
        .map_with(header, |h, r: Result<StringRecord, _>| -> T {
            r.expect("could not read record")
                .deserialize(Some(h.as_ref()))
                .expect("could not deserialize")
        })
}

/// Load a vehicle snapshot file.
pub fn load_agents<P: AsRef<Path>>(fname: P) -> Vec<Agent> {
    load(fname).map(|r: AgentRecord| r.into()).collect()
}

/// Load a simplified building data file.
pub fn load_buildings<P: AsRef<Path>>(fname: P) -> Vec<Building> {
    load(fname).map(|r: BuildingRecord| r.into()).collect()
}
