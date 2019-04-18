'''ResNet in PyTorch.

For Pre-activation ResNet, see 'preact_resnet.py'.

Reference:
[1] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
    Deep Residual Learning for Image Recognition. arXiv:1512.03385
'''
import torch
import torch.nn as nn
import torch.nn.functional as F

from .butterfly_conv import ButterflyConv2d, ButterflyConv2dBBT, ButterflyConv2dBBTBBT


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1, is_structured=False, structure_type='B', ortho_param=False):
        super(BasicBlock, self).__init__()
        butterfly_cls = {'B': ButterflyConv2d, 'BBT': ButterflyConv2dBBT, 'BBTBBT': ButterflyConv2dBBTBBT}[structure_type]
        if is_structured:
            self.conv1 = butterfly_cls(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False, tied_weight=False, ortho_init=True, ortho_param=ortho_param)
        else:
            self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        if is_structured:
            self.conv2 = butterfly_cls(planes, planes, kernel_size=3, stride=1, padding=1, bias=False, tied_weight=False, ortho_init=True, ortho_param=ortho_param)
        else:
            self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion*planes:
            if is_structured:
                self.shortcut = nn.Sequential(
                    butterfly_cls(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=False, tied_weight=False, ortho_init=True, ortho_param=ortho_param),
                    nn.BatchNorm2d(self.expansion*planes)
                )
            else:
                self.shortcut = nn.Sequential(
                    nn.Conv2d(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=False),
                    nn.BatchNorm2d(self.expansion*planes)
                )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, in_planes, planes, stride=1):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, self.expansion*planes, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(self.expansion*planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion*planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion*planes)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10, num_structured_layers=0, structure_type='B', ortho_param=False):
        assert num_structured_layers <= 4
        assert structure_type in ['B', 'BBT', 'BBTBBT']
        super(ResNet, self).__init__()
        self.is_structured = [False] * (4 - num_structured_layers) + [True] * num_structured_layers
        self.in_planes = 64

        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1, is_structured=self.is_structured[0])
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2, is_structured=self.is_structured[1])
        # Only stacking butterflies in the 3rd layer for now
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2, is_structured=self.is_structured[2],
                                       structure_type=structure_type, ortho_param=ortho_param)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2, is_structured=self.is_structured[3])
        self.linear = nn.Linear(512*block.expansion, num_classes)

    def _make_layer(self, block, planes, num_blocks, stride, is_structured, structure_type='B', ortho_param=False):
        strides = [stride] + [1]*(num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride, is_structured,
                                structure_type=structure_type, ortho_param=ortho_param))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def ResNet18(num_structured_layers=0, structure_type='B', ortho_param=False):
    return ResNet(BasicBlock, [2,2,2,2], num_structured_layers=num_structured_layers,
                  structure_type=structure_type, ortho_param=ortho_param)

def ResNet34():
    return ResNet(BasicBlock, [3,4,6,3])

def ResNet50():
    return ResNet(Bottleneck, [3,4,6,3])

def ResNet101():
    return ResNet(Bottleneck, [3,4,23,3])

def ResNet152():
    return ResNet(Bottleneck, [3,8,36,3])


def test():
    net = ResNet18()
    y = net(torch.randn(1,3,32,32))
    print(y.size())

# test()

# class BasicButterflyConv2d(nn.Module):
#     expansion = 1

#     def __init__(self, in_planes, planes):
#         # stride=1
#         super().__init__()
#         self.conv1 = ButterflyConv2d(in_planes, planes, kernel_size=3, padding=1, bias=False)
#         self.bn1 = nn.BatchNorm2d(planes)
#         self.conv2 = ButterflyConv2d(planes, planes, kernel_size=3, padding=1, bias=False)
#         self.bn2 = nn.BatchNorm2d(planes)

#         self.shortcut = nn.Sequential()
#         if in_planes != self.expansion*planes:
#             self.shortcut = nn.Sequential(
#                 nn.Conv2d(in_planes, self.expansion*planes, kernel_size=1, bias=False),
#                 nn.BatchNorm2d(self.expansion*planes)
#             )

#     def forward(self, x):
#         out = F.relu(self.bn1(self.conv1(x)))
#         out = self.bn2(self.conv2(out))
#         out += self.shortcut(x)
#         out = F.relu(out)
#         return out

# class ButterflyNet(nn.Module):
#     def __init__(self, block, num_blocks, num_classes=10):
#         super().__init__()
#         self.in_planes = 64

#         self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
#         self.bn1 = nn.BatchNorm2d(64)
#         self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
#         self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
#         self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
#         self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
#         self.linear = nn.Linear(512*block.expansion, num_classes)

#     def _make_layer(self, block, planes, num_blocks, stride):
#         strides = [stride] + [1]*(num_blocks-1)
#         layers = []
#         for stride in strides:
#             if stride > 1:
#                 layers.append(block(self.in_planes, planes, stride))
#             else:
#                 layers.append(BasicButterflyConv2d(self.in_planes, planes))
#             self.in_planes = planes * block.expansion
#         return nn.Sequential(*layers)

#     def forward(self, x):
#         out = F.relu(self.bn1(self.conv1(x)))
#         out = self.layer1(out)
#         out = self.layer2(out)
#         out = self.layer3(out)
#         out = self.layer4(out)
#         out = F.avg_pool2d(out, 4)
#         out = out.view(out.size(0), -1)
#         out = self.linear(out)
#         return out


# def ButterflyNet18():
#     return ButterflyNet(BasicBlock, [2,2,2,2])

# x = torch.randn(100, 256, 8, 8, device='cuda')
# w = torch.randn(256, 256, 1, 1, device='cuda')
# res = F.conv2d(x, w, padding=0)
# x_reshape = x.view(100, 256, 8 * 8).transpose(1, 2).reshape(-1, 256)
# w_reshape = w.view(256, 256).t()
# res_mm = x_reshape @ w_reshape
# res_mm = res_mm.view(100, 64, 256).transpose(1, 2).view(100, 256, 8, 8)
# assert torch.allclose(res, res_mm)
