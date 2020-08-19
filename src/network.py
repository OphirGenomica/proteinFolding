import torch
import torch.nn as nn
import numpy as np
class ResNet(nn.Module):
    def __init__(self, nlayers):
        super(ResNet, self).__init__()
        nf_in = 526
        nf = 64
        nbins_theta = 24
        nbins_phi = 12
        nbins_d = 36
        nbins_omega = 24
        self.conv_init = nn.Conv2d(nf_in, nf, kernel_size=1)
        self.blocks = []
        dilations = [1,2,4,8,16]
        for i in range(nlayers):
            dilation = dilations[np.mod(i,len(dilations))]
            block = ResidualBlock(nf,dilation)
            self.blocks.append(block)
        self.activation = nn.ELU()
        self.conv_theta = nn.Conv2d(nf, nbins_theta, kernel_size=3)
        self.conv_phi = nn.Conv2d(nf, nbins_phi, kernel_size=3)
        self.conv_d = nn.Conv2d(nf, nbins_d, kernel_size=3)
        self.conv_omega = nn.Conv2d(nf, nbins_omega, kernel_size=3)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        x = self.conv_init(x)
        for block in self.blocks:
            x = block(x)
        x = self.activation(x)
        theta = self.softmax(self.self.conv_theta(x))
        phi = self.softmax(self.self.conv_phi(x))
        y = x + torch.transpose(x, 0, 1)
        d = self.softmax(self.self.conv_d(y))
        omega = self.softmax(self.self.conv_omega(y))
        return theta, phi, d, omega


class ResidualBlock(nn.Module):
    def __init__(self, nf,dilation):
        super().__init__()
        self.conv1 = nn.Conv2d(nf,nf, kernel_size=3,dilation=dilation)
        self.norm1 = nn.InstanceNorm2d(nf)
        self.dropout = nn.Dropout2d()
        self.conv2 = nn.Conv2d(nf, nf, kernel_size=3, dilation=dilation)
        self.norm2 = nn.InstanceNorm2d(nf)
        self.activation = nn.ELU()

    def forward(self, x):
        y = self.activation(x)
        y = self.conv1(y)
        y = self.norm1(y)
        y = self.activation(y)
        y = self.dropout(y)
        y = self.conv2(y)
        y = self.norm2(y)
        z = y + x
        return z