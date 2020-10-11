from pickle import dump, load
from time import time as tm
filename = "listenkey.bin"

def get_listenkey():
    data = load(open(filename, "wb"))
    return data

def set_listenkey(data):
    data['timestamp'] = int(round(tm() * 1000))
    data['createdAt'] = int(round(tm() * 1000))
    dump(data, open(filename, "wb"))

def update_listenkey_timestamp():
    data = get_listenkey()
    data['timestamp'] = int(round(tm() * 1000))
    dump(data, open(filename, "wb"))