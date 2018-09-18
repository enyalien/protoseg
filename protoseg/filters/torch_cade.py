import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.multiprocessing as multiprocessing

cade = None


def torch_cade(img, num_angles=8, distance=5, epochs=2, background_min=0, background_max=100, learn_rate=1, reinit=False):
    global cade
    if cade is None:
        cade = CADE(img, num_angles=num_angles, distance=distance,
                    epochs=epochs, learn_rate=learn_rate, reinit=reinit)
    return cade(img)


class Model(nn.Module):
    def __init__(self, cols, rows):
        super(Model, self).__init__()
        self.cols = cols
        self.rows = rows
        self.layer1 = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=5, stride=1, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer2 = nn.Sequential(
            nn.Conv2d(16, 32, kernel_size=5, stride=1, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer3 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer4 = nn.Conv2d(64, 32, kernel_size=5, stride=1, padding=2)
        self.layer5 = nn.Conv2d(16, 1, kernel_size=5, stride=1, padding=3)

    def forward(self, x):
        out = self.layer1(x)
        #out = self.layer2(out)
        #out = self.layer3(out)
        #out = nn.functional.interpolate(out, scale_factor=2, mode='bilinear', align_corners=True)
        #out = nn.functional.interpolate(out, scale_factor=2, mode='bilinear', align_corners=True)
        out = nn.functional.interpolate(
            out, scale_factor=2, mode='bilinear', align_corners=True)
        #out = self.layer4(out)
        out = self.layer5(out)
        return out

    def weights_init(self, m):
        if isinstance(m, nn.Conv2d) or isinstance(m, nn.BatchNorm2d):
            torch.nn.init.uniform_(m.weight.data)
            torch.nn.init.uniform_(m.bias.data)


class CADE():
    torch.multiprocessing.set_start_method('forkserver', force=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def __init__(self, img, num_angles=8, distance=5, epochs=2, background_min=0, background_max=1, learn_rate=1, reinit=False):
        self.img = img
        if len(img.shape) == 3:
            self.img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        self.rows = img.shape[0]
        self.cols = img.shape[1]
        self.num_angles = num_angles
        self.distance = distance
        self.epochs = epochs
        self.background_min = background_min
        self.background_max = background_max
        self.reinit = reinit
        self.angles = np.linspace(
            0, (360.0 - 360.0 / self.num_angles), self.num_angles)
        self.model = Model(self.cols, self.rows)
        self.model = self.model.to(self.device)
        self.criterion = nn.BCEWithLogitsLoss()
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=learn_rate)

    def rotationFilter(self, angle, distance):
        rows = 2*distance+1
        cols = 2*distance+1
        filt = np.zeros((rows, cols))
        filt[2*distance] = 1
        M = cv2.getRotationMatrix2D((cols, rows), angle, 1)
        return cv2.warpAffine(filt, M, (cols, rows))

    def neighbourhood(self, img, angle, distance):
        return cv2.filter2D(img, -1, kernel=self.rotationFilter(angle, distance))

    def train_cade(self, imgs):
        x = np.array(imgs)
        y = np.repeat(np.expand_dims(
            np.ones(imgs[0].shape), axis=0), len(x), axis=0)
        y_fake = np.repeat(np.expand_dims(
            np.zeros(imgs[0].shape), axis=0), len(x), axis=0)
        x_fake = [np.random.uniform(
            self.background_min, self.background_max, imgs[0].shape) for fake in range(0, len(x))]
        x_batch = self.batchify(x)
        y_batch = self.batchify(y)
        x_fake_batch = self.batchify(x_fake)
        y_fake_batch = self.batchify(y_fake)

        for _ in range(self.epochs):
            self.train_img(x_batch, y_batch)
            self.train_img(x_fake_batch, y_fake_batch)

    def train_img(self, img_batch, label_batch):
        img = torch.from_numpy(img_batch).float().to(self.device)
        label = torch.from_numpy(label_batch).float().to(self.device)
        # Forward pass
        outputs = self.model(img)
        loss = self.criterion(outputs, label)
        # Backward and optimize
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def batchify(self, imgs):
        img_batch = np.array(imgs)
        img_batch = np.expand_dims(img_batch, axis=3)
        img_batch = np.transpose(img_batch, axes=[0, 3, 1, 2])
        return img_batch

    def __call__(self, img=None):
        if img is None:
            img = self.img
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        if self.reinit is True:
            self.model.apply(self.model.weights_init)
        imgs = []
        for angle in self.angles:
            neighbourhood_ = self.neighbourhood(img, angle, self.distance)
            imgs.append(neighbourhood_)

        self.train_cade(imgs)
        self.model.eval()
        x_batch = self.batchify(np.array([img]))
        x_batch = torch.from_numpy(x_batch).float().to(self.device)
        pred = self.model(x_batch)
        pred = pred.data.max(1)[0].cpu().detach().numpy()
        pred = np.squeeze(pred)
        pred = pred / (0.0001+pred.max())
        pred = pred * 255
        return pred.astype(np.uint8)
