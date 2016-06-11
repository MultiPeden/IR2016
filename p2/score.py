from __future__ import division
import sys
import json
import math
from scipy.stats.stats import pearsonr
from scipy.stats.stats import spearmanr
import numpy as np
import itertools
import subprocess
from collections import OrderedDict
from collections import Counter
from sets import Set
import csv



class document():
    def __init__(self, docName, rank, score):
        self.docName = docName
        self.rank = int(rank)
        self.score = float(score)


class Qinfo():
    def __init__(self, std, MAD, trecScore):
        self.std = float(std)
        self.MAD = float(MAD)
        self.trecScore = float(trecScore)



def getTopPercentage(doclist, percentage, N):
    scores = doclist[0].score
    minScore = scores * (percentage / 100)
    index = 0
    for d in doclist[0:N]:
        if d.score < minScore:
            break
        index += 1

    return index


def getStd_MAD(qnr, index):
    #std
    query = Queries[qnr][0:index]
    scores = [doc.score for doc in query]
    std_score = np.std(scores)


    # MAD
    med = np.median(scores)
    MAD = np.median(np.abs(scores - med))

    return (std_score, MAD)


def readQueries(path):
    Queries = OrderedDict()
    print path
    doclist = []
    oldQ = "301"
    with open(path, "r") as file:
        for line in file.readlines():
            qid, _, docName, rank, score, _ = line.split()
            if oldQ != qid:
                
                Queries[oldQ] = doclist            
                oldQ = qid
                doclist = []
            doclist.append(document(docName, rank, score))
        Queries[oldQ] = doclist
    return Queries


def getResText(qnr, index):
    docs = Queries[qnr][0:index]
    string = ""
    for d in docs:
        string += "%s Q0 %s %d %.4f 2016 \n" % (qnr, d.docName, d.rank, d.score)
    return string


def CreateTempResFile(percentage, N):
    resString = ""
    for Qnr, dlist in Queries.iteritems():

        index = getTopPercentage(Queries[Qnr], percentage, N)
        std , MAD = getStd_MAD(Qnr, index)

        QueriesRes[Qnr] = Qinfo(std, MAD, 0)
        resString += getResText(Qnr, index)

    with open("tempRes.txt", "w") as file:
        file.write(resString)
        file.close


def getTrecEval(measure, index):
    command = "trec_eval -q ./qrels.txt tempRes.txt"
    trec_evals = subprocess.check_output(command, shell=True)
    trec_evals = trec_evals.split("num_ret")[1:]

    i = 0
    for Qnr, dlist in Queries.iteritems():
        # get trec_eval measures for i'th query
        trec_eval = trec_evals[i]
       # get the measure specified in the measure var
        trec_eval = trec_eval.split(measure)[1].split()[1]
        QueriesRes[Qnr].trecScore = float(trec_eval)
        i += 1



def stdMeasures(index, QueryTerms, totalDocs):
    QueryTerms = QueryTerms.split()
    Qlen = len(QueryTerms) 
    QueryTermsx = Counter(QueryTerms).items()
    IDFraws = 0
    scs = 0
    distinctDocs = Set()

    for term , termCount in QueryTermsx:
        command = "dumpindex " + index + " t " + term
        termInfo = subprocess.check_output(command, shell=True)
        # read lines
        termInfo = termInfo.split('\n')
        # extract header
        termheader = termInfo[0].split()
        # extract documents
        termInDocs = termInfo[1:-1]

        # IDF - Inverse document frequency
        #  # of lines in dumpindex term funtion -1, gives
        #  the number of documents contaning the term in the collection
        termInQueries = len(termInDocs)
      
        IDFraw = math.log((totalDocs / (1+ termInQueries)))
        IDFraws += termCount * IDFraw

        # SCS - simplified clarify score
        # tf(qi,Q) / |Q|
        pqQ = termCount / Qlen
        # tf(qi,V) / |V|
        pq = float(termheader[2])  / float(termheader[3])
        if pq != 0:
            sc = pqQ * math.log((pqQ / pq),2)
            scs += sc

        for doc in termInDocs:
            docNo = doc.split()[0]
            distinctDocs.add(docNo)

    # qs - query scope
    qs = - math.log((len(distinctDocs) / totalDocs))
    # IDFavg
    avgIDFraws = IDFraws / Qlen

    return (avgIDFraws, qs, scs)





