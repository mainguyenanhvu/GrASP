import numpy as np
import MDAnalysis as mda
from sklearn.cluster import MeanShift
from sklearn.cluster import estimate_bandwidth
from scipy.spatial import ConvexHull, HalfspaceIntersection
from scipy.optimize import linprog
import os
from tqdm import tqdm

def sort_clusters(cluster_ids, probs, labels):
    c_probs = []
    unique_ids = np.unique(cluster_ids)

    for c_id in unique_ids[unique_ids >= 0]:
        c_prob = np.mean(probs[:,1][labels][cluster_ids==c_id])
        c_probs.append(c_prob)

    c_order = np.argsort(c_probs)

    sorted_ids = -1*np.ones(cluster_ids.shape)
    for new_c in range(len(c_order)):
        old_c = c_order[new_c]
        sorted_ids[cluster_ids == old_c] = new_c
        
    return sorted_ids

def cluster_atoms(all_coords, predicted_probs, threshold=.5, quantile=.3, **kwargs):
    predicted_labels = predicted_probs[:,1] > threshold
    if np.sum(predicted_labels) == 0:
        # No positive predictions were made with specified cutoff
        return None, None, None
    bind_coords = all_coords[predicted_labels]
    bw = estimate_bandwidth(bind_coords, quantile=quantile)
    if bw == 0:
        bw = None
    ms_clustering = MeanShift(bandwidth=bw, **kwargs).fit(bind_coords)
    cluster_ids = ms_clustering.labels_
    
    sorted_ids = sort_clusters(cluster_ids, predicted_probs, predicted_labels)

    all_ids = -1*np.ones(predicted_labels.shape)
    all_ids[predicted_labels] = sorted_ids
    
    return bind_coords, sorted_ids, all_ids

def get_centroid(coords):
    return np.mean(coords, axis=0)

def center_dist(site_points1, site_points2):
    centroid1 = get_centroid(site_points1)
    centroid2 = get_centroid(site_points2)
    distance = np.sqrt(np.sum((centroid1 - centroid2)**2))
    
    return distance

def cheb_center(halfspaces):
    norm_vector = np.reshape(np.linalg.norm(halfspaces[:, :-1], axis=1),
    (halfspaces.shape[0], 1))
    c = np.zeros((halfspaces.shape[1],))
    c[-1] = -1
    A = np.hstack((halfspaces[:, :-1], norm_vector))
    b = - halfspaces[:, -1:]
    res = linprog(c, A_ub=A, b_ub=b, bounds=(None, None))
    center = res.x[:-1]
    radius = res.x[-1]
    
    return center, radius

def hull_jaccard(hull1, hull2, intersect_hull):
    intersect_vol = intersect_hull.volume
    union_vol = hull1.volume + hull2.volume - intersect_hull.volume
    return intersect_vol/union_vol

def volumetric_overlap(site_points1, site_points2):
    hull1 = ConvexHull(site_points1)
    hull2 = ConvexHull(site_points2)
    
    halfspaces = np.append(hull1.equations, hull2.equations, axis=0)
    center, radius = cheb_center(halfspaces)
    
    if radius <= 0:
        return 0

    half_inter = HalfspaceIntersection(halfspaces, center)
    intersect_hull = ConvexHull(half_inter.intersections)
    
    jaccard = hull_jaccard(hull1, hull2, intersect_hull)
    
    return jaccard

def site_metrics(all_coords, predicted_probs, true_labels, threshold=.5, quantile=.3, cluster_all=False):
    """Cluster binding sites and calculate distance from true site center and volumetric overlap with true site 

    Parameters
    ----------
    all_coords : numpy array
        Protein atomic coordinates.

    predicted_probs : numpy_array
        Class probabilities for not site in column 0 and site in column 1.

    true_labels : numpy_array
        Class membership, 0 for not site, 1 for site.

    threshold : float
        Probability threshold to predict binding site atoms.

    quantile : float
        Quantile used in bandwidth selection for mean shift clustering.

    cluster_all : bool
        Whether to assign points outside kernels to the nearest cluster or leave them unlabeled.

    Returns
    -------
    center_distances: list
        List of distances from predicted site center to true center. 
        Listed in descending order by predicted site probability.

    volumentric_overlaps: list
        Jaccard similarity between predicted site convex hull and true site convex hull. 
        Listed in descending order by predicted site probability.

    """
    bind_coords, sorted_ids, all_ids = cluster_atoms(all_coords, predicted_probs, threshold=threshold, quantile=quantile, cluster_all=cluster_all)


    true_points = all_coords[true_labels==1]

    center_distances = []
    volumetric_overlaps = []
    for c_id in np.unique(sorted_ids)[::-1]:
        if c_id != None:
            if c_id >= 0:
                predicted_points = bind_coords[sorted_ids == c_id]
                center_distances.append(center_dist(predicted_points, true_points))
                if len(predicted_points) < 4:  # You need four points to define a context whole so we'll say the overlap is 0
                    volumetric_overlaps.append(0) 
                else:
                    volumetric_overlaps.append(volumetric_overlap(predicted_points, true_points))

    return center_distances, volumetric_overlaps


# How the files were saved
# np.save(prepend + '/test_metrics/test_probs/' + model_name + '_' + assembly_name, probs.detach().cpu().numpy())
# np.save(prepend + '/test_metrics/test_labels/' + '_' + assembly_name, labels.detach().cpu().numpy())

model_name = "trained_model_1640072931.267488_epoch_49"
threshold = 0.5

# Calculate Site Metrics
prepend = str(os.getcwd())

cent_dist_list = []
vol_overlap_list = []
no_prediction_count = 0

for file in tqdm(os.listdir(prepend + '/test_data_dir/mol2')):
    assembly_name = file[:-5]
    trimmed_protein = mda.Universe(prepend + '/test_data_dir/mol2/' + assembly_name + '.mol2')
    labels = np.load(prepend + '/test_metrics/test_labels/' + assembly_name + '.npy')
    probs = np.load(prepend + '/test_metrics/test_probs/' + model_name + '_' + assembly_name + '.npy')
    cent_dist, vol_overlap = site_metrics(trimmed_protein.atoms.positions, probs, labels, threshold=threshold)
    if cent_dist == [] or vol_overlap_list == []: 
        no_prediction_count += 1
    cent_dist_list.append(cent_dist)
    vol_overlap_list.append(vol_overlap)
    

cleaned_vol_overlap_list =  [entry[0] if len(entry) > 0 else np.nan for entry in vol_overlap_list]
cleaned_cent_dist_list =  [entry[0] if len(entry) > 0 else np.nan for entry in cent_dist_list]

print("Cutoff (Prediction Threshold):", threshold)
print("Number of systems with no predictions:", no_prediction_count)
print("Average Distance From Center (Top 1):", np.nanmean(cleaned_cent_dist_list))
print("Average Discretized Volume Overlap (Top 1):", np.nanmean(cleaned_vol_overlap_list))


# trimmed_protein = mda.Universe(prepend + '/test_data_dir/mol2/' + assembly_name + '.mol2')
# center_dist, vol_overlap = site_metrics(trimmed_protein.atoms.positions, probs.detach().cpu().numpy(), labels.detach().cpu().numpy())
# print(center_dist)
# print(vol_overlap)