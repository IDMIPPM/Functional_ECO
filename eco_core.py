# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'


import random
import sys
import time
import os
import read_write as rw
import utils as u
import eq_check as eq
import simulation as sim
import greedy_search as gs
import copy
from postprocess_patch_minimizer import minimize_patch_weights
import scheme as sc
from pprint import pprint
from collections import defaultdict


DONT_CUT_CIRCUIT_FOR_SINGLE_TARGET_BLOCK = 1


def choose_next_target(dep_outputs, resolved_tgts, tgts2resolve):
    dep_outs = copy.deepcopy(dep_outputs)
    min = 100
    max = 0
    cur_dep = {}
    outs2resolve = []
    for group in sorted(dep_outs):
        new_group = []
        for tgt in group:
            if tgt not in resolved_tgts:
                new_group.append(tgt)
        if new_group != []:
            if tuple(new_group) in cur_dep:
                cur_dep[tuple(new_group)]+=dep_outs[group]
            else:
                cur_dep[tuple(new_group)] = dep_outs[group]
        else:
            outs2resolve += dep_outs[group]
    if cur_dep == {}:
        return 0
    for group in sorted(cur_dep):
        length = len(group)
        if length < min:
            min = length
    for group in sorted(cur_dep):
        if len(group) == min:
            length = len(cur_dep[group])
            if length > max:
                max = length
                tgts = group
    tgt = random.choice(tgts)
    # tgt = random.choice(tgts2resolve)
    if (tgt,) in cur_dep:
        outs2resolve = cur_dep[(tgt,)]
    else:
        outs2resolve = []
    return outs2resolve, tgt, cur_dep


def init_basic_structures(tgts):
    truth_tables = {}
    patches = {}
    for tgt in sorted(tgts):
        patches[tgt] = None
    return patches


def search4bases(weights, reply, target_vector_int, cap, mit, verbose):
    bases = []
    scores = []
    if cap == 0:
        return [[]]

    #if mit == 0:
        # backward greedy
        #if verbose:
        #    print('\n\n=====================backward greedy=============================')
        #basis = gs.backward_greedy_search(weights, reply.copy(), target_vector_int, cap, verbose)
        #basis = gs.remove_not_needed_nodes(basis, weights, reply, target_vector_int, cap, verbose)
        #if len(basis) < 19:
        #    basis, scors = gs.multi_replacer(basis, weights, reply, target_vector_int, cap, 3, verbose)
        #    scores += scors
        #    bases += basis

    if mit == 0:
        if verbose:
            print('\n\n=====================absolute greedy=============================')
        # forward greedy absolute
        basis = gs.greedy_search(weights, reply.copy(), target_vector_int, cap, 'absolute', verbose)
        basis = gs.remove_not_needed_nodes(basis, weights, reply, target_vector_int, cap, verbose)
        if len(basis) < 19:
            if len(basis) < 15:
                basis, scors = gs.multi_replacer(basis, weights, reply, target_vector_int, cap, 1, verbose)
            else:
                scors = [u.calculate_score(basis, weights)]
                basis = [basis]
            scores += scors
            bases += basis

    if verbose:
        print('\n\n=====================weighted greedy=============================')
    # forward greedy weighted
    basis = gs.greedy_search(weights, reply.copy(), target_vector_int, cap, 'weighted', verbose)
    basis = gs.remove_not_needed_nodes(basis, weights, reply, target_vector_int, cap, 1)
    if len(basis) < 19:
        if len(basis) < 15:
            basis, scors = gs.multi_replacer(basis, weights, reply, target_vector_int, cap, 1, verbose)
        else:
            scors = [u.calculate_score(basis, weights)]
            basis = [basis]
        scores += scors
        bases += basis
    # sorting
    while None in bases:
        bases.remove(None)
    while None in scores:
        scores.remove(None)
    bases = sorted(bases, key=lambda k:scores[bases.index(k)])
    print('Bases list:', bases)
    return bases


