import sys
import re
import treelib
import json
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
    Long_Name: Optional[str]
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
    Work_Package_ID: Optional[str]


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


def check_date(dn):
    if dn is not None:
        return dn.strftime('%Y-%m-%d')
    else:
        return ""


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
    tree_depth = 3
elif area == 'S_C_Ops_Program':
    tree_depth = 1

date_nodes = list(
    mpp_tree.filter_nodes(lambda x: x.data.scheduled_finish < datetime(2027, 1, 1) and mpp_tree.depth(x) == tree_depth))

def print_fields(field_list):
    row_string = ""
    for fl in field_list:
        row_string = row_string + '"' + str(fl) + '";'
    return row_string[:-1]

for dn in date_nodes:
    # print('"' + dn.data.name + '"' + ';' + '"' + str(dn.data.scheduled_finish) + '"' + ';' + '"' + str(dn.data.percent_complete) + '"')
    print(print_fields([dn.data.name, dn.data.scheduled_start, dn.data.scheduled_finish, dn.data.Current_Start_Date, dn.data.Current_Finish_Date, dn.data.actual_start, dn.data.actual_finish, dn.data.percent_complete]))
    sub_tree = mpp_tree.children(dn.data.id)
    sub_tree_len = len(sub_tree)
    if sub_tree_len > 0:
        for cn in sub_tree:
            print('--' + print_fields([cn.data.name, cn.data.scheduled_start, cn.data.scheduled_finish, cn.data.Current_Start_Date, cn.data.Current_Finish_Date, cn.data.actual_start, cn.data.actual_finish, cn.data.percent_complete]))
            # print('--"' + cn.data.name + '"' + ';' + '"' + str(cn.data.scheduled_finish) + '"' + ';' + '"' + str(cn.data.percent_complete) + '"')





