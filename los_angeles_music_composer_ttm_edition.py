# -*- coding: utf-8 -*-
"""Los_Angeles_Music_Composer_TTM_Edition.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/asigalov61/Los-Angeles-Music-Composer/blob/main/Los_Angeles_Music_Composer_TTM_Edition.ipynb

# Los Angeles Music Composer TTM Edition (ver. 4.0)

***

Powered by tegridy-tools: https://github.com/asigalov61/tegridy-tools

***

WARNING: This complete implementation is a functioning model of the Artificial Intelligence. Please excercise great humility, care, and respect. https://www.nscai.gov/

***

#### Project Los Angeles

#### Tegridy Code 2023

***

# (GPU CHECK)
"""

#@title NVIDIA GPU check
!nvidia-smi

"""# (SETUP ENVIRONMENT)"""

#@title Install dependencies
!git clone --depth 1 https://github.com/asigalov61/Los-Angeles-Music-Composer
!pip install torch
!pip install einops
!pip install fuzzywuzzy[speedup]
!pip install torch-summary
!pip install tqdm
!pip install matplotlib
!apt install fluidsynth #Pip does not work for some reason. Only apt works
!pip install midi2audio

# Commented out IPython magic to ensure Python compatibility.
#@title Import modules

print('=' * 70)
print('Loading core Los Angeles Music Composer modules...')

import os
import pickle
import random
import secrets
import statistics
from time import time
import tqdm

print('=' * 70)
print('Loading main Los Angeles Music Composer modules...')
import torch

# %cd /content/Los-Angeles-Music-Composer

import TMIDIX
from lwa_transformer import *

# %cd /content/

from fuzzywuzzy import process

print('=' * 70)
print('Loading aux Los Angeles Music Composer modeules...')

import matplotlib.pyplot as plt

from torchsummary import summary
from sklearn import metrics

from midi2audio import FluidSynth
from IPython.display import Audio, display

print('=' * 70)
print('Done!')
print('Enjoy! :)')
print('=' * 70)

"""# (LOAD MODEL)"""

# Commented out IPython magic to ensure Python compatibility.
#@title Unzip Pre-Trained Los Angeles Music Composer Model
print('=' * 70)
# %cd /content/Los-Angeles-Music-Composer/Model

print('=' * 70)
print('Unzipping pre-trained Los Angeles Music Composer model...Please wait...')

!cat /content/Los-Angeles-Music-Composer/Model/Los_Angeles_Music_Composer_Trained_Model.zip* > /content/Los-Angeles-Music-Composer/Model/Los_Angeles_Music_Composer_Trained_Model.zip
print('=' * 70)

!unzip -j /content/Los-Angeles-Music-Composer/Model/Los_Angeles_Music_Composer_Trained_Model.zip
print('=' * 70)

print('Done! Enjoy! :)')
print('=' * 70)
# %cd /content/
print('=' * 70)

#@title Load Los Angeles Music Composer Model
full_path_to_model_checkpoint = "/content/Los-Angeles-Music-Composer/Model/Los_Angeles_Music_Composer_Model_88835_steps_0.643_loss.pth" #@param {type:"string"}

#@markdown Model precision option

model_precision = "bfloat16" # @param ["bfloat16", "float16", "float32"]

#@markdown bfloat16 == Third precision/triple speed (if supported, otherwise the model will default to float16)

#@markdown float16 == Half precision/double speed

#@markdown float32 == Full precision/normal speed

plot_tokens_embeddings = False # @param {type:"boolean"}

print('=' * 70)
print('Loading Los Angeles Music Composer Pre-Trained Model...')
print('Please wait...')
print('=' * 70)
print('Instantiating model...')

torch.backends.cuda.matmul.allow_tf32 = True # allow tf32 on matmul
torch.backends.cudnn.allow_tf32 = True # allow tf32 on cudnn
device_type = 'cuda'

if model_precision == 'bfloat16' and torch.cuda.is_bf16_supported():
  dtype = 'bfloat16'
else:
  dtype = 'float16'

if model_precision == 'float16':
  dtype = 'float16'

if model_precision == 'float32':
  dtype = 'float32'

ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]
ctx = torch.amp.autocast(device_type=device_type, dtype=ptdtype)

SEQ_LEN = 4096

# instantiate the model

model = LocalTransformer(
    num_tokens = 2831,
    dim = 1024,
    depth = 36,
    causal = True,
    local_attn_window_size = 512,
    max_seq_len = SEQ_LEN
)

model = torch.nn.DataParallel(model)

model.cuda()
print('=' * 70)

print('Loading model checkpoint...')

model.load_state_dict(torch.load(full_path_to_model_checkpoint))
print('=' * 70)

model.eval()

print('Done!')
print('=' * 70)

print('Model will use', dtype, 'precision...')
print('=' * 70)

# Model stats
print('Model summary...')
summary(model)

# Plot Token Embeddings

if plot_tokens_embeddings:
  tok_emb = model.module.token_emb.weight.detach().cpu().tolist()

  cos_sim = metrics.pairwise_distances(
    tok_emb, metric='cosine'
  )
  plt.figure(figsize=(7, 7))
  plt.imshow(cos_sim, cmap="inferno", interpolation="nearest")
  im_ratio = cos_sim.shape[0] / cos_sim.shape[1]
  plt.colorbar(fraction=0.046 * im_ratio, pad=0.04)
  plt.xlabel("Position")
  plt.ylabel("Position")
  plt.tight_layout()
  plt.plot()
  plt.savefig("/content/Los-Angeles-Music-Composer-Tokens-Embeddings-Plot.png", bbox_inches="tight")

"""# (LOAD AUX DATA)"""

