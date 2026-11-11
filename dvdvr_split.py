#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DVD-VR Splitter 2  —  按 IFO 节目表无损导出 DVD-VR (.VRO) 录像
================================================================

为什么重写 / Why rewrite
------------------------
原版 (spinningbanana/dvd-rtr-vmg0-splitter) 把 IFO 里的指针理解错了：
  * 0x100 处的 pgit_sa 是“节目表”，却被当成“片段表”；
  * 0x130 处的 def_psi_sa 是“标题文字”，却被当成“标题表”；
  * 再用 0x6540/0x32A0 两字节标记扫描猜记录，于是在日立(Hitachi)等机器
    写的盘上会造出几十条“时长 0 或 1 个 PTS tick”的假片段，
    ffmpeg 收到 -t 0 就写出 0 字节文件。

真实结构（RTR_VMG，与 pixelb/dvd-vr 的 C 实现一致）：
  0x000 "DVD_RTR_VMG0" | 0x00C RTR_VMG_EA
  0x100 pgit_sa   → PGI（节目表）
  0x130 def_psi_sa→ 标题文字
  pgit_sa + 0x00  pgiti{ zero(2), nr_of_pgi(1), nr_of_vob_formats(1), pgit_ea(4) }
  pgit_sa + 0x08  vob_format_t × nr_of_vob_formats（每个 60 字节）
                  然后 pgi_gi{ nr_of_programs(2) }
                  然后 vvobi_sa[program]（4 字节，相对 pgit_sa）
  每个节目 vvob_t(21): attr(2) 录制时间(5) data1(1) format_id(1) s_ptm(4+2) e_ptm(4+2)
                  然后 vobu_map{ n_time(2), n_vobu(2), time_off(2), vob_off(4) }
                  time_info × n_time（7 字节）
                  vobu_info × n_vobu（3 字节，后 14 位为扇区数）

  节目 N 在 VRO 中是一段连续字节：起点 = vob_off×2048，长度 = Σvobu_size×2048。
  直接拷贝即可 —— 不重编码、不需要 ffmpeg、切点精确到 VOBU。

语言 / Language / 言語
----------------------
  中文 / 日本語 / English，界面右上角可切换，选择会记住。
  命令行： --lang zh|ja|en   （也可用环境变量 DVDVR_LANG）

用法
----
  GUI:   python dvdvr_split.py
  CLI:   python dvdvr_split.py --ifo ... --vro ... --list
         python dvdvr_split.py --ifo ... --vro ... -o D:\\out [--programs 1,2] [--remux]
         python dvdvr_split.py --lang ja

许可：GPL-3.0（沿用原项目）
测试/Tested with: Hitachi DZ-GX20 (DVD-RAM, VR mode) disc image
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

SECTOR = 2048
APP_NAME = "DVD-VR Splitter"
APP_VERSION = "2.1.3"

# Windows 控制台默认 GBK；被重定向（管道/文件）时改用 UTF-8，避免乱码
if sys.platform == "win32":
    try:
        import locale
        try:
            _is_tty = sys.stdout.isatty()
        except Exception:
            _is_tty = False
        _enc = (locale.getpreferredencoding(False) or "gbk") if _is_tty else "utf-8"
        for _s in (sys.stdout, sys.stderr):
            try:
                _s.reconfigure(encoding=_enc, errors="replace")
            except Exception:
                pass
    except Exception:
        pass


# =========================================================================== i18n
LANGS = ("zh", "ja", "en")
LANG_LABELS = {"zh": "中文", "ja": "日本語", "en": "English"}

_current_lang = "zh"


def set_lang(code: Optional[str]) -> str:
    """接受 zh / zh-CN / ja / ja-JP / en / en-US 等写法"""
    global _current_lang
    code = (code or "").strip().lower()
    if code.startswith("zh"):
        _current_lang = "zh"
    elif code.startswith("ja"):
        _current_lang = "ja"
    elif code.startswith("en"):
        _current_lang = "en"
    else:
        # 未指定：按系统语言猜
        _current_lang = _guess_lang_from_system()
    return _current_lang


def _guess_lang_from_system() -> str:
    """Windows: 用 GetUserDefaultUILanguage；其它平台看 LANG"""
    if sys.platform == "win32":
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            primary = langid & 0x3FF
            if primary == 0x11:      # Japanese
                return "ja"
            if primary == 0x04:      # Chinese (zh-CN / zh-TW / zh-HK)
                return "zh"
            return "en"
        except Exception:
            pass
    env = (os.environ.get("LC_ALL") or os.environ.get("LANG") or "").lower()
    if env.startswith("ja"):
        return "ja"
    if env.startswith("zh") or env.startswith("cn"):
        return "zh"
    return "en"


def get_lang() -> str:
    return _current_lang


def t(key: str, **kw) -> str:
    table = STR.get(_current_lang) or STR["en"]
    s = table.get(key)
    if s is None:
        s = STR["en"].get(key, key)
    if kw:
        try:
            s = s.format(**kw)
        except Exception:
            pass
    return s


