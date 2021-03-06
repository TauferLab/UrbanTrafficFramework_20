use std::cmp::Ordering;

use crate::UnitFixedPoint;

const MORTON_TABLE: [u16; 256] = [
    0x0000, 0x0001, 0x0004, 0x0005, 0x0010, 0x0011, 0x0014, 0x0015, 0x0040, 0x0041, 0x0044, 0x0045,
    0x0050, 0x0051, 0x0054, 0x0055, 0x0100, 0x0101, 0x0104, 0x0105, 0x0110, 0x0111, 0x0114, 0x0115,
    0x0140, 0x0141, 0x0144, 0x0145, 0x0150, 0x0151, 0x0154, 0x0155, 0x0400, 0x0401, 0x0404, 0x0405,
    0x0410, 0x0411, 0x0414, 0x0415, 0x0440, 0x0441, 0x0444, 0x0445, 0x0450, 0x0451, 0x0454, 0x0455,
    0x0500, 0x0501, 0x0504, 0x0505, 0x0510, 0x0511, 0x0514, 0x0515, 0x0540, 0x0541, 0x0544, 0x0545,
    0x0550, 0x0551, 0x0554, 0x0555, 0x1000, 0x1001, 0x1004, 0x1005, 0x1010, 0x1011, 0x1014, 0x1015,
    0x1040, 0x1041, 0x1044, 0x1045, 0x1050, 0x1051, 0x1054, 0x1055, 0x1100, 0x1101, 0x1104, 0x1105,
    0x1110, 0x1111, 0x1114, 0x1115, 0x1140, 0x1141, 0x1144, 0x1145, 0x1150, 0x1151, 0x1154, 0x1155,
    0x1400, 0x1401, 0x1404, 0x1405, 0x1410, 0x1411, 0x1414, 0x1415, 0x1440, 0x1441, 0x1444, 0x1445,
    0x1450, 0x1451, 0x1454, 0x1455, 0x1500, 0x1501, 0x1504, 0x1505, 0x1510, 0x1511, 0x1514, 0x1515,
    0x1540, 0x1541, 0x1544, 0x1545, 0x1550, 0x1551, 0x1554, 0x1555, 0x4000, 0x4001, 0x4004, 0x4005,
    0x4010, 0x4011, 0x4014, 0x4015, 0x4040, 0x4041, 0x4044, 0x4045, 0x4050, 0x4051, 0x4054, 0x4055,
    0x4100, 0x4101, 0x4104, 0x4105, 0x4110, 0x4111, 0x4114, 0x4115, 0x4140, 0x4141, 0x4144, 0x4145,
    0x4150, 0x4151, 0x4154, 0x4155, 0x4400, 0x4401, 0x4404, 0x4405, 0x4410, 0x4411, 0x4414, 0x4415,
    0x4440, 0x4441, 0x4444, 0x4445, 0x4450, 0x4451, 0x4454, 0x4455, 0x4500, 0x4501, 0x4504, 0x4505,
    0x4510, 0x4511, 0x4514, 0x4515, 0x4540, 0x4541, 0x4544, 0x4545, 0x4550, 0x4551, 0x4554, 0x4555,
    0x5000, 0x5001, 0x5004, 0x5005, 0x5010, 0x5011, 0x5014, 0x5015, 0x5040, 0x5041, 0x5044, 0x5045,
    0x5050, 0x5051, 0x5054, 0x5055, 0x5100, 0x5101, 0x5104, 0x5105, 0x5110, 0x5111, 0x5114, 0x5115,
    0x5140, 0x5141, 0x5144, 0x5145, 0x5150, 0x5151, 0x5154, 0x5155, 0x5400, 0x5401, 0x5404, 0x5405,
    0x5410, 0x5411, 0x5414, 0x5415, 0x5440, 0x5441, 0x5444, 0x5445, 0x5450, 0x5451, 0x5454, 0x5455,
    0x5500, 0x5501, 0x5504, 0x5505, 0x5510, 0x5511, 0x5514, 0x5515, 0x5540, 0x5541, 0x5544, 0x5545,
    0x5550, 0x5551, 0x5554, 0x5555,
];

