from __future__ import annotations
import csv
import datetime
from collections import deque
from typing import List, Dict, TextIO, Deque, Iterator


def parse_timestamp(ts: str) -> int:
    """Converts an (DD@)HH:MM(:SS) timestamp into the number of 30-second increments
    since 00:00:00."""

    out = 0

    try:
        days, ts = ts.split("@")
        out += int(days) * 24 * 120 # DD@HH:MM:SS
    except ValueError:
        # no '@' in string
        pass

    parts = ts.split(":")
    out += (int(parts[0]) * 60 * 2) + (int(parts[1]) * 2)

    if len(parts) > 2:
        # if there's a :30 part, add 1 to the increment count
        out += 1

    return out


class Frame:
    def __init__(
        self,
        vid: int,
        time: int,
        link: int,
        direct: int,
        lane: int,
        offset: float,
        speed: float,
        accel: float,
        vtype: int,
        driver: int,
        passengers: int,
        x: float,
        y: float,
    ):
        self.vid = vid
        self.time = time
        self.link = link
        self.direct = direct
        self.lane = lane
        self.offset = offset
        self.speed = speed
        self.accel = accel
        self.vtype = vtype
        self.driver = driver
        self.passengers = passengers
        self.x = x
        self.y = y

    @classmethod
    def parse_row(cls, row):
        vid = int(row[0])
        time = parse_timestamp(row[1])
        link = int(row[2])
        direct = int(row[3])
        lane = int(row[4])
        offset = float(row[5])
        speed = float(row[6])
        accel = float(row[7])
        vtype = int(row[8])
        driver = int(row[9])
        passengers = int(row[10])
        x = float(row[11])
        y = float(row[12])

        return cls(
            vid,
            time,
            link,
            direct,
            lane,
            offset,
            speed,
            accel,
            vtype,
            driver,
            passengers,
            x,
            y,
        )

    def timedelta(self) -> datetime.timedelta:
        """Get the time of this frame as a `datetime.timedelta` object."""
        return datetime.timedelta(seconds=self.time * 30)

    def timestamp(self) -> str:
        """Get the time of this frame as a string timestamp."""
        h = int(self.time / 120)
        m = int((self.time % 120) / 2)
        
        res = "{}:{:02d}".format(h, m)
        if self.time % 2 == 1:
            res += ":30"
        
        return res


class Trace:
    def __init__(self):
        self.frames: Deque[Frame] = deque()

    def append(self, frame: Frame):
        self.frames.append(frame)

    def merge(self, other: Trace):
        result = deque()

        while len(self.frames) > 0 and len(other.frames) > 0:
            if self.frames[0].time < other.frames[0].time:
                result.append(self.frames.popleft())
            else:
                result.append(other.frames.popleft())

        if len(self.frames) > 0:
            result.extend(self.frames)

        if len(other.frames) > 0:
            result.extend(other.frames)

        self.frames = result
        other.frames = deque()

    def __len__(self):
        return len(self.frames)

    def __iter__(self) -> Iterator[Frame]:
        return self.frames.__iter__()


class Snapshot:
    def __init__(self):
        self.frames: List[Frame] = []
        self.traces: Dict[int, Trace] = {}

    def append(self, frame: Frame):
        """Append a new frame to this Snapshot.

        Frames are assumed to be appended in ascending time order.
        """
        self.frames.append(frame)

        try:
            self.traces[frame.vid].append(frame)
        except KeyError:
            trace = Trace()
            trace.append(frame)

            self.traces[frame.vid] = trace

    def write(self, fp: TextIO):
        writer = csv.writer(fp)
        writer.writerow(['VEHICLE', 'TIME', 'LINK', 'DIR', 'LANE', 'OFFSET', 'SPEED', 'ACCEL', 'VEH_TYPE',
                         'DRIVER', 'PASSENGERS', 'X_COORD', 'Y_COORD'])
        for frame in self.frames:
            writer.writerow([frame.vid, frame.timestamp(), frame.link, frame.direct, frame.lane, frame.offset,
                             frame.speed, frame.accel, frame.vtype, frame.driver, frame.passengers, frame.x, frame.y])

    @classmethod
    def load(cls, fp: TextIO, ordered=True):
        """Load a snapshot from a CSV file.
        
        If ordered is True, the input CSV file is assumed to be in sorted order
        with respect to time.
        """

        result = cls()
        reader = csv.reader(fp)

        next(reader)  # skip the header row

        if ordered:
            for row in reader:
                result.append(Frame.parse_row(row))
        else:
            frames = sorted(
                (Frame.parse_row(row) for row in reader), key=lambda frame: frame.time
            )

            for frame in frames:
                result.append(frame)

        return result

    def iter_time(self) -> Iterator[Frame]:
        """Iterate over the Frames in this snapshot by time."""
        return self.frames.__iter__()

    def iter_traces(self) -> Iterator[Trace]:
        """Iterate over the Traces in this snapshot."""
        return self.traces.values().__iter__()
