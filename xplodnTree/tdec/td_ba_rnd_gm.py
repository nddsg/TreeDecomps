#!/usr/bin/env python
__version__="0.1.0"

# ToDo:
# [] process mult dimacs.trees to hrg

import sys
import math
import numpy as np
import traceback
import argparse
import os
from glob import glob
import networkx as nx
import pandas as pd
from tdec.PHRG import graph_checks
import subprocess
import math
import itertools
import tdec.graph_sampler as gs
import platform
from itertools import combinations
from collections import defaultdict
from tdec.arbolera import jacc_dist_for_pair_dfrms
import pprint as pp
import tdec.isomorph_interxn as isoint

#_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~_~#
def get_parser ():
	parser = argparse.ArgumentParser(description='Random graphs (BA graph model). --clqs is used when'\
			'.bz2 files are already computed given a path with wild card. Example: `python '\
			'itd_rndGraphs.py --clqs`')
	parser.add_argument('--etd', action='store_true', default=0, required=0,help="Edgelist to Dimacs")
	parser.add_argument('--ctrl',action='store_true',default=0,required=0,help="Control given --orig")
	parser.add_argument('--clqs', action='store_true',default=0, required=0, help="tree objs 2 hrgCT")
	parser.add_argument('--bam', action='store_true',	default=0, required=0,help="Barabasi-Albert")
	parser.add_argument('--tr', nargs=1, required=False, help="indiv. bz2 production rules.")
	parser.add_argument('--isom', nargs=1, required=0, help="isom test")
	parser.add_argument('--stacked', nargs=1, required=0, help="(grouped) stacked production rules.")
	parser.add_argument('--orig',nargs=1, required=False, help="edgelist input file")
	parser.add_argument('--version', action='version', version=__version__)

	return parser

def dimacs_nddgo_tree(dimacsfnm_lst, heuristic):
	'''
	dimacsfnm_lst => list of dimacs file names
	heuristic =====> list of variable elimination schemes to use
	returns: results - a list of tree files
	'''
	# print heuristic,dimacsfnm_lst
	results = []

	for dimacsfname in dimacsfnm_lst:
		
		if isinstance(dimacsfname, list): dimacsfname= dimacsfname[0]
		nddgoout = ""
		outfname = dimacsfname+"."+heuristic+".tree"
		if platform.system() == "Linux":
			args = ["bin/linux/serial_wis -f {} -nice -{} -w {}".format(dimacsfname, heuristic, outfname)]
		else:
			args = ["bin/mac/serial_wis -f {} -nice -{} -w {}".format(dimacsfname, heuristic, outfname)]
		while not nddgoout:
			popen = subprocess.Popen(args, stdout=subprocess.PIPE, shell=True)
			popen.wait()
			# output = popen.stdout.read()
			out, err = popen.communicate()
			nddgoout = out.split('\n')
		
		results.append(outfname)

	return results

def load_edgelist(gfname):
	import pandas as pd
	try:
		edglst = pd.read_csv(gfname, comment='%', delimiter='\t')
		# print edglst.shape
		if edglst.shape[1]==1: edglst = pd.read_csv(gfname, comment='%', delimiter="\s+")
	except Exception, e:
		print "EXCEPTION:",str(e)
		traceback.print_exc()
		sys.exit(1)

	if edglst.shape[1] == 3:
		edglst.columns = ['src', 'trg', 'wt']
	elif edglst.shape[1] == 4:
		edglst.columns = ['src', 'trg', 'wt','ts']
	else:
		edglst.columns = ['src', 'trg']
	g = nx.from_pandas_dataframe(edglst,source='src',target='trg')
	g.name = os.path.basename(gfname)
	return g


