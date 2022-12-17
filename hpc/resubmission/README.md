## Variable time job queues (NERSC overrun/flex/preempt)
For these queues, your job is ran in multiple few hour increments that is determined by the --time-min you set in your #SBATCH comment.
**For flex, the maximum --time-min is 2 hours, for overrun it's 4 hours**, and someone else can figure it out for preempt since
I'm graduating (but same idea applies). What's the benefit of these queues? Overrun is free! Flex is cheaper!
I haven't read the preempt documentation! (Note: overrun requires using an account/repo with 0 computational hours remaining)

You request a total walltime, along with a minimum time, and your job is allocated somewhere between the minimum and the total walltime
(almost always given the minimum, unless the cluster is super empty). When selecting a minimum time, keep in mind that the longer you request,
the longer it will take for your job to start (generally). So it is not always advantageous to select say a 4 hour minimum time for overrun just because you can.
If your job can make significant progress in 2 hours or 1 hour, maybe consider lowering the minimum time - play around with it! 

Here is an example header you can use for overrun jobs. Just change the -q for flex (and presumably preempt as well), and adjust the --time-min to your liking
(keeping in mind the max --time-min limits noted above). In this case, you request 20 hours with a minimum of 2 hours,
so your job will be allocated anywhere from 2 to 20 hours (probably 2).

```python
#!/usr/bin/env python

#SBATCH -t 20:00:00 --time-min=2:00:00
#SBATCH -q overrun -N 1 -C knl --ntasks-per-node=64
#SBATCH --output=job.out --error=job.err

# resubmission stuff, don't touch unless you know what you're doing
#SBATCH --signal=B:USR1@60 --requeue --open-mode=append
```

**NOTE: If you expect your job to finish in less than --time-min, you don't need to worry about resubmission!
In this case, you can just use the above header for your scripts and proceed as normal.** So for things
like single point energy calculations, you can just submit multiple jobs that each runs for ~10 minutes
for each single point (or whatever is needed for your system) and not worry about resubmissions.

## Job resubmission

The general idea for variable time jobs is that right before your job reaches the end of the allocated time,
a signal is sent to your job to initiate the resub process, an optional checkpointing function is called,
and then your job is resubmitted. **Upon resubmission, your entire script is ran again!
It will not continue from the same line of code that it was stopped at.** So for all of this to work properly, you need:

1) A script/function/etc. for catching the signal and resubmitting your job. (I have written resub.py for you to use for this)

2) And either:
    
    a) A script/function to checkpoint your progress right before resubmission, so upon resubmission your script continues from where it was stopped. Or
    
    b) Write your script in a way to check for previous results at the start of the run.

