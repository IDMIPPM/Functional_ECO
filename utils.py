# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'


import numpy as np
import os
import greedy_search as gs
import copy
import scheme as sc
import networkx as nx


def normalize_weights(weights):
    '''
    Нормализует веса, если стандартное отклонение
    в распределении весов больше 300, прибавляя
    среднее значение ко всем весам
    :param weights: Веса, в виде {Узел:'Вес'}
    :return: Нормализованные веса, в виде {Узел:'Вес'}
    '''
    x = [int(i) for i in list(weights.values())]
    std_dev = np.std(x)
    if std_dev > 300:
        print('Normalizing weights...')
        norm_weights = {key:int(weights[key]) for key in weights}
        avr = sum(list(norm_weights.values())) / len(list(norm_weights.values()))
        norm_weights = {key:str(int(norm_weights[key]+avr)) for key in norm_weights}
    else:
        norm_weights = weights
    return norm_weights


def cone_to_outs(sch, node):
    '''
    Находит все узлы, входящие в конус от
    заданного узла до выходов схемы
    :param sch: Схема в формате scheme_alt
    :param node: Узел схемы вида 'n16'
    :return: Список вентилей, входящих в конус ['n1', 'n2', ...]
    '''
    to_process = [node]
    cone = [node]
    copy_el = dict(sch.__elements__)
    while to_process != []:
        for wire in to_process:
            wire_load = []
            cash=[]
            for el in copy_el:
                if wire in copy_el[el][1]:
                    wire_load.append(el)
                    cash.append(el)
                    cone.append(el)
            for x in range(len(cash)):
                sh = 0
                for y in copy_el:
                    if (cash[x] == y): sh = 1
                if (sh == 1): del copy_el[cash[x]]
            to_process.remove(wire)
            to_process += wire_load
    return list(set(cone))


# List of nodes
def cone_to_outs_v2(sch, node_list):
    '''
    Находит все узлы, входящие в конус от
    заданного узла до выходов схемы
    :param sch: Схема в формате scheme_alt
    :param node: Узел схемы вида 'n16'
    :return: Список вентилей, входящих в конус ['n1', 'n2', ...]
    '''
    to_process = node_list.copy()
    cone = node_list.copy()
    copy_el = dict(sch.__elements__)
    while to_process != []:
        for wire in to_process:
            wire_load = []
            cash=[]
            for el in copy_el:
                    wire_load.append(el)
                    cash.append(el)
                    cone.append(el)
            for x in range(len(cash)):
                sh = 0
                for y in copy_el:
                    if (cash[x] == y): sh = 1
                if (sh == 1): del copy_el[cash[x]]
            to_process.remove(wire)
            to_process += wire_load
    return list(set(cone))


def tgt_influence(scheme, etalon, tgts):
    '''
    Оценивает влияние таргетов на выходы схемы, а также
    влияние входов схемы на таргеты
    :param scheme: схема F в формате scheme_alt
    :param etalon: схема G в формате scheme_alt
    :param tgts: список имен таргетов из схемы F
    :return: возвращает кортеж из
            dependent_outs - непересекающиеся классы зависимостей выходов от таргетов
                            вида {(t_0, t_1):[out1, out2]}
                            (выходы out1 и out2 зависят от таргетов 0 и 1)
            significant_inps - списки входов, значимых для каждого таргета
                            словарь вида {'таргет': ['вход1', 'вход2']}

    '''
    cones = {}
    all_outs = []
    for tgt in tgts:
        cone = cone_to_outs(scheme, tgt)
        cones[tgt] = [val for val in cone if val in scheme.__outputs__]
        all_outs += cones[tgt]
    all_out = list(set(all_outs))
    dependent_outs = {}
    for out in all_out:
        sub_group = []
        for tgt in tgts:
            if out in cones[tgt]:
                sub_group.append(tgt)
        if tuple(sub_group) in dependent_outs:
            dependent_outs[tuple(sub_group)].append(out)
        else:
            dependent_outs[tuple(sub_group)] = [out]
    significant_inps = {}
    for tgt in tgts:
        scheme.__elements__[tgt] = ('GND', [])
    for tgt in tgts:
        sub2 = etalon.subscheme_by_outputs(cones[tgt])
        sub = scheme.subscheme_by_outputs(cones[tgt])
        intersect = [el for el in sub2.__inputs__ if el not in sub.__inputs__]
        #print('SIGNIFICANTEST: ', intersect)
        rest = [el for el in sub2.__inputs__ if el not in intersect]
        significant_inps[tgt] = rest+intersect
    for tgt in tgts:
        scheme.__elements__.__delitem__(tgt)
    return dependent_outs, significant_inps


