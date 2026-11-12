"""English Voice: what it takes to add a new English locale (for example en-IN, en-AU) to a voice assistant's ASR
and NLU, or to raise the quality of an existing one.

Curated and checked on CHECKED_ON: every URL was opened, every arXiv ID was checked against the arXiv API, licences
come from the Hugging Face model/dataset cards, and WER figures are quoted only from the source named next to them.
Bixby specifics come from the public Bixby developer docs only (no internal Samsung process).
"""

from __future__ import annotations

CHECKED_ON = "2026-11-12"
PATH_SLUG = "english-voice-asr-nlu"
PATH_TITLE = "English Voice Assistant: ASR + NLU"
PATH_SUMMARY = ("What you need to add an English locale such as en-IN to a voice assistant: speech basics and "
                "accents, state-of-the-art English ASR, text normalization per locale, language models and biasing, "
                "on-device speech, intent and slot NLU, accents and locale variants, entities, LLM-based NLU, data, "
                "evaluation and launch.")

ARXIV = "https://arxiv.org/abs/"

# ------------------------------------------------------------------ language settings used by the shared voice engine

CODE = "en"
NAME = "English"
TITLE = "English Voice: ASR + NLU"
INTRO = ("What it takes to add a new English locale (such as en-IN or en-AU) to a voice assistant such as Bixby, or to "
         "make an existing one better: the skills, courses and technical modules, the best English models, datasets "
         "and papers, the launch process, how to test ASR and NLU across accents, and how to get and generate data.")
SETTINGS_KEY = "english_voice"
JOB_PREFIX = "ev"
SLUG_PREFIX = "ev-"
QA_SOURCES = "papers, model cards and official docs"

QA_SYSTEM = (
    "You write review questions for an engineer working on English ASR and NLU for a voice assistant (for example "
    "Samsung Bixby), including new English locales such as en-IN and accent robustness. Use web search to check "
    "facts against primary sources: arXiv and ACL/Interspeech papers, Hugging Face model and dataset cards, NVIDIA "
    "NeMo, OpenAI Whisper, ESPnet, k2, Kaldi and bixbydevelopers.com docs (cite bixbydevelopers.com itself, never "
    "mirror sites). Prefer 'why', 'how would you test' and 'what goes wrong' questions over definitions. Never "
    "invent numbers, model names or URLs."
)

RESEARCH_SYSTEM = (
    "You track English speech recognition (ASR) and language understanding (NLU) for engineers building a voice "
    "assistant, with attention to accents (Indian, British, Australian, African, non-native English). Use web "
    "search; open the real pages (Hugging Face, the Open ASR Leaderboard, GitHub, arXiv, ACL Anthology, Interspeech, "
    "vendor docs) and report only what you verified there. Never invent numbers, licences or URLs."
)
RESEARCH_PROMPT = (
    "Find what is new in the last {months} months for English ASR and NLU in voice assistants: new or updated open "
    "models and leaderboard changes (NVIDIA Parakeet/Canary, OpenAI, Distil-Whisper, Moonshine, Kyutai, IBM Granite, "
    "Meta...), commercial speech APIs, accented-English datasets and benchmarks, important papers (arXiv, ACL, "
    "Interspeech, ICASSP) on ASR, spoken language understanding and on-device speech, tools, and notable industry "
    "news (assistants and speech-to-speech models). Search each kind separately."
)

GEN_SYSTEM = (
    "You write NLU training data for an English voice assistant used on phones, watches, TVs and cars. Write what "
    "real users say, not written English: short commands, contractions, filler words, indirect requests ('can you', "
    "'I need'), varied word order, and regional usage when a style asks for it. Indian English should sound natural "
    "to Indian users (e.g. 'kindly', 'prepone', 'lakh', '5 o'clock itself', light Hindi words), never caricatured."
)
GEN_VARY = "phrasing, directness ('set' / 'can you set' / 'I need'), length (2-20 words), filler words, and slot values"
UTTER_STYLES = {
    "standard": ("Standard", "Neutral English as most users would say it"),
    "indian": ("Indian English", "English as commonly spoken in India: local vocabulary, lakh/crore, Indian names and "
                                 "places, occasional Hindi words, natural Indian phrasing"),
    "casual": ("Casual", "Very short, informal or slangy commands, sometimes missing words ('alarm 7 tmrw')"),
    "asr": ("ASR-like", "As a speech recogniser would output it: lowercase, no punctuation, numbers as spoken words "
                        "('seven thirty'), with occasional 'um', 'uh' or a restart"),
}
DEFAULT_UTTER = {
    "intent": "SetAlarm", "description": "Set an alarm for a time, optionally on a date with a label",
    "slots": [{"name": "time", "examples": "6 am, half past seven, 7:30"}, {"name": "date", "examples": "tomorrow, Monday"},
              {"name": "label", "examples": "gym, medicine"}],
    "count": 30, "styles": list(UTTER_STYLES),
}

# ------------------------------------------------------------------ competencies (need: 1 basic … 4 expert)

COMPETENCIES = [
    {"id": "speech", "title": "Speech and signal basics", "skills": [
        ("English phonetics and accent variation", 3, "Indian English (retroflex t/d, v/w merger, syllable-timed "
         "rhythm), British, Australian and African varieties sound different; accents cause most English ASR errors."),
        ("Audio features and front-end", 2, "Sampling rates, log-mel features, VAD and AGC: device front-end "
         "mismatches look like model bugs."),
        ("Acoustics of real devices", 2, "Far-field, echo cancellation and noise suppression change what the model "
         "hears; test data must match."),
    ]},
    {"id": "asr", "title": "ASR modelling", "skills": [
        ("End-to-end ASR (CTC, RNN-T, TDT, attention)", 3, "Today's production models; pick the right loss and "
         "decoder for streaming vs offline."),
        ("State-of-the-art English models", 3, "Parakeet, Canary, Whisper and Distil-Whisper set the bar on the Open "
         "ASR Leaderboard; you need to know their trade-offs."),
        ("Accent adaptation and fine-tuning", 4, "A new English locale is mostly an accent and vocabulary problem; "
         "fine-tuning a strong base on local speech is the core job."),
        ("Language models, decoding and contextual biasing", 3, "Contacts, app names and local places are where "
         "generic models fail; biasing fixes them."),
        ("Streaming and on-device optimisation", 2, "Quantisation, chunked attention, latency budgets, wake word and "
         "endpointing."),
    ]},
    {"id": "nlu", "title": "NLU and language understanding", "skills": [
        ("Intent classification and slot filling", 4, "The core of an assistant's NLU, retrained and tested for each "
         "locale."),
        ("Encoders and small models (DeBERTa, ModernBERT, MobileBERT)", 3, "Backbones for intent and slot models, "
         "and their on-device versions."),
        ("Locale variation in language", 3, "en-IN users say 'prepone the meeting' and 'two lakh rupees'; en-GB "
         "users say 'half seven'. NLU must understand local usage."),
        ("Entity resolution and normalization", 3, "Indian and other non-Anglo names, local places, dates (dd/mm vs "
         "mm/dd), currency and units per locale."),
        ("LLM-based NLU and distillation", 2, "LLMs bootstrap data and handle long-tail requests; small distilled "
         "models run on device."),
    ]},
    {"id": "language", "title": "English language and locale knowledge", "skills": [
        ("Text normalization and ITN per locale", 3, "'two lakh fifty thousand' → 2,50,000 in en-IN; dates, times "
         "and currency formats differ by locale."),
        ("Spelling, vocabulary and style per locale", 2, "colour/color, mobile/cell, 'do the needful'; responses "
         "should sound local."),
        ("Pronunciation lexicons and G2P", 2, "CMUdict covers American English; names and local words need custom "
         "pronunciations."),
    ]},
    {"id": "data", "title": "Data engineering", "skills": [
        ("Data collection and annotation design", 4, "Accent quotas, prompts, transcription conventions and label "
         "guidelines decide quality more than the model does."),
        ("Synthetic data (TTS and LLM generation)", 3, "Fills coverage gaps quickly for new intents and rare "
         "entities, if you control the risks."),
        ("Augmentation (noise, RIR, speed, SpecAugment)", 2, "Cheap robustness to devices and rooms."),
        ("Privacy, consent and licences", 3, "Voice is personal data (GDPR, India's DPDP Act 2023); some corpora "
         "are non-commercial or paid (LDC)."),
    ]},
    {"id": "eval", "title": "Evaluation and testing", "skills": [
        ("ASR metrics and slicing (WER, entity WER)", 4, "A single WER hides accent gaps; slice by accent, noise, "
         "device and domain."),
        ("WER normalization", 3, "Casing, punctuation, numbers and spelling variants change WER by points; use one "
         "normaliser (e.g. Whisper's English normaliser) for every system."),
        ("NLU metrics (intent accuracy, slot F1, exact match, out-of-scope)", 4, "Plus robustness sets with ASR "
         "output and casual phrasing."),
        ("End-to-end task success and human evaluation", 3, "What users feel; the launch gate."),
    ]},
    {"id": "platform", "title": "Assistant platform and production", "skills": [
        ("Locale onboarding in the assistant (Bixby capsules)", 3, "Targets per locale, training utterances "
         "(Aligned NL), dialog and resources per locale."),
        ("Serving, latency and monitoring", 2, "Hybrid on-device/cloud routing, dashboards on live traffic, "
         "rollback."),
        ("Continuous improvement loop", 3, "Mining failures from live traffic (with consent), re-labelling and "
         "regular retraining."),
    ]},
]

