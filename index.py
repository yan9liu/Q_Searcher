# coding: utf-8

import ctypes
import codecs
from collections import OrderedDict
import pickle
import sys


stop_tokens = set([u'的', 
                   u'与',
                   u'第'])


# import segmentor
seg = ctypes.CDLL("libprobseg.so")
seg_init = seg.prob_init()
seg_degree = seg.set_seg_granul(seg_init, True)


def is_isbn(query):
    return len(query) == 13 and query[0] == '9' and query.isdigit()
    
    
def cut(query):
    result = ' ' * 1000
    seg.prob_seg(seg_init, query.encode('gb18030'), result)
    tokens = result.decode('gb18030').strip().strip('\0').split()
    return [t for t in tokens if t not in stop_tokens]


def n_gram(n):
    def gram(query):
        tokens = []
        padding = '_' * (n - 1)
        for s in query.split():
            s = padding + s + padding
            for i in range(len(s)-(n-1)):
                tokens.append(s[i:i+n])
        return tokens
    return gram


def create_index(reader, min_freq, to_tokens_func):
    Q = []  # subscript is qid
    Q_inverted = {}  # e.g., {'token':[qid, qid, ...], ...}    
    
    qid = 0
    for line in reader:
        query, freq_str = line.strip().split('\t')
        freq = int(freq_str)
        if freq < min_freq or is_isbn(query):
            continue
        tokens = to_tokens_func(query)
        tokens = OrderedDict.fromkeys(tokens).keys() 
        d = {'query':query, 'freq':freq, 'tokens':tokens}
        Q.append(d)
        
        for t in tokens:
            #if t in stop_tokens: 
            #    continue
            if t not in Q_inverted: 
                Q_inverted[t] = []
            Q_inverted[t].append(qid)

        qid += 1

        # for debug
        if qid % 1 == 0:
            print "[qid:%-7d]  %-50s%d" % (qid, query, freq)
            print '('.rjust(14, ' '),
            for t in tokens: print t,
            print ')'
            print

    return Q, Q_inverted


def main(in_file):
    min_freq = 10
    to_tokens_funcs = {'bigram': n_gram(n=2), 
                       'seg': cut}
        
    with codecs.open(in_file, 'r', 'utf-8') as reader:
        for name, func in to_tokens_funcs.items():
            index = create_index(reader, min_freq, func)
            out_file = "%s.freq%d.%s.idx.dump" % (in_file, min_freq, name)
            print "writing ...  file:", out_file
            with open(out_file, 'wb') as writer:
                pickle.dump(index, writer)
            
            ## for finding stop words while stop_tokens is None
            #token_df_list = \
            #    [(token, len(qids)) for token, qids in index[-1].items()]
            #token_df_list.sort(key=lambda p:p[1], reverse=True)
            #out_file = "%s.freq%d.%s.df" % (in_file, min_freq, name)
            #print "writing ...  file:", out_file
            #with codecs.open(out_file, 'w', 'utf-8') as writer:
            #    for token, df in token_df_list:
            #        writer.write("%s\t%d\n" % (token, df))
            
            reader.seek(0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: python index.py file"
        sys.exit(1)
    main(sys.argv[1]) 