I find 2b to be easier generally, and I will show examples for doing this. That being said, I have implemented checkpoint
capabilities for people interested in 2a (you'll just need to write your own python functions for doing the checkpointing).

## Examples using resub.py
I decided to write a function decorator for this, so you can all just implement it in your own workflows.
If you use kT, it will work with kT. If you're like me and refuse to use kT, you can easily implement it in your own scripts as well.

(As an aside, I will encourage everyone to write your own scripts for your own workflows, even if it is less efficient than existing scripts in the group.
I do not subscribe to the notion that writing a script to accomplish a task when a script already exists in the group is a "waste of time",
and I will die on this hill. If you want to get better at coding, you need to spend time coding!!!!
Write your own scripts when possible, people. They will suck in the beginning, but they will get better as you keep writing more.
Remember you are students, take the time to properly develop the skills you will use in your research.
Also, look at well written code for inspiration - e.g., ASE. Don't use other group members who are equally as inexperienced
as you for inspiration, most of our code is objectively garbage, mine included -
though mine is significantly better than it was 4 years ago because I write my own scripts!! \endrant)

Anyway, just import resub from resub, put your code in a main function, decorate the function with @resub, and call it!
Simple. Here's a very basic example for a vasp optimization:

```python
#!/usr/bin/env python

#SBATCH -t 20:00:00 --time-min=2:00:00
#SBATCH -q overrun -N 1 -C knl --ntasks-per-node=64
#SBATCH --output=job.out --error=job.err

# resubmission stuff, don't touch unless you know what you're doing
#SBATCH --signal=B:USR1@60 --requeue --open-mode=append

import os
from ase.io import read
from ase.calculators.vasp import Vasp

os.environ['VASP_PP_PATH'] = '/path/to/pps'
os.environ['VASP_COMMAND'] = 'srun -n $SLURM_NTASKS vasp_gam'
###############################################################################
from resub import resub

@resub
def main(): # put your code body here
    # write a few new lines to check for previous results
    calc_dir = '.' # going to be needed if you create a new dir for each calc
    if 'vasprun.xml' in os.listdir(calc_dir):
        traj = os.path.join(calc_dir, 'vasprun.xml')
    else:
        traj = 'start.traj'

    # normal vasp stuff
    atoms = read(traj)
    params = dict(nsw=100, ediff=1e-5, encut=400, ivdw=12, kpts=(1,1,1))
    calc = Vasp(**params)
    atoms.calc = calc

	os.makedirs(calc_dir, exist_ok=True)
    os.chdir(calc_dir)
    atoms.get_potential_energy()
    atoms.write('opt_from_vasp.traj')

if __name__ == '__main__':
    main()
```

Here note the lines:

```python
    # write a few new lines to check for previous results
    calc_dir = '.' # going to be needed if you create a new dir for each calc
    if 'vasprun.xml' in os.listdir(calc_dir):
        traj = os.path.join(calc_dir, 'vasprun.xml')
    else:
        traj = 'start.traj'
```

This is the part you will need to add to your existing scripts! Check if results from a previous
run exist, and if so, start from those results. Again, this is needed because each time the
script is resubmitted, the ENTIRE script is reran. Depending on what you're doing, this
may or may not be trivial to implement. Single calculations like above are simple,
but sequential calculations that proceed from the results of the previous
are a bit obnoxious to implement, but I'll let you figure that out ;)
- hint: use glob.glob and write your calc dirs in a sortable way.

Also **NOTE that certain calculations (like vibrational calcs w/ IBRION=5) need to be ran in their
entirety in a single submission. These are not possible for variable time jobs!** Though
for vibrational calculations specifically, you can just use the ASE Vibrations module to
do each displacement as a single point calculation and construct the dynamical matrix from those
results, allowing for resubmissions.

Here's an additional example using kT,

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#SBATCH -t 24:00:00 --comment=24:00:00 --time-min=2:00:00
#SBATCH -q overrun -N 1 -C knl --ntasks-per-node=64
#SBATCH --output=job.out --error=job.err

# use whatever repo you're in that has 0 hours remaining
#SBATCH -A mXXXX

# resubmission stuff
#SBATCH --signal=B:USR1@60 --requeue --open-mode=append

"""
Created on Thu Mar 26 17:10:56 2020

@author: ark245
"""
import os, sys 
import glob
sys.path.insert(0,'/global/homes/t/tdprice/kultools')
from ase import io
from kul_tools import KulTools as KT

from resub import resub

@resub
def main():
    kt = KT(gamma_only=False,structure_type='zeo')
    kt.set_calculation_type('opt')

    # lazy checkpointing for now, overwrites on each resubmission
    opt_dir = glob.glob('opt_*400*') # whatever KT names dirs, this should probably work
    if len(opt_dir) == 0:
        atoms = io.read('start.traj')
        atoms.pbc=True
    else:
        atoms = io.read(os.path.join(opt_dir[0], 'vasprun.xml'))

    kt.set_structure(atoms)
    kt.set_overall_vasp_params({'gga':'PS', 'ivdw': 12, 'encut': 400, 'isif': 2, 'kpts':(2,2,1)})
    kt.run()

if __name__ == "__main__":
    main()
```

**ANOTHER NOTE: In it's current form, the @resub approach will just resubmit indefinitely until
the calculation is finished. So the walltime doesn't actually matter. Which means if something goes
awry and your calculation never converges, it will keep resubmitting until you stop it (or system
maintenance/failure happens).** I personally don't mind this, because it is more apparent that
an issue exists when I see only a few jobs remaining on the queue after a while, so I can go
easily locate the calculations with problems. Plus you will never have the issue of selecting too short
of a walltime :). Though it is admittedly a potentially poor use of computational time. I'll implement
this eventually (it's really not hard, just being lazy).

## Adding checkpoint functions
(Somewhat advanced, most people can probably ignore) If you want to do some form
of checkpointing with your scripts, you can write a python
function to do so and pass it to @resub. This function will be called right
before the script is resubmitted. You can also use this in lieu of having your script
check for previous results in the beginning, e.g., write vasprun.xml to start.traj 
before resubmitting. Here is a general idea of how to implement a checkpoint function
using @resub,

```python
# header stuff from above
###############################################################################
from resub import resub

# use keyword args if you have any arguments!!
def my_checkpoint(kwarg1=None, kwarg2=None):
	do_stuff(kwarg1)
	do_other_stuff(kwarg2)
	return

@resub(checkpoint=my_checkpoint, ckpt_kwargs=dict(kwarg1=whatever, kwarg2=whatever2))
def main():
	code_body_stuff()

if __name__ == '__main__':
	main()
```


If your checkpoint function is computationally demanding,
it may not complete before the job hits the allocated time, and resubmission
won't happen (so the job just stops). If this happens, you can increase the signal time
in the SBATCH comment to something longer.

```python
# old
#SBATCH --signal=B:USR1@60 

# new
#SBATCH --signal=B:USR1@300 
```

This time corresponds to how much time is given for checkpointing to occur before resubmission.
So here we have increased the time from 60 seconds to 300 seconds. Adjust as needed for slow
checkpointing functions. Though I can't imagine you'll ever need more than 60 seconds, just
making a note incase it's an issue someday for someone.

### Side rant on STOPCARs for those who know what I'm talking about
If you're writing STOPCARs for checkpointing VASP, then STOP, because that doesn't really accomplish anything
(I know the NERSC site uses it as an example of a VASP checkpoint script, but it seems pointless to me).
First of all, starting from a converged ionic step only matters if you're writing WAVECARs
- and most people aren't for the majority of calculations
because the files are massive. Plus if you are writing them, it's usually a hybrid functional that
is too slow to justify running as a variable time job anyway. But even if you are writing WAVECARS,
the WAVECAR is only written after each ionic step finishes. What does this mean? If you write a STOPCAR
at N steps, VASP will finish this step, write your WAVECAR, update your geometry, and exit.
Then your job is resubmitted and restarts from the WAVECAR and geometry at N steps. If you don't
worry about STOPCAR checkpointing, the WAVECAR will be written at N steps anyway
(because it's written after each ionic step), then VASP will proceed to N+1 steps
but crash without finishing this step due to resubmission. Then your job is resubmitted...
and AGAIN starts from the WAVECAR and geometry written at N steps. So you have accomplished nothing
except for added additional complications of having to adjust the signal timer to allow for whatever
system + parameters you're using in that calculation to finish an ionic step. (Just including this
so people don't waste their time with this like I did when I first read the NERSC documentation a few years ago).

THAT BEING SAID, SOMEONE PLEASE CORRECT THIS IF I'M WRONG - AND PROVIDE PROOF!
(because I've tested this, and I don't think I'm wrong, but I also wouldn't be
totally surprised if I'm overlooking something here).
