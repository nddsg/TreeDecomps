__version__ = "0.1.0"

import multiprocessing as mp
import networkx as nx
import os
import sys
import re
from collections import defaultdict
import numpy as np
import pandas as pd


# Log Info
# [ ] todo - finish edgelist_basic_info so it writes a file in json form (key, value) of 
#			a given graph {gn: (V,E)}

results= defaultdict(tuple)

def Pandas_DataFrame_From_Edgelist(dataset_files_path):
  dataframes = []

  for input_graph in dataset_files_path:
    dat = []
    with open(input_graph) as ifile:
      for line in ifile:
        if not ("%" in line  or '#' in line):
          lparts = line.rstrip('\r\n').split()
        #   print lparts
          if len(lparts)>=2:
            dat.append(lparts)
    # print np.shape(dat)
    if np.shape(dat)[1] == 4:
        df = pd.DataFrame(dat, columns=['src', 'trg','w', 'ts'])
    elif np.shape(dat)[1]==3:
        df = pd.DataFrame(dat, columns=['src', 'trg','ts'])
    else:
        df = pd.DataFrame(dat, columns=['src', 'trg'])
    Info('... dropping duplicates')
    df = df.drop_duplicates()
    # if 0: print '  sorting by ts ...'
    # df.sort_values(by=['ts'], inplace=True)
    # df = df[df['ts']>0]
    dataframes.append(df)


def graph_name(fname):
	gnames= [x for x in os.path.basename(fname).split('.') if len(x) >3][0]
	if len(gnames):
		return gnames
	else:
		return gnames[0]

def collect_results(result):
	gn,v,e = result
	results[gn] = (v,e)
		
def edgelist_basic_info(fn_lst):
	# if the file exists ... read it and return as dict
	if os.path.exists('.graph_base_info.json'):
		print (" " + "base info file exists ... ")
		g_base_info_dict = load_graph_base_info()
	else:
		resuts=defaultdict(tuple)
		p = mp.Pool(processes=2)
		for f in fn_lst:
			res_d = net_info(f,)
			collect_results(res_d)
		# p.close()
		# p.join()
	
		write_graph_base_info(results)
		g_base_info_dict = results
	return g_base_info_dict 
	
	
def net_info(edgelist_fname):
	dfs = Pandas_DataFrame_From_Edgelist([edgelist_fname])
	df = dfs[0]

	try:
		g = nx.from_pandas_dataframe(df, 'src', 'trg', edge_attr=['ts'])
	except	Exception:
		g = nx.from_pandas_dataframe(df, 'src', 'trg')

	if df.empty:
		g = nx.read_edgelist(edgelist_fname,comments="%")
	gn = graph_name(edgelist_fname)
	
	return (gn, g.number_of_nodes(), g.number_of_edges())	


def write_graph_base_info(ddict):
	import json
	try:
		with open('.graph_base_info.json', 'w') as fp:
			json.dump(ddict, fp)
		return True
	except IOError:
		print ("unable to write to disk")
		return False

def load_graph_base_info():
	import json
	try:
		with open('.graph_base_info.json', 'r') as fp:
			data = json.load(fp)
	except IOError:
		print ("Failed to read file")
		exit()
	return data

def Info(_str):
	print ("	>> {}".format(_str))

def listify_rhs(rhs_rule):
	rhs_clean= [f[1:-1] for f in re.findall("'.+?'", rhs_rule)]
	return rhs_clean

def sample_subgraph(g):
	from .graph_sampler import rwr_sample
	import tempfile

	subgraphs = []
	for j,Gprime in enumerate(rwr_sample(g, 2, 300)):
		fd, path = tempfile.mkstemp()
		try:
			nx.write_edgelist(Gprime,path)		# use the path or the file descriptor
		finally:
			os.close(fd)
		
		subgraphs.append(Gprime)
	return subgraphs
		
	
def largest_conn_comp(fname):
	if fname.endswith(".p"):
		graph	= nx.read_gpickle(fname)
	else:
		graph = load_edgelist(fname)
	giant_nodes = max(nx.connected_component_subgraphs(graph), key=len)

	if giant_nodes.number_of_nodes()>500:
		samp_subgraphs = sample_subgraph(nx.subgraph(graph, giant_nodes))
		print ("samp_subgraphs",len(samp_subgraphs))
		return samp_subgraphs
	else:
		print ("largest cc",nx.info(giant_nodes))
		return giant_nodes

def list_largest_conn_comp(fname):
	if fname.endswith(".p"):
		graph = nx.read_gpickle(fname)
	else:
		graph = load_edgelist(fname)
	print ("	",sorted([len(x) for x in nx.connected_component_subgraphs(graph)]))

def load_edgelist(gfname):
	import pandas as pd
	import traceback

	try:
		edglst = pd.read_csv(gfname, comment='%', delimiter='\t')
		# print edglst.shape
		if edglst.shape[1]==1: edglst = pd.read_csv(gfname, comment='%', delimiter="\s+")
	except Exception:
		# print ("EXCEPTION:",str(e))
		traceback.print_exc()
		# sys.exit(1)
		try:
			edglst = pd.read_csv(gfname, delimiter=",", comment="#")
		except Exception:
			# Info ("EXCEPTION: %s"%str(e))
			traceback.print_exc()
			sys.exit(1)

	if edglst.shape[1] == 3:
		edglst.columns = ['src', 'trg', 'wt']
	elif edglst.shape[1] == 4:
		edglst.columns = ['src', 'trg', 'wt','ts']
	else:
		edglst.columns = ['src', 'trg']
	g = nx.from_pandas_dataframe(edglst,source='src',target='trg')
	g.name = [n for n in os.path.basename(gfname).split(".") if len(n)>3][0]
	return g
