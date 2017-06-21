# -*- coding: utf-8 -*-
# authors: Cyril Iseli, Marco Rodrigues
# date: may-june 2017
# try to restore file by reading inode_bitmap, if is 0 then read inode
# doesn't work i_blocks are always set to 0 when a file is deleted

from fs import *
import sys


workfile = "mediumimg0.ext2.img"


# read inode content
def read_inode(inode_num, ext2fs):
    res = ""
    for i in xrange(0, ext2fs.inodes_list[inode_num].i_size):
        bmap_bloc = ext2fs.bmap(ext2fs.inodes_list[inode_num], i)
        if bmap_bloc is 0:
            return res
        res += ext2fs.disk.read_bloc(bmap_bloc)


if __name__ == '__main__':
    workfile = sys.argv[1]
    ext2fs = ext2(workfile)
    inode_maps = ext2fs.inode_maps
    nb_groups = len(ext2fs.bgroup_desc_list)
    inodes_per_group = ext2fs.superbloc.s_inodes_per_group
    # foreach group
    for i in xrange(nb_groups):
        # foreach inode group
        for j in xrange(inodes_per_group):
            # need +1 because inodes_list content a fictive inode at index 0
            inode_index = i*inodes_per_group+j+1
            inode = ext2fs.inodes_list[inode_index]
            print inode_index, inode_maps[i][j], inode.i_blocks[0]
            # is it free and not null?
            if not inode_maps[i][j] and inode.i_blocks[0]:
                # display informations of inode and file content
                print inode
                file = read_inode(inode_index, ext2fs)
                print file
                yn = raw_input('Do you want to save the file ? Y/N')
                # if the user want to save the file
                if yn == 'Y' or yn == 'y':
                    name = raw_input('Name file:')
                    text_file = open(name, "w")
                    text_file.write(file)
                    text_file.close()






