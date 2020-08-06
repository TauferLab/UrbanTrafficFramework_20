use rayon::prelude::*;
use std::collections::HashMap;
use std::env;
use std::io;

use agent_mapping::loader;
use agent_mapping::AgentRecord;

fn update(m: &mut HashMap<u32, AgentRecord>, item: AgentRecord) {
    if let Some(v) = m.get(&item.vehicle()) {
        let cur_best_time = v.time();
        drop(v);

        if cur_best_time < item.time() {
            m.insert(item.vehicle(), item);
        }
    } else {
        m.insert(item.vehicle(), item);
    }
}

pub fn main() {
    let args: Vec<String> = env::args().skip(1).collect();

    let last_seen: HashMap<u32, AgentRecord> = args
        .par_iter()
        .map(|fname| loader::load::<AgentRecord, _>(fname.as_str()))
        .flatten()
        .fold(
            || HashMap::<u32, AgentRecord>::new(),
            |mut m: HashMap<u32, AgentRecord>, item: AgentRecord| {
                update(&mut m, item);
                m
            },
        )
        .reduce(
            || HashMap::<u32, AgentRecord>::new(),
            |mut a: HashMap<u32, AgentRecord>, b: HashMap<u32, AgentRecord>| {
                for (_, item) in b {
                    update(&mut a, item);
                }
                a
            },
        );

    let mut records: Vec<AgentRecord> = last_seen.into_par_iter().map(|t| t.1).collect();
    records.par_sort_unstable_by_key(|item| item.vehicle());

    let mut writer = csv::Writer::from_writer(io::stdout());
    for record in records {
        writer.serialize(record).unwrap();
    }
    writer.flush().unwrap();
}
