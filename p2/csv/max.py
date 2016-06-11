import os
from glob import glob
import csv
import numpy as np


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

names = {0: '90\%', 1 : "70\%", 2 : '50\%', 3 : "30\%", 4: "10\%" }
N = [20,50,100,200]
paths = glob('*/')
for p in paths:
    measures=[]
    values=[]
    for n in N:
        measures_N=[]
        values_N=[]
        for file in glob(p + "res*" + str(n) + "-*.csv"):
            with open(file, "r") as infile:
                reader = csv.reader(infile, delimiter=',')
                measures_file = []
                values_file = []
                for row in reader:
                    x = [float(ent) for ent in row if is_number(ent)]
                    if x:
                        max_v = max(x)
                        ind = np.argmax(x)
                        measures_file.append(row[0][:-1] + "_{" +names[ind] +"}$")
                        values_file.append(max_v)
                max_v = max(values_file)
                ind = np.argmax(x)
                measures_N.append(measures_file[ind])
                values_N.append(max_v)
        measures.append(measures_N[np.argmax(values_N)])
        values.append(max(values_N))
    with open("max_" + p[:-1] +".csv", 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["N=" + str(N[0]),"N=" + str(N[1]),"N=" + str(N[2]),"N=" + str(N[3])])    
        writer.writerow(measures)
        writer.writerow(values)
    csvfile.close()

