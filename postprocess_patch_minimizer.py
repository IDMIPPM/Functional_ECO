# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'

import random
import utils as u
import eq_check as eq
import scheme as sc
import copy
import time
import os


RENAME_INDEX = 0


def get_basis_score_for_given_signature(cir, basis, sig, weights):
    basis_new = []
    for i in range(len(basis)):
        val = (sig >> i) & 1
        if val == 0:
            basis_new.append(basis[i])
        else:
            if basis[i] in cir.__elements__:
                flag_ok = 1
                for ael in cir.__elements__[basis[i]][1]:
                    if ael not in weights:
                        flag_ok = 0
                        break
                if flag_ok:
                    basis_new += cir.__elements__[basis[i]][1]
                else:
                    basis_new.append(basis[i])
            else:
                basis_new.append(basis[i])
    scr = u.calculate_score(basis_new, weights)
    return scr, basis_new


def add_elements_to_patch(cir, patch, sig):
    basis = patch.__inputs__.copy()
    new_patch = copy.deepcopy(patch)
    # print(new_patch)
    for i in range(len(basis)):
        val = (sig >> i) & 1
        if val == 1 and basis[i] in cir.__elements__:
            print('Replace {}'.format(basis[i]))
            new_patch.__inputs__.remove(basis[i])
            new_patch.__elements__[basis[i]] = copy.deepcopy(cir.__elements__[basis[i]])
            for el in cir.__elements__[basis[i]][1]:
                if el not in new_patch.__inputs__:
                    new_patch.__inputs__.append(el)
    return new_patch


# Rename nodes inside patch except input and outputs
def rename_patch_internal_nodes(cir):
    global RENAME_INDEX

    ret = sc.scheme_alt()
    ret.__inputs__ = cir.__inputs__.copy()
    ret.__outputs__ = cir.__outputs__.copy()
    for el in cir.__elements__:
        elem_inp_list = []
        for i in cir.__elements__[el][1]:
            if i in cir.__inputs__ or i in cir.__outputs__:
                elem_inp_list.append(i)
            else:
                elem_inp_list.append(i + '_pp{}'.format(RENAME_INDEX))
        if el in cir.__inputs__ or el in cir.__outputs__:
            el_changed = copy.copy(el)
        else:
            el_changed = el + '_pp{}'.format(RENAME_INDEX)
        ret.__elements__[el_changed] = (cir.__elements__[el][0], elem_inp_list)

    RENAME_INDEX += 1
    return ret


# Minimze trying to move from current basis to F-circuit inputs, level by level
def minimize_patch_weights_v1(scheme, etalon, weights, final_patch):

    current_basis = final_patch.__inputs__.copy()
    best_score = u.calculate_score(current_basis, weights)

    # Получить конус от базиса к входам
    inp_cone = scheme.subscheme_by_outputs(current_basis)

    # Step 1: Go to F circuit inputs
    current_patch = copy.deepcopy(final_patch)
    while 1:
        # Try to check all possible variations
        local_basis = current_patch.__inputs__.copy()
        best_lscr = u.calculate_score(local_basis, weights)
        best_signature = -1
        if len(local_basis) < 18:
            for sig in range(0, 2**len(local_basis)):
                lscore, lbasis = get_basis_score_for_given_signature(inp_cone, local_basis, sig, weights)
                if lscore < best_lscr:
                    # print(lscore, len(lbasis))
                    best_lscr = lscore
                    best_signature = sig
        else:
            print('Random replaces...')
            # too big basis try random replaces
            for i in range(2**12):
                sig = random.randint(0, 2 ** len(local_basis))
                lscore, lbasis = get_basis_score_for_given_signature(inp_cone, local_basis, sig, weights)
                if lscore < best_lscr:
                    # print(lscore, len(lbasis))
                    best_lscr = lscore
                    best_signature = sig

        # We found something. Need to copy additional elements to current_patch
        if best_signature != -1:
            current_patch = add_elements_to_patch(inp_cone, current_patch, best_signature)
            print('New patch score: {}'.format(best_lscr))
        else:
            break

    if 0:
        # Step 2. Check if some basis nodes are inputs for some element in inp_cone.
        bs = set(current_patch.__inputs__)
        print(bs)
        for el in inp_cone.__elements__:
            inp_nodes = set(inp_cone.__elements__[el][1])
            # print(inp_nodes)
            if inp_nodes.issubset(bs):
                print('Found subset: {}'.format(inp_nodes))

    current_patch = rename_patch_internal_nodes(current_patch)
    return current_patch