def nx_edges_to_nddgo_graph_sampling(graph, n, m, peo_h):
	G = graph
	if n is None and m is None: return
	# n = G.number_of_nodes()
	# m = G.number_of_edges()
	nbr_nodes = 256
	basefname = 'datasets/{}_{}'.format(G.name, peo_h)

	K = int(math.ceil(.25*G.number_of_nodes()/nbr_nodes))
	print "--", nbr_nodes, K, '--';

	for j,Gprime in enumerate(gs.rwr_sample(G, K, nbr_nodes)):
		# if gname is "":
		#	 # nx.write_edgelist(Gprime, '/tmp/sampled_subgraph_200_{}.tsv'.format(j), delimiter="\t", data=False)
		#	 gprime_lst.append(Gprime)
		# else:
		#	 # nx.write_edgelist(Gprime, '/tmp/{}{}.tsv'.format(gname, j), delimiter="\t", data=False)
		#	 gprime_lst.append(Gprime)
		# # print "...	files written: /tmp/{}{}.tsv".format(gname, j)


		edges = Gprime.edges()
		edges = [(int(e[0]), int(e[1])) for e in edges]
		df = pd.DataFrame(edges)
		df.sort_values(by=[0], inplace=True)

		ofname = basefname+"_{}.dimacs".format(j)

		with open(ofname, 'w') as f:
			f.write('c {}\n'.format(G.name))
			f.write('p edge\t{}\t{}\n'.format(n,m))
			# for e in df.iterrows():
			output_edges = lambda x: f.write("e\t{}\t{}\n".format(x[0], x[1]))
			df.apply(output_edges, axis=1)
		# f.write("e\t{}\t{}\n".format(e[0]+1,e[1]+1))
		if os.path.exists(ofname): print 'Wrote: {}'.format(ofname)

	return basefname

def edgelist_dimacs_graph(orig_graph, peo_h, prn_tw = False):
	fname = orig_graph
	gname = os.path.basename(fname).split(".")
	gname = sorted(gname,reverse=True, key=len)[0]

	if ".tar.bz2" in fname:
		from tdec.read_tarbz2 import read_tarbz2_file
		edglst = read_tarbz2_file(fname)
		df = pd.DataFrame(edglst,dtype=int)
		G = nx.from_pandas_dataframe(df,source=0, target=1)
	else:
		G = nx.read_edgelist(fname, comments="%", data=False, nodetype=int)
	# print "...",	G.number_of_nodes(), G.number_of_edges()
	# from numpy import max
	# print "...",	max(G.nodes()) ## to handle larger 300K+ nodes with much larger labels

	N = max(G.nodes())
	M = G.number_of_edges()
	# +++ Graph Checks
	if G is None: sys.exit(1)
	G.remove_edges_from(G.selfloop_edges())
	giant_nodes = max(nx.connected_component_subgraphs(G), key=len)
	G = nx.subgraph(G, giant_nodes)
	graph_checks(G)
	# --- graph checks

	G.name = gname

	# print "...",	G.number_of_nodes(), G.number_of_edges()
	if G.number_of_nodes() > 500 and not prn_tw:
		return (nx_edges_to_nddgo_graph_sampling(G, n=N, m=M, peo_h=peo_h), gname)
	else:
		return (nx_edges_to_nddgo_graph(G, n=N, m=M, varel=peo_h), gname)

def print_treewidth (in_dimacs, var_elim):
	nddgoout = ""
	if platform.system() == "Linux":
		args = ["bin/linux/serial_wis -f {} -nice -{} -width".format(in_dimacs, var_elim)]
	else:
		args = ["bin/mac/serial_wis -f {} -nice -{} -width".format(in_dimacs, var_elim)]
	while not nddgoout:
		popen = subprocess.Popen(args, stdout=subprocess.PIPE, shell=True)
		popen.wait()
		# output = popen.stdout.read()
		out, err = popen.communicate()
		nddgoout = out.split('\n')
	print nddgoout
	return nddgoout

def tree_decomposition_with_varelims(fnames, var_elims):
	'''
	fnames ====> list of dimacs file names
	var_elims => list of variable elimination schemes to use
	returns: 
	'''
	#	print "~~~~ tree_decomposition_with_varelims",'.'*10
	#	print type(fnames), type(var_elims)
	trees_files_d = {}#(list)
	for f in fnames:
		trees_files_d[f[0]]= [dimacs_nddgo_tree(f,td) for td in var_elims]
	#	for varel in var_elims:
	#		tree_files.append([dimacs_nddgo_tree([f], varel) for f in fnames])

	return trees_files_d

def convert_nx_gObjs_to_dimacs_gObjs(nx_gObjs):
	'''
	Take list of graphs and convert to dimacs
	'''
	dimacs_glst=[]
	for G in nx_gObjs:
		N = max(G.nodes())
		M = G.number_of_edges()
		# +++ Graph Checks
		if G is None: sys.exit(1)

		G.remove_edges_from(G.selfloop_edges())
		giant_nodes = max(nx.connected_component_subgraphs(G), key=len)
		G = nx.subgraph(G, giant_nodes)
		graph_checks(G)
		# --- graph checks
		if G.name is None:
			G.name = "synthG_{}_{}".format(N,M)
		
		from tdec.arbolera import nx_edges_to_nddgo_graph
		dimacs_glst.append(nx_edges_to_nddgo_graph(G, n=N, m=M, save_g=True))

	return dimacs_glst


