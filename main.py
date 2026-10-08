"""
Honsen Africa — Container Tracker Desktop
主界面入口

依赖: pip install PyQt6 nodriver
运行: py -3.12 main.py（需要 PyQt6 与 nodriver）
"""

import sys
import asyncio
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame,
    QStackedWidget, QTextEdit, QDialog, QDialogButtonBox, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPalette, QCursor

from core import carriers, cache, history
from grabbers import get_grabber

# ── 颜色 ────────────────────────────────────────
BG     = "#0f172a"
PANEL  = "#1e293b"
PANEL2 = "#243044"
BORDER = "#334155"
BORDER2= "#475569"
ACCENT = "#f97316"
CYAN   = "#38bdf8"
GREEN  = "#4ade80"
YELLOW = "#fbbf24"
RED    = "#f87171"
TEXT   = "#f1f5f9"
MUTED  = "#94a3b8"
DIM    = "#475569"

QSS = f"""
QMainWindow, QWidget#root {{ background:{BG}; color:{TEXT}; }}
QWidget {{ background:transparent; color:{TEXT};
    font-family:'Segoe UI','Microsoft YaHei',sans-serif; }}
QScrollArea {{ border:none; background:transparent; }}
QScrollBar:vertical {{ background:{PANEL}; width:6px; border-radius:3px; }}
QScrollBar::handle:vertical {{ background:{BORDER2}; border-radius:3px; min-height:20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}

QLineEdit#searchInput {{
    background:{BG}; border:1px solid {BORDER}; border-radius:6px;
    color:{TEXT}; padding:0 16px; font-size:14px;
    letter-spacing:2px; height:40px;
}}
QLineEdit#searchInput:focus {{ border-color:{ACCENT}; }}
QComboBox#carrierSelect {{
    background:{BG}; border:1px solid {BORDER}; border-radius:6px;
    color:{TEXT}; padding:0 10px; font-size:12px; height:40px;
}}
QComboBox#carrierSelect:focus {{ border-color:{ACCENT}; }}
QComboBox#carrierSelect::drop-down {{ border:none; width:22px; }}
QComboBox#carrierSelect QAbstractItemView {{ background:{PANEL}; color:{TEXT}; selection-background-color:{PANEL2}; }}

QPushButton#trackBtn {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {ACCENT},stop:1 #ea6c00);
    border:none; border-radius:6px; color:white;
    font-size:13px; font-weight:bold; letter-spacing:1.5px;
    padding:0 20px; height:40px; min-width:100px;
}}
QPushButton#trackBtn:hover {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #fb923c,stop:1 {ACCENT});
}}
QPushButton#trackBtn:pressed {{ background:#ea6c00; }}

QPushButton#iconBtn {{
    background:transparent; border:1px solid {BORDER};
    border-radius:6px; color:{MUTED}; font-size:15px;
    width:40px; height:40px; min-width:40px; max-width:40px;
}}
QPushButton#iconBtn:hover {{ border-color:{ACCENT}; color:{ACCENT}; }}
QPushButton#iconBtn:checked {{ border-color:{ACCENT}; color:{ACCENT}; }}

QPushButton#dangerBtn {{
    background:transparent; border:1px solid {BORDER};
    border-radius:6px; color:{MUTED}; font-size:16px;
    width:40px; height:40px; min-width:40px; max-width:40px;
}}
QPushButton#dangerBtn:hover {{ border-color:{RED}; color:{RED}; }}

QPushButton#smallBtn {{
    background:transparent; border:1px solid {BORDER};
    border-radius:5px; color:{MUTED};
    font-size:11px; padding:3px 10px; height:26px;
}}
QPushButton#smallBtn:hover {{ border-color:{CYAN}; color:{CYAN}; }}

QPushButton#miniBtn {{
    background:transparent; border:1px solid {BORDER};
    border-radius:4px; color:{MUTED};
    font-size:11px; width:22px; height:22px;
    min-width:22px; max-width:22px;
}}
QPushButton#miniBtn:hover {{ border-color:{CYAN}; color:{CYAN}; }}

QPushButton#miniDangerBtn {{
    background:transparent; border:1px solid {BORDER};
    border-radius:4px; color:{MUTED};
    font-size:13px; font-weight:bold;
    width:22px; height:22px; min-width:22px; max-width:22px;
}}
QPushButton#miniDangerBtn:hover {{ border-color:{RED}; color:{RED}; }}

QFrame#topbar   {{ background:{PANEL}; border-bottom:1px solid {BORDER}; }}
QFrame#sidebar  {{ background:{PANEL}; border-right:1px solid {BORDER}; }}
QFrame#statusbar{{ background:#0a101e; border-top:1px solid {BORDER}; }}
QFrame#histItem {{ background:transparent; border-bottom:1px solid rgba(51,65,85,0.4); }}
QFrame#routeCard{{ background:{PANEL2}; border-radius:8px; }}
QFrame#divider  {{ background:{BORDER}; }}

QTextEdit#noteInput {{
    background:{BG}; border:1px solid {BORDER};
    border-radius:5px; color:{TEXT}; font-size:12px; padding:6px;
}}
QTextEdit#noteInput:focus {{ border-color:{CYAN}; }}
QDialog {{ background:{PANEL}; color:{TEXT}; }}
QMessageBox {{ background:{PANEL}; color:{TEXT}; }}
"""


