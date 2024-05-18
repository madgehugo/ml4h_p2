from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score
from sklearn.preprocessing import label_binarize
from tensorflow.keras.layers import (Activation, Add, BatchNormalization,
                                     Conv1D, Dense, Dropout, Flatten, Input,
                                     MaxPooling1D)
from tensorflow.keras.models import Model
from tensorflow.keras.regularizers import l2
from tqdm import tqdm

from sklearn.decomposition import PCA



def load_train_test(dpath="../../data/mitbih/"):
    df_train = pd.read_csv(dpath / 'train.csv', header=None)
    df_test = pd.read_csv(dpath / 'test.csv', header=None)

    # Train split
    X_train = df_train.iloc[:, :-1]
    y_train = df_train.iloc[:, -1]

    # Test split
    X_test = df_test.iloc[:, :-1]
    y_test = df_test.iloc[:, -1]

    return X_train, y_train, X_test, y_test

def reshape_data(X):
    return X.values.reshape((X.shape[0], X.shape[1], 1))

def residual_block(x, filters, kernel_size=3, stride=1,
                   conv_shortcut=True, name=None):
    # Shortcut
    if conv_shortcut is True:
        shortcut = Conv1D(filters, 1, strides=stride, name=name+'_0_conv')(x)
        shortcut = BatchNormalization(name=name+'_0_bn')(shortcut)
    else:
        shortcut = x

    # Residual
    x = Conv1D(filters, kernel_size, padding='same', strides=stride,
               kernel_regularizer=l2(0.001), name=name+'_1_conv')(x)
    x = BatchNormalization(name=name+'_1_bn')(x)
    x = Activation('relu', name=name+'_1_relu')(x)

    x = Conv1D(filters, kernel_size, padding='same',
               kernel_regularizer=l2(0.001), name=name+'_2_conv')(x)
    x = BatchNormalization(name=name+'_2_bn')(x)

    # Add shortcut
    x = Add()([shortcut, x])
    x = Activation('relu', name=name+'_out')(x)
    return x

def build_resnet_encoder(input_shape, filters=32, kernel_size=5, strides=2):
    inputs = Input(shape=input_shape)

    # Initial conv block
    x = Conv1D(filters, kernel_size, strides=strides,
               padding='same', name='conv1')(inputs)
    x = BatchNormalization(name='bn_conv1')(x)
    x = Activation('relu')(x)

    # Residual blocks
    x = residual_block(x, filters, name='res_block1')
    x = MaxPooling1D(3, strides=strides, padding='same')(x)

    x = residual_block(x, 64, name='res_block2')
    x = MaxPooling1D(3, strides=strides, padding='same')(x)

    # Output representation
    representation = Flatten()(x)

    model = Model(inputs, representation)
    return model

def visualize_representations(encoder, dataset, labels, title):
    # Obtain representations
    batch_size = 64
    num_batches = int(np.ceil(len(dataset) / batch_size))
    representations = []

    for i in tqdm(range(num_batches), desc="Predicting"):
        batch_data = dataset[i * batch_size:(i + 1) * batch_size]
        batch_repr = encoder.predict(batch_data)
        representations.append(batch_repr)

    representations = np.vstack(representations)    
    # Dimensionality Reduction
    print("Performing PCA")
    pca = PCA(n_components=30)
    reduced_repr = pca.fit_transform(representations)

    print("Performing t-SNE")
    tsne = TSNE(n_components=2, random_state=42)
    reduced_repr = tsne.fit_transform(reduced_repr)
    
    # Plot
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=reduced_repr[:, 0], y=reduced_repr[:, 1], hue=labels, palette='viridis', legend='full')
    plt.title(title)
    plt.xlabel('Dimension 1')
    plt.ylabel('Dimension 2')
    plt.legend(title='Labels', loc='upper right')
    plt.savefig("learned_representations.png")

# Main
if __name__ == "__main__":
    print("--- ResNet Encoder with Visualization ---")
    # Load the data
    dpath = Path("../../data/mitbih/")
    X_train, y_train, X_test, y_test = load_train_test(dpath)

    # Reshape the data for CNNs
    X_train_reshaped = reshape_data(X_train)
    X_test_reshaped = reshape_data(X_test)
    input_shape = (X_train_reshaped.shape[1], 1)

    # Build ResNet encoder
    resnet_encoder = build_resnet_encoder(input_shape)
    resnet_encoder.summary()

    # Visualize learned representations for MIT-BIH dataset using the encoder
    visualize_representations(resnet_encoder, X_train_reshaped[-20000:], y_train[-20000:], 'Learned Representations - MIT-BIH')
    print(y_train[-10000:])
