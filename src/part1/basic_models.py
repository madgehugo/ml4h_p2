import multiprocessing
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow_decision_forests as tfdf
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score
from sklearn.preprocessing import label_binarize
from tensorflow.keras.layers import Dense
from tensorflow.keras.metrics import AUC, Precision, Recall
from tensorflow.keras.models import Sequential
from tsfresh import extract_features
from tsfresh.feature_extraction import MinimalFCParameters

# from src.utils.utils import fit_evaluate, load_train_test, reshape_data
# TEMP as I had import issues with src utils


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

    predictions = model.predict(X_test)

    roc_score = roc_auc_score(y_test, predictions)
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


def log_reg_model(X_train):
    model = Sequential()
    model.add(
        Dense(1,
              activation='sigmoid',
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


def random_forest_model(X_train, y_train):
    # Convert data to TensorFlow dataset
    # train_ds = tf.data.Dataset.from_tensor_slices((X_train, y_train))

    # Define the Random Forest model with the same hyperparameters
    model = tfdf.keras.RandomForestModel(
        num_trees=100,
        task=tfdf.keras.Task.REGRESSION,
    )

    # Compile the model
    model.compile()

    # Train the model
    return model


if __name__ == "__main__":
    # Load the data
    dpath = Path("../../data/ptbdb/")
    X_train, y_train, X_test, y_test = load_train_test(dpath)

    print(X_train.shape)

    # Reshape the data for LSTM
    X_train_logreg = reshape_data(X_train)
    X_test_logreg = reshape_data(X_test)

    print(X_train_logreg.shape)

    X_train_RF = X_train.values
    X_test_RF = X_test.values

    print("Shapes before passing to random_forest_model:")
    print("X_train shape:", X_train.shape)
    print("X_test shape:", X_test.shape)
    print("y_train shape:", y_train.shape)
    print("y_test shape:", y_test.shape)

    # Logistic Regression
    print("--- Log. Reg. ---")
    logreg = log_reg_model(X_train_logreg)
    fit_evaluate(logreg, X_train_logreg, y_train, X_test_logreg, y_test)

    # Random Forest
    print("--- Random Forest ---")
    RF = random_forest_model(X_train_RF, y_train)
    fit_evaluate(RF, X_train_RF, y_train, X_test_RF, y_test, epochs=1)

    X_train_reshaped = np.reshape(X_train, (X_train.shape[0], -1))
    X_test_reshaped = np.reshape(X_test, (X_test.shape[0], -1))

    print("X_train_reshaped shape:", X_train_reshaped.shape)
    print("X_test_reshaped shape:", X_test_reshaped.shape)

    X_train_df = pd.DataFrame(X_train_reshaped)
    X_test_df = pd.DataFrame(X_test_reshaped)

    X_train_df['time'] = range(len(X_train_df))
    X_test_df['time'] = range(len(X_test_df))

    # --------------- TSFRESH --------------- #
    # Strategy 1: Specify subset of relevant features to reduce # of features
    fc_parameters = MinimalFCParameters()  # Use the minimal feature set
    fc_parameters.update({
        'mean': None,       # Include mean feature
        'median': None,     # Include median feature
        'standard_deviation': None,  # Include standard deviation feature
    })

    # Strategy 2: Parallelize feature extraction
    num_cores = multiprocessing.cpu_count()  # Get the number of CPU cores
    print("Number of CPU cores available:", num_cores)

    # Strategy 3: Optimize parameters
    chunksize = 1000  # Set chunksize parameter for more efficient processing

    # Extract features with specified parameters and parallelization
    X_train_features = extract_features(X_train_df,
                                        column_id='time',
                                        default_fc_parameters=fc_parameters,
                                        n_jobs=num_cores,
                                        chunksize=chunksize)

    # Extract features using tsfresh
    # X_train_features = extract_features(X_train_df, column_id='time')
    X_test_features = extract_features(X_test_df,
                                       column_id='time',
                                       default_fc_parameters=fc_parameters,
                                       n_jobs=num_cores,
                                       chunksize=chunksize)

    # Merge the extracted features with your original dataset
    X_train_combined = pd.concat([X_train, X_train_features], axis=1)
    X_test_combined = pd.concat([X_test, X_test_features], axis=1)

    X_train_logreg = reshape_data(X_train_combined)
    X_test_logreg = reshape_data(X_test_combined)

    X_train_RF = X_train_combined.values
    X_test_RF = X_test_combined.values

    print("Shapes before passing to random_forest_model:")
    print("X_train_RF shape:", X_train_RF.shape)
    print("X_test_RF shape:", X_test_RF.shape)
    print("y_train shape:", y_train.shape)
    print("y_test shape:", y_test.shape)

    # Logistic Regression
    print("--- Log. Reg. ---")
    logreg = log_reg_model(X_train_logreg)
    fit_evaluate(logreg, X_train_logreg, y_train, X_test_logreg, y_test)

    # Random Forest
    print("--- Random Forest ---")
    RF = random_forest_model(X_train_RF, y_train)
    fit_evaluate(RF, X_train_RF, y_train, X_test_RF, y_test, epochs=1)