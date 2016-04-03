#!/user/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'franky'

try:
    import simplejson as json
except ImportError:
    import json
from collections import defaultdict
from task_manager.utils import _compute_kappa, _compute_alpha, _compute_weighted_kappa
from task_manager.models import *


def import_task_unit(task, json_str):
    obj = json.loads(json_str)
    u = TaskUnit()
    u.task = task
    u.tag = unicode(obj['query'])
    u.unit_content = json_str
    u.save()
    return u


def batch_import_task_units_from_file(task, path):
    with open(path, 'r') as fin:
        for line in fin:
            import_task_unit(task, line)


def get_query(annotation):
    obj = json.loads(annotation.annotation_content)
    return obj['query']


def get_score(annotation):
    obj = json.loads(annotation.annotation_content)
    return obj['score']


def get_three_level_score(annotation):
    obj = json.loads(annotation.annotation_content)
    if obj['score'] < 0:
        return -1
    elif obj['score'] > 0:
        return 1
    else:
        return 0


def output_annotations(annotations, key=get_query, value=get_score):
    annotations = list(annotations)

    d = defaultdict(list)
    for a in annotations:
        k = key(a)
        d[k].append(value(a))

    for k in d:
        query = k
        values = sorted(d[k])
        yield query,  values[len(values)/2]


def compute_kappa(annotations, key=get_query, value=get_score):
    annotations = list(annotations)

    value_set = set()
    for a in annotations:
        value_set.add(value(a))

    value_map = {v: i for i, v in enumerate(sorted(value_set))}

    d = defaultdict(list)
    for a in annotations:
        query = key(a)
        d[query].append(value(a))
    return _compute_kappa(d, value_map)


def compute_weighted_kappa(annotations, key=get_query, value=get_score):
    annotations = list(annotations)
    l = [(key(a), a.user.username, value(a)) for a in annotations]
    return _compute_weighted_kappa(l)


def compute_alpha(annotations, key=get_query, value=get_score):

    def iter_pairs(l):
        size = len(l)
        if size >= 2:
            for i in range(size-1):
                for j in range(i+1, size):
                    yield l[i], l[j]

    def dist(x, y):
        return (x - y) * (x - y)

    annotations = list(annotations)

    n = 0
    d = defaultdict(list)
    all_values = []
    for a in annotations:
        query = key(a)
        d[query].append(value(a))
        all_values.append(value(a))
        n += 1
    return _compute_alpha(n, d, all_values)


