# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'

import re
import os
import subprocess
import shutil
import numpy as np
import random
from sys import platform
from read_write import get_project_directory, mapping_abc_abc
from read_write import read_weights, read_verilog
import matplotlib.pyplot as plt


def check_histogram_for_existed_test(weights_file):
    weights = read_weights(weights_file)
    max_weight = -100000000
    min_weight = 100000000
    wvals = np.array(list(weights.values()), dtype=np.float32)
    print('Min weight', wvals.min())
    print('Max weight', wvals.max())

    n, bins, patches = plt.hist(wvals, 20, facecolor='green', alpha=0.75)
    plt.grid(True)
    plt.show()


def print_out_casex_module(out, tt, out_index):
    input_number = len(tt[0])
    out.write("module mod_out_{} (o".format(out_index))
    for i in range(input_number):
        out.write(', in_{}'.format(i))
    out.write(');\n')
    out.write('\toutput o;\n')
    for i in range(input_number):
        out.write('\tinput in_{};\n'.format(i))
    out.write('\talways @(in_{}'.format(0))
    for i in range(1, input_number):
        out.write(' or in_{}'.format(i))
    out.write(')\n')
    out.write('\tbegin\n')
    out.write('\tcase ({{in_{}'.format(0))
    for i in range(1, input_number):
        out.write(', in_{}'.format(i))
    out.write('})\n')

    for i in range(len(tt)):
        out.write("\t\t{}'b".format(input_number))
        for j in range(input_number):
            out.write('{}'.format(tt[i][j]))
        out.write(": o = 'b1;\n")

    out.write('\tendcase\n')
    out.write('\tend\n')
    out.write('endmodule\n\n')


def print_out_module(out, truth_table, out_index, in_num, target_num, term_count):
    max_nodes_in_element = 30000
    type = 1
    basis = []
    for i in range(in_num):
        basis.append('in_{}'.format(i))
    for i in range(target_num):
        basis.append('t_{}'.format(i))

    target_name = 'out_{}'.format(out_index)
    str1 = '\t// OUTPUT: out_{}\n'.format(out_index)
    if len(truth_table) > 0:
        all_terms = []
        for line in truth_table:
            top_node = "trm_{}".format(term_count)
            str1 += '\twire {};\n'.format(top_node)
            all_terms.append(top_node)
            term_count += 1
            wire_list = []
            for i in range(len(line)):
                if (line[i] == '1' and type == 0) or (line[i] == '0' and type == 1):
                    wire_list.append(basis[i])
                elif (line[i] == '0' and type == 0) or (line[i] == '1' and type == 1):
                    nm = 'iww_{}'.format(term_count)
                    term_count += 1
                    str1 += '\twire {};\n'.format(nm)
                    str1 += '\tnot ({}, {});\n'.format(nm, basis[i])
                    wire_list.append(nm)

            if type == 0:
                str1 += '\tand (' + top_node
            else:
                str1 += '\tor (' + top_node
            for w in wire_list:
                str1 += ', ' + w
            if type == 0:
                str1 += ', 1\'b1'
            else:
                str1 += ', 1\'b0'
            str1 += ');\n'

        # Case where can be too much elements for ABC
        if len(all_terms) + 1 > max_nodes_in_element:
            inter_nodes = []
            for i in range(0, len(all_terms), max_nodes_in_element):
                index = i // max_nodes_in_element
                nm = "additional_{}_{}".format(term_count, i)
                inter_nodes.append(nm)
                str1 += '\twire {};\n'.format(nm)
                if type == 0:
                    str1 += '\tor ('
                else:
                    str1 += '\tand ('
                str1 += nm
                for a in all_terms[index * max_nodes_in_element: (index + 1) * max_nodes_in_element]:
                    str1 += ', ' + a
                if type == 0:
                    str1 += ', 1\'b0'
                else:
                    str1 += ', 1\'b1'
                str1 += ');\n'
            if type == 0:
                str1 += '\tor ('
            else:
                str1 += '\tand ('
            str1 += target_name
            for a in inter_nodes:
                str1 += ', ' + a
            if type == 0:
                str1 += ', 1\'b0'
            else:
                str1 += ', 1\'b1'
            str1 += ');\n'
        else:
            if type == 0:
                str1 += '\tor ('
            else:
                str1 += '\tand ('
            str1 += target_name
            for a in all_terms:
                str1 += ', ' + a
            if type == 0:
                str1 += ', 1\'b0'
            else:
                str1 += ', 1\'b1'
            str1 += ');\n'
    else:
        str1 += '\tbuf ({} , 1\'b{});\n'.format(target_name, truth_table)

    out.write(str1)
    return term_count


