#!/usr/bin/env python

# change --comment to match walltime (unless you want script to run for more than allowed max walltime - 48 hrs)
#SBATCH -t 0:30 --comment=24:00:00
#SBATCH -q debug -N 1 -C knl --ntasks-per-node=64 
#SBATCH --output=job.out --error=job.err 

# resubmission stuff
#SBATCH --signal=B:USR1@10 --requeue --open-mode=append

import os
import re
import time
import signal
import shutil
import subprocess
import logging
from threading import Thread


def resub(func, checkpoint=None, ckpt_kwargs={}, sleep_time=30):
    """
    Decorator for running variable time jobs on flex / overrun queues.
    Catches USR1 signal, calls optional checkpointing function, then resubmits
    job to queue and logs stuff. 

    Include something similar to the following in your script's #SBATCH comment,
    #SBATCH --time-min=2:00:00 --signal=B:USR1@60 --requeue --open-mode=append

    Args:
        checkpoint: Optional checkpoint function to call before resubmission.
        sleep_time (int): Time interval to check func status. May need to adjust
            if changing USR1@60 in SBATCH comment (e.g. if using slow checkpoint
            functions).
    """

    def variable_time_func(*args, **kwargs):
        resubber = ResubHandler(func, *args, checkpoint=checkpoint, ckpt_kwargs={}, **kwargs)
        resubber.run(sleep_time=sleep_time)

    return variable_time_func

class ResubHandler:
    def __init__(self, task, *args, checkpoint=None, ckpt_kwargs={}, **kwargs):
        self.stop = False
        self.thread = Thread(target=task, daemon=True, args=args, kwargs=kwargs)
        self.checkpoint = checkpoint
        self.ckpt_kwargs = ckpt_kwargs
        signal.signal(signal.SIGUSR1, self.resub)

        fmt = "%(asctime)s: %(message)s"
        logging.basicConfig(format=fmt, level=logging.INFO, datefmt="%D %H:%M:%S")

    def resub(self, *args):
        logging.info("RESUBISSION INITIATED...")
        if self.checkpoint:
            logging.info("CHECKPOINTING...")
            self.checkpoint(**self.ckpt_kwargs)
        job_id = os.environ["SLURM_JOB_ID"]
        os.system(f"scontrol requeue {job_id}")
        logging.info("JOB RESUBMITTED")
        self.stop = True
        
    def poke(self):
        if not self.thread.is_alive():
            logging.info("TASK COMPLETED, NO RESUBMISSION NECESSARY")
            self.stop = True

    def run(self, sleep_time=30):
        self.thread.start()
        while not self.stop:
            self.poke()
            time.sleep(sleep_time)

