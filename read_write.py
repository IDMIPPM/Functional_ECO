# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'

import re
import scheme as sc
import string
import random
import os
from sys import platform
import subprocess
import shutil
import eq_check as eq


def get_project_directory():
    project_directory = os.path.abspath(os.path.dirname(__file__))
    return project_directory


def gen_name(scheme):
    """
    simple name generator
    :param scheme: scheme in scheme_alt format
    :return: unique name for this scheme
    """
    labels = scheme.input_labels()+scheme.output_labels()+scheme.element_labels()
    attempt = 'ngen'
    while (attempt in labels):
        a = string.ascii_letters + string.digits
        attempt = ''.join([random.choice(a) for i in range(4)])
    return attempt


def read_verilog(filename):
    """
    verilog parser
    :param filename: filename
    :return: scheme in scheme_alt format
    """
    scheme = sc.scheme_alt()
    f = open(filename)
    file = f.read()

    # parse module and ports
    m = re.match(r"\s*module\s+(\S+)\s*\(((\s*\S+\s*,)*\s*\S+\s*)\)\s*;\s*", file)
    if m:
        ports = m.group(2)
        ports = ports.replace(' ', '')
        ports = ports.split(',')
        module_name = m.group(1)
        rest = file[0:m.start()] + file[m.end():len(file)]

    # parse inputs
    m = re.match(r"\s*input\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        inputs = m.group(1)
        inputs = inputs.replace(' ', '')
        inputs = inputs.split(',')
        rest = rest[0:m.start()] + rest[m.end():len(rest)]
    else:
        print('ERROR IN READING VERILOG: no inputs')
        return 0

    # parse outputs
    m = re.match(r"\s*output\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        outputs = m.group(1)
        outputs = outputs.replace(' ', '')
        outputs = outputs.split(',')
        rest = rest[0:m.start()] + rest[m.end():len(rest)]
    else:
        print('ERROR IN READING VERILOG: no outputs')
        return 0

    # parse wires
    m = re.match(r"\s*wire\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        wires = m.group(1)
        wires = wires.replace(' ', '')
        wires = wires.split(',')
        rest = rest[0:m.start()] + rest[m.end():len(rest)]
    else:
        wires = []

    # parse test wires
    m = re.match(r"\s*wire\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        targets = m.group(1)
        targets = targets.replace(' ', '')
        targets = targets.split(',')
        rest = rest[0:m.start()] + rest[m.end():len(rest)]
    else:
        targets = []

    # generate VCC name
    while 1:
        VCC_name = gen_name(scheme)
        if VCC_name not in wires+inputs+outputs+targets:
            break

    # generate GND name
    while 1:
        GND_name = gen_name(scheme)
        if GND_name not in wires + inputs + outputs + targets:
            break
    VCC_name += '_VCC'
    GND_name += '_GND'

    # elements parsing
    lines = rest.splitlines()

    for line in lines:
        m = re.match(r"\s*(\S+)\s*\(((\s*\S+\s*,)*\s*\S+\s*)\)\s*;\s*", line)
        if m:
            elt = m.group(1)
            elt = elt.upper()
            if elt == 'NOT':
                elt = 'INV'
            pts = m.group(2)
            pts = pts.replace(' ', '')
            pts = pts.split(',')
            # проверка не являются ли сигналы - нулями/единицами
            scheme.__elements__[VCC_name] = ('VCC', [])
            scheme.__elements__[GND_name] = ('GND', [])
            k=0
            for inp in pts[1:]:
                k+=1
                if (inp == '1\'b1' or inp =='1'):
                    #name = gen_name(scheme)
                    #scheme.__elements__[name] = ('VCC', [])
                    #pts[k] = name
                    pts[k] = VCC_name
                if (inp == '1\'b0' or inp == '0'):
                    #name = gen_name(scheme)
                    #scheme.__elements__[name] = ('GND', [])
                    #pts[k] = name
                    pts[k] = GND_name
            scheme.__elements__[pts[0]] = (elt, pts[1:])

    scheme.__inputs__ = inputs
    scheme.__outputs__ = outputs

    return targets, scheme


def read_weights(filename):
    f = open(filename)
    lines = f.readlines()
    weights = {}
    for line in lines:
        m = re.match(r"\s*(\S+)\s+(\d+)", line)
        if m:
            node = m.group(1)
            weight = int(m.group(2))
            weights[node] = weight
    return weights


def read_AIG_verilog(filename):
    """
       verilog parser
       :param filename: filename
       :return: scheme in scheme_alt format
       """
    scheme = sc.scheme_alt()
    f = open(filename)
    file = f.read()
    # парсинг модуля и портов
    m = re.match(r".*\s*module\s+(\S+)\s+\(((\s*\S+\s*,)*\s*\S+\s*)\)\s*;\s*", file)
    if m:
        ports = m.group(2)
        ports = ports.replace(' ', '')
        ports = ports.replace('\n', '')
        ports = ports.split(',')
        module_name = m.group(1)
        rest = file[0:m.start()] + file[m.end():len(file)]
    else:
        print('NO MATCH')
    # парсинг входов
    m = re.match(r"\s*input\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        inputs = m.group(1)
        inputs = inputs.replace(' ', '')
        inputs = inputs.replace('\n', '')
        inputs = inputs.split(',')
        rest = rest[0:m.start()] + rest[m.end():len(rest)]
    else:
        print('ERROR IN READING VERILOG: no inputs')
        return 0

    # парсинг выходов
    m = re.match(r"\s*output\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        outputs = m.group(1)
        outputs = outputs.replace(' ', '')
        outputs = outputs.split(',')
        rest = rest[0:m.start()] + rest[m.end():len(rest)]
    else:
        print('ERROR IN READING VERILOG: no outputs')
        return 0

    # парсинг проводов
    m = re.match(r"\s*wire\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        wires = m.group(1)
        wires = wires.replace(' ', '')
        wires = wires.replace('\n', '')
        wires = wires.split(',')
        rest = rest[0:m.start()] + rest[m.end():len(rest)]


    # парсинг элементов
    lines = rest.splitlines()
    new_inputs = []
    for line in lines:
        m = re.match(r"\s*assign\s+(\S+)\s*=\s*(\S+)\s*&\s*(\S+)", line)
        if m:
            out = m.group(1)
            in1 = m.group(2)
            in2 = m.group(3)
            in2 = in2[:-1]

            if (in1 in inputs) | ((in1[0] == '~') & (in1[1:] in inputs)):
                if in1 not in new_inputs:
                    new_inputs.append(in1)
            if (in2 in inputs) | ((in2[0] == '~') & (in2[1:] in inputs)):
                if in2 not in new_inputs:
                    new_inputs.append(in2)

            if (in1[0]+in2[0] == '~~'):
                scheme.__elements__[out] = ('NOR', [in1[1:], in2[1:]])
            elif ('~' in in1[0]+in2[0]):
                if '~' == in1[0]:
                    scheme.__elements__[in1] = ('INV', [in1[1:]])
                    scheme.__elements__[out] = ('AND', [in1, in2])
                elif '~' == in2[0]:
                    scheme.__elements__[in2] = ('INV', [in2[1:]])
                    scheme.__elements__[out] = ('AND', [in1, in2])
            else:
                scheme.__elements__[out] = ('AND', [in1, in2])
        else:
            m = re.match(r"\s*assign\s+(\S+)\s*=\s*(\S+)\s*\|\s*(\S+)", line)
            if m:
                out = m.group(1)
                in1 = m.group(2)
                in2 = m.group(3)
                in2 = in2[:-1]

                if (in1 in inputs) | ((in1[0] == '~') & (in1[1:] in inputs)):
                    if in1 not in new_inputs:
                        new_inputs.append(in1)
                if (in2 in inputs) | ((in2[0] == '~') & (in2[1:] in inputs)):
                    if in2 not in new_inputs:
                        new_inputs.append(in2)


                if (in1[0] + in2[0] == '~~'):
                    scheme.__elements__[out] = ('NAND', [in1[1:], in2[1:]])
                elif ('~' in in1[0] + in2[0]):
                    if '~' == in1[0]:
                        scheme.__elements__[in1] = ('INV', [in1[1:]])
                        scheme.__elements__[out] = ('OR', [in1, in2])
                    elif '~' == in2[0]:
                        scheme.__elements__[in2] = ('INV', [in2[1:]])
                        scheme.__elements__[out] = ('OR', [in1, in2])
                else:
                    scheme.__elements__[out] = ('OR', [in1, in2])
    scheme.__inputs__ = inputs
    scheme.__outputs__ = outputs

    for i in range(len(new_inputs)):
        if new_inputs[i][0] == '~':
            new_inputs[i] = new_inputs[i][1:]

    return list(set(new_inputs)), scheme


def gen_patch_verilog_module_by_basis_and_truth_table_for_abc(target_name, type, basis, truth_table, term_count, out):
    '''
    Генерирует строку с СДНФ или СКНФ для заданного базиса и таблицы истинности.
    Далее можно использовать её для синтеза в ABC
    type = 0: SDNF
    type = 1: SKNF
    '''
    max_nodes_in_element = 30000
    str1 = '\t// Target: {}\n'.format(target_name)
    if len(basis) > 0:
        all_terms = []
        for line in truth_table:
            top_node = "term_{}".format(term_count)
            str1 += '\twire {};\n'.format(top_node)
            all_terms.append(top_node)
            term_count += 1
            wire_list = []
            for i in range(len(line)):
                if (line[i] == '1' and type == 0) or (line[i] == '0' and type == 1):
                    wire_list.append(basis[i])
                elif (line[i] == '0' and type == 0) or (line[i] == '1' and type == 1):
                    nm = 'iw_{}'.format(term_count)
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
        if len(all_terms)+1 > max_nodes_in_element:
            inter_nodes = []
            for i in range(0, len(all_terms), max_nodes_in_element):
                index = i // max_nodes_in_element
                nm = "additional_{}".format(i)
                inter_nodes.append(nm)
                str1 += '\twire {};\n'.format(nm)
                if type == 0:
                    str1 += '\tor ('
                else:
                    str1 += '\tand ('
                str1 += nm
                for a in all_terms[index*max_nodes_in_element: (index+1)*max_nodes_in_element]:
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


def mapping_abc(file_name, out_file):
    dfile = get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    equiv_exe = os.path.join(run_path, "equiv_check.exe")
    lib_file = os.path.join(run_path, "lib.genlib")
    sch_file = os.path.join(run_path, file_name)
    if os.path.isfile(out_file):
        os.remove(out_file)

    exe = equiv_exe + " 2 " + lib_file + " " + sch_file + " " + out_file
    try:
        ret = subprocess.check_output(exe, shell=True, cwd=run_path).decode('UTF-8')
    except:
        ret = 'Error: ' + exe
    return ret


def mapping_abc_abc(file_name, out_file):
    dfile = get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    abc_exe = os.path.join(run_path, "abc.exe")
    lib_file = os.path.join(run_path, "lib.genlib")
    sch_file = os.path.join(run_path, file_name)
    if os.path.isfile(out_file):
        os.remove(out_file)
    if os.path.isfile(os.path.join(run_path, 'map.txt')):
        os.remove(os.path.join(run_path, 'map.txt'))

    f = open(os.path.join(run_path, 'map.txt'), 'w')
    f.write('read_library ' + "lib.genlib" + '\n')
    f.write('read ' + file_name + '\n')
    f.write('map\n')
    f.write('write ' + out_file + '\n')
    f.close()
    exe = abc_exe + " -f map.txt"
    try:
        ret = subprocess.check_output(exe, shell=True, cwd=run_path).decode('UTF-8')
    except:
        ret = 'Error: ' + exe
    return ret



def clean_abc_output(circuit_file, synth_file, converted_circuit_file):
    # get module line from initial circuit file
    f = open(circuit_file, "r")
    top_line = f.readline().strip()
    f.close()

    f = open(converted_circuit_file, 'w')
    f.write(top_line + '\n')
    f1 = open(synth_file, 'r')
    content = f1.read()

    # input
    matches_wires = re.findall(r"\s*?((input)\s+(.*?);)", content, re.DOTALL)
    if len(matches_wires) > 0:
        f.write("\tinput ")
        wires = matches_wires[0][2].strip().split(',')
        f.write(wires[0].strip())
        for w in wires[1:]:
            f.write(', ' + w.strip())
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
        for w in wires[1:]:
            f.write(', ' + w.strip())
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
            wire_map[ws] = 'mod_' + ws
        f.write("\twire ")
        lst = sorted(wire_map.keys())
        f.write(wire_map[lst[0]])
        for w in lst[1:]:
            f.write(', ' + wire_map[w])
        f.write(';\n')
    if len(matches_wires) > 1:
        print('Unexpected behaviour! Many wires for ABC.')
        exit()

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


def generate_out_verilog(F, outpins, inpins, out_file):
    f = open(F)
    lines = f.readlines()
    f.close()
    i = 0
    for line in lines:
        if 'endmodule' in line:
            break
        i += 1
    lines = lines[0:i]

    patchline = 'patch p0 ('
    for i in inpins:
        patchline += i + ', '
    patchline += outpins[0]
    for o in outpins[1:]:
        patchline += ', ' + o
    patchline += ');\n'

    lines.append(patchline)
    lines.append('endmodule\n')
    out_verilog = ''.join(lines)
    f = open(out_file, 'w')
    f.write(out_verilog)
    f.close()


def gen_patch_with_abc(truth_tables, target, dnf_cnf):
    # process trivial case
    if truth_tables[0] == []:
        patch = sc.scheme_alt()
        patch.__outputs__ = [target]
        if truth_tables[1] == '1':
            patch.__elements__[target] = ('VCC', [])
        if truth_tables[1] == '0':
            patch.__elements__[target] = ('GND', [])
        return [], patch

    #print('Running ABC synthesis...')
    dfile = get_project_directory()
    if not os.path.isdir(os.path.join(dfile, "temp")):
        os.mkdir(os.path.join(dfile, "temp"))
    circuit_file = os.path.join(dfile, "temp", "tmp_sheme_abc.v")
    synth_file = os.path.join(dfile, "temp", "tmp_abc.v")
    tgt_patch = os.path.join(dfile, "temp", "tgt_patch.v")

    if os.path.isfile(circuit_file):
        os.remove(circuit_file)
    if os.path.isfile(synth_file):
        os.remove(synth_file)

    all_out_nodes = [target]
    all_input_nodes = truth_tables[0]

    out = open(circuit_file, "w")
    out.write("module patch(")
    for o in all_out_nodes:
        out.write(o + ", ")
    out.write(all_input_nodes[0])
    for i in all_input_nodes[1:]:
        out.write(", " + i)
    out.write(");\n")
    for o in all_out_nodes:
        out.write("\toutput {};\n".format(o))
    for i in all_input_nodes:
        out.write("\tinput {};\n".format(i))
    term_count = 0

    if dnf_cnf == 'dnf':
        type = 0
    elif dnf_cnf == 'cnf':
        type = 1
    else:
        print('cant determine type: dnf/cnf')
        type = 0
    term_count = gen_patch_verilog_module_by_basis_and_truth_table_for_abc(target, type, truth_tables[0], truth_tables[1], term_count, out)

    out.write("endmodule\n")
    out.close()

    ret = mapping_abc_abc(circuit_file, synth_file)

    if not os.path.isfile(synth_file):
        # Если была проблема с ABC выводим сообщение
        print('ABC synthesis error!', ret)
        return None, None


    clean_abc_output(circuit_file, synth_file, tgt_patch)
    patch = read_verilog(tgt_patch)
    return patch


def minimize_patch(patch_file):
    dfile = get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    equiv_exe = os.path.join(run_path, "equiv_check.exe")
    lib_file = os.path.join(run_path, "lib.genlib")
    synth_file = os.path.join(dfile, "temp", "final_patch_synth.v")
    clean_synth_file = os.path.join(dfile, "temp", "final_patch_synth_cleaned.v")
    patch_file = os.path.join(dfile, patch_file)
    exe = equiv_exe + " 2 " + lib_file + " " + patch_file + " " + synth_file
    try:
        ret = subprocess.check_output(exe, shell=True, cwd=run_path).decode('UTF-8')
    except:
        ret = 'Error: ' + exe

    clean_abc_output(patch_file, synth_file, clean_synth_file)

    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    shutil.copy(clean_synth_file, sch1_file)
    shutil.copy(patch_file, sch2_file)

    equiv = eq.equivalence_check_abc()
    if equiv == 1:
        shutil.copy(clean_synth_file, patch_file)
        print('Patch minimization: success')
    else:
        print('Patch minimization: failed')

def minimize_patch_abc(patch_file):
    dfile = get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    abc_exe = os.path.join(run_path, "abc.exe")
    lib_file = os.path.join(run_path, "lib.genlib")
    synth_file = os.path.join(dfile, "temp", "final_patch_synth.v")
    clean_synth_file = os.path.join(dfile, "temp", "final_patch_synth_cleaned.v")
    patch_file = os.path.join(dfile, patch_file)

    f = open(os.path.join(run_path, 'map.txt'), 'w')
    f.write('read_library ' + "lib.genlib" + '\n')
    f.write('read ' + patch_file + '\n')
    f.write('map\n')
    f.write('write ' + synth_file + '\n')
    f.close()
    exe = abc_exe + " -f map.txt"
    try:
        ret = subprocess.check_output(exe, shell=True, cwd=run_path).decode('UTF-8')
    except:
        ret = 'Error: ' + exe

    clean_abc_output(patch_file, synth_file, clean_synth_file)

    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    shutil.copy(clean_synth_file, sch1_file)
    shutil.copy(patch_file, sch2_file)

    equiv = eq.equivalence_check_abc()
    if equiv == 1:
        shutil.copy(clean_synth_file, patch_file)
        print('Patch minimization: success')
    else:
        print('Patch minimization: failed')
