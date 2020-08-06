use csv::ByteRecord;
use rayon::prelude::*;
use std::cmp::Ordering;
use std::collections::HashMap;
use std::env;
use std::fs::File;
use std::hash::Hash;
use std::io::{BufReader, BufWriter};
use std::iter;
use std::mem;
use std::path::{Path, PathBuf};
use std::slice;

use agent_mapping::{Building, UTMCoordinates, UTMTree};

type AgentGrouping = HashMap<u8, Vec<ByteRecord>>;

fn load_record_file(path: &String) -> impl Iterator<Item = ByteRecord> + Send {
    let f = File::open(path).expect("could not open file");
    let mut reader = csv::Reader::from_reader(BufReader::new(f));
    let mut record = ByteRecord::new();

    iter::from_fn(move || {
        while reader.read_byte_record(&mut record).ok()? {
            if record[1].ends_with(b":00") {
                let mut out = ByteRecord::new();
                mem::swap(&mut out, &mut record);
                return Some(out);
            }
        }

        None
    })
}

fn get_hour(timestamp: &[u8]) -> u8 {
    match timestamp[1] {
        b':' => timestamp[0].saturating_sub(b'0'),
        b'@' => 24 + timestamp[2].saturating_sub(b'0'),
        _ => 10 * timestamp[0].saturating_sub(b'0') + timestamp[1].saturating_sub(b'0'),
    }
}

fn group_records(it: impl Iterator<Item = ByteRecord> + Send) -> AgentGrouping {
    let mut hm = HashMap::new();
    for record in it {
        let hour = get_hour(&record[1]);
        let v = hm.entry(hour).or_insert_with(Vec::new);
        v.push(record);
    }

    hm
}

fn merge_groups(mut h1: AgentGrouping, h2: AgentGrouping) -> AgentGrouping {
    for (hour, group2) in h2 {
        if let Some(group1) = h1.get_mut(&hour) {
            group1.extend(group2);
        } else {
            h1.insert(hour, group2);
        }
    }

    h1
}

fn push_as_string<T: ToString>(record: &mut ByteRecord, value: &T) {
    let s = value.to_string();
    record.push_field(s.as_bytes());
}

fn tukey_fences<T, F>(data: &mut [T], k: f64, mapper: F) -> &mut [T]
where
    T: Send,
    F: Fn(&T) -> f64 + Sync,
{
    data.par_sort_unstable_by(|a, b| mapper(a).partial_cmp(&mapper(b)).unwrap());

    let n = data.len() - 1;
    let q1 = n >> 2;
    let q2 = n >> 1;
    let q3 = n - q1;

    let iqr = mapper(&data[q3]) - mapper(&data[q1]);
    let q2 = mapper(&data[q2]);
    let fence_low = q2 - (k * iqr);
    let fence_hi = q2 + (k * iqr);

    // Get the index of the first element greater than or equal to fence_low.
    //
    // binary_search_by should never return Ok(), since the comparison function
    // never returns Ordering::Equal.
    let low_idx = data
        .binary_search_by(|x| {
            if mapper(x).lt(&fence_low) {
                Ordering::Less
            } else {
                Ordering::Greater
            }
        })
        .unwrap_err();

    let high_range = data.split_at_mut(low_idx).1;

    // Get index of first element strictly greater than fence_hi:
    let high_idx = high_range
        .binary_search_by(|x| {
            if mapper(x).le(&fence_hi) {
                Ordering::Less
            } else {
                Ordering::Greater
            }
        })
        .unwrap_err();

    high_range.split_at_mut(high_idx).0
}

fn count_by<T, K, F>(data: &[T], key: F) -> HashMap<K, u64>
where
    T: Sync,
    F: Fn(&T) -> K + Sync,
    K: Hash + Eq + Clone + Send,
{
    data.par_iter()
        .fold_with(HashMap::<K, u64>::new(), |mut acc, item| {
            acc.entry(key(item)).and_modify(|e| *e += 1).or_insert(1);
            acc
        })
        .reduce(
            || HashMap::new(),
            |mut a: HashMap<K, u64>, b: HashMap<K, u64>| {
                for (k, v) in b {
                    a.entry(k).and_modify(|e| *e += v).or_insert(v);
                }
                a
            },
        )
}

type Intermediate<'a> = (ByteRecord, &'a Building, f64);

fn compute_mappings<'a>(
    records: Vec<ByteRecord>,
    buildings: &'a UTMTree<'_, Building>,
) -> Vec<Intermediate<'a>> {
    records
        .into_par_iter()
        .filter_map(|record| {
            let x: f64 = std::str::from_utf8(&record[11])
                .unwrap()
                .parse()
                .expect("expected decimal X-coordinate");
            let y: f64 = std::str::from_utf8(&record[12])
                .unwrap()
                .parse()
                .expect("expected decimal Y-coordinate");
            let coords: UTMCoordinates = (x, y).into();

            let mut nn = (None, 0.0);
            buildings.nearest_neighbors(coords, slice::from_mut(&mut nn), f64::INFINITY);

            if nn.0.is_some() {
                let (bldg, dist_sq) = nn;
                let bldg = bldg.unwrap();
                let dist = dist_sq.sqrt();

                Some((record, bldg, dist))
            } else {
                None
            }
        })
        .collect()
}

