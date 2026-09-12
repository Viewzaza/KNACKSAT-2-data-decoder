"""Minimal KISS + AX.25 UI-frame parsing (no external dependencies).

gr_satellites' --kiss_out writes standard KISS-framed AX.25 packets. We only
need to unwrap KISS escaping and pull apart the AX.25 header so the frontend
can show source/destination callsigns instead of a wall of hex.
"""
from dataclasses import dataclass, field

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD


def split_kiss_frames(data: bytes) -> list[bytes]:
    """Unescape a KISS byte stream into a list of raw AX.25 frames."""
    frames = []
    current = bytearray()
    in_frame = False
    escaped = False

    for byte in data:
        if byte == FEND:
            if in_frame and current:
                frames.append(bytes(current))
            current = bytearray()
            in_frame = True
            escaped = False
            continue
        if not in_frame:
            continue
        if escaped:
            if byte == TFEND:
                current.append(FEND)
            elif byte == TFESC:
                current.append(FESC)
            else:
                current.append(byte)
            escaped = False
            continue
        if byte == FESC:
            escaped = True
            continue
        current.append(byte)

    if in_frame and current:
        frames.append(bytes(current))

    # First byte of each frame is the KISS command/port byte (0x00 = data on port 0)
    return [f[1:] for f in frames if len(f) > 1]


@dataclass
class Ax25Address:
    callsign: str
    ssid: int


@dataclass
class Ax25Frame:
    dest: Ax25Address
    src: Ax25Address
    digipeaters: list[Ax25Address] = field(default_factory=list)
    control: int | None = None
    pid: int | None = None
    info: bytes = b""

    def info_hex(self) -> str:
        return self.info.hex()

    def info_ascii(self) -> str:
        return "".join(chr(b) if 32 <= b < 127 else "." for b in self.info)


def _decode_address(raw: bytes) -> tuple[Ax25Address, bool]:
    callsign = "".join(chr(b >> 1) for b in raw[:6]).strip()
    ssid = (raw[6] >> 1) & 0x0F
    is_last = bool(raw[6] & 0x01)
    return Ax25Address(callsign, ssid), is_last


def parse_ax25(raw: bytes) -> Ax25Frame | None:
    """Parse a raw (unescaped) AX.25 UI frame. Returns None if too short/malformed."""
    if len(raw) < 15:
        return None

    dest, last = _decode_address(raw[0:7])
    src, last = _decode_address(raw[7:14])
    offset = 14
    digipeaters = []

    while not last:
        if offset + 7 > len(raw):
            return None
        addr, last = _decode_address(raw[offset : offset + 7])
        digipeaters.append(addr)
        offset += 7

    if offset + 2 > len(raw):
        return None

    control = raw[offset]
    pid = raw[offset + 1]
    info = raw[offset + 2 :]

    return Ax25Frame(dest=dest, src=src, digipeaters=digipeaters, control=control, pid=pid, info=info)


def parse_kiss_file(path) -> list[dict]:
    with open(path, "rb") as f:
        data = f.read()

    frames = []
    for raw in split_kiss_frames(data):
        parsed = parse_ax25(raw)
        if parsed is None:
            frames.append({"raw_hex": raw.hex(), "parsed": False})
            continue
        frames.append(
            {
                "parsed": True,
                "dest": f"{parsed.dest.callsign}-{parsed.dest.ssid}",
                "src": f"{parsed.src.callsign}-{parsed.src.ssid}",
                "digipeaters": [f"{a.callsign}-{a.ssid}" for a in parsed.digipeaters],
                "control": parsed.control,
                "pid": parsed.pid,
                "info_hex": parsed.info_hex(),
                "info_ascii": parsed.info_ascii(),
                "info_len": len(parsed.info),
            }
        )
    return frames
