import pandas as pd
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score


# TODO: Add headers to the data
def load_train_test(dpath="../../data/"):
    df_train = pd.read_csv(dpath / 'ptbdb_train.csv', header=None)
    df_test = pd.read_csv(dpath / 'ptbdb_test.csv', header=None)

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
                 epochs=50, batch_size=64, val_split=0.1):

    _ = model.fit(X_train, y_train,
                  epochs=epochs, batch_size=batch_size,
                  validation_split=val_split)

    predictions = model.predict(X_test)

    roc_score = roc_auc_score(y_test, predictions)
    print(f"ROC-AUC: {roc_score:.3f}")

    precision, recall, _ = precision_recall_curve(y_test, predictions)
    auprc_score = auc(recall, precision)
    print(f"AUPRC: {auprc_score:.3f} \n")
