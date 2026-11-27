"""Detector backbones. Every model outputs ONE logit: P(fake) = sigmoid(logit).

Why these picks (no model is "perfect"; these are the strongest practical choices for CPU-served ONNX):
  face     EfficientNet-B4 @380  - the standard strong face-forgery backbone (DFDC/FF++ winners used the EfficientNet family).
  scene    CLIP ViT-B/16 + linear head - CLIP features generalise to *unseen* image generators far better than
           CNNs trained on one generator (Ojha et al., "UnivFD", CVPR 2023). Fine-tune the last blocks gently.
  document ConvNeXt-Tiny @384    - modern CNN, keeps fine texture; documents need high resolution so tampered
           text edges survive. Trained on real scans + synthetic edits (training/make_doc_fakes.py).
"""
import torch
import torch.nn as nn
from torchvision import models

IMAGENET = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
CLIP_NORM = ([0.48145466, 0.4578275, 0.40821073], [0.26862954, 0.26130258, 0.27577711])

TASKS = {
    # task: (default arch, image size, description)
    "face":     ("efficientnet_b4", 380, "face deepfakes / face swaps (face crops)"),
    "scene":    ("clip_vit_b16",    224, "AI-generated or edited photos: installation shots, vehicles, scenes"),
    "document": ("convnext_tiny",   384, "tampered ID cards / invoices / scanned documents"),
}


def norm_for(arch: str):
    return CLIP_NORM if arch.startswith("clip") else IMAGENET


class ClipDetector(nn.Module):
    """CLIP vision tower + linear head. `backbone` params are the CLIP tower; `head` is the classifier."""

    def __init__(self, pretrained=True, name="openai/clip-vit-base-patch16"):
        super().__init__()
        from transformers import CLIPVisionConfig, CLIPVisionModel
        self.backbone = CLIPVisionModel.from_pretrained(name) if pretrained else CLIPVisionModel(
            CLIPVisionConfig(hidden_size=768, intermediate_size=3072, num_hidden_layers=12, num_attention_heads=12,
                             image_size=224, patch_size=16, projection_dim=512))  # real ViT-B/16 shape, random weights
        self.head = nn.Linear(self.backbone.config.hidden_size, 1)

    def forward(self, x):
        return self.head(self.backbone(pixel_values=x).pooler_output)


def build(arch: str, pretrained: bool = True) -> nn.Module:
    if arch == "efficientnet_b4":
        m = models.efficientnet_b4(weights="IMAGENET1K_V1" if pretrained else None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
    elif arch == "efficientnet_b0":
        m = models.efficientnet_b0(weights="IMAGENET1K_V1" if pretrained else None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
    elif arch == "convnext_tiny":
        m = models.convnext_tiny(weights="IMAGENET1K_V1" if pretrained else None)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, 1)
    elif arch == "resnet50":
        m = models.resnet50(weights="IMAGENET1K_V2" if pretrained else None)
        m.fc = nn.Linear(m.fc.in_features, 1)
    elif arch == "clip_vit_b16":
        m = ClipDetector(pretrained)
    else:
        raise ValueError(f"unknown arch {arch}")
    return m


def head_params(model: nn.Module):
    """The freshly initialised classifier layer (trained first while the backbone is frozen)."""
    if isinstance(model, ClipDetector):
        return list(model.head.parameters())
    for attr in ("classifier", "fc"):
        if hasattr(model, attr):
            layer = getattr(model, attr)
            last = [l for l in layer.modules() if isinstance(l, nn.Linear)][-1] if attr == "classifier" else layer
            return list(last.parameters())
    raise ValueError("no head found")
