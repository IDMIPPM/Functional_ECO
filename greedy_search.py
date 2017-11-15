# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'


import copy
import time
import random
import utils as u


def cons_check(reply, nodes, tgt_vec):
    truth_table = {0: [], 1: []}
    i = 0
    # target vector inverted comparing to replies!
    for j in range(len(tgt_vec)-1, -1, -1):
        tgt = tgt_vec[j]
        if tgt == '0':
            inp4gnd = ''
            for node in nodes:
                inp4gnd += str((reply[node] >> i) & 1)
            if inp4gnd in truth_table[1]:
                print('Some problem in cons_check function {}...'.format(inp4gnd))
                exit()
            else:
                if inp4gnd not in truth_table[0]:
                    truth_table[0].append(inp4gnd)
        if tgt == '1':
            inp4vcc = ''
            for node in nodes:
                inp4vcc += str((reply[node] >> i) & 1)
            if inp4vcc in truth_table[0]:
                print('Some problem in cons_check function {}...'.format(inp4vcc))
                exit()
            else:
                if inp4vcc not in truth_table[1]:
                    truth_table[1].append(inp4vcc)
        i += 1
    return truth_table


def get_inverse(val, capacity):
    most_significant_bit = val.bit_length()
    # 111111 - 111 = 111000
    high_part = ((2 ** capacity) - 1) - ((2 ** most_significant_bit) - 1)
    return high_part | ~val


def conflict_count(target, target_inverted, group):
    ones = group & target
    ones = bin(ones).count('1')
    if ones == 0:
        return 0
    zeros = group & target_inverted
    zeros = bin(zeros).count('1')
    conflicts = min([ones, zeros])
    return conflicts


def nwise_conflict_metric(conflicts_now, weights, reply, target, target_inverted, groups, capacity, type, n):
    best = 10000
    best_points = capacity

    attempts = len(weights)
    metrics = {}
    # basic node cycle
    keys = list(sorted(weights.keys()))
    best_point_cand = random.sample(keys, n)
    point_res_total_conflicts = conflicts_now
    point_res_groups = groups

    flag = 0
    for _ in range(attempts):
        new_groups = groups
        #candidates = roulette_wheel_best(weights, n)
        candidates = random.sample(keys, n)

        for node in candidates:
            predicted, new_groups, points = predict_conflicts_mixed(target, target_inverted, new_groups, reply[node], capacity)
            if predicted == 0:
                break
        #print(points, candidates)
        if predicted == conflicts_now:
            metrics[tuple(candidates)] = 10000
        else:
            w = 0
            for can in candidates:
                w += int(weights[can])

            if type == 'weighted':
                metric = int(w) / (conflicts_now - predicted)
            elif type == 'absolute':
                metric = predicted

            if metric < best:
                best = metric
                res_cand = candidates
                res_total_conflicts = predicted
                res_groups = new_groups
                res_points = points
                flag = 1
        if points < best_points:
            best_points = points
            best_point_cand = candidates
            point_res_total_conflicts = predicted
            point_res_groups = new_groups
            res_points = points

    if flag == 0:
        #res_cand = roulette_wheel_best(weights, n)
        #print('ATTENTION!!! ADDING RANDOM NODE!!! ')

        #node = random.choice(keys)
        #res_cand = (node,)
        res_cand = tuple(best_point_cand)
        res_total_conflicts = point_res_total_conflicts
        res_groups = point_res_groups
        res_points = best_points
        #res_total_conflicts, res_groups, res_points = predict_conflicts_mixed(target, target_inverted, groups, reply[node], capacity)

    return res_cand, res_total_conflicts, res_groups, res_points


def convert_groups_to_list_representation(groups, capacity):
    # If we already have needed representation then skip:
    if type(groups[0]) is list:
        return groups

    groups_conv = []
    for group in groups:
        arr = bin(group)[2:]
        total = 0
        lst = []
        for i in range(len(arr)-1, -1, -1):
            if arr[i] == '1':
                lst.append(total)
            total += 1
        groups_conv.append(lst)

    #print('Convert groups array to list representation (version 2) finished...')
    return groups_conv


