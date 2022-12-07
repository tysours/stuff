import numpy as np
import matplotlib.pyplot as plt
from ase.io import iread, write
from ase.io.trajectory import Trajectory

class VibModes:
    """
    Class for visualizing vibrational modes from VASP calculations.
    Reads OUTCAR from ibrion=5/6 calculation and writes .traj files
    to see the atomic motions corresponding to each mode.

    Args:
        OUTCAR (str): Path to OUTCAR file
        freuency_range (list[float]): Range of mode frequencies of interest, e.g.,
            [freq_min, freq_max].
    """
    def __init__(self, OUTCAR, frequency_range=None):
        self.set_range(frequency_range)
        self.OUTCAR = OUTCAR
        self.atoms = next(iread(OUTCAR, index=0))
        self.n_atoms = len(self.atoms)
        self.frequencies = []
        self.displacements = []

    def set_range(self, frequency_range):
        if frequency_range:
            self.min_freq, self.max_freq = frequency_range
        else:
            self.min_freq = -np.inf
            self.max_freq = np.inf

    def read(self, read_displacements=True):
        with open(self.OUTCAR) as file:
            lines = file.readlines()
        for i, line in enumerate(lines):
            if "THz" in line:
                freq = self._get_freq(line)
                if self.min_freq <= abs(freq) <= self.max_freq:
                    self.frequencies.append(freq)
                    if read_displacements:
                        disp = self._get_disp(lines[i+2:i+self.n_atoms+2])
                        self.displacements.append(disp)

    def write(self, frequency_range=None, mult=1.0):
        if frequency_range:
            self.set_range(frequency_range)
        r = self.atoms.get_positions()
        atoms = self.atoms.copy()
        j = 0
        for freq, disp in zip(self.frequencies, self.displacements):
            if self.min_freq <= abs(freq) <= self.max_freq:
                i = "" if freq > 0 else "i"
                traj = Trajectory(f"{j:04d}_{abs(freq):.0f}{i}.traj", "w")
                for x in np.linspace(0.0, 2 * np.pi, 20, endpoint=False):
                    atoms.set_positions(r + mult * np.sin(x) * disp)
                    traj.write(atoms)
                j += 1

    @staticmethod
    def _get_freq(line):
        i_freq = 6 if "f/i" in line else 7
        imag = -1 if "f/i" in line else 1
        return float(line.split()[i_freq]) * imag

    @staticmethod
    def _get_disp(lines):
        return np.array([_str_to_float(l) for l in lines])


def _str_to_float(line):
    return list(map(float, line.split()[-3:]))


# CLI stuff
def parse():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("OUTCAR", type=str,
            help="Path to OUTCAR file from VASP vibrational calculation")
    parser.add_argument("-r", "--range", type=list[float], nargs=2,
            metavar=("MIN_FREQ", "MAX_FREQ"),
            help="Range of frequency values of modes to write, fmin fmax")
    parser.add_argument("-m", "--mult", type=float, default=1.0,
            help="Multiplier value to adjust intensity of atomic motions"\
            "(i.e., lower value --> atoms move less in .traj")
    return parser.parse_args()


def main():
    args = parse()
    modes = VibModes(args.outcar, args.range)
    modes.read()
    modes.write(mult=args.mult)


if __name__ == "__main__":
    main()
