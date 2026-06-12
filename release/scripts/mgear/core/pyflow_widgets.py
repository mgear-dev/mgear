##############################################################################
# NOTE:
# this files is a modification/combination of some files from pyflow project
# https://github.com/wonderworks-software/PyFlow
##############################################################################


# Copyright 2015-2019 Ilgar Lunin, Pedro Cabrera

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from copy import copy
import struct

from mgear.vendor.Qt import QtGui, QtCore, QtWidgets, QtCompat


FLOAT_SLIDER_DRAG_STEPS = [100.0, 10.0, 1.0, 0.1, 0.01, 0.001]
INT_SLIDER_DRAG_STEPS = [100.0, 10.0, 1.0]

maxint = 2 ** (struct.Struct("i").size * 8 - 1) - 1

FLOAT_RANGE_MIN = 0.1 + (-maxint - 1.0)
FLOAT_RANGE_MAX = maxint + 0.1
INT_RANGE_MIN = -maxint + 0
INT_RANGE_MAX = maxint + 0

MainColor = QtGui.QColor(60, 60, 60)

ATTR_SLIDER_TYPES = ["int", "float", "double", "doubleLinear", "doubleAngle"]


class Colors:
    AbsoluteBlack = QtGui.QColor(0, 0, 0, 255)
    DarkGray = QtGui.QColor(60, 60, 60)
    DirtyPen = QtGui.QColor(250, 250, 250, 200)
    Gray = QtGui.QColor(110, 110, 110)
    Green = QtGui.QColor(96, 169, 23, 255)
    NodeBackgrounds = QtGui.QColor(40, 40, 40, 200)
    NodeNameRectBlue = QtGui.QColor(28, 74, 149, 200)
    NodeNameRectGreen = QtGui.QColor(74, 124, 39, 200)
    NodeSelectedPenColor = QtGui.QColor(200, 200, 200, 150)
    Red = QtGui.QColor(255, 0, 0, 255)
    White = QtGui.QColor(255, 255, 255, 200)
    Yellow = QtGui.QColor(255, 211, 25)
    Orange = QtGui.QColor(209, 84, 0)


def getSliderStyleSheet(name):

    Styles = {
        "sliderStyleSheetA": """
        QWidget{
            border: 1.25 solid black;
        }
        QSlider::groove:horizontal,
            QSlider::sub-page:horizontal {
            background: %s;
        }
        QSlider::add-page:horizontal,
            QSlider::sub-page:horizontal:disabled {
            background: rgb(32, 32, 32);
        }
        QSlider::add-page:horizontal:disabled {
            background: grey;
        }
        QSlider::handle:horizontal {
            width: 1px;
         }
        """
        % "rgba%s"
        % str(MainColor.getRgb()),
        "sliderStyleSheetB": """
        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: white;
            height: 3px;
            border-radius: 2px;
        }
        QSlider::sub-page:horizontal {
            background: %s;
            border: 0px solid #777;
            height: 3px;
            border-radius: 2px;
        }
        QSlider::add-page:horizontal {
            background: #fff;
            border: 1px solid #777;
            height: 3px;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #eee, stop:1 #ccc);
            border: 1px solid #777;
            width: 4px;
            margin-top: -8px;
            margin-bottom: -8px;
            border-radius: 2px;
            height : 10px;
        }
        QSlider::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #fff, stop:1 #ddd);
            border: 1px solid #444;
            border-radius: 2px;
        }
        QSlider::sub-page:horizontal:disabled {
            background: #bbb;
            border-color: #999;
        }

        QSlider::add-page:horizontal:disabled {
            background: #eee;
            border-color: #999;
        }
        QSlider::handle:horizontal:disabled {
            background: #eee;
            border: 1px solid #aaa;
            border-radius: 2px;
            height : 10;
        }
        """
        % "rgba%s"
        % str(MainColor.getRgb()),
        "sliderStyleSheetC": """
        QSlider,QSlider:disabled,QSlider:focus{
                                  background: qcolor(0,0,0,0);   }

         QSlider::groove:horizontal {
            border: 1px solid #999999;
            background: qcolor(0,0,0,0);
         }
        QSlider::handle:horizontal {
            background:  rgba(255, 255, 255, 150);
            width: 10px;
            border-radius: 4px;
            border: 1.5px solid black;
         }
         QSlider::handle:horizontal:hover {
            border: 2.25px solid %s;
         }
        """
        % "rgba%s"
        % str(MainColor.getRgb()),
        "draggerstyleSheet": """
        QGroupBox{
            border: 0.5 solid darkgrey;
            background : black;
            color: white;
        }
        QLabel{
            background: transparent;
            border: 0 solid transparent;
            color: white;
        }
        """,
        "draggerstyleSheetHover": """
        QGroupBox{
            border: 0.5 solid darkgrey;
            background : %s;
            color: white;
        }
        QLabel{
            background: transparent;
            border: 0 solid transparent;
            color: white;
        }
        """
        % "rgba%s"
        % str(MainColor.getRgb()),
        "timeStyleSheet": """
        QSlider,QSlider:disabled,QSlider:focus{
                                  background: qcolor(0,0,0,0);   }
         QSlider::groove:horizontal {
            border: 1px solid #999999;
            background: qcolor(0,0,0,0);
         }
        QSlider::handle:horizontal {
            background:  %s;
            width: 3px;
         }
        """
        % "rgba%s"
        % str(MainColor.getRgb()),
    }
    return Styles[name]


