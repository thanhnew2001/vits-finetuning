# -*- coding: utf-8 -*-
"""Vits inference.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/151qOrmuUHZ4cmpS5yU96EYl1SORUGtpz
"""

!wget -nc https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
!chmod +x Miniconda3-latest-Linux-x86_64.sh
!./Miniconda3-latest-Linux-x86_64.sh -b -f -p /usr/local
!conda install --channel defaults conda python=3.8 --yes
!conda update --channel defaults --all --yes

# Commented out IPython magic to ensure Python compatibility.
!git clone https://github.com/thanhnew2001/vits-finetuning.git
# %cd vits-finetuning

!pip install pip==21.3.1
!pip install -r requirements.txt
!pip install gradio

import sys
sys.path.append('vits-finetuning')

!pip install unicode

# Commented out IPython magic to ensure Python compatibility.
# %matplotlib inline
import matplotlib.pyplot as plt
import IPython.display as ipd

import os
import json
import math
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader

import commons
import utils
from data_utils import TextAudioLoader, TextAudioCollate, TextAudioSpeakerLoader, TextAudioSpeakerCollate
from models import SynthesizerTrn
from text.symbols import symbols
from text import text_to_sequence

from scipy.io.wavfile import write


def get_text(text, hps):
    text_norm = text_to_sequence(text, hps.data.text_cleaners)
    if hps.data.add_blank:
        text_norm = commons.intersperse(text_norm, 0)
    text_norm = torch.LongTensor(text_norm)
    return text_norm

from google.colab import drive
drive.mount('/content/drive')

"""## Single Speaker"""

hps = utils.get_hparams_from_file("/content/drive/MyDrive/vits-finetune/checkpoints/config.json")

net_g = SynthesizerTrn(
    len(symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    **hps.model).cuda()
_ = net_g.eval()

_ = utils.load_checkpoint("/content/drive/MyDrive/vits-finetune/checkpoints/G_epoch_10.pth", net_g, None)

stn_tst = get_text("こんにちは", hps)
with torch.no_grad():
    x_tst = stn_tst.cuda().unsqueeze(0)
    x_tst_lengths = torch.LongTensor([stn_tst.size(0)]).cuda()
    audio = net_g.infer(x_tst, x_tst_lengths, noise_scale=.667, noise_scale_w=0.8, length_scale=1)[0][0,0].data.cpu().float().numpy()
ipd.display(ipd.Audio(audio, rate=hps.data.sampling_rate, normalize=False))

"""## Multiple Speakers"""

hps = utils.get_hparams_from_file("./configs/XXX.json")

net_g = SynthesizerTrn(
    len(symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    n_speakers=hps.data.n_speakers,
    **hps.model).cuda()
_ = net_g.eval()

_ = utils.load_checkpoint("/path/to/model.pth", net_g, None)

stn_tst = get_text("こんにちは", hps)
with torch.no_grad():
    x_tst = stn_tst.cuda().unsqueeze(0)
    x_tst_lengths = torch.LongTensor([stn_tst.size(0)]).cuda()
    sid = torch.LongTensor([4]).cuda()
    audio = net_g.infer(x_tst, x_tst_lengths, sid=sid, noise_scale=.667, noise_scale_w=0.8, length_scale=1)[0][0,0].data.cpu().float().numpy()
ipd.display(ipd.Audio(audio, rate=hps.data.sampling_rate, normalize=False))

"""### Voice Conversion"""

dataset = TextAudioSpeakerLoader(hps.data.validation_files, hps.data)
collate_fn = TextAudioSpeakerCollate()
loader = DataLoader(dataset, num_workers=8, shuffle=False,
    batch_size=1, pin_memory=True,
    drop_last=True, collate_fn=collate_fn)
data_list = list(loader)

with torch.no_grad():
    x, x_lengths, spec, spec_lengths, y, y_lengths, sid_src = [x.cuda() for x in data_list[0]]
    sid_tgt1 = torch.LongTensor([1]).cuda()
    sid_tgt2 = torch.LongTensor([2]).cuda()
    sid_tgt3 = torch.LongTensor([4]).cuda()
    audio1 = net_g.voice_conversion(spec, spec_lengths, sid_src=sid_src, sid_tgt=sid_tgt1)[0][0,0].data.cpu().float().numpy()
    audio2 = net_g.voice_conversion(spec, spec_lengths, sid_src=sid_src, sid_tgt=sid_tgt2)[0][0,0].data.cpu().float().numpy()
    audio3 = net_g.voice_conversion(spec, spec_lengths, sid_src=sid_src, sid_tgt=sid_tgt3)[0][0,0].data.cpu().float().numpy()
print("Original SID: %d" % sid_src.item())
ipd.display(ipd.Audio(y[0].cpu().numpy(), rate=hps.data.sampling_rate, normalize=False))
print("Converted SID: %d" % sid_tgt1.item())
ipd.display(ipd.Audio(audio1, rate=hps.data.sampling_rate, normalize=False))
print("Converted SID: %d" % sid_tgt2.item())
ipd.display(ipd.Audio(audio2, rate=hps.data.sampling_rate, normalize=False))
print("Converted SID: %d" % sid_tgt3.item())
ipd.display(ipd.Audio(audio3, rate=hps.data.sampling_rate, normalize=False))