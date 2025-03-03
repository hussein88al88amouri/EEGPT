import argparse
import datetime
from pyexpat import model
import numpy as np
import time
import torch
import torch.backends.cudnn as cudnn
import json
import os

from pathlib import Path
from collections import OrderedDict
from timm.data.mixup import Mixup
from timm.models import create_model
from timm.loss import LabelSmoothingCrossEntropy, SoftTargetCrossEntropy
from timm.utils import ModelEma
from optim_factory import create_optimizer, get_parameter_groups, LayerDecayValueAssigner

from engine_for_finetuning_EEGPT import train_one_epoch, evaluate
from utils import NativeScalerWithGradNormCount as NativeScaler
import utils as utils
from Modules.models.EEGPT_mcae_finetune_change_tuev import EEGPTClassifier

import run_class_finetuning_EEGPT_change_teuv as runfinetune
from run_class_finetuning_EEGPT_change_teuv import get_models, get_dataset

from attrdict import AttrDict


device = 'cpu'

args = AttrDict({'nb_classess': 8, 'use_mean_pooling': False, 'dataset':'TUSZ'})

# Prepare Data for Inference
print('Prepare Data for Inference\n')
dataset_train, dataset_test, dataset_val, ch_names, metrics = get_dataset(args)

# Prepare Pretrained Model for Inference
print('Prepare Pretrained Model for Inference\n')
finetune = '../checkpoint/eegpt_mcae_58chs_4s_large4E.ckpt'
print("Load ckpt from %s" % finetune)
model = get_models(args)
checkpoint = torch.load(finetune, map_location='cpu')
checkpoint_model = checkpoint['state_dict']
model_prefix = ''
utils.load_state_dict(model, checkpoint_model, prefix=model_prefix)
model.to(device)

# Evaluate
print('Evaluate')
balanced_accuracy = []
accuracy = []
for data_loader in data_loader_test:
    test_stats = evaluate(data_loader, model, device, header='Test:', ch_names=ch_names, metrics=metrics, is_binary=(args.nb_classes == 1))
    accuracy.append(test_stats['accuracy'])
    balanced_accuracy.append(test_stats['balanced_accuracy'])
print(f"Accuracy: {np.mean(accuracy)} {np.std(accuracy)}, balanced accuracy: {np.mean(balanced_accuracy)} {np.std(balanced_accuracy)}")