def patches_generator(bases, signatures, target_vector, target):
    patches = []

    # тривиальные случаи
    if target_vector == 'x' * len(target_vector):
        patch = sc.scheme_alt()
        patch.__outputs__ = [target]
        patch.__elements__[target] = ('GND', [])
        patches.append(patch)
        patch = sc.scheme_alt()
        patch.__outputs__ = [target]
        patch.__elements__[target] = ('VCC', [])
        patches.append(patch)
        return patches

    for basis in bases:
        # ищем таблицу истинности
        tt_dnf = u.form_tt(signatures, basis, target_vector, 'dnf')
        tt_cnf = u.form_tt(signatures, basis, target_vector, 'cnf')

        # генерируем патч для текущего таргета
        _, patch_dnf = rw.gen_patch_with_abc((basis, tt_dnf[0]), target, 'dnf')
        _, patch_cnf = rw.gen_patch_with_abc((basis, tt_cnf[0]), target, 'cnf')
        patches.append(patch_dnf)
        patches.append(patch_cnf)
    return patches


def eq_check_patches(dut, etalon, patches, outs2resolve):
    ok_fail_lst = []
    for patch in patches:
        eql = eq.check_some_outputs(dut, etalon, patch, outs2resolve)
        if eql == 1:
            ok_fail_lst.append('OK')
        else:
            ok_fail_lst.append('FAIL')
    return ok_fail_lst


def choose_patch4miter(dut, etalon, patches, outs2resolve):
    best_stim = 1000000
    best_patch = patches[0]
    out_stim = []
    i = 0

    for patch in patches:
        i+=1
        sys.stdout.write('\nCreating mitter...')
        sys.stdout.flush()
        eq.create_miter_abc(dut, etalon, patch, outs2resolve)
        print(' done')

        print('Simulating mitter for patch N', i, '...')
        stim = eq.mittering(1000000, dut.__inputs__, 1)
        if stim == []:
            cur_stim = 1000000
        else:
            cur_stim = len(stim)
        if cur_stim < best_stim:
            out_stim = stim
            best_patch = patch
            best_stim = cur_stim
        print('done')
    return out_stim, [best_patch]


