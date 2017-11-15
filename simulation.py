# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'

import random
import itertools
import copy
import utils as u
from sys import platform
import read_write as rw
import os


def random_stimulus(inp_num, capacity):
    stimulus = [random.randrange(0, 2 ** capacity - 1) for _ in range(inp_num)]
    return stimulus


def exhaustive_stimulus(inp_num):
    capacity = 2**inp_num
    tmp=1
    res = []
    for i in range(inp_num-1, -1, -1):
        res.append((2 ** (2 ** i) - 1)*tmp)
        tmp = tmp*(1+2**(2**i))
    return (res, capacity)


def pseudo_random_stimulus(inp_num):
    if inp_num < 16:
        return exhaustive_stimulus(inp_num)
    exh_part = exhaustive_stimulus(13)
    rnd_part = random_stimulus(inp_num-13, 2**13)
    res = exh_part[0] + rnd_part
    return res, exh_part[1]


def simulate_outputs(scheme, capacity, stimulus=[]):
    """
    function to simulate outputs
    :param scheme: scheme under test in scheme_alt format
    :param capacity: number of bits for simultaneous modeling
    :return: returns list of tuples [(node_name, num), ...] num - decimal reaction on stimulus
    """
    if stimulus == []:
        stimulus = random_stimulus(scheme.inputs(), capacity)
    reaction = scheme.process(stimulus, [], capacity)
    res = {}
    for i in range(len(reaction)):
        react = "{0:b}".format(reaction[i])
        react = '0'*(capacity - len(react)) + react
        res[scheme.__outputs__[i]] = react

    #res = list(zip(scheme.__outputs__, reaction))
    return res


def form_target_array(scheme, etalon, capacity, tgts, stimulus):
    etalon_reply = simulate_outputs(etalon, capacity, stimulus)
    reply = {}
    for vector in itertools.product((0, 1), repeat=len(tgts)):
        #print('Target vector: {}'.format(vector))
        # Forming design under test
        dut = copy.deepcopy(scheme)
        for i in range(len(tgts)):
            if vector[i] == 0:
                dut.__elements__[tgts[i]] = ('GND', [])
            if vector[i] == 1:
                dut.__elements__[tgts[i]] = ('VCC', [])
        reply[vector] = simulate_outputs(dut, capacity, stimulus)
    outputs = list(etalon_reply.keys())
    length = len(etalon_reply[outputs[0]])
    tgt_vecs = list(reply.keys())
    target_array = []
    for i in range(length):
        etal = ''
        for out in outputs:
            etal += etalon_reply[out][i]
        fits = []
        for tgt_vec in tgt_vecs:
            cand = ''
            for out in outputs:
                cand += reply[tgt_vec][out][i]
            if cand == etal:
                fits.append(tgt_vec)
        target_array.append(fits)

    return target_array


def reduce_stimulus(stimulus, target_array, capacity):
    input_number = len(stimulus)
    max_d_c = 2**len(target_array[0][0])
    new_target_array = []
    new_stimulus = [0]*input_number
    new_capacity = 0

    for i in range(len(target_array) - 1, -1, -1):
        target_variant = target_array[i]
        if len(target_variant) != max_d_c:
            new_target_array.append(target_variant)
            cap2 = (1 << new_capacity)
            for j in range(input_number):
                current_bit = (stimulus[j] >> (capacity - i - 1)) & 1
                if current_bit:
                    new_stimulus[j] += cap2
            new_capacity += 1

    new_target_array = new_target_array[::-1]
    return new_stimulus, new_target_array, new_capacity


def critical_stimulus(stimulus, target_array, capacity):
    input_number = len(stimulus)
    new_stimulus = [0]*input_number
    new_capacity = 0

    for i in range(len(target_array) - 1, -1, -1):
        target_variant = target_array[i]
        if len(target_variant) == 0:
            cap2 = (1 << new_capacity)
            for j in range(input_number):
                current_bit = (stimulus[j] >> (capacity - i - 1)) & 1
                if current_bit:
                    new_stimulus[j] += cap2
            new_capacity += 1
    return new_stimulus, new_capacity


def form_nodes_list(scheme, tgts):
    nodes_list = []
    for target in tgts:
        nodes_list += u.cone_to_outs(scheme, target)
    exclude = list(set(nodes_list))
    nodes_list = [item for item in scheme.element_labels() if item not in exclude]
    full_nodes_list = nodes_list + scheme.input_labels()
    #print('Total elements:', scheme.elements(), ' Used wires: ', len(nodes_list))
    return full_nodes_list

def form_nodes_list2(scheme, tgts, all_sign_inps):
    nodes_list = []
    for target in tgts:
        nodes_list += u.cone_to_outs(scheme, target)
    exclude = list(set(nodes_list))
    infl_list = u.cone_to_outs_v2(scheme, all_sign_inps)
    nodes_list = [item for item in infl_list if item not in exclude]
    full_nodes_list = nodes_list + scheme.input_labels()
    #print('Total elements:', scheme.elements(), ' Used wires: ', len(nodes_list))
    return nodes_list


def form_dut(scheme, dut, etalon, patches):
    # Forming design under test
    inp_order = dut.__inputs__
    dut = copy.deepcopy(scheme)
    tgts = sorted(patches)
    for tgt in tgts:
        if patches[tgt] == None:
            dut.__elements__[tgt] = ('GND', [])
        else:
            dut = u.patch_circuit(dut, patches[tgt][0])
    dut.__inputs__ = inp_order
    etalon.__inputs__ = inp_order
    return dut, etalon