def print_overall_module_G(file_name, tt, innum, outnum):
    out = open(file_name, "w")
    out.write("module top (out_{}".format(0))
    for i in range(1, outnum):
        out.write(', out_{}'.format(i))
    for i in range(innum):
        out.write(', in_{}'.format(i))
    out.write(');\n')
    for i in range(innum):
        out.write('\tinput in_{};\n'.format(i))
    for i in range(outnum):
        out.write('\toutput out_{};\n'.format(i))

    term_count = 0
    for i in range(outnum):
        term_count = print_out_module(out, tt[i], i, innum, 0, term_count)

    out.write('endmodule\n\n')
    out.close()


def broke_truth_table(tt, target_num, prob):
    tt_reduced = dict()
    for out in tt:
        tt_reduced[out] = []
        for line in tt[out]:
            if random.uniform(0, 1) > prob or 1:
                for k in range(target_num):
                    val = random.randint(0, 1)
                    line += str(val)
                tt_reduced[out].append(line)
    return tt_reduced


def print_overall_module_F(file_name, tt, innum, outnum, targetnum):
    out = open(file_name, "w")
    out.write("module top (out_{}".format(0))
    for i in range(1, outnum):
        out.write(', out_{}'.format(i))
    for i in range(innum):
        out.write(', in_{}'.format(i))
    out.write(');\n')
    for i in range(innum):
        out.write('\tinput in_{};\n'.format(i))
    for i in range(outnum):
        out.write('\toutput out_{};\n'.format(i))
    for i in range(targetnum):
        out.write('\tinput t_{};\n'.format(i))

    term_count = 0
    for i in range(outnum):
        term_count = print_out_module(out, tt[i], i, innum, targetnum, term_count)

    out.write('endmodule\n\n')
    out.close()


