use once_cell::sync::OnceCell;
use rayon::prelude::*;

use crate::{Agent, Building, Region, UTMCoordinates, ZValue};

/// Process a single region or quadrant.
/// The `agents` must be sorted by Z-order.
/// Buildings must be a Vec of building references with at least one corner
/// within this region.
fn process_region<'a, F>(
    split_threshold: usize,
    prefix: ZValue,
    depth: u64,
    region: Region,
    agents: &[(&Agent, ZValue, OnceCell<&'a Building>)],
    buildings: Vec<&'a Building>,
    mapper: &F,
) where
    for<'b> F: Fn(&Agent, &[&'b Building]) -> &'b Building + Sync,
{
    // No mappings to be done here
    if agents.len() == 0 || buildings.len() == 0 {
        return;
    }

    // If we're below the split threshold, then just process this area
    if agents.len() < split_threshold || buildings.len() < split_threshold {
        for (agent, _, out) in agents {
            let mapping = (*mapper)(*agent, &buildings);

            // the only way this can fail is if an agent were in multiple
            // regions at once, somehow
            out.set(mapping).expect("could not set agent mapping");
        }

        return;
    }

    // Need to divide region into quadrants:

    // Compute Z-value prefixes for SW, NE, and SE quadrants:
    let x_bit: u64 = 0x4000_0000_0000_0000 >> (2 * depth);
    let y_bit: u64 = 0x8000_0000_0000_0000 >> (2 * depth);
    let p: u64 = prefix.into();
    let nw_prefix = ZValue::from_raw(p | y_bit);
    let se_prefix = ZValue::from_raw(p | x_bit);
    let ne_prefix = ZValue::from_raw(p | y_bit | x_bit);

    // Split agents using z-values:
    let (agents_s, agents_n) = agents.split_at(find_split(agents, nw_prefix));
    let (agents_nw, agents_ne) = agents_n.split_at(find_split(agents_n, ne_prefix));
    let (agents_sw, agents_se) = agents_s.split_at(find_split(agents_s, se_prefix));

    // Collect buildings that lie in each quadrant
    // (buildings can be duplicated if they have corners in multiple quadrants)
    let mut bldgs_ne = Vec::new();
    let mut bldgs_nw = Vec::new();
    let mut bldgs_se = Vec::new();
    let mut bldgs_sw = Vec::new();
    let region_center = region.center();

    // compute quadrant bounds
    let ne = Region::new(region.east, region_center.x, region.north, region_center.y);
    let nw = Region::new(region_center.x, region.west, region.north, region_center.y);
    let se = Region::new(region.east, region_center.x, region_center.y, region.south);
    let sw = Region::new(region_center.x, region.west, region_center.y, region.south);

    for b in buildings {
        let bbox = b.bbox();
        let north = bbox.north > region_center.y;
        let south = bbox.south < region_center.y;
        let west = bbox.west < region_center.x;
        let east = bbox.east > region_center.x;

        if north && east {
            bldgs_ne.push(b);
        }

        if north && west {
            bldgs_nw.push(b);
        }

        if south && east {
            bldgs_se.push(b);
        }

        if south && west {
            bldgs_sw.push(b);
        }
    }

    // Recurse into each quadrant
    rayon::join(
        || {
            rayon::join(
                || {
                    process_region(
                        split_threshold,
                        nw_prefix,
                        depth + 1,
                        nw,
                        agents_nw,
                        bldgs_nw,
                        mapper,
                    )
                },
                || {
                    process_region(
                        split_threshold,
                        ne_prefix,
                        depth + 1,
                        ne,
                        agents_ne,
                        bldgs_ne,
                        mapper,
                    )
                },
            )
        },
        || {
            rayon::join(
                || {
                    process_region(
                        split_threshold,
                        prefix,
                        depth + 1,
                        sw,
                        agents_sw,
                        bldgs_sw,
                        mapper,
                    )
                },
                || {
                    process_region(
                        split_threshold,
                        se_prefix,
                        depth + 1,
                        se,
                        agents_se,
                        bldgs_se,
                        mapper,
                    )
                },
            )
        },
    );
}