def conflict_count_list_based(target, group):
    ones = 0
    zeros = 0
    for i in group:
        val = (target >> i) & 1
        if val == 1:
            ones += 1
        elif val == 0:
            zeros += 1
    conflicts = min([ones, zeros])
    return conflicts


def predict_conflicts_based_on_list(target, groups, signature):
    prediction = 0
    points = 0
    new_group = []
    # print('Need to process {} groups'.format(len(groups)))
    for group in groups:
        # print('Go for group {}...'.format(len(group)))
        temp_ones = []
        temp_zeros = []
        for i in group:
            val = (signature >> i) & 1
            if val == 0:
                temp_zeros.append(i)
            elif val == 1:
                temp_ones.append(i)
        temp_ones_conflicts = conflict_count_list_based(target, temp_ones)
        temp_zeros_conflicts = conflict_count_list_based(target, temp_zeros)
        if temp_ones_conflicts != 0:
            new_group.append(temp_ones)
            points += len(temp_ones)
        if temp_zeros_conflicts !=0:
            new_group.append(temp_zeros)
            points += len(temp_zeros)
        prediction += temp_ones_conflicts + temp_zeros_conflicts
    return prediction, new_group, points


def predict_conflicts_based_on_vectors(target, target_inverted, groups, signature, capacity):
    '''
    :param target: вектор значений для узла для которого ищется патч
    :param groups: набор уже найденных групп в виде векторов. Каждый вектор состоит из 0 и 1. 1 - означает что текущий тест находится в данной группе
    :param signature: вектор-сигнатура для узла, который мы пытаемся добавить в базис
    :param capacity: длина всех векторов
    :return: возвращает
    prediction - общее число оставшихся конфликтов
    new_group - массив новых групп разбиения после добавления текущего узла
    points - число тестов оставшихся в негомогенных группах
    '''
    prediction = 0
    points = 0
    new_group = []
    signature_inverted = get_inverse(signature, capacity)
    for group in groups:
        temp_ones = group & signature
        temp_zeros = group & signature_inverted
        temp_ones_conflicts = conflict_count(target, target_inverted, temp_ones)
        temp_zeros_conflicts = conflict_count(target, target_inverted, temp_zeros)
        if temp_ones_conflicts != 0:
            new_group.append(temp_ones)
            points += bin(temp_ones).count('1')
        if temp_zeros_conflicts != 0:
            new_group.append(temp_zeros)
            points += bin(temp_zeros).count('1')
        prediction += temp_ones_conflicts + temp_zeros_conflicts
    return prediction, new_group, points


def predict_conflicts_mixed(target, target_inverted, groups, signature, capacity):
    if type(groups[0]) is not list:
        prediction, new_group, points = predict_conflicts_based_on_vectors(target, target_inverted, groups, signature, capacity)
    else:
        prediction, new_group, points = predict_conflicts_based_on_list(target, groups, signature)

    return prediction, new_group, points


def convert_groups_to_vector_representation(groups, capacity):
    # If we already have needed representation then skip:
    if type(groups[0]) is not list:
        return groups

    groups_conv = [0]*len(groups)
    for j in range(len(groups)):
        group = groups[j]
        for i in group:
            groups_conv[j] |= (1 << i)
    #print('Convert groups array to vector representation finished...')
    return groups_conv


def convert_group_if_needed(groups, capacity, points):
    if 1:
        val = (-0.00033294130926821697)*len(groups) + (1.1005592849262523e-05)*points + (1.9404527601493484e-08)*len(groups)*points - (3.4479678737546884e-10)*capacity - (2.4297100675459702e-08)*len(groups)*capacity
        if val > 0:
            # It's faster to operate as vectors
            new_groups = convert_groups_to_vector_representation(groups, capacity)
        else:
            # It's faster to operate as list of indexes
            new_groups = convert_groups_to_list_representation(groups, capacity)
    return new_groups