def clean_abc_output_v2(circuit_file, synth_file, converted_circuit_file):
    # get module line from initial circuit file
    full_nodes_list = []

    f = open(circuit_file, "r")
    top_line = f.readline().strip()
    f.close()

    f = open(converted_circuit_file, 'w')
    f.write(top_line + '\n')
    f1 = open(synth_file, 'r')
    content = f1.read()

    # input
    # find t_* as special cases
    t_cases = []
    matches_wires = re.findall(r"\s*?((input)\s+(.*?);)", content, re.DOTALL)
    if len(matches_wires) > 0:
        f.write("\tinput ")
        wires = matches_wires[0][2].strip().split(',')

        comma = 0
        for w in wires:
            node_name = w.strip()
            if 't_' in node_name:
                t_cases.append(node_name)
            else:
                if comma == 0:
                    comma += 1
                else:
                    f.write(', ')
                f.write(w.strip())
            full_nodes_list.append(node_name)
        f.write(';\n')
    if len(matches_wires) > 1:
        print('Unexpected behaviour! Many inputs for ABC.')
        exit()

    # output
    matches_wires = re.findall(r"\s*?((output)\s+(.*?);)", content, re.DOTALL)
    if len(matches_wires) > 0:
        f.write("\toutput ")
        wires = matches_wires[0][2].strip().split(',')
        f.write(wires[0].strip())
        full_nodes_list.append(wires[0].strip())
        for w in wires[1:]:
            f.write(', ' + w.strip())
            full_nodes_list.append(w.strip())
        f.write(';\n')
    if len(matches_wires) > 1:
        print('Unexpected behaviour! Many outputs for ABC.')
        exit()

    # wires
    wire_map = dict()
    matches_wires = re.findall(r"\s*?((wire) (.*?);)", content, re.DOTALL)
    if len(matches_wires) == 1:
        wires = matches_wires[0][2].strip().split(',')
        for w in wires:
            ws = w.strip()
            wire_map[ws] = 'gm_' + ws
        f.write("\twire ")
        lst = sorted(wire_map.keys())
        f.write(wire_map[lst[0]])
        full_nodes_list.append(wire_map[lst[0]])
        for w in lst[1:]:
            f.write(', ' + wire_map[w])
            full_nodes_list.append(wire_map[w])
        f.write(';\n')
    if len(matches_wires) > 1:
        print('Unexpected behaviour! Many wires for ABC.')
        exit()

    # t_* elements
    if len(t_cases) > 0:
        f.write("\twire ")
        f.write(t_cases[0])
        for w in t_cases[1:]:
            f.write(', ' + w)
        f.write(';\n')

    # Все элементы
    matches = re.findall(r"\s*?(buf|not|nand|and|nor|or|xor|xnor)\d+\s+(.*?)\((.*?);", content, re.DOTALL)
    for m in matches:
        # print(m[2])
        cell_type = m[0]
        nodes = re.search("\.O\((.*?)\)", m[2], re.M)
        if nodes is None:
            print('Error converting verilog file (3)')
        out = nodes.group(1)
        if out in wire_map:
            out = wire_map[out]

        nodes = re.findall("\.[a-z]\((.*?)\)", m[2], re.DOTALL)
        if nodes is None:
            print('Error converting verilog file (1)')

        f.write('\t' + cell_type + ' (' + out)
        for n in nodes:
            if n in wire_map:
                f.write(', ' + wire_map[n])
            else:
                f.write(', ' + n)
        f.write(');\n')
    # Bufs
    matches = re.findall(r"\s*?(vcc|gnd)\s+[^\(]+\(.O\(([^\)]+)\)\);", content)
    for m in matches:
        if m[0] == 'gnd':
            f.write('\t' + 'buf' + ' (' + m[1] + ', 1\'b0);\n')
        if m[0] == 'vcc':
            f.write('\t' + 'buf' + ' (' + m[1] + ', 1\'b1);\n')

    f.write('endmodule\n')
    f.close()
    f1.close()
    return full_nodes_list


def generate_weights(file_weights, nodes_list):
    out = open(file_weights, 'w')
    for n in nodes_list:
        weight_value = random.randint(10, 20)
        out.write('{} {}\n'.format(n, weight_value))
    out.close()


def generate_random_test_v1(out_dir):
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    dfile = get_project_directory()
    file_G_1 = os.path.join(dfile, out_dir, 'G_init.v')
    file_G_2 = os.path.join(dfile, out_dir, 'G_abc.v')
    file_G_3 = os.path.join(dfile, out_dir, 'G.v')
    file_F_1 = os.path.join(dfile, out_dir, 'F_init.v')
    file_F_2 = os.path.join(dfile, out_dir, 'F_abc.v')
    file_F_3 = os.path.join(dfile, out_dir, 'F.v')
    file_weights = os.path.join(dfile, out_dir, 'weight.txt')

    input_number = 10
    output_number = 10
    target_number = 1
    rows_in_truth_table = 30
    remove_rows_probablity = 0.2

    truth_table_initital = dict()
    for i in range(output_number):
        truth_table_initital[i] = []
        for j in range(rows_in_truth_table):
            truth_table_initital[i].append('')
            for k in range(input_number):
                val = random.randint(0, 1)
                truth_table_initital[i][j] += str(val)

    print_overall_module_G(file_G_1, truth_table_initital, input_number, output_number)
    ret = mapping_abc_abc(file_G_1, file_G_2)
    clean_abc_output_v2(file_G_1, file_G_2, file_G_3)

    truth_table_reduced = broke_truth_table(truth_table_initital, target_number, remove_rows_probablity)
    print(truth_table_reduced)
    print_overall_module_F(file_F_1, truth_table_reduced, input_number, output_number, target_number)
    ret = mapping_abc_abc(file_F_1, file_F_2)
    nodes_list = clean_abc_output_v2(file_F_1, file_F_2, file_F_3)
    generate_weights(file_weights, nodes_list)


