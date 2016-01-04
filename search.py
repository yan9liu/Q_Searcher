# coding:utf-8

import codecs
import ctypes
import math
import pickle
import sys

from index import cut, n_gram
from norm import normalize_query

stop_subs = [u'旗舰店', u'当当自营', u'货到付款', 
             u'外贸原单', u'外贸', u'原单', 
             u'清仓特价', u'清仓', u'特价', 
             u'明星同款', u'包邮', u'新款',
             u'2014', u'2015', u'2016']

class Searcher(object):
    print 'loading index...'
    index_list = [pickle.load(open('query_20150702_all.freq10.seg.idx.dump', 'rb')),
                  pickle.load(open('query_20150702_all.freq10.bigram.idx.dump', 'rb'))]
    # corresponding token functions used in building indexes
    index_token_func_list = [cut, n_gram(n=2)]
                       
    def __init__(self, type_str):
        # corresponding conditions for filtering candidate qids
        # Pay attention that jaccard condition is very different between cut and ngram.
        # The condition right for cut is '>0.5', but that for ngram is '>3.0/7'.
        # Jaccard_char condition is only applied to cut, which is also '>0.5'.
        condition_funcs = [
            # for cut
            lambda cid: (self.jaccard(cid) > 0.5 and self.jaccard_char(cid) > 0.5),
            lambda cid: self.jaccard(cid) > 3.0 / 7, # for ngram
            self.is_subset] 
        score_funcs = [self.tf, self.bm25, 
                       self.jaccard, self.jaccard_char,
                       self.is_subset]

        index_id = int(type_str[0])
        self._Q, self._Q_inverted = Searcher.index_list[index_id]
        self._token_func = Searcher.index_token_func_list[index_id]
        condition_id = int(type_str[1])
        self._condition_func = condition_funcs[condition_id]
        self._score_funcs_on = [score_funcs[i] 
                                for i, ch in enumerate(type_str[2:]) 
                                if ch == '1']
        #sum_ql = 0
        #for d in self._Q:
        #    sum_ql += len(d['tokens'])
        #self._avg_ql = float(sum_ql) / len(self._Q)

    def tf(self, cid):
        k = 2.0
        return (self._Q[cid]['freq'] * (k + 1) / 
                (self._Q[cid]['freq'] + k))

    def idf(self, token):
        N = len(self._Q)
        df = len(self._Q_inverted[token])
        return math.log(float(N) / df + 1, 2)

    def bm25(self, cid):
        tf = self.tf(cid)
        c_tokens = self._Q[cid]['tokens']
        n_set = set(c_tokens).intersection(self._q_tokens)
        return tf * sum([self.idf(t) for t in n_set])

    def jaccard(self, cid):
        c_tokens = set(self._Q[cid]['tokens'])
        n_set = c_tokens.intersection(self._q_tokens)
        u_set = c_tokens.union(self._q_tokens)
        return float(len(n_set)) / len(u_set)

    def jaccard_char(self, cid):
        c = set(self._Q[cid]['query'])
        n_set = c.intersection(self._q)
        u_set = c.union(self._q)
        return float(len(n_set)) / len(u_set)
        
    def is_subset(self, cid):
        c_tokens = set(self._Q[cid]['tokens'])
        return c_tokens.issubset(self._q_tokens)

    def is_eligible(self, cid):
        c = self._Q[cid]['query']
        c_tokens = set(self._Q[cid]['tokens'])
        c_clean = "".join(c_tokens).strip('_')
        if len(c_clean) <= 2:
            return False
        elif c.isdigit():
            return False
        elif c in stop_subs:
            return False
        elif len(self._q) == 4 and len(c) == 3:
            return False
        else:
            return True
        #return (len("".join(c_tokens).strip('_')) > 2 and
        #        not c.isdigit() and c not in stop_subs and
        #        not (len(self._q) == 4 and len(c) == 3))

    def search(self, q):
        self._q = normalize_query(q)
        self._q_tokens = self._token_func(self._q)
        
        # get candidate query ids
        cid_set = set()
        for token in self._q_tokens:
            for cid in self._Q_inverted.get(token, []):
                if cid not in cid_set:
                    if self._condition_func(cid):
                        cid_set.add(cid)

        # compute ranking scores
        scores = []
        for cid in cid_set:
            score = 1.0
            for func in self._score_funcs_on:
                score *= func(cid)
            scores.append(score)

        # rank by score and return top_n queries
        ranked_cids = sorted(zip(cid_set, scores),
                             key=lambda p:p[1], 
                             reverse=True)
        return [(self._Q[cid]['query'], score) 
                for cid, score in ranked_cids[:1] if self.is_eligible(cid)]


def main(query_file):
    searcher_list = [Searcher('1110100'), # gram similarity 
                     Searcher('0010100'), # cut similarity
                     Searcher('0210100'), ] # cut subset

    reader = codecs.open(query_file, 'r', 'utf-8')
    writer = codecs.open(query_file + ".search", 'w', 'utf-8')
    for line in reader:
        q = line.strip()
        print q
        writer.write("[%s]\n" % q)

        for sub in stop_subs[:1]:
            pos = q.find(sub)
            if pos != -1:
                before = q[:pos]
                after = q[pos+len(sub):]
                break
        if pos != -1:
            writer.write(before + after + '\n')

        for se in searcher_list:
            writer.write('-' * 14 + '\n')
            for cand, score in se.search(q):
                writer.write(("%g" % score).ljust(14))
                writer.write(cand + '\n')
        writer.write('\n\n')
    reader.close()
    writer.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: python search.py query_file"
        sys.exit(1)
    main(sys.argv[1])

