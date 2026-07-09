import torch
from torchvision.models import ResNet50_Weights, resnet50


class ResNetClassifier:
    def __init__(self) -> None:
        self.weights = ResNet50_Weights.IMAGENET1K_V2
        self.model = resnet50(weights=self.weights)
        self.model.eval()
        self.preprocess = self.weights.transforms()
        self.categories = self.weights.meta["categories"]

    @torch.inference_mode()
    def predict(self, image) -> list[tuple[str, float]]:
        batch = self.preprocess(image).unsqueeze(0)
        probs = self.model(batch).squeeze(0).softmax(0)
        top5 = probs.topk(5)
        return [
            (self.categories[idx], float(probs[idx])) for idx in top5.indices.tolist()
        ]
