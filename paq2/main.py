import sys
import os
import cv2
import numpy as np
import json
import ctypes
import librosa

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QSlider, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QUrl
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QPainter, QPainterPath, QFontDatabase, QRegion, QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

try:
    myappid = 'mycompany.p_aq2_player.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

TRACKS_FOLDER = get_resource_path("tracks")
COVERS_FOLDER = get_resource_path("covers")
METADATA_FOLDER = get_resource_path("metadata")
BACKGROUND_VIDEO = get_resource_path("background.mp4")
FONT_PATH = get_resource_path("GhastlyPanicCyr.otf")
APP_ICON = get_resource_path("main.ico")

WIN_W = 1350
WIN_H = 650
ROUND_RADIUS = 12

class AnalysisThread(QThread):
    analysis_finished = pyqtSignal(np.ndarray)
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
    def run(self):
        try:
            y, sr = librosa.load(self.file_path, sr=22050)
            rms = librosa.feature.rms(y=y)[0]
            rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)
            speed_map = 0.7 + (rms_norm * 1.8) 
            self.analysis_finished.emit(speed_map)
        except Exception as e:
            print(f"Ошибка анализа: {e}")

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stopped = False
        self.speed_map = None
        self.current_speed = 1.0
        self.parent_player = None

    def run(self):
        if not os.path.exists(BACKGROUND_VIDEO): return
        cap = cv2.VideoCapture(BACKGROUND_VIDEO)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        base_interval = int(1000 / fps)
        
        while not self.stopped:
            if self.parent_player and self.parent_player.state() == QMediaPlayer.PausedState:
                self.msleep(30)
                continue
            
            if self.speed_map is not None and self.parent_player:
                idx = int((self.parent_player.position() / 1000.0 * 22050) / 512)
                self.current_speed = self.speed_map[idx] if idx < len(self.speed_map) else 1.0

            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (WIN_W, WIN_H))
            frame = cv2.GaussianBlur(frame, (11, 11), 0)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            dark = (rgb * 0.45).astype(np.uint8)
            
            qt_img = QImage(dark.data, WIN_W, WIN_H, 3 * WIN_W, QImage.Format_RGB888)
            self.change_pixmap_signal.emit(qt_img)
            
            sleep_time = max(int(base_interval / self.current_speed), 5)
            self.msleep(sleep_time)
        cap.release()

