# dvdvr_split.py — corrected, lossless DVD-VR splitter (v2.1.0)

A drop-in replacement for `splitter.py` that fixes the IFO parsing and adds
zh / ja / en UI plus IFO-timestamp file naming.

Japanese / 日本語概要は末尾にあります。

---

## Why the current splitter produces empty files

`splitter.py` reads three fields from the IFO:

| offset | current code calls it | what it really is |
|---|---|---|
| `0x100` | start of the “clip table” | `pgit_sa` — **Program Information Table** |
| `0x104` | end of the “clip table” | `M_AVFIT`-ish end pointer |
| `0x130` | start of the “title table” | `def_psi_sa` — default Program Set Info (title text) |

It then walks that block looking for the 2-byte markers `0x6540` / `0x32A0`
and treats every hit as a clip, taking a 4-byte duration at `+4`.

On discs written by some recorders (verified: **Hitachi DZ-GX20**, DVD-RAM,
VR mode) those bytes are actually playlist/date data, so the “clips” come out
with durations of `0`, `1` PTS tick (`1/90000 s`) or one bogus huge value:

```
31 “clips” parsed  →  30 files written
   27 files = 0 bytes
    1 file  = 1 frame     (0.032 s)
    1 file  = 11 frames   (0.384 s)
    1 file  = whole movie (66.5 MB)
ffmpeg also aborted on one clip: “Invalid duration for option t: 1.111e-05”
```

## What the real structure is

```
0x000  "DVD_RTR_VMG0"
0x00C  RTR_VMG_EA
0x100  pgit_sa     → pgiti{ zero(2), nr_of_pgi(1), nr_of_vob_formats(1), pgit_ea(4) }
                     vob_format_t × nr_of_vob_formats   (60 bytes each)
                     pgi_gi{ nr_of_programs(2) }
                     vvobi_sa[program]  (4-byte offsets, relative to pgit_sa)
0x130  def_psi_sa  → title strings

vvob_t (21 bytes): attr(2) rec_time(5) data1(1) format_id(1) v_s_ptm(4+2) v_e_ptm(4+2)
  then:  (attr & 0x80 ? adj_vob(12) : 0) + 2 bytes
         vobu_map{ n_time(2), n_vobu(2), time_off(2), vob_off(4 sectors) }
         time_info × n_time      (7 bytes each)
         vobu_info × n_vobu      (3 bytes each, low 14 bits = sector count)
```

So program *N* occupies a **contiguous byte range** in `VR_MOVIE.VRO`:

```
start  = vob_off * 2048
length = Σ(vobu_size) * 2048
```

Copy that range and you are done — no re-encode, no ffmpeg, VOBU-exact cuts.
(This is the same model pixelb/dvd-vr uses.)

## Verification on the test disc (Hitachi DZ-GX20)

| | IFO | frames after export |
|---|---|---|
| program 1 | 2026-11-11 17:36:20, 00:01:02.562, 45.0 MB, offset 0 | 1875 ✓ |
| program 2 | 2026-11-11 17:50:32, 00:00:30.030, 21.6 MB, offset 47,228,928 | 900 ✓ |

Total 66.6 MB / 92.59 s — matches decoding the whole VRO (2775 frames).
Byte counts match exactly (`47,228,928` / `22,657,024`), and program 2 starts
exactly where program 1 ends.

## What v2 adds

* correct RTR_VMG parsing, with bounds checks at every offset
* **zh / ja / en** UI language switch (persisted in `%APPDATA%\DVDVRSplitter\config.json`),
  `--lang zh|ja|en` on the command line
* output files are named from the **recording date/time stored in the IFO**
  (`2026-11-11_17-36-20.mpg`), falling back to `program_01.mpg` when absent
* export runs in a worker thread with progress and Cancel
* clear errors instead of silent 0-byte output: wrong IFO type, damaged IFO,
  IFO/VRO mismatch, CPRM-encrypted disc
* optional `--remux` (ffmpeg `-c copy`) for a cleaner MPEG-PS

## Usage

```bat
python dvdvr_split.py                     :: GUI
python dvdvr_split.py --ifo G:\DVD_RTAV\VR_MANGR.IFO --vro G:\DVD_RTAV\VR_MOVIE.VRO --list
python dvdvr_split.py --ifo ... --vro ... -o D:\out --programs 1,2 [--remux] [--lang ja]
```

Requires Python 3.9+; GUI needs `PySide6`; `--remux` needs `ffmpeg`.
License: GPL-3.0 (same as the project).

---

## 日本語

現行の `splitter.py` は IFO の `0x100`（pgit_sa = 番組情報テーブル）を
「クリップテーブル」と誤解し、`0x6540`/`0x32A0` の 2 バイトマーカーで
レコードを推測しています。日立 DZ-GX20 で録画した DVD-RAM（VR モード）では
これが 31 個の偽クリップを生み、うち 27 個が 0 バイトの .mpg になりました。

本バージョンは RTR_VMG の実際の構造（pgiti → vob_format → pgi_gi →
vvobi_sa → vvob → vobu_map）を辿り、番組ごとの連続バイト範囲をそのまま
コピーします（再エンコードなし、ffmpeg 不要、VOBU 単位で正確）。

追加点：中国語 / 日本語 / 英語の UI 切り替え、IFO の録画日時による
ファイル名（`2026-11-11_17-36-20.mpg`）、ワーカースレッド + 進捗 + キャンセル、
分かりやすいエラー表示、任意の `--remux`。
