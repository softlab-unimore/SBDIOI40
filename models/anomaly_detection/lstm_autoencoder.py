"""
The implementation of LSTM AutoEncoder models for anomaly detection.
"""
import numpy as np
# import pandas as pd
from tensorflow import keras
from tensorflow.keras import layers


# import matplotlib.pyplot as plt


class LSTMAutoEncoder(object):

    def __init__(self, with_lazy=True, learning_rate=0.01):
        """ LSTM AutoEncoder models for anomaly detection """
        self.sequence_length = None
        self.num_features = None

        self.learning_rate = learning_rate
        self.loss = 'mse'

        self.history = None
        self.with_lazy = with_lazy
        self.threshold = 0

    def _set_input(self, X):
        assert len(X.shape) == 3, 'Invalid input shape'
        self.sequence_length = X.shape[1]
        self.num_features = X.shape[2]

    def _define_model(self, ):
        # model.add())
        # model.add(RepeatVector(n_in))
        # model.add(LSTM(100, activation='relu', return_sequences=True))
        # model.add(TimeDistributed(Dense(1)))

        model = keras.Sequential(
            [
                layers.Input(shape=(self.sequence_length, self.num_features)),
                layers.LSTM(100, activation='relu', return_sequences=True),
                layers.LSTM(64, activation='relu', return_sequences=False),
                layers.RepeatVector(self.sequence_length),
                layers.LSTM(64, activation='relu', return_sequences=True),
                layers.LSTM(100, activation='relu', return_sequences=True),
                layers.TimeDistributed(layers.Dense(self.num_features))
            ]
        )
        model.compile(optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate), loss=self.loss)
        # model.summary()

        self.model = model

    def _compute_reconstruction_error(self, x, x_pred):
        x = x.reshape((len(x), -1))
        x_pred = x_pred.reshape((len(x_pred), -1))
        mae_loss = np.mean(np.abs(x_pred - x), axis=1)
        return mae_loss

    def _set_reconstruction_error(self, x):
        # Get train MAE loss.
        x_pred = self.model.predict(x)

        train_mae_loss = self._compute_reconstruction_error(x, x_pred)

        # plt.hist(train_mae_loss, bins=50)
        # plt.xlabel("Train MAE loss")
        # plt.ylabel("No of samples")
        # plt.show()

        # Get reconstruction loss threshold.
        threshold = np.max(train_mae_loss)
        print("Reconstruction error threshold: ", threshold)
        print("Min error: ", np.min(train_mae_loss))
        print("Max error: ", np.max(train_mae_loss))
        print("Average error: ", np.mean(train_mae_loss))
        print("Std error: ", np.std(train_mae_loss))

        if self.with_lazy:
            # threshold = threshold + np.std(train_mae_loss)
            iqr = np.quantile(train_mae_loss, 0.75) - np.quantile(train_mae_loss, 0.25)
            threshold = threshold + 10 * iqr
            print("Use lazy reconstruction error threshold: ", threshold)

        self.threshold = np.max(threshold, self.threshold)

    def fit(self, x):
        print('LSTM AutoEncoder Fit')
        self._set_input(x)
        self._define_model()

        history = self.model.fit(
            x=x, y=x,
            epochs=100,
            batch_size=128,
            validation_split=0.1,
            verbose=0,
            callbacks=[
                keras.callbacks.EarlyStopping(monitor="val_loss", patience=20, mode="min")
            ],
        )
        self.history = history

        # plt.plot(history.history["loss"], label="Training Loss")
        # plt.plot(history.history["val_loss"], label="Validation Loss")
        # plt.legend()
        # plt.show()

        self._set_reconstruction_error(x)

    def tune(self, new_x):
        self.model.fit(
            x=new_x, y=new_x,
            epochs=50,
            batch_size=128,
            validation_split=0.1,
            callbacks=[
                keras.callbacks.EarlyStopping(monitor="val_loss", patience=10, mode="min")
            ],
        )

        self._set_reconstruction_error(new_x)

    def predict(self, x):
        print('LSTM AutoEncoder Predict')
        x_pred = self.model.predict(x)

        test_mae_loss = self._compute_reconstruction_error(x, x_pred)

        # Detect all the samples which are anomalies.
        anomalies = test_mae_loss > self.threshold
        print("Number of anomaly samples: ", np.sum(anomalies))
        print("Mean Error: ", np.mean(test_mae_loss))
        print("Max Error: ", np.max(test_mae_loss))

        # print("Indices of anomaly samples: ", np.where(anomalies))

        return anomalies

    def decision_score(self, x):
        print('LSTM AutoEncoder Decision Score')
        x_pred = self.model.predict(x)

        test_mae_loss = self._compute_reconstruction_error(x, x_pred)

        # Detect all the samples which are anomalies.
        scores = test_mae_loss - self.threshold
        print("Number of anomaly samples: ", np.sum(scores > 0))

        print("Mean reconstruction error: {:.05f}".format(np.mean(test_mae_loss)))
        print("Mean distance from threshold: {:.05f}".format(np.mean(scores)))

        return scores