def get_project_directory():
    project_directory = os.path.abspath(os.path.dirname(__file__))
    return project_directory


def form_weights(weights, nodes_list, overall_basis, current_basis):
    current_weights = {}
    if current_basis == None:
        current_basis = []

    for node in nodes_list:
        if node in weights:
            if node in overall_basis:
                current_weights[node] = 0  # minimum weight for existing nodes
            elif node in current_basis:
                current_weights[node] = 0  # minimum weight for previous iteration
            else:
                current_weights[node] = weights[node]
    return current_weights


def form_tt(signatures, basis, target_vector, dnf_cnf):
    #print('Forming truth table...')
    tt = gs.cons_check(signatures, basis, target_vector)
    #print('Minimizing...')
    minimized_tt = {}
    if basis != []:
        if dnf_cnf == 'dnf':
            # minimized_tt = run_espresso_dnf((basis, tt))
            minimized_tt[0] = tt[1]
        elif dnf_cnf == 'cnf':
            minimized_tt[0] = tt[0]
            # minimized_tt = run_espresso_cnf((basis, tt))
    else:
        if tt[0] == ['']:
            minimized_tt = ['0']
        elif tt[1] == ['']:
            minimized_tt = ['1']
    return minimized_tt


def patch_circuit(scheme, patch):
    renamed_patch = sc.scheme_alt()
    renamed_patch.__inputs__ = copy.deepcopy(patch.__inputs__)
    renamed_patch.__outputs__ = copy.deepcopy(patch.__outputs__)
    postfix = '_' + '_'.join(patch.__outputs__)
    for elem in patch.__elements__:
        if elem in patch.__outputs__:
            element = elem
        else:
            element = elem+postfix

        type = patch.__elements__[elem][0]
        ports = []
        for port in patch.__elements__[elem][1]:
            if port in patch.__inputs__:
                ports.append(port)
            elif port in patch.__outputs__:
                ports.append(port)
            else:
                ports.append(port + postfix)
        renamed_patch.__elements__[element] = (type, ports)
    patched = copy.deepcopy(scheme)
    for gate in renamed_patch.__elements__:
        patched.__elements__[gate] = renamed_patch.__elements__[gate]
    return patched


def patch_merger(patches):
    patchlist = []
    for target in patches:
        patchlist.append(patches[target][0])
    all_inps = []
    all_outs = []
    for patch in patchlist:
        all_inps += patch.__inputs__
        all_outs += patch.__outputs__
    all_inps = list(set(all_inps))
    all_outs = list(set(all_outs))
    final_patch = sc.merge_schemes(patchlist, [], [])
    final_patch.__inputs__ = all_inps
    final_patch.__outputs__ = all_outs
    return final_patch


def calculate_score(basis, weights):
    score = 0
    for node in basis:
        # If some error case
        if node not in weights:
            return 1000000000
        score += int(weights[node])
    return score


def shuffle_inputs(scheme, etalon, sign_inps):
    for inp in sign_inps:
        scheme.__inputs__.remove(inp)
        scheme.__inputs__ = [inp] + scheme.__inputs__
    etalon.__inputs__ = scheme.__inputs__.copy()
    return scheme, etalon


def flatten(dict):
    res = []
    for key in sorted(dict):
        res += dict[key]
    return res


def construct_graph_from_circuit(cir):
    G = nx.Graph()
    for el in cir.__inputs__:
        G.add_node(el)
    for el in cir.__outputs__:
        G.add_node(el)
    for el in cir.__elements__:
        for c in cir.__elements__[el][1]:
            G.add_edge(c, el)
    # print(list(G.nodes()))
    # print(list(G.edges()))
    # shp = nx.shortest_path(G, 't_0', 'y1')
    # print(shp)
    # exit()
    return G


def get_closest_nodes_to_basis(graph, basis, weights, limit):
    closest = [[]]*len(basis)
    for i in range(len(basis)):
        closest[i] = []
        node = basis[i]
        paths = nx.shortest_path(graph, source=node)
        for p in paths.keys():
            dst = len(paths[p])-1
            if dst < limit:
                if p not in basis:
                    if p in weights:
                        add = (p, dst)
                        closest[i].append(add)
    return closest