def get_patch_for_independent_target_list(tgts, scheme, etalon, weights, time_limit=1000000):
    Bk = '\033[0m'   # normal
    Rd = '\033[31m'  # red
    Wh = '\033[37m'  # white
    Bl = '\033[34m'  # blue

    start = time.time()
    dep_outs, sign_inps = u.tgt_influence(scheme, etalon, tgts)
    all_sign_inps = list(set([item for sublist in list(sign_inps.values()) for item in sublist]))
    outs_to_process = [item for sublist in list(dep_outs.values()) for item in sublist]
    eq_outs = [out for out in scheme.__outputs__ if out not in outs_to_process]
    formal = u.tgts4formal(scheme, tgts)
    print('STATS:')
    print(' Targets: ', len(tgts))
    print('     Suitable for formal evaluation: ', len(formal), ' (', list(formal),')')
    print(' Inputs: ', scheme.inputs())
    print(' Outputs: ', scheme.outputs())
    print(' Elements: ', scheme.elements())
    print(' Elements etalon: ', etalon.elements())
    print(' Significant: ')
    print('     Inputs: ', len(all_sign_inps))
    print('     Outputs: ', len(outs_to_process))
    print(' Dependencies:')
    pprint(dep_outs)
    print('================================================================')

    # инициализация
    sys.stdout.write('Initializing variables...')
    sys.stdout.flush()
    patches = init_basic_structures(tgts)               # пустые заготовки под патчи
    resolved_tgts = []                                  # заготовка под обработанные таргеты
    tgts2resolve = tgts.copy()                          # заготовка под НЕобработанные таргеты
    mit = 0                          # флаг - текущая итерация - миттеринг или нет?
    iter = 0
    attempt = 0
    target = None
    stimulus = []
    dut = copy.deepcopy(scheme)
    print(' done')

    # формируем список узлов для работы
    sys.stdout.write('Forming nodes list...')
    sys.stdout.flush()
    #nodes_list = sim.form_nodes_list(scheme, tgts)
    nodes_list = sim.form_nodes_list2(scheme, tgts, all_sign_inps)
    print(' done\n')
    # =============================================================
    # базовый цикл, заканчивающийся полностью эквивалентным патчем
    # =============================================================
    while 1:
        if time.time() - start > time_limit:
            print(Rd+'...TIME EXCEEDED...')
            return None
        iter += 1
        print(Bk+'================================================================')
        print(Rd+'                     Iteration N', iter)
        print(Bk+'================================================================')
        if mit == 1:
            attempt = 0
            print(Rd + '                     MITTERING\n' + Bk)

        # выбираем таргет и выходы, которые можно будет однозначно проверить после решения данного таргета
        if mit == 0:
            old_target = copy.copy(target)
            outs2resolve, target, cur_dep = choose_next_target(dep_outs, resolved_tgts, tgts2resolve)
            if target == old_target:
                attempt += 1
            else:
                attempt = 0
            if attempt > 2:
                print(Bk + '================================================================')
                print(Rd + '            Iterations Limit Exceeded for Target ', target)
                print(Bk + '================================================================\n')
                tgts2reset = []
                for dep in dep_outs:
                    if target in dep:
                        temp = list(dep)
                        temp.remove(target)
                        tgts2reset += temp
                temp = [el for el in resolved_tgts if el in tgts2reset]
                tgts2reset = temp
                print(Bk + 'reseting all dependent targets...\n' + ', '.join(tgts2reset))
                resolved_tgts = [el for el in resolved_tgts if el not in tgts2reset]
                tgts2resolve += tgts2reset
                for tgt in tgts2reset:
                    patches[tgt] = None
                attempt = 0
                target = None
                continue
        unresolved_outputs = u.flatten(cur_dep)
        print(Wh+'Outputs left to resolve: ', Bk, len(unresolved_outputs), ':   ', unresolved_outputs)
        print(Wh+'Targets left to resolve: ', Bk, len(tgts2resolve), ':   ', tgts2resolve)
        print(' Current dependencies:')
        print(cur_dep)
        sys.stdout.write('Choosing target: ')
        sys.stdout.flush()

        print(Rd + target + Wh + ' (attempt #' + str(attempt+1) + ')' + Bk)
        print(Wh + 'Outputs will be resolved by this target: ', Bk+str(len(outs2resolve)))

        # формируем тестовую схему (подцепляем все ненайденные таргеты к нулю, все найденные к патчам)
        sys.stdout.write(Wh+'Forming Design Under Test...')
        sys.stdout.flush()
        dut, etalon = sim.form_dut(scheme, dut, etalon, patches)
        print(' done')

        # формируем стимулы
        sys.stdout.write(Wh+'Forming input stimulus...')
        sys.stdout.flush()
        if stimulus == []: # если стимулы не переопределены (например миттером)
            # меняем порядок инпутов местами
            dut, etalon = u.shuffle_inputs(dut, etalon, sign_inps[target])
            # генерируем стимулы
            (stimulus, capacity) = sim.pseudo_random_stimulus(dut.inputs())
        print(' done')
        print('Initial stimulus capacity:', Bk, capacity)

        # строим target array
        sys.stdout.write(Wh + 'Simulating and forming target vector...\n')
        sys.stdout.flush()
        target_array = sim.form_target_array(dut, etalon, capacity, tgts2resolve, stimulus)

        # в случае конфликтов - ищем патч, на котором конфликтует
        if [] in target_array:
            print('unable to build TA')
            if not os.path.isdir('bugfix'):
                os.mkdir('bugfix')

            dut.print_verilog_in_file('bugfix/dut.v', 'top')
            etalon.print_verilog_in_file('bugfix/etalon.v', 'top')
            # определяем стимулы, на которых нельзя построить таргет
            crit_stimulus, crit_capacity = sim.critical_stimulus(stimulus, target_array, capacity)
            # определяем патчи, из-за которых валится
            tmp_ptchs = init_basic_structures(tgts)
            tmp_tgts2resolve = tgts.copy()
            for tgt in resolved_tgts:
                tmp_ptchs[tgt] = copy.deepcopy(patches[tgt])
                tmp_dut, tmp_etalon = sim.form_dut(scheme, dut, etalon, tmp_ptchs)
                tmp_tgts2resolve.remove(tgt)
                tmp_t_a = sim.form_target_array(tmp_dut, tmp_etalon, crit_capacity, tmp_tgts2resolve, crit_stimulus)
                print(tgt)
                if [] in tmp_t_a:
                    # нашли порченый патч
                    print(Rd+'\nFOUND FAULTY PATCH FOR', tgt, 'TARGET')
                    for tr in resolved_tgts:
                        patches[tr][0].print_verilog_in_file('bugfix/failed_patch' + tr + '.v', 'top')
                    #tmp_dut.print_verilog_in_file('bugfix/dut.v', 'top')
                    #tmp_etalon.print_verilog_in_file('bugfix/etalon.v', 'top')

                    if len(patches[tgt]) > 1:
                        patches[tgt].pop(0)
                        print(Bk+'trying another patch...')
                        break
                    else:
                        patches[tgt] = None
                        tgts2resolve.append(tgt)
                        resolved_tgts.remove(tgt)
                        print(Bk+'tgt is again unresolved...')
                        mit = 0
                        break

            print(Bk+'go from start...')
            attempt = 0
            continue

        # убираем don't cares
        stimulus, target_array, capacity = sim.reduce_stimulus(stimulus, target_array, capacity)
        sys.stdout.write(Wh + 'Stimulus capacity after target array reduction: ' + Bk + str(capacity) + '\n')

        # симулируем все внутренние узлы
        signatures = sim.simulate_all_nodes(dut, capacity, stimulus)

        # формируем текущие веса
        if mit == 0:
            current_basis = []
        overall_basis = []
        for key in patches:
            if patches[key] != None:
                overall_basis += patches[key][0].__inputs__
        current_weights = u.form_weights(weights, nodes_list, overall_basis, current_basis)

        # формируем вектор для таргета
        pos = tgts2resolve.index(target)
        target_vector = sim.get_target_vector(target_array, capacity, pos)

        # еще раз чистим от don't cares
        if target_vector == 'x'*capacity:
            cap = 0
            reply = None
            target_vector_int = None
        else:
            reply, target_vector_int, cap = sim.reduce_target_array(dut, signatures, target_vector)
        sys.stdout.write(Wh + 'Stimulus capacity after target vector reduction: ' + Bk + str(cap) + '\n')

        # ищем базисЫ
        print(Bl+'================================================================')
        print(Rd+'                           bases search                         '+Bl)
        bases = search4bases(current_weights, reply, target_vector_int, cap, mit, 1)
        if bases == []:
            if target not in formal:
                mit = 0
                continue

        for basis in bases:
            print(Rd + 'BASIS of length', len(basis), 'found for', target, 'with score', u.calculate_score(basis, weights))
        print(Bl+'================================================================')

        # генерируем патчи по найденным базисам
        sys.stdout.write(Bk+'Forming patches for founded bases...')
        sys.stdout.flush()
        patches[target] = patches_generator(bases, signatures, target_vector, target)
        print(' done')

        if target in formal:
            formal_patch = u.formal_patch_creation(scheme, etalon, formal, target)
            formal_score = u.calculate_score(formal_patch.__inputs__, weights)
            print(Rd+'Adding formal patch with score ' + str(formal_score) + '...' + Bl)
            tmp = []
            for patch in patches[target]:
                if formal_score < u.calculate_score(patch.__inputs__, weights):
                    break
                tmp.append(patch)
            patches[target] = tmp
            tmp.append(formal_patch)
        # проверка на эквивалентность тех выходов пропатченных схем, которые можно проверить
        sys.stdout.write('Checking patches outputs on equivalence... ')
        sys.stdout.flush()
        if outs2resolve != []:
            eql = eq_check_patches(dut, etalon, patches[target], outs2resolve)
            print(Rd+', '.join(eql))

            if 'OK' not in eql: # если ни одна схема не прошла чек
                mit = 1         # то берем самую близкую (по митеру) и начинаем итеративный поиск
                print(Bl)
                stim, patches[target] = choose_patch4miter(dut, etalon, patches[target], outs2resolve)
                if stim == []:
                    stimulus = []
                    mit = 0
                    patches[target] = None
                    continue
                additional_stimulus, additional_capacity = sim.convert_stimuli(stim)
                for j in range(scheme.inputs()):
                    stimulus[j] = (stimulus[j] << additional_capacity) + additional_stimulus[j]
                capacity = capacity + additional_capacity
                current_basis = patches[target][0].__inputs__
                patches[target] = None
                continue
            else:   # если ОК был в схеме, то
                    # корректируем patches[tgt], чтобы остались только ОК патчи. Основной - тот что первый
                mit = 0
                tmp_patches = []
                for i in range(len(eql)):
                    if eql[i] == 'OK':
                        tmp_patches.append(patches[target][i])
                patches[target] = tmp_patches
        else:
            print(' nothing to check')
        # правим список таргетов для работы
        resolved_tgts.append(target)
        tgts2resolve.remove(target)

        # проверка на точку останова
        if tgts2resolve == []:
            break

    # =============================================================
    #      финальные проверки и вывод файлов в нужном формате
    # =============================================================
    print(Bk+'================================================================')
    print(Rd+'                     Patch verification                         ')
    print(Bk+'================================================================')
    # объединение всех патчей
    final_patch = u.patch_merger(patches)
    score = u.calculate_score(final_patch.__inputs__, weights)
    print(Rd+'BASIS: ')
    print(Bk+' Score:', score)
    print(' Patch size:', final_patch.elements())
    print(' Number of nodes:', len(final_patch.__inputs__))

    return final_patch