#########################################
# Helper functions
#########################################


def lerp(start, end, alpha):
    """Performs a linear interpolation

    >>> start + alpha * (end - start)

    :param start: start the value to interpolate from
    :param end: end the value to interpolate to
    :param alpha: alpha how far to interpolate
    :returns: The result of the linear interpolation
    """
    return start + alpha * (end - start)


def clamp(n, vmin, vmax):
    """Computes the value of the first specified argument clamped to a range
    defined by the second and third specified arguments

    :param n: input Value
    :param vmin: MiniMum Value
    :param vmax: Maximum Value
    :returns: The clamped value of n
    """
    return max(min(n, vmax), vmin)


def GetRangePct(MinValue, MaxValue, Value):
    """Calculates the percentage along a line from **MinValue** to
    **MaxValue** that value is.

    :param MinValue: Minimum Value
    :param MaxValue: Maximum Value
    :param Value: Input value
    :returns: The percentage (from 0.0 to 1.0) betwen the two values where
                input value is
    """
    return (Value - MinValue) / (MaxValue - MinValue)


def mapRangeClamped(Value, InRangeA, InRangeB, OutRangeA, OutRangeB):
    """Returns Value mapped from one range into another where the Value is
    clamped to the Input Range.
    (e.g. 0.5 normalized from the range 0->1 to 0->50 would result in 25)
    """

    ClampedPct = clamp(GetRangePct(InRangeA, InRangeB, Value), 0.0, 1.0)
    return lerp(OutRangeA, OutRangeB, ClampedPct)


def mapRangeUnclamped(Value, InRangeA, InRangeB, OutRangeA, OutRangeB):
    """Returns Value mapped from one range into another where the Value is
    clamped to the Input Range.
    (e.g. 0.5 normalized from the range 0->1 to 0->50 would result in 25)"""
    return lerp(OutRangeA, OutRangeB, GetRangePct(InRangeA, InRangeB, Value))


#########################################
# Widgets
#########################################
class inputDragger(QtWidgets.QWidget):
    """Custom Widget to drag values when midClick over field type input widget,
    Right Drag increments value, Left Drag decreases Value

    Signals:
        :valueChanged: Signal Emitted when value has change (float)
    """

    def __init__(self, parent, factor, *args, **kwargs):
        """
        :param parent: parent Widget
        :type parent: QtWidget
        :param factor: amount to increment the value
        :type factor: float/int
        """
        super(inputDragger, self).__init__(*args, **kwargs)
        self.parent = parent
        self.setLayout(QtWidgets.QVBoxLayout())
        self.frame = QtWidgets.QGroupBox()
        self.frame.setLayout(QtWidgets.QVBoxLayout())
        self.label = QtWidgets.QLabel("+" + str(factor))
        self.frame.setContentsMargins(0, 0, 0, 0)
        self.frame.layout().setContentsMargins(0, 0, 0, 0)
        self.frame.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        font = self.label.font()
        font.setPointSize(7)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.frame.layout().addWidget(self.label)
        self.layout().addWidget(self.frame)
        self.setStyleSheet(getSliderStyleSheet("draggerstyleSheet"))
        self.size = 35
        self.setMinimumHeight(self.size)
        self.setMinimumWidth(self.size)
        self.setMaximumHeight(self.size)
        self.setMaximumWidth(self.size)
        self._factor = factor
        self.setAttribute(QtCore.Qt.WA_Hover)
        self.installEventFilter(self)
        self.label.installEventFilter(self)

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.HoverEnter:
            self.setStyleSheet(getSliderStyleSheet("draggerstyleSheetHover"))
            self.parent.activeDrag = self
            for drag in self.parent.drags:
                if drag != self:
                    drag.setStyleSheet(
                        getSliderStyleSheet("draggerstyleSheet")
                    )
        if event.type() == QtCore.QEvent.HoverLeave:
            if event.pos().y() > self.height() or event.pos().y() < 0:
                self.setStyleSheet(getSliderStyleSheet("draggerstyleSheet"))

        if event.type() == QtCore.QEvent.MouseMove:
            self.parent.eventFilter(self, event)

        return False