def tgts4formal(scheme, targets):
    '''
    :param scheme: scheme in scheme_alt format 
    :param targets: list of targets
    :return: list of targets, suitable for formal evaluation
    '''
    formal = {}
    attempt = 0
    for target in targets:
        next_net = copy.copy(target)
        wires_list = []
        while 1:
            # search for next net
            got_it = 0
            for el in scheme.__elements__:
                if next_net in scheme.__elements__[el][1]:
                    # нашли проводок
                    if got_it == 1:
                        # найдено разветвление
                        got_it = 0
                        break
                    else:
                        attempt = copy.copy(el)
                        got_it = 1
            if got_it == 1:
                next_net = attempt
                wires_list.append(next_net)
                if next_net in scheme.__outputs__:
                    # дошли до выхода
                    formal[target] = copy.copy(wires_list)
                    break
            else:
                break
    return formal


def formal_patch_creation(scheme, etalon, formal, target):
    wires = copy.copy(formal[target])
    wires.reverse()
    sch = etalon.subscheme_by_outputs([wires[0]])
    patch = copy.deepcopy(sch)
    # переиминовываем внутренние провода
    for el in sch.__elements__:
        temp = sch.__elements__[el]
        ports = []
        for port in temp[1]:
            if port not in sch.__inputs__:
                ports.append('mod_'+port)
            else:
                ports.append(port)
        patch.__elements__.__delitem__(el)
        patch.__elements__['mod_'+el] = (temp[0], ports)
    wires.append('tgt')
    temp = copy.deepcopy(patch.__elements__['mod_'+patch.__outputs__[0]])
    patch.__elements__.__delitem__('mod_'+patch.__outputs__[0])
    patch.__elements__['g_out'] = temp
    patch.__outputs__ = [target]
    previous_name = 'g_out'
    i = 0
    for element in wires[:-1]:
        name = 'ptch_' + element
        if scheme.__elements__[element][0] == 'AND':
            temp = copy.deepcopy(patch.__elements__[previous_name])
            patch.__elements__.__delitem__(previous_name)
            patch.__elements__[name] = temp
            previous_name = copy.copy(name)
        elif scheme.__elements__[element][0] == 'NAND':
            patch.__elements__[name] = ('INV', [previous_name])
            previous_name = copy.copy(name)
        elif scheme.__elements__[element][0] == 'OR':
            temp = copy.deepcopy(patch.__elements__[previous_name])
            patch.__elements__.__delitem__(previous_name)
            patch.__elements__[name] = temp
            previous_name = copy.copy(name)
        elif scheme.__elements__[element][0] == 'NOR':
            patch.__elements__[name] = ('INV', [previous_name])
            previous_name = copy.copy(name)
        elif scheme.__elements__[element][0] == 'XOR':
            ports = copy.deepcopy(scheme.__elements__[element][1])
            ext_nodes = ports.remove(wires[i+1])
            patch.__inputs__ += ext_nodes
            patch.__elements__[name] = ('XOR', [previous_name] + ext_nodes)
            previous_name = copy.copy(name)
        elif scheme.__elements__[element][0] == 'XNOR':
            ports = copy.deepcopy(scheme.__elements__[element][1])
            ext_nodes = ports.remove(wires[i+1])
            patch.__inputs__ += ext_nodes
            patch.__elements__[name] = ('XNOR', [previous_name] + ext_nodes)
            previous_name = copy.copy(name)
        elif scheme.__elements__[element][0] == 'INV':
            patch.__elements__[name] = ('INV', [previous_name])
            previous_name = copy.copy(name)
        elif scheme.__elements__[element][0] == 'BUF':
            temp = copy.deepcopy(patch.__elements__[previous_name])
            patch.__elements__.__delitem__(previous_name)
            patch.__elements__[name] = temp
            previous_name = copy.copy(name)
        i+=1
    temp = copy.deepcopy(patch.__elements__[previous_name])
    patch.__elements__.__delitem__(previous_name)
    patch.__elements__[target] = temp
    patch.__inputs__ = list(sorted(set(patch.__inputs__)))
    return patch


if __name__ == '__main__':
    import read_write as rw
    tgts, F = rw.read_verilog('testcases\\unit11\\F.v')
    _, G = rw.read_verilog('testcases\\unit11\\G.v')
    formal = tgts4formal(F, tgts)
    patch = formal_patch_creation(F, G, formal, 't_4')
    patch.print_verilog_in_file('ptch.v', 'formal')
    print(patch)