# ── 抓取线程 ─────────────────────────────────────
class FetchWorker(QThread):
    result = pyqtSignal(dict)
    error  = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, no: str, carrier_override: tuple[str, str] | None = None):
        super().__init__()
        self.no = no
        self.carrier_override = carrier_override

    def run(self):
        cached = None if self.carrier_override else cache.get(self.no)
        if cached:
            self.result.emit(cached)
            return

        carrier_name, grabber_name = self.carrier_override or (
            carriers.get_carrier_name(self.no), carriers.get_grabber_name(self.no)
        )
        if not grabber_name:
            self.error.emit(f'未识别的承运商前缀：{self.no[:4]}\n请手动前往官网查询。')
            return

        grabber = get_grabber(grabber_name, self.no, carrier_name)
        grabber.on_status = lambda msg: self.status.emit(msg)  # 注入状态回调
        if not grabber:
            self.error.emit(f'{grabber_name} 抓取器尚未实现\n可在 grabbers/{grabber_name}.py 中添加。')
            return

        self.status.emit(f'⟳ 正在启动 {grabber_name} 抓取器...')
        try:
            data = asyncio.run(grabber.fetch())
            if self.carrier_override:
                data['carrier'] = carrier_name
            if not data.pop('_skip_cache', False):
                cache.set(self.no, data)
            data['_cached'] = False
            self.result.emit(data)
        except NotImplementedError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f'抓取失败：{e}')