def merge_circuits(scheme, inp_part, out_part):
    final_circ = copy.deepcopy(out_part)
    final_circ.__inputs__ = copy.deepcopy(inp_part.__inputs__)
    for el in inp_part.__elements__:
        final_circ.__elements__[el] = copy.deepcopy(inp_part.__elements__[el])
    # In some cases out_part contains primary inputs which must be added separately
    for i in out_part.__inputs__:
        if i in scheme.__inputs__:
            if i not in final_circ.__inputs__:
                final_circ.__inputs__.append(i)
    return final_circ


# Minimize trying to check basis cone inputs weights only
def minimize_patch_weights_v2(scheme, etalon, weights, final_patch):
    current_basis = final_patch.__inputs__.copy()

    # Получить конус от базиса к входам
    inp_cone = scheme.subscheme_by_outputs(current_basis)
    current_patch = merge_circuits(scheme, inp_cone, final_patch)
    score = u.calculate_score(current_patch.__inputs__, weights)
    print('Input cone basis length: {} Weight: {}'.format(len(current_patch.__inputs__), score))
    current_patch = rename_patch_internal_nodes(current_patch)
    return current_patch


def remove_cone(cir, element):
    # Delete cone
    elements_to_remove = [element]
    while len(elements_to_remove) > 0:
        remove_list = []
        for el in elements_to_remove.copy():
            # It's possible that we already remove this on previous step
            if el in sorted(cir.__elements__):
                for i in cir.__elements__[el][1]:
                    if i in cir.__elements__:
                        if i not in remove_list:
                            remove_list.append(i)
                cir.__elements__.pop(el)
        elements_to_remove = remove_list.copy()
        # print('Remove next:', elements_to_remove)

    # Add all non-driven nodes to inputs
    for el in cir.__elements__:
        for i in cir.__elements__[el][1]:
            if i not in cir.__inputs__:
                if i not in cir.__elements__:
                    cir.__inputs__.append(i)

    # Remove inputs which is not connected to anything
    inp = [0]*cir.inputs()
    for el in cir.__elements__:
        for i in cir.__elements__[el][1]:
            if i in cir.__inputs__:
                index = cir.__inputs__.index(i)
                inp[index] += 1

    new_inputs = []
    for i in range(cir.inputs()):
        if inp[i] > 0:
            new_inputs.append(cir.__inputs__[i])
    cir.__inputs__ = new_inputs
    return cir


