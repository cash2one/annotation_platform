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

        task_units = TaskUnit.objects(task=task, unit_type='normal')
        task_units = sorted(task_units, key=lambda x: json.loads(x.unit_content)['query'])
        random.shuffle(task_units)
        task_unit_tags = [t.tag for t in task_units]
        annotations = Annotation.objects(task=task, user=user)
        annotated_tags = set([a.task_unit.tag for a in annotations])

        # 在18,35,52,69,86各设一个check point
        check_units = TaskUnit.objects(task=task, unit_type='check')
        if 10 < len(annotations) < 90 and len(annotations) % 17 == 0:
            i = len(annotations) / 17 - 1
            return check_units[i]
        for tag in task_unit_tags:
            if tag in annotated_tags:
                continue
            else:
                return TaskUnit.objects(task=task, tag=tag)[0]
        if len(task_units) > 0:
            self.send_task_finished_emails(request, task, user, admin_emails=['zhangfan12@mails.tsinghua.edu.cn'])

        return None

    def get_annotation_content(self, request, user, task, unit_tag):
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
            html_srcs = {'baidu': html_baidu, 'sogou': html_sogou}
            htmls = ['baidu', 'sogou']
            html1 = ''
            html2 = ''

            unit_annotations = Annotation.objects(task_unit=task_unit)
            valid_unit_annotations = len(unit_annotations)

            # 统计之前的标注中baidu和sogou在左边出现的次数,选较少的放左边
            baidu_num = 0
            sogou_num = 0
            for annotation in unit_annotations:
                annotation_content = json.loads(annotation.annotation_content)
                html_left = annotation_content['html1']
                if html_left == 'baidu':
                    baidu_num += 1
                if html_left == 'sogou':
                    sogou_num += 1
            if baidu_num < sogou_num:
                html1 = 'baidu'
                html2 = 'sogou'
            if sogou_num < baidu_num:
                html1 = 'sogou'
                html2 = 'baidu'
            if baidu_num == sogou_num:
                # 如果之前的标注中baidu和sogou在左边出现的次数相同
                user_annotations = Annotation.objects(user=user)
                # 如果这个user当前标注的数量为奇数
                # 统计这个user之前的标注中baidu和sogou在左边出现的次数,选较少的放在左边
                user_baidu_num = 0
                user_sogou_num = 0
                for annotation in user_annotations:
                    annotation_content = json.loads(annotation.annotation_content)
                    html_left = annotation_content['html1']
                    if html_left == 'baidu':
                        user_baidu_num += 1
                    if html_left == 'sogou':
                        user_sogou_num += 1
                if user_baidu_num < user_sogou_num:
                    html1 = 'baidu'
                    html2 = 'sogou'
                if user_sogou_num < user_baidu_num:
                    html1 = 'sogou'
                    html2 = 'baidu'
                if user_sogou_num == user_baidu_num:
                    # 随机分配一个放在左边
                    i = random.randint(0, 1)
                    html1 = htmls[i]
                    html2 = htmls[1-i]

            t = loader.get_template('annotation_task_user_preference_content.html')
            c = RequestContext(
                request,
                {
                    'task_id': task.id,
                    'unit_tag': unit_tag,
                    'query': jsonObj['query'],
                    'html_src1': html_srcs[html1],
                    'html_src2': html_srcs[html2],
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
        annotations = Annotation.objects(user=user, task=task)
        annotated_tags = set([a.task_unit.tag for a in annotations])
        finished_task_num = len(annotated_tags)
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
            task_unit.save()

            user = get_user_from_request(request)
            score = int(request.POST['score'])
            html1 = request.POST['html1']
            html2 = request.POST['html2']
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
        annotated_users = set([a.user for a in annotations])
        task_units = TaskUnit.objects(task=task, unit_type='normal')
        # 每个人标注的情况
        for user in annotated_users:
            user_annotations = []
            for unit in task_units:
                if len(Annotation.objects(task_unit=unit, user=user)) > 0:
                    user_annotations.append(Annotation.objects(task_unit=unit, user=user)[0])
            annotation_scores = {}
            for i in range(-3, 4):
                annotation_scores[i] = 0
            for user_annotation in user_annotations:
                annotation_scores[int(get_score(user_annotation))] += 1
            scores_info = ''
            for i in range(-3, 4):
                scores_info += str(i) + ':' + str(annotation_scores[i]) + ';'
            ret[str(user.username)] = scores_info
        # task整体情况
        unit_30 = 0
        unit_21 = 0
        unit_111 = 0
        for unit in task_units:
            unit_annotations = []
            for user in annotated_users:
                if len(Annotation.objects(task_unit=unit, user=user)) > 0:
                    unit_annotations.append(Annotation.objects(task_unit=unit, user=user)[0])
            '''if len(unit_annotations) == 3:
                sogou_scores = []
                for annotation in unit_annotations:
                    html2 = json.loads(annotation.annotation_content)['html2']
                    score_sogou = get_score(annotation)
                    if html2 == 'baidu':
                        score_sogou = 0 - score_sogou
                    sogou_scores.append(score_sogou)
                ret[unit.tag] = str(sogou_scores[0]) + ',' + str(sogou_scores[1]) + ',' + str(sogou_scores[2])'''
            if len(unit_annotations) == 3:
                sogou_scores = []
                for annotation in unit_annotations:
                    html2 = json.loads(annotation.annotation_content)['html2']
                    score_sogou = get_three_level_score(annotation)
                    if html2 == 'baidu':
                        score_sogou = 0 - score_sogou
                    sogou_scores.append(score_sogou)
                conflicts = 0
                for i in range(0, len(sogou_scores)):
                    for j in range(i+1, len(sogou_scores)):
                        if sogou_scores[i] != sogou_scores[j]:
                            conflicts += 1
                if conflicts == 0:
                    unit_30 += 1
                    # ret[unit.tag] = "3-0," + str(sogou_scores[0])
                if conflicts == 2:
                    unit_21 += 1
                    # ret[unit.tag] = "2-1"
                if conflicts == 3:
                    unit_111 += 1
                    # ret[unit.tag] = "1-1-1"
        ret["3-0"] = str(unit_30)
        ret["2-1"] = str(unit_21)
        ret["1-1-1"] = str(unit_111)
        annotated_users = list(annotated_users)
        for i in range(0, len(annotated_users)):
            for j in range(i+1, len(annotated_users)):
                user1 = annotated_users[i]
                user2 = annotated_users[j]
                # 计算三级kappa
                matrix = [
                    [0, 0, 0],
                    [0, 0, 0],
                    [0, 0, 0]
                ]
                total = 0
                for unit in task_units:
                    if len(Annotation.objects(task_unit=unit, user=user1)) > 0 and len(Annotation.objects(task_unit=unit, user=user2)) > 0:
                        total += 1
                        annotation1 = Annotation.objects(task_unit=unit, user=user1)[0]
                        html2 = json.loads(annotation1.annotation_content)['html2']
                        score_sogou1 = get_three_level_score(annotation1)
                        if html2 == 'baidu':
                            score_sogou1 = 0 - score_sogou1
                        annotation2 = Annotation.objects(task_unit=unit, user=user2)[0]
                        html2 = json.loads(annotation2.annotation_content)['html2']
                        score_sogou2 = get_three_level_score(annotation2)
                        if html2 == 'baidu':
                            score_sogou2 = 0 - score_sogou2
                        matrix[score_sogou1 + 1][score_sogou2 + 1] += 1
                p_o = (matrix[0][0] + matrix[1][1] + matrix[2][2]) / float(total)
                p_c = (
                          (matrix[0][0] + matrix[0][1] + matrix[0][2]) * (matrix[0][0] + matrix[1][0] + matrix[2][0])
                          + (matrix[1][0] + matrix[1][1] + matrix[1][2]) * (matrix[0][1] + matrix[1][1] + matrix[2][1])
                          + (matrix[2][0] + matrix[2][1] + matrix[2][2]) * (matrix[0][2] + matrix[1][2] + matrix[2][2])
                      ) / float(total * total)
                if p_c == 1:
                    kappa = 1
                else:
                    kappa = (p_o - p_c) / (1 - p_c)
                ret[user1.username + '-' + user2.username + 'kappa'] = str(kappa) + ','.join(str(x) for x in matrix)

                # 计算二级kappa
                binary_matrix = [[0, 0], [0, 0]]
                total = 0
                for unit in task_units:
                    if len(Annotation.objects(task_unit=unit, user=user1)) > 0 and len(Annotation.objects(task_unit=unit, user=user2)) > 0:
                        total += 1
                        annotation1 = Annotation.objects(task_unit=unit, user=user1)[0]
                        html2 = json.loads(annotation1.annotation_content)['html2']
                        score_sogou1 = get_three_level_score(annotation1)
                        if html2 == 'baidu':
                            score_sogou1 = 0 - score_sogou1
                        annotation2 = Annotation.objects(task_unit=unit, user=user2)[0]
                        html2 = json.loads(annotation2.annotation_content)['html2']
                        score_sogou2 = get_three_level_score(annotation2)
                        if html2 == 'baidu':
                            score_sogou2 = 0 - score_sogou2
                        binary_matrix[abs(score_sogou1)][abs(score_sogou2)] += 1
                p_o = (binary_matrix[0][0] + binary_matrix[1][1]) / float(total)
                p_c = (
                    (binary_matrix[0][0] + binary_matrix[0][1]) * (binary_matrix[0][0] + binary_matrix[1][0]) +
                    (binary_matrix[1][1] + binary_matrix[0][1]) * (binary_matrix[1][1] + binary_matrix[1][0])
                ) / float(total * total)
                if p_c == 1:
                    binary_kappa = 1
                else:
                    binary_kappa = (p_o - p_c) / (1 - p_c)
                ret[user1.username + '-' + user2.username + 'binary_kappa'] = binary_kappa

        check_units = TaskUnit.objects(task=task, unit_type='check')
        for check_unit in check_units:
            annotations = Annotation.objects(task_unit=check_unit)
            for annotation in annotations:
                html2 = json.loads(annotation.annotation_content)['html2']
                score_sogou = get_three_level_score(annotation)
                if html2 == 'baidu':
                    score_sogou = 0 - score_sogou
                ret[annotation.user.username + check_unit.tag] = str(score_sogou)
        return ret