# ------------------------------------------------------------------ courses

PHASES = [
    {"id": "foundations", "title": "1. Foundations", "summary": "Speech and language processing basics."},
    {"id": "asr", "title": "2. ASR in practice", "summary": "Train, fine-tune and evaluate speech models."},
    {"id": "nlu", "title": "3. NLU and LLMs", "summary": "Transformers, intent and slot models, LLMs."},
    {"id": "benchmarks", "title": "4. Benchmarks and leaderboards", "summary": "Where English models are compared."},
    {"id": "platform", "title": "5. Assistant platform", "summary": "How a new locale goes into Bixby capsules."},
]


def _course(cid, title, provider, url, phase, *, kind="Course", level="intermediate", cost="Free", covers="",
            top=False):
    return {"id": cid, "title": title, "provider": provider, "url": url, "phase": phase, "kind": kind,
            "level": level, "cost": cost, "covers": covers, "top_pick": top}


COURSES = [
    _course("slp3", "Speech and Language Processing (3rd ed. draft)", "Jurafsky & Martin, Stanford",
            "https://web.stanford.edu/~jurafsky/slp3/", "foundations", kind="Free textbook", level="beginner",
            covers="The standard reference: n-grams, transformers, ASR, TTS, dialogue systems and evaluation.",
            top=True),
    _course("cs224s", "CS224S: Spoken Language Processing", "Stanford", "https://web.stanford.edu/class/cs224s/",
            "foundations", kind="University course (slides, lectures)",
            covers="Speech recognition, end-to-end ASR, TTS, spoken dialogue and voice assistants.", top=True),
    _course("mit-6345", "6.345 Automatic Speech Recognition", "MIT OpenCourseWare",
            "https://ocw.mit.edu/courses/6-345-automatic-speech-recognition-spring-2003/", "foundations",
            kind="University course (lecture notes)", level="intermediate",
            covers="Classic ASR foundations: acoustics, phonetics of English, HMMs and search. Older, but explains "
                   "why lexicons and LMs exist."),
    _course("hf-audio", "Hugging Face Audio Course", "Hugging Face", "https://huggingface.co/learn/audio-course",
            "asr", level="beginner",
            covers="Audio data, Whisper and CTC models, fine-tuning ASR, evaluation with WER. The fastest hands-on "
                   "start.", top=True),
    _course("nemo-asr", "NVIDIA NeMo ASR docs and tutorials", "NVIDIA",
            "https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/intro.html", "asr",
            kind="Docs + notebooks", level="advanced",
            covers="FastConformer CTC, RNN-T and TDT, Parakeet and Canary, fine-tuning, streaming and biasing.",
            top=True),
    _course("whisper-repo", "OpenAI Whisper repository", "OpenAI", "https://github.com/openai/whisper", "asr",
            kind="Code + paper", covers="Model sizes, decoding options and the English text normaliser used for "
                                        "fair WER."),
    _course("speechbrain", "SpeechBrain tutorials", "SpeechBrain", "https://github.com/speechbrain/speechbrain",
            "asr", kind="Toolkit + tutorials",
            covers="PyTorch recipes for ASR, speaker, enhancement and SLU, including SLURP."),
    _course("icefall", "k2 / icefall", "Next-gen Kaldi", "https://k2-fsa.github.io/icefall/", "asr",
            kind="Toolkit docs + recipes", level="advanced",
            covers="Streaming zipformer transducers and, with sherpa-onnx, deployment on Android and embedded "
                   "devices."),
    _course("kaldi", "Kaldi documentation", "Kaldi", "https://kaldi-asr.org/doc/", "asr", kind="Toolkit docs",
            level="advanced", covers="WFST decoding, lexicons and classic hybrid ASR."),
    _course("hf-llm", "Hugging Face LLM Course", "Hugging Face", "https://huggingface.co/learn/llm-course", "nlu",
            level="beginner",
            covers="Transformers, tokenizers, fine-tuning for token classification (slots) and sequence "
                   "classification (intents)."),
    _course("cs224n", "CS224N: NLP with Deep Learning", "Stanford", "https://web.stanford.edu/class/cs224n/", "nlu",
            kind="University course (slides, lectures)", covers="Word vectors to transformers and LLMs."),
    _course("dlai-nlp", "Natural Language Processing Specialization", "DeepLearning.AI on Coursera",
            "https://www.coursera.org/specializations/natural-language-processing", "nlu",
            kind="MOOC with certificate", cost="Free to audit; certificate paid",
            covers="Classification, sequence models, attention and transformers with projects."),
    _course("setfit", "SetFit (few-shot text classification)", "Hugging Face", "https://github.com/huggingface/setfit",
            "nlu", kind="Library + docs", covers="Train an intent classifier from 8-16 examples per intent; good for "
                                                 "bootstrapping a new locale."),
    _course("open-asr", "Open ASR Leaderboard", "Hugging Face", "https://huggingface.co/spaces/hf-audio/open_asr_leaderboard",
            "benchmarks", kind="Leaderboard", covers="Compares open and commercial English ASR on 8 test sets (WER and "
                                                     "speed). Check before picking a model.", top=True),
    _course("open-asr-blog", "Open ASR Leaderboard: how it works", "Hugging Face",
            "https://huggingface.co/blog/open-asr-leaderboard", "benchmarks", kind="Blog",
            covers="Test sets, text normalization and what the numbers mean."),
    _course("bixby-quick", "Bixby Developer Center: quick start", "Samsung",
            "https://bixbydevelopers.com/dev/docs/get-started/quick-start", "platform", kind="Developer docs",
            level="beginner", covers="Capsules, models, actions and Bixby Developer Studio."),
    _course("bixby-training", "Bixby: training for natural language", "Samsung",
            "https://bixbydevelopers.com/dev/docs/dev-guide/developers/handling-nl.training-for-nl", "platform",
            kind="Developer docs",
            covers="Training utterances per language, goals and annotations (Aligned NL), and testing them.",
            top=True),
    _course("bixby-language", "Bixby: modeling language and dialog", "Samsung",
            "https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.language", "platform",
            kind="Developer docs", covers="How a capsule's language resources are modelled per locale."),
    _course("bixby-variations", "Bixby design guide: writing variations", "Samsung",
            "https://bixbydevelopers.com/dev/docs/dev-guide/design-guides/writing.variations", "platform",
            kind="Developer docs", covers="Writing response variations that sound natural in each locale."),
]

# ------------------------------------------------------------------ technical modules (also used for review Q&A)

def _mod(slug, side, title, summary, url, outline, refs=()):
    return {"slug": slug, "side": side, "title": title, "summary": summary, "url": url, "outline": outline,
            "refs": list(refs), "lessons": sum(len(ls) for _, ls in outline)}