def connected_components(lists):
    neighbors = defaultdict(set)
    seen = set()
    for each in lists:
        for item in each:
            neighbors[item].update(each)
    def component(node, neighbors=neighbors, seen=seen, see=seen.add):
        nodes = set([node])
        next_node = nodes.pop
        while nodes:
            node = next_node()
            see(node)
            nodes |= neighbors[node] - seen
            yield node
    for node in neighbors:
        if node not in seen:
            yield sorted(component(node))


def get_fully_independent_targets(dep_outs):
    groups = []
    for t in dep_outs:
        groups.append(t)
    cc = list(connected_components(groups))
    cc.sort(key=len)

    res = dict()
    for c in cc:
        ct = tuple(c)
        res[ct] = []
        for t in c:
            for d in list(dep_outs.keys()):
                if t in d:
                    for k in dep_outs[d]:
                        if k not in res[ct]:
                            res[ct].append(k)
    # print(res)
    return res


def create_subpart_for_outputs_v1(scheme, etalon, all_tgts, needed_tgts, needed_outputs):

    # Unused targets connect to VDD and remove unused outputs
    new_scheme = copy.deepcopy(scheme)
    for t in all_tgts:
        if t not in needed_tgts:
            new_scheme.__elements__[t] = ('VCC', [])
    for o in new_scheme.__outputs__.copy():
        if o not in needed_outputs:
            new_scheme.__outputs__.remove(o)

    # Remove unused outputs
    new_etalon = copy.deepcopy(etalon)
    for o in new_etalon.__outputs__.copy():
        if o not in needed_outputs:
            new_etalon.__outputs__.remove(o)

    return new_scheme, new_etalon


