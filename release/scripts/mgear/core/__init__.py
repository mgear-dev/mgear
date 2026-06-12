import mgear.pymaya as pm
import mgear


def getMayaVer():
    """Get Maya version

    :return: Maya version
    """
    version = pm.versions.current()
    return version


def aboutMgear(*args):
    """About mgear"""
    version = mgear.getVersion()
    note = """

    mGear version: {}

    MGEAR is under the terms of the MIT License

    Copyright (c) 2011-2018 Jeremie Passerin, Miquel Campos
    Copyright (c) 2018-2023 The mGear-Dev Organization

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
    OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
    OR OTHER DEALINGS IN THE SOFTWARE.

    """.format(version)
    pm.confirmDialog(title='About mGear', message=note, button=["OK"],
                     defaultButton='OK', cancelButton='OK', dismissString='OK')