MODULES = [
    _mod("ev-speech-basics", "asr", "English speech and accents",
         "How English sounds vary across accents, and how audio becomes model input.",
         "https://web.stanford.edu/~jurafsky/slp3/",
         [("English phonetics", ["English phonemes, stress and reduced vowels",
                                 "Accent features of Indian English (retroflex stops, v/w, rhythm)",
                                 "British, American, Australian and African English differences",
                                 "Non-native English and why ASR degrades on it"]),
          ("Audio front-end", ["Sampling rate, codecs and microphones on phones and TVs",
                               "Log-mel features, VAD, AGC, noise suppression and echo cancellation"])],
         ["https://huggingface.co/learn/audio-course", ARXIV + "2305.15760", ARXIV + "2303.18110"]),
    _mod("ev-asr-models", "asr", "English ASR models: from Whisper to Parakeet",
         "The model families that lead English ASR today, and how to choose and adapt one.",
         "https://huggingface.co/spaces/hf-audio/open_asr_leaderboard",
         [("Architectures", ["CTC, RNN-Transducer and Token-and-Duration Transducer (TDT)",
                             "Attention encoder-decoders and Whisper", "Conformer and FastConformer encoders",
                             "Speech-LLMs (e.g. Canary-Qwen, Granite Speech)"]),
          ("Choosing and adapting", ["Reading the Open ASR Leaderboard: WER vs speed",
                                     "Distillation: Distil-Whisper and small on-device models",
                                     "Self-supervised models: wav2vec 2.0, HuBERT, WavLM",
                                     "Fine-tuning a strong base for a new English accent"])],
         [ARXIV + "2304.06795", ARXIV + "2212.04356", ARXIV + "2510.06961"]),
    _mod("ev-text", "asr", "Text normalization, casing and punctuation",
         "Getting from spoken words to clean written output, per locale, and keeping WER fair.",
         "https://github.com/NVIDIA/NeMo-text-processing",
         [("Normalization", ["Text normalization (TN) for TTS and LM training",
                             "Inverse text normalization (ITN): numbers, dates, times, currency",
                             "Locale formats: lakh/crore in en-IN, dd/mm vs mm/dd, £ vs $"]),
          ("Output formatting", ["Punctuation and capitalization restoration",
                                 "Fully formatted end-to-end ASR (SPGISpeech style)"]),
          ("Scoring", ["WER normalization (Whisper English normaliser) and why it matters",
                       "Pronunciation lexicons (CMUdict) and G2P for names"])],
         [ARXIV + "1611.00068", ARXIV + "2104.02014"]),
    _mod("ev-lm-decoding", "asr", "Language models, decoding and contextual biasing",
         "Getting assistant-specific words right: contacts, apps, places, commands.",
         "https://github.com/kensho-technologies/pyctcdecode",
         [("Decoding", ["Beam search with n-gram LMs (KenLM, pyctcdecode)", "Shallow fusion and LM weight tuning",
                        "WFST decoding graphs in brief"]),
          ("Biasing", ["Contextual biasing: CLAS, TCPGen and word boosting",
                       "Domain LMs for assistant commands", "Rare and out-of-vocabulary names"])],
         [ARXIV + "1808.02480", ARXIV + "2109.00627"]),
    _mod("ev-on-device", "asr", "Wake word, endpointing and on-device ASR",
         "The parts that make an assistant feel fast: wake word, knowing when the user stopped, running locally.",
         "https://github.com/k2-fsa/sherpa-onnx",
         [("Always-on", ["Wake-word / keyword spotting and false-accept trade-offs",
                         "Voice activity detection and endpointing (e.g. Silero VAD)"]),
          ("Streaming", ["Streaming ASR latency: chunking, look-ahead, partial results",
                         "Small models for devices: Moonshine and streaming transducers",
                         "Hybrid on-device and server ASR routing"]),
          ("Optimisation", ["Quantisation and model compression for phones", "Memory, battery and thermal budgets"])],
         [ARXIV + "1811.06621", ARXIV + "2410.15608", ARXIV + "1804.03209"]),
    _mod("ev-nlu-core", "nlu", "Intent classification and slot filling",
         "Mapping an utterance to a goal and its arguments, and saying no to out-of-scope requests.",
         "https://huggingface.co/learn/llm-course",
         [("Task", ["Intents, slots and BIO tagging", "Joint intent-slot models (JointBERT)",
                    "Compositional parses (MTOP / TOP style)", "Out-of-scope detection (CLINC150)"]),
          ("Models", ["Encoders: BERT, RoBERTa, DeBERTa-v3, ModernBERT", "Small models: DistilBERT and MobileBERT",
                      "Few-shot intents with SetFit and sentence embeddings"]),
          ("Benchmarks", ["ATIS, SNIPS, HWU64, SLURP and MASSIVE en-US", "Writing annotation guidelines"])],
         [ARXIV + "1902.10909", ARXIV + "1909.02027", ARXIV + "2011.13205"]),
    _mod("ev-variants", "nlu", "Accents and locale variants (en-IN, en-GB, en-AU…)",
         "What changes when you add a new English locale, and how to adapt ASR and NLU to it.",
         "https://huggingface.co/datasets/ai4bharat/Svarah",
         [("What differs", ["Accent and pronunciation differences per locale",
                            "Vocabulary and usage: prepone, lakh, 'half seven', mobile vs cell",
                            "Code-mixing with Hindi and other languages in en-IN"]),
          ("Adapting", ["Accent benchmarks: Svarah, EdAcc, L2-ARCTIC, Earnings-22",
                        "Accent-aware data collection and fine-tuning",
                        "Locale-specific NLU training and response style"])],
         [ARXIV + "2305.15760", ARXIV + "2303.18110", ARXIV + "2203.15591"]),
    _mod("ev-entities", "nlu", "Entities: names, places, dates, money",
         "Resolving what the user named to something the device can act on, in each locale.",
         "https://github.com/NVIDIA/NeMo-text-processing",
         [("Recognition", ["Names from many cultures in English ASR and NER", "Gazetteers and catalog matching"]),
          ("Resolution", ["Phonetic and fuzzy matching of contact names",
                          "Dates and times per locale ('half seven', 'day after tomorrow')",
                          "Currency, units and number formats per locale"])]),
    _mod("ev-llm-nlu", "nlu", "LLMs for NLU, dialog and responses",
         "Where LLMs help an English assistant, and where small models still win.",
         "https://github.com/huggingface/setfit",
         [("Understanding", ["Few-shot and function-calling NLU with LLMs",
                             "Distilling LLM labels into small on-device models",
                             "End-to-end spoken language understanding (speech to intent)"]),
          ("Responses", ["Localizing responses: spelling, vocabulary and tone per locale",
                         "TTS voices per locale (Kokoro, Parler-TTS, Piper)"])],
         [ARXIV + "2209.11055", ARXIV + "1904.03670"]),
    _mod("ev-data", "process", "Data strategy for a new English locale",
         "Getting the right speech and text data: accent coverage, collection, synthesis and consent.",
         "https://huggingface.co/datasets/MLCommons/peoples_speech",
         [("Planning", ["Variability matrix: accents, devices, noise, domains", "How much local data you need on top "
                        "of a strong base model", "Read vs spontaneous speech"]),
          ("Collection", ["Vendor and crowd collection with accent quotas",
                          "Transcription conventions and inter-annotator agreement"]),
          ("Synthesis", ["Synthetic speech from TTS for new commands and names", "LLM-generated utterances for NLU",
                         "Augmentation: noise, room impulse responses, speed, SpecAugment"]),
          ("Governance", ["Consent, GDPR / DPDP and corpus licences (LDC, non-commercial)"])],
         [ARXIV + "2111.09344", ARXIV + "1909.11699", ARXIV + "1904.08779"]),
    _mod("ev-eval", "process", "Testing and evaluation",
         "Proving the English assistant works for every accent and locale before launch.",
         "https://github.com/jitsi/jiwer",
         [("ASR", ["WER with consistent normalization", "Entity WER and command success",
                   "Slicing by accent, gender, age, noise, device and domain",
                   "Benchmarks: Open ASR Leaderboard sets, ESB, Earnings-22, Svarah"]),
          ("NLU", ["Intent accuracy, slot F1, exact match and out-of-scope", "Robustness sets: ASR output, casual "
                   "phrasing, locale vocabulary"]),
          ("End to end", ["Task success rate and human evaluation", "Regression suites and release gates",
                          "Sample sizes and confidence intervals"])],
         [ARXIV + "2210.13352", ARXIV + "2510.06961"]),
    _mod("ev-launch", "process", "Launching and improving an English locale",
         "The programme from scoping to post-launch, with the Bixby capsule details.",
         "https://bixbydevelopers.com/dev/docs/dev-guide/developers/handling-nl.training-for-nl",
         [("Platform", ["Locale targets and per-locale resources in a capsule",
                        "Training utterances and Aligned NL per locale", "Dialog localization per English locale"]),
          ("Release", ["Dog-food and beta programmes", "Launch gates and staged rollout"]),
          ("Improve", ["Monitoring live quality by accent", "Mining failures and active learning",
                       "Retraining cadence"])]),
]
MODULE_BY_SLUG = {m["slug"]: m for m in MODULES}
SIDES = [
    {"id": "asr", "title": "ASR (speech to text)"},
    {"id": "nlu", "title": "NLU (text to meaning)"},
    {"id": "process", "title": "Data, testing and launch"},
]

