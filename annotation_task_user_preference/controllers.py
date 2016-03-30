#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'franky'

from django.template import loader, RequestContext
from django import forms
from task_manager.models import *
from task_manager.controllers import TaskManager
from user_system.utils import *
from .utils import *
import random

try:
    import simplejson as json
except ImportError:
    import json


class UserPreferenceTaskManager(TaskManager):
    """
    TaskManager for query-document pair annotation
    """

    def get_next_task_unit(self, request, user, task):
        """
        The default schedule method just returns next task unit that the user has not annotated.
        :param user: user
        :param task: task
        :return: next task unit, None if no new task needs annotation
        """

        task_units = TaskUnit.objects(task=task)
        task_units = sorted(task_units, key=lambda x: json.loads(x.unit_content)['query'])
        random.shuffle(task_units)
        task_unit_tags = [t.tag for t in task_units]
        annotations = Annotation.objects(task=task, user=user)
        annotated_tags = set([a.task_unit.tag for a in annotations])

        for tag in task_unit_tags:
            if tag in annotated_tags:
                continue
            else:
                return TaskUnit.objects(task=task, tag=tag)[0]
        if len(task_units) > 0:
            self.send_task_finished_emails(request, task, user, admin_emails=['zhangfan12@mails.tsinghua.edu.cn'])

        return None

    def get_annotation_content(self, request, task, unit_tag):
        """
        :param task: task
        :param unit_tag:
        :return: Html fragment that will be inserted to the content block.
        """
        try:
            task_unit = TaskUnit.objects.get(task=task, tag=unit_tag)
            jsonObj = json.loads(task_unit.unit_content)
            html_baidu = '/static/SERP_baidu/' + jsonObj['query'] + '_baidu.html'
            html_sogou = '/static/SERP_sogou/' + jsonObj['query'] + '_sogou.html'
            htmls = [html_baidu, html_sogou]
            if task_unit.annotations == 0:
                html1 = htmls[0]
                html2 = htmls[1]
            elif task_unit.annotations == 1:
                html1 = htmls[1]
                html2 = htmls[0]
            else:
                ran = len(unit_tag)
                html1 = htmls[ran % 2]
                html2 = htmls[(ran + 1) % 2]
            t = loader.get_template('annotation_task_user_preference_content.html')
            c = RequestContext(
                request,
                {
                    'task_id': task.id,
                    'unit_tag': unit_tag,
                    'query': jsonObj['query'],
                    'html1': html1,
                    'html2': html2,
                })
            return t.render(c)
        except DoesNotExist:
            return '<div>Error! Can\'t find task unit!</div>'

    def get_annotation_description(self, request, task, unit_tag):
        """
        :param task:
        :param unit_tag:
        :return: Html fragment that will be inserted to the description block
        """
        user = get_user_from_request(request)
        finished_task_num = len(Annotation.objects(user=user, task=task))
        all_task_num = len(TaskUnit.objects(task=task))
        t = loader.get_template('annotation_task_user_preference_description.html')
        c = RequestContext(
            request,
            {
                'task_name': task.task_name,
                'task_description': task.task_description,
                'finished_unit_num': finished_task_num,
                'all_unit_num': all_task_num,
            }
        )
        return t.render(c)

    def get_style(self, request, task, unit_tag):
        """
        :param task:
        :param unit_tag:
        :return: CSS fragment that will be inserted to the css block
        """
        t = loader.get_template('annotation_task_user_preference.css')
        c = RequestContext(
            request, {}
        )
        return t.render(c)

    def validate_annotation(self, request, task, unit_tag):
        try:
            unit_tag = request.POST['unit_tag']
            task_id = request.POST['task_id']
            score = int(request.POST['score'])
            my_task = Task.objects.get(id=task_id)
            if task != my_task:
                return False
            task_unit = TaskUnit.objects.get(task=task, tag=unit_tag)
            return True
        except KeyError:
            return False
        except DoesNotExist:
            return False
        except ValueError:
            return False

    def save_annotation(self, request, task, unit_tag):
        try:
            task_unit = TaskUnit.objects.get(task=task, tag=unit_tag)
            htmls = ['baidu', 'sogou']
            if task_unit.annotations == 0:
                html1 = htmls[0]
                html2 = htmls[1]
            elif task_unit.annotations == 1:
                html1 = htmls[1]
                html2 = htmls[0]
            else:
                ran = len(unit_tag)
                html1 = htmls[ran % 2]
                html2 = htmls[(ran + 1) % 2]
            task_unit.annotations += 1
            task_unit.save()
            user = get_user_from_request(request)
            score = int(request.POST['score'])
            a = Annotation()
            a.user = user
            a.task_unit = task_unit
            content = json.loads(task_unit.unit_content)

            a.annotation_content = json.dumps(
                {
                    'annotator': user.username,
                    'query': content['query'],
                    'html1': html1,
                    'html2': html2,
                    'score': score
                }
            )
            a.task = task
            a.credit = task.credit_per_annotation
            a.save()
        except DoesNotExist:
            return None
        except ValueError:
            return None

    def get_annotation_quality(self, task):
        annotations = list(Annotation.objects(task=task))
        ret = {}
        if len(annotations) == 0:
            return ret

        ret['weighted kappa'] = compute_weighted_kappa(annotations)
        ret['4-level kappa'] = compute_kappa(annotations)
        ret['Kripendorff\'s alpha'] = compute_alpha(annotations)

        return ret

