import os.path as osp
import random
import lmdb
import pyarrow as pa
import torch.utils.data as data
import copy

from srcOld.dataloader_utils import SeqFlip, DrawFromProbabilityMatrix


class Dataset_lmdb(data.Dataset):
    '''
    Reads an lmdb database.
    Expects the data to be packed as follows:
    (features, target, mask)
        features = (seq, pssm, entropy)
        target = (dist, omega, phi, theta)

    '''
    def __init__(self, db_path, chan_in, transform=None, target_transform=None, mask_transform=None, chan_out=3, draw_seq_from_msa=False):
        self.db_path = db_path
        self.env = lmdb.open(db_path, subdir=osp.isdir(db_path), max_readers=1,
                             readonly=True, lock=False,
                             readahead=False, meminit=False)


        with self.env.begin(write=False) as txn:
            # self.length = txn.stat()['entries'] - 1
            self.length = pa.deserialize(txn.get(b'__len__'))
            self.keys = pa.deserialize(txn.get(b'__keys__'))

        self.transform = transform
        self.target_transform = target_transform
        self.mask_transform = mask_transform
        self.chan_out = chan_out
        self.chan_in = chan_in
        self.draw_seq_from_msa = draw_seq_from_msa
        self.draw = DrawFromProbabilityMatrix(fraction_of_seq_drawn=0.2)
        self.draw_prob = 0.5

    def __getitem__(self, index):
        env = self.env
        with env.begin(write=False) as txn:
            byteflow = txn.get(self.keys[index])
        unpacked = pa.deserialize(byteflow)
        features = copy.deepcopy(unpacked[0])
        features = self.select_features(features)

        targets = copy.deepcopy(unpacked[1])
        targets = self.match_target_channels(targets)

        if isinstance(self.transform.transforms[0], SeqFlip):
            self.transform.transforms[0].reroll()
        if self.transform is not None:
            features = self.transform(features)

        if self.target_transform is not None:
            distances, coords = self.target_transform(targets)

        return features, distances, coords

    def __len__(self):
        return self.length

    def select_features(self,features):
        seq,pssm,entropy = features
        p = random.random()
        if self.chan_in == 21:
            if self.draw_seq_from_msa and p > self.draw_prob:
                features = (self.draw(pssm, seq=seq),)
            else:
                features = (seq,)
        elif self.chan_in == 22:
            if self.draw_seq_from_msa and p > self.draw_prob:
                features = (self.draw(pssm, seq=seq), entropy)
            else:
                features = (seq, entropy)
        elif self.chan_in == 41:
            features = (seq, pssm)
        elif self.chan_in == 42:
            features = (seq, pssm, entropy)
        else:
            raise NotImplementedError("The selected number of channels in is not currently supported")


        return features


    def match_target_channels(self,target):
        if self.chan_out == 3:
            target = (target[0],)
        elif self.chan_out == 6:
            target = target[0:2]
        elif self.chan_out == 9:
            pass
        else:
            raise NotImplementedError("chan_out is {}, which is not implemented".format(self.chan_out))
        return target


    def __repr__(self):
        return self.__class__.__name__ + ' (' + self.db_path + ')'