# ------------------------------------------------------------------ models

def _model(name, org, kind, url, *, paper="", licence="", size="", on_device="", result="", notes="", top=False):
    return {"name": name, "org": org, "kind": kind, "url": url, "paper": paper, "licence": licence, "size": size,
            "on_device": on_device, "result": result, "notes": notes, "top_pick": top}


MODEL_KINDS = [
    {"id": "asr", "title": "English ASR models"},
    {"id": "nlu", "title": "NLU encoders"},
    {"id": "tooling", "title": "Text tools, TTS and runtimes"},
]

MODELS = [
    _model("Canary-Qwen-2.5B", "NVIDIA", "asr", "https://huggingface.co/nvidia/canary-qwen-2.5b",
           licence="CC-BY-4.0", size="2.5B", on_device="Server",
           result="Open ASR Leaderboard mean WER 5.63 (LibriSpeech clean 1.60, AMI 10.18, Earnings-22 10.42) per "
                  "the model card.",
           notes="Speech-LLM: FastConformer encoder with an LLM decoder. English only. Top accuracy for offline "
                 "transcription.", top=True),
    _model("Parakeet TDT 0.6B v2", "NVIDIA", "asr", "https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2",
           paper=ARXIV + "2304.06795", licence="CC-BY-4.0", size="600M", on_device="Server; small enough for edge GPUs",
           result="Open ASR Leaderboard average WER 6.05 (LibriSpeech clean 1.69, AMI 11.16, Earnings-22 11.15) per "
                  "the model card.",
           notes="FastConformer + Token-and-Duration Transducer: very fast and accurate. English only; v3 adds 25 "
                 "European languages. The best base to fine-tune for a new accent.", top=True),
    _model("Canary-1B-flash", "NVIDIA", "asr", "https://huggingface.co/nvidia/canary-1b-flash",
           paper=ARXIV + "2406.19674", licence="CC-BY-4.0", size="1B", on_device="Server",
           notes="Multilingual ASR and translation (English, German, French, Spanish) with fast decoding."),
    _model("Whisper large-v3 / large-v3-turbo", "OpenAI", "asr", "https://huggingface.co/openai/whisper-large-v3-turbo",
           paper=ARXIV + "2212.04356", licence="MIT (turbo card)", size="1.55B / 809M (turbo)",
           on_device="Turbo on high-end devices; smaller sizes for edge",
           notes="Robust across accents and noise, huge ecosystem. Watch for hallucination on silence; not "
                 "streaming by design."),
    _model("Distil-Whisper large-v3.5", "Hugging Face", "asr", "https://huggingface.co/distil-whisper/distil-large-v3.5",
           paper=ARXIV + "2311.00430", licence="MIT", size="756M",
           on_device="Faster Whisper replacement", notes="Distilled from Whisper: much faster at similar English WER."),
    _model("Moonshine", "Useful Sensors", "asr", "https://github.com/usefulsensors/moonshine",
           paper=ARXIV + "2410.15608", licence="MIT (English models)", size="27M (tiny) / 61M (base)",
           on_device="Yes: built for live transcription and voice commands on device",
           notes="Compute scales with audio length, so short commands are fast. A strong on-device English "
                 "baseline.", top=True),
    _model("Kyutai STT 1B (en/fr)", "Kyutai", "asr", "https://huggingface.co/kyutai/stt-1b-en_fr",
           licence="CC-BY-4.0", size="1B", on_device="Server", notes="Streaming speech-to-text with low latency and "
                                                                    "semantic voice-activity detection."),
    _model("Granite Speech 3.3 8B", "IBM", "asr", "https://huggingface.co/ibm-granite/granite-speech-3.3-8b",
           licence="Apache-2.0", size="8B", on_device="Server",
           notes="Speech-LLM with a permissive licence; good for enterprise research comparisons."),
    _model("HuBERT large (LibriSpeech fine-tuned)", "Meta", "asr", "https://huggingface.co/facebook/hubert-large-ls960-ft",
           paper=ARXIV + "2106.07447", licence="Apache-2.0", size="316M",
           notes="Self-supervised speech model; useful for studying SSL and for small-data accent adaptation."),
    _model("Google Chirp 3 (Cloud Speech-to-Text)", "Google", "asr",
           "https://cloud.google.com/speech-to-text/v2/docs/chirp_3-model", licence="Commercial API", on_device="Cloud",
           notes="Commercial baseline with en-IN and other English locales."),
    _model("Deepgram Nova-3", "Deepgram", "asr", "https://deepgram.com/learn/introducing-nova-3-speech-to-text-api",
           licence="Commercial API", on_device="Cloud", notes="Commercial streaming baseline with keyterm prompting "
                                                              "(biasing)."),
    _model("AssemblyAI Universal", "AssemblyAI", "asr", "https://www.assemblyai.com/universal",
           licence="Commercial API", on_device="Cloud", notes="Commercial baseline; useful to compare accent "
                                                              "robustness."),
    _model("Azure AI Speech", "Microsoft", "asr",
           "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-to-text",
           licence="Commercial API", on_device="Cloud (some containers)",
           notes="Many English locales including en-IN, with custom speech models for adaptation."),
    # NLU
    _model("DeBERTa-v3", "Microsoft", "nlu", "https://huggingface.co/microsoft/deberta-v3-base",
           paper=ARXIV + "2111.09543", licence="MIT", size="184M (base)", on_device="Distil or quantise first",
           notes="Usually the most accurate base-size encoder for intent and slot fine-tuning.", top=True),
    _model("ModernBERT", "Answer.AI / LightOn", "nlu", "https://huggingface.co/answerdotai/ModernBERT-base",
           paper=ARXIV + "2412.13663", licence="Apache-2.0", size="149M (base)",
           notes="Modern, fast encoder with long context; a strong newer default.", top=True),
    _model("DistilBERT", "Hugging Face", "nlu", "https://huggingface.co/distilbert/distilbert-base-uncased",
           paper=ARXIV + "1910.01108", licence="Apache-2.0", size="66M", on_device="Yes, after quantisation",
           notes="Small, fast baseline for intent models."),
    _model("MobileBERT", "Google", "nlu", "https://huggingface.co/google/mobilebert-uncased", paper=ARXIV + "2004.02984",
           licence="Apache-2.0", size="25M", on_device="Yes: designed for phones",
           notes="Task-agnostic compact BERT for on-device NLU."),
    _model("all-MiniLM-L6-v2 (+ SetFit)", "sentence-transformers", "nlu",
           "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2", paper=ARXIV + "2209.11055",
           licence="Apache-2.0", size="22M", on_device="Yes",
           notes="Sentence embeddings for few-shot intents (SetFit), dedupe and nearest-neighbour checks."),
    # tooling
    _model("NeMo Text Processing (TN/ITN)", "NVIDIA", "tooling", "https://github.com/NVIDIA/NeMo-text-processing",
           licence="Apache-2.0", notes="WFST grammars for English text normalization and inverse normalization.",
           top=True),
    _model("Whisper English text normaliser", "OpenAI / community", "tooling",
           "https://pypi.org/project/whisper-normalizer/",
           notes="The normaliser used by most English WER reports; apply it to every system you compare."),
    _model("CMU Pronouncing Dictionary", "CMU", "tooling", "http://www.speech.cs.cmu.edu/cgi-bin/cmudict",
           notes="134k+ American English pronunciations; extend it for names and local words."),
    _model("g2p_en", "Kyubyong Park", "tooling", "https://github.com/Kyubyong/g2p", licence="Apache-2.0",
           notes="Neural grapheme-to-phoneme for words missing from CMUdict."),
    _model("KenLM + pyctcdecode", "K. Heafield / Kensho", "tooling", "https://github.com/kensho-technologies/pyctcdecode",
           notes="n-gram LMs and CTC beam search with hotword boosting."),
    _model("Silero VAD", "Silero", "tooling", "https://github.com/snakers4/silero-vad", licence="MIT",
           on_device="Yes", notes="Small, accurate voice activity detector for endpointing."),
    _model("openWakeWord", "D. Scripka", "tooling", "https://github.com/dscripka/openWakeWord",
           on_device="Yes", notes="Train custom wake words from synthetic speech; check the pre-trained model "
                                  "licences before product use."),
    _model("sherpa-onnx", "k2-fsa", "tooling", "https://github.com/k2-fsa/sherpa-onnx", licence="Apache-2.0",
           on_device="Yes (Android, iOS, embedded)", notes="Runs streaming ASR, wake word and VAD on device."),
    _model("Kokoro-82M", "hexgrad", "tooling", "https://huggingface.co/hexgrad/Kokoro-82M", licence="Apache-2.0",
           size="82M", notes="Small, high-quality English TTS with several accents; good for synthetic training "
                             "audio."),
    _model("Parler-TTS mini", "Hugging Face", "tooling", "https://huggingface.co/parler-tts/parler-tts-mini-v1",
           licence="Apache-2.0", notes="TTS controlled by a text description of the speaker (gender, pace, noise)."),
    _model("jiwer", "Jitsi", "tooling", "https://github.com/jitsi/jiwer", licence="Apache-2.0",
           notes="WER/CER computation in Python. Normalise text first."),
]

