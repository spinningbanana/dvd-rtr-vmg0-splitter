# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.5.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QWidget)

class Ui_Splitter(object):
    def setupUi(self, Splitter):
        if not Splitter.objectName():
            Splitter.setObjectName(u"Splitter")
        Splitter.resize(540, 550)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Splitter.sizePolicy().hasHeightForWidth())
        Splitter.setSizePolicy(sizePolicy)
        Splitter.setMinimumSize(QSize(540, 550))
        Splitter.setMaximumSize(QSize(540, 550))
        font = QFont()
        font.setFamilies([u"MS Gothic"])
        font.setPointSize(9)
        Splitter.setFont(font)
        Splitter.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.button_ifo = QPushButton(Splitter)
        self.button_ifo.setObjectName(u"button_ifo")
        self.button_ifo.setGeometry(QRect(80, 140, 381, 21))
        self.button_ifo.setFont(font)
        self.button_ifo.setCheckable(False)
        self.button_vro = QPushButton(Splitter)
        self.button_vro.setObjectName(u"button_vro")
        self.button_vro.setGeometry(QRect(80, 180, 381, 21))
        self.button_vro.setFont(font)
        self.button_vro.setCheckable(False)
        self.label_title = QLabel(Splitter)
        self.label_title.setObjectName(u"label_title")
        self.label_title.setGeometry(QRect(50, 20, 440, 80))
        font1 = QFont()
        font1.setFamilies([u"MS UI Gothic"])
        font1.setPointSize(18)
        font1.setBold(False)
        self.label_title.setFont(font1)
        self.label_title.setTextFormat(Qt.TextFormat.RichText)
        self.label_title.setScaledContents(True)
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output = QScrollArea(Splitter)
        self.output.setObjectName(u"output")
        self.output.setGeometry(QRect(50, 350, 441, 161))
        self.output.setWidgetResizable(True)
        self.output_contents = QWidget()
        self.output_contents.setObjectName(u"output_contents")
        self.output_contents.setGeometry(QRect(0, 0, 439, 159))
        self.output_text = QTextEdit(self.output_contents)
        self.output_text.setObjectName(u"output_text")
        self.output_text.setGeometry(QRect(0, 0, 441, 161))
        sizePolicy1 = QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.output_text.sizePolicy().hasHeightForWidth())
        self.output_text.setSizePolicy(sizePolicy1)
        self.output_text.setFont(font)
        self.output_text.setReadOnly(True)
        self.output.setWidget(self.output_contents)
        self.button_split = QPushButton(Splitter)
        self.button_split.setObjectName(u"button_split")
        self.button_split.setEnabled(False)
        self.button_split.setGeometry(QRect(80, 310, 381, 21))
        self.button_split.setFont(font)
        self.button_split.setCheckable(False)
        self.label_output = QLabel(Splitter)
        self.label_output.setObjectName(u"label_output")
        self.label_output.setGeometry(QRect(80, 330, 81, 21))
        font2 = QFont()
        font2.setFamilies([u"MS Gothic"])
        font2.setPointSize(11)
        self.label_output.setFont(font2)
        self.label_output.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.label_output.setIndent(5)
        self.selected_ifo = QLabel(Splitter)
        self.selected_ifo.setObjectName(u"selected_ifo")
        self.selected_ifo.setGeometry(QRect(0, 160, 541, 20))
        self.selected_ifo.setMaximumSize(QSize(16777215, 16777215))
        self.selected_ifo.setFont(font)
        self.selected_ifo.setTextFormat(Qt.TextFormat.AutoText)
        self.selected_ifo.setScaledContents(False)
        self.selected_ifo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_ifo.setWordWrap(False)
        self.selected_ifo.setMargin(0)
        self.selected_ifo.setIndent(10)
        self.selected_vro = QLabel(Splitter)
        self.selected_vro.setObjectName(u"selected_vro")
        self.selected_vro.setGeometry(QRect(0, 200, 541, 20))
        self.selected_vro.setFont(font)
        self.selected_vro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_vro.setMargin(0)
        self.selected_vro.setIndent(10)
        self.spinbox_offset = QDoubleSpinBox(Splitter)
        self.spinbox_offset.setObjectName(u"spinbox_offset")
        self.spinbox_offset.setGeometry(QRect(140, 280, 131, 20))
        self.spinbox_offset.setFont(font)
        self.spinbox_offset.setDecimals(4)
        self.spinbox_offset.setMinimum(-1.000000000000000)
        self.spinbox_offset.setMaximum(1.000000000000000)
        self.spinbox_offset.setSingleStep(0.000100000000000)
        self.spinbox_offset.setValue(0.000000000000000)
        self.label_offset = QLabel(Splitter)
        self.label_offset.setObjectName(u"label_offset")
        self.label_offset.setGeometry(QRect(270, 280, 101, 21))
        self.label_offset.setFont(font)
        self.label_offset.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.label_offset.setMargin(0)
        self.label_offset.setIndent(2)
        self.checkbox_grouping = QCheckBox(Splitter)
        self.checkbox_grouping.setObjectName(u"checkbox_grouping")
        self.checkbox_grouping.setGeometry(QRect(140, 240, 231, 20))
        self.checkbox_grouping.setFont(font)
        self.checkbox_grouping.setChecked(True)
        self.hint_offset = QLabel(Splitter)
        self.hint_offset.setObjectName(u"hint_offset")
        self.hint_offset.setGeometry(QRect(370, 280, 31, 21))
        self.hint_offset.setFont(font)
        self.hint_offset.setToolTipDuration(-1)
        self.hint_offset.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.hint_offset.setMargin(0)
        self.hint_offset.setIndent(2)
        self.hint_grouping = QLabel(Splitter)
        self.hint_grouping.setObjectName(u"hint_grouping")
        self.hint_grouping.setGeometry(QRect(370, 240, 31, 21))
        self.hint_grouping.setFont(font)
        self.hint_grouping.setToolTipDuration(-1)
        self.hint_grouping.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.hint_grouping.setMargin(0)
        self.hint_grouping.setIndent(2)
        self.label_splitting = QLabel(Splitter)
        self.label_splitting.setObjectName(u"label_splitting")
        self.label_splitting.setGeometry(QRect(80, 220, 101, 21))
        self.label_splitting.setFont(font2)
        self.label_splitting.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.label_splitting.setIndent(5)
        self.checkbox_skip = QCheckBox(Splitter)
        self.checkbox_skip.setObjectName(u"checkbox_skip")
        self.checkbox_skip.setGeometry(QRect(140, 260, 231, 20))
        self.checkbox_skip.setFont(font)
        self.checkbox_skip.setChecked(True)
        self.hint_skip = QLabel(Splitter)
        self.hint_skip.setObjectName(u"hint_skip")
        self.hint_skip.setGeometry(QRect(370, 260, 31, 21))
        self.hint_skip.setFont(font)
        self.hint_skip.setToolTipDuration(-1)
        self.hint_skip.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.hint_skip.setMargin(0)
        self.hint_skip.setIndent(2)
        self.meta_version = QLabel(Splitter)
        self.meta_version.setObjectName(u"meta_version")
        self.meta_version.setGeometry(QRect(280, 510, 211, 20))
        self.meta_version.setFont(font)
        self.meta_version.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignTrailing)
        self.meta_version.setMargin(0)
        self.meta_version.setIndent(0)
        self.meta_copyright = QLabel(Splitter)
        self.meta_copyright.setObjectName(u"meta_copyright")
        self.meta_copyright.setGeometry(QRect(50, 510, 211, 20))
        self.meta_copyright.setFont(font)
        self.meta_copyright.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.meta_copyright.setMargin(0)
        self.meta_copyright.setIndent(1)
        self.hint_file_enforce = QLabel(Splitter)
        self.hint_file_enforce.setObjectName(u"hint_file_enforce")
        self.hint_file_enforce.setGeometry(QRect(370, 120, 31, 21))
        self.hint_file_enforce.setFont(font)
        self.hint_file_enforce.setToolTipDuration(-1)
        self.hint_file_enforce.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.hint_file_enforce.setMargin(0)
        self.hint_file_enforce.setIndent(2)
        self.checkbox_file_enforce = QCheckBox(Splitter)
        self.checkbox_file_enforce.setObjectName(u"checkbox_file_enforce")
        self.checkbox_file_enforce.setEnabled(True)
        self.checkbox_file_enforce.setGeometry(QRect(140, 120, 231, 20))
        self.checkbox_file_enforce.setFont(font)
        self.checkbox_file_enforce.setCheckable(True)
        self.checkbox_file_enforce.setChecked(True)

        self.retranslateUi(Splitter)
        self.button_ifo.clicked.connect(Splitter.choose_ifo)
        self.button_vro.clicked.connect(Splitter.choose_vro)
        self.button_split.clicked.connect(Splitter.split_vro)

        QMetaObject.connectSlotsByName(Splitter)
    # setupUi

    def retranslateUi(self, Splitter):
        Splitter.setWindowTitle(QCoreApplication.translate("Splitter", u"Splitter", None))
        Splitter.setWindowFilePath("")
        self.button_ifo.setText(QCoreApplication.translate("Splitter", u"Choose .IFO", None))
        self.button_vro.setText(QCoreApplication.translate("Splitter", u"Choose .VRO", None))
        self.label_title.setText("")
        self.button_split.setText(QCoreApplication.translate("Splitter", u"Split .VRO", None))
        self.label_output.setText(QCoreApplication.translate("Splitter", u"Output", None))
        self.selected_ifo.setText(QCoreApplication.translate("Splitter", u"Selected: NONE", None))
        self.selected_vro.setText(QCoreApplication.translate("Splitter", u"Selected: NONE", None))
        self.label_offset.setText(QCoreApplication.translate("Splitter", u"Split Offset", None))
        self.checkbox_grouping.setText(QCoreApplication.translate("Splitter", u"Group clips by title", None))