# Commented out IPython magic to ensure Python compatibility.
#@title Unzip Los Angeles Music Composer Aux Data
print('=' * 70)
# %cd /content/Los-Angeles-Music-Composer/Aux-Data

print('=' * 70)
print('Unzipping Los Angeles Music Composer Aux Data...Please wait...')

!cat /content/Los-Angeles-Music-Composer/Aux-Data/Los_Angeles_Music_Composer_Aux_Data.zip* > /content/Los-Angeles-Music-Composer/Aux-Data/Los_Angeles_Music_Composer_Aux_Data.zip
print('=' * 70)

!unzip -j /content/Los-Angeles-Music-Composer/Aux-Data/Los_Angeles_Music_Composer_Aux_Data.zip
print('=' * 70)

print('Done! Enjoy! :)')
print('=' * 70)
# %cd /content/
print('=' * 70)

#@title Load Los Angeles Music Composer Aux Data

AUX_DATA = TMIDIX.Tegridy_Any_Pickle_File_Reader('/content/Los-Angeles-Music-Composer/Aux-Data/Los_Angeles_Music_Composer_Aux_Data')

print('Done!')

"""# (GENERATE)"""

#@title Standard/Simple Continuation

#@markdown Text-To-Music Settings

#@markdown NOTE: You can enter any desired title or artist, or both

enter_desired_song_title = "Family Guy" #@param {type:"string"}
enter_desired_artist = "TV Themes" #@param {type:"string"}

#@markdown Generation Settings

number_of_tokens_to_generate = 512 #@param {type:"slider", min:32, max:2048, step:32}
number_of_batches_to_generate = 4 #@param {type:"slider", min:1, max:16, step:1}
temperature = 0.9 #@param {type:"slider", min:0.1, max:1, step:0.1}
allow_model_to_stop_generation_if_needed = False #@param {type:"boolean"}
render_MIDI_to_audio = True # @param {type:"boolean"}

print('=' * 70)
print('Los Angeles Music Composer TTM Model Generator')
print('=' * 70)

print('Searching titles...Please wait...')
random.shuffle(AUX_DATA)

titles_index = []

for A in AUX_DATA:
  titles_index.append(A[0])

search_string = ''

if enter_desired_song_title != '' and enter_desired_artist != '':
  search_string = enter_desired_song_title + ' --- ' + enter_desired_artist

else:
  search_string = enter_desired_song_title + enter_desired_artist

search_match = process.extract(query=search_string, choices=titles_index, limit=1)
search_index = titles_index.index(search_match[0][0])

print('Done!')
print('=' * 70)
print('Selected title:', AUX_DATA[search_index][0])
print('=' * 70)

if allow_model_to_stop_generation_if_needed:
  min_stop_token = 2816
else:
  min_stop_token = 0

outy = AUX_DATA[search_index][1]

block_marker = sum([(y * 10) for y in outy if y < 128]) / 1000

inp = [outy] * number_of_batches_to_generate

inp = torch.LongTensor(inp).cuda()

with ctx:
  out = model.module.generate(inp,
                        number_of_tokens_to_generate,
                        temperature=temperature,
                        return_prime=True,
                        min_stop_token=min_stop_token,
                        verbose=True)

out0 = out.tolist()
print('=' * 70)
print('Done!')
print('=' * 70)
#======================================================================
print('Rendering results...')

for i in range(number_of_batches_to_generate):

  print('=' * 70)
  print('Batch #', i)
  print('=' * 70)

  out1 = out0[i]

  print('Sample INTs', out1[:12])
  print('=' * 70)

  if len(out) != 0:

      song = out1
      song_f = []
      tim = 0
      dur = 0
      vel = 0
      pitch = 0
      channel = 0

      son = []
      song1 = []

      for s in song:
        if s >= 128 and s < (12*128)+1152:
          son.append(s)
        else:
          if len(son) == 3:
            song1.append(son)
          son = []
          son.append(s)

      for ss in song1:

        tim += ss[0] * 10

        dur = ((ss[1]-128) // 8) * 20
        vel = (((ss[1]-128) % 8)+1) * 15

        channel = (ss[2]-1152) // 128
        pitch = (ss[2]-1152) % 128

        song_f.append(['note', tim, dur, channel, pitch, vel ])

      detailed_stats = TMIDIX.Tegridy_ms_SONG_to_MIDI_Converter(song_f,
                                                                output_signature = 'Los Angeles Music Composer',
                                                                output_file_name = '/content/Los-Angeles-Music-Composer-Music-Composition_'+str(i),
                                                                track_name='Project Los Angeles',
                                                                list_of_MIDI_patches=[0, 24, 32, 40, 42, 46, 56, 71, 73, 0, 53, 19, 0, 0, 0, 0]
                                                                )
      print('=' * 70)
      print('Displaying resulting composition...')
      print('=' * 70)

      fname = '/content/Los-Angeles-Music-Composer-Music-Composition_'+str(i)

      x = []
      y =[]
      c = []

      colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'pink', 'orange', 'purple', 'gray', 'white', 'gold', 'silver']

      for s in song_f:
        x.append(s[1] / 1000)
        y.append(s[4])
        c.append(colors[s[3]])

      if render_MIDI_to_audio:
        FluidSynth("/usr/share/sounds/sf2/FluidR3_GM.sf2", 16000).midi_to_audio(str(fname + '.mid'), str(fname + '.wav'))
        display(Audio(str(fname + '.wav'), rate=16000))

      plt.figure(figsize=(14,5))
      ax=plt.axes(title=fname)
      ax.set_facecolor('black')

      plt.scatter(x,y, c=c)

      ax.axvline(x=block_marker, c='w')

      plt.xlabel("Time")
      plt.ylabel("Pitch")
      plt.show()

"""# Congrats! You did it! :)"""