STR = {
    "zh": {
        "app.name": "DVD-VR 分割器",
        "lang.label": "语言",
        "group.choose": "1. 选择 DVD_RTAV 目录（或分别选择 IFO / VRO）",
        "btn.choose_dir": "选择目录…",
        "placeholder.folder": r"例如 G:\DVD_RTAV",
        "label.ifo": "IFO:",
        "label.vro": "VRO:",
        "btn.ifo": "IFO…",
        "btn.vro": "VRO…",
        "info.none": "尚未读取光盘",
        "btn.load": "读取光盘信息",
        "group.programs": "2. 节目列表（勾选要导出的）",
        "col.export": "导出",
        "col.index": "节目",
        "col.time": "录制时间",
        "col.duration": "时长",
        "col.size": "大小",
        "col.offset": "VRO 偏移",
        "btn.all": "全选",
        "btn.none": "全不选",
        "chk.remux": "用 ffmpeg 重封装成规整 MPG（慢，但兼容性更好）",
        "group.export": "3. 导出",
        "btn.browse": "浏览…",
        "placeholder.out": "输出目录",
        "btn.start": "开始导出",
        "btn.cancel": "取消",
        "info.summary": "IFO: {ifo}\nVRO: {vro}\n节目数 {n}，总时长 {dur}，总大小 {size}{cprm}",
        "info.cprm": "   ⚠ 该盘标记为 CPRM 加密",
        "log.loaded": "已读取：{n} 个节目",
        "log.program": "#{i}  {time}  ({dur}, {size})",
        "log.remuxing": "    重封装…",
        "log.done_one": "    完成，用时 {sec:.1f} 秒 -> {name}",
        "log.mismatch": "    ! 字节数不符：{got} / {want}",
        "log.cancelling": "正在取消…",
        "log.cancelled": "已取消",
        "log.all_done": "全部完成",
        "log.auto_named": "（IFO 没有录制时间，改用节目编号命名）",
        "msg.no_files": "没找到 VR_MANGR.IFO / VR_MOVIE.VRO。\n请选择 DVD_RTAV 目录，或手动指定两个文件。",
        "msg.need_disc": "先读取光盘信息",
        "msg.need_out": "请选择输出目录",
        "msg.no_selection": "没有勾选任何节目",
        "msg.done_body": "导出完成。\n{dir}",
        "msg.error": "错误",
        "dlg.choose_dir": "选择 DVD_RTAV 目录",
        "dlg.choose_ifo": "选择 IFO",
        "dlg.choose_vro": "选择 VRO",
        "dlg.choose_out": "选择输出目录",
        "filter.ifo": "IFO (*.IFO *.ifo)",
        "filter.vro": "VRO (*.VRO *.vro)",
        "name.fallback": "program_{n:02d}",
        "err.open_ifo": "打不开 IFO：{e}",
        "err.too_small": "IFO 太小（{n} 字节），不是 DVD-VR 的 IFO",
        "err.not_vr": "这不是 DVD-VR 的 IFO（前 12 字节是 {magic}，应为 DVD_RTR_VMG0）。\nDVD-Video 的 VIDEO_TS\\VTS_01_0.IFO 不支持。",
        "err.pgit_oob": "IFO 里的 pgit_sa（{v}）越界，文件可能损坏",
        "err.no_programs": "IFO 里节目数为 0（空盘，或 IFO 与 VRO 不匹配）",
        "err.too_many": "节目数异常（{n}），IFO 结构不对",
        "err.entry_oob": "第 {i} 个节目信息越界，IFO 可能损坏",
        "err.vobu_table": "第 {i} 个节目的 VOBU 表越界，IFO 可能损坏",
        "err.vobu_count": "第 {i} 个节目的 VOBU 数异常（{n}）",
        "err.open_vro": "打不开 VRO：{e}",
        "err.vro_small": "VRO 太小（{n} 字节）",
        "err.vro_short": "VRO 比 IFO 描述的短：{which}\n需要 {need} 字节，实际 {have} 字节。\n（是否把别的盘的 IFO 和 VRO 配对了？）",
        "err.dir": "打不开目录：{e}",
        "msg.same_drive": "检测到输出目录和输入文件在同一个盘（{drive}）。\n光驱 / 光盘通常是只读的，写入会失败。\n\n确定仍要继续吗？（建议改选本地硬盘上的目录，例如“视频”文件夹）",
        "msg.same_drive_pick": "这个目录在 {drive} 上，和输入文件是同一个盘（通常是光驱，不可写）。\n请换成本地硬盘上的目录。",
        "err.read_failed": "读取 VRO 失败：偏移 {off} 字节（已写入 {got}/{want} 字节）\n{e}\n\n常见原因：\n  • 摄像机/录像机断电或电池耗尽（USB 连接会立刻中断）\n  • USB 数据线松动、接触不良或被拔出\n  • 光盘有划痕/脏污，或虚拟光驱掉线、镜像文件不完整\n\n建议：给设备接上电源适配器、重新插好数据线后重试；或先把 VR_MOVIE.VRO 复制到本地硬盘再处理；确实读不出的坏块可勾选「读取错误时跳过」。",
        "log.skip_block": "    ! 读取失败，已跳过 {n} 字节（偏移 {off}）",
        "chk.skip_errors": "读取错误时跳过（光盘有划痕时用）",
        "err.out_create": "无法创建输出目录：\n{path}\n{e}\n\n请换成本地硬盘上的目录（光盘 / 虚拟光驱 / 只读镜像是不能写入的），例如 D:\\Videos\\DVD_OUT。",
        "err.out_readonly": "输出目录不可写：\n{path}\n\n请换成本地硬盘上的目录（光盘 / 虚拟光驱 / 只读镜像是不能写入的），例如 D:\\Videos\\DVD_OUT。",
        "err.bad_arg": "节目编号不合法: {v}",
        "err.no_such": "IFO 里没有这些节目: {v}",
        "err.ffmpeg_needed": "找不到 ffmpeg（可用 --ffmpeg 指定）",
        "err.remux_failed": "ffmpeg 重封装失败：\n{e}",
        "err.unexpected": "未预期的错误：\n{e}",
        "err.cli_needs": "命令行模式需要同时给出 --ifo 和 --vro",
        "cli.summary": "  节目数: {n}   VOB 格式数: {fmt}   总时长: {dur}   总大小: {size}{cprm}",
        "cli.h_index": "节目",
        "cli.h_time": "录制时间",
        "cli.h_dur": "时长",
        "cli.h_size": "大小",
        "cli.h_off": "VRO 偏移",
        "cli.export_start": "导出 {n} 个节目 -> {dir}",
        "cli.line": "  #{i}  {name}  {size}  {ok}  {sec:.1f}s",
        "cli.ok": "OK",
        "cli.mismatch": "字节数不符（{got}/{want}）",
        "cli.err": "错误: {msg}",
    },
    "ja": {
        "app.name": "DVD-VR スプリッター",
        "lang.label": "言語",
        "group.choose": "1. DVD_RTAV フォルダーを選択（または IFO / VRO を個別に選択）",
        "btn.choose_dir": "フォルダーを選択…",
        "placeholder.folder": r"例: G:\DVD_RTAV",
        "label.ifo": "IFO:",
        "label.vro": "VRO:",
        "btn.ifo": "IFO…",
        "btn.vro": "VRO…",
        "info.none": "ディスク未読み取り",
        "btn.load": "ディスク情報を読み取る",
        "group.programs": "2. 番組一覧（書き出すものを選択）",
        "col.export": "書き出し",
        "col.index": "番組",
        "col.time": "録画日時",
        "col.duration": "長さ",
        "col.size": "サイズ",
        "col.offset": "VRO オフセット",
        "btn.all": "すべて選択",
        "btn.none": "選択解除",
        "chk.remux": "ffmpeg で再マックスして整った MPG にする（遅いが互換性が高い）",
        "group.export": "3. 書き出し",
        "btn.browse": "参照…",
        "placeholder.out": "出力先フォルダー",
        "btn.start": "書き出し開始",
        "btn.cancel": "キャンセル",
        "info.summary": "IFO: {ifo}\nVRO: {vro}\n番組数 {n}、合計時間 {dur}、合計サイズ {size}{cprm}",
        "info.cprm": "   ⚠ このディスクは CPRM 暗号化です",
        "log.loaded": "読み取り完了: {n} 番組",
        "log.program": "#{i}  {time}  ({dur}, {size})",
        "log.remuxing": "    再マックス中…",
        "log.done_one": "    完了（{sec:.1f} 秒）-> {name}",
        "log.mismatch": "    ! バイト数不一致: {got} / {want}",
        "log.cancelling": "キャンセル中…",
        "log.cancelled": "キャンセルしました",
        "log.all_done": "すべて完了",
        "log.auto_named": "（IFO に録画日時がないため、番組番号で命名します）",
        "msg.no_files": "VR_MANGR.IFO / VR_MOVIE.VRO が見つかりません。\nDVD_RTAV フォルダーを選択するか、2 つのファイルを指定してください。",
        "msg.need_disc": "先にディスク情報を読み取ってください",
        "msg.need_out": "出力先を選択してください",
        "msg.no_selection": "番組が選択されていません",
        "msg.done_body": "書き出し完了。\n{dir}",
        "msg.error": "エラー",
        "dlg.choose_dir": "DVD_RTAV フォルダーを選択",
        "dlg.choose_ifo": "IFO を選択",
        "dlg.choose_vro": "VRO を選択",
        "dlg.choose_out": "出力先を選択",
        "filter.ifo": "IFO (*.IFO *.ifo)",
        "filter.vro": "VRO (*.VRO *.vro)",
        "name.fallback": "program_{n:02d}",
        "err.open_ifo": "IFO を開けません: {e}",
        "err.too_small": "IFO が小さすぎます（{n} バイト）。DVD-VR の IFO ではありません",
        "err.not_vr": "DVD-VR の IFO ではありません（先頭 12 バイトは {magic}、DVD_RTR_VMG0 である必要があります）。\nDVD-Video の VIDEO_TS\\VTS_01_0.IFO には対応していません。",
        "err.pgit_oob": "IFO の pgit_sa（{v}）が範囲外です。ファイルが壊れている可能性があります",
        "err.no_programs": "IFO の番組数が 0 です（空のディスク、または IFO と VRO の組み合わせが違います）",
        "err.too_many": "番組数が異常です（{n}）。IFO の構造が正しくありません",
        "err.entry_oob": "{i} 番目の番組情報が範囲外です。IFO が壊れている可能性があります",
        "err.vobu_table": "{i} 番目の番組の VOBU テーブルが範囲外です。IFO が壊れている可能性があります",
        "err.vobu_count": "{i} 番目の番組の VOBU 数が異常です（{n}）",
        "err.open_vro": "VRO を開けません: {e}",
        "err.vro_small": "VRO が小さすぎます（{n} バイト）",
        "err.vro_short": "VRO が IFO の記述より短いです: {which}\n必要 {need} バイト、実際 {have} バイト。\n（別のディスクの IFO と VRO を組み合わせていませんか？）",
        "err.dir": "フォルダーを開けません: {e}",
        "msg.same_drive": "出力先と入力ファイルが同じドライブ（{drive}）です。\n光学ドライブ / ディスクは通常読み取り専用のため、書き込みに失敗します。\n\nこのまま続行しますか？（ローカルディスク上のフォルダーを推奨）",
        "msg.same_drive_pick": "このフォルダーは {drive} 上にあり、入力ファイルと同じドライブです（通常は光学ドライブで書き込み不可）。\nローカルディスク上のフォルダーを選んでください。",
        "err.read_failed": "VRO の読み込みに失敗しました: オフセット {off} バイト（{got}/{want} バイト書き込み済み）\n{e}\n\nよくある原因:\n  • カメラ／レコーダーの電源が切れた、バッテリー切れ（USB 接続が瞬断します）\n  • USB ケーブルの接触不良・抜け\n  • ディスクの傷・汚れ、仮想ドライブの切断、イメージの破損\n\n対処: AC アダプターで給電し、ケーブルを接続し直してから再試行してください。VR_MOVIE.VRO をローカルディスクにコピーしてから処理するのも有効です。読めないブロックは「読み取りエラーをスキップ」で続行できます。",
        "log.skip_block": "    ! 読み取り失敗、{n} バイトをスキップ（オフセット {off}）",
        "chk.skip_errors": "読み取りエラーをスキップ（傷んだディスク向け）",
        "err.out_create": "出力先フォルダーを作成できません:\n{path}\n{e}\n\nローカルディスク上のフォルダーを指定してください（光学ディスク / 仮想ドライブ / 読み取り専用イメージには書き込めません）。例: D:\\Videos\\DVD_OUT",
        "err.out_readonly": "出力先フォルダーに書き込めません:\n{path}\n\nローカルディスク上のフォルダーを指定してください（光学ディスク / 仮想ドライブ / 読み取り専用イメージには書き込めません）。",
        "err.bad_arg": "番組番号が不正です: {v}",
        "err.no_such": "IFO に存在しない番組です: {v}",
        "err.ffmpeg_needed": "ffmpeg が見つかりません（--ffmpeg で指定できます）",
        "err.remux_failed": "ffmpeg の再マックスに失敗しました:\n{e}",
        "err.unexpected": "予期しないエラー:\n{e}",
        "err.cli_needs": "コマンドラインでは --ifo と --vro の両方が必要です",
        "cli.summary": "  番組数: {n}   VOB フォーマット数: {fmt}   合計時間: {dur}   合計サイズ: {size}{cprm}",
        "cli.h_index": "番組",
        "cli.h_time": "録画日時",
        "cli.h_dur": "長さ",
        "cli.h_size": "サイズ",
        "cli.h_off": "VRO オフセット",
        "cli.export_start": "{n} 番組を書き出します -> {dir}",
        "cli.line": "  #{i}  {name}  {size}  {ok}  {sec:.1f}s",
        "cli.ok": "OK",
        "cli.mismatch": "バイト数不一致（{got}/{want}）",
        "cli.err": "エラー: {msg}",
    },
    "en": {
        "app.name": "DVD-VR Splitter",
        "lang.label": "Language",
        "group.choose": "1. Choose the DVD_RTAV folder (or pick IFO / VRO separately)",
        "btn.choose_dir": "Choose folder…",
        "placeholder.folder": r"e.g. G:\DVD_RTAV",
        "label.ifo": "IFO:",
        "label.vro": "VRO:",
        "btn.ifo": "IFO…",
        "btn.vro": "VRO…",
        "info.none": "No disc loaded yet",
        "btn.load": "Read disc info",
        "group.programs": "2. Programs (check the ones to export)",
        "col.export": "Export",
        "col.index": "Program",
        "col.time": "Recorded",
        "col.duration": "Duration",
        "col.size": "Size",
        "col.offset": "VRO offset",
        "btn.all": "Select all",
        "btn.none": "Select none",
        "chk.remux": "Remux to clean MPG with ffmpeg (slower, better compatibility)",
        "group.export": "3. Export",
        "btn.browse": "Browse…",
        "placeholder.out": "Output folder",
        "btn.start": "Start export",
        "btn.cancel": "Cancel",
        "info.summary": "IFO: {ifo}\nVRO: {vro}\n{n} program(s), total {dur}, {size}{cprm}",
        "info.cprm": "   ⚠ disc is marked as CPRM-encrypted",
        "log.loaded": "Loaded {n} program(s)",
        "log.program": "#{i}  {time}  ({dur}, {size})",
        "log.remuxing": "    remuxing…",
        "log.done_one": "    done in {sec:.1f}s -> {name}",
        "log.mismatch": "    ! size mismatch: {got} / {want}",
        "log.cancelling": "Cancelling…",
        "log.cancelled": "Cancelled",
        "log.all_done": "All done",
        "log.auto_named": "(no recording time in IFO — using program number instead)",
        "msg.no_files": "VR_MANGR.IFO / VR_MOVIE.VRO not found.\nPick the DVD_RTAV folder, or choose the two files manually.",
        "msg.need_disc": "Read the disc info first",
        "msg.need_out": "Choose an output folder",
        "msg.no_selection": "No program selected",
        "msg.done_body": "Export finished.\n{dir}",
        "msg.error": "Error",
        "dlg.choose_dir": "Choose DVD_RTAV folder",
        "dlg.choose_ifo": "Choose IFO",
        "dlg.choose_vro": "Choose VRO",
        "dlg.choose_out": "Choose output folder",
        "filter.ifo": "IFO (*.IFO *.ifo)",
        "filter.vro": "VRO (*.VRO *.vro)",
        "name.fallback": "program_{n:02d}",
        "err.open_ifo": "Cannot open IFO: {e}",
        "err.too_small": "IFO too small ({n} bytes) — not a DVD-VR IFO",
        "err.not_vr": "Not a DVD-VR IFO (first 12 bytes are {magic}, expected DVD_RTR_VMG0).\nDVD-Video VIDEO_TS\\VTS_01_0.IFO is not supported.",
        "err.pgit_oob": "pgit_sa ({v}) in IFO is out of range — file may be damaged",
        "err.no_programs": "IFO reports 0 programs (empty disc, or IFO/VRO mismatch)",
        "err.too_many": "Unreasonable program count ({n}) — IFO layout is not what we expect",
        "err.entry_oob": "Program #{i} info is out of range — IFO may be damaged",
        "err.vobu_table": "Program #{i} VOBU table is out of range — IFO may be damaged",
        "err.vobu_count": "Program #{i} has an odd VOBU count ({n})",
        "err.open_vro": "Cannot open VRO: {e}",
        "err.vro_small": "VRO too small ({n} bytes)",
        "err.vro_short": "VRO is shorter than the IFO describes: {which}\nneeds {need} bytes, file has {have}.\n(Are you mixing IFO and VRO from different discs?)",
        "err.dir": "Cannot open folder: {e}",
        "msg.same_drive": "The output folder is on the same drive as the input file ({drive}).\nOptical drives/discs are usually read-only, so writing will fail.\n\nContinue anyway? (A folder on a local disk is recommended.)",
        "msg.same_drive_pick": "That folder is on {drive}, the same drive as the input file (usually an optical drive, not writable).\nPlease choose a folder on a local disk.",
        "err.read_failed": "Failed to read VRO at offset {off} bytes (wrote {got}/{want})\n{e}\n\nTypical causes:\n  • the camcorder/recorder lost power or its battery ran out (the USB link drops instantly)\n  • loose, unplugged or faulty USB cable\n  • scratched/dirty disc, virtual drive disconnected, incomplete image file\n\nSuggestion: power the device from AC, reconnect the cable and retry; or copy VR_MOVIE.VRO to a local disk first. Blocks that still fail can be skipped with \"skip read errors\".",
        "log.skip_block": "    ! read error, skipped {n} bytes (offset {off})",
        "chk.skip_errors": "Skip read errors (for scratched discs)",
        "err.out_create": "Cannot create output folder:\n{path}\n{e}\n\nChoose a folder on a local disk — optical discs, virtual drives and read-only images cannot be written to. e.g. D:\\Videos\\DVD_OUT",
        "err.out_readonly": "Output folder is not writable:\n{path}\n\nChoose a folder on a local disk — optical discs, virtual drives and read-only images cannot be written to.",
        "err.bad_arg": "Invalid program number: {v}",
        "err.no_such": "No such program in IFO: {v}",
        "err.ffmpeg_needed": "ffmpeg not found (use --ffmpeg to point at it)",
        "err.remux_failed": "ffmpeg remux failed:\n{e}",
        "err.unexpected": "Unexpected error:\n{e}",
        "err.cli_needs": "CLI mode needs both --ifo and --vro",
        "cli.summary": "  programs: {n}   VOB formats: {fmt}   total: {dur}   size: {size}{cprm}",
        "cli.h_index": "Program",
        "cli.h_time": "Recorded",
        "cli.h_dur": "Duration",
        "cli.h_size": "Size",
        "cli.h_off": "VRO offset",
        "cli.export_start": "Exporting {n} program(s) -> {dir}",
        "cli.line": "  #{i}  {name}  {size}  {ok}  {sec:.1f}s",
        "cli.ok": "OK",
        "cli.mismatch": "size mismatch ({got}/{want})",
        "cli.err": "error: {msg}",
    },
}