class draggers(QtWidgets.QWidget):
    """PopUp Draggers Houdini Style

    Custom Widget that holds a bunch of :obj:`inputDragger` to drag values
    when midClick over field type input widget, Right Drag increments value,
    Left Drag decreases Value
    """

    increment = QtCore.Signal(object)

    def __init__(
        self, parent=None, isFloat=True, draggerSteps=FLOAT_SLIDER_DRAG_STEPS
    ):
        super(draggers, self).__init__(parent)
        self.initialPos = None
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setWindowFlags(QtCore.Qt.Popup)
        self.activeDrag = None
        self.lastDeltaX = 0
        self.drags = []
        steps = copy(draggerSteps)
        if not isFloat:
            # if int, cut steps less than 1.0
            steps = list([x for x in steps if abs(x) >= 1.0])
        for i in steps:
            drag = inputDragger(self, i)
            self.drags.append(drag)
            self.layout().addWidget(drag)
        self.installEventFilter(self)

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.MouseMove:
            if self.activeDrag:
                modifiers = event.modifiers()
                self.activeDrag.setStyleSheet(
                    getSliderStyleSheet("draggerstyleSheetHover")
                )
                if self.initialPos is None:
                    self.initialPos = event.globalPos()
                deltaX = event.globalPos().x() - self.initialPos.x()
                self._changeDirection = clamp(
                    deltaX - self.lastDeltaX, -1.0, 1.0
                )

                if self._changeDirection != 0:
                    v = self._changeDirection * self.activeDrag._factor

                    if modifiers == QtCore.Qt.NoModifier and deltaX % 4 == 0:
                        self.increment.emit(v)
                    modif = [
                        QtCore.Qt.ShiftModifier,
                        QtCore.Qt.ControlModifier,
                    ]
                    if modifiers in modif and deltaX % 8 == 0:
                        self.increment.emit(v)
                    modif = QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier
                    if modifiers == modif and deltaX % 32 == 0:
                        self.increment.emit(v)

                self.lastDeltaX = deltaX

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            self.hide()
            self.lastDeltaX = 0
            del self
        return False


