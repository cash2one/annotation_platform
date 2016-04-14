#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'franky'

from .models import *
from django.db import transaction, models
import re

patterns = {key: re.compile('%s=(.*?)\\t' % key) for key in ['TIME', 'ACTION', 'HTML', 'SITE']}


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


def extensionfromString(line, user, task_id, unit_tag):
    time = patterns['TIME'].search(line).group(1)
    action = patterns['ACTION'].search(line).group(1)
    site = patterns['SITE'].search(line+'\t').group(1)
    task = Task.objects.get(id=task_id)
    task_unit = TaskUnit.objects.get(task=task, tag=unit_tag)
    extensionlogObj = ExtensionLog.objects.create(
        user=user,
        task=task,
        task_unit=task_unit,
        action=action,
        site=site,
        content=line
    )
    return extensionlogObj


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


def insertExtensionMessageToDB(message, user, task_id, unit_tag):
    try:
        for line in message.split('\n'):
            print line
            if line == '':
                continue

            extensionlog = extensionfromString(line, user, task_id, unit_tag)
            extensionlog.save()
    except Exception:
        transaction.rollback()
    else:
        transaction.commit()

