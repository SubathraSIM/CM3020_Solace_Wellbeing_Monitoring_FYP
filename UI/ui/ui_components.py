# Import required libraries
import os
import math
from pathlib import Path
from PySide6.QtCore import Qt,QRectF,QPoint,QPropertyAnimation,QParallelAnimationGroup,QEasingCurve,QTimer,QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QWidget, QScrollArea, QFrame, QGraphicsOpacityEffect

# images folder
IMAGES = Path(__file__).resolve().parents[1] / 'images'

# Load the first available image
def _load_pixmap(*names):
    # available image filenames in order
    for name in names:
        path = IMAGES / name
        if path.exists():
            pixmap = QPixmap(str(path))
            # Check the image loaded successfully
            if not pixmap.isNull():
                return pixmap
    return QPixmap()


# garden image with rounded left corners
class GardenArtwork(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Try both spellings of the garden image filename
        self.pixmap = _load_pixmap('quite_garden.png')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setMinimumSize(0, 0)

    # garden artwork inside its rounded border
    def paintEvent(self, event):
        # skip drawing if the image could not be loaded
        if self.pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        radius = 16
        rect = QRectF(self.rect())
        # Build outline with rounded corners on the left
        path = QPainterPath()
        path.moveTo(rect.right(), rect.top())
        path.lineTo(rect.left() + radius, rect.top())
        path.quadTo(rect.left(), rect.top(), rect.left(), rect.top() + radius)
        path.lineTo(rect.left(), rect.bottom() - radius)
        path.quadTo(rect.left(), rect.bottom(), rect.left() + radius, rect.bottom())
        path.lineTo(rect.right(), rect.bottom())
        path.closeSubpath()

        # artwork to the rounded outline
        painter.setClipPath(path)

        # Scale and centre the image without stretching it
        scaled = self.pixmap.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation,)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


# content in a scrollable area
def scroll_page(content):
    # borderless scroll area that resizes with its contents
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(content)
    return scroll


# Fade the widget into view
def reveal(widget):
    # Skip animation when reduced motion is enabled
    if os.environ.get('SOLACE_REDUCED_MOTION') == '1':
        return
    # Stop and release any previous fade animation
    old = getattr(widget, "_reveal_animation", None)
    if old is not None:
        old.stop()
        old.deleteLater()
    # Apply opacity effect for fade
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    # Fade from partly transparent to fully visible
    animation = QPropertyAnimation(effect, b'opacity', widget)
    animation.setDuration(340)
    animation.setStartValue(0.3)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.OutCubic)

    # Keep animation alive on the widget
    widget._reveal_animation = animation
    animation.start()

# Fade and slide the widget into place
def float_in(widget, rise=28, duration=560):
    # skip animation when reduced motion is enabled
    if os.environ.get('SOLACE_REDUCED_MOTION') == '1':
        return

    # Stop any earlier slide and fade animation
    old = getattr(widget, "_float_group", None)
    if old is not None:
        old.stop()

    # effect and widget
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    # Prepare the fade from invisible to fully visible
    fade = QPropertyAnimation(effect, b'opacity', widget)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.OutCubic)

    # final position before preparing the slide
    pos = widget.pos()

    # Slide the widget upward to its original position
    slide = QPropertyAnimation(widget, b'pos', widget)
    slide.setDuration(duration)
    slide.setStartValue(QPoint(pos.x(), pos.y() + rise))
    slide.setEndValue(pos)
    slide.setEasingCurve(QEasingCurve.OutCubic)

    # Run the fade and slide together and keep the group alive
    group = QParallelAnimationGroup(widget)
    group.addAnimation(fade)
    group.addAnimation(slide)
    widget._float_group = group
    group.start()

# Add shadow and entrance animation around a card
class FloatCard(QWidget):
    # leave room around the card for its shadow
    PAD = 44

    def __init__(self, card, rise=34, parent=None):
        super().__init__(parent)
        self._card = card
        self._rise = rise
        self._radius = 16
        card.setParent(self)

        # Make room around the card for the shadow
        self.setFixedSize(card.width() + self.PAD * 2,card.height() + self.PAD * 2)

        # Place card inside the space reserved for its shadow
        self._rest = QPoint(self.PAD, self.PAD)
        card.move(self._rest)

        # Apply one opacity effect to animated card wrapper
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)

    # soft shadow behind the card
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        # x,y,width and height
        x = self._rest.x()
        y = self._rest.y()
        w = self._card.width()
        h = self._card.height()

        # soft shadow using several transparent layers
        layers = 16

        # bias the shadow downward
        drop = 2

        # draw the outer shadow layers before the inner ones
        for i in range(layers, 0, -1):
            spread = i * 2
            # outer shadow layers more transparent
            alpha = int(12 * (1 - i / layers) ** 2)
            if alpha <= 0:
                continue
            painter.setBrush(QColor(26, 44, 77, alpha))
            # Expand each rounded layer around the card
            rect = QRectF(x - spread,y - spread + drop,w + spread * 2,h + spread * 2,)
            painter.drawRoundedRect(rect, self._radius + spread, self._radius + spread)

    # card entrance animation
    def play(self):
        # Skip animation when reduced motion is enabled
        if os.environ.get('SOLACE_REDUCED_MOTION') == '1':
            return

        # previous entrance animation before starting another
        old = getattr(self, '_entrance', None)
        if old is not None:
            old.stop()

        # card below its resting point and hide it
        start = QPoint(self._rest.x(), self._rest.y() + self._rise)
        self._card.move(start)
        self._opacity.setOpacity(0.0)

        # fade into view
        fade = QPropertyAnimation(self._opacity, b'opacity', self)
        fade.setDuration(560)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        # upward slide to the resting position
        slide = QPropertyAnimation(self._card, b'pos', self)
        slide.setDuration(560)
        slide.setStartValue(start)
        slide.setEndValue(self._rest)
        slide.setEasingCurve(QEasingCurve.OutCubic)

        # animations together and keep the group alive
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        self._entrance = group
        group.start()

# illustration with animation
class AnimatedIllustration(QWidget):
    def __init__(self, filename, parent=None, fit=False):
        super().__init__(parent)
        # chosen illustration
        self.pixmap = _load_pixmap(filename)
        self._fit = fit
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # elapsed time for animation
        self._clock = QElapsedTimer()
        self._clock.start()

        # timer that can request regular redraws
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self.update)

        # Remember whether reduced motion is enabled
        self._reduced = os.environ.get('SOLACE_REDUCED_MOTION') == '1'

    # show event
    def showEvent(self, event):
        super().showEvent(event)

    # widget being hidden
    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    # illustration at its current size and position
    def paintEvent(self, event):
        # Skip drawing when the illustration is missing
        if self.pixmap.isNull():
            return

        # painter render hint
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        pw = self.pixmap.width()
        ph = self.pixmap.height()

        # avoid dividing by empty image size
        if pw == 0 or ph == 0:
            return

        # gentle movement
        phase = 0 if self._reduced else math.sin(self._clock.elapsed() / 1500.0)

        # scale that fits or fills available space
        base = min(self.width() / pw, self.height() / ph) if self._fit \
            else max(self.width() / pw, self.height() / ph)
        
        # gentle scaling movement to image dimensions
        scale = base * (1 + phase * 0.012)
        w = pw * scale
        h = ph * scale

        # Centre image and add small vertical movement
        x = (self.width() - w) / 2
        y = (self.height() - h) / 2 - phase * 1.3
        painter.drawPixmap(QRectF(x, y, w, h), self.pixmap, QRectF(0, 0, pw, ph))