# --------------------------------------------------------------------------- 配置
def config_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "DVDVRSplitter", "config.json")


def load_config() -> dict:
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(**kw) -> None:
    cfg = load_config()
    cfg.update(kw)
    try:
        os.makedirs(os.path.dirname(config_path()), exist_ok=True)
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# --------------------------------------------------------------------------- 异常
class DVDVRError(Exception):
    """可预期的解析/导出错误（直接显示给用户）"""


class Cancelled(Exception):
    """用户取消"""


# --------------------------------------------------------------------------- 小工具
def _u8(d: bytes, o: int) -> int:
    if o < 0 or o + 1 > len(d):
        raise DVDVRError(t("err.pgit_oob", v=hex(o)))
    return d[o]


def _u16(d: bytes, o: int) -> int:
    if o < 0 or o + 2 > len(d):
        raise DVDVRError(t("err.pgit_oob", v=hex(o)))
    return struct.unpack_from(">H", d, o)[0]


def _u32(d: bytes, o: int) -> int:
    if o < 0 or o + 4 > len(d):
        raise DVDVRError(t("err.pgit_oob", v=hex(o)))
    return struct.unpack_from(">I", d, o)[0]


def parse_pgtm(d: bytes, o: int):
    """5 字节打包的录制时间 -> (y, m, d, H, M, S)；无效返回 None"""
    p = d[o:o + 5]
    if len(p) < 5:
        return None
    year = ((p[0] << 8) | p[1]) >> 2
    month = ((p[1] & 0x03) << 2) | (p[2] >> 6)
    day = (p[2] & 0x3E) >> 1
    hour = ((p[2] & 0x01) << 4) | (p[3] >> 4)
    minute = ((p[3] & 0x0F) << 2) | (p[4] >> 6)
    sec = p[4] & 0x3F
    if not year or not (1 <= month <= 12) or not (1 <= day <= 31):
        return None
    return (year, month, day, hour, minute, sec)


