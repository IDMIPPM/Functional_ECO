# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'

import random
import os
import time
from datetime import datetime as dt
import eco_core as ic
import utils as u
import subprocess
from sys import platform


def mean(l):
    if len(l) == 0:
        return 0
    return sum(l) / float(len(l))


def verification(out_file, patch_file, G):
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    dfile = u.get_project_directory()

    run_path = os.path.join(dfile, "equiv_check", ostype)
    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    if os.path.isfile(sch1_file):
        os.remove(sch1_file)
    if os.path.isfile(sch2_file):
        os.remove(sch2_file)
    f = open(out_file)
    sch = f.read()
    f.close()
    f = open(patch_file)
    patch = f.read()
    f.close()
    f = open(G)
    etal = f.read()
    f.close()
    f = open(sch1_file, 'w')
    f.write(sch + '\n\n' + patch)
    f.close()
    f = open(sch2_file, 'w')
    f.write(etal)
    f.close()

    abc_exe = os.path.join(run_path, "abc.exe")
    exe = abc_exe + " -f check.txt"
    try:
        if platform == "linux":
            ret = subprocess.check_output(exe, cwd=run_path, shell=True, timeout=20).decode('UTF-8')
        else:
            ret = subprocess.check_output(exe, cwd=run_path, timeout=20).decode('UTF-8')
    except subprocess.TimeoutExpired:
        ret = 'Error: ' + exe
        print('Timeout')
    except:
        ret = 'Error: ' + exe + ' Working dir:' + run_path
    if 'NOT EQUIVALENT' in ret:
        # print('Schemes are NOT equivalent')
        return 0
    elif 'are equivalent' in ret:
        # print('Schemes are equivalent')
        return 1
    else:
        # print('EQUIVALENCE CHECK FAILED')
        print(ret)
        return None


if __name__ == '__main__':
    seeds = [100, 101]
    runs_num = 1
    time_limit = 1800
    stat = {}
    detailed_stat = []
    date_str = str(dt.now().replace(microsecond=0).isoformat()).replace("-", "_").replace(":", "_").replace("T", "_")
    stat_log = open('temp/log_revision_{}.txt'.format(date_str), 'a')
    stat_log.write('seed:(Equivalence, Score, Patch size, Time)\n')
    capacity = 20000
    for test_number in range(1, 25):
        not_equiv_cases = 0
        test_stat_avg_score = []
        test_stat_avg_elements = []
        test_stat_avg_time = []
        test_stat_min_score = 1000000000.0
        test_stat_max_score = -1000000000.0
        test_stat_min_time = 1000000000.0
        test_stat_max_time = -1000000000.0

        stat[test_number] = []
        stat_log.write(str(test_number) + '     -     ')
        stat_log.flush()
        for _ in range(runs_num):
            seed = random.randint(0, 10000)
            random.seed(seed)
            log = open('testcases/unit{}/log.txt'.format(test_number), 'a')
            log.write('\n\n')
            log.write('================================================================\n')
            log.write(time.asctime())
            log.write('\nSeed {}'.format(seed) + '\n')
            log.write(str(capacity) + ' Stimulus\n')
            log.flush()
            print('Start testcase {} [Seed {}]'.format(test_number, seed))
            F = './testcases/unit{}/F.v'.format(test_number)
            G = './testcases/unit{}/G.v'.format(test_number)
            weights = './testcases/unit{}/weight.txt'.format(test_number)
            patch_file = "./results/patch.v"
            out_file = "./results/out.v"
            out_dir = './results/'
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir)
            print('PATHS INFO')
            print('F file:', F)
            print('G file:', G)
            print('weight file:', weights)
            print('patch.v file:', patch_file)
            print('out.v file:', out_file)
            res = ic.ic(F, G, weights, patch_file, out_file, time_limit)
            res = list(res)
            if platform != "linux":
                if res[0] != 0:
                    res[0] = verification(out_file, patch_file, G)
            res = tuple(res)
            if res[0] != 1:
                not_equiv_cases += 1
            test_stat_avg_score.append(res[1])
            test_stat_avg_elements.append(res[2])
            test_stat_avg_time.append(res[3])
            if res[1] < test_stat_min_score:
                test_stat_min_score = res[1]
            if res[1] > test_stat_max_score:
                test_stat_max_score = res[1]
            if res[3] < test_stat_min_time:
                test_stat_min_time = res[3]
            if res[3] > test_stat_max_time:
                test_stat_max_time = res[3]

            stat[test_number].append(res)
            stat_log.write(str(seed) + ':' + str(res) + '    ')
            stat_log.flush()
        stat_str = ''
        if not_equiv_cases > 0:
            stat_str += 'Error! Found not equivalent cases: {} '.format(not_equiv_cases)
        stat_str += 'Score: [Min: {:.0f} Max: {:.0f} Avg: {:.0f}]'.format(
            test_stat_min_score, test_stat_max_score, mean(test_stat_avg_score))
        stat_str += ' Time: [Min: {:.0f} Max: {:.0f} Avg: {:.0f}] Elements: [Avg: {:.0f}]'.format(
            test_stat_min_time, test_stat_max_time, mean(test_stat_avg_time), mean(test_stat_avg_elements))

        stat_log.write('\n' + stat_str + '\n')
        detailed_stat.append('Testcase: {}: {}'.format(test_number, stat_str))
        print(detailed_stat[-1])
    print(stat)
    for d in detailed_stat:
        print(d)
