"""Siamese change detector: shared ImageNet backbone, |f(a) - f(b)| head, focal loss."""

from __future__ import annotations

import timm
import torch
from torch import Tensor, nn


class SiameseChangeNet(nn.Module):
    def __init__(
        self, backbone: str = "resnet50", in_chans: int = 4, pretrained: bool = True
    ) -> None:
        super().__init__()
        self.encoder = timm.create_model(
            backbone, pretrained=pretrained, in_chans=in_chans, features_only=True, out_indices=(2,)
        )
        ch = self.encoder.feature_info.channels()[-1]
        self.head = nn.Sequential(
            nn.Conv2d(ch, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 2, 1),
        )

    def forward(self, before: Tensor, after: Tensor) -> Tensor:
        fa = self.encoder(before)[-1]
        fb = self.encoder(after)[-1]  # shared weights: same module, both branches
        logits = self.head(torch.abs(fa - fb))
        out: Tensor = nn.functional.interpolate(
            logits, size=before.shape[-2:], mode="bilinear", align_corners=False
        )
        return out


class FocalLoss(nn.Module):
    """Change is rare; plain cross-entropy predicts 'no change' everywhere."""

    def __init__(self, alpha: float = 0.25, gamma: float = 2.0) -> None:
        super().__init__()
        self.alpha, self.gamma = alpha, gamma

    def forward(self, logits: Tensor, target: Tensor) -> Tensor:
        log_p = nn.functional.log_softmax(logits, dim=1)
        log_pt = log_p.gather(1, target.unsqueeze(1)).squeeze(1)
        pt = log_pt.exp()
        alpha_t = torch.where(target == 1, self.alpha, 1 - self.alpha)
        loss: Tensor = (-alpha_t * (1 - pt) ** self.gamma * log_pt).mean()
        return loss


def tile_probability(logits: Tensor) -> Tensor:
    """Per-tile change probability = mean change-class probability over the mask."""
    prob: Tensor = torch.softmax(logits, dim=1)[:, 1].mean(dim=(1, 2))
    return prob