class slider(QtWidgets.QSlider):
    """Customized Int QSlider

    Re implements QSlider adding a few enhancements

    Modifiers:
        :Left/Mid:  Click to move handle
        :Ctrl:  and drag to move handle half velocity
        :Shift:  and drag to move handle quarter velocity
        :Ctrl+Shift:  and drag to move handle eighth velocity

    Extends:
        QtWidgets.QSlider
    """

    editingFinished = QtCore.Signal()
    editingStart = QtCore.Signal()
    valueIncremented = QtCore.Signal(object)
    floatValueChanged = QtCore.Signal(object)

    def __init__(
        self,
        custom_signals,
        parent=None,
        draggerSteps=INT_SLIDER_DRAG_STEPS,
        sliderRange=[-100, 100],
        *args,
        **kwargs
    ):
        super(slider, self).__init__(parent, **kwargs)
        self.sliderRange = sliderRange
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setOrientation(QtCore.Qt.Horizontal)
        self.draggerSteps = draggerSteps
        self.isFloat = False
        self.deltaValue = 0
        self.startDragpos = QtCore.QPointF()
        self.realStartDragpos = QtCore.QPointF()
        self.LeftButton = QtCore.Qt.LeftButton

        # Try importing PySide6, fall back to PySide2 if not available
        try:
            MiddleButton = QtCompat.Qt.MidButton
        except ImportError:
            MiddleButton = QtCore.Qt.MidButton

        self.MidButton = MiddleButton
        self.draggers = None
        self._click_offset = 0
        self._prev_x = 0
        self.custom_signals = custom_signals

        self.setRange(self.sliderRange[0], self.sliderRange[1])

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.sliderMoved.emit(self.value())  # emit signal with new value
        self.editingFinished.emit()
        # if self.parent():
        #     self.parent().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        self.editingStart.emit()
        if self.parent():
            self.parent().mousePressEvent(event)
        self.prevValue = self.value()
        self.startDragpos = event.pos()

        emodif = event.modifiers()
        modif = [QtCore.Qt.ControlModifier, QtCore.Qt.ShiftModifier]

        if event.button() == self.MidButton:
            if self.draggers is None:
                self.draggers = draggers(
                    self, self.isFloat, draggerSteps=self.draggerSteps
                )
                self.draggers.increment.connect(self.valueIncremented.emit)
            self.draggers.show()
            if self.isFloat:
                self.draggers.move(
                    self.mapToGlobal(
                        QtCore.QPoint(
                            event.pos().x() - 1,
                            event.pos().y() - self.draggers.height() / 2,
                        )
                    )
                )
            else:
                self.draggers.move(
                    self.mapToGlobal(
                        QtCore.QPoint(
                            event.pos().x() - 1,
                            event.pos().y()
                            - (
                                self.draggers.height()
                                - self.draggers.height() / 6
                            ),
                        )
                    )
                )

        elif (
            event.button() == self.LeftButton
            and emodif == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
        ):
            butts = QtCore.Qt.MouseButtons(self.LeftButton)
            nevent = QtGui.QMouseEvent(
                event.type(),
                event.pos(),
                self.LeftButton,
                butts,
                event.modifiers(),
            )
            super(slider, self).mousePressEvent(nevent)

        elif event.button() == self.LeftButton or emodif in modif:
            opt = QtWidgets.QStyleOptionSlider()
            opt.initFrom(self)
            opt.subControls = QtWidgets.QStyle.SC_None
            opt.activeSubControls = QtWidgets.QStyle.SC_None
            opt.orientation = self.orientation()
            opt.maximum = self.maximum()
            opt.minimum = self.minimum()
            opt.pageStep = self.pageStep()
            opt.sliderPosition = self.sliderPosition()
            opt.sliderValue = self.value()

            hit = self.style().hitTestComplexControl(
                QtWidgets.QStyle.CC_Slider, opt, event.pos(), self
            )
            if hit == QtWidgets.QStyle.SC_SliderHandle:
                super(slider, self).mousePressEvent(event)
                self._click_offset = (
                    event.pos().x()
                    - self.style().sliderPositionFromValue(
                        self.minimum(),
                        self.maximum(),
                        self.value(),
                        self.width() - 16,
                    )
                )
            else:
                slider_handle_pos = self.style().sliderPositionFromValue(
                    self.minimum(),
                    self.maximum(),
                    self.value(),
                    self.width() - 16,
                )
                self._click_offset = event.pos().x() - slider_handle_pos
                self.mouseMoveEvent(event)

    def mouseMoveEvent(self, event):
        modif = [QtCore.Qt.ControlModifier, QtCore.Qt.ShiftModifier]
        modif_ctl_shift = QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier

        if event.modifiers() == modif_ctl_shift:
            super(slider, self).mouseMoveEvent(event)
        elif event.buttons() & QtCore.Qt.LeftButton:
            if event.modifiers() in modif:
                new_position = event.pos().x() - self._click_offset

                # modifiers = QGuiApplication.queryKeyboardModifiers()
                if event.modifiers() == (QtCore.Qt.ControlModifier):
                    step_size = 0.01
                elif event.modifiers() == QtCore.Qt.ShiftModifier:
                    step_size = 0.1
                else:
                    step_size = 1.0

                new_value = round(self.value() / (1000 * step_size)) * (
                    1000 * step_size
                ) + int(step_size * 1000) * (
                    1 if event.pos().x() > self._prev_x else -1
                )
                self.setValue(new_value)
                self._prev_x = event.pos().x()
                event.accept()
            else:
                new_position = event.pos().x() - self._click_offset
                new_value = self.style().sliderValueFromPosition(
                    self.minimum(),
                    self.maximum(),
                    new_position,
                    self.width() - 16,
                )
                self.setValue(new_value)
                event.accept()
        else:
            super(slider, self).mouseMoveEvent(event)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super(slider, self).wheelEvent(event)

    def keyPressEvent(self, event):
        p = self.mapFromGlobal(QtGui.QCursor.pos())
        self.startDragpos = p
        self.realStartDragpos = p
        self.deltaValue = 0
        super(slider, self).keyPressEvent(event)