def get_vdd_gnd_nodes(ckt):
    gnd_vdd_nodes = []
    for c in ckt.__elements__:
        if ckt.__elements__[c][0] == 'GND' or ckt.__elements__[c][0] == 'VCC':
            if c not in gnd_vdd_nodes:
                gnd_vdd_nodes.append(c)
    return gnd_vdd_nodes


def create_subpart_for_outputs_v2(scheme, etalon, weights, all_tgts, needed_tgts, needed_outputs):
    from scheme import scheme_alt

    # Go for output cone and copy everything (etalon)
    new_ckt = scheme_alt()
    copy_list = needed_outputs.copy()
    new_ckt.__outputs__ = needed_outputs.copy()
    while len(copy_list) > 0:
        for c in copy_list.copy():
            if c in etalon.__elements__:
                if c not in new_ckt.__elements__:
                    new_ckt.__elements__[c] = copy.deepcopy(etalon.__elements__[c])
                    copy_list += etalon.__elements__[c][1]
            elif c in etalon.__inputs__:
                if c not in new_ckt.__inputs__:
                    new_ckt.__inputs__.append(c)
            copy_list.remove(c)
    new_ckt.__inputs__ = sorted(new_ckt.__inputs__)
    new_etalon = copy.deepcopy(new_ckt)

    # Go for all valid inputs (scheme)
    new_ckt = scheme_alt()
    list_of_vdd_gnd_nodes = get_vdd_gnd_nodes(scheme)
    copy_list = u.cone_to_outs_v2(scheme, list(list_of_vdd_gnd_nodes) + list(new_etalon.__inputs__) + list(needed_tgts))
    for c in sorted(copy_list):
        if c in scheme.__elements__:
            if c not in new_ckt.__elements__:
                new_ckt.__elements__[c] = copy.deepcopy(scheme.__elements__[c])
    new_ckt.__outputs__ = needed_outputs.copy()
    new_ckt.__inputs__ = new_etalon.__inputs__.copy()
    # Set VCC on all non-input leaves
    for c in new_ckt.__elements__.copy():
        for el in new_ckt.__elements__[c][1]:
            if el not in new_ckt.__elements__:
                if el not in new_ckt.__inputs__ and el not in needed_tgts:
                    print(el, 'VCC')
                    new_ckt.__elements__[el] = ('VCC', [])
    new_scheme = copy.deepcopy(new_ckt)

    print('Elements reduction: {} from {}'.format(len(new_scheme.__elements__), len(scheme.__elements__)))

    new_weights = dict()
    for el in weights:
        if el in new_ckt.__elements__ or el in new_ckt.__inputs__:
            new_weights[el] = weights[el]

    return new_scheme, new_etalon, new_weights


