import os
import numpy as np
from ase.build import molecule
from ase.neighborlist import mic
from ase.io import read


class FillMOF:
    def __init__(self, atoms, adsorbate='H2O', tol=2.0):
        """
        Class for randomly adding an adsorbate to an adsorbent unit cell.

        Args:
            atoms (ase.Atoms): adsorbent (MOF, etc.) to add stuff to.

            adsorbate (str or ase.Atoms): Adsorbate formula (for use with ase.build.molecule),
                path to .traj file, or ase.Atoms object.

            tol (float): Minimum distance between all adsorbate and adsorbent atoms.
        """
        self._atoms = atoms.copy()
        self.atoms = self._atoms.copy()
        self.n_atoms = len(atoms)
        if isinstance(adsorbate, str):
            if os.path.isfile(adsorbate): # traj file or similar
                self.adsorbate = read(adsorbate)
            else:
                self.adsorbate = molecule(adsorbate)
        else: # Atoms object
            self.adsorbate = adsorbate
        self.full = False
        self.tol = tol

    def fill(self, n=None, maxiter=500, verbose=True):
        """
        Attempts to fill adsorbent with n adsorbate molecules.

        Args:
            n (int): Max number of adsorbate molecules to add
            maxiter (int): Maximum number of random positions to try to add adsorbate to
            verbose (bool): Print stuff or not

        Returns:
            ase.Atoms: Atoms object with adsorbent and new adsorbate molecules
        """

        self.atoms = self._atoms.copy()
        self.maxiter = maxiter
        ads = self.adsorbate.get_chemical_formula()
        j = 0
        while self.add():
            j += 1
            if n and n == j:
                break
            if verbose:
                print(f"ADDED {ads} AFTER {self.k} ATTEMPTS" )
        self.n_ads = (len(self.atoms) - self.n_atoms) // len(self.adsorbate)
        if verbose:
            print(f"Added {self.n_ads} {ads} molecules")
        return self.atoms

    def add(self):
        ads = self.adsorbate.copy()
        self.rotate(ads)

        self.position = np.sum(self.atoms.cell.array * np.random.random((3, 1)), axis=0)
        self.translate(ads)

        distances = self.get_distances(ads)

        self.k = 0
        #TODO: make this more efficient, it's terrible for dense adsorbents
        while min(distances) < self.tol:
            if self.k !=0 and self.k % 50 == 0:
                self.rotate(ads)
            self.position = np.sum(self.atoms.cell.array * np.random.random((3, 1)), axis=0)
            self.translate(ads)

            distances = self.get_distances(ads)
            self.k += 1

            if self.k == self.maxiter:
                return False

        self.atoms += ads
        return True

    def rotate(self, ads):
        # random unit vectors to rotate water randomly
        u, v = np.random.normal(size=(3,)), np.random.normal(size=(3,))
        u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
        ads.rotate(u, v)
        self.cop = np.sum(ads.positions, 0) / len(ads)

    def translate(self, ads):
        # random unit vectors to rotate water randomly
        ads.translate(self.position - self.cop)
        self.cop = np.sum(ads.positions, 0) / len(ads)

    def get_distances(self, adsorbate):
        all_distances = []
        for a in adsorbate:
            distances = mic(a.position - self.atoms.positions, self.atoms.cell)
            distances = np.linalg.norm(distances, axis=1)
            all_distances.extend(distances)
        return all_distances


if __name__ == "__main__":
    # EXAMPLE
    adsorbate = read("CO2.traj")
    mof = read("zif8.traj")

    filler = FillMOF(mof, adsorbate=adsorbate, tol=2.0)
    filler.fill(n=5) # add 5 CO2 molecules if possible with specified tol