# ------------------------------------------------------------------ datasets

def _ds(name, kind, url, *, paper="", licence="", size="", what="", use=""):
    return {"name": name, "kind": kind, "url": url, "paper": paper, "licence": licence, "size": size,
            "what": what, "use": use}


DATASET_KINDS = [
    {"id": "speech", "title": "English speech (training)"},
    {"id": "accent", "title": "Accented English and Indian English"},
    {"id": "benchmark", "title": "Benchmarks and test sets"},
    {"id": "nlu", "title": "NLU and spoken language understanding"},
    {"id": "augment", "title": "Wake word, augmentation and synthesis"},
]

DATASETS = [
    _ds("LibriSpeech", "speech", "https://www.openslr.org/12/", licence="CC-BY-4.0", size="~1,000 h read audiobooks",
        what="The classic read-speech corpus with clean and 'other' test sets.", use="Pre-training and a sanity test; "
                                                                                    "too clean for assistants."),
    _ds("GigaSpeech", "speech", "https://huggingface.co/datasets/speechcolab/gigaspeech", paper=ARXIV + "2106.06909",
        licence="Apache-2.0 (gated)", size="10,000 h transcribed",
        what="Podcasts, YouTube and audiobooks across many topics.", use="Large, varied English training data."),
    _ds("The People's Speech", "speech", "https://huggingface.co/datasets/MLCommons/peoples_speech",
        paper=ARXIV + "2111.09344", licence="CC-BY / CC-BY-SA mix (per card)", size="~30,000 h",
        what="Diverse English speech released for commercial use.", use="Large training set with commercial-friendly "
                                                                        "licensing; check per-file licences."),
    _ds("SPGISpeech", "speech", "https://huggingface.co/datasets/kensho/spgispeech", paper=ARXIV + "2104.02014",
        licence="Kensho licence (gated; read terms)", size="5,000 h",
        what="Financial earnings calls with fully formatted transcripts (casing, punctuation, numbers).",
        use="Training formatted output; check licence for commercial use."),
    _ds("TED-LIUM 3", "speech", "https://huggingface.co/datasets/LIUM/tedlium", paper=ARXIV + "1805.04699",
        what="TED talks.", use="Lecture-style speech; check the licence (non-commercial terms)."),
    _ds("VoxPopuli (English)", "speech", "https://huggingface.co/datasets/facebook/voxpopuli", paper=ARXIV + "2101.00390",
        licence="CC0 (per card)", what="European Parliament speeches, including many non-native speakers.",
        use="Non-native accented English."),
    _ds("Common Voice (English)", "speech", "https://commonvoice.mozilla.org/en/datasets", paper=ARXIV + "1912.06670",
        licence="CC0", what="Crowd-sourced read sentences with self-reported accent labels.",
        use="Accent slices (including India and South Asia) for training and testing."),
    _ds("AMI Meeting Corpus", "speech", "https://huggingface.co/datasets/edinburghcstr/ami", licence="CC-BY-4.0",
        size="~100 h", what="Meetings recorded with close-talk and far-field microphones.",
        use="Far-field and overlapping speech."),
    _ds("Svarah", "accent", "https://huggingface.co/datasets/ai4bharat/Svarah", paper=ARXIV + "2305.15760",
        licence="CC-BY-4.0 (gated)", size="9.6 h, 117 speakers, 65 districts in 19 states",
        what="Indian-accented English: read and spontaneous, including tasks like ordering groceries and payments.",
        use="The key en-IN accent test set; shows how much English ASR drops on Indian accents."),
    _ds("NPTEL2020 Indian English", "accent", "https://github.com/AI4Bharat/NPTEL2020-Indian-English-Speech-Dataset",
        size="15,700 h (noisy subtitles)", what="Indian-accented lecture speech from NPTEL videos.",
        use="Large but noisy en-IN training data; filter before use."),
    _ds("EdAcc (Edinburgh International Accents of English)", "accent",
        "https://huggingface.co/datasets/edinburghcstr/edacc", paper=ARXIV + "2303.18110",
        what="Conversations between speakers of many English accents worldwide.",
        use="Accent robustness test across dozens of accents."),
    _ds("L2-ARCTIC", "accent", "https://psi.engr.tamu.edu/l2-arctic-corpus/",
        what="Non-native English (Hindi, Mandarin, Arabic, Korean, Spanish, Vietnamese L1 speakers).",
        use="Study pronunciation differences by first language."),
    _ds("Speech Accent Archive", "accent", "https://accent.gmu.edu/",
        what="The same paragraph read by speakers of hundreds of language backgrounds.",
        use="Learn accent features; small, for analysis not training."),
    _ds("Open ASR Leaderboard test sets / ESB", "benchmark", "https://huggingface.co/datasets/hf-audio/esb-datasets-test-only-sorted",
        paper=ARXIV + "2210.13352", what="AMI, Earnings-22, GigaSpeech, LibriSpeech, SPGISpeech, TED-LIUM and "
                                         "VoxPopuli test sets in one place.",
        use="Compare your model with published leaderboard numbers."),
    _ds("Earnings-22", "benchmark", "https://huggingface.co/datasets/distil-whisper/earnings22",
        paper=ARXIV + "2203.15591", what="Earnings calls from companies around the world.",
        use="Accents in the wild, with entity-heavy speech."),
    _ds("Switchboard", "benchmark", "https://catalog.ldc.upenn.edu/LDC97S62", licence="LDC (paid licence)",
        what="Telephone conversations.", use="Classic conversational benchmark; needs an LDC licence."),
    _ds("SLURP", "nlu", "https://github.com/pswietojanski/slurp", paper=ARXIV + "2011.13205",
        what="Spoken commands to a home assistant, with audio, intents and entities.",
        use="Train and test end-to-end spoken language understanding."),
    _ds("MASSIVE (en-US)", "nlu", "https://huggingface.co/datasets/AmazonScience/massive", paper=ARXIV + "2204.08582",
        licence="CC-BY-4.0", size="11,514 train / 2,033 dev / 2,974 test per locale",
        what="Assistant utterances with 60 intents and 55 slot types.", use="Standard assistant NLU benchmark."),
    _ds("SNIPS", "nlu", "https://github.com/sonos/nlu-benchmark", paper=ARXIV + "1805.10190",
        what="Utterances for 7 assistant intents with slots.", use="Quick intent/slot sanity benchmark."),
    _ds("HWU64 (NLU-Evaluation-Data)", "nlu", "https://github.com/xliuhw/NLU-Evaluation-Data", paper=ARXIV + "1903.05566",
        what="25k home-assistant utterances across 64 intents.", use="Broad intent coverage."),
    _ds("CLINC150", "nlu", "https://github.com/clinc/oos-eval", paper=ARXIV + "1909.02027", licence="CC-BY-3.0",
        what="150 intents plus out-of-scope queries.", use="Test that the assistant refuses what it can't do."),
    _ds("MTOP (English)", "nlu", ARXIV + "2008.09335", paper=ARXIV + "2008.09335",
        what="Compositional assistant parses.", use="Nested and multi-intent requests."),
    _ds("Speech Commands", "augment", "https://huggingface.co/datasets/google/speech_commands",
        paper=ARXIV + "1804.03209", licence="CC-BY-4.0", what="One-second spoken keywords.",
        use="Train and test keyword spotting / wake-word models."),
    _ds("MUSAN noise corpus", "augment", "https://www.openslr.org/17/", licence="CC-BY-4.0",
        what="Music, speech and noise recordings.", use="Mix in background noise for robust ASR."),
    _ds("Room impulse responses (OpenSLR 28)", "augment", "https://www.openslr.org/28/", licence="Apache-2.0",
        what="Real and simulated room impulse responses.", use="Simulate far-field and reverberant rooms."),
]

