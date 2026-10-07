"""
API for creating, deleting, debuging callbacks

# examples --------------------------------------------------------------------
# module
cb.selectionChangedCB("testingSessssslection", cb.testFunc)
cb.RECORDED_CALLBACKS
cb.removeAllSessionCB()


# manager A
e = cb.CallbackManager()
e.namespace
e.debug = False
e.selectionChangedCB("synopticUI1", cb.testFunc)
e.newSceneCB("synopticNewScene", cb.testFunc)
e.removeManagedCB("synopticUI1")
e.removeManagedCB("synopticNewScene")

e.attributeChangedCB("attrChanged", cb.testFunc, "pSphere1", ["tx"])
e.removeManagedCB("attrChanged")

e.MANAGER_CALLBACKS
e.removeAllManagedCB()

# manager b
r = cb.CallbackManager()
r.selectionChangedCB("synopticUI1", cb.testFunc)
r.MANAGER_CALLBACKS
r.removeAllManagedCB()

__author__ = "Rafael Villar"
__email__ = "rav@ravrigs.com"

"""
# interesting callbacks to look into
# OpenMaya.MCommandMessage (mel command executed)
# OpenMaya.MConditionMessage (some type of maya condition met)
# MDagMessage.addWorldMatrixModifiedCallback
# MDagMessage.addDagDagPathCallback (specific dag path)
# MDGMessage.addDelayedTimeChangeCallback
# MDGMessage.addForceUpdateCallback (time change after all dirty evals)
# OpenMaya.MEventMessage.addEventCallback(SceneSaved, SceneOpened)

# python
import uuid
from functools import wraps, partial

# dcc
from maya.api import OpenMaya as om

# constants -------------------------------------------------------------------
try:
    # dict to record all the callbacks made by any manager
    # As this module matures, it may not need to be in this try
    # but this allows the dict to be maintained even while reloading
    RECORDED_CALLBACKS
except NameError:
    RECORDED_CALLBACKS = {}


# manage callback functions ---------------------------------------------------
def removeAllSessionCB():
    """Remove all the callbacks created in this session, provided they are in
    the RECORDED_CALLBACKS dict
    """
    for cb in list(RECORDED_CALLBACKS.keys()):
        removeCB(cb)


def removeCBviaMayaID(mayaID, callback_info=RECORDED_CALLBACKS):
    """This if have the maya pointer only, this will remove it from the
    recorded_callbacks as well

    Args:
        mayaID (long): maya point to a callback
        callback_info (dict, optional): remove it from desired cb recorder
    """
    for callback_name, callback_id in list(callback_info.items()):
        if callback_id == mayaID:
            removeCB(callback_name, callback_info=callback_info)


def removeAllCBFromNode(node):
    """remove all callbacks from the provided node

    Args:
        node (str): name of node to remove callbacks from
    """
    m_node = getMObject(node)
    for mayaID in om.MMessage.nodeCallbacks(m_node):
        removeCBviaMayaID(mayaID)
        # om.MMessage.removeCallback(mayaID)


def removeCB(callback_identifier, callback_info=RECORDED_CALLBACKS):
    """Remove callback from scene and RECORDED_CALLBACKS(or provided dict)

    Args:
        callback_identifier (str): name of callback
        callback_info (dict, optional): dict to remove callback from
    """
    callback_id = callback_info.pop(callback_identifier, callback_identifier)
    try:
        om.MMessage.removeCallback(callback_id)
    except (RuntimeError, ValueError):
        pass


def removeNamespaceCB(namespace):
    """Remove all callbacks under the provided namespace

    Args:
        namespace (str): uuid or other type of namespace
    """
    for cb in list(RECORDED_CALLBACKS.keys()):
        if cb.startswith(namespace):
            removeCB(cb)


def checkAndRecordCB(callback_name,
                     callback_id,
                     callback_info=RECORDED_CALLBACKS):
    """will remove any callbacks of the same name prior to creating a new one

    Args:
        callback_name (str): desired name of the callback, readable
        callback_id (long): api method of identifying callbacks
    """
    if callback_name in callback_info:
        removeCB(callback_name, callback_info=callback_info)
    callback_info[callback_name] = callback_id


def registerSessionCB(func):
    """decorator to ensure that every callback created is recorded

    Args:
        func (function): function that will create the callback

    Returns:
        function: function
    """
    @wraps(func)
    def wrap(*args, **kwargs):
        callback_name, callback_func = args[:2]
        callback_id = func(*args, **kwargs)
        checkAndRecordCB(callback_name, callback_id)
        return callback_id
    return wrap


def testFunc(*args):
    """test function used for debugging/dev

    Args:
        *args: things that will printed
    """
    print("TESTFUNC", args)


# api convenience -------------------------------------------------------------
def getMObject(node):
    """get the mobject of any name provided, so it can have cb's assined to it

    Args:
        node (str): of node

    Returns:
        om.MObject: MOBJECT
    """
    mSel = om.MSelectionList()
    mSel.add(node)
    return mSel.getDependNode(0)


# types of callbacks managed --------------------------------------------------