def greedy_search(current_weights, reply, target, capacity, metric, verbose):

    # initializing first group
    weights = copy.deepcopy(current_weights)
    groups = [0]
    groups[0] = (2 ** capacity) - 1
    target_inverted = get_inverse(target, capacity)
    total_conflicts = conflict_count(target, target_inverted, groups[0])
    points = capacity
    if verbose:
        print(total_conflicts, 'conflicts and', points, 'points left in 1 group')

    basis = []
    iter = 0
    while total_conflicts != 0:
        iter += 1
        cycle_time = time.time()
        # Convert group to needed type
        groups = convert_group_if_needed(groups, capacity, points)

        # fast zero weight nodes clean-up phase
        new_weights = {}
        for node in sorted(weights):
            if weights[node] == 0:
                predicted, groups_predicted, points = predict_conflicts_mixed(target, target_inverted, groups, reply[node], capacity)
                if predicted < total_conflicts:
                    total_conflicts = predicted
                    groups = groups_predicted
                    basis.append(node)
                    if verbose:
                        print(node, ' node added with weight', weights[node])
                        print('Basis:', basis)
                        print(total_conflicts, 'conflicts and', points, 'points left in', len(groups), 'groups')
                    if total_conflicts == 0:
                        return basis
            else:
                new_weights[node] = weights[node]
        weights = new_weights
        if total_conflicts == 0:
            return basis
        rnd = random.random()
        if rnd < 0.01:
            n = 3
        elif rnd < 0.1:
            n = 2
        else:
            n = 1
        # CHOOSING NODE
        candidate, total_conflicts, groups, points = nwise_conflict_metric(total_conflicts, weights, reply, target, target_inverted, groups, capacity, metric, n)
        basis += candidate

        w = 0
        for can in candidate:
            w += int(weights[can])
            #weights.pop(can)
            #reply.pop(can)
        if verbose:
            print(candidate, ' nodes added with weight', w)
            print(basis)
            print(total_conflicts, 'conflicts and', points, 'points left in', len(groups), 'groups. Step time: {} sec'.format(round(time.time() - cycle_time, 2)))
        if len(basis) > 20:
            print('unable to find')
            return(basis)
    return basis


def check_if_basis_has_no_conflicts(basis, reply, target, capacity):
    #print('Check basis: {}'.format(basis))

    # initializing first group
    predicted = -1
    groups = [0]
    groups[0] = (2 ** capacity) - 1
    target_inverted = get_inverse(target, capacity)
    #total_conflicts = conflict_count_v4(target, target_inverted, groups[0])
    #print('Initial conflicts {}'.format(total_conflicts))

    for node in basis:
        predicted, groups, points = predict_conflicts_mixed(target, target_inverted, groups, reply[node],
                                                                      capacity)
        #print('After node {} number of conflics: {}'.format(node, predicted))
        if predicted == 0:
            break

    return predicted


def remove_not_needed_nodes(basis, current_weights, reply, target, capacity, verbose):
    if verbose:
        print('Start removing not-needed nodes...')
    init_score = u.calculate_score(basis, current_weights)
    if init_score == 0:
        return basis
    if verbose:
        print('Initial score = ', init_score)
    if len(basis) == 0:
        return basis

    current_basis = basis.copy()
    flag_removed = 1
    while flag_removed:
        flag_removed = 0
        for b in current_basis:
            new_basis = current_basis.copy()
            new_basis.remove(b)
            confl = check_if_basis_has_no_conflicts(new_basis, reply, target, capacity)
            if confl == 0:
                score = u.calculate_score(new_basis, current_weights)
                if score <= init_score:
                    current_basis = copy.copy(new_basis)
                    init_score = score
                    if verbose:
                        print('Remove node {} from basis. New score: {}'.format(b, score))
                    flag_removed = 1
                    break
    return current_basis