class DoubleSlider(slider):
    doubleValueChanged = QtCore.Signal(float)

    def __init__(
        self,
        custom_signals,
        parent=None,
        sliderRange=(-100.0, 100.0),
        defaultValue=0.0,
        dencity=1000000,
        draggerSteps=FLOAT_SLIDER_DRAG_STEPS,
    ):
        super(DoubleSlider, self).__init__(
            parent, draggerSteps=draggerSteps, sliderRange=sliderRange
        )
        self.isFloat = True
        self._dencity = abs(dencity)
        self.setOrientation(QtCore.Qt.Horizontal)

        self.defaultValue = defaultValue

        # set internal int slider range (dencity)
        self.setMinimum(0)
        self.setMaximum(self._dencity)

        # set out range
        self.valueChanged.connect(self.onInternalValueChanged)
        self.valueIncremented.connect(self.onValueIncremented)
        self.setMappedValue(self.defaultValue, True)

    def setRange(self, min_val, max_val):
        # implement a dummny setRange to avoid integer interpolation in
        # the slider
        # NOTE: not 100% sure why this should be override
        pass

    def onValueIncremented(self, step):
        # convert step value to slider internal space
        sliderInternalRange = (self.minimum(), self.maximum())
        sliderDistance = max(sliderInternalRange) - min(sliderInternalRange)
        valueDistance = max(self.sliderRange) - min(self.sliderRange)
        factor = sliderDistance / valueDistance
        unMappedStep = step * factor

        currentInternalValue = self.value()
        newUnmappedValue = currentInternalValue + unMappedStep
        self.setValue(newUnmappedValue)

    def mappedValue(self):
        return self.mapValue(self.value())

    def setMappedValue(self, value, blockSignals=False):
        # convert mapped value to slider internal integer
        internalValue = self.unMapValue(value)

        if blockSignals:
            self.blockSignals(True)

        self.setValue(internalValue)

        if self.signalsBlocked() and blockSignals:
            self.blockSignals(False)

    def mapValue(self, inValue):
        # convert slider int value to slider float range value
        return mapRangeUnclamped(
            inValue,
            self.minimum(),
            self.maximum(),
            self.sliderRange[0],
            self.sliderRange[1],
        )

    def unMapValue(self, outValue):
        # convert mapped float value to slider integer
        return int(
            mapRangeUnclamped(
                outValue,
                self.sliderRange[0],
                self.sliderRange[1],
                self.minimum(),
                self.maximum(),
            )
        )

    def onInternalValueChanged(self, x):
        mappedValue = self.mapValue(x)
        self.doubleValueChanged.emit(mappedValue)


