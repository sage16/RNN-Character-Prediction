import streamlit as st
from PIL import Image
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
from torch import optim as  optim


# One_hot_encode
def one_hot_encode(arr, n_labels):
    # initialize the encoded array
    one_hot = np.zeros((np.multiply(*arr.shape), n_labels), dtype=np.float32)

    # fill the appropriate elements with ones
    one_hot[np.arange(one_hot.shape[0]), arr.flatten()] = 1.

    # finally reshape it to get back the original array
    one_hot = one_hot.reshape((*arr.shape, n_labels))

    return one_hot


# Model Architecture
class CharRNN(nn.Module):
    def __init__(self, tokens, n_hidden=256, n_layers=2,
                 drop_prob=0.5, lr=0.001):
        super().__init__()
        self.drop_prob = drop_prob
        self.n_layers = n_layers
        self.n_hidden = n_hidden
        self.lr = lr

        # creating character dictionaries
        self.chars = tokens
        self.int2char = dict(enumerate(self.chars))
        self.char2int = {ch: ii for ii, ch in self.int2char.items()}

        # define the LSTM
        self.lstm = nn.LSTM(len(self.chars), n_hidden, n_layers,
                            dropout=drop_prob, batch_first=True)

        # define a dropout layer
        self.dropout = nn.Dropout(drop_prob)

        # define the final, fully-connected output layer
        self.fc = nn.Linear(n_hidden, len(self.chars))

    def forward(self, x, hidden):
        ''' Forward pass throuh the network.
        These inputs are x, and the hidden/cell state 'hidden'. '''

        # get the outputs and the new hidden state from the lstm
        r_output, hidden = self.lstm(x, hidden)

        # pass through a dropout layer
        out = self.dropout(r_output)

        # Stack up LSTM outputs using view
        out = out.contiguous().view(-1, self.n_hidden)

        # put x through the fully-connected layer
        out = self.fc(out)

        # return the final output and the hidden state
        return out, hidden

    def init_hidden(self, batch_size):
        '''Initializes hidden stae'''
        # create two new tensors with sizes n_layers x batch_size x n_hidden,
        # initialized to zero, for hidden state and cell state of LSTM
        weight = next(self.parameters()).data

        hidden = (weight.new(self.n_layers, batch_size, self.n_hidden).zero_(),
                  weight.new(self.n_layers, batch_size, self.n_hidden).zero_())

        return hidden


# Character Prediction Function
def predict(net, char, h=None, top_k=None):
    ''' Given a character, predict the next character.
              Returns the predicted character and the hidden state.
          '''

    # tensor inputs
    x = np.array([[net.char2int[char]]])
    x = one_hot_encode(x, len(net.chars))
    inputs = torch.from_numpy(x)

    # detach hidden state from history
    h = tuple([each.data for each in h])
    # get the output of the model
    out, h = net(inputs, h)

    # get the character probabilities
    p = F.softmax(out, dim=1).data

    # get top characters
    if top_k is None:
        top_ch = np.arange(len(net.chars))
    else:
        p, top_ch = p.topk(top_k)
        top_ch = top_ch.numpy().squeeze()

        # select the likely next character with some element of randomness
    p = p.numpy().squeeze()
    char = np.random.choice(top_ch, p=p / p.sum())

    # return the encoded value of the predicted char and the hidden state
    return net.int2char[char], h


# prime = st.text_input('Enter Your Start Word', 'Type Here')

# Join Characters function
def sample(net, size, prime='The', top_k=None):
    net.eval()  # eval mode

    # First off, run through the prime characters
    chars = [ch for ch in prime]
    h = net.init_hidden(1)
    for ch in prime:
        char, h = predict(net, ch, h, top_k=top_k)

    chars.append(char)

    # Now pass in the previous character and get a new one
    for ii in range(size):
        char, h = predict(net, chars[-1], h, top_k=top_k)
        chars.append(char)

    return ''.join(chars)


# Load Model
with open('rnn_15_epoch.pth', 'rb') as f:
    checkpoint = torch.load(f)

loaded = CharRNN(checkpoint['tokens'], n_hidden=checkpoint['n_hidden'], n_layers=checkpoint['n_layers'])
loaded.load_state_dict(checkpoint['state_dict'])

# Streamlit WebApp Creation

st.title('Character Prediction App')
st.write('This webapp uses artificial intelligence to generate characters to form English words.The English words are seen when the artificial intelligence is given the total number characters you want produced and a starting word')
image = Image.open('writing.jpg')
st.image(image, use_column_width=True)

char_number = st.slider('Select your character length', 1, 10000)

start_word = st.text_input('Enter Your Start Word', 'Type Here')
output = sample(loaded, char_number, start_word, top_k=5)
button = st.button('Submit')
if button:
    output

st.write()