# ------------------------------------------------------------------ papers (all IDs checked on arXiv)

def _paper(arxiv_id, title, year, topic, why, top=False):
    return {"id": arxiv_id, "title": title, "year": year, "topic": topic, "url": ARXIV + arxiv_id, "why": why,
            "top_pick": top}


PAPER_TOPICS = [
    {"id": "asr-sota", "title": "State-of-the-art English ASR"},
    {"id": "asr-core", "title": "Core ASR methods"},
    {"id": "accent", "title": "Accents and benchmarks"},
    {"id": "data", "title": "Data and augmentation"},
    {"id": "nlu", "title": "NLU and spoken language understanding"},
    {"id": "device", "title": "On-device, wake word and biasing"},
]

PAPERS = [
    _paper("2212.04356", "Robust Speech Recognition via Large-Scale Weak Supervision", 2022, "asr-sota",
           "Whisper: why large weakly supervised training is robust to accents and noise.", True),
    _paper("2304.06795", "Efficient Sequence Transduction by Jointly Predicting Tokens and Durations", 2023,
           "asr-sota", "TDT, the decoder behind Parakeet TDT: faster transducer inference.", True),
    _paper("2305.05084", "Fast Conformer with Linearly Scalable Attention for Efficient Speech Recognition", 2023,
           "asr-sota", "The FastConformer encoder used by Parakeet and Canary."),
    _paper("2406.19674", "Less is More: Accurate Speech Recognition & Translation without Web-Scale Data", 2024,
           "asr-sota", "Canary: top accuracy with far less data than Whisper."),
    _paper("2311.00430", "Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling", 2023,
           "asr-sota", "How to make Whisper much faster for production."),
    _paper("2510.06961", "Open ASR Leaderboard: Towards Reproducible and Transparent Multilingual and Long-Form "
                         "Speech Recognition Evaluation", 2025, "asr-sota",
           "How the leaderboard measures WER and speed fairly.", True),
    _paper("2005.08100", "Conformer: Convolution-augmented Transformer for Speech Recognition", 2020, "asr-core",
           "The encoder behind most production ASR."),
    _paper("1211.3711", "Sequence Transduction with Recurrent Neural Networks", 2012, "asr-core",
           "The RNN-Transducer: the streaming model family assistants use."),
    _paper("2006.11477", "wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations", 2020,
           "asr-core", "Self-supervised speech: learn from unlabelled audio."),
    _paper("2106.07447", "HuBERT: Self-Supervised Speech Representation Learning by Masked Prediction of Hidden "
                         "Units", 2021, "asr-core", "A strong self-supervised alternative to wav2vec 2.0."),
    _paper("2305.15760", "Svarah: Evaluating English ASR Systems on Indian Accents", 2023, "accent",
           "Shows how far English ASR drops on Indian accents, with a public test set.", True),
    _paper("2303.18110", "The Edinburgh International Accents of English Corpus: Towards the Democratization of "
                         "English ASR", 2023, "accent", "Accent gaps across dozens of English varieties."),
    _paper("2203.15591", "Earnings-22: A Practical Benchmark for Accents in the Wild", 2022, "accent",
           "Real-world accented speech with named entities."),
    _paper("2210.13352", "ESB: A Benchmark For Multi-Domain End-to-End Speech Recognition", 2022, "accent",
           "Why one test set is not enough; the basis of the Open ASR Leaderboard."),
    _paper("2004.09249", "CHiME-6 Challenge: Tackling Multispeaker Speech Recognition for Unsegmented Recordings",
           2020, "accent", "Far-field, multi-speaker home recordings: the hardest assistant-like conditions."),
    _paper("2106.06909", "GigaSpeech: An Evolving, Multi-domain ASR Corpus with 10,000 Hours of Transcribed Audio",
           2021, "data", "How a large, varied English corpus was built."),
    _paper("2111.09344", "The People's Speech: A Large-Scale Diverse English Speech Recognition Dataset for "
                         "Commercial Usage", 2021, "data", "A large corpus with commercial-friendly licensing."),
    _paper("2104.02014", "SPGISpeech: 5,000 hours of transcribed financial audio for fully formatted end-to-end "
                         "speech recognition", 2021, "data", "Training ASR to output punctuated, formatted text."),
    _paper("1805.04699", "TED-LIUM 3: twice as much data and corpus repartition for experiments on speaker "
                         "adaptation", 2018, "data", "Speaker adaptation experiments on lecture speech."),
    _paper("2101.00390", "VoxPopuli: A Large-Scale Multilingual Speech Corpus for Representation Learning, "
                         "Semi-Supervised Learning and Interpretation", 2021, "data",
           "Includes lots of non-native English."),
    _paper("1912.06670", "Common Voice: A Massively-Multilingual Speech Corpus", 2019, "data",
           "Crowd collection with accent metadata."),
    _paper("1904.08779", "SpecAugment: A Simple Data Augmentation Method for Automatic Speech Recognition", 2019,
           "data", "The default augmentation for ASR training."),
    _paper("1909.11699", "Speech Recognition with Augmented Synthesized Speech", 2019, "data",
           "When TTS-generated audio helps ASR, and how to stop it hurting.", True),
    _paper("1611.00068", "RNN Approaches to Text Normalization: A Challenge", 2016, "data",
           "Why text normalization is hard and where neural models fail."),
    _paper("1902.10909", "BERT for Joint Intent Classification and Slot Filling", 2019, "nlu",
           "The standard joint intent-slot architecture.", True),
    _paper("1810.04805", "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding", 2018,
           "nlu", "The encoder most NLU models still build on."),
    _paper("1907.11692", "RoBERTa: A Robustly Optimized BERT Pretraining Approach", 2019, "nlu",
           "Better pre-training for the same architecture."),
    _paper("2111.09543", "DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled "
                         "Embedding Sharing", 2021, "nlu", "A top base-size encoder for classification."),
    _paper("2412.13663", "Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory "
                         "Efficient, and Long Context Finetuning and Inference", 2024, "nlu", "ModernBERT."),
    _paper("1910.01108", "DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter", 2019,
           "nlu", "Small models for fast intent classification."),
    _paper("2004.02984", "MobileBERT: a Compact Task-Agnostic BERT for Resource-Limited Devices", 2020, "nlu",
           "BERT built for phones."),
    _paper("2209.11055", "Efficient Few-Shot Learning Without Prompts", 2022, "nlu",
           "SetFit: intents from a handful of examples."),
    _paper("1805.10190", "Snips Voice Platform: an embedded Spoken Language Understanding system for "
                         "private-by-design voice interfaces", 2018, "nlu",
           "An end-to-end on-device assistant stack, described openly.", True),
    _paper("1903.05566", "Benchmarking Natural Language Understanding Services for building Conversational Agents",
           2019, "nlu", "HWU64 and a comparison of commercial NLU services."),
    _paper("1909.02027", "An Evaluation Dataset for Intent Classification and Out-of-Scope Prediction", 2019, "nlu",
           "CLINC150: testing what the assistant should refuse."),
    _paper("2011.13205", "SLURP: A Spoken Language Understanding Resource Package", 2020, "nlu",
           "Spoken assistant commands with audio and labels."),
    _paper("2204.08582", "MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 "
                         "Typologically-Diverse Languages", 2022, "nlu", "The standard assistant NLU benchmark."),
    _paper("2008.09335", "MTOP: A Comprehensive Multilingual Task-Oriented Semantic Parsing Benchmark", 2020, "nlu",
           "Compositional assistant parses."),
    _paper("1811.06621", "Streaming End-to-end Speech Recognition For Mobile Devices", 2018, "device",
           "How RNN-T got onto phones: latency, size and quality.", True),
    _paper("2410.15608", "Moonshine: Speech Recognition for Live Transcription and Voice Commands", 2024, "device",
           "Small English ASR built for on-device commands."),
    _paper("1808.02480", "Deep context: end-to-end contextual speech recognition", 2018, "device",
           "CLAS: biasing ASR towards contacts and app names."),
    _paper("2109.00627", "Tree-constrained Pointer Generator for End-to-end Contextual Speech Recognition", 2021,
           "device", "TCPGen: scalable biasing to large lists of names."),
    _paper("1804.03209", "Speech Commands: A Dataset for Limited-Vocabulary Speech Recognition", 2018, "device",
           "The standard keyword-spotting dataset."),
    _paper("1711.07128", "Hello Edge: Keyword Spotting on Microcontrollers", 2017, "device",
           "Small-footprint wake-word models."),
]

