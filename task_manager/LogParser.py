#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'franky'

from .models import *
from django.db import transaction, models
import re

patterns = {key: re.compile('%s=(.*?)\\t' % key) for key in ['TIME', 'ACTION', 'HTML']}


def fromString(line, user, task_id, unit_tag):
    time = patterns['TIME'].search(line).group(1)
    action = patterns['ACTION'].search(line).group(1)
    html = patterns['HTML'].search(line).group(1)
    task = Task.objects.get(id=task_id)
    task_unit = TaskUnit.objects.get(task=task, tag=unit_tag)
    logObj = Log.objects.create(user=user,
                                task=task,
                                task_unit=task_unit,
                                action=action,
                                action_object=html,
                                content=line)
    return logObj


def insertMessageToDB(message, user, task_id, unit_tag):
    try:
        for line in message.split('\n'):
            print line
            if line == '':
                continue
            log = fromString(line, user, task_id, unit_tag)
            log.save()
    except Exception:
        transaction.rollback()
    else:
        transaction.commit()