fn process_group<'a>(
    records: Vec<ByteRecord>,
    buildings: &'a UTMTree<'_, Building>,
    filter_distance_outliers: bool,
) -> (Vec<ByteRecord>, HashMap<u32, u64>) {
    let mut mappings = compute_mappings(records, buildings);
    let data = if filter_distance_outliers {
        &*tukey_fences(&mut mappings, 1.5, |i| i.2)
    } else {
        &mappings
    };

    let counts = count_by(data, |i| i.1.id());
    let out_records = data
        .par_iter()
        .map(|x: &Intermediate<'a>| {
            let record = &x.0;
            let bldg = x.1;
            let dist = x.2;
            let count = counts.get(&bldg.id()).copied().unwrap_or(0);

            let mut out = ByteRecord::new();
            out.push_field(&record[0]);
            out.push_field(&record[2]);
            out.push_field(&record[11]);
            out.push_field(&record[12]);
            push_as_string(&mut out, &bldg.id());
            push_as_string(&mut out, &bldg.centroid().x);
            push_as_string(&mut out, &bldg.centroid().y);
            push_as_string(&mut out, &dist);
            push_as_string(&mut out, &count);

            out
        })
        .collect();

    (out_records, counts)
}

fn write_group(hour: u8, records: Vec<ByteRecord>, out_path: &Path) {
    let mut pb: PathBuf = out_path.to_path_buf();
    pb.push(format!("{:02}_mappings.csv", hour));

    let f = File::create(pb).expect("could not open file");
    let mut writer = csv::Writer::from_writer(BufWriter::new(f));
    writer
        .write_record(&[
            "VEHICLE",
            "LINK",
            "X_COORD",
            "Y_COORD",
            "BUILDING",
            "BUILDING_X",
            "BUILDING_Y",
            "DISTANCE",
            "MAPPED_VEHICLE_COUNT",
        ])
        .expect("could not write header row");

    for record in records {
        writer
            .write_byte_record(&record)
            .expect("could not write record");
    }
    writer.flush().expect("could not flush writer");
}

fn write_buildings(
    hour: u8,
    out_path: &Path,
    counts: HashMap<u32, u64>,
    building_record_starts: &HashMap<u32, ByteRecord>,
) {
    let mut pb: PathBuf = out_path.to_path_buf();
    pb.push(format!("{:02}_counts.csv", hour));

    let f = File::create(pb).expect("could not open file");
    let mut writer = csv::Writer::from_writer(BufWriter::new(f));
    writer
        .write_record(&[
            "BUILDING",
            "BUILDING_X",
            "BUILDING_Y",
            "BUILDING_AREA",
            "BUILDING_EAST",
            "BUILDING_WEST",
            "BUILDING_NORTH",
            "BUILDING_SOUTH",
            "MAPPED_VEHICLE_COUNT",
        ])
        .expect("could not write header row");

    for (id, count) in counts {
        let mut record = building_record_starts.get(&id).unwrap().clone();
        push_as_string(&mut record, &count);

        writer
            .write_byte_record(&record)
            .expect("could not write record");
    }

    writer.flush().expect("could not flush writer");
}

#[derive(Debug)]
struct Arguments {
    filter_distance_outliers: bool,
    mapping_out_path: PathBuf,
    count_out_path: PathBuf,
    buildings_path: String,
    snapshot_paths: Vec<String>,
}

fn read_args() -> Arguments {
    let mut args = env::args().skip(1);
    let mut map: HashMap<String, String> = HashMap::new();

    for arg in args.by_ref() {
        if arg == "--" {
            break;
        }

        let mut s = arg.splitn(2, '=');
        let k = s.next().unwrap().to_ascii_lowercase();
        let v = s.next().map_or_else(String::new, |x| x.into());
        map.insert(k, v);
    }

    let snapshot_paths: Vec<String> = args.collect();

    let mapping_out_path = PathBuf::from(map.get("map_out").expect("missing argument: 'map_out'"))
        .canonicalize()
        .unwrap();

    let count_out_path =
        PathBuf::from(map.get("count_out").expect("missing argument: 'count_out'"))
            .canonicalize()
            .unwrap();

    let buildings_path = map
        .get("buildings")
        .expect("missing argument: 'buildings'")
        .clone();

    Arguments {
        filter_distance_outliers: map.contains_key("filter_outliers"),
        mapping_out_path,
        count_out_path,
        buildings_path,
        snapshot_paths,
    }
}

pub fn main() {
    let args = read_args();
    let buildings = agent_mapping::load_buildings(&args.buildings_path);
    let tree = UTMTree::new(&buildings);
    let building_record_starts: HashMap<u32, ByteRecord> = buildings
        .par_iter()
        .map(|bldg| {
            let center = bldg.centroid();
            let bbox = bldg.bbox();
            let record = ByteRecord::from(vec![
                bldg.id().to_string(),
                center.x.to_string(),
                center.y.to_string(),
                bldg.area().to_string(),
                bbox.east.to_string(),
                bbox.west.to_string(),
                bbox.north.to_string(),
                bbox.south.to_string(),
            ]);

            (bldg.id(), record)
        })
        .collect();

    let groups: AgentGrouping = args
        .snapshot_paths
        .par_iter()
        .map(load_record_file)
        .map(group_records)
        .reduce(HashMap::new, merge_groups);

    for (hour, records) in groups {
        let (out_records, counts) = process_group(records, &tree, args.filter_distance_outliers);
        rayon::join(
            || {
                write_group(hour, out_records, &args.mapping_out_path);
            },
            || {
                write_buildings(hour, &args.count_out_path, counts, &building_record_starts);
            },
        );
    }
}
