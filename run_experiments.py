import argparse
import os
import sys
import multiprocessing

from create_graphs import *

# TODO: write instructions, test script in docker
# TODO: mention thread count in Figure 4 and remove alpha=0.75. Make it more clear which ones are lock-free and which are lock-based

# parameters:
#  - datastructures: lists, trees, other, with-vs-try-lock
#  - type: scalability, rqsize, size, ratio
#  - threads, rqsize, zipfian, ratio

parser = argparse.ArgumentParser()
parser.add_argument("datastructures", help="pick one of [lists, trees, sets, btrees, with-vs-try-lock]")
parser.add_argument("threads", help="Number of threads")
parser.add_argument("sizes", help="Initial size")
parser.add_argument("zipfians", help="Zipfian parameter, number between [0, 1)")
parser.add_argument("ratios", help="Update ratio, number between 0 and 100.")
parser.add_argument("-t", "--test_only", help="test script",
                    action="store_true")
parser.add_argument("-g", "--graphs_only", help="graphs only",
                    action="store_true")
parser.add_argument("-p", "--paper_ver", help="paper version of graphs, no title or legends",
                    action="store_true")

args = parser.parse_args()
print("datastructures: " + args.datastructures)
print("threads: " + args.threads)
print("sizes: " + args.sizes)
print("zipfians: " + args.zipfians)
print("ratios: " + args.ratios)

test_only = args.test_only
graphs_only = args.graphs_only
rounds = 3

# compile everything
if test_only:
  rounds = 1

maxcpus = multiprocessing.cpu_count()
already_ran = set()

ds_list = {
           "lists": ['list-trylock-lb', 'dlist-trylock-lb', 'list-trylock-lf', 'dlist-trylock-lf', 'harris_list', 'harris_list_opt'],
           "trees": ['chromatic', 'leaftree-trylock-lb', 'leaftree-trylock-lf', 'bronson', 'drachsler', 'natarajan', 'ellen'],
           "sets": ['leaftree-trylock-lb', 'leaftree-trylock-lf', 'arttree-trylock-lb', 'blockleaftree-b-trylock-lb', 'arttree-trylock-lf', 'blockleaftree-b-trylock-lf', 'hash_optimistic-trylock-lf', 'hash_optimistic-trylock-lb', 'btree-trylock-lf', 'btree-trylock-lb', 'sri_abtree_pub'],
           "with-vs-try-lock": ['leaftree-trylock-lb', 'leaftree-trylock-lf', 'leaftree-lf', 'leaftree-lb'],
           "btrees": ['sri_abtree', 'sri_abtree_mcs', 'sri_abtree_pub']
          }

def string_to_list(s):
  s = s.strip().strip('[').strip(']').split(',')
  return [ss.strip() for ss in s]

def to_list(s):
  if type(s) == list:
    return s
  return [s]

def runstring(test, op, outfile):
    if op in already_ran:
        return
    already_ran.add(op)
    os.system("echo \"" + op + "\"")
    os.system("echo \"datastructure: " + test + "\"")
    os.system("echo \"" + op + "\" >> " + outfile)
    os.system("echo \"datastructure: " + test + "\" >> " + outfile)
    for i in range(rounds):
        x = os.system(op + " >> " + outfile)
        if (x) :
            if (os.WEXITSTATUS(x) == 0) : raise NameError("  aborted: " + op)
            os.system("echo Failed")
    
def runtest(test,procs,n,z,u,sparse,extra,outfile) :
    r = 1
    strsparse = ""
    if (sparse) : strsparse = "-sparse "
    strzip = ""
    if (float(z) > 0.0) : strzip = "-z -zp " + str(z) + " "
    otherargs = " -no_check -v -tt 1.0 "
    if test_only:
        otherargs = " -no_check -v -tt 0.01 "

    runstring(test, "PARLAY_NUM_THREADS=" + str(max(int(procs), maxcpus)) + " numactl -i all ./" + dsinfo[test].binary + " -r " + str(r) + " -p " + str(procs) + " -fixed_time " + extra + strzip + strsparse + "-n " + str(n) + " -u " + str(u) + otherargs, outfile)

datastructures = ds_list[args.datastructures]
sparse = (args.datastructures == 'sets')
exp_type = ""
threads = args.threads
sizes = args.sizes
zipfians = args.zipfians
ratios = args.ratios
if '[' in args.threads:
  exp_type = "scalability"
  threads = string_to_list(threads)
elif '[' in args.sizes:
  exp_type = "size"
  sizes = string_to_list(sizes)
elif '[' in args.zipfians:
  exp_type = "zipfian"
  zipfians = string_to_list(zipfians)
elif '[' in args.ratios:
  exp_type = "ratio"
  ratios = string_to_list(ratios)
else:
  print('invalid argument')
  exit(1)

outfile = "results/" + "-".join([args.datastructures, args.threads, args.sizes, args.zipfians, args.ratios]) + ".txt"

if not graphs_only:
  # clear output file
  os.system("echo \"\" > " + outfile)
  for ds in datastructures:
    for th in to_list(threads):
      for size in to_list(sizes):
        for zipfian in to_list(zipfians):
          for ratio in to_list(ratios):
            runtest(ds,th,size,zipfian,ratio,sparse,"",outfile)

throughput = {}
stddev = {}
threads = []
ratios = []
maxkeys = []
alphas = []
algs = []

readResultsFile(outfile, throughput, stddev, threads, ratios, maxkeys, alphas, algs)

threads.sort()
ratios.sort()
maxkeys.sort()
alphas.sort()

print('threads: ' + str(threads))
print('update ratios: ' + str(ratios))
print('maxkeys: ' + str(maxkeys))
print('alphas: ' + str(alphas))
print('algs: ' + str(algs))
# print(throughput)

if exp_type == "scalability":
  plot_scalability_graphs(throughput, stddev, threads, ratios, maxkeys, alphas, datastructures, args.datastructures, args.paper_ver)
elif exp_type == "size":
  plot_size_graphs(throughput, stddev, threads, ratios, maxkeys, alphas, datastructures, args.datastructures, args.paper_ver)
elif exp_type == "zipfian":
  plot_alpha_graphs(throughput, stddev, threads, ratios, maxkeys, alphas, datastructures, args.datastructures, args.paper_ver)
elif exp_type == "ratio":
  plot_ratio_graphs(throughput, stddev, threads, ratios, maxkeys, alphas, datastructures, args.datastructures, args.paper_ver)
