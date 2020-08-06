use std::env;
use std::io;

use agent_mapping::quadtree;
use agent_mapping::{Agent, Building};

fn map_to_closest<'a>(agent: &Agent, buildings: &[&'a Building]) -> &'a Building {
    buildings
        .iter()
        .map(|&b| (b, b.centroid().squared_dist(agent.position())))
        .min_by(|a, b| {
            a.1.partial_cmp(&b.1)
                .expect("could not compare squared distances")
        })
        .expect("empty buildings slice")
        .0
}

pub fn main() {
    let args: Vec<String> = env::args().skip(1).collect();

    let agents = agent_mapping::load_agents(args[0].as_str());
    let buildings = agent_mapping::load_buildings(args[1].as_str());
    let mut writer = csv::Writer::from_writer(io::stdout());
    writer
        .write_record(&["vehicle", "time", "building", "distance"])
        .unwrap();

    for (agent, bldg) in quadtree::map_vehicles(10, &agents, &buildings, map_to_closest) {
        let p1 = agent.position();
        let p2 = bldg.centroid();

        let row = [
            format!("{}", agent.id()),
            agent.formatted_time(),
            format!("{}", bldg.id()),
            format!("{}", p1.distance(p2)),
        ];
        writer.serialize(&row).unwrap();
    }

    writer.flush().unwrap();
}
