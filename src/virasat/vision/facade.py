"""ViT facade classifier — second-stage refiner on street-level crops of flagged tiles."""

from __future__ import annotations

import timm
from torch import Tensor, nn

CLASSES = [
    "COMPLIANT",
    "UNAUTHORISED_FLOOR",
    "MODERN_MATERIAL",
    "SIGNAGE_VIOLATION",
    "COLOUR_VIOLATION",
]


class FacadeClassifier(nn.Module):
    def __init__(self, pretrained: bool = True) -> None:
        super().__init__()
        self.vit = timm.create_model(
            "vit_small_patch16_224", pretrained=pretrained, num_classes=len(CLASSES)
        )

    def forward(self, x: Tensor) -> Tensor:
        out: Tensor = self.vit(x)
        return out
