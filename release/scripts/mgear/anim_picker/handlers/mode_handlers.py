from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class EditMode(object):
    """UI edition status mode handler"""

    def __init__(self, status=False):
        self.main_status = status
        self.status = status

    def __call__(self):
        return self.get()

    def set_init(self, status=False):
        self.__init__(status=status)

    def get_main(self):
        """Return main status for special override"""
        return self.main_status

    def toggle(self):
        """Toggle edit status"""
        self.status = not self.status

    def set(self, status=False):
        """Set edit status"""
        self.status = status

    def get(self):
        """Get edit current status"""
        return self.status