class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(WIN_W, WIN_H)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(APP_ICON))
        self.setWindowTitle("p||aq2")

        self.old_pos = QPoint()
        
        if os.path.exists(FONT_PATH):
            font_id = QFontDatabase.addApplicationFont(FONT_PATH)
            self.custom_font = QFontDatabase.applicationFontFamilies(font_id)[0] if font_id != -1 else "Impact"
        else:
            self.custom_font = "Impact"

        self.background_label = QLabel(self)
        self.background_label.setGeometry(0, 0, WIN_W, WIN_H)
        self.setup_background_mask()

        self.player = QMediaPlayer()
        self.video_thread = VideoThread(self)
        self.video_thread.parent_player = self.player
        self.video_thread.change_pixmap_signal.connect(self.update_video_frame)
        self.video_thread.start()

        self.tracks = []
        self.current = 0
        self.playing = False

        self.setup_ui()
        self.load_tracks_list()

        self.player.positionChanged.connect(self.pos_changed)
        self.player.durationChanged.connect(self.dur_changed)
        self.player.mediaStatusChanged.connect(self.status_changed)

    def setup_background_mask(self):
        path = QPainterPath()
        path.addRoundedRect(0, 0, WIN_W, WIN_H, ROUND_RADIUS, ROUND_RADIUS)
        self.background_label.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def update_video_frame(self, img):
        self.background_label.setPixmap(QPixmap.fromImage(img))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, WIN_W, WIN_H, ROUND_RADIUS, ROUND_RADIUS)
        p.fillPath(path, QColor(10, 10, 10, 210))

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 15, 15, 0)
        top_bar.addStretch()
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(45, 45)
        self.btn_close.setStyleSheet("QPushButton { background: transparent; color: white; font-size: 40px; border: none; } QPushButton:hover { color: #ff5555; }")
        self.btn_close.clicked.connect(self.close)
        top_bar.addWidget(self.btn_close)
        self.root_layout.addLayout(top_bar)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(80, 0, 80, 60)

        self.left_widget = QWidget()
        left_vbox = QVBoxLayout(self.left_widget)
        self.cover = QLabel()
        self.cover.setFixedSize(380, 380)
        self.cover.setStyleSheet(f"background: rgba(255,255,255,10); border-radius: {ROUND_RADIUS}px;")
        
        self.title = QLabel("LOADING...")
        self.title.setFont(QFont(self.custom_font, 42, QFont.Bold))
        self.title.setStyleSheet("color: white; background: transparent;")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFixedWidth(400)
        self.title.setWordWrap(True)

        left_vbox.addStretch()
        left_vbox.addWidget(self.cover, alignment=Qt.AlignCenter)
        left_vbox.addSpacing(20)
        left_vbox.addWidget(self.title, alignment=Qt.AlignCenter)
        left_vbox.addStretch()

        self.right_widget = QWidget()
        self.right_widget.setFixedWidth(550)
        right_vbox = QVBoxLayout(self.right_widget)
        
        self.time_curr = QLabel("0:00")
        self.time_total = QLabel("0:00")
        t_style = "color: white; font-family: 'Arial'; font-size: 15px; font-weight: bold;"
        self.time_curr.setStyleSheet(t_style)
        self.time_total.setStyleSheet(t_style)

        time_info = QHBoxLayout()
        time_info.addWidget(self.time_curr)
        time_info.addStretch()
        time_info.addWidget(self.time_total)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 5px; background: rgba(255,255,255,40); border-radius: 2px; }
            QSlider::handle:horizontal { background: white; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }
            QSlider::sub-page:horizontal { background: white; }
        """)
        self.slider.sliderMoved.connect(self.seek)

        btns = QHBoxLayout()
        self.btn_prev = QPushButton("«")
        self.btn_play = QPushButton("▶")
        self.btn_next = QPushButton("»")
        btn_style = "QPushButton { background: transparent; color: white; font-size: 60px; font-family: 'Arial'; } QPushButton:hover { color: #ccc; }"
        for b in [self.btn_prev, self.btn_play, self.btn_next]:
            b.setFixedSize(120, 120)
            b.setStyleSheet(btn_style)
            b.setCursor(Qt.PointingHandCursor)
        
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_prev.clicked.connect(self.prev_track)
        self.btn_next.clicked.connect(self.next_track)

        btns.addStretch()
        btns.addWidget(self.btn_prev)
        btns.addSpacing(30)
        btns.addWidget(self.btn_play)
        btns.addSpacing(30)
        btns.addWidget(self.btn_next)
        btns.addStretch()

        right_vbox.addStretch()
        right_vbox.addLayout(time_info)
        right_vbox.addWidget(self.slider)
        right_vbox.addSpacing(50)
        right_vbox.addLayout(btns)
        right_vbox.addStretch()

        content_layout.addWidget(self.left_widget)
        content_layout.addStretch()
        content_layout.addWidget(self.right_widget)
        
        self.root_layout.addLayout(content_layout)

    def load_track(self, path):
        self.video_thread.speed_map = None
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(os.path.abspath(path))))

        self.worker = AnalysisThread(path)
        self.worker.analysis_finished.connect(self.set_speed_data)
        self.worker.start()

        filename = os.path.splitext(os.path.basename(path))[0]
        self.title.setText(filename.upper())
        self.load_cover(filename)
        if self.playing:
            self.player.play()

    def set_speed_data(self, data):
        self.video_thread.speed_map = data

    def load_cover(self, name):
        cover_path = None
        for ext in ['.jpg', '.png', '.jpeg']:
            p = os.path.join(COVERS_FOLDER, name + ext)
            if os.path.exists(p):
                cover_path = p
                break
        if cover_path:
            pixmap = QPixmap(cover_path).scaled(380, 380, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.cover.setPixmap(pixmap)
        else:
            self.cover.clear()

    def toggle_play(self):
        if not self.tracks: return
        if self.playing:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("||")
        self.playing = not self.playing

    def prev_track(self):
        if not self.tracks: return
        self.current = (self.current - 1 + len(self.tracks)) % len(self.tracks)
        self.load_track(self.tracks[self.current])

    def next_track(self):
        if not self.tracks: return
        self.current = (self.current + 1) % len(self.tracks)
        self.load_track(self.tracks[self.current])

    def status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.next_track()

    def seek(self, position):
        self.player.setPosition(position)

    def pos_changed(self, p):
        if not self.slider.isSliderDown():
            self.slider.setValue(p)
        self.time_curr.setText(f"{p//60000}:{(p%60000)//1000:02d}")

    def dur_changed(self, d):
        self.slider.setRange(0, d)
        self.time_total.setText(f"{d//60000}:{(d%60000)//1000:02d}")

    def load_tracks_list(self):
        if os.path.exists(TRACKS_FOLDER):
            self.tracks = sorted([os.path.join(TRACKS_FOLDER, f) for f in os.listdir(TRACKS_FOLDER) if f.lower().endswith(('.mp3', '.wav'))])
            if self.tracks:
                self.load_track(self.tracks[0])

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.old_pos = e.globalPos()
    def mouseMoveEvent(self, e):
        if not self.old_pos.isNull():
            delta = QPoint(e.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = e.globalPos()
    def mouseReleaseEvent(self, e):
        self.old_pos = QPoint()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec_())