# Merge final_patch + inp_cone and try to remove nodes from the start of circuit
def minimize_patch_weights_v3(scheme, etalon, weights, final_patch):
    start_time = time.time()
    time_limit = 30
    current_patch = copy.deepcopy(final_patch)
    current_basis = final_patch.__inputs__.copy()
    best_score = u.calculate_score(current_basis, weights)
    best_elements = final_patch.elements()

    # Получить конус от базиса к входам
    inp_cone = scheme.subscheme_by_outputs(current_basis)
    starter_patch = merge_circuits(scheme, inp_cone, final_patch)
    score = u.calculate_score(starter_patch.__inputs__, weights)
    print('Started basis. Inputs: {} Elements: {} Weight: {}'.format(len(starter_patch.__inputs__), len(starter_patch.__elements__), score))
    if (score < best_score) or ((score == best_score) and starter_patch.elements() < best_elements):
        current_patch = copy.deepcopy(starter_patch)
        best_score = score
        best_elements = starter_patch.elements()

    for el in sorted(inp_cone.__elements__):
        new_patch = remove_cone(copy.deepcopy(starter_patch), el)
        if len(new_patch.__elements__) == 0:
            continue
        score = u.calculate_score(new_patch.__inputs__, weights)
        # print('New basis. Inputs: {} Elements: {} Weight: {}'.format(len(new_patch.__inputs__), len(new_patch.__elements__), score))
        if (score < best_score) or ((score == best_score) and new_patch.elements() < best_elements):
            print('New best score reached: {}'.format(score))
            current_patch = copy.deepcopy(new_patch)
            best_score = score
            best_elements = new_patch.elements()

        if time.time() - start_time > time_limit:
            print('Time limit for weights optimization search v3...')
            break

        if 0:
            # 2nd level inception
            inter_elements = list(set(inp_cone.__elements__.keys()) & set(new_patch.__elements__.keys()))
            for el in sorted(inter_elements):
                new_patch1 = remove_cone(copy.deepcopy(new_patch), el)
                if len(new_patch1.__elements__) == 0:
                    continue
                score = u.calculate_score(new_patch1.__inputs__, weights)
                # print('New basis level 2. Inputs: {} Elements: {} Weight: {}'.format(len(new_patch1.__inputs__), len(new_patch1.__elements__), score))
                if (score < best_score) or ((score == best_score) and new_patch1.elements() < best_elements):
                    print('New best score reached: {}'.format(score))
                    current_patch = copy.deepcopy(new_patch1)
                    best_score = score
                    best_elements = new_patch1.elements()

                if 0:
                    # 3rd level inception
                    inter_elements = list(set(inp_cone.__elements__.keys()) & set(new_patch1.__elements__.keys()))
                    for el in sorted(inter_elements):
                        new_patch2 = remove_cone(copy.deepcopy(new_patch), el)
                        if len(new_patch2.__elements__) == 0:
                            continue
                        score = u.calculate_score(new_patch2.__inputs__, weights)
                        if 0:
                            print('New basis level 3. Inputs: {} Elements: {} Weight: {}'.format(len(new_patch2.__inputs__),
                                                                                             len(new_patch2.__elements__),
                                                                                             score))
                        if (score < best_score) or ((score == best_score) and new_patch2.elements() < best_elements):
                            current_patch = copy.deepcopy(new_patch2)
                            best_score = score
                            best_elements = new_patch2.elements()

    current_patch = rename_patch_internal_nodes(current_patch)
    equiv = eq.check_some_outputs(scheme, etalon, current_patch, scheme.__outputs__)
    if equiv == 1:
        print('Patch with weight {} and elements {} is equivalent'.format(best_score, best_elements))
    else:
        print('Patch with weight {} and elements {} is not equivalent! Go to next!'.format(best_score, best_elements))

    return current_patch


# Рекурсивно удаляем случайные конусы к входам пока не останется 0
def minimize_patch_weights_v4(scheme, etalon, weights, final_patch):
    start_time = time.time()
    time_limit = 30
    current_patch = copy.deepcopy(final_patch)
    current_basis = final_patch.__inputs__.copy()
    best_score = u.calculate_score(current_basis, weights)
    best_elements = final_patch.elements()

    # Получить конус от базиса к входам
    inp_cone = scheme.subscheme_by_outputs(current_basis)
    starter_patch = merge_circuits(scheme, inp_cone, final_patch)
    score = u.calculate_score(starter_patch.__inputs__, weights)
    print('Started basis for v4 algo. Inputs: {} Elements: {} Weight: {}'.format(len(starter_patch.__inputs__), len(starter_patch.__elements__), score))
    if (score < best_score) or ((score == best_score) and starter_patch.elements() < best_elements):
        current_patch = copy.deepcopy(starter_patch)
        best_score = score
        best_elements = starter_patch.elements()

    max_iter = 2000
    while max_iter > 0:
        new_patch = copy.deepcopy(starter_patch)
        while 1:
            inter_elements = list(set(inp_cone.__elements__.keys()) & set(new_patch.__elements__.keys()))
            if len(inter_elements) == 0:
                break
            el = random.choice(inter_elements)
            new_patch = remove_cone(copy.deepcopy(new_patch), el)
            if len(new_patch.__elements__) == 0:
                break
            score = u.calculate_score(new_patch.__inputs__, weights)
            # print('New basis. Inputs: {} Elements: {} Weight: {}'.format(len(new_patch.__inputs__), len(new_patch.__elements__), score))
            if (score < best_score) or ((score == best_score) and new_patch.elements() < best_elements):
                print('New best score reached: {}'.format(score))
                current_patch = copy.deepcopy(new_patch)
                best_score = score
                best_elements = new_patch.elements()

        if time.time() - start_time > time_limit:
            print('Time limit for weights optimization search v4...')
            break

        max_iter -= 1

    current_patch = rename_patch_internal_nodes(current_patch)
    # Debug only
    if 0:
        equiv = eq.check_some_outputs(scheme, etalon, current_patch, scheme.__outputs__)
        if equiv == 1:
            print('Patch with weight {} and elements {} is equivalent'.format(best_score, best_elements))
        else:
            print('Patch with weight {} and elements {} is not equivalent! Go to next!'.format(best_score, best_elements))

    return current_patch


