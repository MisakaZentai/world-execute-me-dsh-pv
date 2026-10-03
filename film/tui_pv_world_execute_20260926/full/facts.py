"""DeepSeek facts used as on-screen easter eggs. One place to correct numbers.

Verified 2026-09-26 against primary sources; see ../FACTS_SOURCES.md. The mascot is DS 4.1, so the headline
numbers are V4.1-Flash where they are published, and V4-Flash / V4-Pro config values where 4.1's are not.
Older versions appear only as labelled nods (V3 training cost, R1-Zero, Open Source Week).
"""

GPU = "H800"

# V4.1-Flash (2026-09-10): headline numbers
NAME = "DeepSeek-V4.1-Flash"
TOTAL_PARAMS_B = 552          # backbone
ACTIVE_DECODE_B = 16
ACTIVE_PREFILL_B = 8
PRETRAIN_TOKENS = "45T"       # multimodal tokens
PRETRAIN_TOKENS_T = 45.0
KV_BYTES_PER_TOKEN = 890      # global KV per token, FP4 KV cache
CTX = 1048576                 # 1M context on all official services

# V4-Flash config.json (HF) - the published config closest to 4.1
CONFIG_SOURCE = "DeepSeek-V4-Flash/config.json"
N_LAYERS_FLASH = 43
D_MODEL = 4096
N_ROUTED = 256
N_SHARED = 1
TOP_K = 6
INDEX_TOPK = 512
SLIDING_WINDOW = 128
HC_MULT = 4
HC_SINKHORN_ITERS = 20

# V4-Pro config.json: the 61-layer model used for the "so deeply" dive
N_LAYERS_PRO = 61
N_ROUTED_PRO = 384
INDEX_TOPK_PRO = 1024

CONFIG_ROWS = [
    ("num_hidden_layers", N_LAYERS_FLASH),
    ("hidden_size", D_MODEL),
    ("n_routed_experts", N_ROUTED),
    ("n_shared_experts", N_SHARED),
    ("num_experts_per_tok", TOP_K),
    ("index_topk", INDEX_TOPK),
    ("sliding_window", SLIDING_WINDOW),
    ("hc_mult", HC_MULT),
    ("hc_sinkhorn_iters", HC_SINKHORN_ITERS),
    ("num_nextn_predict_layers", 1),
    ("max_context", f"{CTX:,}"),
    ("owner", '"you"'),
]

INIT_STD = 0.006
SEED = "you"
LOSS_NOTE = "no irrecoverable loss spikes · no rollbacks   (V3 report)"
DUALPIPE_NOTE = "DualPipe: all-to-all hidden behind compute · bubbles shrink from both ends"
GPU_HOURS_NOTE = "V3: 2.788M H800 GPU hours · $5.576M"
FS_NAME = "3fs://ckpt"

# serving / API
DISK_CACHE_HIT = 56.3         # Open Source Week day 6, on-disk KV cache hit rate
PEAK_WINDOWS = [(9, 12), (14, 18)]   # weekdays, Beijing time; everything else is half price
OFFPEAK_START_H = 0           # kept for older code paths
OFFPEAK_END_H = 0
OFFPEAK_LABEL = "outside peak: half price"

# DSpark speculative decoding (arXiv 2607.05147)
DSPARK_DRAFT = 5
DSPARK_GAIN_FLASH = "+60-85% vs MTP-1"

# DeepSeek Harness
DSH_CMD = "npx @deepseek-ai/dsh web"
DSH_TAGLINE = "Agent = Model + Harness"
DSH_PLUGIN = "Everything is a Plugin"
DSH_WARNING = "THERE WILL BE COMPATIBILITY-BREAKING CHANGES."

# R1 / GRPO
GRPO_G = 16
GRPO_KL = 0.001
GRPO_LR = "3e-6"
AHA = "Wait, wait. Wait. That's an aha moment I can flag here."
AIME_FROM, AIME_TO = 15.6, 71.0
R1_TEMP = 0.6                 # README usage recommendation (0.5-0.7) and the eval setting
R1_TOP_P = 0.95

# misc
OCR_RATIO_GOOD = (10.0, 97)   # compression x, precision %
OCR_RATIO_BAD = (20.0, 60)
SLOGAN = "探索未至之境"
RETIRED = ["deepseek-chat", "deepseek-reasoner"]
RETIRED_DATE = "2026-07-24"