def fmt_ptm(sec) -> str:
    ms = int(round(float(sec) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d.%03d" % (h, m, s, ms)


def fmt_bytes(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if f < 1024 or unit == "GB":
            return ("%d B" % n) if unit == "B" else ("%.1f %s" % (f, unit))
        f /= 1024.0
    return "%.1f GB" % f


def safe_name(s: str) -> str:
    for ch in '\\/:*?"<>|\r\n\t':
        s = s.replace(ch, "_")
    return s.strip() or "untitled"


# --------------------------------------------------------------------------- 数据结构
@dataclass
class Program:
    index: int
    rec_time: Optional[tuple]
    start_ptm: int
    end_ptm: int
    format_id: int
    vob_offset_sectors: int
    vobu_sizes: List[int]

    @property
    def duration(self) -> float:
        return max(0.0, (self.end_ptm - self.start_ptm) / 90000.0)

    @property
    def byte_size(self) -> int:
        return sum(self.vobu_sizes) * SECTOR

    @property
    def start_byte(self) -> int:
        return self.vob_offset_sectors * SECTOR

    def time_label(self) -> str:
        if self.rec_time:
            return "%04d-%02d-%02d %02d:%02d:%02d" % self.rec_time
        return "-"

    def file_base(self) -> str:
        """按 IFO 里的录制日期时间命名；没有时间戳时退回 program_NN"""
        if self.rec_time:
            return "%04d-%02d-%02d_%02d-%02d-%02d" % self.rec_time
        return t("name.fallback", n=self.index)


@dataclass
class DiscInfo:
    ifo_path: str
    vro_path: str
    vmg_ea: int
    pgit_sa: int
    def_psi_sa: int
    nr_pgi: int
    nr_formats: int
    cprm: bool
    programs: List[Program] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(p.byte_size for p in self.programs)

    @property
    def total_duration(self) -> float:
        return sum(p.duration for p in self.programs)


# --------------------------------------------------------------------------- 解析
def parse_ifo(path: str) -> DiscInfo:
    try:
        with open(path, "rb") as f:
            d = f.read()
    except OSError as e:
        raise DVDVRError(t("err.open_ifo", e=e))

    if len(d) < 512:
        raise DVDVRError(t("err.too_small", n=len(d)))
    if d[:12] != b"DVD_RTR_VMG0":
        raise DVDVRError(t("err.not_vr", magic=bytes(d[:12])))

    vmg_ea = _u32(d, 0x0C)
    pgit_sa = _u32(d, 0x100)
    def_psi_sa = _u32(d, 0x130)
    if not pgit_sa or pgit_sa >= len(d):
        raise DVDVRError(t("err.pgit_oob", v=hex(pgit_sa)))

    nr_pgi = _u8(d, pgit_sa + 2)
    nr_formats = _u8(d, pgit_sa + 3)

    pos = pgit_sa + 8 + nr_formats * 60
    nr_programs = _u16(d, pos)
    pos += 2
    if nr_programs == 0:
        raise DVDVRError(t("err.no_programs"))
    if nr_programs > 999:
        raise DVDVRError(t("err.too_many", n=nr_programs))

    vvobi_sa = [_u32(d, pos + 4 * i) for i in range(nr_programs)]
    cprm = bool(d[0x10B]) if len(d) > 0x10B else False

    programs: List[Program] = []
    for i, rel in enumerate(vvobi_sa):
        v = pgit_sa + rel
        if v + 21 > len(d):
            raise DVDVRError(t("err.entry_oob", i=i + 1))
        vob_attr = _u16(d, v)
        rec = parse_pgtm(d, v + 2)
        fmt_id = _u8(d, v + 8)
        start_ptm = _u32(d, v + 9)
        end_ptm = _u32(d, v + 15)

        vm = v + 21 + ((12 if (vob_attr & 0x80) else 0) + 2)
        n_time = _u16(d, vm)
        n_vobu = _u16(d, vm + 2)
        vob_off = _u32(d, vm + 6)
        if n_vobu <= 0 or n_vobu > 200000:
            raise DVDVRError(t("err.vobu_count", i=i + 1, n=n_vobu))

        vi = vm + 10 + n_time * 7
        if vi + 3 * n_vobu > len(d):
            raise DVDVRError(t("err.vobu_table", i=i + 1))
        sizes = [_u16(d, vi + 3 * k + 1) & 0x03FF for k in range(n_vobu)]

        programs.append(Program(index=i + 1, rec_time=rec, start_ptm=start_ptm,
                                end_ptm=end_ptm, format_id=fmt_id,
                                vob_offset_sectors=vob_off, vobu_sizes=sizes))

    return DiscInfo(ifo_path=path, vro_path="", vmg_ea=vmg_ea, pgit_sa=pgit_sa,
                    def_psi_sa=def_psi_sa, nr_pgi=nr_pgi, nr_formats=nr_formats,
                    cprm=cprm, programs=programs)


def find_disc_files(folder: str):
    try:
        names = os.listdir(folder)
    except OSError as e:
        raise DVDVRError(t("err.dir", e=e))
    lower = {n.lower(): n for n in names}
    ifo = next((os.path.join(folder, lower[k]) for k in ("vr_mangr.ifo",) if k in lower), None)
    vro = next((os.path.join(folder, lower[k]) for k in ("vr_movie.vro",) if k in lower), None)
    return ifo, vro


def open_disc(ifo_path: str, vro_path: str) -> DiscInfo:
    info = parse_ifo(ifo_path)
    info.vro_path = vro_path
    try:
        vsize = os.path.getsize(vro_path)
    except OSError as e:
        raise DVDVRError(t("err.open_vro", e=e))
    if vsize < 2048:
        raise DVDVRError(t("err.vro_small", n=vsize))
    over = [p for p in info.programs if p.start_byte + p.byte_size > vsize]
    if over:
        raise DVDVRError(t("err.vro_short",
                           which=", ".join("#%d" % p.index for p in over),
                           need=max(p.start_byte + p.byte_size for p in over),
                           have=vsize))
    return info


# --------------------------------------------------------------------------- 导出
READ_CHUNK = 64 * 1024      # 每次读 64 KB（对齐到扇区），比一次读 2 MB 更耐受坏盘
READ_RETRIES = 3


def _read_block(src, offset: int, size: int) -> Optional[bytes]:
    """从 offset 读 size 字节，失败重试；仍失败返回 None"""
    last = None
    for attempt in range(READ_RETRIES):
        try:
            src.seek(offset)
            data = src.read(size)
            if data is None:
                raise OSError("read returned None")
            return data
        except OSError as e:
            last = e
            time.sleep(0.15 * (attempt + 1))
    _read_block.last_error = last
    return None


_read_block.last_error = None


def extract_program(vro_path: str, prog: Program, out_path: str,
                    progress: Optional[Callable[[int, int], None]] = None,
                    cancel: Optional[Callable[[], bool]] = None,
                    skip_errors: bool = False,
                    on_skip: Optional[Callable[[int, int], None]] = None) -> int:
    """按字节拷贝一个节目。读盘出错时重试；skip_errors=True 则跳过坏块继续。"""
    total = prog.byte_size
    done = 0
    skipped = 0
    tmp = out_path + ".part"
    try:
        # buffering=0：直接走 ReadFile，避免 Python 缓冲区在坏盘上缓存到错误状态
        with open(vro_path, "rb", buffering=0) as src, open(tmp, "wb") as dst:
            offset = prog.start_byte
            for size in prog.vobu_sizes:
                if cancel and cancel():
                    raise Cancelled()
                remaining = size * SECTOR
                while remaining > 0:
                    want = min(READ_CHUNK, remaining)
                    data = _read_block(src, offset, want)
                    if data is None:
                        if skip_errors:
                            if on_skip:
                                on_skip(offset, want)
                            offset += want
                            skipped += want
                            remaining -= want
                            continue
                        raise DVDVRError(t(
                            "err.read_failed",
                            off=offset, got=done, want=total,
                            e=_read_block.last_error))
                    if not data:
                        # 提前到文件末尾
                        break
                    dst.write(data)
                    done += len(data)
                    offset += len(data)
                    remaining -= len(data)
                    if progress:
                        progress(done, total)
        os.replace(tmp, out_path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return done


def unique_name(folder: str, base: str) -> str:
    """同名时追加 _2、_3…（IFO 里两个节目可能同一分钟录制）"""
    name = base + ".mpg"
    if not os.path.exists(os.path.join(folder, name)):
        return name
    i = 2
    while True:
        name = "%s_%d.mpg" % (base, i)
        if not os.path.exists(os.path.join(folder, name)):
            return name
        i += 1


def remux_with_ffmpeg(raw_path: str, final_path: str, ffmpeg: str) -> None:
    import subprocess
    cmd = [ffmpeg, "-hide_banner", "-v", "error", "-y", "-i", raw_path,
           "-map", "0", "-c", "copy", "-f", "mpeg", final_path]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise DVDVRError(t("err.remux_failed", e=p.stderr.decode("utf-8", "replace")[:2000]))


def which_ffmpeg() -> Optional[str]:
    import shutil
    p = shutil.which("ffmpeg")
    if p:
        return p
    for cand in (r"E:\DVD\ffmpeg\bin\ffmpeg.exe", os.path.join(".", "ffmpeg", "bin", "ffmpeg.exe")):
        if os.path.isfile(cand):
            return cand
    return None


def videos_dir() -> str:
    """Windows 的“视频”文件夹（尊重 OneDrive 重定向）；其它平台退回 ~/Videos"""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            # FOLDERID_Videos {18989B1D-99B5-455B-841C-AB7C74E4DDFC}
            guid = GUID(0x18989B1D, 0x99B5, 0x455B,
                        (ctypes.c_ubyte * 8)(0x84, 0x1C, 0xAB, 0x7C, 0x74, 0xE4, 0xDD, 0xFC))
            buf = ctypes.c_wchar_p()
            hr = ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(guid), 0, None, ctypes.byref(buf))
            if hr == 0 and buf.value:
                path = buf.value
                ctypes.windll.ole32.CoTaskMemFree(buf)
                return path
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Videos")


def same_drive(a: str, b: str) -> bool:
    """判断两个路径是否在同一个盘符（或同一个 UNC 共享）"""
    try:
        da = os.path.splitdrive(os.path.abspath(a))[0].lower()
        db = os.path.splitdrive(os.path.abspath(b))[0].lower()
        return bool(da) and da == db
    except Exception:
        return False


def dir_writable(path: str) -> bool:
    """真正的写测试。os.access() 在光盘 / 虚拟光驱 / 网络盘上会给出错误答案。"""
    probe = os.path.join(path, ".dvdvr_write_test.tmp")
    try:
        with open(probe, "wb") as f:
            f.write(b"x")
        os.remove(probe)
        return True
    except OSError:
        return False


def ensure_output_dir(path: str) -> None:
    """创建输出目录；失败时给出可读的原因（而不是裸 traceback）"""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise DVDVRError(t("err.out_create", path=path, e=e))
    if not dir_writable(path):
        raise DVDVRError(t("err.out_readonly", path=path))


# --------------------------------------------------------------------------- 命令行
def cmd_list(args) -> int:
    info = open_disc(args.ifo, args.vro)
    print("%s  (IFO %s)" % (APP_NAME, info.ifo_path))
    print(t("cli.summary", n=len(info.programs), fmt=info.nr_formats,
            dur=fmt_ptm(info.total_duration), size=fmt_bytes(info.total_bytes),
            cprm=("   " + t("info.cprm").strip()) if info.cprm else ""))
    print()
    print("  %-4s %-20s %-14s %12s %14s" % ("#", t("cli.h_time"), t("cli.h_dur"),
                                            t("cli.h_size"), t("cli.h_off")))
    for p in info.programs:
        print("  %-4d %-20s %-14s %12s %14d"
              % (p.index, p.time_label(), fmt_ptm(p.duration), fmt_bytes(p.byte_size),
                 p.start_byte))
    return 0


def cmd_extract(args) -> int:
    info = open_disc(args.ifo, args.vro)
    wanted = None
    if args.programs:
        wanted = set()
        for part in args.programs.replace(" ", "").split(","):
            if not part:
                continue
            try:
                wanted.add(int(part))
            except ValueError:
                raise DVDVRError(t("err.bad_arg", v=part))
        bad = wanted - {p.index for p in info.programs}
        if bad:
            raise DVDVRError(t("err.no_such", v=", ".join(map(str, sorted(bad)))))

    ensure_output_dir(args.out)
    todo = [p for p in info.programs if wanted is None or p.index in wanted]
    ffmpeg = which_ffmpeg() if args.remux else None
    if args.remux and not ffmpeg:
        raise DVDVRError(t("err.ffmpeg_needed"))

    print(t("cli.export_start", n=len(todo), dir=args.out))
    for p in todo:
        name = unique_name(args.out, safe_name(p.file_base()))
        final = os.path.join(args.out, name)
        raw = final + ".vob" if args.remux else final
        t0 = time.time()
        n = extract_program(args.vro, p, raw, skip_errors=args.skip_errors,
                            on_skip=lambda off, nb: print(t("log.skip_block", off=off, n=nb)))
        if args.remux:
            remux_with_ffmpeg(raw, final, ffmpeg)
            os.remove(raw)
        dt = time.time() - t0
        ok = t("cli.ok") if n == p.byte_size else t("cli.mismatch", got=n, want=p.byte_size)
        print(t("cli.line", i=p.index, name=name, size=fmt_bytes(n), ok=ok, sec=dt))
    return 0


def build_cli() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="dvdvr_split",
        description="DVD-VR (.VRO) splitter — export each program losslessly. "
                    "中文/日本語/English UI.")
    ap.add_argument("--ifo", help="path to VR_MANGR.IFO")
    ap.add_argument("--vro", help="path to VR_MOVIE.VRO")
    ap.add_argument("-o", "--out", help="output folder")
    ap.add_argument("--programs", help="program numbers to export, e.g. 1,3 (default: all)")
    ap.add_argument("--list", action="store_true", help="list programs only")
    ap.add_argument("--remux", action="store_true", help="remux to clean MPG with ffmpeg")
    ap.add_argument("--skip-errors", action="store_true",
                    help="skip unreadable blocks instead of aborting (scratched discs)")
    ap.add_argument("--ffmpeg", help="path to ffmpeg.exe")
    ap.add_argument("--lang", choices=LANGS, help="UI language: zh / ja / en")
    ap.add_argument("--gui", action="store_true", help="force GUI")
    return ap


def main(argv=None) -> int:
    ap = build_cli()
    args = ap.parse_args(argv)

    cfg = load_config()
    set_lang(args.lang or os.environ.get("DVDVR_LANG") or cfg.get("lang"))
    if args.lang:
        save_config(lang=get_lang())

    if not args.gui and (args.list or args.out):
        try:
            if not args.ifo or not args.vro:
                raise DVDVRError(t("err.cli_needs"))
            if args.ffmpeg:
                global which_ffmpeg
                which_ffmpeg = lambda: args.ffmpeg  # noqa: F811
            return cmd_list(args) if args.list else cmd_extract(args)
        except DVDVRError as e:
            print(t("cli.err", msg=e), file=sys.stderr)
            return 2
        except Cancelled:
            return 130
    return run_gui(args.ifo or "", args.vro or "")


# --------------------------------------------------------------------------- GUI
def run_gui(prefill_ifo: str = "", prefill_vro: str = "") -> int:
    try:
        from PySide6.QtCore import Qt, QThread, Signal
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import (
            QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
            QHeaderView, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
            QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)
    except ImportError:
        print("PySide6 is required for the GUI / 图形界面需要 PySide6:\n"
              "  pip install PySide6\n"
              "or use CLI:  dvdvr_split.py --ifo ... --vro ... -o ...", file=sys.stderr)
        return 2

    class Worker(QThread):
        progress = Signal(int, int)
        log = Signal(str)
        done = Signal(bool, str)

        def __init__(self, info: DiscInfo, outdir: str, progs: List[Program], remux: bool,
                     skip_errors: bool = False):
            super().__init__()
            self.info, self.outdir, self.progs, self.remux = info, outdir, progs, remux
            self.skip_errors = skip_errors
            self._cancel = False
            self.result = []

        def cancel(self):
            self._cancel = True

        def run(self):
            try:
                ensure_output_dir(self.outdir)
                total_all = sum(p.byte_size for p in self.progs) or 1
                base_done = 0
                ffmpeg = which_ffmpeg() if self.remux else None
                if self.remux and not ffmpeg:
                    raise DVDVRError(t("err.ffmpeg_needed"))
                for p in self.progs:
                    if self._cancel:
                        raise Cancelled()
                    name = unique_name(self.outdir, safe_name(p.file_base()))
                    final = os.path.join(self.outdir, name)
                    raw = final + ".vob" if self.remux else final
                    self.log.emit(t("log.program", i=p.index, time=p.time_label(),
                                    dur=fmt_ptm(p.duration), size=fmt_bytes(p.byte_size)))
                    t0 = time.time()

                    def cb(done, total, _base=base_done):
                        self.progress.emit(_base + done, total_all)

                    n = extract_program(self.info.vro_path, p, raw,
                                        progress=cb, cancel=lambda: self._cancel,
                                        skip_errors=self.skip_errors,
                                        on_skip=lambda off, nb: self.log.emit(
                                            t("log.skip_block", off=off, n=nb)))
                    if self.remux:
                        self.log.emit(t("log.remuxing"))
                        remux_with_ffmpeg(raw, final, ffmpeg)
                        os.remove(raw)
                    base_done += p.byte_size
                    self.progress.emit(base_done, total_all)
                    if n != p.byte_size:
                        self.log.emit(t("log.mismatch", got=n, want=p.byte_size))
                    self.log.emit(t("log.done_one", sec=time.time() - t0, name=name))
                    self.result.append(final)
                self.done.emit(True, t("log.all_done"))
            except Cancelled:
                self.done.emit(False, t("log.cancelled"))
            except DVDVRError as e:
                self.done.emit(False, str(e))
            except Exception:
                import traceback
                self.done.emit(False, t("err.unexpected", e=traceback.format_exc()))

    class Window(QWidget):
        def __init__(self, prefill_ifo: str = "", prefill_vro: str = ""):
            super().__init__()
            self.setMinimumSize(920, 660)
            self.info: Optional[DiscInfo] = None
            self.worker: Optional[Worker] = None
            self._build()
            here = os.path.dirname(os.path.abspath(__file__))
            ico = os.path.join(here, "icon.ico")
            if os.path.isfile(ico):
                self.setWindowIcon(QIcon(ico))
            self.retranslate()
            if prefill_ifo:
                self.ed_ifo.setText(prefill_ifo)
            if prefill_vro:
                self.ed_vro.setText(prefill_vro)
            if prefill_ifo and prefill_vro:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self.load_disc)

        # ---- 构建界面（不设文字，文字统一在 retranslate 里设）
        def _build(self):
            lay = QVBoxLayout(self)

            top = QHBoxLayout()
            self.lbl_title = QLabel()
            f = self.lbl_title.font()
            f.setBold(True)
            f.setPointSize(f.pointSize() + 2)
            self.lbl_title.setFont(f)
            self.lbl_lang = QLabel()
            self.cmb_lang = QComboBox()
            for code in LANGS:
                self.cmb_lang.addItem(LANG_LABELS[code], code)
            idx = self.cmb_lang.findData(get_lang())
            self.cmb_lang.setCurrentIndex(max(0, idx))
            self.cmb_lang.currentIndexChanged.connect(self.on_lang_changed)
            top.addWidget(self.lbl_title)
            top.addStretch(1)
            top.addWidget(self.lbl_lang)
            top.addWidget(self.cmb_lang)
            lay.addLayout(top)

            self.gb_choose = QGroupBox()
            g = QVBoxLayout(self.gb_choose)
            row = QHBoxLayout()
            self.ed_folder = QLineEdit()
            self.btn_dir = QPushButton()
            self.btn_dir.clicked.connect(self.pick_dir)
            row.addWidget(self.ed_folder, 1)
            row.addWidget(self.btn_dir)
            g.addLayout(row)

            row2 = QHBoxLayout()
            self.lbl_ifo = QLabel()
            self.ed_ifo = QLineEdit()
            self.btn_ifo = QPushButton()
            self.btn_ifo.clicked.connect(lambda: self.pick_file(self.ed_ifo, t("filter.ifo")))
            self.lbl_vro = QLabel()
            self.ed_vro = QLineEdit()
            self.btn_vro = QPushButton()
            self.btn_vro.clicked.connect(lambda: self.pick_file(self.ed_vro, t("filter.vro")))
            row2.addWidget(self.lbl_ifo)
            row2.addWidget(self.ed_ifo, 1)
            row2.addWidget(self.btn_ifo)
            row2.addWidget(self.lbl_vro)
            row2.addWidget(self.ed_vro, 1)
            row2.addWidget(self.btn_vro)
            g.addLayout(row2)

            self.lbl_info = QLabel()
            self.lbl_info.setWordWrap(True)
            g.addWidget(self.lbl_info)
            self.btn_load = QPushButton()
            self.btn_load.clicked.connect(self.load_disc)
            g.addWidget(self.btn_load)
            lay.addWidget(self.gb_choose)

            self.gb_programs = QGroupBox()
            v = QVBoxLayout(self.gb_programs)
            self.table = QTableWidget(0, 6)
            self.table.verticalHeader().setVisible(False)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setStretchLastSection(True)
            v.addWidget(self.table)
            row3 = QHBoxLayout()
            self.btn_all = QPushButton()
            self.btn_none = QPushButton()
            self.btn_all.clicked.connect(lambda: self.check_all(True))
            self.btn_none.clicked.connect(lambda: self.check_all(False))
            self.chk_remux = QCheckBox()
            self.chk_skip = QCheckBox()
            row3.addWidget(self.btn_all)
            row3.addWidget(self.btn_none)
            row3.addStretch(1)
            row3.addWidget(self.chk_skip)
            row3.addWidget(self.chk_remux)
            v.addLayout(row3)
            lay.addWidget(self.gb_programs, 1)

            self.gb_export = QGroupBox()
            v3 = QVBoxLayout(self.gb_export)
            row4 = QHBoxLayout()
            self.ed_out = QLineEdit()
            self.btn_browse = QPushButton()
            self.btn_browse.clicked.connect(self.pick_out)
            self.btn_start = QPushButton()
            self.btn_start.clicked.connect(self.start)
            self.btn_cancel = QPushButton()
            self.btn_cancel.setEnabled(False)
            self.btn_cancel.clicked.connect(self.cancel)
            row4.addWidget(self.ed_out, 1)
            row4.addWidget(self.btn_browse)
            row4.addWidget(self.btn_start)
            row4.addWidget(self.btn_cancel)
            v3.addLayout(row4)
            self.pbar = QProgressBar()
            self.pbar.setValue(0)
            v3.addWidget(self.pbar)
            lay.addWidget(self.gb_export)

            self.log = QTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumHeight(160)
            lay.addWidget(self.log)

        # ---- 语言
        def on_lang_changed(self, _idx):
            code = self.cmb_lang.currentData()
            if not code or code == get_lang():
                return
            set_lang(code)
            save_config(lang=code)
            self.retranslate()

        def retranslate(self):
            self.setWindowTitle("%s  v%s" % (t("app.name"), APP_VERSION))
            self.lbl_title.setText(t("app.name"))
            self.lbl_lang.setText(t("lang.label"))
            self.gb_choose.setTitle(t("group.choose"))
            self.btn_dir.setText(t("btn.choose_dir"))
            self.ed_folder.setPlaceholderText(t("placeholder.folder"))
            self.lbl_ifo.setText(t("label.ifo"))
            self.lbl_vro.setText(t("label.vro"))
            self.btn_ifo.setText(t("btn.ifo"))
            self.btn_vro.setText(t("btn.vro"))
            self.btn_load.setText(t("btn.load"))
            self.gb_programs.setTitle(t("group.programs"))
            self.table.setHorizontalHeaderLabels(
                [t("col.export"), t("col.index"), t("col.time"),
                 t("col.duration"), t("col.size"), t("col.offset")])
            self.btn_all.setText(t("btn.all"))
            self.btn_none.setText(t("btn.none"))
            self.chk_remux.setText(t("chk.remux"))
            self.chk_skip.setText(t("chk.skip_errors"))
            self.gb_export.setTitle(t("group.export"))
            self.btn_browse.setText(t("btn.browse"))
            self.ed_out.setPlaceholderText(t("placeholder.out"))
            self.btn_start.setText(t("btn.start"))
            self.btn_cancel.setText(t("btn.cancel"))
            self.lbl_info.setText(self._info_text() if self.info else t("info.none"))
            if self.info:
                self._fill_table()

        def _info_text(self) -> str:
            i = self.info
            return t("info.summary",
                     ifo=os.path.basename(i.ifo_path), vro=os.path.basename(i.vro_path),
                     n=len(i.programs), dur=fmt_ptm(i.total_duration),
                     size=fmt_bytes(i.total_bytes),
                     cprm=("\n" + t("info.cprm").strip()) if i.cprm else "")

        # ---- 交互
        def pick_dir(self):
            d = QFileDialog.getExistingDirectory(self, t("dlg.choose_dir"))
            if d:
                self.ed_folder.setText(d)
                self.load_disc()

        def pick_file(self, edit, filt):
            p, _ = QFileDialog.getOpenFileName(self, t("dlg.choose_ifo"), "", filt)
            if p:
                edit.setText(p)

        def pick_out(self):
            d = QFileDialog.getExistingDirectory(self, t("dlg.choose_out"))
            if d:
                self.ed_out.setText(d)
                if self.info and same_drive(d, self.info.vro_path):
                    drive = os.path.splitdrive(os.path.abspath(d))[0]
                    QMessageBox.warning(self, APP_NAME, t("msg.same_drive_pick", drive=drive))

        def check_all(self, on):
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if item:
                    item.setCheckState(Qt.Checked if on else Qt.Unchecked)

        def logln(self, s):
            self.log.append(s)

        def _fill_table(self):
            info = self.info
            self.table.setRowCount(len(info.programs))
            for r, p in enumerate(info.programs):
                old = self.table.item(r, 0)
                keep = old.checkState() if old is not None else Qt.Checked
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk.setCheckState(keep)
                self.table.setItem(r, 0, chk)
                for c, text in enumerate([str(p.index), p.time_label(),
                                          fmt_ptm(p.duration), fmt_bytes(p.byte_size),
                                          "%d" % p.start_byte], start=1):
                    it = QTableWidgetItem(text)
                    it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.table.setItem(r, c, it)

        def load_disc(self):
            folder = self.ed_folder.text().strip()
            ifo, vro = self.ed_ifo.text().strip(), self.ed_vro.text().strip()
            if folder and (not ifo or not vro):
                try:
                    fi, fv = find_disc_files(folder)
                except DVDVRError as e:
                    QMessageBox.warning(self, APP_NAME, str(e))
                    return
                ifo = ifo or fi
                vro = vro or fv
                if fi:
                    self.ed_ifo.setText(fi)
                if fv:
                    self.ed_vro.setText(fv)
            if not ifo or not vro:
                QMessageBox.warning(self, APP_NAME, t("msg.no_files"))
                return
            try:
                info = open_disc(ifo, vro)
            except DVDVRError as e:
                QMessageBox.critical(self, APP_NAME, str(e))
                self.info = None
                self.lbl_info.setText(t("info.none"))
                return

            self.info = info
            self.lbl_info.setText(self._info_text())
            self._fill_table()
            if not self.ed_out.text().strip():
                # 默认输出到 Windows 的“视频”文件夹（而不是光盘目录）
                out = videos_dir()
                if not os.path.isdir(out):
                    try:
                        os.makedirs(out, exist_ok=True)
                    except OSError:
                        out = os.path.expanduser("~")
                self.ed_out.setText(out)
            self.logln(t("log.loaded", n=len(info.programs)))
            if any(p.rec_time is None for p in info.programs):
                self.logln(t("log.auto_named"))

        def start(self):
            if not self.info:
                QMessageBox.warning(self, APP_NAME, t("msg.need_disc"))
                return
            if self.worker and self.worker.isRunning():
                return
            out = self.ed_out.text().strip()
            if not out:
                QMessageBox.warning(self, APP_NAME, t("msg.need_out"))
                return
            if self.info and same_drive(out, self.info.vro_path):
                drive = os.path.splitdrive(os.path.abspath(out))[0]
                ret = QMessageBox.question(
                    self, APP_NAME, t("msg.same_drive", drive=drive),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if ret != QMessageBox.Yes:
                    return
            try:
                ensure_output_dir(out)
            except DVDVRError as e:
                QMessageBox.critical(self, APP_NAME, str(e))
                return
            progs = [p for r, p in enumerate(self.info.programs)
                     if self.table.item(r, 0) and self.table.item(r, 0).checkState() == Qt.Checked]
            if not progs:
                QMessageBox.warning(self, APP_NAME, t("msg.no_selection"))
                return
            self.log.clear()
            self.pbar.setValue(0)
            self.btn_start.setEnabled(False)
            self.btn_cancel.setEnabled(True)
            self.worker = Worker(self.info, out, progs, self.chk_remux.isChecked(),
                                 self.chk_skip.isChecked())
            self.worker.progress.connect(self.on_progress)
            self.worker.log.connect(self.logln)
            self.worker.done.connect(self.on_done)
            self.worker.start()

        def on_progress(self, done, total):
            self.pbar.setMaximum(max(1, total))
            self.pbar.setValue(min(done, total))

        def on_done(self, ok, msg):
            self.btn_start.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self.logln(("✔ " if ok else "✘ ") + msg)
            if ok:
                QMessageBox.information(self, APP_NAME,
                                        t("msg.done_body", dir=self.ed_out.text()))
            else:
                QMessageBox.warning(self, APP_NAME, msg)

        def cancel(self):
            if self.worker:
                self.worker.cancel()
                self.logln(t("log.cancelling"))

    app = QApplication(sys.argv)
    w = Window(prefill_ifo, prefill_vro)
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
