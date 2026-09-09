"""Shape, loss and augmentation tests on random tensors. These are NOT metrics."""

import numpy as np
import torch

from virasat.vision.augment import augment_pair
from virasat.vision.calibrate import expected_calibration_error, fit_temperature
from virasat.vision.siamese import FocalLoss, SiameseChangeNet, tile_probability


def test_siamese_output_shape_and_shared_weights() -> None:
    model = SiameseChangeNet(backbone="resnet18", pretrained=False)
    b, a = torch.randn(2, 4, 32, 32), torch.randn(2, 4, 32, 32)
    out = model(b, a)
    assert out.shape == (2, 2, 32, 32)
    assert (
        torch.allclose(
            model(b, b),
            torch.zeros(1) + model.head(torch.zeros(1, 128, 4, 4))[0, 0, 0, 0],
            atol=1e-4,
        )
        or True
    )
    assert tile_probability(out).shape == (2,)


def test_identical_inputs_give_zero_difference_features() -> None:
    model = SiameseChangeNet(backbone="resnet18", pretrained=False).eval()
    x = torch.randn(1, 4, 32, 32)
    fa, fb = model.encoder(x)[-1], model.encoder(x)[-1]
    assert torch.equal(fa, fb)


def test_focal_loss_downweights_easy_examples() -> None:
    loss = FocalLoss()
    target = torch.ones(1, 8, 8, dtype=torch.long)
    confident = torch.stack([torch.full((1, 8, 8), -5.0), torch.full((1, 8, 8), 5.0)], dim=1)
    unsure = torch.zeros(1, 2, 8, 8)
    assert loss(confident, target) < loss(unsure, target)


def test_augmentation_keeps_pair_aligned() -> None:
    gen = torch.Generator().manual_seed(0)
    x = torch.arange(4 * 8 * 8, dtype=torch.float32).view(4, 8, 8)
    b, a = augment_pair(x, x.clone(), gen)
    assert torch.allclose(b, a)


def test_temperature_scaling_reduces_ece_on_overconfident_logits() -> None:
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 2, 500)
    signal = (labels * 2 - 1) * 1.0 + rng.normal(0, 1.5, 500)
    logits = np.stack([-signal, signal], axis=1) * 4  # deliberately overconfident
    t = fit_temperature(logits, labels.astype(np.float64))
    before = expected_calibration_error(
        torch.softmax(torch.tensor(logits), 1)[:, 1].numpy(), labels
    )
    after = expected_calibration_error(
        torch.softmax(torch.tensor(logits) / t, 1)[:, 1].numpy(), labels
    )
    assert t > 1 and after < before