def CalcCorrelation(percentage, N,  index):
    CreateTempResFile(percentage, N)
    getTrecEval(measure,  index)
    x = [res.std for Qnr, res in QueriesRes.iteritems()]
    y = [res.trecScore for Qnr, res in QueriesRes.iteritems()]
    std_p = pearsonr(x, y)[0]
    std_s = spearmanr(x, y)[0]
    x = [res.std / math.sqrt(len(Qterms[Qnr].split())) for Qnr, res in QueriesRes.iteritems()]
    std_n_p = pearsonr(x, y)[0]
    std_n_s = spearmanr(x, y)[0]
    x = [res.MAD for Qnr, res in QueriesRes.iteritems()]
    mad_p = pearsonr(x, y)[0]
    mad_s = spearmanr(x, y)[0]
    x = [res.MAD / math.sqrt(len(Qterms[Qnr].split())) for Qnr, res in QueriesRes.iteritems()]
    mad_n_p = pearsonr(x, y)[0]
    mad_n_s = spearmanr(x, y)[0]
    if debug:
        print "N", N, "----", "Percentage", percentage
        print "std pearson      ", std_p
        print "std spearman     ", std_s
        print "std norm pearson ", std_n_p
        print "std norm spearman", std_n_s
        print "MAD pearson      ", mad_p 
        print "MAD spearman     ", mad_s
        print "MAD norm pearson ", mad_n_p
        print "MAD norm spearman", mad_n_s
    return (std_p, std_s, std_n_p, std_n_s, mad_p,mad_s, mad_n_p, mad_n_s)


def stdPredictors(coll):

    command = "trec_eval -q ./qrels.txt ./res/" + col +"_res.txt"
    trec_evals = subprocess.check_output(command, shell=True)
    trec_evals = trec_evals.split("num_ret")[1:-1]

    trec_res = []
    for trec_eval in trec_evals:
        trec_eval = trec_eval.split(measure)[1].split()[1] 
        trec_res.append(float(trec_eval))

    avgIDFrawL, qsL, scsL =[],[],[] 

    for Qnr, dlist in Queries.iteritems():
        (avgIDFraws, qs, scs) = stdMeasures(index, Qterms[Qnr], totalDocs)
        avgIDFrawL.append(avgIDFraws)
        qsL.append(qs)
        scsL.append(scs)

    IDF_p = pearsonr(avgIDFrawL, trec_res)[0]
    IDF_s = spearmanr(avgIDFrawL, trec_res)[0]
    qs_p = pearsonr(qsL, trec_res)[0]
    qs_s = spearmanr(qsL, trec_res)[0]
    scs_p = pearsonr(scsL, trec_res)[0] 
    scs_s = spearmanr(scsL, trec_res)[0]

    if debug:
        print "avgIDF pearson   ", IDF_p
        print "avgIDF spearman  ", IDF_s
        print "qs     pearson   ", qs_p
        print "qs     spearman  ", qs_s
        print "scs    pearson   ", scs_p
        print "scs    spearman  ", scs_s
        print "\n\n"

    return (IDF_p, IDF_s, qs_p, qs_s, scs_p, scs_s)



debug = 0

Qterms = json.load(open("Queries.json"))
measures = ["P_10", "bpref"]
#measure = "bpref"
Ns = [20,50,100,200]
#percen = [10,30,50,70,90]
ps = [90,70,50,30,10]
collections = ["fbis", "ft", "latimes"]

#print len (Qterms)
#print Qterms