fn find_split(arr: &[(&Agent, ZValue, OnceCell<&Building>)], query: ZValue) -> usize {
    match arr.binary_search_by_key(&query, |t| t.1) {
        Err(idx) => idx,
        Ok(start) => arr
            .iter()
            .enumerate()
            .rev()
            .skip(arr.len() - start)
            .find(|&(_, t)| t.1 < query)
            .map_or(0, |(i, _)| i + 1),
    }
}

fn reduce_region_point(mut a: Region, b: UTMCoordinates) -> Region {
    if b.x < a.west {
        a.west = b.x;
    }

    if b.x > a.east {
        a.east = b.x;
    }

    if b.y > a.north {
        a.north = b.y;
    }

    if b.y < a.south {
        a.south = b.y;
    }

    a
}

fn reduce_regions(mut a: Region, b: &Region) -> Region {
    if b.west < a.west {
        a.west = b.west;
    }

    if b.east > a.east {
        a.east = b.east;
    }

    if b.south < a.south {
        a.south = b.south;
    }

    if b.north > a.north {
        a.north = b.north;
    }

    a
}

fn min_region() -> Region {
    Region::new(
        f64::NEG_INFINITY,
        f64::INFINITY,
        f64::NEG_INFINITY,
        f64::INFINITY,
    )
}

/// Map a set of `Agent`s to a set of `Building`s, using a customizable
/// `mapper` function.
///
/// The `mapper` function will be called once for each `Agent`, and will be passed
/// a slice containing references to nearby `Building`s. The `mapper` must then
/// map the passed agent to one of these buildings by selecting and returning it.
/// The order in which the `mapper` function will be called for each agent is
/// unpredictable.
///
/// `split_threshold` specifies the number of agents and buildings above which
/// quadtree cells will be split, and bounds the number of buildings each invocation
/// of the `mapper` function must consider.
///
/// The overall mapping is done in parallel via Rayon, therefore the `mapper`
/// function must be `Sync`.
///
/// This function returns an iterator over pairs of references to mapped
/// `Agent`s and `Building`s.
pub fn map_vehicles<'a, F>(
    split_threshold: usize,
    agents: &'a [Agent],
    buildings: &'a [Building],
    mapper: F,
) -> impl Iterator<Item = (&'a Agent, &'a Building)>
where
    for<'b> F: Fn(&Agent, &[&'b Building]) -> &'b Building + Sync,
{
    // Compute region spanned by all agents and buildings:
    let buildings_bbox: Region = buildings
        .par_iter()
        .fold(min_region, |r, bldg| reduce_regions(r, bldg.bbox()))
        .reduce(min_region, |r1, r2| reduce_regions(r1, &r2));

    let agents_bbox: Region = agents
        .par_iter()
        .fold(min_region, |r, a| reduce_region_point(r, a.position()))
        .reduce(min_region, |r1, r2| reduce_regions(r1, &r2));

    let region = reduce_regions(buildings_bbox, &agents_bbox);

    // validate region:
    assert!(region.west < region.east, "invalid region east-west length");
    assert!(
        region.south < region.north,
        "invalid region north-south length"
    );

    // allocate temp storage for agents:
    let mut agent_data: Vec<(&Agent, ZValue, OnceCell<&Building>)> = agents
        .par_iter()
        .map(|a| {
            let z = a
                .position()
                .z_value(&region)
                .expect("could not normalize agent position?");
            (a, z, OnceCell::new())
        })
        .collect();

    // sort agents by Z-value:
    agent_data.par_sort_unstable_by_key(|m| m.1);

    let bldgs: Vec<&Building> = buildings.iter().collect();

    // Run the algorithm:
    process_region(
        split_threshold,
        ZValue::from_raw(0),
        0,
        region,
        &agent_data,
        bldgs,
        &mapper,
    );

    agent_data
        .into_iter()
        .filter_map(|(agent, _, cell)| cell.get().map(|&bldg| (agent, bldg)))
}
