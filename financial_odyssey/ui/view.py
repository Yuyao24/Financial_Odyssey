"""Scales the fixed-size canvas uniformly into the window, with black bars."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QTransform
from PyQt6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

from .theme import AL_C


class ScaledView(QGraphicsView):
    """Uniformly scales the fixed canvas into any window, centred; leftover space shows as bars."""

    def __init__(self, root, cw, ch):
        super().__init__()
        self.cw, self.ch = cw, ch
        self.scene_ = QGraphicsScene(self)
        self.proxy = self.scene_.addWidget(root)
        self.setScene(self.scene_)
        self.setSceneRect(0, 0, cw, ch)
        self._setup()

    def set_root(self, root, cw, ch):
        """Replace the canvas without recreating the view, so nothing flashes black."""
        self.setUpdatesEnabled(False)
        old = self.scene_
        self.cw, self.ch = cw, ch
        self.scene_ = QGraphicsScene(self)
        self.proxy = self.scene_.addWidget(root)
        self.setScene(self.scene_)
        self.setSceneRect(0, 0, cw, ch)
        self._fit()
        self.setUpdatesEnabled(True)
        old.deleteLater()                     # deletes the old UI with it

    def _setup(self):
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(QColor(0, 0, 0)))
        self.setAlignment(AL_C)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        vp = self.viewport()
        if vp is None or vp.width() <= 0 or vp.height() <= 0:
            return
        s = min(vp.width() / self.cw, vp.height() / self.ch)
        self.setTransform(QTransform.fromScale(s, s))
        self.centerOn(self.cw / 2, self.ch / 2)

    def wheelEvent(self, e):
        if self.itemAt(e.position().toPoint()) is not None:
            super().wheelEvent(e)
