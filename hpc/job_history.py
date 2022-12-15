#!/usr/bin/env python

import os
import sys
import subprocess
import calendar
import json
import numpy as np
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
    def __init__(self, start_year, start_month, end_year=None, end_month=None):
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

    def get_month_of_jobs(self, year=None, month=None, verbose=False):
        year = year if year else self.start.year
        month = month if month else self.start.month
        start_date = date(year, month, 1)
        end_date = self.last_day(year, month)
        if verbose:
            print(f"Checking jobs from {start_date} to {end_date}")
        fmt_arg = "--format='user,jobid%15,ElapsedRaw,CPUTimeRaw'"
        date_args = f"--starttime={start_date} --endtime={end_date}"

        command = f"sacct {date_args} {fmt_arg} | grep {self.user} > .jobhistory.temp"
        os.system(command)
        jobs = np.loadtxt(".jobhistory.temp", dtype=int, usecols=(2,3))
        os.remove(".jobhistory.temp")

        nonzero = [] # filter out cancelled jobs w/ 0 run time
        for _id, row in enumerate(jobs):
            if row.sum() != 0:
                nonzero.append(_id)
        jobs = jobs[nonzero]

        n_jobs = jobs.shape[0]
        if n_jobs:
            elapsed, cpu = np.sum(jobs, axis=0) / 3600.0
        else:
            elapsed, cpu = 0.0, 0.0
        self.cache = n_jobs, elapsed, cpu
        return n_jobs, elapsed, cpu

    def last_day(self, year=None, month=None):
        year = year if year else self.start.year
        month = month if month else self.start.month
        n_days = calendar.monthrange(year, month)[1]
        return date(year, month, n_days)

    def update_total(self):
        if self.cache:
            print(self.start)
            n_jobs, elapsed, cpu = self.cache
        else:
            n_jobs, elapsed, cpu = self.get_month_of_jobs(verbose=True)
        self.jobs += n_jobs
        self.elapsed_time += elapsed
        self.cpu_time += cpu

    def next_month(self, year=None, month=None):
        return self.last_day(year, month) + timedelta(days=1)

    def get_history(self):
        while self.start < self.end:
            self.update_total()
            self.start = self.next_month()

    @property
    def cache(self):
        if not hasattr("self", "_cache"):
            if "history.json" in os.listdir():
                with open("history.json") as file:
                    self._cache = json.loads(file.read())
            else:
                self._cache = {}
        return self._cache.get(str(self.start))

    @cache.setter
    def cache(self, vals):
        self._cache[str(self.start)] = vals
        with open("history.json", "w") as file:
            file.write(json.dumps(self._cache, indent=2))

if __name__ == "__main__":
    start_year = 2019
    start_month = 1

    history = JobHistory(start_year, start_month)
    history.get_history()
    print(history.jobs, history.elapsed_time, history.cpu_time)