const X_MASK: u64 = 0x5555_5555_5555_5555;
const Y_MASK: u64 = 0xAAAA_AAAA_AAAA_AAAA;

/// Interleave two bytes into a 16-bit Morton number.
#[inline(always)]
fn interleave_8(x: u8, y: u8) -> u64 {
    (MORTON_TABLE[x as usize] | (MORTON_TABLE[y as usize] << 1)) as u64
}

/// A 64-bit z-value.
#[repr(transparent)]
#[derive(Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct ZValue(u64);

impl ZValue {
    /// Compute a z-value from two 32-bit integer coordinates.
    #[inline(always)]
    pub fn new(x: u32, y: u32) -> ZValue {
        let x = x.to_le_bytes();
        let y = y.to_le_bytes();

        ZValue(
            interleave_8(x[0], y[0])
                | (interleave_8(x[1], y[1]) << 16)
                | (interleave_8(x[2], y[2]) << 32)
                | (interleave_8(x[3], y[3]) << 48),
        )
    }

    pub fn from_fp(x: UnitFixedPoint, y: UnitFixedPoint) -> ZValue {
        Self::new(x.into(), y.into())
    }

    pub fn from_raw(v: u64) -> ZValue {
        ZValue(v)
    }

    pub fn x_bits(self) -> u64 {
        self.0 & X_MASK
    }

    pub fn y_bits(self) -> u64 {
        self.0 & Y_MASK
    }

    pub fn cmp_x(self, other: ZValue) -> Ordering {
        self.x_bits().cmp(&other.x_bits())
    }

    pub fn cmp_y(self, other: ZValue) -> Ordering {
        self.y_bits().cmp(&other.y_bits())
    }
}

impl From<(u32, u32)> for ZValue {
    fn from(xy: (u32, u32)) -> Self {
        ZValue::new(xy.0, xy.1)
    }
}

impl From<(UnitFixedPoint, UnitFixedPoint)> for ZValue {
    fn from(xy: (UnitFixedPoint, UnitFixedPoint)) -> Self {
        ZValue::from_fp(xy.0, xy.1)
    }
}

impl From<ZValue> for u64 {
    fn from(v: ZValue) -> Self {
        v.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[quickcheck]
    fn quickcheck_x_cmp(p1: (u32, u32), p2: (u32, u32)) -> bool {
        let z1: ZValue = p1.into();
        let z2: ZValue = p2.into();

        let o1 = p1.0.cmp(&p2.0);
        let o2 = z1.x_bits().cmp(&z2.x_bits());
        let o3 = z1.cmp_x(z2);

        (o1 == o2) && (o2 == o3)
    }

    #[quickcheck]
    fn quickcheck_y_cmp(p1: (u32, u32), p2: (u32, u32)) -> bool {
        let z1: ZValue = p1.into();
        let z2: ZValue = p2.into();

        let o1 = p1.1.cmp(&p2.1);
        let o2 = z1.y_bits().cmp(&z2.y_bits());
        let o3 = z1.cmp_y(z2);

        (o1 == o2) && (o2 == o3)
    }

    #[quickcheck]
    fn quickcheck_z_cmp(p1: (u32, u32), p2: (u32, u32)) -> bool {
        let z1: ZValue = p1.into();
        let z2: ZValue = p2.into();

        let m1 = p1.0 ^ p2.0;
        let m2 = p1.1 ^ p2.1;

        let expected = if m1.leading_zeros() < m2.leading_zeros() {
            // x-coordinate difference MSB is higher
            p1.0.cmp(&p2.0)
        } else {
            // y-coordinate difference MSB is higher
            p1.1.cmp(&p2.1)
        };

        (z1.cmp(&z2)) == expected
    }
}
