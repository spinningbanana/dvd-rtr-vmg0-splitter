# This Python file uses the following encoding: utf-8

"""
DVD_RTR_VMG0 .VRO Splitter -- splits the .VRO file from DVDRAM camcorders into multiple .mpg files
Copyright (C) 2025 spinningbanana

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see https://www.gnu.org/licenses/.
"""

import os
import subprocess
import sys
import traceback

from datetime import datetime

from PySide6.QtWidgets import QApplication, QWidget, QFileDialog, QLabel, QScrollArea, QTextEdit, QCheckBox, QDoubleSpinBox, QPushButton
from PySide6.QtGui import QIcon
from ui_form import Ui_Splitter

class Splitter(QWidget):
    ENCODING = "utf-8"
    TAB = " "
    FILENAME_MAX_CHARS = 50

    # IMPORTANT OFFSETS FOR PARSING
    CLIPS_OFFSET = 68
    CLIPS_TITLE_OFFSET = -9
    CLIPS_DURATION_OFFSET = 4
    MARKER_OFFSET = 5
    TITLES_OFFSET = 73
    TITLES_END_OFFSET = 10

    ifo = None
    ifo_bin_size = -1
    ifo_clips = -1
    ifo_marker = None
    ifo_titles = {} # As of Python 3.7, dictionaires are ordered. This is very important!

    ifo_titles_ok = True
    ifo_durations = [] # only used if failed to map to titles

    vro = None

    clips_split = 0 # counter used when splitting clips

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Splitter()
        self.ui.setupUi(self)

        # get logo from resource path and set it
        label_title = self.findChild(QLabel, "label_title")
        pixmap = label_title.pixmap()
        pixmap.load(self.resource_path("logo.png"))
        label_title.setPixmap(pixmap)

        # get icon from resource path and set it
        self.setWindowIcon(QIcon(self.resource_path("icon.ico")))

    # taken from https://stackoverflow.com/a/13790741, thanks max
    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    def pts_to_seconds(self, pts):
        return pts / 90000

    def pts_to_frames(self, pts):
        return pts / 3003

    # IFO PARSING #####################################################################################

    # finds the two bytes that act as the marker for this file
    def get_marker(self, info_head, info_end, f):
        f.seek(int.from_bytes(info_head, "big") + self.CLIPS_OFFSET)

        odd = False
        while f.tell() < int.from_bytes(info_end, "big") and f.tell() < self.ifo_bin_size:
            next = f.read(2).hex()
            if odd and next != "0000":
                f.seek(self.MARKER_OFFSET, 1)
                return f.read(2).hex()
            odd = not odd
        return None


    # seeks the file to the next marker byte
    def seek_to_marker(self, f):
        prev_byte = ""

        while f.tell() < self.ifo_bin_size:
            byte = f.read(1).hex()

            if prev_byte == self.ifo_marker[:2] and byte == self.ifo_marker[-2:]:
                f.seek(-2, 1)
                return 0

            prev_byte = byte

        return -1

    # get all titles in file
    def get_titles(self, titles_head, f):
        f.seek(int.from_bytes(titles_head, "big"))

        while f.tell() < self.ifo_bin_size:
            f.seek(self.TITLES_OFFSET, 1)

            title = ""
            while f.tell() < self.ifo_bin_size:
                byte = f.read(1)

                if byte.hex() == "00":
                    break

                title += byte.decode(self.ENCODING)

            self.ifo_titles[title] = []

            self.seek_to_marker(f)
            pos = f.tell()
            f.seek(self.TITLES_END_OFFSET, 1)
            if f.read(1).hex() != "00":
                return 0
            else:
                f.seek(pos)

        return -1

    # get all clip durations in file
    def map_clips_to_titles(self, info_head, info_end, f):
        f.seek(int.from_bytes(info_head, "big"))
        titles = list(self.ifo_titles.keys())

        self.seek_to_marker(f)

        title_hashes = []
        while f.tell() < int.from_bytes(info_end, "big") and f.tell() < self.ifo_bin_size:
            marker = f.tell()

            f.seek(self.CLIPS_TITLE_OFFSET, 1)
            title_hash = f.read(3)

            f.seek(marker + self.CLIPS_DURATION_OFFSET)
            duration = int.from_bytes(f.read(4), "big")

            for i in range(len(title_hashes)):
                if title_hash == title_hashes[i]:
                    self.ifo_titles[titles[i]].append(duration)

            if title_hash not in title_hashes:
                title_str = titles[len(title_hashes)]
                self.ifo_titles[title_str].append(duration)
                title_hashes.append(title_hash)

            self.seek_to_marker(f)

    # get clip durations in their own list (in case mapping to titles failed)
    def get_clips(self, info_head, info_end, f):
        f.seek(int.from_bytes(info_head, "big"))

        self.seek_to_marker(f)

        while f.tell() < int.from_bytes(info_end, "big") and f.tell() < self.ifo_bin_size:
            marker = f.tell()

            f.seek(marker + self.CLIPS_DURATION_OFFSET)
            duration = int.from_bytes(f.read(4), "big")

            self.ifo_durations.append(duration)

            self.seek_to_marker(f)

    # returns a string, a formatted list of clips
    def list_clips(self, clips):
        count = 0
        output = ""
        for c in clips:
            count += 1
            output += f"{self.TAB} Clip {count}: {self.pts_to_seconds(c)} seconds, {self.pts_to_frames(c)} frames"
            if count < self.ifo_clips:
                output += "\n"
        return output

    # parse through the current ifo file
    # will obtain the following:
    #   number of clips in the ifo
    #   the titles present in the ifo
    #   the duration of each clip, along with which title it belongs to
    # then, will update and show the output with findings
    def parse_ifo(self):
        if not self.ifo:
            return

        checkbox_file_enforce = self.findChild(QCheckBox, "checkbox_file_enforce")

        output = ""
        try:
            with open(self.ifo, "rb") as f:
                type = f.read(12).decode(self.ENCODING)

                output += f".IFO type: {type}\n"

                if type != "DVD_RTR_VMG0" and checkbox_file_enforce.isChecked():
                    self.update_output(f'[CRITICAL] This .IFO is of type "{type}", not "DVD_RTR_VMG0"! Task aborted.', append=True)
                    self.ifo = None
                    self.update_selected()
                    return
                else:
                    output += f'[ALERT] This .IFO is of type "{type}", not "DVD_RTR_VMG0"!'

                f.seek(0x00000100)
                info_head = f.read(4)

                f.seek(0x00000104)
                info_end = f.read(4)

                # get size of binary
                f.seek(0, 2)
                self.ifo_bin_size = f.tell()

                # get the marker for this file
                self.ifo_marker = self.get_marker(info_head, info_end, f)

                if self.ifo_marker is None:
                    self.update_output("[CRITICAL] Could not find clip marker, aborted!", append=True)
                    self.ifo = None
                    self.update_selected()
                    return

                # get titles
                f.seek(0x00000130)
                titles_head = f.read(4)

                self.get_titles(titles_head, f)

                # get clip info
                f.seek(int.from_bytes(info_head, "big") + self.CLIPS_OFFSET)
                self.ifo_clips = int.from_bytes(f.read(2), "big")

                output += f"Number of clips: {str(self.ifo_clips)}\n"

                try:
                    self.map_clips_to_titles(info_head, info_end, f)

                    output += "\n[Titles and their clip durations]\n"
                    for t in list(self.ifo_titles.keys()):
                        output += t + ":\n"
                        output += self.list_clips(self.ifo_titles[t])
                except IndexError: # if assigning titles fails
                    self.get_clips(info_head, info_end, f)
                    self.ifo_titles_ok = False
                    output += "[ALERT] Failed to map clips to titles! Clips will not be grouped.\n"
                    output += "\n[Titles]\n"
                    for t in list(self.ifo_titles.keys()):
                        output += t + "\n"
                    output += "\n[Clips]\n"
                    output += self.list_clips(self.ifo_durations)

                self.update_output(output)

                return

        except FileNotFoundError:
            self.update_output("The .IFO file was not found??", append=True)
        except PermissionError:
            self.update_output("Cannot read the .IFO file (missing permissions)", append=True)
        except IOError:
            self.update_output("Something went wrong while reading the .IFO file", append=True)
        except OSError:
            self.update_output("Something went wrong while reading the .IFO file", append=True)
        except Exception:
            self.update_output("[CRITICAL] Reading the .IFO file resulted in the following:\n" + traceback.format_exc(), append=True)

        self.update_output(output, append=True)

    # VRO SPLITTING ###################################################################################

    # replaces '/', along with any other illegal characters with '-'
    # also removes spaces
    def clean_title(self, title):
        title = title.replace("/", "-")
        title = title.replace("\\", "-")
        title = title.replace(":", "-")
        title = title.replace("*", "-")
        title = title.replace("?", "-")
        title = title.replace('"', "-")
        title = title.replace("<", "-")
        title = title.replace(">", "-")
        title = title.replace("|", "-")
        title = title.replace(" ", "")
        return title

    # split all clips in a list and increase self.clips_split
    # send all clips to dest directory
    # returns the accumulated duration so far after splitting clips
    def split_clips(self, clips, dest, duration_so_far):
        checkbox_skip = self.findChild(QCheckBox, "checkbox_skip")
        spinbox_offset = self.findChild(QDoubleSpinBox, "spinbox_offset")

        for c in clips:
            self.clips_split += 1

            start = duration_so_far
            end = self.pts_to_seconds(c) + spinbox_offset.value()
            duration_so_far = start + end

            self.update_output(f"[{datetime.now()}] Splitting clip {self.clips_split}...", append=True, logging=True)

            # skip existing files
            if checkbox_skip.isChecked() and os.path.exists(f"{dest}{self.clips_split}.mpg"):
                self.update_output(f"[{datetime.now()}] Skipped clip {self.clips_split} as it already exists", append=True, logging=True)
                continue

            # i'm not using ffmpeg-python because it opens terminal popups that require editing
            # the code of ffmpeg-python to get rid of. so might as well do it myself and
            # minimize some jank

            job = subprocess.run([
                "ffmpeg",
                "-i", self.vro,
                "-ss", str(start),
                "-t", str(end),
                "-f", "dvd",
                "-c", "copy",
                f"{dest}{self.clips_split}.mpg",
                "-y"
            ], shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

            if job.returncode == 0:
                self.update_output(f"[{datetime.now()}] Successfully split clip {self.clips_split}", append=True, logging = True)
            else:
                self.update_output(f"[{datetime.now()}] Failed to split clip {self.clips_split}:\n{job.stderr.decode(self.ENCODING)}", append=True, logging = True)

        return duration_so_far

    # split all the clips in the .VRO with the help of ffmpeg
    def split(self, dir):
        if not dir:
            return

        initial_dir = os.getcwd()

        try:
            os.chdir(dir)
        except OSError:
            self.update_output("[CRITICAL] A problem occured while accessing the chosen directory!", append=True)
            return

        try:
            subprocess.run("ffmpeg", shell=True, stdin=subprocess.PIPE)
        except Exception:
            self.update_output("[CRITICAL] Failed to run ffmpeg. Is ffmpeg installed?", append=True)
            return

        self.clips_split = 0

        checkbox_grouping = self.findChild(QCheckBox, "checkbox_grouping")

        try:
            duration_so_far = 0

            self.update_output(f"[{datetime.now()}] NOW SPLITTING--program may seem frozen", append=True, logging=True)

            if self.ifo_titles_ok:
                for t in list(self.ifo_titles.keys()):
                    t_clean = self.clean_title(t)

                    dest = ""
                    if checkbox_grouping.isChecked():
                        dest = f"{os.getcwd()}/{t_clean}"
                        if not os.path.exists(dest):
                            os.mkdir(dest)
                        dest = f"{t_clean}/"

                    self.update_output(f'[{datetime.now()}] Now splitting clips in title "{t}"', append=True, logging=True)

                    duration_so_far = self.split_clips(self.ifo_titles[t], dest, duration_so_far)
            else:
                duration_so_far = self.split_clips(self.ifo_titles[t], "", 0)

            self.update_output(f"[{datetime.now()}] Finished!", append=True, logging=True)
        except OSError:
            self.update_output("[CRITICAL] A problem occured while splitting!\n" + traceback.format_exc(), append=True, logging=True)

        os.chdir(initial_dir)

    # INTERACTIONS WITH UI ELEMENTS ###################################################################

    # updates the output scroll pane
    # set append to True for the new text to be appended onto the existing output,
    # otherwise it will override the text
    # additionally, adds to the log.txt file
    def update_output(self, text, append=False, logging=False):
        output = (self.findChild(QScrollArea, "output")
                    .findChild(QWidget, "output_contents")
                    .findChild(QTextEdit, "output_text"))

        if append:
            output.setText(text + "\n" + output.toPlainText())
        else:
            output.setText(text)

        if logging:
            with open("log.txt", "a") as f:
                f.write(text + "\n")
                f.flush()

        QApplication.processEvents()

    def limit_characters(self, s):
        if len(s) > self.FILENAME_MAX_CHARS:
            s = f"{s[:(self.FILENAME_MAX_CHARS - 19)]}... ...{s[-12:]}"
        return s

    # updates the "Selected: NONE" next to the ifo and vro buttons
    # if both have been selected, enable button_split
    def update_selected(self):
        selected_ifo = self.findChild(QLabel, "selected_ifo")
        selected_vro = self.findChild(QLabel, "selected_vro")
        button_split = self.findChild(QPushButton, "button_split")

        if self.ifo:
            selected_ifo.setText("Selected: " + self.limit_characters(os.path.basename(self.ifo)))
            selected_ifo.setToolTip(self.ifo)
        else:
            selected_ifo.setText("Selected: NONE")

        if self.vro:
            selected_vro.setText("Selected: " + self.limit_characters(os.path.basename(self.vro)))
            selected_vro.setToolTip(self.vro)
        else:
            selected_vro.setText("Selected: NONE")

        if self.ifo and self.vro:
            button_split.setEnabled(True)
        else:
            button_split.setEnabled(False)

    # "select ifo" button in the ui calls this function
    def choose_ifo(self):
        self.ifo_titles.clear()
        self.ifo_titles_ok = True

        file = QFileDialog.getOpenFileName(
            self,
            "Choose .IFO",
            "",
            "Choose file (*.IFO)"
        )[0]

        if file:
            self.ifo = file
            self.update_selected()
            self.parse_ifo()

    # "select vro" button in the ui calls this function
    def choose_vro(self):
        file = QFileDialog.getOpenFileName(
            self,
            "Choose .VRO",
            "",
            "Choose file (*.VRO)"
        )[0]

        if file:
            self.vro = file
            self.update_selected()

    # "split vro button in the ui calls this function
    def split_vro(self):
        destination = QFileDialog.getExistingDirectory(
            self, "Choose Destination",
            "",
            QFileDialog.ShowDirsOnly
            |QFileDialog.DontResolveSymlinks
        )

        self.split(destination)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Splitter()
    widget.show()

    sys.exit(app.exec())
