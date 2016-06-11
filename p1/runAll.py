import subprocess
import os
import csv


# Creates the res files using IndriRunQuery on query parameter files
def createRes():
    for filename in os.listdir("./querypar/forreport"):
        print filename
        filenameSplit = filename.split("_")
        dataset = filenameSplit[1]
        size = filenameSplit[2]
        mu = filenameSplit[3]
        print dataset
        command = "IndriRunQuery querypar/" + dataset +"/" + filename +  " > results/results_" +dataset+ "_" + size + "_" + mu
        print command
        os.system(command)


# Do the reranking
def rerank():
    for filename in os.listdir("./results"):
        filenameSplit = filename.split("_")
        dataset = filenameSplit[1]
        outname = filenameSplit[2] + "/" + filenameSplit[1] + "/"+filenameSplit[1] + "_" + filenameSplit[2] + "_" + filenameSplit[3].split(".")[0]  
        command ="./rerank/rerank ../indexpar/IR2016-index-"+ dataset+ " results/" + filename + " " + outname
        print command
        os.system(command)


def strP(str1, str2):
    percentage = int(round(100 - ((float(str1) / float(str2)) * 100)))
    if percentage < 0:
        return "(+" + str(abs(percentage)) + "\%)"
    else:
        return "(-" + str(percentage) + "\%)"


# Evaluate the results using trec_eval
def eval():
    rankdir = "./reranked"
    dirs = os.listdir(rankdir)
    methods = {'R1R2': '+R1+R2', 'R1': "+R1", 'R2': "+R2", '1000.txt': "LM"}
    for d in dirs:
        with open("./csv/N" + d + ".csv", "w") as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(["corp", "meth", "mmr", "pone", "pfive", "ndcg"])
            for sd in os.listdir(rankdir + "/" + d):
                corp = sd.strip()
                fileN = os.listdir(rankdir + "/" + d + "/" + sd)
                fileN.sort()
                fileN = reversed(fileN)
                for filename in fileN:
                    rerankedfile = "reranked/" + d + "/" + sd + "/" + filename
                    command = "python2.7 calcP1.py " + rerankedfile
                    p1 = subprocess.check_output(command, shell=True)
                    command = "trec_eval qrels.txt " + rerankedfile
                    res = subprocess.check_output(command, shell=True)
                    p1 = "{0:.4f}".format(float(p1.strip()))
                    p5 = res.splitlines()[21].split("all")[1].strip()
                    mmr = res.splitlines()[9].split("all")[1].strip()
                    command = "trec_eval -m ndcg_cut  qrels.txt " + rerankedfile
                    res = subprocess.check_output(command, shell=True).splitlines()[0]
                    ndcg_cut_5 = res.split()[2].strip()

#                   writer.writerow(["corp","meth","mmr", "pone" , "pfive", "ndcg"])
                    writer.writerow([corp,methods[filename.split("_")[3]], mmr, p1, p5, ndcg_cut_5])
                    if len(corp):
                        baseline = [mmr, p1, p5, ndcg_cut_5]

                    else:
                        writer.writerow(["", "", strP(mmr, baseline[0]), strP(p1, baseline[1]), strP(p5, baseline[2]), strP(ndcg_cut_5, baseline[3]) ])
                    corp = ""


def main():
    createRes()
    rerank()
    eval()


if __name__ == "__main__":
    main()