def multi_replacer(basis, weights, reply, target, capacity, ln, verbose):

    if verbose:
        print('Start multi replacer...')
    init_score = u.calculate_score(basis, weights)

    bases = []
    scores = []
    for _ in range(ln-1):
        bases.append(None)
        scores.append(None)
    bases.append(basis)
    scores.append(init_score)

    if init_score == 0:
        return bases, scores
    if verbose:
        print('Initial basis: ', basis)
        print('Initial score: ', init_score)
    if len(basis) == 0:
        return bases, scores

    #graph = construct_graph_from_circuit(cir)
    #closest_nodes = get_closest_nodes_to_basis(graph, basis, weights, 10)
    current_basis = basis.copy()
    best_one = basis.copy()
    target_inverted = get_inverse(target, capacity)
    best_score = init_score
    i = -1
    nodes = list(sorted(weights.keys()))
    while 1:
        i += 1
        # удаляем i-ый узел
        # initializing first group
        predicted = -1
        groups = [0]
        groups[0] = (2 ** capacity) - 1
        for j in range(len(current_basis)):
            if j != i:
                predicted, groups, points = predict_conflicts_mixed(target, target_inverted, groups, reply[current_basis[j]],
                                                                    capacity)
                if predicted == 0:
                    break

        # уже и так базис
        if predicted == 0:
            if verbose:
                print('basis:', current_basis)
                print('killing ', i, 'node')
            current_basis.pop(i)
            best_one = current_basis.copy()
            i = -1
            best_score = u.calculate_score(current_basis, weights)
            if verbose:
                print('basis:', current_basis)
                print('score:', best_score)
            bases.append(current_basis)
            bases.pop(0)
            scores.append(best_score)
            scores.pop(0)
            continue

        # пробуем вставить в i-ую позицию новый узел из всех
        # если еще удалось сократить длину базиса, то досрочно выходим
        # и начинаем с новым базисом с первого узла
        for node in nodes:
            if node == current_basis[i]:
                continue
            predicted, _, _ = predict_conflicts_mixed(target, target_inverted, groups, reply[node],
                                                                    capacity)
            # получился базис
            if predicted == 0:
                tst_basis = current_basis.copy()
                tst_basis[i] = node
                tst_basis = remove_not_needed_nodes(tst_basis, weights, reply, target, capacity, 0)
                tst_score = u.calculate_score(tst_basis, weights)
                # стало лучше
                if tst_score < best_score:
                    # базис сократился
                    if len(tst_basis) != len(current_basis):
                        i = -1
                        current_basis = tst_basis.copy()
                        best_score = tst_score
                        best_one = current_basis.copy()
                        if verbose:
                            print('basis:', current_basis)
                            print('score:', best_score)
                        bases.append(current_basis)
                        bases.pop(0)
                        scores.append(best_score)
                        scores.pop(0)
                        break
                    # базис не сократился
                    else:
                        current_basis = tst_basis.copy()
                        best_score = tst_score
                        best_one = current_basis.copy()
                        if verbose:
                            print('basis:', current_basis)
                            print('score:', best_score)
                        bases.append(current_basis)
                        bases.pop(0)
                        scores.append(best_score)
                        scores.pop(0)
        # останов: когда перебрали все узлы в текущем базисе
        if i == len(current_basis)-1:
            break
    if verbose:
        print('New basis: ', best_one)
        print('New score: ', best_score)
    bases.reverse(), scores.reverse()
    return bases, scores


def backward_greedy_search(current_weights, reply, target, capacity, verbose):
    # initializing first group
    predicted = -1
    groups = [0]
    groups[0] = (2 ** capacity) - 1
    target_inverted = get_inverse(target, capacity)

    # Sorting weights
    nod_weight = {}
    for weight in sorted(current_weights):
        if int(current_weights[weight]) not in nod_weight:
            nod_weight[int(current_weights[weight])] = [weight]
        else:
            nod_weight[int(current_weights[weight])].append(weight)
    wcluster = sorted(nod_weight)
    sorted_nodes = []
    for cluster in wcluster:
        cl = nod_weight[cluster]
        random.shuffle(cl)
        sorted_nodes += cl
    basis = []
    total_conflicts = conflict_count(target, target_inverted, groups[0])
    points = capacity
    if verbose:
        print(total_conflicts, 'conflicts and', points, 'points left in 1 group')

    for node in sorted_nodes:
        predicted, groups, points = predict_conflicts_mixed(target, target_inverted, groups, reply[node], capacity)
        basis.append(node)
        if verbose:
            print(node, ' node added with weight', current_weights[node])
        reply.pop(node)
        if verbose:
            print('Basis:', basis)
            print(predicted, 'conflicts and', points, 'points left in', len(groups), 'groups')
        if predicted == 0:
            break
    return basis
