from mgear.core import pyqt
from mgear.vendor.Qt import QtCore, QtWidgets
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import mgear.pymaya as pm


class SpaceRecorderUI(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SpaceRecorderUI, self).__init__(parent)

        # init 3 different buffers
        SpaceRecorderUI.world_spaces = [[], [], []]

        self.setWindowTitle("World Space Recorder")
        self.setMinimumWidth(275)
        self.setWindowFlags(QtCore.Qt.Tool)

        # Delete UI on close to avoid winEvent error
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.record_A_btn = QtWidgets.QPushButton("Record Buffer A")
        self.apply_A_btn = QtWidgets.QPushButton("Apply Buffer A")
        self.apply_A_selected_btn = QtWidgets.QPushButton("Apply Sel Buffer A")

        self.record_B_btn = QtWidgets.QPushButton("Record Buffer B")
        self.apply_B_btn = QtWidgets.QPushButton("Apply Buffer B")
        self.apply_B_selected_btn = QtWidgets.QPushButton("Apply Sel Buffer B")

        self.record_C_btn = QtWidgets.QPushButton("Record Buffer C")
        self.apply_C_btn = QtWidgets.QPushButton("Apply Buffer C")
        self.apply_C_selected_btn = QtWidgets.QPushButton("Apply Sel Buffer C")

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        groupBox = QtWidgets.QGroupBox()
        groupBox.setTitle("Record World Spaces")
        record_layout = QtWidgets.QHBoxLayout(groupBox)
        record_layout.addWidget(self.record_A_btn)
        record_layout.addWidget(self.record_B_btn)
        record_layout.addWidget(self.record_C_btn)
        main_layout.addWidget(groupBox)

        groupBox = QtWidgets.QGroupBox()
        groupBox.setTitle("Apply World Spaces")
        apply_layout = QtWidgets.QHBoxLayout(groupBox)
        apply_layout.addWidget(self.apply_A_btn)
        apply_layout.addWidget(self.apply_B_btn)
        apply_layout.addWidget(self.apply_C_btn)
        main_layout.addWidget(groupBox)

        groupBox = QtWidgets.QGroupBox()
        groupBox.setTitle("Apply to Selection")
        apply_sel_layout = QtWidgets.QHBoxLayout(groupBox)
        apply_sel_layout.addWidget(self.apply_A_selected_btn)
        apply_sel_layout.addWidget(self.apply_B_selected_btn)
        apply_sel_layout.addWidget(self.apply_C_selected_btn)
        main_layout.addWidget(groupBox)

        main_layout.addStretch()

        self.setLayout(main_layout)

    def create_connections(self):
        self.record_A_btn.clicked.connect(SpaceRecorderUI.record_spaces_A)
        self.apply_A_btn.clicked.connect(SpaceRecorderUI.apply_spaces_A)
        self.apply_A_selected_btn.clicked.connect(
            SpaceRecorderUI.apply_to_selection_A
        )

        self.record_B_btn.clicked.connect(SpaceRecorderUI.record_spaces_B)
        self.apply_B_btn.clicked.connect(SpaceRecorderUI.apply_spaces_B)
        self.apply_B_selected_btn.clicked.connect(
            SpaceRecorderUI.apply_to_selection_B
        )

        self.record_C_btn.clicked.connect(SpaceRecorderUI.record_spaces_C)
        self.apply_C_btn.clicked.connect(SpaceRecorderUI.apply_spaces_C)
        self.apply_C_selected_btn.clicked.connect(
            SpaceRecorderUI.apply_to_selection_C
        )

    @classmethod
    def record_spaces(cls, buffer=0):
        """Record the world spaces of the selected object using the timeline range

        Args:
            buffer (int, optional): the buffer index to archive the spaces
        """
        cls.world_spaces[buffer] = []
        start = pm.playbackOptions(q=True, min=True)
        end = pm.playbackOptions(q=True, max=True)
        frame_range = int(end - start) + 1
        # store
        oSel = pm.selected()
        ct = start
        p_amount = 0
        increment = 100 / frame_range
        pm.progressWindow(
            title="Recording World Spaces", progress=p_amount, max=100
        )
        for i in range(frame_range):
            frame_spaces = []
            pm.progressWindow(
                e=True,
                progress=p_amount,
                status="Recording Frame:{} ".format(str(i)),
            )
            for x in oSel:
                pm.currentTime(int(ct))
                space = []
                space.append(x)
                space.append(x.getMatrix(worldSpace=True))
                frame_spaces.append(space)
            ct += 1
            cls.world_spaces[buffer].append(frame_spaces)
            p_amount += increment
        pm.progressWindow(e=True, endProgress=True)

    @classmethod
    def apply_spaces(cls, buffer=0):
        """Apply the archived world spaces  using the timeline range

        Args:
            buffer (int, optional): the buffer index to retrieve the spaces
        """
        if not cls.world_spaces[buffer]:
            pm.displayWarning("Space buffer is empty. Please record before")
            return
        start = pm.playbackOptions(q=True, min=True)
        end = pm.playbackOptions(q=True, max=True)
        frame_range = int(end - start) + 1
        ct = start
        p_amount = 0
        increment = 100 / frame_range
        pm.progressWindow(
            title="Apply World Spaces", progress=p_amount, max=100
        )
        for i in range(frame_range):
            pm.currentTime(int(ct))
            frame_spaces = cls.world_spaces[buffer][i]
            pm.progressWindow(
                e=True,
                progress=p_amount,
                status="Apply Frame:{} ".format(str(i)),
            )
            for space in frame_spaces:
                space[0].setMatrix(space[1], worldSpace=True)
                pm.setKeyframe(space[0])
            ct += 1
            p_amount += increment
        pm.progressWindow(e=True, endProgress=True)

    @classmethod
    def apply_to_selection(cls, buffer=0):
        """Apply the world spaces to the selected object using the timeline range
        The order of selection will determine the space used relative to the order
        of selection at the store time

        Args:
            buffer (int, optional): the buffer index to retrieve the spaces
        """
        if not cls.world_spaces[buffer]:
            pm.displayWarning("Space buffer is empty. Please record before")
            return
        oSel = pm.selected()
        if not oSel:
            pm.displayWarning("Please select object to apply spaces")
            return
        start = pm.playbackOptions(q=True, min=True)
        end = pm.playbackOptions(q=True, max=True)
        frame_range = int(end - start) + 1
        ct = start
        p_amount = 0
        increment = 100 / frame_range
        pm.progressWindow(
            title="Apply To Selection World Spaces", progress=p_amount, max=100
        )
        for i in range(frame_range):
            pm.currentTime(int(ct))
            frame_spaces = cls.world_spaces[buffer][i]
            for e, x in enumerate(oSel):
                frame_spaces[e][1]
                x.setMatrix(frame_spaces[e][1], worldSpace=True)
                pm.setKeyframe(x)
            ct += 1
            p_amount += increment
        pm.progressWindow(e=True, endProgress=True)

    @classmethod
    def record_spaces_A(cls):
        SpaceRecorderUI.record_spaces(buffer=0)

    @classmethod
    def record_spaces_B(cls):
        SpaceRecorderUI.record_spaces(buffer=1)

    @classmethod
    def record_spaces_C(cls):
        SpaceRecorderUI.record_spaces(buffer=2)

    @classmethod
    def apply_spaces_A(cls):
        SpaceRecorderUI.apply_spaces(buffer=0)

    @classmethod
    def apply_spaces_B(cls):
        SpaceRecorderUI.apply_spaces(buffer=1)

    @classmethod
    def apply_spaces_C(cls):
        SpaceRecorderUI.apply_spaces(buffer=2)

    @classmethod
    def apply_to_selection_A(cls):
        SpaceRecorderUI.apply_to_selection(buffer=0)

    @classmethod
    def apply_to_selection_B(cls):
        SpaceRecorderUI.apply_to_selection(buffer=1)

    @classmethod
    def apply_to_selection_C(cls):
        SpaceRecorderUI.apply_to_selection(buffer=2)


def open(*args):
    return pyqt.showDialog(SpaceRecorderUI)


if __name__ == "__main__":

    pyqt.showDialog(SpaceRecorderUI)
