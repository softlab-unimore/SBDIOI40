import os
import json
import argparse
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report

import matplotlib.pyplot as plt

from timely.utils.manage_model import get_model
from timely.utils.manage_file import get_files, read_ds_lvm
from timely.utils.tools import get_sliding_window_matrix
from timely.transforms.transformer import resample, resample_with_feature_extractor, get_transformer


def get_argument():
    parser = argparse.ArgumentParser(description='Evaluation Anomaly and Normal behaviour')

    parser.add_argument('--input', required=True, type=str, help='Input Params')
    args = parser.parse_args()

    try:
        with open(args.input) as file:
            params = json.load(file)
    except (json.decoder.JSONDecodeError, FileNotFoundError) as e:
        raise ValueError('Impossible read json params')

    return params


def apply_transform(ds, transformer):
    return pd.DataFrame(transformer.transform(ds.values), columns=ds.columns)


def transform_data(ds_list, transform_type):
    # Concat list of dataframe
    ds_concat = pd.concat(ds_list, axis=0, ignore_index=True)

    # Train transformer
    transformer = get_transformer(ds_concat, transform_type)

    # Apply transformer
    ds_transformed_list = [apply_transform(ds, transformer) for ds in ds_list]

    return ds_transformed_list, transformer


def prepare_data(ds_list, labels, kernel, stride=1):
    # Create slide window matrix for each train
    x_list = [get_sliding_window_matrix(ds.values, kernel, stride) for ds in ds_list]

    # Assign labels for each matrix values
    y = np.hstack([[i] * len(x) for i, x in zip(labels, x_list)])

    # Concat each matrix
    x = np.vstack(x_list)

    return x, y


def main():
    params = get_argument()
    all_state_folder = params['all_state_folder'][:3]
    features_list = params['features_list']
    kernel = params['kernel']
    stride = params['stride']
    model_type = params['model_type']
    resample_rate = 6400

    kernel = 80
    stride = 1
    # model_type = 'cnn'
    transform_type = 'minmax'

    save_result = True
    output_dir = './results'

    skip_list = [0]
    train_list = [1]
    for selected_state_id, selected_state in enumerate(all_state_folder):
        ds_train_list = []
        y_train_list = []
        ds_test_list = []
        y_test_list = []
        file_train_list = []
        file_test_list = []

        # Read train and test files
        print('Evaluation state: {}'.format(selected_state_id))
        for state_id, folder in enumerate(all_state_folder):
            print('Read state: ', os.path.basename(folder))
            files = get_files(folder, ext='lvm')
            for i, filename in enumerate(files):
                if i in skip_list:
                    continue

                ds = read_ds_lvm(filename, get_header=False)
                ds = ds[features_list]
                ds = resample(ds, resample_rate)

                # plt.figure(figsize=(15, 8))
                # ds.plot(title='{}_{}'.format(state_id, filename))
                # plt.show()

                if i in train_list and state_id != selected_state_id:
                    ds_train_list.append(ds)
                    print('Train state {} file: {}'.format(state_id, filename))
                    y_train_list.append(state_id)
                else:
                    ds_test_list.append(ds)
                    print('Test state {} file: {}'.format(state_id, filename))
                    y_test_list.append(state_id)

        # Apply transform
        transformer = None
        if transform_type:
            print('Apply transform: ', transform_type)
            x_train_list, transformer = transform_data(ds_train_list, transform_type)
            x_test_list = [apply_transform(ds, transformer) for ds in ds_test_list]

        else:
            print('No transform selected')
            x_train_list = ds_train_list
            x_test_list = ds_test_list

        # Create train and test matrix set
        x_train, y_train = prepare_data(x_train_list, labels=y_train_list, kernel=kernel, stride=stride)
        x_test, y_test = prepare_data(x_test_list, labels=y_test_list, kernel=kernel, stride=stride)

        print('Train size:       ', x_train.shape)
        print('Train label size: ', y_train.shape)
        print('Test size:        ', x_test.shape)
        print('Test label size:  ', y_test.shape)

        order = np.random.permutation(len(x_train))
        x_new = x_train[order]
        y_new = y_train[order]

        # Model initialization
        print("Model initialization: {}".format(model_type))
        model = get_model(model_type)

        # Training
        print("Training...")
        model.fit(x=x_new, verbose=2)

        print("Anomaly accuracy")
        y_pred = model.predict(x_test, classifier=False)
        y_true = np.zeros(len(y_test))
        y_true[y_test == selected_state_id] = 1
        print(classification_report(y_true, y_pred))

        ds_res = pd.DataFrame(classification_report(y_true, y_pred, output_dict=True))

        if save_result:
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            filename = os.path.join(output_dir, 'results_anomaly_{}_{}_.csv'.format(selected_state_id, model_type))
            ds_res.to_csv(filename, index=False)

        print("Locate Anomaly")
        x_selected = x_test[y_test == selected_state_id]
        y_selected = y_test[y_test == selected_state_id]
        x_reconstructed = model.model.predict(x_selected)

        ds_res = []
        num_records = len(x_selected)
        for i in range(num_records):
            x_true = x_selected[i]
            x_pred = x_reconstructed[i]
            if transformer is not None:
                x_true = transformer.inverse_transform(x_true)
                x_pred = transformer.inverse_transform(x_pred)

            diff = np.mean(np.abs(x_true - x_pred), axis=0)
            res = {k: val for k, val in zip(features_list, diff)}
            res['threshold'] = model.threshold
            res['score'] = y_selected[i]
            ds_res.append(res)

        ds_res = pd.DataFrame(ds_res)

        if save_result:
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            filename = os.path.join(output_dir, 'results_locate_{}_{}_.csv'.format(selected_state_id, model_type))
            ds_res.to_csv(filename, index=False)


if __name__ == '__main__':
    main()
