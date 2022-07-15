import os
import numpy as np
import pyximport; pyximport.install()


def process_system(path_to_protein_mol2_files, save_directory='./data_dir'):
    # I really wish I didn't have to do this but the way some of these paackages pickle I have no other way. If you know a better alternative feel free to reach out
    import re
    import MDAnalysis as mda
    from MDA_fix.MOL2Parser import MOL2Parser # fix added in MDA development build
    import numpy as np
    from pathlib import Path
    import scipy
    from fast_distance_computation import get_distance_matrix

    from rdkit import Chem
    from rdkit.Chem import ChemicalFeatures
    from rdkit import RDConfig

    from mdtraj import shrake_rupley
    from mdtraj import load as mdtrajload
    from collections import defaultdict

    # import warnings
    # warnings.filterwarnings("ignore") 

    #                     [One hot encoding of residue name                           polar Y/N     Acidic,Basic,Neutral  Pos/Neg/Neutral Charge]
    residue_dict = {'ALA':[1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    'ARG':[0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    0,     1,     0,      1,  0,  0], 
                    'ASN':[0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    0,     0,     1,      0,  0,  1], 
                    'ASP':[0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], 
                    'CYS':[0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  0,  1], 
                    'GLN':[0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    0,     0,     1,      0,  0,  1],                                           
                    'GLU':[0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,0,    1,     0,     0,      0,  1,  0], 
                    'GLY':[0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    'HIS':[0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    0,     1,     0,      0,  0,  1], 
                    "ILE":[0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    "LEU":[0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    "LYS":[0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    0,     1,     0,      1,  0,  0], 
                    "MET":[0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    "PHE":[0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    "PRO":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    "SER":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    0,     0,     1,      0,  0,  1], 
                    "THR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    0,     0,     1,      0,  0,  1], 
                    "TRP":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1], 
                    "TYR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  0,  1], 
                    "VAL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,   0,1,    0,     0,     1,      0,  0,  1],
                    "C":  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "G":  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "A":  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "U":  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "I":  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "DC": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # | < Pretty sure these are all acidic and negatively charged
                    "DG": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "DA": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "DU": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "DT": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,   1,0,    1,     0,     0,      0,  1,  0], # |
                    "DI": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,   1,0,    1,     0,     0,      0,  1,  0]  # |
    }
    hybridization_dict = {
        "S":          [1,0,0,0,0,0,0], 
        "SP":         [0,1,0,0,0,0,0], 
        "SP2":        [0,0,1,0,0,0,0],
        "SP3":        [0,0,0,1,0,0,0], 
        "SP3D":       [0,0,0,0,1,0,0], 
        "SP3D2":      [0,0,0,0,0,1,0], 
        "OTHER":      [0,0,0,0,0,0,1],
        "UNSPECIFIED":[0,0,0,0,0,0,0]
    }

    atom_dict = {'C': [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                'N': [0,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                'O': [0,0,1,0,0,0,0,0,0,0,0,0,0,0,0],
                'S': [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
                'H': [0,0,0,0,1,0,0,0,0,0,0,0,0,0,0],
                'MG':[0,0,0,0,0,1,0,0,0,0,0,0,0,0,0],
                'Z': [0,0,0,0,0,0,1,0,0,0,0,0,0,0,0],
                'MN':[0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
                'CA':[0,0,0,0,0,0,0,0,1,0,0,0,0,0,0],
                'FE':[0,0,0,0,0,0,0,0,0,1,0,0,0,0,0],
                'P': [0,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
                'CL':[0,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
                'F': [0,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
                'I': [0,0,0,0,0,0,0,0,0,0,0,0,0,1,0],
                'Br':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    }

    # Leaving an extra bit to denote self loops
    bond_type_dict = {
        '1': [1,0,0,0,0,0,0],
        '2': [0,1,0,0,0,0,0],
        '3': [0,0,1,0,0,0,0],
        'ar':[0,0,0,1,0,0,0],
        'am':[0,0,0,0,1,0,0],
        'un':[0,0,0,0,0,1,0]
    }
    selection_str = "".join(["resname " + x + " or " for x in list(residue_dict.keys())[:-1]]) + "resname " + str(list(residue_dict.keys())[-1])
    feature_factory = ChemicalFeatures.BuildFeatureFactory(str(Path(RDConfig.RDDataDir) / "BaseFeatures.fdef"))
    
    # Adjacency Matrix
    path_to_files = path_to_protein_mol2_files
    structure_name = path_to_protein_mol2_files.split('/')[-1]
    try:
        protein_w_H = mda.Universe(path_to_files + '/protein.mol2', format='mol2')
        rdkit_protein_w_H = Chem.MolFromMol2File(path_to_files + '/protein.mol2', removeHs = False, sanitize=False, cleanupSubstructures=False)
        # rdkit_protein_w_H = Chem.MolFromMol2File(path_to_files + '/protein.mol2', removeHs = False)

    except Exception as e: 
        raise e
        print("Failed to compute charges for the following file due to a structure error. This file will be skipped:", path_to_files + '/protein.mol2', flush=True)
        return
    res_names = protein_w_H.residues.resnames
    new_names = [ "".join(re.findall("[a-zA-Z]+", name)).upper() for name in res_names]
    protein_w_H.residues.resnames = new_names
    
    protein_w_H = protein_w_H.select_atoms(selection_str)
    # Calculate SAS for each atom, this needs to be done before hydrogens are dropped
    try:
        traj = mdtrajload(path_to_files + '/protein.mol2')
        SAS = shrake_rupley(traj, mode='atom')
        if len(SAS) > 1:
            # Sanity check, I'm pretty sure this should never happen
            raise Exception("Did not expect more than one list of SAS values")   
        # SAS_org = SAS
        SAS = SAS[0]
    except KeyError as e:
        print("Value not included in dictionary \"{}\" while calculating SASA {}.".format(e, path_to_files))
        # failed_list.append([path_to_files, "Value not included in dictionary \"{}\" while calculating SASA {}.".format(e, path_to_files)])
        return

    # Add SAS from hydrogen to bonded atom, create number of bonded hydrogens feature
    num_bonded_H = np.zeros(traj.n_atoms)
    for atom in protein_w_H:
        is_bonded_to_H = [re.search("^[a-zA-Z]+", bond.type).group().upper() == 'H' for _, bond in atom.bonds]
        num_bonded_H[atom.index] = sum(is_bonded_to_H)
        # Because the bonds have the old ids, we use our map to the new ids to access the SAS value, if the value is -1
        # it means that the bonded atom no longer exists in our universe (i.e., it was dropped). If this happens it will
        # be a very rare occasion as must things other than solvents are not droppped.
        local_SAS = np.array([SAS[atom_idx[1]]  for atom_idx in atom.bonds.indices])    
        SAS[atom.index] += np.sum(local_SAS * is_bonded_to_H)       # Only take the values from hydrogens
    # Drop Hydrogens
    protein_w_H.ids = np.arange(0, len(protein_w_H.atoms))
    protein = protein_w_H.select_atoms("not type H")
    protein.ids = np.arange(0, len(protein.atoms))              # Abusing atoms ids to make them zero-indexed which makes our life easier

    trimmed = scipy.sparse.lil_matrix((len(protein.atoms.positions), len(protein.atoms.positions)), dtype='float')
    get_distance_matrix(protein.atoms.positions, trimmed, 7)
    trimmed = trimmed.tocsr()

    # Feature Matrix
    feature_array = []  # This will contain all of the features for a given molecule

    try:
        rdkit_protein_w_H.UpdatePropertyCache(strict=False)
    except Exception as e:
        print("Failed to update property cache while processing", path_to_files)
        return
    acceptor_indices = [x.GetAtomIds()[0] for x in feature_factory.GetFeaturesForMol(rdkit_protein_w_H, includeOnly="Acceptor")]
    donor_indices = [x.GetAtomIds()[0] for x in feature_factory.GetFeaturesForMol(rdkit_protein_w_H, includeOnly="Donor")]
    hydrophobe_indices = [x.GetAtomIds()[0] for x in feature_factory.GetFeaturesForMol(rdkit_protein_w_H, includeOnly="Hydrophobe")]                # Seems to be the slow one, comparitively
    lumped_hydrophobe_indices = [x.GetAtomIds()[0] for x in feature_factory.GetFeaturesForMol(rdkit_protein_w_H, includeOnly="LumpedHydrophobe")]


    bins = np.arange(0,10)
    pi_4 = 4 * np.pi
    for atom in protein.atoms:                                                              # Iterate through residues and create vectors of features
        name = "".join(re.findall("^[a-zA-Z]+", atom.resname)).upper()                      # Remove numbers from the name string
        element = re.search("^[a-zA-Z]+", atom.type).group().upper()
        try:
            # rdf calculation where dr = 1 and r_max = 5
            d = trimmed[np.where(protein.ids == atom.id)[0][0]]
            n, bins = np.histogram(d[d>0], bins =bins)
            r = bins[1:]
            g = n/(pi_4 * r ** 2)

            # RDKit Features
            rdkit_atom = rdkit_protein_w_H.GetAtomWithIdx(int(atom.index))
            
            num_bonds_w_heavy_atoms = [rdkit_atom.GetTotalDegree() - rdkit_atom.GetTotalNumHs(includeNeighbors=True)]
            formal_charge = [rdkit_atom.GetFormalCharge()]
            is_in_ring = [1,0] if rdkit_atom.IsInRing() else [0,1]
            is_aromatic = [1,0] if rdkit_atom.GetIsAromatic() else [0,1]
            num_radical_electrons = [rdkit_atom.GetNumRadicalElectrons()]
            mass = [rdkit_atom.GetMass()]
            hybridization = hybridization_dict[str(rdkit_atom.GetHybridization())]
            
            acceptor = [1,0] if atom.index in acceptor_indices else [0,1] 
            donor = [1,0] if atom.index in donor_indices else [0,1]
            hydrophobe = [1,0] if atom.index in hydrophobe_indices else [0,1]
            lumped_hydrophobe = [1,0] if atom.index in lumped_hydrophobe_indices else [0,1]

            if name == 'MET' and element == 'SE': element = 'S' # for featurizing selenomethionine

            assert not np.any(np.isnan(num_bonds_w_heavy_atoms))
            assert not np.any(np.isnan(formal_charge))
            assert not np.any(np.isnan(is_in_ring))
            assert not np.any(np.isnan(is_aromatic))
            assert not np.any(np.isnan(num_radical_electrons))
            assert not np.any(np.isnan(mass))
            assert not np.any(np.isnan(hybridization))
            assert not np.any(np.isnan(acceptor))
            assert not np.any(np.isnan(donor))
            assert not np.any(np.isnan(hydrophobe)) 
            assert not np.any(np.isnan(lumped_hydrophobe))

            # Add feature vector with                                                  54-63          64               65               66               67-68        69-70                   71        72        73-79       80-81    82-83     84-85       86-87
            feature_array.append(np.concatenate((residue_dict[name], atom_dict[element], g, [SAS[atom.index]], formal_charge, num_bonds_w_heavy_atoms, is_in_ring, is_aromatic, num_radical_electrons, mass, hybridization, acceptor, donor, hydrophobe, lumped_hydrophobe)))  #,formal_charge     25                       # Add corresponding features to feature array
        except Exception as e:
            print("Error while feautrizing atom for file {}.{}".format(path_to_files,e), flush=True)
            return -2
            # raise ValueError ("Value not included in dictionary \"{}\" while generating feature vector for {}.".format(name, path_to_files)) from e


    if trimmed.shape[0] != len(feature_array):  # Sanity Check
        raise ValueError ("Adjacency matrix shape ({}) did not match feature array shape ({}). {}".format(np.array(trimmed).shape, np.array(feature_array).shape, structure_name))

    # Classes
    site = mda.Universe(path_to_files + '/site.mol2', format='mol2')
    res_names = site.residues.resnames
    new_names = [ "".join(re.findall("[a-zA-Z]+", name)).upper() for name in res_names]
    site.residues.resnames = new_names
    site = site.select_atoms(selection_str).select_atoms("not type H")

    site.ids = np.arange(0,len(site.atoms))

    binding_site_lst = []

    # Sometimes the site atoms are not found in the protein. This happens when they're a part of a nonstandard residues.
    # For now, we'll skip them and keep a count of how many there are
    for atom in site.atoms:
        try:
            x, y, z = atom.position                                                                       # Get the coordinates of each atom of the binding site
            binding_site_lst.append(protein.select_atoms("point {} {} {} 0.1".format(x, y, z))[0].id)      # Select that atom in the whole protein
        except Exception as e:
            print(atom)
            print("Binding site atom not found in filtered protein. Was it dropped? \n Filename:", str(path_to_files))
            # return -1

    if binding_site_lst == []:
        print(site.atoms)
        raise Exception("Binding Site Not Found")

    mask = np.ones(len(protein.atoms), bool)                                                         # Inverse of the atoms in the binding site
    mask[binding_site_lst] = False

    classes = np.zeros((len(protein.atoms),2))
    classes[binding_site_lst, 1] = 1                                                                    # Set all atoms in the binding site to class 2
    classes[mask, 0] = 1                                                                                # Set all atoms not in the binding site to class 1

    # Creating edge_attributes dictionary. Only holds bond types, weights are stored in trimmed
    edge_attributes = {tuple(bond.atoms.ids):{"bond_type":bond_type_dict[bond.order]} for bond in protein.bonds}

    np.savez_compressed(save_directory + '/raw/' + structure_name, adj_matrix = trimmed, feature_matrix = feature_array, class_array = classes, edge_attributes = edge_attributes)
    protein.atoms.write(save_directory + '/mol2/' + str(structure_name) +'.mol2')

    return None


# Should run when file is called but not imported
# if __name__ == "__main__":
#     from joblib import Parallel, delayed
#     from tqdm import tqdm
    
#     # print(selection_str)
#     # total_files = len(os.listdir('./scPDB_raw_data'))
#     # index = 1 # I have no idea what this was for, got I hope we don't need it
#     # failed_list = []

#     inputs = ['./scPDB_raw_data' + struct_name for struct_name in sorted(list(os.listdir('./scPDB_raw_data')))]

#     if not os.path.isdir('./data_dir'):
#         os.makedirs('./data_dir')
#     ##########################################
#     # Comment me out to run just one file
#     num_cores = 24
    
#     from joblib.externals.loky import set_loky_pickler
#     set_loky_pickler("dill")
    
#     r = Parallel(n_jobs=num_cores)(delayed(process_system)(x, save_directory='./data_dir') for x in tqdm(inputs[:]))
#     # Parallel(n_jobs=2)(delayed(process_system)(x) for x in ['1iep_1','3eky_1'])

#     # np.savez('./failed_list', np.array(failed_list))
    ##########################################

    ##########################################
    # Uncomment me to run just one file
    import time
    # print("Starting")
    # start = time.time()
    # process_system('1iep_1',residue_dict,hybridization_dict,atom_dict,bond_type_dict,selection_str) 
    # print("Finished. Total Time:", str(time.time() - start)) 
    ##########################################
# finally:
#     res, i = zip(*r)
#     if res.count(-1) > 0:
#         print("Warning: Number of files skipped due to a nonstandard residue being a part of the site:", res.count(-1))

if __name__ == "_main__":
    structure_name = '1ds7_2'
    process_system('./data_dir/unprocessed_mol2/' + structure_name, save_directory='./data_dir')
