# -*- coding: utf-8 -*- 

"""implentation of the clustering algorithm proposed in
"Context-Aware Query Suggestion by Mining Click-Through and Sesstion Data"

@author: yan9liu@gmail.com
"""


import ctypes
import math
import sys
import codecs


class Utility(object):

    # import segmentor
    seg = ctypes.CDLL("libprobseg.so")
    seg_init = seg.prob_init()
    seg_degree = seg.set_seg_granul(seg_init, True)

    # only true for l2 normalized vec
    max_euclidean_distance = math.sqrt(2)

    @staticmethod
    def cut(str):
        result = ' ' * 1000
        Utility.seg.prob_seg(Utility.seg_init, str.encode('gb18030'), result)
        tokens = result.decode('gb18030').strip().strip('\0').split()
        return set(tokens)

    @staticmethod
    def l2_normalize(d):
        total = sum([v * v for v in d.values()])
        sqrt = math.sqrt(total)
        for k in d:
            d[k] /= sqrt

    @staticmethod
    def euclidean_distance(d1, d2):
        dist = 0.0
        for k in set(d1.keys()).union(d2.keys()):
            diff = d1.get(k, 0.0)
            diff -= d2.get(k, 0.0)
            dist += diff ** 2
        return math.sqrt(dist)

    @staticmethod
    def diameter(d_list):
        count = 0
        total = 0.0
        for i in range(len(d_list)-1):
            for j in range(i+1, len(d_list)):
                count += 1
                dist = Utility.euclidean_distance(d_list[i], d_list[j])
                total += dist ** 2
        total /= count
        return math.sqrt(total)

    @staticmethod
    def centroid(d_list):
        centroid = {}
        for d in d_list:
            for k in d:
                centroid[k] = centroid.get(k, 0.0) + d[k]
        for k in centroid:
            centroid[k] /= len(d_list) * 1.0
        return centroid


min_click_freq = 5
min_click_weight = 0.1
Q = []  # index = qid

def load(reader):
    """
    data format:
    query\tfreq|pid\tpos\tfreq\tpos\tfreq|pid\tpos\tfreq\n

    for example:
    会计从业证中华会计网	1|23525084	12	1
    会计从业资料2015吉林	1|1126724309	3	1|1253514637	22	1
    会计从业资格 云南	1|1066085507	4	1	0	1
    """
    for line in reader:
        a = line.strip().split('|')
        query, freq_q_str = a[0].split('\t')
        freq_q = int(freq_q_str)

        click_dict = {}
        for i in range(1, len(a)):
            a_i = a[i].split('\t')
            pid = a_i[0]
            freq_p = 0
            # use step 2 to skip pos
            for j in range(2, len(a_i), 2):
                freq_p += int(a_i[j])
            if freq_p <= min_click_freq:
                continue
            click_dict[pid] = freq_p
        if not click_dict:
            continue
        Utility.l2_normalize(click_dict)
        for pid, weight in click_dict.items():
            if weight <= min_click_weight:
                del click_dict[pid]
        if not click_dict:
            continue
        Utility.l2_normalize(click_dict)

        tokens = Utility.cut(query)
        token_dict = dict.fromkeys(tokens, 1)
        Utility.l2_normalize(token_dict)

        Q.append({'query':query,
                  'freq':freq_q,
                  'clicks':click_dict,
                  'tokens':token_dict})

class Cluster(object):

    max_diameter = None

    def __init__(self, qids, sim_field):
        self._qids = qids
        self._sim_field = sim_field

        # index = cid 
        # [[qid, qid ...], [qid, ...], ...]
        self._clusters = []
        self._centroids = []

        # for fast finding cluster candidates to be merged
        # {pid:set([cid, cid, ...]), ...}
        self._pid_cids_map = {}

    def cluster(self):
        for qid in self._qids:
            # get cluster candidates
            cids = []
            for pid in Q[qid][self._sim_field]:
                cids.extend(self._pid_cids_map.get(pid, []))

            if cids:
                # find closest cluster
                min_dist = Utility.max_euclidean_distance
                # min_cid = None
                for cid in set(cids):
                    dist = Utility.euclidean_distance(Q[qid][self._sim_field],
                                                      self._centroids[cid])
                    if dist < min_dist:
                        min_dist, min_cid = dist, cid
                c_update = self._clusters[min_cid] + [qid]
                c_update_sim_field = [Q[i][self._sim_field] for i in c_update]
                
                if Utility.diameter(c_update_sim_field) <= Cluster.max_diameter: 
                    # update the cluster with min_cid
                    self._clusters[min_cid] = c_update 
                    self._centroids[min_cid] = \
                        Utility.centroid(c_update_sim_field)
                    for pid in Q[qid][self._sim_field]:
                        if pid not in self._pid_cids_map:
                            self._pid_cids_map[pid] = set()
                        self._pid_cids_map[pid].add(min_cid)
                    continue

            # a new cluster. 
            # either "not cids"
            # or "not (diameter <= Cluster.D_max)" can arrive here
            self._clusters.append([qid])
            self._centroids.append(Q[qid][self._sim_field])

            new_cid = len(self._clusters) - 1
            for pid in Q[qid][self._sim_field]:
                if pid not in self._pid_cids_map:
                    self._pid_cids_map[pid] = set()
                self._pid_cids_map[pid].add(new_cid)
        
        self._clusters.sort(key=lambda c:len(c), reverse=True)
        for c in self._clusters:
            c.sort(key=lambda qid:Q[qid]['freq'], reverse=True)

    def get_clusters(self):
        return self._clusters

    def dump(self, writer, label_fmt):
        for cid, cluster in enumerate(self._clusters):
            writer.write(label_fmt % cid)
            for qid in cluster:
                writer.write("%s\t%d\n" % (Q[qid]['query'], Q[qid]['freq']))
        return len(self._clusters)

    @staticmethod
    def main(in_file):
        with codecs.open(in_file, 'r', 'utf-8') as reader:
            print "loading data ..."
            load(reader)
            print "done."

        max_d_list = [ i * 0.1 for i in range(1, 11)]
        for max_c in max_d_list:
            print "\nmax_c = %.1f" % max_c
            Cluster.max_diameter = max_c
            cluster = Cluster(qids=range(len(Q)), sim_field='clicks')
            print "clustering & dumping ..."
            cluster.cluster()
            out_file = "%s_cluster2_Dmax%g" % (in_file, max_c)
            with codecs.open(out_file, 'w', 'utf-8') as writer:
                cluster.dump(writer, label_fmt="[cluster %d]\n")
            print "done."
            print "#clusters = %d" % len(cluster.get_clusters())
            
            for max_g in max_d_list:
                print "\tmax_g = %.1f" % max_g
                Cluster.max_diameter = max_g
                group_count = 0
                out_file2 = "%s_group_Dmax%g" % (out_file, max_g)
                print "\tgrouping & dumping ..."
                with codecs.open(out_file2, 'w', 'utf-8') as writer:
                    for cid, qids in enumerate(cluster.get_clusters()):
                        writer.write("[cluster %d]\n" % cid)
                        grouper = Cluster(qids, sim_field='tokens')
                        grouper.cluster()
                        group_count += grouper.dump(
                            writer, label_fmt="----------group %d----------\n")
                        writer.write('\n')
                print "\tdone."
                print "\t#groups = %d" % group_count

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: python co_click_v2.py file"
        sys.exit(1)
    Cluster.main(sys.argv[1])