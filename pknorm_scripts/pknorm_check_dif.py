#module load python/2.7
import os
from subprocess import call
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm, nbinom

################################################################################################
### read 2d array
def read2d_array(filename,dtype_used):
	import numpy as np
	data=open(filename,'r')
	data0=[]
	for records in data:
		tmp = [x.strip() for x in records.split('\t')]
		data0.append(tmp)
	data0 = np.array(data0,dtype=dtype_used)
	data.close()
	return data0

################################################################################################
### write 2d matrix
def write2d_array(array,output):
	r1=open(output,'w')
	for records in array:
		for i in range(0,len(records)-1):
			r1.write(str(records[i])+'\t')
		r1.write(str(records[len(records)-1])+'\n')
	r1.close()

################################################################################################
### p-value adjust (fdr & bonferroni)
def p_adjust(pvalue, method):
	p = pvalue
	n = len(p)
	p0 = np.copy(p, order='K')
	nna = np.isnan(p)
	p = p[~nna]
	lp = len(p)
	if method == "bonferroni":
		p0[~nna] = np.fmin(1, lp * p)
	elif method == "fdr":
		i = np.arange(lp, 0, -1)
		o = (np.argsort(p))[::-1]
		ro = np.argsort(o)
		p0[~nna] = np.fmin(1, np.minimum.accumulate((p[o]/i*lp)))[ro]
	else:
		print "Method is not implemented"
		p0 = None
	return p0

################################################################################################
### NewtonRaphsonMethod
def NewtonRaphsonMethod(sig1_pk,sig1_bg, sig2_pk,sig2_bg, A,B, moment, converge_thresh, numIterations):
	sig1_pk_mean = np.mean(sig1_pk**moment)
	sig1_bg_mean = np.mean(sig1_bg**moment)

	for i in range(0, numIterations):
		fb = sig1_bg_mean * np.mean(sig2_pk**(moment*B)) - sig1_pk_mean * np.mean(sig2_bg**(moment*B))
		dfb = moment * sig1_bg_mean * np.mean(np.log(sig2_pk) * sig2_pk**(moment*B)) - moment * sig1_pk_mean * np.mean(np.log(sig2_bg) * sig2_bg**(moment*B))

		### next step
		B = B - fb / dfb	
		A = sig1_bg_mean / np.mean(sig2_bg**(moment*B))

		print("Iteration %d | dFB: %f" % (i, dfb))
		print([A,B])

		last_AB = [A, B]

		if abs(fb / dfb) < converge_thresh:
			print('converged!')
			used_AB = [A, B]
			break

	if abs(fb / dfb) >= converge_thresh:
		print('NOT converged...')
		used_AB = last_AB

	print('used: ')
	print(used_AB)
	return np.array(used_AB)

################################################################################################
### Negative binomial p-value
def nb_cpf(signal_vec):
	sig_mean = np.mean(signal_vec)
	sig_var = np.var(signal_vec)
	sig_prob = sig_mean / sig_var
	if sig_prob < 0.1:
		sig_prob = 0.1
	elif sig_prob > 0.9:
		sig_prob = 0.9
	sig_size = sig_mean * sig_prob / (1-sig_prob)
	nbp = 1-nbinom.cdf(signal_vec, sig_size, sig_prob)
	return nbp

################################################################################################
### PKnorm
def pknorm_check_dif(sig1_wg_raw, sig2_wg_raw, fdr_thresh, script_folder, p_method):
	sig1_output_name = sig1_wg_raw.split('.')[0]
	sig2_output_name = sig2_wg_raw.split('.')[0]

	### read whole genome signals
	sig1 = read2d_array(sig1_wg_raw, float)
	sig2 = read2d_array(sig2_wg_raw, float)
	
	### read whole genome binary label
	if p_method == 'nb':
		call('Rscript ' + script_folder + 'nbp_0326.R ' + sig1_wg_raw + ' ' + sig1_wg_raw + '.nbp.txt', shell=True)
		sig1_p = read2d_array(sig1_wg_raw + '.nbp.txt', float)
		sig1_z_p_fdr = p_adjust(sig1_p, 'fdr')
		sig1_binary = sig1_z_p_fdr < fdr_thresh
	elif p_method == 'z':
		sig1_z_p_fdr = p_adjust(1 - norm.cdf((sig1 - np.mean(sig1))/ np.std(sig1)), 'fdr')
		sig1_binary = sig1_z_p_fdr < fdr_thresh

	sig1_pk_num = np.sum(sig1_binary)

	print(sum(sig1_binary))
	print(sig1_pk_num)

	if p_method == 'nb':
		call('Rscript ' + script_folder + 'nbp_0326.R ' + sig2_wg_raw + ' ' + sig2_wg_raw + '.nbp.txt', shell=True)
		sig2_p = read2d_array(sig2_wg_raw + '.nbp.txt', float)
		sig2_z_p_fdr = p_adjust(sig2_p, 'fdr')
		sig2_binary = sig2_z_p_fdr < fdr_thresh
	elif p_method == 'z':
		sig2_z_p_fdr = p_adjust(1 - norm.cdf((sig2 - np.mean(sig2))/ np.std(sig2)), 'fdr')
		sig2_binary = sig2_z_p_fdr < fdr_thresh

	sig2_pk_num = np.sum(sig2_binary)

	print(sum(sig2_binary))
	print(sig2_pk_num)

	### peak region (both != 0 in sig1 & sig2)
	peak_binary = (sig1_binary[:,0] & sig2_binary[:,0])
	print(np.sum(peak_binary))

	### background region (both == 0 in sig1 & sig2)
	bg_binary = ~(sig1_binary[:,0] | sig2_binary[:,0])
	print(np.sum(bg_binary))

	sig1_cpk = sig1[peak_binary,0]
	sig2_cpk = sig2[peak_binary,0]

	cpk_table = np.concatenate((sig1_cpk, sig2_cpk), axis=1)
	write2d_array(cpk_table, sig1_output_name+'cpk_table.txt')

############################################################################

import getopt
import sys
def main(argv):
	try:
		opts, args = getopt.getopt(argv,"hr:t:f:s:p:")
	except getopt.GetoptError:
		print 'time python pknorm_check_dif.py -r reference_signal_track.txt -t target_signal_track.txt -m moment -i initial_B -f fdrthresh -n plotpoints_num -l rank_lim -a upperlimit -b lowerlimit -s script_folder-p p-value_method'
		sys.exit(2)

	for opt,arg in opts:
		if opt=="-h":
			print 'time python pknorm_check_dif.py -r reference_signal_track.txt -t target_signal_track.txt -m moment -i initial_B -f fdrthresh -n plotpoints_num -l rank_lim -a upperlimit -b lowerlimit -s script_folder -p p-value_method'		
		elif opt=="-r":
			sig1_wg_raw=str(arg.strip())				
		elif opt=="-t":
			sig2_wg_raw=str(arg.strip())
		elif opt=="-f":
			fdr_thresh=float(arg.strip())
		elif opt=="-s":
			script_folder=str(arg.strip())
		elif opt=="-p":
			p_method=str(arg.strip())

	pknorm_check_dif(sig1_wg_raw, sig2_wg_raw, fdr_thresh, script_folder, p_method)

if __name__=="__main__":
	main(sys.argv[1:])

