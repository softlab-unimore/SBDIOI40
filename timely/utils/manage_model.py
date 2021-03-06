import os
import json
import numpy as np
import pandas as pd

from ..models.anomaly_detection.setup_clustering import SetupClustering
from ..models.anomaly_detection.isolation_forest import IsolationForest
from ..models.anomaly_detection.one_class_svm import OneClassSVM
from ..models.anomaly_detection.local_outlier_factor import LOF
from ..models.anomaly_detection.pca import PCA

from ..models.anomaly_detection.cnn_autoencoder import CNNAutoEncoder
from ..models.anomaly_detection.lstm_autoencoder import LSTMAutoEncoder
from ..models.anomaly_detection.bilstm_autoencoder import BiLSTMAutoEncoder
from ..models.anomaly_detection.deep_autoencoder import DeepAutoEncoder

from ..models.classifier.deep_classifier import DeepClassifier
from ..models.classifier.regression import LinearClassifier

from .tools import get_sliding_window_matrix


def get_model(model_type, params_file=None):
    # Get models params
    # print('Get params')
    if params_file is None or not os.path.isfile(params_file):
        print('No provided params: use default one')
        params = {}
    else:
        try:
            with open(params_file) as file:
                params = json.load(file)
        except (json.decoder.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError('Impossible read json params')

    # Model initialization
    print("Model initialization: ", model_type)
    if model_type == 'isolation_forest':
        model = IsolationForest(verbose=True, n_jobs=2, **params)
    elif model_type == 'setup_clustering':
        model = SetupClustering(**params)
    elif model_type == 'pca':
        model = PCA(**params)
    elif model_type == 'svm':
        model = OneClassSVM(**params)
    elif model_type == 'lof':
        model = LOF(**params)
    elif model_type == 'cnn':
        model = CNNAutoEncoder(**params)
    elif model_type == 'lstm':
        model = LSTMAutoEncoder(**params)
    elif model_type == 'bilstm':
        model = BiLSTMAutoEncoder(**params)
    elif model_type == 'deep':
        model = DeepAutoEncoder(**params)
    elif model_type == 'classifier':
        model = DeepClassifier(**params)
    elif model_type == 'linear':
        model = LinearClassifier(**params)

    else:
        raise ValueError('{} does not exist'.format(model_type))

    return model


def predict_anomaly(ds, model, kernel, with_skip=True):
    if with_skip:
        stride = kernel
    else:
        stride = 1

    # Create set
    x_test = get_sliding_window_matrix(ds.values, kernel, stride)

    # Testing
    y_pred = model.predict(x_test)

    # Expand results
    y_pred = [val for val in y_pred for _ in range(stride)]
    res = np.zeros((len(ds)))

    if with_skip:
        res[:len(y_pred)] = y_pred
    else:
        res[-len(y_pred):] = y_pred

    y_pred = pd.Series(res, index=ds.index, name='features')

    return y_pred
