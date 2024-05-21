### 2.2. part 2 #######

from pathlib import Path
from secrets import randbelow

from tensorflow.keras.utils import to_categorical
from sklearn.metrics import average_precision_score, roc_auc_score

# from src.part1.cnn import build_resnet_cnn
# from src.utils.utils import fit_evaluate, load_train_test, reshape_data

from tensorflow.keras.layers import (Activation, Add, BatchNormalization,
                                     Conv1D, Dense, Dropout, Flatten, Input,
                                     MaxPooling1D)
from tensorflow.keras.metrics import AUC, Precision, Recall
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.regularizers import l2

from tensorflow.keras.layers import Input, Conv1D, BatchNormalization, Activation, MaxPooling1D, Flatten, Dense, Dropout, UpSampling1D, Reshape
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.layers import Input, Dense, Reshape, BatchNormalization, LeakyReLU
from tensorflow.keras.models import Model

import numpy as np
import pandas as pd
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score
from sklearn.preprocessing import label_binarize
import matplotlib.pyplot as plt
import keras
from keras import layers


def load_train_test(dpath="../../data/ptbdb/"):
    df_train = pd.read_csv(dpath / 'train.csv', header=None)
    df_test = pd.read_csv(dpath / 'test.csv', header=None)

    # Train split
    X_train = df_train.iloc[:, :-1]
    y_train = df_train.iloc[:, -1]

    # Test split
    X_test = df_test.iloc[:, :-1]
    y_test = df_test.iloc[:, -1]

    return X_train, y_train, X_test, y_test
    

# Reshape the data for LSTM
def reshape_data(X):
    return X.values.reshape((X.shape[0], X.shape[1], 1))


# Fit and evaluate models
def fit_evaluate(model, X_train, y_train, X_test, y_test,
                 epochs=50, batch_size=64, val_split=0.1,
                 num_classes=1):

    _ = model.fit(X_train, y_train,
                  epochs=epochs, batch_size=batch_size,
                  validation_split=val_split)

    predictions = np.array(model.predict(X_test))

    roc_score = roc_auc_score(y_test, predictions, multi_class='ovo')
    print(f"ROC-AUC: {roc_score:.3f}")

    if num_classes == 1:
        precision, recall, _ = precision_recall_curve(y_test, predictions)
        auprc_score = auc(recall, precision)
        print(f"AUPRC: {auprc_score:.3f} \n")

    else:
        # One vs. Rest (OvR) AUPRC
        y_test_binarized = label_binarize(
            y_test, classes=np.arange(num_classes)
            )

        # Calculate AUPRC for each class
        auprc_scores = []
        for i in range(num_classes):
            precision, recall, _ = precision_recall_curve(
                y_test_binarized[:, i],
                predictions[:, i]
                )
            auprc_score = auc(recall, precision)
            auprc_scores.append(auprc_score)

        # Calculate the average AUPRC across all classes
        average_auprc = np.mean(auprc_scores)

        print("Average AUPRC: {:.3f}".format(average_auprc))


def residual_block(x, filters, kernel_size=3, stride=1, conv_shortcut=True, name=None):
    if conv_shortcut:
        shortcut = Conv1D(filters, 1, strides=stride, name=name+'_0_conv')(x)
        shortcut = BatchNormalization(name=name+'_0_bn')(shortcut)
    else:
        shortcut = x

    x = Conv1D(filters, kernel_size, padding='same', strides=stride, kernel_regularizer=l2(0.001), name=name+'_1_conv')(x)
    x = BatchNormalization(name=name+'_1_bn')(x)
    x = Activation('relu', name=name+'_1_relu')(x)

    x = Conv1D(filters, kernel_size, padding='same', kernel_regularizer=l2(0.001), name=name+'_2_conv')(x)
    x = BatchNormalization(name=name+'_2_bn')(x)

    x = Add()([shortcut, x])
    x = Activation('relu', name=name+'_out')(x)
    return x


def build_resnet_encoder(input_shape, num_classes, filters=32, kernel_size=5, strides=2, out_activation='sigmoid'):
    inputs = Input(shape=input_shape)
    x = Conv1D(filters, kernel_size, strides=strides, padding='same', name='conv1')(inputs)
    x = BatchNormalization(name='bn_conv1')(x)
    x = Activation('relu')(x)
   
    x = residual_block(x, filters, name='res_block1')
    x = MaxPooling1D(3, strides=strides, padding='same')(x)

    x = residual_block(x, 64, name='res_block2')
    x = MaxPooling1D(3, strides=strides, padding='same')(x)

    x = Flatten()(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(0.5)(x)
   
    encoder = Model(inputs, x, name='encoder')

    return encoder


def build_decoder(num_classes,latent_dim, output_shape):

    encoded_input = Input(shape=(latent_dim,))
    x = Dense(64, activation='relu')(encoded_input)
    x = Dropout(0.5)(x)  # Add dropout layer with a dropout rate of 0.5
    x = Dense(output_shape[0] * output_shape[1], activation='relu')(x)
    x = Reshape(output_shape)(x)

    decoder = Model(encoded_input, x, name='decoder')
    return decoder


def log_reg_model(X_train):
    model = Sequential()
    model.add(
        Dense(
            1, 
            activation='sigmoid',  # Sigmoid activation for logistic regression
            input_shape=(X_train.shape[1],)  # Input shape is 1D
            )) 
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=[
            AUC(name='auc'),
            Precision(name='precision'),
            Recall(name='recall')
        ])
    return model


if __name__ == "__main__":
    print("--- Representation Learning Q2.2 ---")
    # Load the data
    dpath = Path("../../data/mitbih/")
    X_train, y_train, X_test, y_test = load_train_test(dpath)

    # Reshape the data for CNNs
    X_train_reshaped = reshape_data(X_train)
    X_test_reshaped = reshape_data(X_test)
    input_dim = X_train_reshaped.shape[1]
    input_shape = (X_train_reshaped.shape[1], 1)
    # input_shape = (X_train_reshaped.shape[1], 1)
    latent_dim = 64
    n_classes = 5

    encoder = build_resnet_encoder(input_shape, filters=32, kernel_size=5, strides=2, out_activation='sigmoid', num_classes=64)
    decoder = build_decoder(num_classes = n_classes, latent_dim = latent_dim, output_shape = input_shape)

    latent_dim=64
    autoencoder_input = Input(shape=input_shape)
    encoded_output = encoder(autoencoder_input)
    decoded_output = decoder(encoded_output)

    autoencoder = Model(autoencoder_input, decoded_output, name='autoencoder')
    autoencoder.compile(optimizer='adam', loss='binary_crossentropy')

    autoencoder.fit(X_train_reshaped, X_train_reshaped,
                    epochs=20,
                    batch_size=256,
                    shuffle=True)
    
    #encoder representations
    encoded = encoder.predict(X_train_reshaped)
    encoded = encoded.reshape((encoded.shape[0], encoded.shape[1], 1))
    test_encoded = encoder.predict(X_test_reshaped)
    test_encoded = test_encoded.reshape((test_encoded.shape[0], test_encoded.shape[1], 1))
    print(encoded)
    logreg = log_reg_model(encoded)
    
    fit_evaluate(logreg, encoded, y_train, test_encoded, y_test)

  