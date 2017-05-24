# -*- coding: utf-8 -*-

from fs_inode import ext2_inode
import fs_superbloc
from fs_bloc_group import ext2_bgroup_desc
from bitarray import bitarray
import struct
from bloc_device import *


# This class implements read only ext2 filesystem

class ext2(object):
    def __init__(self, filename):
        self.sb = fs_superbloc.ext2_superbloc(filename)
        self.disk = bloc_device(1024 << self.sb.s_log_block_size, filename)

        file = open(filename)

        blkgrps = self.sb.s_blocks_count/self.sb.s_blocks_per_group
        if self.sb.s_blocks_count%self.sb.s_blocks_per_group:
            blkgrps += 1
        self.bgroup_desc_list = []
        for i in xrange(blkgrps):
            file.seek(2048+i*32)
            raw = file.read(self.disk.blksize)
            bgroup = ext2_bgroup_desc(raw)
            self.bgroup_desc_list.append(bgroup)

        self.inode_map = bitarray(endian='little')
        self.inode_map.frombytes(self.disk.read_bloc(self.bgroup_desc_list[0].bg_inode_bitmap))

        self.bloc_map = bitarray(endian='little')
        self.bloc_map.frombytes(self.disk.read_bloc(self.bgroup_desc_list[0].bg_block_bitmap))

        self.inodes_list = []
        self.inodes_list.append(ext2_inode(None))
        for group in self.bgroup_desc_list:
            for i in xrange(0, self.sb.s_inodes_per_group):
                file.seek(group.bg_inode_table*self.disk.blksize + i*self.sb.s_inode_size)
                self.inodes_list.append(ext2_inode(file.read(self.sb.s_inode_size), i+1))
        self.direct = 12
        self.single_indirect = self.disk.blksize/4
        self.double_indirect = self.single_indirect**2
        self.triple_indirect = self.single_indirect**3
        return

    # find the directory inode number of a path
    # given : ex '/usr/bin/cat' return the inode
    # of '/usr/bin'
    def dirnamei(self, path):
        return
        # find an inode number according to its path

    # ex : '/usr/bin/cat'
    # only works with absolute paths

    def namei(self, path):
        if path[0] != "/":
            return
        inode = 2
        directory = self.inodes_list[inode]
        path_splitted = path.split("/")

        for file in path_splitted:
            if file != '':
                inode = self.lookup_entry(directory, file)
                directory = self.inodes_list[inode]
            if path_splitted[-1] == file:
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
        for i in xrange(dinode.i_size):
            bloc = self.bmap(dinode, i)
            if bloc == 0:
                return
            data = self.disk.read_bloc(bloc)
            shift = 0
            name_length = 0
            while shift + name_length+8 < self.disk.blksize:
                inode, record_length, name_length = struct.unpack_from("<IHB", data, shift)
                if data[shift+8:shift + name_length+8] == name:
                    return inode
                shift += record_length

        return