def broke_G_file(G_file, out_file):
    f1 = open(G_file, 'r')
    out = open(out_file, "w")

    need_to_replace = 1
    nodes_to_replace = []
    while 1:
        line = f1.readline()
        if line == '':
            break

        for n in nodes_to_replace:
            line = line.replace(n[0] + ',', n[1] + ',')
            line = line.replace(n[0] + ')', n[1] + ')')

        matches_wires = re.findall(r"\s*?((input)\s+(.*?);)", line, re.DOTALL)
        if len(matches_wires) > 0:
            out.write('\tinput t_0;\n')

        matches = re.findall(r"\s*?(buf|not|nand|and|nor|or|xor|xnor)\s+(.*?)\((.*?);", line, re.DOTALL)
        if len(matches) > 0:
            if 'in_' in matches[0][2] or 'out_' in matches[0][2]:
                out.write(line)
                continue
            if need_to_replace > 0:
                print('Replace line:', line)
                out.write('\t//' + line)
                nodes_to_replace.append((matches[0][2].split(',')[0], 't_0'))
                need_to_replace -= 1
            else:
                out.write(line)
        else:
            out.write(line)

    print('Replaced nodes:', nodes_to_replace)
    out.close()


def check_if_node_can_be_removed(cir, l):
    if 'out_' in l or 'in_' in l or 't_' in l or '_VDD' in l or '_GND' in l or '_VCC' in l:
        return 0
    inps = cir.__elements__[l][1]
    denied = 0
    for inp in inps:
        if 'out_' in inp or 'in_' in inp or 't_' in inp:
            denied += 1
    if denied > 0:
        return 0
    return 1


def replace_node_in_cir(cir, l, rep):
    for i in range(len(cir.__inputs__)):
        if cir.__inputs__[i] == l:
            cir.__inputs__[i] = rep
    for i in range(len(cir.__outputs__)):
        if cir.__outputs__[i] == l:
            cir.__outputs__[i] = rep
    for el in cir.__elements__:
        for i in range(len(cir.__elements__[el][1])):
            if cir.__elements__[el][1][i] == l:
                cir.__elements__[el][1][i] = rep


def broke_circuit(cir, targets, num_of_removed):
    for i in range(targets):
        print('Create target: t_{}'.format(i))
        lbls = list(cir.__elements__.keys())
        random.shuffle(lbls)
        for l in lbls:
            if not check_if_node_can_be_removed(cir, l):
                continue
            # OK remove it and other elements connected to it
            print('Removed {}'.format(l))
            replace_node_in_cir(cir, l, 't_{}'.format(i))
            nodes_for_removal = cir.__elements__[l][1].copy()
            num_of_removed -= 1
            cir.__elements__.pop(l)
            while num_of_removed > 0 and len(nodes_for_removal) > 0:
                node = random.choice(nodes_for_removal)
                if check_if_node_can_be_removed(cir, node):
                    print('Removed {}'.format(node))
                    nodes_for_removal += cir.__elements__[node][1].copy()
                    cir.__elements__.pop(node)
                    num_of_removed -= 1
                nodes_for_removal.remove(node)
            break


