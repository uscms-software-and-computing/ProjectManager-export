import datetime
import json
import re
from dataclasses import dataclass
from dacite import Config, from_dict, Optional
from datetime import datetime
from typing import Any
import treelib
from dateutil.parser import parse
import jpype
import mpxj

jpype.startJVM("-Dlog4j2.loggerContextFactory=org.apache.logging.log4j.simple.SimpleLoggerContextFactory")
from net.sf.mpxj.reader import UniversalProjectReader
from net.sf.mpxj.json import JsonWriter


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


class MppData:

    def __init__(self, input_file_name, json_output_file):
        self.input_file_name = input_file_name
        self.json_output_file = json_output_file
        self.mpp_data = None

    def convert_mpp_to_json(self):
        project = UniversalProjectReader().read(self.input_file_name)
        writer = JsonWriter()
        writer.write(project, self.json_output_file)
        jpype.shutdownJVM()
        with open(self.json_output_file, 'r') as json_mpp_data:
            # self.json_mpp_data = json.load(json_mpp_data)
            self.mpp_data = json.load(json_mpp_data)

    def create_project_tree(self):
        custom_fields = {}

        for custom_field in self.mpp_data['custom_fields']:
            new_alias = re.sub(r"[&\s]", "_", custom_field['field_alias'], 0)
            custom_fields[custom_field['field_type']] = new_alias

        tasks = self.mpp_data['tasks']
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
