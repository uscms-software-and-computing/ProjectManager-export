import numpy as np
from pyopenproject.model.work_package import WorkPackage


def _check_date(dn):
    if dn is not None:
        return dn.strftime('%Y-%m-%d')
    else:
        return ""


class OpenProjectUtils:

    def __init__(self, op, wpSer, wbs):
        self.op = op
        self.wpSer = wpSer
        self.wbs = wbs

    def create_work_package(self, task_data, package_type='Activity', parent_id=None, parent_title=None):
        dn = task_data
        wP = WorkPackage(self.wpSer.create_form()._embedded["payload"])

        wP.subject = dn.data.name
        wP.scheduleManually = True
        if package_type == 'Milestone':
            wP.date = dn.data.start.strftime('%Y-%m-%d')
        else:
            wP.startDate = dn.data.scheduled_start.strftime('%Y-%m-%d')
            wP.dueDate = dn.data.scheduled_finish.strftime('%Y-%m-%d')
            bus_days = np.busday_count(wP.startDate, wP.dueDate) + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            wP.duration = duration
        if parent_id is not None:
            if dn.data.percent_complete is not None:
                wP.percentageDone = int(dn.data.percent_complete)
            else:
                wP.percentageDone = 0
        wP.customField1 = _check_date(dn.data.Expected_Finish_Date)
        wP.customField2 = _check_date(dn.data.Current_Start_Date)
        wP.customField3 = dn.data.CA_Milestone_ID
        wP.customField4 = _check_date(dn.data.Current_Finish_Date)
        wP.customField5 = dn.data.Work_Package_ID
        wP.customField6 = dn.data.Long_Name
        wP.customField7 = dn.data.S_C_ID
        wP.customField8 = _check_date(dn.data.actual_start)
        wP.customField9 = _check_date(dn.data.actual_finish)

        # aps = wpSer.find_available_projects()
        # project = aps[0].__dict__['_links']['self']
        project = list(filter(
            lambda x: x.name == self.wbs,
            self.wpSer.find_available_projects()
        ))[0].__dict__['_links']['self']
        wP._links["project"]["href"] = project['href']

        work_package_type = list(filter(
            lambda x: x.name == package_type,
            self.op.get_type_service().find_all()
        ))[0].__dict__['_links']['self']['href']
        wP.__dict__["_links"]["type"]["href"] = work_package_type
        if parent_id:
            wP.__dict__["_links"]["parent"] = {'href': '/api/v3/work_packages/' + str(parent_id),
                                               'title': parent_title}

        # types = list(op.get_work_package_service().find_all())
        wP = self.wpSer.create(wP)

        print(wP.subject)

        return wP

    def update_work_package_actual_dates(self, wp, task_data):
        dn = task_data
        if dn.data.milestone:
            newWp = WorkPackage({"id": wp.id,
                                 "lockVersion": wp.lockVersion,
                                 "date": wp.date
                                 })

            if (actual_start := _check_date(dn.data.actual_start)) != "":
                newWp.date = actual_start

            updated_wP = self.wpSer.update(newWp)

            if actual_start != "" and actual_start != wp.date:
                start_raw_comment = f'''Milestone date changed from {wp.date} to {actual_start} [ACTUAL]'''
                print(start_raw_comment)
                self.wpSer.create_activity(updated_wP, start_raw_comment)

            return updated_wP

        else:
            newWp = WorkPackage({"id": wp.id,
                                 "lockVersion": wp.lockVersion,
                                 "startDate": wp.startDate,
                                 "dueDate": wp.dueDate,
                                 "duration": wp.duration})
            # wP = wp

            if (actual_start := _check_date(dn.data.actual_start)) != "":
                newWp.startDate = actual_start

            if (actual_finish := _check_date(dn.data.actual_finish)) != "":
                newWp.dueDate = actual_finish

            if newWp.dueDate < newWp.startDate:
                print("Error in Actual Dates - " + wp.subject)
                return wp

            bus_days = np.busday_count(newWp.startDate, newWp.dueDate) + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            newWp.duration = duration

            updated_wP = self.wpSer.update(newWp)

            if actual_finish != "" and actual_finish != wp.dueDate:
                finish_raw_comment = f'''Finish date changed from {wp.dueDate} to {actual_finish} [ACTUAL]'''
                print(finish_raw_comment)
                self.wpSer.create_activity(updated_wP, finish_raw_comment)

            if actual_start != "" and actual_start != wp.startDate:
                start_raw_comment = f'''Start date changed from {wp.startDate} to {actual_start} [ACTUAL]'''
                print(start_raw_comment)
                self.wpSer.create_activity(updated_wP, start_raw_comment)

            # actSer = op.get_activity_service()
            #
            # actSer.update(act)

            return updated_wP

    def update_work_package_current_dates(self, wp, task_data):
        dn = task_data
        if dn.data.milestone:
            newWp = WorkPackage({"id": wp.id,
                                 "lockVersion": wp.lockVersion,
                                 "date": wp.date
                                 })

            if (current_start := _check_date(dn.data.Current_Start_Date)) != "":
                newWp.date = current_start

            final_wP = self.wpSer.update(newWp)

            if current_start != "" and current_start != wp.date:
                start_raw_comment = f'''Milestone date changed from {wp.date} to {current_start} [CURRENT]'''
                print(start_raw_comment)
                self.wpSer.create_activity(final_wP, start_raw_comment)

            return final_wP

        else:
            newWp = WorkPackage({"id": wp.id,
                             "lockVersion": wp.lockVersion,
                             "startDate": wp.startDate,
                             "dueDate": wp.dueDate,
                             "duration": wp.duration})
            # updated_wP = wpSer.update_form(updated_wp)

            if (current_start := _check_date(dn.data.Current_Start_Date)) != "":
                newWp.startDate = current_start

            if (current_finish := _check_date(dn.data.Current_Finish_Date)) != "":
                newWp.dueDate = current_finish

            if newWp.dueDate < newWp.startDate:
                print("Error in dates - " + wp.subject)
                return wp

            bus_days = np.busday_count(newWp.startDate, newWp.dueDate) + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            newWp.duration = duration

            final_wP = self.wpSer.update(newWp)

            if current_finish != "" and current_finish != wp.dueDate:
                finish_raw_comment = f'''Finish date changed from {wp.dueDate} to {current_finish} [CURRENT]'''
                print(finish_raw_comment)
                self.wpSer.create_activity(final_wP, finish_raw_comment)

            if current_start != "" and current_start != wp.startDate:
                start_raw_comment = f'''Start date changed from {wp.startDate} to {current_start} [CURRENT]'''
                print(start_raw_comment)
                self.wpSer.create_activity(final_wP, start_raw_comment)

            return final_wP

    def update_work_package_add_note(self, wp, task_data):
        dn = task_data
        # newWp = WorkPackage({"id": wp.id,
        #                      "lockVersion": wp.lockVersion
        #                      })

        if dn.data.notes is not None:
            print(dn.data.notes)
            self.wpSer.create_activity(wp, dn.data.notes)

        return wp
