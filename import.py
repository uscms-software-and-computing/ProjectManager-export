import sys
import re
import treelib
import json
import numpy as np
from pyopenproject.openproject import OpenProject
from pyopenproject.model.work_package import WorkPackage
from dataclasses import dataclass
from dacite import Config, from_dict, Optional
from datetime import datetime
from dateutil.parser import *
import warnings
from typing import Any
import jpype
import mpxj
jpype.startJVM("-Dlog4j2.loggerContextFactory=org.apache.logging.log4j.simple.SimpleLoggerContextFactory")
from net.sf.mpxj.reader import UniversalProjectReader
from net.sf.mpxj.json import JsonWriter

warnings.filterwarnings("ignore", category=RuntimeWarning)


@dataclass
class TaskClass:
    active: Optional[bool]
    actual_duration: Optional[int]
    actual_finish: Optional[datetime]
    actual_start: Optional[datetime]
    actual_work: Optional[int]
    CA_Milestone_ID: Optional[str]
    complete_through: Optional[str]
    constraint_date: Optional[datetime]
    constraint_type: Optional[str]
    created: Optional[datetime]
    critical: Optional[bool]
    Current_Finish_Date: Optional[datetime]
    Current_Start_Date: Optional[datetime]
    duration: Optional[int]
    early_finish: Optional[datetime]
    early_start: Optional[str]
    Expected_Finish_Date: Optional[datetime]
    External: Optional[str]
    finish: Optional[datetime]
    finish_slack: Optional[int]
    fixed_cost_accrual: Optional[str]
    free_slack: Optional[int]
    guid: Optional[str]
    id: Optional[int]
    KPI_Value: Optional[Any]
    late_finish: Optional[datetime]
    late_start: Optional[datetime]
    Level: Optional[str]
    level_assignments: Optional[bool]
    leveling_can_split: Optional[bool]
    leveling_delay_units: Optional[str]
    milestone: Optional[bool]
    name: Optional[str]
    notes: Optional[str]
    Notes: Optional[str]
    outline_level: Optional[int]
    outline_number: Optional[str]
    parent_task_unique_id: Optional[int]
    percent_complete: Optional[float]
    percent_work_complete: Optional[float]
    Performance_Goal: Optional[bool]
    PM_Task_Is_Priority_Null: Optional[bool]
    PM_Task_Theme: Optional[str]
    PM_TASKID: Optional[str]
    predecessors: Optional[list]
    priority: Optional[int]
    remaining_duration: Optional[int]
    resume: Optional[str]
    S_C_ID: Optional[str]
    scheduled_duration: Optional[int]
    scheduled_finish: Optional[datetime]
    scheduled_start: Optional[datetime]
    start: Optional[datetime]
    start_slack: Optional[int]
    stop: Optional[datetime]
    successors: Optional[list]
    summary: Optional[bool]
    Target: Optional[str]
    total_slack: Optional[int]
    type: Optional[str]
    unique_id: Optional[int]
    wbs: Optional[str]
    work: Optional[int]
    work_variance: Optional[int]


def convert_mpp_to_json(mpp_file):
    project = UniversalProjectReader().read(mpp_file)
    writer = JsonWriter()
    writer.write(project, json_output_file)
    jpype.shutdownJVM()


def create_project_tree(mpp_data):
    custom_fields = {}

    for custom_field in mpp_data['custom_fields']:
        new_alias = re.sub(r"[&\s]", "_", custom_field['field_alias'], 0)
        custom_fields[custom_field['field_type']] = new_alias

    tasks = mpp_data['tasks']
    root_data = tasks.pop(0)

    for custom_field, alias in custom_fields.items():
        if custom_field in root_data:
            root_data[alias] = root_data.pop(custom_field)

    root_object = from_dict(TaskClass, root_data, Config({datetime: parse}), )

    tree = treelib.Tree()
    tree.create_node("root", 0, data=root_object)

    for task in tasks:

        parent_key = task['parent_task_unique_id']
        task_id = task['id']
        task_name = ""
        if 'name' in task:
            task_name = task['name'] + " ID: " + str(task['id'])
        else:
            continue
        for custom_field, alias in custom_fields.items():
            if custom_field in task:
                task[alias] = task.pop(custom_field)

        task_object = from_dict(TaskClass, task, Config({datetime: parse}))
        tree.create_node(task_name, task_id, parent=parent_key, data=task_object)

    return tree


