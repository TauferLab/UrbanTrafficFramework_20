use rayon::prelude::*;
use std::env;
use std::io;
use std::slice;

use agent_mapping::UTMTree;
use agent_mapping::{Agent, Building};

pub fn main() {
    let args: Vec<String> = env::args().skip(1).collect();

    let agents = agent_mapping::load_agents(args[0].as_str());
    let buildings = agent_mapping::load_buildings(args[1].as_str());
    let time = if args.len() > 2 {
        Some(agent_mapping::parse_timestamp(&args[2]))
    } else {
        None
    };

    let mut writer = csv::Writer::from_writer(io::stdout());
    writer
        .write_record(&["vehicle", "time", "building", "distance"])
        .unwrap();

    let tree = UTMTree::new(&buildings);
    let mappings: Vec<(&Agent, &Building, f64)> = agents
        .par_iter()
        .filter(|&agent| time.is_none() || agent.time() == time.unwrap())
        .map_with((None, 0.0), |out, agent| {
            tree.nearest_neighbors(agent.position(), slice::from_mut(out), f64::INFINITY);
            out.0.map(|bldg| (agent, bldg, out.1.sqrt()))
        })
        .flatten()
        .collect();

    for (agent, bldg, distance) in mappings {
        let row = [
            format!("{}", agent.id()),
            agent.formatted_time(),
            format!("{}", bldg.id()),
            format!("{}", distance),
        ];

        writer.serialize(&row).unwrap();
    }

    writer.flush().unwrap();
}
