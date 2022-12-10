#!/usr/bin/env python

import os
import sys
import subprocess
import calendar
from datetime import date, timedelta


class JobHistory:
    """
    Class to view job history on Slurm systems.

    Args:
        start_year (int): Year to use for start of search.

        start_month (int): Month to use for start of search.

        end_year (int or None): Year to use for end of search (current year if None).

        end_month (int or None): Year to use for end of search (today if None
            and end_year=None, else December (31) if end_year!=None).
    """
    def __init__(start_year, start_month, end_year=None, end_month=None):
        self.start = date(start_year, start_month, 1)
        if end_year is None and end_month is None:
            self.end = date.today()
        elif end_year is None:
            self.end = last_day(date.today().year, end_month)
        elif end_month is None:
            self.end = date(end_year, 12, 31)
        else:
            self.end = date(end_year, end_month)
        self.user = os.environ["USER"]
        self.jobs = 0
        self.elapsed_time = 0
        self.cpu_time = 0

    def get_month_of_jobs(self, year=None, month=None):
        end_date = start_date + last_day(year, month)
        #fmt = '--format="user,jobid%15,state%20,CPUTimeRaw,ElapsedRaw"'
        fmt_arg = '--format="user,jobid%15,ElapsedRaw,CPUTimeRaw"'
        date_args = f"--starttime={self.start} --endtime={end_date}"

        command = f"sacct {date_args} {fmt_arg} | grep {user}"
        jobs = subprocess.check_output(command.split())
        elapsed, cpu = list(map(float, jobs.split()[-2:]))
        n_jobs = len(cpu)
        return n_jobs, elapsed, cpu

    def last_day(self, year=None, month=None):
        year = year if year else self.start.year
        month = month if month else self.start.month
        return date(year, month, calendar.monthrange(year, month))

    def update_total(self):
        n_jobs, elapsed, cpu = self.get_month_of_jobs()
        self.jobs += n_jobs
        self.elapsed_time += elapsed
        self.cpu_time += cpu

    def next_month(self, year=None, month=None):
        return self.last_day(year, month)

    def get_history(self):
        while self.start < self.end:
            self.update_total()
            self.start = self.last_day() + timedelta(days=1)

def get_month_of_jobs(start_date):
    end_date = last_day(start_date.year, start_date.month)
    print(end_date)

    fmt_arg = '--format="user,jobid%15,state%20,CPUTimeRaw,ElapsedRaw'
    date_args = f"--starttime={start_date} --endtime={end_date}"
    user = os.environ["USER"]

    command = f"sacct {date_args} {fmt_arg} | grep {user}"
    #jobs = subprocess.check_output(command.split())
    print(end_date + timedelta(days=1))
    print()


def last_day(year, month):
    n_days = calendar.monthrange(year, month)[1]
    return date(year, month, n_days)

start_year = 2019
start_month = 1

start = date(start_year, start_month, 1)
today = date.today()

next_month = start + timedelta(days=30)

while next_month < today:
    print(next_month)
    get_month_of_jobs(next_month)
    next_month += timedelta(days=31)

