use std::env;
use std::io;

use agent_mapping::quadtree;
use agent_mapping::{Agent, Building};

fn map_weighted<'a>(agent: &Agent, buildings: &[&'a Building]) -> &'a Building {
    assert_ne!(buildings.len(), 0, "empty buildings slice");
    let area_sum: f64 = buildings.iter().map(|&b| b.area()).sum();

    buildings
        .iter()
        .map(|&b| -> (&'a Building, f64) {
            let rel_area = b.area() / area_sum;
            let dist = b.centroid().distance(agent.position());
            (b, dist / rel_area)
        })
        .min_by(|a, b| {
            a.1.partial_cmp(&b.1)
                .expect("could not compare weighted distances")
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
        .write_record(&["vehicle", "building", "x", "y", "bldg_x", "bldg_y"])
        .unwrap();

    for (agent, bldg) in quadtree::map_vehicles(10, &agents, &buildings, map_weighted) {
        let p1 = agent.position();
        let p2 = bldg.centroid();

        let row = [
            format!("{}", agent.id()),
            format!("{}", bldg.id()),
            format!("{}", p1.x),
            format!("{}", p1.y),
            format!("{}", p2.x),
            format!("{}", p2.y),
        ];
        writer.serialize(&row).unwrap();
    }

    writer.flush().unwrap();
}
