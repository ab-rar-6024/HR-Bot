"""Convert a trained .pth (from training/train.py) to ONNX for the Gate.

    python scripts/export_onnx.py face.pth scene.pth document.pth      # writes models/<task>.onnx (+ models/<task>.json)

Needs torch, torchvision, onnx, onnxruntime on the machine running it (not on the serving image).
Checks PyTorch vs ONNX output parity before finishing. INT8 quantization is optional (--int8) and
should be re-evaluated on a held-out set before use because it can shift scores.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training.models import build  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pth", nargs="+")
    ap.add_argument("--out", default="models")
    ap.add_argument("--int8", action="store_true")
    a = ap.parse_args()
    import onnxruntime as ort

    for f in a.pth:
        ck = torch.load(f, map_location="cpu", weights_only=True)  # downloaded file: no arbitrary pickle code
        task, size = ck["task"], ck["img_size"]
        net = build(ck["arch"], pretrained=False)
        net.load_state_dict(ck["state_dict"])
        net.eval()
        out = Path(a.out) / f"{task}.onnx"
        out.parent.mkdir(parents=True, exist_ok=True)
        x = torch.randn(2, 3, size, size)
        torch.onnx.export(net, x, str(out), input_names=["input"], output_names=["logit"],
                          dynamic_axes={"input": {0: "batch"}, "logit": {0: "batch"}}, opset_version=17, dynamo=False)
        with torch.no_grad():
            ref = net(x).numpy()
        got = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"]).run(None, {"input": x.numpy()})[0]
        assert np.allclose(ref, got, atol=1e-3), f"{task}: ONNX output diverges from PyTorch"
        if a.int8:
            from onnxruntime.quantization import QuantType, quantize_dynamic
            q = out.with_name(f"{task}.int8.onnx")
            quantize_dynamic(str(out), str(q), weight_type=QuantType.QInt8)
            print(f"  wrote {q} (re-evaluate before using)")
        meta = {"task": task, "arch": ck["arch"], "img_size": size, "threshold": ck.get("threshold", 0.5),
                "mean": ck["mean"], "std": ck["std"], "metrics": ck.get("metrics")}
        out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
        print(f"{task}: parity OK -> {out}  (val AUC {ck.get('metrics', {}).get('auc')})")


if __name__ == "__main__":
    main()
