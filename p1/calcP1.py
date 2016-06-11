from __future__ import division
import sys

def main(args):
    for arg in args:
       # print arg
        Qarray =[];

        with open(arg) as resfile:
            res = resfile.read().splitlines()
            for r in res:
                rSplit= r.split()
                rank = rSplit[3]
                docname = rSplit[2]
                if (rank == "1"):
                    Qarray.append(docname)

        matches =0;
        with open('qrels.txt') as qfile:
            qrels = qfile.read().splitlines()
            for qrel in qrels:
                qrelSplit = qrel.split()
                if (qrelSplit[3] =="1"):
                    name = qrelSplit[2]
                    if(name in Qarray ):
                        matches +=1
        p1=matches /len(Qarray) 
        print p1
 

if __name__ == "__main__":
    main(sys.argv[1:])
    


