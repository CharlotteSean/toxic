from __future__ import absolute_import

import os, sys, gc, re, datetime, unidecode, pickle, tqdm, math, random, itertools, multiprocessing
from joblib import Parallel, delayed
from IPython.lib.display import FileLink

import scipy
import numpy as np
import pandas as pd

from imblearn.under_sampling import RandomUnderSampler
from imblearn.over_sampling import RandomOverSampler

from keras import backend as K

import toxic
from toxic.callbacks import *
from toxic.losses import *
from toxic.metrics import *
from toxic.models import *
from toxic.text_analyzer import *
from toxic.utils.data_utils import *
from toxic.utils.evaluation_utils import *
from toxic.utils.post_processing_utils import *
from toxic.utils.sampling_utils import *
from toxic.tokenizers import nltk_tokenizers, spacy_tokenizers, deepmoji_tokenizer, glove_twitter_tokenizer

data_dir = 'data/'
models_dir = 'models/'
results_dir = 'results/'
stacking_dir = models_dir+'stacking/'

# Seed
seed = 7961730
print("Seed: {}".format(seed))

cfg = K.tf.ConfigProto()
cfg.gpu_options.allow_growth = True
K.set_session(K.tf.Session(config=cfg))
cpu_cores = multiprocessing.cpu_count()

def lr_change(i, lr): 
            if (i == 0): return 0.003
            if (i == 1): return 0.001
            return lr*0.95

def preprocess(text, lower=False):
    text = re.sub("[§@#\$%^&\*:;\"\-_\<\>\\/`]", "", 
                  re.sub("[\t\n]", " ", 
                         re.sub("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", " ", 
                                unidecode.unidecode(text))))
    if lower:
        text = text.lower()
    
    return text

def load_data(cleaned=False):
    if cleaned:
        df = pd.read_csv(data_dir + 'train_cleaned.csv', index_col='id', encoding='utf-8')
        test_df = pd.read_csv(data_dir + 'test_cleaned.csv', index_col='id', encoding='utf-8')
    else:
        df = pd.read_csv(data_dir + 'train.csv', index_col='id', encoding='utf-8')
        test_df = pd.read_csv(data_dir + 'test.csv', index_col='id', encoding='utf-8')

    inx2label = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
    label2inx = {col: i for i, col in enumerate(inx2label)}

    ids = np.array(df.index)
    test_ids = np.array(test_df.index)

    comments = list(df['comment_text'].fillna("_NAN_").values)
    test_comments = list(test_df['comment_text'].fillna("_NAN_").values)

    Y = df[inx2label].values
    return ids, comments, Y, test_ids, test_comments, inx2label, label2inx

def load_augmented_data():
    comments_fr = pickle.load(open('data/comments_fr.pkl', 'rb'))
    comments_de = pickle.load(open('data/comments_de.pkl', 'rb'))
    comments_es = pickle.load(open('data/comments_es.pkl', 'rb'))
    
    return comments_fr, comments_de, comments_es