class valueBox(QtWidgets.QDoubleSpinBox):
    """Custom QDoubleSpinBox

    Custom SpinBox with Houdini Style draggers, :obj:`draggers`.
    Middle Click to display a bunch of draggers to change value by
    adding different delta values

    Extends:
        QtWidgets.QDoubleSpinBox
    """

    valueIncremented = QtCore.Signal(object)

    def __init__(
        self,
        labelText="",
        type="float",
        buttons=False,
        decimals=3,
        draggerSteps=FLOAT_SLIDER_DRAG_STEPS,
        *args,
        **kwargs
    ):
        """
        :param type: Choose if create a float or int spinBox,
            defaults to "float"
        :type type: str, optional
        :param buttons: Show or hidden right up/Down Buttons, defaults to False
        :type buttons: bool, optional
        :param decimals: Number of decimals if type is "float", defaults to 3
        :type decimals: int, optional
        :param *args: [description]
        :type *args: [type]
        :param **kwargs: [description]
        :type **kwargs: [type]
        """
        super(valueBox, self).__init__(*args, **kwargs)
        self.labelFont = QtGui.QFont("Serif", 10, QtGui.QFont.Bold)
        self.labelText = labelText
        self.draggerSteps = copy(draggerSteps)
        self.isFloat = type == "float"
        if not self.isFloat:
            self.setDecimals(0)
        else:
            self.setDecimals(decimals)
        if not buttons:
            self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.setStyleSheet(getSliderStyleSheet("sliderStyleSheetA"))
        self.lineEdit().installEventFilter(self)
        self.installEventFilter(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.draggers = None
        self.setRange(FLOAT_RANGE_MIN, FLOAT_RANGE_MAX)

    def paintEvent(self, event):
        super(valueBox, self).paintEvent(event)
        p = QtGui.QPainter()
        p.begin(self)
        p.setPen(Colors.DarkGray)
        p.setFont(self.labelFont)
        p.drawText(self.rect(), QtCore.Qt.AlignCenter, self.labelText)
        p.end()

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super(valueBox, self).wheelEvent(event)

    def onValueIncremented(self, step):
        self.valueIncremented.emit(step)
        val = self.value() + step
        self.setValue(val)

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.MiddleButton:
                if self.draggers is None:
                    self.draggers = draggers(
                        self, self.isFloat, draggerSteps=self.draggerSteps
                    )
                    self.draggers.increment.connect(self.onValueIncremented)
                self.draggers.show()
                if self.isFloat:
                    self.draggers.move(
                        self.mapToGlobal(
                            QtCore.QPoint(
                                event.pos().x() - 1,
                                event.pos().y() - self.draggers.height() / 2,
                            )
                        )
                    )
                else:
                    self.draggers.move(
                        self.mapToGlobal(
                            QtCore.QPoint(
                                event.pos().x() - 1,
                                event.pos().y() - self.draggers.height() + 15,
                            )
                        )
                    )
        return False

    def update(self):
        self.setStyleSheet(getSliderStyleSheet("sliderStyleSheetA"))
        super(valueBox, self).update()


class pyf_Slider(QtWidgets.QWidget):
    """Custom Slider that encapsulates a :obj:`slider` or a :obj:`DoubleSlider`
    and a :obj:`valueBox` linked together

    Signals:
        :valueChanged: Signal emitted when slider or valueBox value changes,
        int/float
    """

    valueChanged = QtCore.Signal(object)
    sliderPressed = QtCore.Signal()
    sliderReleased = QtCore.Signal()

    # editingStart = QtCore.Signal()
    # editingFinished = QtCore.Signal()

    def __init__(
        self,
        parent,
        custom_signals,
        Type="float",
        style=0,
        name=None,
        sliderRange=(-100.0, 100.0),
        defaultValue=0.0,
        draggerSteps=FLOAT_SLIDER_DRAG_STEPS,
        *args
    ):
        """
        :param parent: Parent Widget
        :type parent: QtWidgets.QWidget
        :param type: Choose if create a float or int Slider, defaults
            to "float"
        :type type: str, optional
        :param style: Choose looking style, 0 is a full colored xsi style
            slider, and 1 is a normal colored slider, defaults to 0
        :type style: number, optional
        :param name: Name to display in a label, if None no label created,
            defaults to None
        :type name: [type], optional
        :param *args: [description]
        :type *args: [type]
        """
        super(pyf_Slider, self).__init__(parent=parent, *args)
        self.parent = parent
        self.setLayout(QtWidgets.QHBoxLayout())
        self.input = valueBox(type=Type)
        self.input.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.input.valueIncremented.connect(self.incrementValue)
        self.input.setValue(defaultValue)
        self.type = Type

        if self.type in ATTR_SLIDER_TYPES:
            self.sld = DoubleSlider(
                self,
                custom_signals,
                defaultValue=defaultValue,
                sliderRange=sliderRange,
                draggerSteps=draggerSteps,
            )
        if self.type == "int":
            self.sld = slider(self, custom_signals, sliderRange=sliderRange)
        self.sld.valueIncremented.connect(self.incrementValue)

        self.input.setRange(sliderRange[0], sliderRange[1])

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.input.setContentsMargins(0, 0, 0, 0)
        self.sld.setContentsMargins(0, 0, 0, 0)
        self.label = None
        if name:
            self.label = QtWidgets.QLabel(name + "  ")
            self.layout().addWidget(self.label)
        self.layout().addWidget(self.input)
        self.layout().addWidget(self.sld)
        h = 17
        self.input.setMinimumWidth(50)
        self.input.setMaximumWidth(50)
        self.setMaximumHeight(h)
        self.setMinimumHeight(h)
        self.sld.setMaximumHeight(h)
        self.sld.setMinimumHeight(h)
        self.input.setMaximumHeight(h)
        self.input.setMinimumHeight(h)
        self.styleSheetType = style
        if self.styleSheetType == 0:
            self.layout().setSpacing(0)
            self.sld.setStyleSheet(getSliderStyleSheet("sliderStyleSheetA"))
        elif self.styleSheetType == 1:
            self.sld.setStyleSheet(getSliderStyleSheet("sliderStyleSheetB"))

        self.sld.valueChanged.connect(self.sliderValueChanged)
        self.sld.sliderPressed.connect(self.signalSliderPressed)
        self.sld.sliderReleased.connect(self.signalSliderReleased)
        self.input.valueChanged.connect(self.valBoxValueChanged)

        self._value = 0.0

    def signalSliderPressed(self):
        self.sliderPressed.emit()

    def signalSliderReleased(self):
        self.sliderReleased.emit()

    def sliderValueChanged(self, x):

        outValue = mapRangeUnclamped(
            x,
            float(self.sld.minimum()),
            float(self.sld.maximum()),
            self.input.minimum(),
            self.input.maximum(),
        )
        self.input.blockSignals(True)
        self.input.setValue(outValue)
        self.input.blockSignals(False)
        self.valueChanged.emit(outValue)

    def valBoxValueChanged(self, x):
        val = self.input.value()

        sv = mapRangeUnclamped(
            val,
            self.input.minimum(),
            self.input.maximum(),
            self.sld.minimum(),
            self.sld.maximum(),
        )
        self.sld.blockSignals(True)
        self.sld.setValue(int(sv))
        self.sld.blockSignals(False)
        self.valueChanged.emit(x)

    def update(self):
        if self.styleSheetType == 0:
            self.layout().setSpacing(0)
            self.sld.setStyleSheet(getSliderStyleSheet("sliderStyleSheetA"))
        elif self.styleSheetType == 1:
            self.sld.setStyleSheet(getSliderStyleSheet("sliderStyleSheetB"))
        super(pyf_Slider, self).update()

    @property
    def _value_range(self):
        return self.maximum - self.minimum

    @property
    def minimum(self):
        return self.input.minimum()

    @property
    def maximum(self):
        return self.input.maximum()

    def value(self):
        self._value = self.input.value()
        if self.type == "int":
            self._value = int(self._value)
        return self._value

    def incrementValue(self, delta):
        if delta == 0.0:
            return
        old = self.input.value()
        new = old + delta
        self.input.setValue(new)
        self.valueChanged.emit(new)

    def setValue(self, value):
        self.input.setValue(value)
        self._value = self.input.value()
        self.valueChanged.emit(self.value())
        self.valBoxValueChanged(0)

    def setMinimum(self, value):
        self.input.setMinimum(value)
        self.sld.setMinimum(value)
        pass

    def setMaximum(self, value):
        self.input.setMaximum(value)
        self.sld.setMaximum(value)
        # pass

    def getRange(self):
        return [self.input.minimum(), self.input.maximum()]

    def setRange(self, min, max):
        """Sets the range for the input value, real max and min range

        :param min: Minimum Value
        :type min: float/int
        :param max: Maximum Value
        :type max: float/int
        """
        # self.setMinimum(min)
        # self.setMaximum(max)
        self.input.setRange(min, max)
        self.sld.setRange(min, max)

    def setDisplayMinimun(self, value):
        """Sets the Minimum value for display options, real min value don't
        touched, if current value is less than this display value,Widget
        automatically recalculates minDisplay

        :param value: New Display MinValue
        :type value: float/int
        """
        # self._dispMin = value
        # self.sld.setMinimum(value)
        pass

    def setDisplayMaximum(self, value):
        """Sets the Maximum value for display options, real max value don't
        touched, if current value is bigger than this display value,Widget
        automatically recalculates maxDisplay

        :param value: New Display MaxValue
        :type value: float/int
        """
        # self._dispMax = value
        # self.sld.setMaximum(value)
        pass

    def setDecimals(self, decimals):
        self.input.setDecimals(decimals)
        # if type != "int":
        #     self.sld.setDecimals(decimals)

    def setSingleStep(self, step):
        self.input.setSingleStep(step)

    def hideLabel(self):
        """Hides Name label"""
        if self.label:
            self.label.hide()

    def showLabel(self):
        """Shows Name label"""
        if self.label:
            self.label.show()

    def hideSlider(self):
        """Hides Slider"""
        self.sld.hide()

    def showSlider(self):
        """Show Slider"""
        self.sld.show()
