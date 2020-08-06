use serde::{Deserialize, Serialize};
use std::convert::{AsMut, AsRef};

use super::UTMCoordinates;

/// A snapshot of an individual vehicle, with an associated time, position, and
/// vehicle ID.
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Agent {
    pub id: u32,
    pub time: u32,
    pub position: UTMCoordinates,
}

impl Agent {
    /// Create a new Vehicle.
    pub fn new(id: u32, time: u32, position: UTMCoordinates) -> Agent {
        Agent { id, time, position }
    }

    pub fn id(&self) -> u32 {
        self.id
    }

    pub fn time(&self) -> u32 {
        self.time
    }

    pub fn position(&self) -> UTMCoordinates {
        self.position
    }

    /// Get the UTM X-coordinate for this vehicle's position.
    pub fn x(&self) -> f64 {
        self.position.x
    }

    /// Get the UTM Y-coordinate for this vehicle's position.
    pub fn y(&self) -> f64 {
        self.position.y
    }

    /// Get the formatted time associated with this vehicle snapshot.
    pub fn formatted_time(&self) -> String {
        format_time(self.time)
    }
}

impl AsRef<UTMCoordinates> for Agent {
    fn as_ref(&self) -> &UTMCoordinates {
        &self.position
    }
}

impl AsMut<UTMCoordinates> for Agent {
    fn as_mut(&mut self) -> &mut UTMCoordinates {
        &mut self.position
    }
}

impl From<Agent> for UTMCoordinates {
    fn from(agent: Agent) -> Self {
        agent.position
    }
}

impl AsRef<u32> for Agent {
    fn as_ref(&self) -> &u32 {
        &self.id
    }
}

impl AsMut<u32> for Agent {
    fn as_mut(&mut self) -> &mut u32 {
        &mut self.id
    }
}

impl From<Agent> for u32 {
    fn from(agent: Agent) -> u32 {
        agent.id
    }
}

/// A raw vehicle simulation snapshot record, as found in both the original and
/// the preprocessed data.
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct AgentRecord {
    #[serde(alias = "VEHICLE")]
    vehicle: u32,

    #[serde(alias = "TIME", with = "timestamp_serde")]
    time: u32,

    #[serde(alias = "LINK")]
    link: u16,

    #[serde(alias = "DIR")]
    direction: u8,

    #[serde(alias = "LANE")]
    lane: u8,

    #[serde(alias = "OFFSET")]
    offset: f32,

    #[serde(alias = "DRIVER")]
    driver: u32,

    #[serde(alias = "X_COORD")]
    x: f64,

    #[serde(alias = "Y_COORD")]
    y: f64,
}

impl AgentRecord {
    pub fn vehicle(&self) -> u32 {
        self.vehicle
    }

    pub fn time(&self) -> u32 {
        self.time
    }

    pub fn link(&self) -> u16 {
        self.link
    }

    pub fn direction(&self) -> u8 {
        self.direction
    }

    pub fn lane(&self) -> u8 {
        self.lane
    }

    pub fn offset(&self) -> f32 {
        self.offset
    }

    pub fn driver(&self) -> u32 {
        self.driver
    }

    pub fn x(&self) -> f64 {
        self.x
    }

    pub fn y(&self) -> f64 {
        self.y
    }

    pub fn position(&self) -> UTMCoordinates {
        UTMCoordinates::new(self.x, self.y)
    }
}

impl From<AgentRecord> for Agent {
    fn from(record: AgentRecord) -> Self {
        Agent {
            id: record.vehicle,
            time: record.time,
            position: record.position(),
        }
    }
}

impl From<&'_ AgentRecord> for Agent {
    fn from(record: &'_ AgentRecord) -> Self {
        Agent {
            id: record.vehicle,
            time: record.time,
            position: record.position(),
        }
    }
}

fn format_time(t: u32) -> String {
    let days = t / 86400;
    let t = t % 86400;

    let hours = t / 3600;
    let t = t % 3600;

    let minutes = t / 60;
    let seconds = t % 60;

    let s1 = if days > 0 {
        format!("{:02}@", days)
    } else {
        String::new()
    };

    let s2 = if seconds > 0 {
        format!(":{:02}", seconds)
    } else {
        String::new()
    };

    format!("{}{}:{:02}{}", s1, hours, minutes, s2)
}

/// Parse a record timestamp from a vehicle simulation snapshot file.
pub fn parse_timestamp(timestamp: &str) -> u32 {
    // Timestamp strings for snapshots are in the format:
    // [day@]hour:minute[:second]
    // so, for example:
    //  1@0:59:30
    //    2:48:30
    //    0:02

    // Use rsplit with '@' to get at the hour/minute/second portion first.
    let mut split1 = timestamp.rsplit('@');
    let hms = split1.next().expect("could not split by @");

    // now parse hour:minute[:second]
    let mut split2 = hms.split(':');
    let hour: u32 = split2
        .next()
        .expect("could not get hour")
        .parse()
        .expect("invalid hour");

    let minute: u32 = split2
        .next()
        .expect("could not get minute")
        .parse()
        .expect("invalid minute");

    let second: u32 = if let Some(second) = split2.next() {
        second.parse().expect("invalid second")
    } else {
        0
    };

    // parse the day
    let day: u32 = if let Some(day) = split1.next() {
        day.parse().expect("invalid day")
    } else {
        0
    };

    (day * 86400) + (hour * 3600) + (minute * 60) + second
}

mod timestamp_serde {
    use serde::de::{self, Deserializer, Unexpected, Visitor};
    use serde::ser::Serializer;
    use std::fmt;

    struct TimestampVisitor;
    impl<'de> Visitor<'de> for TimestampVisitor {
        type Value = u32;

        fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
            formatter.write_str("either an unsigned integer < 2^32 or a string timestamp")
        }

        fn visit_str<E>(self, v: &str) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            Ok(super::parse_timestamp(v))
        }

        fn visit_i64<E>(self, v: i64) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            if v < 0 || v > (u32::MAX as i64) {
                Err(E::invalid_value(Unexpected::Signed(v), &self))
            } else {
                Ok(v as Self::Value)
            }
        }

        fn visit_u64<E>(self, v: u64) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            if v > (u32::MAX as u64) {
                Err(E::invalid_value(Unexpected::Unsigned(v), &self))
            } else {
                Ok(v as Self::Value)
            }
        }
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<u32, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_str(TimestampVisitor)
    }

    pub fn serialize<S>(time: &u32, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let s = super::format_time(*time);
        serializer.serialize_str(&s)
    }
}