def write_broken_circut(out_file, cir, target_number):
    out = open(out_file, "w")
    out.write("module top (")
    for o in cir.__outputs__:
        out.write(o + ', ')
    if len(cir.__inputs__) > 0:
        out.write(cir.__inputs__[0])
        for i in cir.__inputs__[1:]:
            out.write(', ' + i)
    out.write(');\n')

    if len(cir.__inputs__) > 0:
        out.write('\tinput ')
        out.write(cir.__inputs__[0])
        for i in cir.__inputs__[1:]:
            out.write(', ' + i)
        out.write(';\n')

    out.write('\toutput ')
    out.write(cir.__outputs__[0])
    for i in cir.__outputs__[1:]:
        out.write(', ' + i)
    out.write(';\n')

    wires = []
    targets = []
    for el in cir.__elements__:
        if el not in wires:
            if el not in cir.__inputs__:
                if el not in cir.__outputs__:
                    if 't_' not in el:
                        wires.append(el)
                    else:
                        if el not in targets:
                            targets.append(el)

        for i in range(len(cir.__elements__[el][1])):
            w = cir.__elements__[el][1][i]
            if w not in wires:
                if w not in cir.__inputs__:
                    if w not in cir.__outputs__:
                        if 't_' not in w:
                            wires.append(w)
                        else:
                            if w not in targets:
                                targets.append(w)
    out.write('\twire ')
    out.write(wires[0])
    for i in wires[1:]:
        out.write(', ' + i)
    out.write(';\n')

    if len(targets) > 0:
        out.write('\tinput ')
        out.write(targets[0])
        for i in targets[1:]:
            out.write(', ' + i)
        out.write(';\n')

    for el in cir.__elements__:
        node = el
        type = cir.__elements__[el][0].lower()
        if type == 'inv':
            type = 'not'

        if type == 'gnd':
            out.write('\tbuf (' + node + ', 1\'b0);\n')
            continue
        if type == 'vcc':
            out.write('\tbuf (' + node + ', 1\'b0);\n')
            continue
        if type == 'vdd':
            out.write('\tbuf (' + node + ', 1\'b1);\n')
            continue

        out.write('\t' + type + ' (')
        out.write(node)
        for i in cir.__elements__[el][1]:
            out.write(', ' + i)
        out.write(');\n')

    out.write('endmodule\n')
    out.close()
    return


def generate_random_test(params):
    out_dir = params['output_dir']
    input_number = 10
    output_number = 10
    target_number = 2
    remove_elements = 3
    rows_in_truth_table = 32
    if 'input_number' in params:
        input_number = int(params['input_number'])
    if 'output_number' in params:
        output_number = int(params['output_number'])
    if 'target_number' in params:
        target_number = int(params['target_number'])
    if 'remove_elements' in params:
        remove_elements = int(params['remove_elements'])
    if 'rows_in_truth_table' in params:
        rows_in_truth_table = int(params['rows_in_truth_table'])
    random.seed(params['seed'])

    print('Generate circuit in {}'.format(out_dir))
    print('Params: {}'.format(params))

    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    dfile = get_project_directory()
    file_G_1 = os.path.join(dfile, out_dir, 'G_init.v')
    file_G_2 = os.path.join(dfile, out_dir, 'G_abc.v')
    file_G_3 = os.path.join(dfile, out_dir, 'G.v')
    file_F_1 = os.path.join(dfile, out_dir, 'F_init.v')
    file_F_2 = os.path.join(dfile, out_dir, 'F_abc.v')
    file_F_3 = os.path.join(dfile, out_dir, 'F.v')
    file_weights = os.path.join(dfile, out_dir, 'weight.txt')

    truth_table_initital = dict()
    for i in range(output_number):
        truth_table_initital[i] = []
        for j in range(rows_in_truth_table):
            truth_table_initital[i].append('')
            for k in range(input_number):
                val = random.randint(0, 1)
                truth_table_initital[i][j] += str(val)

    print_overall_module_G(file_G_1, truth_table_initital, input_number, output_number)
    ret = mapping_abc_abc(file_G_1, file_G_2)
    clean_abc_output_v2(file_G_1, file_G_2, file_G_3)

    _, scheme = read_verilog(file_G_3)
    broke_circuit(scheme, target_number, remove_elements)
    write_broken_circut(file_F_1, scheme, target_number)

    ret = mapping_abc_abc(file_F_1, file_F_2)
    nodes_list = clean_abc_output_v2(file_F_1, file_F_2, file_F_3)
    generate_weights(file_weights, nodes_list)


if __name__ == '__main__':

    params = {
        'seed': 3,
        'output_dir': 'testcases/unit30',
        'input_number': 15,
        'output_number': 15,
        'target_number': 10,
        'remove_elements': 15,
        'rows_in_truth_table': 100,
    }

    generate_random_test(params)
