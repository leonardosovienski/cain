"""Local claim verifiers loaded from pinned snapshots: no remote code, no network at inference.

* HHEM-2.1-Open (vectara/hallucination_evaluation_model, Apache-2.0): the published model is a
  ``T5ForTokenClassification`` over google/flan-t5-base; its custom class only formats a fixed
  prompt and reads softmax(logits[:, 0, :])[:, 1]. That is reproduced here from the reviewed
  code at the pinned revision instead of ``trust_remote_code``.
* MiniCheck-Flan-T5-Large (lytang/MiniCheck-Flan-T5-Large, MIT): seq2seq; input
  ``"predict: " + premise + </s> + hypothesis`` (max 2048 tokens), one decoder step from token 0,
  softmax over the logits of token ids 3 and 209; index 1 is the support probability.

Thresholds are policy, not code: ``claims/data/verifier-policy.json`` (versioned, hashed in every
assessment). Both checkpoints are trained on English; see the golden set report for Portuguese.
"""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path

HHEM_REPO, HHEM_REVISION = "vectara/hallucination_evaluation_model", "8e4a2e6e96c708cc76c2344f7e4757df2515292c"
FLAN_T5_BASE_REPO, FLAN_T5_BASE_REVISION = "google/flan-t5-base", "7bcac572ce56db69c1ea7c8af255c5d7c9672fc2"
MINICHECK_REPO, MINICHECK_REVISION = "lytang/MiniCheck-Flan-T5-Large", "96eafd01cee2d16cf81aaa2fb226b14f422a37b3"
HHEM_PROMPT = ("<pad> Determine if the hypothesis is true given the premise?\n\n"
               "Premise: {text1}\n\nHypothesis: {text2}")
DEFAULT_MODELS_DIR = Path.home() / "predictors" / "tools" / "hf" / "models"


def policy() -> dict:
    raw = files("cain.claims").joinpath("data/verifier-policy.json").read_bytes()
    value = json.loads(raw)
    value["sha256"] = sha256(raw).hexdigest()
    return value


def _snapshot(models_dir, repo: str) -> Path:
    path = Path(models_dir or DEFAULT_MODELS_DIR) / repo.replace("/", "--")
    if not path.is_dir():
        raise FileNotFoundError(f"verifier snapshot missing: {path} (download {repo} at the pinned revision)")
    return path


class HHEMVerifier:
    verifier_id = HHEM_REPO
    weights_revision = HHEM_REVISION

    def __init__(self, models_dir=None, *, threshold: float):
        import torch
        from safetensors.torch import load_file
        from transformers import AutoConfig, AutoTokenizer, T5ForTokenClassification

        base = _snapshot(models_dir, FLAN_T5_BASE_REPO)
        weights = _snapshot(models_dir, HHEM_REPO) / "model.safetensors"
        self.torch, self.threshold = torch, threshold
        self.tokenizer = AutoTokenizer.from_pretrained(base, local_files_only=True)
        self.model = T5ForTokenClassification(AutoConfig.from_pretrained(base, local_files_only=True))
        state = {key[len("t5."):]: value for key, value in load_file(str(weights)).items() if key.startswith("t5.")}
        result = self.model.load_state_dict(state, strict=False)
        missing = [key for key in result.missing_keys if not key.endswith("embed_tokens.weight")]
        if missing or result.unexpected_keys:
            raise RuntimeError(f"HHEM weights do not match T5ForTokenClassification: {missing[:5]} "
                               f"{result.unexpected_keys[:5]}")
        self.model.eval()

    def score(self, premise: str, hypothesis: str) -> float:
        inputs = self.tokenizer([HHEM_PROMPT.format(text1=premise, text2=hypothesis)], return_tensors="pt",
                                padding=True)
        with self.torch.no_grad():
            logits = self.model(**inputs).logits[:, 0, :]
        return float(self.torch.softmax(logits, dim=-1)[0, 1])


class MiniCheckVerifier:
    verifier_id = MINICHECK_REPO
    weights_revision = MINICHECK_REVISION

    def __init__(self, models_dir=None, *, threshold: float):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        path = _snapshot(models_dir, MINICHECK_REPO)
        self.torch, self.threshold = torch, threshold
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True)
        self.model.eval()

    def score(self, premise: str, hypothesis: str) -> float:
        text = "predict: " + self.tokenizer.eos_token.join([premise, hypothesis])
        inputs = self.tokenizer([text], max_length=2048, truncation=True, return_tensors="pt")
        decoder = self.torch.zeros((1, 1), dtype=self.torch.long)
        with self.torch.no_grad():
            logits = self.model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"],
                                decoder_input_ids=decoder).logits.squeeze(1)
        return float(self.torch.softmax(logits[:, [3, 209]], dim=-1)[0, 1])


def load_default_pair(models_dir=None) -> list:
    """The two verifiers named by the versioned policy, with the policy's thresholds."""
    rules = policy()
    return [HHEMVerifier(models_dir, threshold=rules["thresholds"][HHEM_REPO]),
            MiniCheckVerifier(models_dir, threshold=rules["thresholds"][MINICHECK_REPO])]