@registerSessionCB
def selectionChangedCB(callback_name, func):
    """When the selection is changed call the provided function

    Args:
        callback_name (str): name you want to assign cb
        func (function): will be called upon

    Returns:
        long: maya id to created callback
    """
    callback_id = om.MEventMessage.addEventCallback("SelectionChanged", func)
    return callback_id


@registerSessionCB
def attributeChangedCB(callback_name, func, node, attributes):
    """call the provided function any of the provided attributes are changed

    Args:
        callback_name (str): name of the callback
        func (function): to be called upon
        node (str): name of node to montior for attr changes
        attributes (list): of SHORTNAMED attributes to monitor

    Returns:
        long: maya id to created callback
    """
    m_node = getMObject(node)
    attrMan = AttributeChangedManager(m_node, attributes, func)
    managerFunc = attrMan.attributeChanged
    callback_id = om.MNodeMessage.addAttributeChangedCallback(m_node,
                                                              managerFunc)
    return callback_id


@registerSessionCB
def newSceneCB(callback_name, func):
    """When a new scene is opened, call the provided function

    Args:
        callback_name (str): name you want to assign cb
        func (function): will be called upon

    Returns:
        long: maya id to created callback
    """
    callBackType = om.MSceneMessage.kSceneUpdate
    callback_id = om.MSceneMessage.addCallback(callBackType, func)
    return callback_id


@registerSessionCB
def timeChangedCB(callback_name, func):
    """ANYTIME the time is changed, call the provided function

    Args:
        callback_name (str): name you want to assign cb
        func (function): will be called upon

    Returns:
        long: maya id to created callback
    """
    callback_id = om.MDGMessage.addTimeChangeCallback(func)
    return callback_id


@registerSessionCB
def userTimeChangedCB(callback_name, func):
    """Callback triggers during user timeChange, skips PLAYBACK

    Args:
        callback_name (str): name you want to assign cb
        func (function): will be called upon

    Returns:
        long: maya id to created callback
    """
    timeManager = UserTimeChangedManager(func)
    managerFunc = timeManager.userTimeChanged
    callback_id = om.MDGMessage.addTimeChangeCallback(managerFunc)
    return callback_id


@registerSessionCB
def timerCB(callback_name, func, period):
    """Call the provided function at a fixed interval

    Args:
        callback_name (str): name you want to assign cb
        func (function): called with (elapsedTime, lastTime, clientData)
        period (float): interval in seconds

    Returns:
        long: maya id to created callback
    """
    callback_id = om.MTimerMessage.addTimerCallback(period, func)
    return callback_id


@registerSessionCB
def eventCB(callback_name, func, event):
    """Call the provided function when the named Maya event fires

    Use om.MEventMessage.getEventNames() for the list of valid events,
    e.g. "timeChanged" or "SelectionChanged".

    Args:
        callback_name (str): name you want to assign cb
        func (function): called with (clientData)
        event (str): Maya event name

    Returns:
        long: maya id to created callback
    """
    callback_id = om.MEventMessage.addEventCallback(event, func)
    return callback_id


@registerSessionCB
def conditionCB(callback_name, func, condition):
    """Call the provided function when the named Maya condition changes

    Use om.MConditionMessage.getConditionNames() for the list of valid
    conditions, e.g. "playingBack".

    Args:
        callback_name (str): name you want to assign cb
        func (function): called with (state, clientData)
        condition (str): Maya condition name

    Returns:
        long: maya id to created callback
    """
    callback_id = om.MConditionMessage.addConditionCallback(condition, func)
    return callback_id


@registerSessionCB
def sceneMessageCB(callback_name, func, message):
    """Call the provided function on a scene message

    Args:
        callback_name (str): name you want to assign cb
        func (function): called with (clientData)
        message (int): om.MSceneMessage type, e.g. kBeforeNew, kBeforeOpen

    Returns:
        long: maya id to created callback
    """
    callback_id = om.MSceneMessage.addCallback(message, func)
    return callback_id


@registerSessionCB
def sampleCallback(callback_name, func):
    """argument order is important. Callback_name and func must always be first
    must always return the mayaID to the callback
    Args:
        callback_name (str): name you want to assign cb
        func (function): will be called upon

    Returns:
        long: maya id to created callback
    """
    callback_id = 2349823749
    return callback_id


class AttributeChangedManager(object):

    """mini class that will be called upon when attrChanged callback is run
    this will check the plugs passed in to see if it is an attr of desired name

    Attributes:
        attributes (list): [tx, ty] of SHORT NAMED attrs to monitor
        func (function): to call when criteria met
        m_node (om.MOBJECT): mobject
    """

    def __init__(self, m_node, attributes, func):
        self.m_node = m_node
        self.attributes = attributes
        self.func = func

    def attributeChanged(self, id, plug1, plug2, payload):
        """actual function that will be called when attrChanged callback is
        created

        Args:
            id (int): 2056 is the desired, attr changed id
            plug1 (om.MPlug): MPlug attr to query

        Returns:
            n/a: n/a
        """
        if id != 2056:
            return

        if plug1.partialName() in self.attributes:
            self.func()


