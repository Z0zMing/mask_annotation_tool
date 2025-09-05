import os
import time
import numpy as np
import torch
from PIL import Image
from segment_anything_hq import SamPredictor
from segment_anything_hq.build_sam import sam_model_registry
from .sam_refiner import sam_refiner


class Config:
    def __init__(self):
        self.hq_model_type = "vit_l"
        self.checkpoint_metal_hq = "checkpoints/Metal_HQ.pth"
        self.sam_ckpt = "models/Pretrained_model/sam_vit_l_01ec64.pth"
        self.multimask_output = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.use_fp16 = False


class Inference:
    def __init__(self):
        self.config = Config()
        self._load_metal_model()

    def _load_metal_model(self):
        print(f"[Inference] HQ类型: {self.config.hq_model_type}")
        print(f"[Inference] HQ权重路径: {self.config.checkpoint_metal_hq}")
        self.model_hq = sam_model_registry[self.config.hq_model_type](checkpoint=None)
        if os.path.exists(self.config.checkpoint_metal_hq):
            state = torch.load(self.config.checkpoint_metal_hq, map_location=self.config.device, weights_only=True)
            try:
                self.model_hq.load_state_dict(state)
                print("[Inference] 已加载HQ权重")
            except Exception:
                print("[Inference] 加载HQ权重失败，但将继续使用随机初始化模型")
        else:
            print("[Inference] 未找到HQ权重文件，将使用随机初始化模型")
        self.model_hq = self.model_hq.to(self.config.device)
        self.model_hq.eval()
        self.use_fp16 = False
        if self.config.use_fp16:
            print("[Inference] 已强制禁用FP16以避免dtype不匹配")
        print(f"[Inference] 模型设备: {self.config.device}")
        return self.model_hq

    def run_prompt_inference(self, image, box, multimask_output=None, hq_token_only=False):
        """拉框提示推理（仅金属）"""
        if multimask_output is None:
            multimask_output = self.config.multimask_output
        t0 = time.time()
        pil_img = Image.open(image).convert("RGB")
        np_img = np.array(pil_img)
        print(f"[Inference] 图像尺寸: {np_img.shape[:2]}  框: {box}")
        predictor = SamPredictor(self.model_hq)
        predictor.set_image(np_img)
        xyxy = np.array(box, dtype=np.float32)
        masks, scores, logits = predictor.predict(
            point_coords=None,
            point_labels=None,
            box=xyxy,
            multimask_output=multimask_output,
            hq_token_only=hq_token_only,
        )
        dt = (time.time() - t0) * 1000.0
        try:
            print(f"[Inference] 输出: masks{getattr(masks,'shape',None)}, scores{getattr(scores,'shape',None)}, logits{getattr(logits,'shape',None)}  用时{dt:.1f}ms")
        except Exception:
            print(f"[Inference] 推理用时{dt:.1f}ms")
        
        if masks.ndim == 3 and masks.shape[0] >= 1:
            mask = masks[0].astype(np.uint8)
        elif masks.ndim == 2:
            mask = masks.astype(np.uint8)
        else:
            mask = np.zeros((np_img.shape[0], np_img.shape[1]), dtype=np.uint8)
        pos = int(mask.sum()) if mask.dtype != bool else int(mask.astype(np.uint8).sum())
        print(f"[Inference] 掩膜像素和: {pos}")
        mask = sam_refiner(image, masks, self.model_hq, use_samhq=True, iters=6)[0]
        
        return mask, pil_img