#if QT_CONFIG(tooltip)
        self.hint_offset.setToolTip(QCoreApplication.translate("Splitter", u"<html><head/><body><p>How many seconds to offset splitting by. </p><p>May be useful as ffmpeg trimming isn't perfect so there may be a few frames of the next clip at the end of each clip. Tweaking this will help mitigate it, but still may not be perfect...</p><p>(e.g. offset of -0.2937: two clips 12s and 15s --&gt; 11.7063s and 14.7063s)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.hint_offset.setText(QCoreApplication.translate("Splitter", u"(?)", None))
#if QT_CONFIG(tooltip)
        self.hint_grouping.setToolTip(QCoreApplication.translate("Splitter", u"<html><head/><body><p>Whether or not clips should be grouped into directories based on their titles or not (when possible)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.hint_grouping.setStatusTip("")
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.hint_grouping.setWhatsThis("")
#endif // QT_CONFIG(whatsthis)
        self.hint_grouping.setText(QCoreApplication.translate("Splitter", u"(?)", None))
        self.label_splitting.setText(QCoreApplication.translate("Splitter", u"Splitting", None))
        self.checkbox_skip.setText(QCoreApplication.translate("Splitter", u"Skip existing clips", None))
#if QT_CONFIG(tooltip)
        self.hint_skip.setToolTip(QCoreApplication.translate("Splitter", u"<html><head/><body><p>Whether or not existing clips in the chosen directory should be skipped</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.hint_skip.setStatusTip("")
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.hint_skip.setWhatsThis("")
#endif // QT_CONFIG(whatsthis)
        self.hint_skip.setText(QCoreApplication.translate("Splitter", u"(?)", None))
        self.meta_version.setText(QCoreApplication.translate("Splitter", u"v1.0.2", None))
        self.meta_copyright.setText(QCoreApplication.translate("Splitter", u"\u00a9 2025 spinningbanana", None))
#if QT_CONFIG(tooltip)
        self.hint_file_enforce.setToolTip(QCoreApplication.translate("Splitter", u"<html><head/><body><p>Whether or not the &quot;DVD_RTR_VMG0&quot; .IFO file type should be enforced. </p><p>NOTICE: If you uncheck this and submit an .IFO file that is not of type &quot;DVD_RTR_VMG0&quot;, things may break!</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.hint_file_enforce.setStatusTip("")
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.hint_file_enforce.setWhatsThis("")
#endif // QT_CONFIG(whatsthis)
        self.hint_file_enforce.setText(QCoreApplication.translate("Splitter", u"(?)", None))
        self.checkbox_file_enforce.setText(QCoreApplication.translate("Splitter", u"Enforce file type", None))
    # retranslateUi