def convert_dimacs_tree_objs_to_hrg_clique_trees(treeObjs):
	#	print '~~~~ convert_dimacs_tree_objs_to_hrg_clique_trees','~'*10
	results = []
	from dimacsTree2ProdRules import dimacs_td_ct

	for f in treeObjs:
		results.append(dimacs_td_ct(f, synthg=True))
	
	return results

def get_hrg_prod_rules(prules):
	'''
	These are production rules
	prules is list of bz2 files
	'''
	mdf = pd.DataFrame()#columns=['rnbr', 'lhs', 'rhs', 'pr'])
	for f in prules:
		df = pd.read_csv(f, index_col=0, compression='bz2')
		df.columns=['rnbr', 'lhs', 'rhs', 'pr']
		tname = os.path.basename(f).split(".")
		df['cate'] = ".".join(tname[:2])
		mdf = pd.concat([mdf,df])
	
	mdf[['rnbr', 'lhs', 'rhs', 'pr']].to_csv(f.split(".")[0]+".prs", sep="\t", header=False, index=False)
	return mdf

def get_isom_overlap_in_stacked_prod_rules(td_keys_lst, df ):
#	for p in [",".join(map(str, comb)) for comb in combinations(td_keys_lst, 2)]:
#		p p.split(',')
#		print df[df.cate == p[0]].head()
#		print df[df.cate == p[1]].head()
#		print

		
#		js = jacc_dist_for_pair_dfrms(stckd_df[stckd_df['cate']==p[0]],
#														 stckd_df[stckd_df['cate']==p[1]])
#		print js
#		print stckd_df[stckd_df['cate']==p[0]].head()
	for comb in combinations(td_keys_lst, 2):
		js = jacc_dist_for_pair_dfrms(df[df['cate']==comb[0]],
																	df[df['cate']==comb[1]])
		print "\t", js

def graph_stats_and_visuals(gobjs=None):
	"""
	graph stats & visuals
	:gobjs: input nx graph objects
	:return: 
	"""
	import matplotlib
	matplotlib.use('pdf')
	import matplotlib.pyplot as plt
	import matplotlib.pylab as pylab
	params = {'legend.fontsize': 'small',
						'figure.figsize': (1.6 * 7, 1.0 * 7),
						'axes.labelsize': 'small',
						'axes.titlesize': 'small',
						'xtick.labelsize': 'small',
						'ytick.labelsize': 'small'}
	pylab.rcParams.update(params)
	import matplotlib.gridspec as gridspec

	print "BA G(V,E)"
	if gobjs is None:
		gobjs = glob("datasets/synthG*.dimacs")
	dimacs_g = {}
	for fl in gobjs:
		with open(fl, 'r') as f:
			l=f.readline()
			l=f.readline().rstrip('\r\n')
			bn = os.path.basename(fl)
			dimacs_g[bn] = [int(x) for x in l.split()[-2:]]
		print "%d\t%s" %(dimacs_g[bn][0], dimacs_g[bn][1])

	print "BA Prod rules size"
	for k in dimacs_g.keys():
		fname = "ProdRules/"+k.split('.')[0]+".prs"
		f_sz = np.loadtxt(fname, delimiter="\t", dtype=str)
		print k, len(f_sz)
		



#def hrg_graph_gen_from_interxn(iso_interxn_df):
def trees_to_hrg_clq_trees():
	gname = 'synthG_15_60'
	files = glob('ProdRules/{}*.bz2'.format(gname))
	print files
	print '\tNbr of files:',len(files)
	prod_rules_lst = []
	
	stacked_pr_rules = get_hrg_prod_rules(files)
	print '\tSize of the df',len(stacked_pr_rules)
	df = stacked_pr_rules 
	gb = df.groupby(['cate']).groups.keys()
	print 'Jaccard Similarity'
	A = get_isom_overlap_in_stacked_prod_rules(gb, df)
	print A
	print 
	iso_union, iso_interx = isoint.isomorph_intersection_2dfstacked(df)
	iso_interx[[1,2,3,4]].to_csv('Results/{}_isom_interxn.tsv'.format(gname),
															 sep="\t", header=False, index=False)
	if os.path.exists('Results/{}_isom_interxn.tsv'.format(gname)):
		print 'Results/{}_isom_interxn.tsv'.format(gname)+' saved'


