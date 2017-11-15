# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'


import utils as u
from sys import platform
import os
import subprocess
import re
import shutil
import simulation as sim
import scheme as sc
import read_write as rw


def patch_circuit(scheme_file, patch_file, etalon_file):
    '''
    Формируем файлы sch1.v и sch2.v в директории для проверки на эквивалентность
    :param out_file: Файл на базе файла F.v с вызовом патча
    :param patch_file: Файл патча
    :param etalon_file: Эталонный файл G.v
    :return:
    '''
   #print('Patching circuit...')
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    if os.path.isfile(sch1_file):
        os.remove(sch1_file)
    if os.path.isfile(sch2_file):
        os.remove(sch2_file)

    patch = rw.read_verilog(patch_file)
    scheme = rw.read_verilog(scheme_file)
    patched = u.patch_circuit(scheme[1], patch[1])
    patched.print_verilog_in_file(sch1_file, 'top')

    f = open(etalon_file)
    etalon = f.read()
    f.close()

    out = open(sch2_file, "w")
    out.write(etalon)
    out.close()


def equivalence_check():
    '''
    Проводим проверку на эквивалентность двух схем в директории
    equiv_check/win32(linux) - sch1.v и sch2.v
    :return: возвращаем 1 - в случае эквивалентности
                        0 - в обратном случае
                        сообщение об ошибке - при ошибке
    '''
    #print('Running equivalence check...')
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    equiv_exe = os.path.join(run_path, "equiv_check.exe")
    s1_path = 'sch1.v'
    s2_path = 'sch2.v'
    if platform == "linux":
        s1_path = os.path.join(run_path, 'sch1.v')
        s2_path = os.path.join(run_path, 'sch2.v')

    exe = equiv_exe + " 1 " + s1_path + " " + s2_path + " "
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
        #print('Schemes are NOT equivalent')
        return 0
    elif 'EQUIVALENT' in ret:
        #print('Schemes are equivalent')
        return 1
    else:
        #print('EQUIVALENCE CHECK FAILED')
        print(ret)
        return None


def equivalence_check_abc():
    '''
    Проводим проверку на эквивалентность двух схем в директории
    equiv_check/win32(linux) - sch1.v и sch2.v
    :return: возвращаем 1 - в случае эквивалентности
                        0 - в обратном случае
                        сообщение об ошибке - при ошибке
    '''
    #print('Running equivalence check...')


    '''
     Проводим проверку на эквивалентность двух схем в директории
     equiv_check/win32(linux) - sch1.v и sch2.v
     :return: возвращаем 1 - в случае эквивалентности
                         0 - в обратном случае
                         сообщение об ошибке - при ошибке
     '''
    # print('Running equivalence check...')
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    s1_path = 'sch1.v'
    s2_path = 'sch2.v'
    check_txt = 'check.txt'
    if platform == "linux":
        s1_path = os.path.join(run_path, 'sch1.v')
        s2_path = os.path.join(run_path, 'sch2.v')
        check_txt = os.path.join(run_path, "check.txt")
    abc_exe = os.path.join(run_path, "abc.exe")

    f = open(os.path.join(run_path, 'check.txt'), 'w')
    f.write('cec ' + s1_path + ' ' + s2_path +'\n')
    f.close()
    # print('OK')
    # exit()
    # checking...
    exe = abc_exe + " -f " + check_txt
    try:
        if platform == "linux":
            ret = subprocess.check_output(exe, cwd=run_path, shell=True, timeout=60).decode('UTF-8')
        else:
            ret = subprocess.check_output(exe, cwd=run_path, timeout=60).decode('UTF-8')
    except subprocess.TimeoutExpired:
        ret = 'Error: ' + exe
        print('Timeout')
    except:
        ret = 'Error: ' + exe + ' Working dir:' + run_path
    # print(ret)
    if 'NOT EQUIVALENT' in ret:
        #print('Schemes are NOT equivalent')
        result = 0
    elif 'are equivalent' in ret:
        #print('Schemes are equivalent')
        result = 1
    else:
        #print('EQUIVALENCE CHECK FAILED')
        print(ret)
        result = None
    if os.path.isfile(s1_path):
        os.remove(s1_path)
    if os.path.isfile(s2_path):
        os.remove(s2_path)
    return result


