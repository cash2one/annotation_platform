#!/user/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'defaultstr'

from annotation_task_1.controllers import QueryDocumentTaskManager
from annotation_task_2.controllers import SessionTaskManager
from annotation_task_user_preference.controllers import UserPreferenceTaskManager

tag2controller = {
    'task_1': QueryDocumentTaskManager(),
    'task_2': SessionTaskManager(),
    'task_user_preference': UserPreferenceTaskManager,
}

