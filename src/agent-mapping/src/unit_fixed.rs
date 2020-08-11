use std::fmt;
use std::fmt::Display;

/// A number in the range [0, 1], represented in a 32-bit fixed-point format.
///
/// The representation consists of 32 fractional bits-- in other words,
/// given an integer `i` in this format, the actual number `i` represents is
/// `r = (i / 4294967296.0)`.
///
/// The conversion (using `From<f64>`) clips numbers outside the range [0,1):
///  - An input number less than 0 returns 0
///  - An input > 1 returns 0xFFFF_FFFF (which represents 1).
#[derive(Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd, Hash)]
#[repr(transparent)]
pub struct UnitFixedPoint(u32);

impl From<f64> for UnitFixedPoint {
    fn from(x: f64) -> UnitFixedPoint {
        if x.is_nan() {
            panic!("cannot convert NaN to UnitFixedPoint");
        } else if x <= 0.0 {
            UnitFixedPoint(0)
        } else if x >= 1.0 {
            UnitFixedPoint(u32::MAX)
        } else {
            // NaN and +/- infinity are handled above
            UnitFixedPoint((x * 4294967295.0) as u32)
        }
    }
}

impl From<UnitFixedPoint> for f64 {
    fn from(x: UnitFixedPoint) -> f64 {
        (x.0 as f64) / 4294967295.0
    }
}

impl From<u32> for UnitFixedPoint {
    fn from(v: u32) -> Self {
        UnitFixedPoint(v)
    }
}

impl From<UnitFixedPoint> for u32 {
    fn from(v: UnitFixedPoint) -> Self {
        v.0
    }
}

impl Display for UnitFixedPoint {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x: f64 = (*self).into();
        write!(f, "{}", x)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use quickcheck::TestResult;

    #[quickcheck]
    fn quickcheck_comparison(f0: f64, f1: f64, f2: f64, f3: f64) -> TestResult {
        let mut d = [f0, f1, f2, f3];
        d.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap());

        let range = d[3] - d[0];
        if range == 0.0 {
            return TestResult::discard();
        }

        let f1 = (d[1] - d[0]) / range;
        let f2 = (d[2] - d[0]) / range;

        if f1.is_nan() || f2.is_nan() || (f1 < 0.0) || (f1 >= 1.0) || (f2 < 0.0) || (f2 >= 1.0) {
            return TestResult::discard();
        }

        let n1: UnitFixedPoint = f1.into();
        let n2: UnitFixedPoint = f2.into();

        if let Some(c1) = f1.partial_cmp(&f2) {
            TestResult::from_bool(c1 == n1.cmp(&n2))
        } else {
            TestResult::discard()
        }
    }
}
