import subprocess
import time
import os

datasets=["fbis", "ft", "latimes" ] 

for d in datasets:

	for filename in os.listdir("/home/peden/Dropbox/UNI/master/IR/IR2016/querypar/" + d ):
		print filename

	#for mu in mus:
		command ="IndriRunQuery /home/peden/Dropbox/UNI/master/IR/IR2016/querypar/" + d + "/"+ filename ;

		f = open('tempres.txt', 'w', 0)
		queries = subprocess.check_output(command,shell=True)
		f.write(queries)
		f.flush
		f.close

		command ="trec_eval qrels.txt tempres.txt" ;


		print subprocess.check_output(command,shell=True).splitlines()[21].split("all")[1]
		os.remove('tempres.txt')
	#
