# -*- coding: utf-8 -*-
# emulate a simple bloc device using a file
# reading it only by bloc units

class bloc_device(object):
    def __init__(self, blksize, pathname):
        self.blksize = blksize
        self.file = open(pathname)
        return

    def read_bloc(self, bloc_num, numofblk=1):
        # type: (object, object) -> object

        self.file.seek(self.blksize*bloc_num)
        return self.file.read(self.blksize*numofblk)