def add_other_input_to_patch(patch, old_input, new_input, logic):
    # Если такая же логическая функция, то просто заменяем все вхождения в элементах
    new_patch = copy.deepcopy(patch)
    if logic == True:
        for el in new_patch.__elements__:
            for k in range(len(new_patch.__elements__[el][1])):
                if new_patch.__elements__[el][1][k] == old_input:
                    new_patch.__elements__[el][1][k] = new_input
    # Если инвертированная, то добавляем инвертор
    else:
        new_patch.__elements__[old_input] = ('INV', [new_input])

    # Заменяем в списке входов
    for i in range(len(new_patch.__inputs__)):
        if new_patch.__inputs__[i] == old_input:
            new_patch.__inputs__[i] = new_input
    return new_patch


def minimize_patch_weights_go_to_outputs_v1(scheme, etalon, weights, final_patch):
    start_time = time.time()
    time_limit = 30
    current_basis = final_patch.__inputs__.copy()
    best_score = u.calculate_score(current_basis, weights)
    best_elements = final_patch.elements()

    # Находим деревья из инверторов или буферов от текущего базиса
    trees = dict()
    logic = dict()
    for b in current_basis:
        trees[b] = [b]
        # First element True values, second False values
        logic[b] = [[b], []]
    change = 1
    while change > 0:
        change = 0
        for b in current_basis:
            # Check if element is input of inverter or buffer
            for el in scheme.__elements__:
                if el not in trees[b]:
                    for i in scheme.__elements__[el][1]:
                        if i in trees[b]:
                            if scheme.__elements__[el][0] == 'INV':
                                # print(b, el, 'INV')
                                if el not in trees[b]:
                                    trees[b].append(el)
                                    if i in logic[b][0]:
                                        logic[b][1].append(el)
                                    elif i in logic[b][1]:
                                        logic[b][0].append(el)
                                    else:
                                        print('Strange!')
                                    change += 1
                            if scheme.__elements__[el][0] == 'BUF':
                                # print(b, el, 'BUF')
                                if el not in trees[b]:
                                    trees[b].append(el)
                                    if i in logic[b][0]:
                                        logic[b][0].append(el)
                                    elif i in logic[b][1]:
                                        logic[b][1].append(el)
                                    else:
                                        print('Strange!')
                                    change += 1

    new_patch = copy.deepcopy(final_patch)
    for i in range(len(current_basis)):
        el = current_basis[i]
        best_replace = el
        best_logic = -1
        best_weight = weights[el]
        # Start from second element since first is always the same
        for j in range(1, len(trees[el])):
            element = trees[el][j]
            if element in weights:
                if weights[element] <= best_weight:
                    best_weight = weights[element]
                    best_replace = element
                    if element in logic[el][0]:
                        best_logic = True
                    elif element in logic[el][1]:
                        best_logic = False
                    else:
                        print('Strange!')
                    print('Found better replacement: ', element, weights[element])
                    current_basis[i] = element
        if best_replace != el:
            new_patch = add_other_input_to_patch(new_patch, el, best_replace, best_logic)

    new_patch = rename_patch_internal_nodes(new_patch)
    # Debug only
    if 0:
        equiv = eq.check_some_outputs(scheme, etalon, new_patch, scheme.__outputs__)
        if equiv == 1:
            print('Patch with weight {} and elements {} is equivalent'.format(best_score, best_elements))
        else:
            print('Patch with weight {} and elements {} is not equivalent! Go to next!'.format(best_score, best_elements))
            if not os.path.isdir('bugfix'):
                os.mkdir('bugfix')
            new_patch.print_verilog_in_file('bugfix/failed_minimized_patch.v', 'top')
            final_patch.print_verilog_in_file('bugfix/failed_minimized_patch_initital.v', 'top')

    return new_patch