def create_work_package(wpSer, task_data, wbs, package_type='Phase', parent_id=None, parent_title=None):
    dn = task_data
    wP = WorkPackage(wpSer.create_form()._embedded["payload"])

    wP.subject = dn.data.name
    wP.startDate = dn.data.scheduled_start.strftime('%Y-%m-%d')
    wP.dueDate = dn.data.scheduled_finish.strftime('%Y-%m-%d')
    wP.scheduleManually = True
    bus_days = np.busday_count(wP.startDate, wP.dueDate) + 1
    duration = 'P' + str(bus_days) + 'D'
    if duration == 'P0D':
        duration = 'P1D'
    wP.duration = duration

    # aps = wpSer.find_available_projects()
    # project = aps[0].__dict__['_links']['self']
    project = list(filter(
        lambda x: x.name == wbs,
        my_wpSer.find_available_projects()
    ))[0].__dict__['_links']['self']
    wP._links["project"]["href"] = project['href']



    work_package_type = list(filter(
        lambda x: x.name == package_type,
        op.get_type_service().find_all()
    ))[0].__dict__['_links']['self']['href']
    wP.__dict__["_links"]["type"]["href"] = work_package_type
    if parent_id:
        wP.__dict__["_links"]["parent"] = {'href': '/api/v3/work_packages/' + str(parent_id), 'title': parent_title}

    # types = list(op.get_work_package_service().find_all())
    wP = wpSer.create(wP)

    print(wP.subject)

    return wP


if len(sys.argv) < 2:
    print("Supply AREA name")
    exit()

area = sys.argv[1]

input_file = "Tasks-" + area + ".mpp"

json_output_file = input_file + ".json"

convert_mpp_to_json(input_file)

with open(json_output_file, 'r') as json_mpp_data:
    json_mpp_data = json.load(json_mpp_data)

mpp_tree = create_project_tree(json_mpp_data)

# WBS1, depth = 1
# WBS3, depth = 2
# WBS4, depth = 3 -- really a depth of 2 with an added layer of tree iteration in the import

tree_depth = 0

if area == 'WBS1':
    tree_depth = 1
elif area == 'WBS3':
    tree_depth = 1
elif area == 'WBS4':
    tree_depth = 2

date_nodes = list(
    mpp_tree.filter_nodes(lambda x: x.data.scheduled_finish < datetime(2027, 1, 1) and mpp_tree.depth(x) == tree_depth))

op = OpenProject(url="http://localhost:8080",
                 api_key="8cd9b8fe0794a7271dad818d015b6666fc7bd959fdbb6f18101a17929319293b")

my_wpSer = op.get_work_package_service()

# test = my_wpSer.find_available_projects()
#
# test2 = list(filter(
#         lambda x: x.name == 'WBS4',
#         my_wpSer.find_available_projects()
#     ))[0].__dict__['_links']['self']['href']


print()
for data_node in date_nodes:
    wp = create_work_package(my_wpSer, data_node, area)
    sub_tree = mpp_tree.children(data_node.data.id)
    sub_tree_len = len(sub_tree)
    if sub_tree_len > 0:
        for child_node in sub_tree:
            child_task = create_work_package(my_wpSer, child_node, area, "Task", wp.id, data_node.data.name)
            sub_sub_tree = mpp_tree.children(child_node.data.id)
            sub_sub_tree_len = len(sub_sub_tree)
            if sub_sub_tree_len > 0:
                for child_child_node in sub_sub_tree:
                    create_work_package(my_wpSer, child_child_node, area, 'Task', child_task.id, child_node.data.name)