def simulate_all_nodes(scheme, capacity, stimulus):
    """
    function to simulate all nodes
    :param scheme: scheme under test in scheme_alt format
    :param capacity: number of bits for simultaneous modeling
    :return: returns list of tuples [(node_name, num), ...] num - decimal reaction on stimulus
    """
    if capacity == 0:
        return 0
    init_outs = copy.deepcopy(scheme.__outputs__)
    scheme.__outputs__ = scheme.element_labels()
    reaction = scheme.process(stimulus, [], capacity)
    res = {}
    for i in range(len(reaction)):
        res[scheme.__outputs__[i]] = reaction[i]

    for i in range(scheme.inputs()):
        res[scheme.__inputs__[i]] = stimulus[i]
    scheme.__outputs__ = copy.deepcopy(init_outs)
    return res


def get_target_vector(target_array, capacity, pos):

    target_vector = ''  # Basic vector for target
    for i in range(capacity):
        # forming target_vector from target_array
        tmp = []
        for tgt_variant in target_array[i]:
            tmp.append(tgt_variant[pos])
        if 0 in tmp:
            if 1 in tmp:
                target_vector += 'x'
            else:
                target_vector += '0'
        elif 1 in tmp:
            target_vector += '1'
        else:
            print('ERROR: UNABLE TO BUILD TARGET VECTOR')
            exit()
    return target_vector


# We just replace 'x' on '0'
def prepare_reduced_arrays_v6(signatures, target_vector):
    '''
    :param signatures: dict of big python integers
    :param target_vector: vector of following form '001010xx0x1'
    :return: return signatures with bits removed in positions where target == 'x'
    '''

    # Invert target vector
    target_vector = target_vector[::-1]
    target_vector = target_vector.replace('x', '0')
    capacity = len(target_vector)
    new_cap_checker = capacity - target_vector.count('x')

    # Recalculate target
    target = 0
    new_capacity = 0
    for i in range(capacity):
        if target_vector[i] == 'x':
            continue
        cap2 = (1 << new_capacity)
        if target_vector[i] == '1':
            target |= cap2
        new_capacity += 1
    if new_capacity != new_cap_checker:
        print('Some error here!')
        exit()

    return copy.deepcopy(signatures), target, new_capacity

# Change only inputs, then simulate from begining
def prepare_reduced_arrays_v7(scheme, signatures, target_vector):
    '''
    :param signatures: dict of big python integers
    :param target_vector: vector of following form '001010xx0x1'
    :return: return signatures with bits removed in positions where target == 'x'
    '''

    tv = target_vector[::-1]
    capacity = len(tv)
    reply = dict()
    for el in signatures:
        reply[el] = 0
    new_cap_checker = capacity - target_vector.count('x')

    stimulus = [0]*len(scheme.__inputs__)

    # Recreate target and remove x
    new_capacity = 0
    target = 0
    for i in range(capacity):
        if tv[i] == 'x':
            continue
        cap2 = (1 << new_capacity)
        if tv[i] == '1':
            target |= cap2
        for j in range(len(scheme.__inputs__)):
            el = scheme.__inputs__[j]
            current_bit = (signatures[el] >> i) & 1
            if current_bit:
                stimulus[j] |= cap2
        new_capacity += 1

    if new_capacity != new_cap_checker:
        print('Some error here!')
        exit()

    reply = simulate_all_nodes(scheme, new_capacity, stimulus)

    return reply, target, new_capacity


def reduce_target_array(scheme, signatures, target_vector):
    if 'x' not in target_vector:
        reply, target, capacity = prepare_reduced_arrays_v6(signatures, target_vector)
    else:
        reply, target, capacity = prepare_reduced_arrays_v7(scheme, signatures, target_vector)
    return reply, target, capacity


def simulate_miter(capacity, input_order):
    ostype = "win32"
    if platform == "linux":
        ostype = "linux"
    path = os.path.join("equiv_check", ostype, 'miter.v')
    inp, sch = rw.read_AIG_verilog(path)
    #print('Number of conflicted inputs in miter: {} out of {}'.format(len(inp), len(input_order)))
    print('...')
    sch.__inputs__ = input_order
    if 2**len(inp) < capacity:
        print('Generate all possible variants in mitter...')
        (stimulus, capacity) = exhaustive_stimulus(len(inp))
    else:
        stimulus = random_stimulus(len(inp), capacity)
    inp_vector = []
    matrix = []
    for i in sch.__inputs__:
        if i in inp:
            stimul = stimulus.pop()
            inp_vector.append(stimul)
            vec = "{0:b}".format(stimul)
            vec = '0' * (capacity - len(vec)) + vec
            matrix.append(vec)
        else:
            inp_vector.append(0)
            matrix.append(0)
    if sch.__elements__ == {}:
        return []
    miter = sch.process(inp_vector, [], capacity)
    miter = "{0:b}".format(miter[0])
    miter = '0' * (capacity - len(miter)) + miter
    ind = 0
    result = []
    for i in miter:
        if i == '1':
            stimul = ''
            for vec in matrix:
                if vec == 0:
                    stimul += '0'
                else:
                    stimul += vec[ind]
            result.append(stimul)
        ind += 1
    return result


def convert_stimuli(sim):
    stimuli = [0]*len(sim[0])
    for i in range(len(sim)):
        s = sim[i]
        sum = 1 << i
        for j in range(len(stimuli)):
            if s[j] == '1':
                stimuli[j] += sum
    return stimuli, len(sim)