# ------------------------------------------------------------------ launch playbook

PLAYBOOK = [
    {"id": "scope", "title": "Scope the locale",
     "goal": "Decide what the new English locale (e.g. en-IN) must support, and how it differs from en-US.",
     "steps": ["Pick the locale and devices: phone, watch, TV, fridge, car",
               "List launch domains and intents, ranked by usage in existing English locales",
               "List locale differences: vocabulary, number and date formats, spelling, names, code-mixing",
               "Set launch quality targets per domain and per accent group",
               "Check legal: consent, privacy law for the market, corpus licences"],
     "outputs": ["Locale scope document", "Quality targets", "Locale difference list"],
     "owners": "Product, language lead, legal",
     "pitfalls": ["Assuming en-US models are 'good enough' without measuring on local accents"]},
    {"id": "language", "title": "Define locale language resources",
     "goal": "Agreed spelling, formats and pronunciations for the locale across ASR, NLU and TTS.",
     "steps": ["Write the transcription convention (spelling variant, numbers, fillers, local words)",
               "Write TN/ITN rules for local formats (lakh/crore, dates, currency, phone numbers)",
               "Extend the pronunciation lexicon with local names and places",
               "Write NLU annotation guidelines with locale examples for every slot",
               "Pick one WER normaliser for all evaluations"],
     "outputs": ["Transcription guide", "TN/ITN grammar", "Lexicon additions", "Annotation guide"],
     "owners": "Linguists, ASR and NLU engineers",
     "pitfalls": ["Comparing WER across systems with different normalisers"]},
    {"id": "data", "title": "Plan and get data",
     "goal": "Training and test data that covers the locale's accents and conditions.",
     "steps": ["Fill the variability matrix and set accent and device quotas",
               "Inventory open data and licences (Svarah, Common Voice accents, People's Speech, MASSIVE…)",
               "Commission local collection for gaps: wake word, commands, far-field, regions",
               "Generate synthetic data: LLM utterances in the local style, TTS for local names",
               "Freeze speaker-disjoint test sets before training"],
     "outputs": ["Data plan with quotas", "Training sets", "Frozen test sets"],
     "owners": "Data lead, vendors, annotators",
     "pitfalls": ["Test speakers leaking into training", "Only urban, educated speakers"]},
    {"id": "asr", "title": "Adapt ASR",
     "goal": "An ASR model that meets targets for the locale's accents.",
     "steps": ["Benchmark baselines on local test sets: current production model, Parakeet, Canary, Whisper, APIs",
               "Fine-tune the chosen base on local speech; add augmentation",
               "Tune the wake word on local speakers; check false accepts with local TV and speech",
               "Add local entities to biasing lists and the domain LM",
               "Optimise for streaming and on-device; measure latency"],
     "outputs": ["Locale ASR model", "Wake-word tuning", "Benchmark report"],
     "owners": "ASR team", "pitfalls": ["Improving local accents while regressing other English locales"]},
    {"id": "nlu", "title": "Adapt NLU",
     "goal": "Intents and slots that understand local usage and phrasing.",
     "steps": ["Add locale training utterances per intent: native writers plus LLM generation",
               "Fine-tune or extend the English NLU model with locale data",
               "Localise entity resolution: names, places, dates, currency, units",
               "Train and test on ASR output, not only clean text",
               "Check out-of-scope handling with locale examples"],
     "outputs": ["Locale NLU model", "Entity resolvers", "NLU test report"],
     "owners": "NLU team", "pitfalls": ["Copying en-US training data and only changing spellings"]},
    {"id": "platform", "title": "Localise the assistant",
     "goal": "Every capsule and response works and sounds natural in the locale.",
     "steps": ["Add the locale to each capsule's targets",
               "Write locale training utterances (Aligned NL) per goal",
               "Localise dialog: spelling, vocabulary, formats, tone",
               "Choose the locale TTS voice; check names and numbers",
               "Localise UI strings, help and errors"],
     "outputs": ["Localised capsules", "Locale dialog", "TTS voice"],
     "owners": "Capsule developers, content writers",
     "pitfalls": ["en-US responses that sound foreign to local users"]},
    {"id": "test", "title": "Test end to end",
     "goal": "Evidence the launch targets are met for every accent group.",
     "steps": ["ASR tests per accent and condition slice; NLU tests on clean and ASR text",
               "End-to-end task tests on real devices in real rooms",
               "Human evaluation with local users from several regions",
               "Regression suite across all English locales",
               "Fix, retrain, repeat until the gates pass"],
     "outputs": ["Test report per slice", "Go/no-go sign-off"], "owners": "QA, language lead",
     "pitfalls": ["Testing only with the engineering team's accents"]},
    {"id": "beta", "title": "Dog-food and beta",
     "goal": "Real users and devices before public launch.",
     "steps": ["Internal dog-food with speakers from different regions", "Closed beta with opted-in users",
               "Triage failures: ASR, NLU, entity, capsule, TTS", "Fix top issues and retrain"],
     "outputs": ["Beta findings", "Updated models"], "owners": "Programme, QA",
     "pitfalls": ["Beta group that doesn't match the target users"]},
    {"id": "launch", "title": "Launch",
     "goal": "Ship safely and be able to roll back.",
     "steps": ["Staged rollout by device and region", "Dashboards: usage, task success, fallbacks, latency",
               "Rollback plan and on-call"],
     "outputs": ["Live locale"], "owners": "Programme, SRE", "pitfalls": ["No rollback path for models"]},
    {"id": "improve", "title": "Improve continuously",
     "goal": "Quality keeps rising after launch, for every accent.",
     "steps": ["Mine low-confidence and failed requests (with consent)", "Label and add them to training",
               "Retrain on a regular cadence and re-run all test sets",
               "Track the gap between accent groups and close it"],
     "outputs": ["Monthly quality report", "Retrained models"], "owners": "ASR, NLU and data teams",
     "pitfalls": ["Average quality rising while one accent group falls behind"]},
]

# ------------------------------------------------------------------ testing

