import numpy as np
import cv2
import os
#from sklearn.cluster import KMeans
import faiss
from time import sleep, strftime, time

class FaissKMeans:
    def __init__(self, n_clusters=8, n_init=10, max_iter=300):
        self.n_clusters = n_clusters
        self.n_init = n_init
        self.max_iter = max_iter
        self.kmeans = None
        self.cluster_centers_ = None
        self.inertia_ = None

    def fit(self, X):
        self.kmeans = faiss.Kmeans(d=X.shape[1],
                                   k=self.n_clusters,
                                   niter=self.max_iter,
                                   nredo=self.n_init)
        self.kmeans.train(X).astype(np.float32)
        self.cluster_centers_ = self.kmeans.centroids
        self.inertia_ = self.kmeans.obj[-1]

    def predict(self, X):
        return self.kmeans.index.search(X.astype(np.float32), 1)[1]

class BovwPlaceRecognition:
    def __init__(self):
        self.num_clusters = 150 # TODO tune this parameter
        self.sift = cv2.SIFT_create()
        self.images = {}
        self.training_img_histograms = {}
        self.visual_words = []


    def build_database(self, image_folder):
        print('5: ',time())
        self.images = self._load_images_from_folder(image_folder)
        print('6: ',time())

        descriptor_list, image_to_descriptors = self._compute_sift_features(self.images)
        print('7: ',time())
        self.visual_words = self._build_visual_words(descriptor_list)
        print('8: ',time())

        for key, desc in image_to_descriptors.items():
            hist = self._calculate_histogram(desc, self.visual_words)
            self.training_img_histograms[key] = hist


    def query_by_image(self, query_img):
        _kp, des = self.sift.detectAndCompute(query_img, None)
        query_hist = self._calculate_histogram(des, self.visual_words)
        match_filename, match_distance = self._get_tentative_match(query_hist, self.training_img_histograms)
        match_img = self.images[match_filename]
        # TODO geometric verification
        return match_filename, match_img, match_distance


    def _load_images_from_folder(self, folder):
        images = {}
        for image_name in os.listdir(folder):
            image_path = os.path.join(folder, image_name)
            #images.append(cv2.imread(image_path))
            images[image_name] = cv2.imread(image_path)
        return images


    def _compute_sift_features(self, images):
        descriptor_list = []
        image_to_descriptors = {}

        for key, img in images.items():
            _kp, des = self.sift.detectAndCompute(img, None)
            if des is not None:
                descriptor_list.extend(des)
                image_to_descriptors[key] = des
        descriptor_array = np.array(descriptor_list, dtype=np.float32)
        return descriptor_array, image_to_descriptors


    def _build_visual_words(self, descriptor_list):
        kmeans = FaissKMeans(n_clusters=self.num_clusters)
        kmeans.fit(descriptor_list)
        visual_words = kmeans.cluster_centers_
        return visual_words


    def _calculate_histogram(self, descriptors, visual_words):
        # Create an array to store the histogram
        histogram = np.zeros(len(visual_words))

        for descriptor in descriptors:
            # Find the nearest visual word for the descriptor
            nearest_word = np.argmin(np.linalg.norm(visual_words - descriptor, axis=1))
            # Increment the corresponding bin in the histogram
            histogram[nearest_word] += 1

        return histogram


    def _get_tentative_match(self, target_histogram, dataset_histograms):
        best_match = None
        min_distance = float('inf')

        for key, histogram in dataset_histograms.items():
            distance = np.linalg.norm(target_histogram - histogram)
            if distance < min_distance:
                min_distance = distance
                best_match = key

        return best_match, min_distance
