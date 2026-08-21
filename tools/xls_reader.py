"""
Readers for the measurement files in this project, using only the standard
library plus `olefile` (both available in the container; xlrd/openpyxl are not
installable here because the venv is read-only).

  read_xls(path)  -> {sheet_name: {(row, col): value}}   legacy BIFF8 .xls
  sheet_columns(cells)                                   -> {col: [values]} dense
  read_xlsx(path) -> {sheet_name: [[cell, ...], ...]}     OOXML .xlsx
"""

import re
import struct
import zipfile
from xml.etree import ElementTree as ET

import olefile

# --- BIFF record ids -------------------------------------------------------
BOF, EOF = 0x0809, 0x000A
BOUNDSHEET = 0x0085
SST, CONTINUE = 0x00FC, 0x003C
LABELSST, LABEL = 0x00FD, 0x0204
NUMBER, RK, MULRK = 0x0203, 0x027E, 0x00BD
FORMULA = 0x0006


def _rk_value(rk):
    """Decode a 32-bit RK number (BIFF packed float)."""
    cents, is_int = rk & 1, rk & 2
    v = rk & 0xFFFFFFFC
    if is_int:
        i = v - 0x100000000 if v & 0x80000000 else v
        x = float(i >> 2)
    else:
        x = struct.unpack("<d", struct.pack("<Q", (v & 0xFFFFFFFF) << 32))[0]
    return x / 100.0 if cents else x


def _records(data, pos=0):
    """Yield (id, payload) walking the BIFF record stream from `pos`."""
    while pos + 4 <= len(data):
        rid, ln = struct.unpack("<HH", data[pos:pos + 4])
        pos += 4
        yield rid, data[pos:pos + ln]
        pos += ln


def _unicode_string(buf, off, cch, rich_run_bytes=False):
    """Decode a BIFF8 XLUnicodeString body starting at `off` (after the count)."""
    flags = buf[off]
    off += 1
    rich = flags & 0x08
    ext = flags & 0x04
    nrun = cext = 0
    if rich:
        nrun = struct.unpack("<H", buf[off:off + 2])[0]
        off += 2
    if ext:
        cext = struct.unpack("<I", buf[off:off + 4])[0]
        off += 4
    if flags & 0x01:  # UTF-16LE
        raw = buf[off:off + cch * 2]
        off += cch * 2
        s = raw.decode("utf-16-le", "replace")
    else:
        raw = buf[off:off + cch]
        off += cch
        s = raw.decode("latin-1", "replace")
    off += nrun * 4 + cext
    return s, off


def _parse_sst(payload):
    """Minimal shared-string-table parse (no CONTINUE splitting mid-string)."""
    out = []
    try:
        total, unique = struct.unpack("<II", payload[:8])
        off = 8
        for _ in range(unique):
            if off + 2 > len(payload):
                break
            cch = struct.unpack("<H", payload[off:off + 2])[0]
            s, off = _unicode_string(payload, off + 2, cch)
            out.append(s)
    except Exception:
        pass
    return out


def read_xls(path):
    """Read a legacy BIFF8 .xls into {sheet_name: {(row, col): value}}."""
    ole = olefile.OleFileIO(path)
    stream = next(n for n in ole.listdir() if n[-1] in ("Workbook", "Book"))
    data = ole.openstream(stream).read()

    # Pass 1 - globals: sheet names, their stream offsets, and the SST.
    sheets, sst, pos, depth = [], [], 0, 0
    for rid, body in _records(data):
        if rid == BOF:
            depth += 1
            if depth > 1:
                break
        elif rid == BOUNDSHEET and len(body) >= 8:
            off = struct.unpack("<I", body[0:4])[0]
            cch, flags = body[6], body[7]
            name = (body[8:8 + cch * 2].decode("utf-16-le", "replace")
                    if flags & 0x01 else
                    body[8:8 + cch].decode("latin-1", "replace"))
            sheets.append((off, name))
        elif rid == SST:
            sst = _parse_sst(body)

    # Pass 2 - one substream per sheet.
    result = {}
    for off, name in sheets:
        cells, depth = {}, 0
        for rid, body in _records(data, off):
            if rid == BOF:
                depth += 1
            elif rid == EOF:
                depth -= 1
                if depth <= 0:
                    break
            elif rid == NUMBER and len(body) >= 14:
                r, c, _, v = struct.unpack("<HHHd", body[:14])
                cells[(r, c)] = v
            elif rid == RK and len(body) >= 10:
                r, c = struct.unpack("<HH", body[:4])
                cells[(r, c)] = _rk_value(struct.unpack("<I", body[6:10])[0])
            elif rid == MULRK and len(body) >= 6:
                r, c0 = struct.unpack("<HH", body[:4])
                for i in range((len(body) - 6) // 6):
                    raw = struct.unpack("<I", body[4 + i * 6 + 2:4 + i * 6 + 6])[0]
                    cells[(r, c0 + i)] = _rk_value(raw)
            elif rid == FORMULA and len(body) >= 14:
                r, c = struct.unpack("<HH", body[:4])
                if body[12:14] != b"\xff\xff":  # numeric result
                    cells[(r, c)] = struct.unpack("<d", body[6:14])[0]
            elif rid == LABELSST and len(body) >= 10:
                r, c = struct.unpack("<HH", body[:4])
                idx = struct.unpack("<I", body[6:10])[0]
                if idx < len(sst):
                    cells[(r, c)] = sst[idx]
            elif rid == LABEL and len(body) >= 8:
                r, c = struct.unpack("<HH", body[:4])
                cch = struct.unpack("<H", body[6:8])[0]
                try:
                    cells[(r, c)] = _unicode_string(body, 8, cch)[0]
                except Exception:
                    pass
        result[name] = cells
    return result


def sheet_columns(cells, numeric_only=True):
    """Turn {(row, col): value} into {col: [values in row order]}."""
    if not cells:
        return {}
    cols = {}
    for (r, c), v in cells.items():
        if numeric_only and not isinstance(v, float):
            continue
        cols.setdefault(c, []).append((r, v))
    return {c: [v for _, v in sorted(rv)] for c, rv in sorted(cols.items())}


# --- OOXML .xlsx -----------------------------------------------------------
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_xlsx(path):
    """Read an .xlsx into {sheet_name: [[cell, ...], ...]} (stdlib only)."""
    z = zipfile.ZipFile(path)
    names = z.namelist()

    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in si.iter(_NS + "t"))
                  for si in root.findall(_NS + "si")]

    # sheet name <- workbook.xml, in the same order as sheetN.xml files
    labels = []
    if "xl/workbook.xml" in names:
        root = ET.fromstring(z.read("xl/workbook.xml"))
        labels = [s.get("name") for s in root.iter(_NS + "sheet")]

    out = {}
    paths = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml", n))
    for i, sp in enumerate(paths):
        root = ET.fromstring(z.read(sp))
        rows = []
        for row in root.iter(_NS + "row"):
            cells = []
            for c in row.findall(_NS + "c"):
                t = c.get("t")
                if t == "inlineStr":
                    cells.append("".join(x.text or "" for x in c.iter(_NS + "t")))
                    continue
                v = c.find(_NS + "v")
                if v is None or v.text is None:
                    cells.append(None)
                elif t == "s":
                    cells.append(shared[int(v.text)])
                elif t == "str":
                    cells.append(v.text)
                else:
                    try:
                        cells.append(float(v.text))
                    except ValueError:
                        cells.append(v.text)
            rows.append(cells)
        out[labels[i] if i < len(labels) else f"sheet{i + 1}"] = rows
    return out