#for key, value in Qterms.iteritems() :
#    print key, value
for measure in measures:
    print "-------------------- " + measure + "----------------------"
    IDF_ps, IDF_ss, qs_ps, qs_ss, scs_ps, scs_ss = [], [],[],[],[],[]
    for col in collections: 
        print "COLLECTION" , col
        print "------------------------------------------"
        index = "../indexpar/IR2016-index-" + col
        Queries = readQueries("./res/" + col +"_res.txt")


        # get total number of docs in collection
        command = "dumpindex " + index + " s " 
        stats = subprocess.check_output(command, shell=True)
        totalDocs = int(stats.split("\n",2)[1].split()[1])


        (IDF_p, IDF_s, qs_p, qs_s, scs_p, scs_s) = stdPredictors(col)
        IDF_ps.append(IDF_p) 
        IDF_ss.append(IDF_s)
        qs_ps.append(qs_p)
        qs_ss.append(qs_s)
        scs_ps.append(scs_p)
        scs_ss.append(scs_s)


        for N in Ns:
            std_ps   = ["$\sigma (r)$"]
            std_ss   = ["$\sigma (\\rho)$"]
            std_n_ps = ["$n(\sigma) (r)$"]
            std_n_ss = ["$n(\sigma) (\\rho)$"]
            mad_ps   = ["$MAD (r)$"]
            mad_ss   = ["$MAD(\\rho)$"]
            mad_n_ps = ["$n(MAD) (r)$"]
            mad_n_ss = ["$n(MAD) (\\rho)$"]
            with open("./csv/" + measure +"/res" + str(N) +"-" + col + ".csv" , "w") as csvfile:
                writer = csv.writer(csvfile, delimiter=',')

                for p in ps:
                    QueriesRes = OrderedDict()
                    (std_p, std_s, std_n_p, std_n_s, mad_p, mad_s, mad_n_p, mad_n_s) = CalcCorrelation(p,N, index)

                    std_ps.append("{0:.3f}".format(std_p))
                    std_ss.append("{0:.3f}".format(std_s))
                    std_n_ps.append("{0:.3f}".format(std_n_p))
                    std_n_ss.append("{0:.3f}".format(std_n_s))
                    mad_ps.append("{0:.3f}".format(mad_p))
                    mad_ss.append("{0:.3f}".format(mad_s))
                    mad_n_ps.append("{0:.3f}".format(mad_n_p))
                    mad_n_ss.append("{0:.3f}".format(mad_n_s))
                writer.writerow(["cut-offs", "si"+str(ps[0]), "si"+str(ps[1]), "si"+str(ps[2]), "si"+str(ps[3]), "si"+str(ps[4])])
                writer.writerow(std_ps)
                writer.writerow(std_ss)
                writer.writerow(std_n_ps)
                writer.writerow(std_n_ss)
                writer.writerow(mad_ps)
                writer.writerow(mad_ss)
                writer.writerow(mad_n_ps)
                writer.writerow(mad_n_ss)

    with open("./csv/" + measure +"/pred_avg.csv" , "w") as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(["pred","avgr","avgp"])
        writer.writerow(["$idf_{avg}$","{0:.3f}".format(np.average(IDF_ps)),"{0:.3f}".format(np.average(IDF_ss))])
        writer.writerow(["qs","{0:.3f}".format(np.average(qs_ps)),"{0:.3f}".format(np.average(qs_ss))])
        writer.writerow(["SCS","{0:.3f}".format(np.average(scs_ps)),"{0:.3f}".format(np.average(scs_ss))])

    with open("./csv/" + measure + "/pred_median.csv" , "w") as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(["pred","meanr","meanp"])
        writer.writerow(["$idf_{avg}$","{0:.3f}".format(np.median(IDF_ps)),"{0:.3f}".format(np.median(IDF_ss))])
        writer.writerow(["qs","{0:.3f}".format(np.median(qs_ps)),"{0:.3f}".format(np.median(qs_ss))])
        writer.writerow(["SCS","{0:.3f}".format(np.median(scs_ps)),"{0:.3f}".format(np.median(scs_ss))])