def get_best_patch_by_weights(patches_list, weights):
    if len(patches_list) == 0:
        return []
    scores_list = []
    for p in patches_list:
        score = u.calculate_score(p.__inputs__, weights)
        scores_list.append(score)
    indexes = sorted(range(len(scores_list)), key=lambda k: scores_list[k])
    current_best = patches_list[indexes[0]]
    return current_best


def minimize_patch_weights(scheme, etalon, weights, final_patch):
    patches_list = []
    inputs_patch = None

    current_basis = final_patch.__inputs__.copy()
    score = u.calculate_score(current_basis, weights)
    print('Initital basis to minimize: {} Elements: {} Weight: {}'.format(current_basis, final_patch.elements(), score))

    if 1:
        p = copy.deepcopy(final_patch)
        patches_list.append(p)
        p = minimize_patch_weights_v1(scheme, etalon, weights, final_patch)
        patches_list.append(p)
        inputs_patch = minimize_patch_weights_v2(scheme, etalon, weights, final_patch)
        patches_list.append(inputs_patch)
        # Лучше использовать версию 4
        # p = minimize_patch_weights_v3(scheme, etalon, weights, final_patch)
        # patches_list.append(p)
        # Only start for relatively large circuits
        if len(scheme.__inputs__) > 10 and len(scheme.__elements__) > 50:
            p = minimize_patch_weights_v4(scheme, etalon, weights, final_patch)
            patches_list.append(p)

    if 1:
        # Minimize forward best patch if any
        if len(patches_list) > 0:
            current_best = get_best_patch_by_weights(patches_list, weights)
            p = minimize_patch_weights_go_to_outputs_v1(scheme, etalon, weights, current_best)
            patches_list.append(p)
        # Minimize forward initial patch
        p = minimize_patch_weights_go_to_outputs_v1(scheme, etalon, weights, final_patch)
        patches_list.append(p)

        if inputs_patch is not None:
            print('Minimize input based patch...')
            # Minimize patch consisted of inputs
            p = minimize_patch_weights_go_to_outputs_v1(scheme, etalon, weights, inputs_patch)
            patches_list.append(p)

    # Find best patches from list (sort by score and number of elements)
    scores_list = []
    index = 0
    for p in patches_list:
        score = u.calculate_score(p.__inputs__, weights)
        elements = p.elements()
        scores_list.append((score, elements, index))
        index += 1

    print('Created patches: {}'.format(len(patches_list)))
    # Sort by score
    scores_list = sorted(scores_list, key=lambda element: (element[0], element[1]))
    print('Best patches: {}'.format(scores_list))

    for scr, elm, i in scores_list:
        p = patches_list[i]
        print('Equivalence checker for minimized patches...')
        equiv = eq.check_some_outputs(scheme, etalon, p, scheme.__outputs__)
        if equiv == 1:
            print('Patch with weight {} is equivalent: {}'.format(scr, p.__inputs__))
            return p
        else:
            print('Patch with weight {} is not equivalent! Go to next!'.format(scr))

    print('Equivalence Fail after minimizer! Return initial patch')
    return final_patch