def ic(F, G, weights, patch_file, out_file, time_limit=1000000):
    Bk = '\033[0m'   # normal
    Rd = '\033[31m'  # red
    Wh = '\033[37m'  # white
    Bl = '\033[34m'  # blue

    start = time.time()
    sys.setrecursionlimit(20000)
    tgts, scheme = rw.read_verilog(F)
    _, etalon = rw.read_verilog(G)
    weights = rw.read_weights(weights)
    dep_outs, sign_inps = u.tgt_influence(scheme, etalon, tgts)
    outs_to_process = [item for sublist in list(dep_outs.values()) for item in sublist]
    eq_outs = [out for out in scheme.__outputs__ if out not in outs_to_process]
    sys.stdout.write(Wh + 'Check the rest of outputs on equivalence... ')
    sys.stdout.flush()
    if not eq.check_clean_outputs(F, G, eq_outs):
        print(Rd + 'ERROR: impossible to create patch')
        exit()
    print('ok')

    print(Bk + '================================================================')
    print(Rd + '                    Initial targets split                       ')
    print(Bk + '================================================================')

    print(Bk + str(tgts) + ' ' + str(dep_outs))
    independent_targets = get_fully_independent_targets(dep_outs)
    print('Independent target groups: {} Targets split: {}'.format(len(independent_targets), independent_targets))

    if len(independent_targets) == 1 and DONT_CUT_CIRCUIT_FOR_SINGLE_TARGET_BLOCK:
        final_patch = get_patch_for_independent_target_list(tgts, scheme, etalon, weights, time_limit)
    else:
        all_patches = dict()
        for target_part in sorted(independent_targets):
            print('Run independent patch search for targets: {} and outputs: {}'.format(target_part, independent_targets[target_part]))
            new_scheme, new_etalon = create_subpart_for_outputs_v1(scheme, etalon, tgts, target_part, independent_targets[target_part])
            # new_scheme, new_etalon, new_weights = create_subpart_for_outputs_v2(scheme, etalon, weights, tgts, target_part, independent_targets[target_part])
            # new_scheme.print_verilog_in_file('sch_VCC.v', 'VCC')
            independent_patch = get_patch_for_independent_target_list(list(target_part), new_scheme, new_etalon, weights, time_limit)
            all_patches[target_part] = [copy.deepcopy(independent_patch)]
        final_patch = u.patch_merger(all_patches)

    if final_patch == None:
        return 0, 0, 0, time.time() - start
    # Минимизация
    print(Bk + '================================================================')
    print(Rd + '                     Patch minimization                         ')
    print(Bk + '================================================================')

    final_patch = minimize_patch_weights(scheme, etalon, weights, final_patch)

    score = u.calculate_score(final_patch.__inputs__, weights)
    # write in output directory
    final_patch.print_verilog_in_file(patch_file, 'patch')
    print('Patch size before elements minimizer:', final_patch.elements())
    # minimizing patch
    rw.minimize_patch_abc(patch_file)
    _, final_patch = rw.read_verilog(patch_file)

    print(Rd + 'BASIS: ')
    print(Bk + ' Score:', score)
    print(' Patch size:', final_patch.elements())
    print(' Number of nodes:', len(final_patch.__inputs__))

    # генерируем пропатченный файл
    rw.generate_out_verilog(F, final_patch.__outputs__, final_patch.__inputs__, out_file)

    # финальная верификация
    eq.patch_circuit(out_file, patch_file, G)
    print(Rd + 'TIMING: ')
    timing = time.time() - start
    print(Bk, timing, ' seconds')

    # проверяем на эквивалентность
    print(Rd + 'EQUIVALENCE: ')
    eql = eq.equivalence_check_abc()
    if eql == 1:
        print(Bk + '  SUCCESS')
    else:
        print(Bk + '  FAIL')

    return eql, score, final_patch.elements(), int(timing)


if __name__ == '__main__':
    test_number = 7
    seed = random.randint(0, 1000)
    seed = 408
    random.seed(seed)

    log = open('testcases/unit{}/log.txt'.format(test_number), 'a')
    log.write('\n\n')
    log.write('================================================================\n')
    log.write(time.asctime())
    log.write('\nSeed {}'.format(seed) + '\n')
    log.flush()
    print('================================================================')
    print('Start testcase {}'.format(test_number))
    F = 'testcases/unit{}/F.v'.format(test_number)
    G = 'testcases/unit{}/G.v'.format(test_number)
    weights = 'testcases/unit{}/weight.txt'.format(test_number)
    patch_file = "results/patch.v"
    out_file = "results/out.v"
    out_dir = 'results/'
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    print('PATHS INFO')
    print('F file:', F)
    print('G file:', G)
    print('weight file:', weights)
    print('patch.v file:', patch_file)
    print('out.v file:', out_file)
    print('================================================================')

    ic(F, G, weights, patch_file, out_file)

    if log is not None:
        log.close()