# ── 历史条目 ─────────────────────────────────────
class HistItem(QFrame):
    # 用 str/object 避免 int 信号与 clicked(bool) 混淆
    trackReq  = pyqtSignal(str)   # 点条目 → 查询
    deleteReq = pyqtSignal(object)  # 删除
    editReq   = pyqtSignal(object, str, str)  # 编辑备注

    def __init__(self, h: dict, parent=None):
        super().__init__(parent)
        self.h   = h
        self.hid = h['id']
        self.setObjectName('histItem')
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._build()

    def _build(self):
        h   = self.h
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 9, 14, 9)
        lay.setSpacing(3)

        # 箱号
        no_lbl = QLabel(h['no'])
        no_lbl.setStyleSheet(
            f"color:{ACCENT}; font-family:'Courier New';"
            f"font-size:13px; font-weight:bold; letter-spacing:2px;"
        )
        lay.addWidget(no_lbl)

        # 元信息
        meta = QHBoxLayout()
        meta.setSpacing(8)
        c_lbl = QLabel(h.get('carrier', ''))
        c_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        meta.addWidget(c_lbl)
        meta.addStretch()
        t_lbl = QLabel(history.fmt_time(h.get('time', '')))
        t_lbl.setStyleSheet(f"color:{DIM}; font-size:10px; font-family:'Courier New';")
        meta.addWidget(t_lbl)
        lay.addLayout(meta)

        # 备注
        if h.get('note'):
            n_lbl = QLabel(f"📝 {h['note']}")
            n_lbl.setStyleSheet(f"color:{CYAN}; font-size:11px; font-style:italic;")
            n_lbl.setWordWrap(True)
            lay.addWidget(n_lbl)

        # 按钮行
        self.btn_row = QWidget()
        br = QHBoxLayout(self.btn_row)
        br.setContentsMargins(0, 2, 0, 0)
        br.setSpacing(4)
        br.addStretch()

        edit_btn = QPushButton('✏')
        edit_btn.setObjectName('miniBtn')
        edit_btn.setFixedSize(22, 22)
        # 用 lambda 不带 checked 参数，用实例变量捕获
        edit_btn.clicked.connect(self._on_edit_click)
        br.addWidget(edit_btn)

        del_btn = QPushButton('×')
        del_btn.setObjectName('miniDangerBtn')
        del_btn.setFixedSize(22, 22)
        del_btn.clicked.connect(self._on_del_click)
        br.addWidget(del_btn)

        self.btn_row.setVisible(False)
        lay.addWidget(self.btn_row)

    def _on_edit_click(self):
        self.editReq.emit(self.hid, self.h['no'], self.h.get('note', ''))

    def _on_del_click(self):
        self.deleteReq.emit(self.hid)

    def enterEvent(self, e):
        self.btn_row.setVisible(True)
        self.setStyleSheet(
            f"QFrame#histItem {{background:rgba(249,115,22,0.05);"
            f"border-bottom:1px solid rgba(51,65,85,0.4);}}"
        )

    def leaveEvent(self, e):
        self.btn_row.setVisible(False)
        self.setStyleSheet(
            f"QFrame#histItem {{background:transparent;"
            f"border-bottom:1px solid rgba(51,65,85,0.4);}}"
        )

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.btn_row.isVisible() and self.btn_row.geometry().contains(e.pos()):
                super().mousePressEvent(e)
                return
            self.trackReq.emit(self.h['no'])


# ── 备注对话框 ───────────────────────────────────
class NoteDialog(QDialog):
    def __init__(self, no: str, note: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'备注 — {no}')
        self.setFixedSize(400, 210)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        lbl = QLabel(f'📝 为 <span style="color:{ACCENT}">{no}</span> 添加备注')
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setStyleSheet("font-size:13px;")
        lay.addWidget(lbl)

        self.edit = QTextEdit()
        self.edit.setObjectName('noteInput')
        self.edit.setPlainText(note)
        self.edit.setFixedHeight(80)
        self.edit.setPlaceholderText('如：精装材料、客梯、卫浴洁具…')
        lay.addWidget(self.edit)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.setStyleSheet(f"""
            QPushButton {{
                background:{CYAN}; color:#0f172a; border:none;
                border-radius:5px; padding:6px 18px; font-weight:bold;
            }}
            QPushButton:last-child {{
                background:transparent; color:{MUTED};
                border:1px solid {BORDER};
            }}
        """)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_note(self) -> str:
        return self.edit.toPlainText().strip()