def define_outs(outs_to_check):
    #print('Correcting outputs...')
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    if not os.path.isfile(sch1_file):
        print('ERROR: sch1.v not found...')
        return 0
    if not os.path.isfile(sch2_file):
        print('ERROR: sch2.v not found...')
        return 0

    f = open(sch1_file)
    sch1 = f.read()
    # парсинг модуля и портов
    m = re.match(r"\s*module\s+(\S+)\s+\(((\s*\S+\s*,)*\s*\S+\s*)\)\s*;\s*", sch1)
    if m:
        ports = m.group(2)
        ports = ports.replace(' ', '')
        ports = ports.split(',')
        module_name = m.group(1)
        rest = sch1[0:m.start()] + sch1[m.end():len(sch1)]

    # парсинг входов
    m = re.match(r"\s*input\s+((\s*\S+\s*,)*\s*\S+\s*)\s*;\s*", rest)
    if m:
        inputs = m.group(1)
        inputs = inputs.replace(' ', '')
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
    f.close()

    # формирование правильного заголовка
    ports = [port for port in ports if port in outs_to_check+inputs]
    wires = [wire for wire in outputs if wire not in outs_to_check]
    outputs = [output for output in outputs if output in outs_to_check]
    head = ''
    head += 'module top ( ' + ', '.join(ports) + ' );\n'
    head += 'input ' + ', '.join(inputs) + ';\n'
    head += 'output ' + ', '.join(outputs) + ';\n'
    if wires != []:
        head += 'wire ' + ', '.join(wires) + ';\n'
    head += 'wire '

    # формирование конечного содержания файлов
    f = open(sch1_file)
    sch = f.read()
    sch = sch.split('wire ', 1)
    newsch1 = head + sch[-1]
    f.close()
    f = open(sch2_file)
    sch = f.read()
    sch = sch.split('wire ', 1)
    newsch2 = head + sch[-1]
    f.close()

    # запись в те же файлы
    # os.remove(sch1_file)
    # os.remove(sch2_file)
    out = open(sch1_file, "w")
    out.write(newsch1)
    out.close()
    out = open(sch2_file, "w")
    out.write(newsch2)
    out.close()

    if not os.path.isfile(sch1_file):
        print('ERROR: sch1.v not found...')
        return 0
    if not os.path.isfile(sch2_file):
        print('ERROR: sch2.v not found...')
        return 0


def check_clean_outputs(F, G, eq_outs):
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    print('Copy {} to {}'.format(F, sch1_file))
    shutil.copy(F, sch1_file)
    shutil.copy(G, sch2_file)
    if not os.path.isfile(sch1_file):
        print('Couldnt copy verilog file sch1.v')
    if not os.path.isfile(sch2_file):
        print('Couldnt copy verilog file sch2.v')
    define_outs(eq_outs)
    return equivalence_check_abc()


def check_some_outputs(scheme, etalon, patch, outputs):
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")

    patched = u.patch_circuit(scheme, patch)
    patched.print_verilog_in_file(sch1_file, 'top')
    etalon.print_verilog_in_file(sch2_file, 'top')
    define_outs(outputs)
    return equivalence_check_abc()


def create_miter(scheme, etalon, patch, outputs):
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    equiv_exe = os.path.join(run_path, "equiv_check.exe")

    patched = u.patch_circuit(scheme, patch)
    patched.print_verilog_in_file(sch1_file, 'top')
    etalon.print_verilog_in_file(sch2_file, 'top')
    define_outs(outputs)
    exe = equiv_exe + " 0 " + " sch1.v " + " sch2.v "
    try:
        ret = subprocess.check_output(exe, shell=True, cwd=run_path).decode('UTF-8')
    except:
        ret = 'Error:' + exe + 'Run path:' + run_path
        print(ret)


def create_miter_abc(scheme, etalon, patch, outputs):
    dfile = u.get_project_directory()
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    run_path = os.path.join(dfile, "equiv_check", ostype)
    sch1_file = os.path.join(run_path, "sch1.v")
    sch2_file = os.path.join(run_path, "sch2.v")
    abc_exe = os.path.join(run_path, "abc.exe")

    patched = u.patch_circuit(scheme, patch)
    patched.print_verilog_in_file(sch1_file, 'top')
    etalon.print_verilog_in_file(sch2_file, 'top')
    define_outs(outputs)
    exe = abc_exe + " -f miter.txt"
    try:
        ret = subprocess.check_output(exe, shell=True, cwd=run_path).decode('UTF-8')
    except:
        ret = 'Error:' + exe + 'Run path:' + run_path
        print(ret)



def mittering(capacity, input_order, verbose):
    sim_num = 0
    stim = sim.simulate_miter(1000, input_order)
    if len(stim) > 10:
        if verbose:
            print('Overflow...')
        return []
    while 1:
        stim = sim.simulate_miter(capacity, input_order)
        sim_num += 1
        if sim_num > 7:
            return []
        if len(stim) > 0:
            if verbose:
                print('Additional simulations from mitter: {}'.format(len(stim)))
            if len(stim) > 10000:
                return []
            else:
                return stim