TESTING = [
    {"id": "asr", "title": "ASR testing", "metrics": [
        ("WER (word error rate)", "(substitutions + deletions + insertions) / reference words",
         "Normalise both sides the same way first (casing, punctuation, numbers, spelling variants)."),
        ("Accent gap", "WER of each accent group minus the best group's WER",
         "The fairness metric for a new English locale; track it every release."),
        ("Entity / keyword error rate", "Errors on names, apps, numbers and command words only",
         "What actually breaks commands, even when WER looks fine."),
        ("Sentence error rate", "Share of utterances with any error", "Matches how users feel short commands."),
        ("Wake-word FAR / FRR", "False accepts per hour of non-wake audio; false rejects per wake attempt",
         "Tune per device and test with local TV and background speech."),
        ("Latency and real-time factor", "Time to final result after end of speech; compute per second of audio",
         "Measure on the target device."),
     ], "slices": ["Accent / region", "Native vs non-native speakers", "Gender and age group", "Device and microphone",
                   "Near vs far field", "Noise type and SNR", "Domain", "Code-mixing (en-IN)", "Utterance length"]},
    {"id": "nlu", "title": "NLU testing", "metrics": [
        ("Intent accuracy", "Share of utterances with the right intent", "Report per intent, not only overall."),
        ("Slot F1", "Precision and recall of slot spans and labels", "Use exact span match."),
        ("Exact match (semantic accuracy)", "Intent and all slots correct", "The NLU launch metric."),
        ("Robustness gap", "Score on clean text minus score on ASR output or casual phrasing",
         "Shows where NLU depends on perfect input."),
        ("Out-of-scope detection", "Correct rejection of requests the assistant can't do",
         "Use CLINC150-style out-of-scope sets."),
     ], "slices": ["Clean text vs ASR n-best", "Local vocabulary and phrasing", "Paraphrases", "Rare entities",
                   "Per intent and domain"]},
    {"id": "e2e", "title": "End-to-end and human testing", "metrics": [
        ("Task success rate", "Did the device do what the user asked?", "The launch gate."),
        ("Turns to success / fallback rate", "Extra turns and 'sorry, I didn't get that' rate",
         "A measure of user friction."),
        ("Response quality (human rating)", "Local users rate correctness, naturalness and tone",
         "Catches responses that sound foreign to the locale."),
        ("TTS intelligibility and MOS", "Listener scores of the locale voice", "Includes local names and numbers."),
        ("Regression", "No drop in other English locales or earlier builds", "Run before every release."),
     ], "slices": ["Real devices and rooms", "Regions", "First-time vs experienced users"]},
]

TEST_SIZING = [
    "WER differences under about 0.5% absolute need thousands of utterances per slice to be meaningful; use "
    "bootstrap confidence intervals.",
    "Keep test speakers out of training data entirely (speaker-disjoint splits).",
    "Freeze and version test sets; never tune on them.",
    "Have at least a few hundred utterances per accent group so the accent gap is stable.",
    "Score every system with the same normaliser, or the comparison is meaningless.",
]

# ------------------------------------------------------------------ data variability, sourcing and generation

VARIABILITY = [
    {"dimension": "Accent and first language",
     "values": ["Indian English: North, South, East, West and North-East", "Hindi, Tamil, Telugu, Bengali, Marathi "
                "first-language speakers", "British, American, Australian, African English",
                "Other non-native English"],
     "why": "Accent is the biggest source of English ASR error; Svarah and EdAcc show large gaps.",
     "how": "Accent quotas in collection; Svarah, Common Voice accent labels and EdAcc for testing."},
    {"dimension": "Speaker demographics", "values": ["Gender balance", "Children, adults, elderly",
                                                     "Urban vs rural", "Education levels"],
     "why": "Pitch, pace and vocabulary vary.", "how": "Quota per cell; check open datasets' distributions."},
    {"dimension": "Speaking style", "values": ["Read prompts", "Spontaneous commands", "Follow-ups",
                                               "Disfluencies and restarts", "Fast vs slow speech"],
     "why": "Users don't read to assistants.", "how": "Scenario prompts ('ask the phone to…') instead of reading."},
    {"dimension": "Local vocabulary and code-mixing", "values": ["Locale words (prepone, lakh, petrol pump)",
                                                                 "Hindi words in en-IN", "Local brands and apps",
                                                                 "Spelling variants"],
     "why": "NLU and ITN must handle local usage.", "how": "Native writers plus LLM generation in the local style."},
    {"dimension": "Acoustic environment", "values": ["Quiet room", "TV or music", "Traffic and outdoors",
                                                     "Kitchen, fan, AC", "In-car", "Other speakers"],
     "why": "Real homes are noisy.", "how": "Record in real places; augment with MUSAN at several SNRs."},
    {"dimension": "Device and distance", "values": ["Phone near-field", "Arm's length", "Watch",
                                                    "TV / fridge far-field", "Earbuds", "Low-end mics"],
     "why": "Microphones and distance change the signal a lot.",
     "how": "Collect on target hardware; simulate distance with room impulse responses."},
    {"dimension": "Content and entities", "values": ["Contacts with names from many cultures", "App names",
                                                     "Local places and addresses", "Numbers, dates, money",
                                                     "Song and film titles", "Every launch intent"],
     "why": "Entities are where commands fail.",
     "how": "Template + gazetteer generation, TTS for rare names, and biasing tests."},
]

SOURCING = [
    {"method": "Open datasets", "how": "LibriSpeech, GigaSpeech, People's Speech, Common Voice, Svarah, MASSIVE, "
                                      "SLURP (see the Datasets list).",
     "pros": "Free and large.", "cons": "Licences vary (non-commercial, LDC paid); little local-accent assistant "
                                        "speech."},
    {"method": "Vendor collection", "how": "Commission recordings with accent, device, environment and domain "
                                          "quotas; a specification with prompts and QA rules.",
     "pros": "Matches your locale, devices and domains.", "cons": "Costly and slow; needs strong QA."},
    {"method": "Crowd / community collection", "how": "Crowd platforms for wide regional reach.",
     "pros": "Many speakers quickly.", "cons": "Variable quality; validate every clip."},
    {"method": "In-house dog-food", "how": "Employees and testers record commands on real devices.",
     "pros": "Realistic, quick.", "cons": "Biased to employees' accents."},
    {"method": "Live traffic (with consent)", "how": "After launch, sample opted-in requests, mainly failures, and "
                                                    "label them.",
     "pros": "Exactly your distribution.", "cons": "Only after launch; strict privacy controls."},
    {"method": "Mining public audio", "how": "Align lectures or broadcasts with subtitles (as NPTEL2020 did).",
     "pros": "Large local-accent volume.", "cons": "Noisy transcripts; check rights."},
]

GENERATION = [
    {"name": "LLM utterance generation (NLU)", "for": "nlu",
     "how": "Give the LLM an intent, slots and example values; ask for varied phrasings in standard, local (e.g. "
            "Indian English), casual and ASR-like styles, with slot labels. Dedupe, validate slots and have local "
            "speakers review a sample.",
     "caution": "LLMs drift to formal, American phrasing; ask for local styles explicitly and check diversity.",
     "tool": "The Utterance generator on this page does this."},
    {"name": "Template + gazetteer expansion (NLU)", "for": "nlu",
     "how": "Carrier phrases with slots ('call {contact} on {app}') filled from local entity lists.",
     "caution": "Too much templated data makes models brittle.", "tool": ""},
    {"name": "Locale rewriting (NLU)", "for": "nlu",
     "how": "Rewrite existing en-US training data into the new locale's vocabulary and formats with an LLM, then "
            "review.", "caution": "Rewrites keep en-US sentence patterns; add native-written data too.", "tool": ""},
    {"name": "TTS synthetic speech (ASR)", "for": "asr",
     "how": "Synthesise new commands and local names with several voices and accents, then add noise and "
            "reverberation.",
     "caution": "Keep synthetic audio a minority; check on real accent test sets.", "tool": "Kokoro, Parler-TTS"},
    {"name": "Noise and room augmentation (ASR)", "for": "asr",
     "how": "Mix MUSAN noise at several SNRs and convolve with room impulse responses.",
     "caution": "Match the noise your users have.", "tool": "MUSAN, OpenSLR RIRs"},
    {"name": "Speed perturbation and SpecAugment (ASR)", "for": "asr",
     "how": "Speed perturb at 0.9x/1.0x/1.1x; mask time and frequency bands in training.",
     "caution": "Standard and safe; small gains.", "tool": "SpecAugment, torchaudio"},
    {"name": "Pseudo-labelling local audio (ASR)", "for": "asr",
     "how": "Transcribe unlabelled local-accent audio with a strong model (as Distil-Whisper did), keep "
            "high-confidence results, train on them.",
     "caution": "Errors reinforce themselves; filter by confidence and model agreement.", "tool": "Distil-Whisper recipe"},
]

PLATFORM_NOTES = [
    "Each Bixby capsule declares the device types and language/locale pairs it supports in the targets block of "
    "capsule.bxb, so a new English locale means adding its target to every capsule you launch.",
    "Natural language training is per locale: each capsule needs training utterances for that locale, written as "
    "Aligned NL (the utterance plus its goal and slot annotations).",
    "Training entries double as tests: a mismatch means the planner's goal differs from the one in the Aligned NL.",
    "Dialog and responses are localized per locale; spelling, vocabulary and formats should match local use.",
    "Bixby added Indian English (en-IN) with Hinglish vocabulary in 2021; this tab covers adding or improving any "
    "English locale, based on public documentation only.",
]
