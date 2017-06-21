# -*- coding: utf-8 -*-
# authors: Cyril Iseli, Marco Rodrigues
# date: may-june 2017
from math import ceil
from fs_inode import ext2_inode
import fs_superbloc
from fs_bloc_group import ext2_bgroup_desc
from bitarray import bitarray
import struct
from bloc_device import *


# This class implements read only ext2 filesystem
class ext2(object):
    def __init__(self, filename):
        self.superbloc = fs_superbloc.ext2_superbloc(filename)
        self.disk = bloc_device(1024 << self.superbloc.s_log_block_size, filename)

        file = open(filename)

        # read groups
        blkgrps = int(ceil(float(self.superbloc.s_blocks_count) / self.superbloc.s_blocks_per_group))
        self.bgroup_desc_list = []
        bg_bloc = 1024*2 if self.disk.blksize == 1024 else self.disk.blksize
        for i in xrange(blkgrps):
            file.seek(bg_bloc+i*32)
            raw = file.read(self.disk.blksize)
            bgroup = ext2_bgroup_desc(raw)
            self.bgroup_desc_list.append(bgroup)
        self.inode_maps = []
        self.bloc_maps = []

        # read inodes, inode_bitmaps, bloc_bitmaps
        self.inodes_list = []
        self.inodes_list.append(ext2_inode(None))
        for group in self.bgroup_desc_list:
            for i in xrange(0, self.superbloc.s_inodes_per_group):
                file.seek(group.bg_inode_table * self.disk.blksize + i * self.superbloc.s_inode_size)
                self.inodes_list.append(ext2_inode(file.read(self.superbloc.s_inode_size), i + 1))
            bloc_bitarray = bitarray(endian='little')
            bloc_bitarray.frombytes(self.disk.read_bloc(group.bg_block_bitmap))
            inode_bitarray = bitarray(endian='little')
            inode_bitarray.frombytes(self.disk.read_bloc(group.bg_inode_bitmap))
            self.inode_maps.append(inode_bitarray)
            self.bloc_maps.append(bloc_bitarray)

        # to pass unittest
        self.inode_map = self.inode_maps[0]
        self.bloc_map = self.bloc_maps[0]

        # number of blocks for each case
        self.direct = 12
        self.single_indirect = self.disk.blksize/4
        self.double_indirect = self.single_indirect**2
        self.triple_indirect = self.single_indirect**3
        return

    # find the directory inode number of a path
    # given : ex '/usr/bin/cat' return the inode
    # of '/usr/bin'
    def dirnamei(self, path):
        if path[0] != "/":
            return
        elif path == "/":
            return 2
        inode = 2
        directory = self.inodes_list[inode]
        path_splitted = path.split("/")
        actualPath = ""
        path_splitted.pop(0)
        # follow the path until found file
        for file in path_splitted:
            actualPath += "/" + file
            old_inode = inode
            inode = self.lookup_entry(directory, file)
            if inode is None:
                raise OSError(2, 'No such file or directory', path)
            directory = self.inodes_list[inode]
            if actualPath == path:
                return old_inode
        return
        # find an inode number according to its path

    # ex : '/usr/bin/cat'
    # only works with absolute paths

    def namei(self, path):
        if path[0] != "/":
            return
        elif path == "/":
            return 2
        inode = 2
        directory = self.inodes_list[inode]
        path_splitted = path.split("/")
        actualPath = ""
        path_splitted.pop(0)
        # follow the path until found file
        for file in path_splitted:
            actualPath += "/" + file
            inode = self.lookup_entry(directory, file)
            if inode is None:
                raise OSError(2, 'No such file or directory', path)
            directory = self.inodes_list[inode]
            if actualPath == path:
                return inode
        return

    def bmap(self, inode, blk):
        # case 0
        if blk < self.direct:
            return inode.i_blocks[blk]
        if inode.i_blocks[12] == 0:
            return 0
        blk -= self.direct
        # single indirect
        if blk < self.single_indirect:
            indirect = self.disk.read_bloc(inode.i_blocks[12])
            return struct.unpack_from("<I", indirect, blk*4)[0]
        # double indirect
        if inode.i_blocks[13] == 0:
            return 0
        blk -= self.single_indirect
        if blk < self.double_indirect:
            indirect = self.disk.read_bloc(inode.i_blocks[13])
            double_indirect = struct.unpack_from("<I", indirect, blk / self.single_indirect*4)[0]
            if double_indirect == 0:
                return 0
            double_indirect_bloc = self.disk.read_bloc(double_indirect)
            return struct.unpack_from("<I", double_indirect_bloc, blk % self.single_indirect*4)[0]
        # triple indirect
        if inode.i_blocks[14] == 0:
            return 0
        blk -= self.double_indirect
        indirect = self.disk.read_bloc(inode.i_blocks[14])
        double_indirect = struct.unpack_from("<I", indirect, blk / self.double_indirect * 4)[0]
        if double_indirect == 0:
            return 0
        double_indirect_bloc = self.disk.read_bloc(double_indirect)
        triple_indirect = struct.unpack_from("<I", double_indirect_bloc, blk % self.double_indirect / self.single_indirect * 4)[0]
        if triple_indirect == 0:
            return 0
        triple_indirect_bloc = self.disk.read_bloc(triple_indirect)
        return struct.unpack_from("<I", triple_indirect_bloc, blk % self.single_indirect * 4)[0]
        # lookup for a name in a directory, and return its inode number,

    # given inode directory dinode
    # ext2 release 0 store directories in a linked list of records
    # pointing to the next by length
    # - records cannot span multiple blocs.
    # - the end of the linked list as an inode num equal to zero.
    def lookup_entry(self, dinode, name):
        # read each bloc until find name in directory
        for i in xrange(int(ceil(float(dinode.i_size)/self.disk.blksize))):
            bloc = self.bmap(dinode, i)
            if bloc == 0:
                return
            data = self.disk.read_bloc(bloc)
            shift = 0
            name_length = 0
            # read each entry of the bloc
            while shift + name_length+8 < self.disk.blksize:
                inode, record_length, name_length = struct.unpack_from("<IHB", data, shift)
                if data[shift+8:shift + name_length+8] == name:
                    return inode
                shift += record_length
        return
