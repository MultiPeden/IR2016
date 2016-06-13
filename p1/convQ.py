from __future__ import division
import  os
import re




out2 = open('queriesReRank.txt', 'w')
stopstring = ""
with open('stopwords.txt') as f:
      stoppers = f.read().splitlines()
      for stop in stoppers:
            stopstring +=  "<word>"+stop+"</word>\n"
      
datasets=["fbis", "ft", "latimes" ] 
numberRes=[20,50];
mus=[1000,1500,2000,2500,3000];
first = 1
avglen = 0

for d in datasets:
    for numd in numberRes: 
        for mu in mus: 
            filename = "querypar/" + d + "/queries_" + d + "_" + str(numd)+ "_" + str(mu) + ".txt"
            out = open(filename, 'w')
            out.write("""<parameters>
            <index>../indexpar/IR2016-index-""" + d + """</index>
            <runID>2016</runID>
            <trecFormat>true</trecFormat>
            <count>""" + str(numd) + """</count>
            <rule>method:dir,mu:""" + str(mu) + """</rule> \n""")

            files =  ["queries/topics.301-350","queries/topics.351-400","queries/topics.401-450"]
            for fname in files:
                  f = open(fname,'r')
                  queries = f.read().split("<top>")
                  for q in queries[1:]:
                        number = q.split("Number: ")[1].split("\n")[0].strip()
                        text = q.split("<title> ")[1].split("\n")[0].lower() 
                        text = text.replace("'s","")
                        text = re.sub(r'[^\w]', ' ', text)
                        text = " ".join(text.split())
                        if first:
                            textWOstop =  ' '.join([word for word in text.split() if word not in stoppers])
                            textWOstop = " ".join(textWOstop.split())
                            out2.write(number + "," + textWOstop + "\n")
                            avglen += len(textWOstop.split())
                        string = "<query>\n<number>"
                        string += number + "</number>\n"
                        string += "<text>" + text + "</text>\n"
                        string += "</query>\n"

                        out.write(string)
            out.write("""<stemmer>
                <name>krovetz</name>
                </stemmer>
                <stopper>
                 """ +  stopstring + """
                </stopper>\n""");

            out.write("</parameters>")
            first = 0