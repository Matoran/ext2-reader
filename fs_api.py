# -*- coding: utf-8 -*-
import hexdump
import stat
import struct

from math import ceil


class ext2_file_api(object):
    def __init__(self, filesystem):
        self.fs = filesystem
        self.files = []
        self.frees = []
        return

    # For all symlink shorter than 60 bytes long, the data is stored within the inode itself; 
    # it uses the fields which would normally be used to store the pointers to data blocks. 
    # This is a worthwhile optimisation as it we avoid allocating a full block for the symlink, 
    # and most symlinks are less than 60 characters long. 
    def readlink(self, path):
        inode_num = self.fs.namei(path)
        inode = self.fs.inodes_list[inode_num]
        if inode.i_size < 60:
            return struct.pack("<15I", *inode.i_blocks).rstrip('\0')
        else:
            for i in xrange(int(ceil(float(inode.i_size)/self.fs.disk.blksize))):
                bloc = self.fs.bmap(inode, i)
                if bloc == 0:
                    return
                return self.fs.disk.read_bloc(bloc).rstrip('\0')
        return

    # open a file, i.e reserve a file descriptor
    # in the open file table, pointing to the corresponding
    # inode. file descriptor is just an handle used to find the
    # corresponding inode. This handle is allocated by the filesystem.
    def open(self, path):
        if len(self.frees) == 0:
            self.files.append(self.fs.namei(path))
            return len(self.files) - 1
        else:
            index = self.frees.pop()
            self.files[index] = self.fs.namei(path)
            return index

    # release file descriptor entry, should we flush buffers : no, this is separate ?
    # openfiles[fd] = None 
    def close(self, fd):
        self.files[fd] = None
        self.frees.append(fd)
        return

    # read nbytes from the file descriptor previously opened, starting at the given offset
    def read(self, fd, offset, count):
        res = ""
        inode = self.fs.inodes_list[self.files[fd]]

        total_left = 0 if offset > inode.i_size else min(inode.i_size - offset, count)
        buffer_offset = 0
        while total_left > 0:
            bloc_num = self.fs.bmap(inode, int(offset / self.fs.disk.blksize))
            offset_in_bloc = offset % self.fs.disk.blksize
            to_read = min(self.fs.disk.blksize - offset_in_bloc, total_left)
            if bloc_num != 0:
                blk = self.fs.disk.read_bloc(bloc_num)
                res += blk[offset_in_bloc:offset_in_bloc + to_read]

            offset += to_read
            buffer_offset += to_read
            total_left -= to_read
        return res

    # get the attributes of a node in a stat dictionnary :
    # keys st_ctime, st_mtime, st_nlink, st_mode, st_size, st_gid, st_uid, st_atime
    # {'st_ctime': 1419027551.4907832, 'st_mtime': 1419027551.4907832, \
    # 'st_nlink': 36, 'st_mode': 16877, 'st_size': 4096, 'st_gid': 0, \
    #  'st_uid': 0, 'st_atime': 1423220038.6543322}
    def attr(self, path):
        inode_num = self.fs.namei(path)
        inode = self.fs.inodes_list[inode_num]
        res = {
            'st_ctime': inode.i_ctime,
            'st_mtime': inode.i_mtime,
            'st_blocks': int(ceil(float(inode.i_size)/512)),
            'st_gid': inode.i_gid,
            'st_nlink': inode.i_links_count,
            'st_mode': inode.i_mode,
            'st_blksize': self.fs.disk.blksize,
            'st_size': inode.i_size,
            'st_atime': inode.i_atime,
            'st_uid': inode.i_uid
        }
        return res

        # implementation of readdir(3) :

    # open the named file, and read each dir_entry in it
    # note that is not a syscall but a function from the libc§

    def dodir(self, path):
        inode = self.fs.inodes_list[self.fs.namei(path)]
        dirlist = []
        for i in xrange(int(ceil(float(inode.i_size)/self.fs.disk.blksize))):
            bloc = self.fs.bmap(inode, i)
            if bloc == 0:
                return
            data = self.fs.disk.read_bloc(bloc)
            shift = 0
            name_length = 0
            while shift + name_length+8 < self.fs.disk.blksize:
                inode_num, record_length, name_length = struct.unpack_from("<IHB", data, shift)
                dirlist.append(unicode(data[shift+8:shift + name_length+8]))
                shift += record_length
        return dirlist