class UserTimeChangedManager(object):

    """mini class that will be called upon when timeChanged callback is run
    this will check to see if playback is active, if so BREAK

    Attributes:
        attributes (list): [tx, ty] of SHORT NAMED attrs to monitor
        func (function): to call when criteria met
        m_node (om.MOBJECT): mobject
    """

    def __init__(self, func):
        self.func = func

    def userTimeChanged(self, *args):
        """Check if playback is active, if so return without calling func
        """
        if om.MConditionMessage.getConditionState("playingBackAuto"):
            return
        self.func(*args)


class CallbackManager(object):

    """Convenience to manage callbacks

    Attributes:
        debug (bool): should callbacks created by manager produce print outs
        MANAGER_CALLBACKS (dict): record of all created callbacks
        namespace (str): namespace to put callbacks under
    """

    def __init__(self):
        self.debug = False
        self.namespace = None
        self.MANAGER_CALLBACKS = {}
        self.setNamespace(uuid.uuid1())

    def setNamespace(self, namespace):
        """set the namespace to put callbacks under

        Args:
            namespace (str): desired namespace
        """
        self.namespace = namespace

    def addNamespace(self, callback_name):
        """used in the decorator, add namespace to any name provided

        Args:
            callback_name (str): name of callback

        Returns:
            str: provided name with namespace
        """
        return "{}.{}".format(self.namespace, callback_name)

    def removeAllManagedCB(self):
        """remove all the callbacks created my this manager
        """
        for callback_id in list(self.MANAGER_CALLBACKS.keys()):
            removeCB(callback_id, callback_info=self.MANAGER_CALLBACKS)
            removeCB(callback_id)

    def removeManagedCB(self, callback_name):
        """remove specific callback under this manager

        Args:
            callback_name (str): name
        """
        for callback_id in list(self.MANAGER_CALLBACKS.keys()):
            if callback_id.endswith(callback_name):
                removeCB(callback_id, callback_info=self.MANAGER_CALLBACKS)
                removeCB(callback_id)

    def registerManagerCB(func):
        """decorator, adds debug and namespace to every callback created

        Args:
            func (function): function to wrap

        Returns:
            function: wrapped function
        """
        @wraps(func)
        def wrap(self, *args, **kwargs):
            args = list(args)
            callback_name, callback_func = args[:2]
            namespace_CB = self.addNamespace(callback_name)
            args[0] = namespace_CB
            debugInfo = []
            args[1] = self.wrapWithDebug(debugInfo, args[1])
            callback_id = func(self, *args, **kwargs)
            debugInfo.append(namespace_CB)
            debugInfo.append(callback_id)
            # manager created
            checkAndRecordCB(namespace_CB,
                             callback_id,
                             callback_info=self.MANAGER_CALLBACKS)
            return callback_id
        return wrap

    def checkDebug(self, debugInfo, *args):
        """safely check if manager is in debug mode

        Args:
            debugInfo (list): callback name, function being called with args
            *args: args to pass to the function associated with callback
        """
        try:
            callback_id = debugInfo[0]
            mayaID = debugInfo[1]
            func_name = args[0].__name__
            if self.debug:
                print("{} >> {} >> {}({})".format(callback_id,
                                                  mayaID,
                                                  func_name,
                                                  *args[1:]))
        except Exception:
            pass
        finally:
            # ensure that the function is always called
            args[0](*args[1:])

    def wrapWithDebug(self, debugInfo, func):
        """so every function that is associated with a callback is swapped
        out for this one, so it will check for debugging

        Args:
            debugInfo (list): callback name, mayacallback id, functions to call
            func (function): to wrap with this debug checker

        Returns:
            function: partial function that will check for debug
        """
        wrappedFunc = partial(self.checkDebug, debugInfo, func)
        return wrappedFunc

    @registerManagerCB
    def selectionChangedCB(self, callback_name, func):
        callback_id = selectionChangedCB(callback_name, func)
        return callback_id

    @registerManagerCB
    def attributeChangedCB(self, callback_name, func, node, attributes):
        callback_id = attributeChangedCB(callback_name, func, node, attributes)
        return callback_id

    @registerManagerCB
    def newSceneCB(self, callback_name, func):
        callback_id = newSceneCB(callback_name, func)
        return callback_id

    @registerManagerCB
    def timeChangedCB(self, callback_name, func):
        callback_id = timeChangedCB(callback_name, func)
        return callback_id

    @registerManagerCB
    def userTimeChangedCB(self, callback_name, func):
        callback_id = userTimeChangedCB(callback_name, func)
        return callback_id

    @registerManagerCB
    def timerCB(self, callback_name, func, period):
        callback_id = timerCB(callback_name, func, period)
        return callback_id

    @registerManagerCB
    def eventCB(self, callback_name, func, event):
        callback_id = eventCB(callback_name, func, event)
        return callback_id

    @registerManagerCB
    def conditionCB(self, callback_name, func, condition):
        callback_id = conditionCB(callback_name, func, condition)
        return callback_id

    @registerManagerCB
    def sceneMessageCB(self, callback_name, func, message):
        callback_id = sceneMessageCB(callback_name, func, message)
        return callback_id
