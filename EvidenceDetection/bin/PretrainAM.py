import os
import argparse
import glob

import numpy as np
import pandas as pd

import tensorflow as tf

from keras.preprocessing import sequence
from keras import backend as K
from keras.models import Sequential
from keras.layers import recurrent, Embedding, Dropout, Dense, Bidirectional
from keras.optimizers import SGD, Adam

from sklearn.metrics import classification_report, accuracy_score


from evidencedetection.vectorizer import EmbeddingVectorizer

def parse_arguments():
    parser = argparse.ArgumentParser("Trains a simple BiLSTM to detect sentential arguments across multiple topics.")

    parser.add_argument("--embeddings", type=str, help="The path to the embedding folder.")
    parser.add_argument("--data", type=str, help="The path to the folder containing the TSV files with the training data.")
    parser.add_argument("--seed", type=int, help="The random seed to use for training.")

    return parser.parse_args()


def read_data(data_path):
    data = pd.read_csv(data_path, sep="\t")
    return data


def create_model(embeddings, units, max_length, seed):

    tf.set_random_seed(seed)
    session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
    sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
    K.set_session(sess)

    model = Sequential()
    emb = Embedding(embeddings.shape[0],
                        embeddings.shape[1],
                        weights=[embeddings],
                        input_length=max_length,
                        mask_zero=True,
                        name="foo")  
    model.add(emb)
    model.add(Dropout(0.5, name="dropoutemb"))
    for i, unit in enumerate(units):
        model.add(Bidirectional(recurrent.LSTM(unit, return_sequences=False, name="lstm" + str(i))))
    # model.add(recurrent.LSTM(5, return_sequences=False, name="lstm", activation="relu"))
        model.add(Dropout(0.5, name="dropout" + str(i)))
    model.add(Dense(units=2, activation="softmax", name="dense"))
    
    optimizer = Adam(lr=0.01)
    model.compile(loss='binary_crossentropy', optimizer=optimizer, metrics=['accuracy'])
    print(model.summary())
    return model


if __name__=="__main__":

    args = parse_arguments()

    data = read_data(args.data)
    splits = data.groupby("set")
    train = splits.get_group("train")
    dev = splits.get_group("val")

    vectorizer = EmbeddingVectorizer(args.embeddings, label="NoArgument")

    train_sentences = train["sentence"].values
    lengths = map(lambda s: len(s.split(" ")), train_sentences)
    max_length = max(lengths)
    train_data, train_labels = vectorizer.prepare_data(train_sentences, train["annotation"].values)
    padded_train_data = vectorizer.sentences_to_padded_indices(train_sentences, max_length) 

    model = create_model(vectorizer.embeddings, [100], max_length, args.seed)

    label_array = np.array(train_labels)
    two_d_train_labels = np.zeros((label_array.shape[0], 2))
    two_d_train_labels[np.where(label_array==0), 0] = 1
    two_d_train_labels[np.where(label_array==1), 1] = 1
    
    # model.fit(padded_train_data[::100], two_d_train_labels[::100], epochs=1, batch_size=32)
    model.fit(padded_train_data, two_d_train_labels, epochs=5, batch_size=32)
    test_sentences = dev["sentence"]
    _, test_labels = vectorizer.prepare_data(test_sentences, dev["annotation"].values)
    padded_test_data = vectorizer.sentences_to_padded_indices(test_sentences, max_length) 
    raw_preds = model.predict(padded_test_data)
    preds = np.argmax(raw_preds, axis=1)

    print(preds.shape)
    print(classification_report(test_labels, preds, target_names=["no Argument", "Argument"]))  # we defined no argument to be label 0 in the embedding vectorizer

    print(accuracy_score(test_labels, preds))

    model_json = model.to_json()
    # serialize weights to HDF5
    model_folder = "../models/sentential-argument-mining/{0}/".format(args.seed)
    if not os.path.exists(model_folder):
        os.makedirs(model_folder)

    model.save("../models/sentential-argument-mining/{0}/sentential-argument-mining.h5".format(args.seed))
