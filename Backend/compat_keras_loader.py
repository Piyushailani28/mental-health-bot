import sys
import types
import keras.preprocessing.text
import keras.preprocessing.sequence

# Create dummy keras module to match old pickle path
sys.modules['tensorflow.keras.preprocessing.text'] = keras.preprocessing.text
sys.modules['tensorflow.keras.preprocessing.sequence'] = keras.preprocessing.sequence

import pickle

def load_tokenizer(path):
    with open(path, 'rb') as f:
        tokenizer = pickle.load(f)
    return tokenizer