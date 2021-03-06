
import os
from os.path import expanduser
from importlib import import_module
import numpy as np
import cv2
from . import backends
from tqdm import tqdm

class DataLoader():

    current = 0
    images = []
    masks = []

    def __init__(self, config=None, mode='train', augmentation=None):
        self.config = config
        self.root = expanduser(config['datapath'])
        self.mode = mode
        self.augmentation = augmentation
        assert(config)

        _image_dir = os.path.join(self.root, mode)
        _masks_dir = os.path.join(self.root, mode + "_masks")

        self.images = (os.path.join(_image_dir, f)
                       for f in os.listdir(_image_dir) if "mask" not in f)
        self.images = sorted(self.images)

        if mode != 'test':
            self.masks = (os.path.join(_masks_dir, f)
                          for f in os.listdir(_masks_dir))
            self.masks = sorted(self.masks)
            if config['ignore_unlabeled'] is True:
                i = 0
                for _ in tqdm(range(len(self.masks))):
                    mask = cv2.imread(self.masks[i], cv2.IMREAD_GRAYSCALE)
                    if np.sum(mask) == 0:
                        del self.images[i]
                        del self.masks[i]
                    else:
                        i += 1

        if mode != 'test':
            assert (len(self.images) == len(self.masks))

        self.filters = []
        filters = self.config.get('filters')
        if filters:
            print('___ loading filters ___')
            for f in filters:
                full_function = list(f.keys())[0]
                module_name, function_name = full_function.rsplit('.', 1)
                parameters = f[full_function]
                print(module_name, function_name, parameters)
                mod = import_module(module_name)
                met = getattr(mod, function_name)
                self.filters.append(
                    {'function': met, 'parameters': parameters})

    def filter(self, img):
        for f in self.filters:
            if type(f['parameters']) is list:
                img = f['function'](img, *f['parameters'])
            else:
                img = f['function'](img, **f['parameters'])
        return img

    def resize(self, img, mask=None, width=None, height=None):
        img = cv2.resize(
            img, (height or self.config['height'],width or self.config['width']))
        if mask is None:
            return img
        if self.config.get('mask_width'):
            width = self.config['mask_width']
        if self.config.get('mask_height'):
            height = self.config['mask_height']
        mask = cv2.resize(
            mask, (height or self.config['height'], width or self.config['width']), interpolation=cv2.INTER_NEAREST)
        return img, mask

    def __getitem__(self, index):

        if self.config['gray_img']:
            img = cv2.imread(self.images[index], cv2.IMREAD_GRAYSCALE)
        elif self.config['color_img']:
            img = cv2.imread(self.images[index], cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(self.images[index], cv2.IMREAD_UNCHANGED)

        img = self.filter(img)

        if self.mode == 'test':
            img = self.resize(img)
            return backends.backend().dataloader_format(img), self.images[index]

        if self.config['gray_mask']:
            mask = cv2.imread(self.masks[index], cv2.IMREAD_GRAYSCALE)
        elif self.config['color_mask']:
            mask = cv2.imread(self.masks[index], cv2.IMREAD_COLOR)
        else:
            mask = cv2.imread(self.masks[index], cv2.IMREAD_UNCHANGED)

        if self.augmentation:
            img, mask = self.augmentation.random_flip(img, mask)
            img, mask = self.augmentation.random_rotation(img, mask)
            img, mask = self.augmentation.random_shift(img, mask)
            img, mask = self.augmentation.random_zoom(img, mask)
            img, mask = self.augmentation.shape_augmentation(img, mask)
            img = self.augmentation.random_noise(img)
            img = self.augmentation.random_brightness(img)

            img = self.augmentation.img_augmentation(img)

        img, mask = self.resize(img, mask)

        return backends.backend().dataloader_format(img, mask)

    def __len__(self):
        return len(self.images)

    def generator(self, shuffle=False):
        indices = np.arange(len(self))
        if shuffle == True:
            np.random.shuffle(indices)
        index = 0
        while index < len(self):
            img, mask = self[indices[index]]
            yield img, mask
            index += 1

    def batch_generator(self, batch_size=1, shuffle=False):
        indices = np.arange(len(self))
        if shuffle == True:
            np.random.shuffle(indices)
        index = 0
        while index + batch_size <= len(self):
            img_batch = []
            mask_batch = []
            for i in range(batch_size):
                img, mask = self[indices[index + i]]
                img_batch.append(img)
                mask_batch.append(mask)
            yield img_batch, mask_batch
            index = index + batch_size

    def next(self):
        img, mask = self[self.current]
        self.current += 1
        if self.current >= len(self):
            self.current = 0
        return img, mask