def isomorphic_test_on_stacked_prs(stacked_pr_rules_fname=None):
	in_fname = stacked_pr_rules_fname
	gname = os.path.basename(in_fname).split(".")[0]
	outfname = 'Results/{}_isom_itrxn.tsv'.format(gname)
	if os.path.exists(outfname):
		print '\tFile already exists:', outfname
	else:
		if in_fname is None:
			in_fname = "ProdRules/synthG_63_stcked_prs.tsv"
		else:
			stacked_df = pd.read_csv(in_fname,sep="\t",header=None)
			if len(stacked_df.columns) == 5: stacked_df.columns = ['rnbr', 'lhs','rhs', 'pr', 'cate']
			iso_union, iso_interx = isoint.isomorph_intersection_2dfstacked(stacked_df)
			
			iso_interx[[1,2,3,4]].to_csv(outfname, sep="\t", header=False, index=False)
			if os.path.exists(outfname):
				print "\t", 'Written:',outfname

	return outfname

def main (args_d):
	print "Hello"
	if args_d['ctrl']:
		orig = args_d['orig'][0]
		import subprocess
		from threading import Timer
		args = ("./exact_phrg.py",  "--orig", orig)
		proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		kill_proc = lambda p: p.kill()
		timer = Timer(600, kill_proc, [proc])
		try:
			timer.start()
			output, stderr = proc.communicate()
		finally:
			timer.cancel()
		print output
		gname = [x for x in os.path.basename(orig).split('.') if len(x) >3][0]
		fname = "ProdRules/" + gname + "_prs.tsv"
		print fname
		
		from td_rndGStats import graph_gen_isom_interxn
		graph_gen_isom_interxn(in_fname=fname, orig_el=orig) # gen graph from the prod rules
		sys.exit(0)

	if args_d['etd']:
		dimacs_gObjs = edgelist_to_dimacs(args)
		#~#
		#~# decompose the given graphs
		print '~~~~ And tree_decomposition_with_varelims'
		var_el_m = ['mcs','mind','minf','mmd','lexm','mcsm']
		trees_d = tree_decomposition_with_varelims(dimacs_gObjs, var_el_m)
		for k in trees_d.keys():
			print	'\t',k, "==>"
			for v in trees_d[k]: print "\t	", v

	if args_d['tr']: # / process trees and gen stacked PRS /
		files = glob('datasets/synthG_31_*.dimacs*.tree')
		files = glob("datasets/contact*dimacs*.tree")
		files = glob(args_d['tr'][0])
		convert_dimacs_tree_objs_to_hrg_clique_trees(files)

	if args_d['isom']:
		print '~~~~ isom intrxn from stacked df'
		files = glob(args_d['isom'][0])
		orig  = args_d['orig'][0] # reference path
		orig_bbn = [x for x in os.path.basename(orig).split(".") if len(x) > 3][0]
		print orig
		print orig_bbn
		
		files = glob("ProdRules/{}*stcked_prs.tsv".format(orig_bbn))
		for f in files:
			ba_vnbr = os.path.basename(f).split(".")[0]
			isom_ntrxn_f = isomorphic_test_on_stacked_prs(f)
			#from td_rndGStats import graph_gen_isom_interxn
			#graph_gen_isom_interxn(in_fname= isom_ntrxn_f, orig_el = orig)
	
	
	if args_d['stacked']:
		flspath = 'ProdRules/synthG_31_*.bz2'
		flspath = 'ProdRules/contact*.bz2'
		files = glob(args_d['stacked'][0])
		stckd = get_hrg_prod_rules(files)
		# ** stckd is a DataFrame **
		opath = args_d['stacked'][0].split("*")[0] + "_stcked_prs.tsv"
		stckd.to_csv(opath, sep="\t", header=False, index=False)
		if os.path.exists(opath): print "\tSaved ...", opath
		exit()
	
	
	

	if (args_d['bam']):
		print "~~~~ Groups of Random Graphs (BA):"
		n_nodes_set = [math.pow(2,x) for x in range(4,5,1)]
		ba_gObjs = [nx.barabasi_albert_graph(n, 3) for n in n_nodes_set]
		for g in ba_gObjs:
			print "\tG(V,E):", (g.number_of_nodes(), g.number_of_edges())
			out_el_fname = 'datasets/bar_alb_{}_exp3.tsv'.format(g.number_of_nodes())
			if not os.path.exists(out_el_fname): nx.write_edgelist(g, out_el_fname, delimiter="\t")
			print "\t",out_el_fname

		#~#
		#~# convert to dimacs graph
		print '~~~~ convert to_dimacs'
		print type(ba_gObjs[0])
		dimacs_gObjs = convert_nx_gObjs_to_dimacs_gObjs(ba_gObjs,)
		print "\t",type(dimacs_gObjs), dimacs_gObjs[0][0]

		#~#
		#~# decompose the given graphs
		print '~~~~ tree_decomposition_with_varelims'
		var_el_m = ['mcs','mind','minf','mmd','lexm','mcsm']
		trees_d = tree_decomposition_with_varelims(dimacs_gObjs, var_el_m)
		for k in trees_d.keys():
			print	'\t',k, "==>"
			for v in trees_d[k]: print "\t	", v

		#~#
		#~# dimacs tree to HRG clique tree
		print '~~~~ tree_objs_to_hrg_clique_trees'
		print '~~~~ prules.bz2 saved in ProdRules; individual files'
		pr_rules_d={}
		for k in trees_d.keys():
			pr_rules_d[k] = convert_dimacs_tree_objs_to_hrg_clique_trees(trees_d[k])
			print "\tCT:", len(pr_rules_d[k])


		#~#
		#~# get stacked HRG prod rules
		#~# - read sets of prod rules *.bz2
		print '~~~~ Stacked HRG get_hrg_prod_rules (stacked | prs)'
		st_prs_d = {}
		for k in pr_rules_d.keys():
			st_prs_d[k] = get_hrg_prod_rules(pr_rules_d[k])

		print'	', st_prs_d.keys()
		for k in st_prs_d.keys():
			df = pd.DataFrame(st_prs_d[k])
			outfname = "Results/"+os.path.basename(k).split('.')[0]+"stckd_prs.tsv"
			df[['rnbr','lhs','rhs','pr']].to_csv(outfname, header=False, index=False, sep="\t")

		#~#
		#~# get the isomophic overlap
		#	intxn_prod_rules = get_isom_overlap_in_stacked_prod_rules(stck_prod_rules)
		#	for nm	in sorted(stck_prod_rules.groupby(['cate']).groups.keys()):
		#		if os.path.exists('ProdRules/'+nm+'.bz2'):
		#			print '	ProdRules/'+nm+'.bz2'
		print '\n~~~~ get_isom_overlap_in_stacked_prod_rules'
		print '~~~~ output is Jaccard Sim Scores'
		for k in st_prs_d.keys():
			df = st_prs_d[k]
			gb = df.groupby(['cate']).groups.keys()
			get_isom_overlap_in_stacked_prod_rules(gb, df)


		#~#
		#~# get the isomophic overlap production rules subset
		#~# (two diff animals, not the same as the Jaccard Sim above)
		print '~~~~ isom intrxn from stacked df'
		for k in st_prs_d.keys():
			stacked_df = st_prs_d[k]
			iso_union, iso_interx = isoint.isomorph_intersection_2dfstacked(stacked_df)
			gname = os.path.basename(k).split(".")[0]
			iso_interx[[1,2,3,4]].to_csv('Results/{}_isom_interxn.tsv'.format(gname),
																				 sep="\t", header=False, index=False)
			if os.path.exists('Results/{}_isom_interxn.tsv'.format(gname)):
				print "\t", 'Written:','Results/{}_isom_interxn.tsv'.format(gname)

		#~#
		#~#	hrg_graph_gen_from_interxn(iso_interx[[1,2,3,4]])

def edgelist_to_dimacs(args):
	g =nx.read_edgelist(args['orig'][0], comments="%", data=False, nodetype=int)
	g.name = [x for x in os.path.basename(args['orig'][0]).split(".") if len(x)>3][0]
	return convert_nx_gObjs_to_dimacs_gObjs([g])

if __name__ == '__main__':
	parser = get_parser()
	args = vars(parser.parse_args())
	try:
		main(args)
	except Exception, e:
		print str(e)
		traceback.print_exc()
		sys.exit(1)
	sys.exit(0)