# ── 主窗口 ───────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Honsen Africa · Container Tracker')
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self._worker = None
        self._build_ui()
        self._refresh_history()
        self._start_clock()

    def _build_ui(self):
        root = QWidget(); root.setObjectName('root')
        self.setCentralWidget(root)
        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)
        vlay.addWidget(self._make_topbar())
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        self.sidebar = self._make_sidebar()
        bl.addWidget(self.sidebar)
        bl.addWidget(self._make_main(), 1)
        vlay.addWidget(body, 1)
        vlay.addWidget(self._make_statusbar())

    # ── Topbar ───────────────────────────────────
    def _make_topbar(self):
        bar = QFrame(); bar.setObjectName('topbar'); bar.setFixedHeight(64)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0); lay.setSpacing(12)

        ico = QLabel('🚢')
        ico.setFixedSize(34, 34)
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                          f"stop:0 {ACCENT},stop:1 #c2410c);"
                          f"border-radius:7px; font-size:18px;")
        lay.addWidget(ico)

        nw = QWidget()
        nl = QVBoxLayout(nw); nl.setContentsMargins(0,0,0,0); nl.setSpacing(1)
        n1 = QLabel('HONSEN AFRICA')
        n1.setStyleSheet(f"font-size:13px; font-weight:bold; color:{ACCENT}; letter-spacing:2px;")
        n2 = QLabel('WMS · LOGISTICS CONSOLE v1.0')
        n2.setStyleSheet(f"font-size:10px; color:{DIM};")
        nl.addWidget(n1); nl.addWidget(n2)
        lay.addWidget(nw)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(32); sep.setStyleSheet(f"color:{BORDER};")
        lay.addWidget(sep)

        self.search_input = QLineEdit()
        self.search_input.setObjectName('searchInput')
        self.search_input.setPlaceholderText('MRSU6845613  ·  输入集装箱号（4字母+7数字）')
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(self._do_track)
        self.search_input.textChanged.connect(self._on_input_change)
        lay.addWidget(self.search_input, 1)

        self.carrier_select = QComboBox()
        self.carrier_select.setObjectName('carrierSelect')
        self.carrier_select.setFixedWidth(165)
        self.carrier_select.addItem('自动识别', None)
        for name, grabber_name in carriers.get_carrier_options():
            self.carrier_select.addItem(name, (name, grabber_name))
        self.carrier_select.currentIndexChanged.connect(self._on_carrier_change)
        lay.addWidget(self.carrier_select)

        self.badge = QLabel(); self.badge.setVisible(False)
        self.badge.setStyleSheet(f"background:rgba(56,189,248,0.08);"
                                 f"border:1px solid rgba(56,189,248,0.3);"
                                 f"color:{CYAN}; border-radius:4px;"
                                 f"padding:2px 10px; font-size:11px; font-family:'Courier New';")
        lay.addWidget(self.badge)

        track_btn = QPushButton('TRACK ▶')
        track_btn.setObjectName('trackBtn'); track_btn.setFixedHeight(40)
        track_btn.clicked.connect(self._do_track)
        lay.addWidget(track_btn)

        clear_btn = QPushButton('✕')
        clear_btn.setObjectName('dangerBtn'); clear_btn.setFixedSize(40, 40)
        clear_btn.clicked.connect(self._do_clear)
        lay.addWidget(clear_btn)

        self.hist_btn = QPushButton('🕐')
        self.hist_btn.setObjectName('iconBtn'); self.hist_btn.setFixedSize(40, 40)
        self.hist_btn.setCheckable(True)
        self.hist_btn.clicked.connect(self._toggle_sidebar)
        lay.addWidget(self.hist_btn)
        return bar

    # ── Sidebar ──────────────────────────────────
    def _make_sidebar(self):
        sb = QFrame(); sb.setObjectName('sidebar')
        sb.setFixedWidth(0); sb.setMaximumWidth(300)
        lay = QVBoxLayout(sb); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        head = QFrame(); head.setFixedHeight(44)
        head.setStyleSheet(f"border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(head); hl.setContentsMargins(14,0,14,0); hl.setSpacing(8)
        title = QLabel('📋 查询历史')
        title.setStyleSheet(f"font-size:11px; font-weight:bold; color:{MUTED}; letter-spacing:2px;")
        hl.addWidget(title); hl.addStretch()
        clr = QPushButton('清空'); clr.setObjectName('smallBtn')
        clr.clicked.connect(self._clear_history)
        hl.addWidget(clr)
        lay.addWidget(head)

        self.hist_scroll = QScrollArea(); self.hist_scroll.setWidgetResizable(True)
        self.hist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.hist_container = QWidget()
        self.hist_layout = QVBoxLayout(self.hist_container)
        self.hist_layout.setContentsMargins(0,0,0,0); self.hist_layout.setSpacing(0)
        self.hist_layout.addStretch()
        self.hist_scroll.setWidget(self.hist_container)
        lay.addWidget(self.hist_scroll)
        return sb

    # ── Main stack ───────────────────────────────
    def _make_main(self):
        self.stack = QStackedWidget()

        # 0: 空状态
        idle = QWidget()
        il = QVBoxLayout(idle); il.setAlignment(Qt.AlignmentFlag.AlignCenter); il.setSpacing(14)
        il.addWidget(self._lbl('🌍', f"font-size:56px;", center=True))
        il.addWidget(self._lbl('CONTAINER TRACKER',
            f"font-size:20px; font-weight:bold; color:{DIM}; letter-spacing:4px;", center=True))
        il.addWidget(self._lbl(
            '输入集装箱号，自动识别承运商并查询追踪数据\n'
            '■ 本地缓存 12 小时，重复查询秒出结果\n'
            '■ 暂不支持自动解析的航司将打开其官网追踪页\n'
            '■ 完整运踪时间轴，港口、船名、时间一览\n'
            '■ 历史记录 + 备注，随时查阅',
            f"font-size:11px; color:{DIM};", center=True))
        self.stack.addWidget(idle)  # 0

        # 1: 加载中
        loading = QWidget()
        ll = QVBoxLayout(loading); ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_lbl = QLabel('⟳ 正在查询...')
        self.loading_lbl.setStyleSheet(f"font-size:14px; color:{MUTED}; font-family:'Courier New';")
        self.loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_lbl.setWordWrap(True)
        ll.addWidget(self.loading_lbl)
        self.stack.addWidget(loading)  # 1

        # 2: 结果
        rs = QScrollArea(); rs.setWidgetResizable(True)
        rs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_w = QWidget()
        self.result_lay = QVBoxLayout(self.result_w)
        self.result_lay.setContentsMargins(24, 20, 24, 24); self.result_lay.setSpacing(0)
        self.result_lay.addStretch()
        rs.setWidget(self.result_w)
        self.stack.addWidget(rs)  # 2

        # 3: 错误
        ew = QWidget()
        el = QVBoxLayout(ew); el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl = QLabel()
        self.error_lbl.setStyleSheet(f"font-size:13px; color:{RED}; font-family:'Courier New';")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl.setWordWrap(True)
        el.addWidget(self.error_lbl)
        retry = QPushButton('🔄 重新查询'); retry.setObjectName('smallBtn')
        retry.clicked.connect(self._do_track)
        el.addWidget(retry, 0, Qt.AlignmentFlag.AlignHCenter)
        self.stack.addWidget(ew)  # 3

        return self.stack

    # ── Statusbar ────────────────────────────────
    def _make_statusbar(self):
        bar = QFrame(); bar.setObjectName('statusbar'); bar.setFixedHeight(28)
        lay = QHBoxLayout(bar); lay.setContentsMargins(14,0,14,0); lay.setSpacing(10)
        self.dot = QLabel('●')
        self.dot.setStyleSheet(f"color:{GREEN}; font-size:8px;")
        lay.addWidget(self.dot)
        self.status_lbl = QLabel('系统就绪 — 等待查询指令')
        self.status_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px; font-family:'Courier New';")
        lay.addWidget(self.status_lbl, 1)
        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet(f"color:{DIM}; font-size:10px; font-family:'Courier New';")
        lay.addWidget(self.clock_lbl)
        return bar

    # ── 工具 ─────────────────────────────────────
    def _lbl(self, text, style='', center=False):
        l = QLabel(text)
        if style: l.setStyleSheet(style)
        if center: l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setWordWrap(True)
        return l

    def _set_status(self, msg, color=GREEN):
        self.status_lbl.setText(msg)
        self.dot.setStyleSheet(f"color:{color}; font-size:8px;")

    def _start_clock(self):
        self._tick()
        t = QTimer(self); t.timeout.connect(self._tick); t.start(1000)

    def _tick(self):
        self.clock_lbl.setText(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '  © Honsen Africa')

    def _toggle_sidebar(self, checked):
        self.sidebar.setFixedWidth(300 if checked else 0)

    # ── 搜索 ─────────────────────────────────────
    def _on_input_change(self, text):
        self._update_carrier_badge(text)

    def _on_carrier_change(self, _index):
        self._update_carrier_badge(self.search_input.text())

    def _update_carrier_badge(self, text):
        no = text.strip().upper()
        manual = self.carrier_select.currentData()
        if manual:
            self.badge.setText(f'手动：{manual[0]}')
            self.badge.setStyleSheet(f"background:rgba(249,115,22,0.08);"
                f"border:1px solid rgba(249,115,22,0.3); color:{ACCENT};"
                f"border-radius:4px; padding:2px 10px; font-size:11px; font-family:'Courier New';")
            self.badge.setVisible(True)
            return
        if len(no) < 4:
            self.badge.setVisible(False); return
        name = carriers.get_carrier_name(no)
        if name and name != '未知承运商':
            self.badge.setText(name)
            self.badge.setStyleSheet(f"background:rgba(56,189,248,0.08);"
                f"border:1px solid rgba(56,189,248,0.3); color:{CYAN};"
                f"border-radius:4px; padding:2px 10px; font-size:11px; font-family:'Courier New';")
        else:
            self.badge.setText('UNKNOWN')
            self.badge.setStyleSheet(f"background:rgba(71,85,105,0.08);"
                f"border:1px solid {DIM}; color:{DIM};"
                f"border-radius:4px; padding:2px 10px; font-size:11px; font-family:'Courier New';")
        self.badge.setVisible(True)

    def _do_track(self):
        try:
            no = carriers.normalize_container_no(self.search_input.text())
        except ValueError as e:
            self._on_error(str(e))
            self.search_input.setFocus()
            return

        carrier_override = self.carrier_select.currentData()
        carrier_name = carrier_override[0] if carrier_override else carriers.get_carrier_name(no)
        if not carrier_override and carrier_name == '未知承运商':
            self._on_error(f'未识别的承运商前缀：{no[:4]}\n请前往官网查询。')
            return

        self.stack.setCurrentIndex(1)
        self.loading_lbl.setText(
            f'⟳ 正在查询 {no} ...\n\n承运商：{carrier_name}\n浏览器将自动打开，请稍候（约10秒）'
        )
        self._set_status(f'⟳ 正在查询 {no}...', CYAN)

        if self._worker and self._worker.isRunning():
            self._worker.terminate(); self._worker.wait()

        self._worker = FetchWorker(no, carrier_override)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.status.connect(lambda s: self._set_status(s, CYAN))
        self._worker.start()

    def _on_result(self, data):
        history.add(data.get('container', ''), data.get('carrier') or carriers.get_carrier_name(data.get('container', '')))
        self._refresh_history()
        self._render_result(data)
        no = data.get('container', '')
        suffix = ' （缓存）' if data.get('_cached') else ''
        self._set_status(f'✔ 查询完成 · {no}{suffix}', GREEN)

    def _on_error(self, msg):
        self.error_lbl.setText(f'⚠ {msg}')
        self.stack.setCurrentIndex(3)
        self._set_status('⚠ 查询失败', RED)

    def _do_clear(self):
        self.search_input.clear(); self.badge.setVisible(False)
        self.stack.setCurrentIndex(0)
        self._set_status('系统就绪 — 等待查询指令', GREEN)

    # ── 结果渲染 ─────────────────────────────────
    def _render_result(self, data):
        while self.result_lay.count() > 1:
            item = self.result_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        no     = data.get('container', '')
        fp     = data.get('from_port', '—')
        tp     = data.get('to_port', '—')
        upd    = data.get('updated', '')
        status = data.get('status', '')
        events = data.get('events', [])
        cached = data.get('_cached', False)
        pos    = self.result_lay.count() - 1

        # 头部
        hdr = QWidget()
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(0,0,0,14); hl.setSpacing(12)
        no_lbl = QLabel(no)
        no_lbl.setStyleSheet(f"color:{ACCENT}; font-family:'Courier New';"
                             f"font-size:20px; font-weight:bold; letter-spacing:3px;")
        hl.addWidget(no_lbl)
        c_lbl = QLabel(data.get('carrier') or carriers.get_carrier_name(no))
        c_lbl.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        hl.addWidget(c_lbl)
        if cached:
            ca = QLabel('💾 缓存')
            ca.setStyleSheet(f"background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.3);"
                             f"color:{CYAN}; border-radius:4px; padding:2px 8px; font-size:10px;")
            hl.addWidget(ca)
        hl.addStretch()
        if upd:
            u = QLabel(upd); u.setStyleSheet(f"color:{DIM}; font-size:11px; font-family:'Courier New';")
            hl.addWidget(u)

        copy_btn = QPushButton('📋 复制'); copy_btn.setObjectName('smallBtn')
        copy_btn.clicked.connect(lambda: (
            QApplication.clipboard().setText(no),
            self._set_status(f'✓ 已复制 {no}', GREEN)
        ))
        hl.addWidget(copy_btn)

        web_btn = QPushButton('↗ 官网'); web_btn.setObjectName('smallBtn')
        web_btn.clicked.connect(lambda: self._open_web(no))
        hl.addWidget(web_btn)

        ref_btn = QPushButton('🔄 强制刷新'); ref_btn.setObjectName('smallBtn')
        ref_btn.clicked.connect(lambda: self._force_refresh(no))
        hl.addWidget(ref_btn)

        self.result_lay.insertWidget(pos, hdr); pos += 1

        div = QFrame(); div.setObjectName('divider')
        div.setFrameShape(QFrame.Shape.HLine); div.setFixedHeight(1)
        self.result_lay.insertWidget(pos, div); pos += 1

        if status:
            st = QLabel(f'📍 {status}')
            st.setStyleSheet(f"color:{CYAN}; font-size:12px; font-family:'Courier New'; padding:8px 0;")
            st.setWordWrap(True)
            self.result_lay.insertWidget(pos, st); pos += 1

        # 路线卡片
        route = QFrame(); route.setObjectName('routeCard')
        rl = QHBoxLayout(route); rl.setContentsMargins(18,14,18,14); rl.setSpacing(10)

        def port_w(name, label):
            w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(3)
            n = QLabel(name); n.setStyleSheet(f"font-size:15px; font-weight:bold; color:{TEXT}; letter-spacing:1px;")
            lb = QLabel(label); lb.setStyleSheet(f"font-size:11px; color:{ACCENT}; font-family:'Courier New';")
            l.addWidget(n); l.addWidget(lb); return w

        rl.addWidget(port_w(fp, '出发港'), 1)
        arr = QLabel('→'); arr.setStyleSheet(f"color:{DIM}; font-size:22px;")
        arr.setAlignment(Qt.AlignmentFlag.AlignCenter); rl.addWidget(arr)
        rl.addWidget(port_w(tp, '目的港'), 1)
        self.result_lay.insertWidget(pos, route); pos += 1

        sp = QWidget(); sp.setFixedHeight(16)
        self.result_lay.insertWidget(pos, sp); pos += 1

        tl = QLabel('📍 运踪记录')
        tl.setStyleSheet(f"color:{DIM}; font-size:10px; letter-spacing:2px;"
                         f"font-family:'Courier New'; padding-bottom:8px;")
        self.result_lay.insertWidget(pos, tl); pos += 1

        for i, ev in enumerate(events):
            ms  = ev.get('milestone', '')
            loc = ev.get('loc', '')
            p   = ms.split('\n', 1)
            evname = p[0]; evtime = p[1] if len(p) > 1 else ''
            is_last = (i == len(events) - 1)

            row = QWidget()
            rl2 = QHBoxLayout(row); rl2.setContentsMargins(0,0,0,0); rl2.setSpacing(14)

            dc_w = QWidget(); dc_w.setFixedWidth(24)
            dc = QVBoxLayout(dc_w); dc.setContentsMargins(0,4,0,0); dc.setSpacing(0)
            dot = QLabel('●')
            dot.setStyleSheet(f"color:{ACCENT if is_last else GREEN}; font-size:9px;")
            dot.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            dc.addWidget(dot)
            if not is_last:
                line = QLabel(); line.setFixedWidth(1); line.setMinimumHeight(18)
                line.setStyleSheet(f"background:{BORDER};")
                dc.addWidget(line, 1, Qt.AlignmentFlag.AlignHCenter)
            rl2.addWidget(dc_w)

            content = QWidget()
            cl = QVBoxLayout(content); cl.setContentsMargins(0,0,0,10); cl.setSpacing(2)
            tr = QHBoxLayout()
            nl = QLabel(evname); nl.setStyleSheet(f"font-size:12px; font-weight:bold; color:{TEXT};")
            tr.addWidget(nl); tr.addStretch()
            if evtime:
                tl2 = QLabel(evtime)
                tl2.setStyleSheet(f"font-size:10px; color:{DIM}; font-family:'Courier New';")
                tr.addWidget(tl2)
            cl.addLayout(tr)
            if loc:
                ll = QLabel(f'📍 {loc.replace(chr(10), " · ")}')
                ll.setStyleSheet(f"font-size:11px; color:{MUTED};")
                cl.addWidget(ll)
            rl2.addWidget(content, 1)
            self.result_lay.insertWidget(pos, row); pos += 1

        self.stack.setCurrentIndex(2)

    def _open_web(self, no):
        import webbrowser
        webbrowser.open(carriers.get_tracking_url(no) or 'https://www.google.com/search?q=' + no)

    def _force_refresh(self, no):
        cache.delete(no); self.search_input.setText(no); self._do_track()

    # ── 历史记录 ─────────────────────────────────
    def _refresh_history(self):
        while self.hist_layout.count() > 1:
            item = self.hist_layout.takeAt(0)
            w = item.widget()
            if w:
                # 明确断开所有信号再销毁
                try: w.trackReq.disconnect()
                except: pass
                try: w.deleteReq.disconnect()
                except: pass
                try: w.editReq.disconnect()
                except: pass
                w.setParent(None)
                w.deleteLater()

        arr = history.load()
        if not arr:
            empty = QLabel('📭\n\n暂无历史记录\n查询后自动保存')
            empty.setStyleSheet(f"color:{DIM}; font-size:11px; font-family:'Courier New';")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.hist_layout.insertWidget(0, empty)
            return

        for h in arr:
            item = HistItem(h)
            item.trackReq.connect(self._on_hist_track)
            item.deleteReq.connect(self._on_hist_delete)
            item.editReq.connect(self._on_hist_edit)
            self.hist_layout.insertWidget(self.hist_layout.count() - 1, item)

    def _on_hist_track(self, no):
        self.search_input.setText(no); self._do_track()

    def _on_hist_delete(self, hid):
        history.delete(hid)
        self._refresh_history()

    def _on_hist_edit(self, hid, no, note):
        dlg = NoteDialog(no, note, self)
        dlg.setStyleSheet(QSS)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            history.update_note(hid, dlg.get_note())
            self._refresh_history()

    def _clear_history(self):
        reply = QMessageBox.question(self, '确认', '确定清空所有查询历史？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            history.clear(); self._refresh_history()


# ── 入口 ─────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Honsen Africa · Container Tracker')
    app.setStyle('Fusion')

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(PANEL))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(PANEL2))
    pal.setColor(QPalette.ColorRole.Text,            QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(PANEL))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
    app.setPalette(pal)
    app.setStyleSheet(QSS)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
